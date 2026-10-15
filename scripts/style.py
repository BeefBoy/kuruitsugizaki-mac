"""A style profile from a folder of .flp: what the person's projects have in common, as profile.json and a plain
profile.md. Reads only; writes to tmp/profile/<folder name>/.

Weights: files under a favourites/ (favorites/, fav/) folder count 3; files under negative/ (bad/, hate/) are left out
of the totals and reported as a contrast. Without favourites, a file counts 1, plus 0.5 each for 32 bars or more of
arrangement, a render (.wav/.mp3) beside it, and a name that reads as a later version (v2, final, _3).

Roles are guessed from content, not channel names (most are defaults like "Nexus #3"): samplers and audio clips by
words in the sample's file name; synths by register, notes sounding at once and note length.
"""
import json
import math
import re
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

import flp
import project
from view import PARKED, midi, tick

PPQ, BAR, STEP = 96, 384, 24
FAV, NEG = {"favourites", "favorites", "fav"}, {"negative", "bad", "hate"}
KITS = {"FPC", "Addictive Drums 2", "Kickstart 2", "Battery 4", "Fruity slicer", "Slicex"}
DRUM_WORDS = [  # first match wins
    ("kick", r"kick|kck|\bbd\b|bassdrum"), ("808", r"808"), ("snare", r"snare|snr|\bsd\b|\brim"), ("clap", r"clap|clp"),
    ("hat", r"\b[foc]?hats?\b|hihat|hi hat|\bhh\b|\boh\b|\bch\b|shaker"), ("cymbal", r"crash|\bride\b|cymbal|\bcym\b"),
    ("perc", r"perc|\btoms?\b|conga|bongo|tamb|cowbell"),
]
AUDIO_WORDS = [("own bounce", r"\bmaster\b|\d{4} \d\d \d\d \d\d \d\d|^pattern \d+"),  # words() has turned _ and - into spaces
               ("vocal", r"vox|vocal|acap|chop|verse|hook"), ("fx", r"riser|impact|sweep|noise|fx|downlifter|uplifter"),
               ("drum loop", r"break|amen|drum|loop|kit")]
PROFILES = {  # Krumhansl-Kessler
    "major": [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88],
    "minor": [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17],
}
PC = "C C# D D# E F F# G G# A A# B".split()
CHORDS = [("maj7", (0, 4, 7, 11)), ("m7", (0, 3, 7, 10)), ("7", (0, 4, 7, 10)), ("m7b5", (0, 3, 6, 10)), ("", (0, 4, 7)),
          ("m", (0, 3, 7)), ("dim", (0, 3, 6)), ("aug", (0, 4, 8)), ("sus4", (0, 5, 7)), ("sus2", (0, 2, 7)), ("5", (0, 7))]
DEGREE = ["I", "bII", "II", "bIII", "III", "IV", "bV", "V", "bVI", "VI", "bVII", "VII"]


def words(text: str, table) -> str | None:
    t = text.lower().replace("_", " ").replace("-", " ")
    return next((role for role, pat in table if re.search(pat, t)), None)


def weight_of(path: Path, root: Path, bars: float, any_fav: bool) -> float:
    parts = {p.lower() for p in path.relative_to(root).parts[:-1]}
    if parts & NEG:
        return 0.0
    if any_fav:
        return 3.0 if parts & FAV else 1.0
    w = 1.0 + 0.5 * (bars >= 32)
    w += 0.5 * any(path.with_suffix(s).exists() for s in (".wav", ".mp3"))
    w += 0.5 * bool(re.search(r"v\d|final|_\d+$", path.stem.lower()))
    return w


def key_of(pcs: list[float]) -> tuple[str, float]:
    if sum(pcs) == 0:
        return "?", 0.0
    best = ("?", -2.0)
    for mode, prof in PROFILES.items():
        for t in range(12):
            x = pcs[t:] + pcs[:t]
            mx, my = sum(x) / 12, sum(prof) / 12
            num = sum((a - mx) * (b - my) for a, b in zip(x, prof))
            den = math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in prof)) or 1
            if num / den > best[1]:
                best = (f"{PC[t]} {mode}", num / den)
    return best[0], round(best[1], 2)


def chord_name(keys: list[int]) -> tuple[int, str] | None:
    pcs = {k % 12 for k in keys}
    if len(pcs) < 2:
        return None
    bass = min(keys) % 12
    for name, tpl in CHORDS:
        for root in sorted(pcs, key=lambda r: (r != bass, r)):
            if {(root + i) % 12 for i in tpl} <= pcs and len(pcs) - len(tpl) <= 1:
                return root, name
    return None


def roman(root: int, name: str, tonic: int) -> str:
    d = DEGREE[(root - tonic) % 12]
    minor = name.startswith("m") and not name.startswith("maj") or name in ("dim", "m7b5")
    return (d.lower() if minor else d) + (name[1:] if name.startswith("m") and not name.startswith("maj") else name)


def synth_role(notes: list[dict]) -> str:
    keys = [midi(n["key"]) for n in notes]
    starts = Counter(tick(n["at"]) for n in notes)
    poly = st.mean(starts.values())
    med, length = st.median(keys), st.median(n["len"] for n in notes)
    if med < 48 and poly < 1.5:
        return "bass"
    if poly >= 2.5:
        return "pad" if length >= PPQ else "chords"
    if length <= STEP * 2 and len(notes) >= 16:
        return "arp"
    return "lead"


def steps_line(hist: list[float]) -> str:
    return "".join("X" if p >= 0.75 else "x" if p >= 0.4 else "-" if p >= 0.1 else "." for p in hist)


def one(path: Path, root: Path, any_fav: bool) -> dict:
    raw = path.read_bytes()
    p = flp.parse(raw)
    d = project.export(str(path))
    out = {"file": path.relative_to(root).as_posix(), "fl": d["project"].get("fl_version"), "bpm": d["project"].get("bpm"),
           "flags": [] if flp.serialize(p) == raw else ["does not round-trip"]}
    notes_by = defaultdict(list)
    pat_insts = defaultdict(set)
    for pt in d["patterns"]:
        for n in pt["notes"]:
            notes_by[n["inst"]].append((pt["id"], n))
            pat_insts[pt["id"]].add(n["inst"])
    insts = {c["id"]: c for c in d["instruments"]}
    insts.update({c["id"]: dict(c, kind="sampler") for c in d["samples"] if c["id"] in notes_by})  # audio channels played from patterns
    placed = {c.get("sampler") or c.get("plugin") for a in d["arrangements"] for c in a["clips"]} - {None}
    roles = {}
    for iid, c in insts.items():
        ns = [n for _, n in notes_by.get(iid, [])]
        plugin = c.get("plugin") or c.get("kind")
        if plugin in KITS:
            roles[iid] = "drum kit"
        elif c.get("kind") == "sampler":
            if not ns and iid not in placed:
                roles[iid] = "unused"
            else:
                roles[iid] = words(Path((c.get("path") or "").replace("\\", "/")).name + " " + c["name"], DRUM_WORDS) or (synth_role(ns) if ns else "sampler")
        elif ns:
            roles[iid] = synth_role(ns)
        else:
            roles[iid] = "unused"
    for iid, ns in notes_by.items():
        if iid not in insts:
            out["flags"].append(f"notes on a channel not read: {iid}")
    # arrangement: the one with most clips
    arrs = sorted(d["arrangements"], key=lambda a: -len(a["clips"]))
    clips = [c for c in (arrs[0]["clips"] if arrs else []) if tick(c["at"]) < PARKED]
    bad = [c for c in clips if not 1 <= c["track"] <= 500 or c["len"] > BAR * 2000]
    if bad:
        out["flags"].append(f"{len(bad)} clips off the playlist or absurdly long")
        clips = [c for c in clips if c not in bad]
    end = max((tick(c["at"]) + c["len"] for c in clips), default=0)
    nbars = math.ceil(end / BAR)
    out["bars"] = nbars
    audio = {c["id"]: c for c in d["samples"]}
    active = [set() for _ in range(nbars)]
    for c in clips:
        s, e = tick(c["at"]), tick(c["at"]) + c["len"]
        who = pat_insts.get(c["pattern"], set()) if "pattern" in c else {c.get("audio") or c.get("sampler") or c.get("plugin")} - {None}
        for b in range(s // BAR, min(nbars, math.ceil(e / BAR))):
            active[b] |= who
    dens = [len(a) for a in active]
    sections, start = [], 0
    for b in range(1, nbars + 1):
        if b == nbars or active[b] != active[b - 1]:
            if b > start:
                sections.append(b - start)
            start = b
    merged = []  # runs shorter than 2 bars join the one before
    for s in sections:
        if merged and s < 2:
            merged[-1] += s
        else:
            merged.append(s)
    out["sections"] = merged
    out["density"] = dens
    if dens and max(dens):
        top = max(dens)
        out["intro_bars"] = next(i for i, v in enumerate(dens) if v >= top / 2)
        out["first_full_bar"] = next(i for i, v in enumerate(dens) if v == top) + 1
    # key from the pitched parts, weighted by length
    pcs = [0.0] * 12
    for iid, ns in notes_by.items():
        if roles.get(iid) in ("bass", "pad", "chords", "lead", "arp", "808", "sampler"):
            for _, n in ns:
                pcs[midi(n["key"]) % 12] += n["len"]
    out["key"], out["key_fit"] = key_of(pcs)
    tonic = PC.index(out["key"].split()[0]) if out["key"] != "?" else 0
    # drums: step histogram over one bar, per role
    drums = {}
    pat_bars = {pt["id"]: max(1, math.ceil(pt["len_from_notes"] / BAR)) for pt in d["patterns"]}
    for iid, ns in notes_by.items():
        r = roles.get(iid)
        if r not in ("kick", "snare", "clap", "hat", "perc", "cymbal", "808"):
            continue
        hist, bars_seen, vel, off = [0.0] * 16, 0, [], 0
        for pid in {pid for pid, _ in ns}:
            pn = [n for q, n in ns if q == pid]
            nb = pat_bars[pid]
            bars_seen += nb
            hits = defaultdict(set)
            for n in pn:
                t = tick(n["at"])
                hits[t // BAR].add(round((t % BAR) / STEP) % 16)
                off += t % STEP != 0
                vel.append(n["vel"])
            for steps in hits.values():
                for s in steps:
                    hist[s] += 1
        drums.setdefault(r, {"hist": [0.0] * 16, "bars": 0, "vel": [], "off": 0, "n": 0})
        g = drums[r]
        g["hist"] = [a + b for a, b in zip(g["hist"], hist)]
        g["bars"] += bars_seen
        g["vel"] += vel
        g["off"] += off
        g["n"] += len(ns)
    out["drums"] = {r: {"steps": [round(h / g["bars"], 2) for h in g["hist"]], "vel_mean": round(st.mean(g["vel"])),
                        "vel_sd": round(st.pstdev(g["vel"]), 1), "off_grid": round(g["off"] / g["n"], 2)} for r, g in drums.items() if g["n"]}
    # harmony: stacks that start together on one chord-playing channel
    chords, progs = Counter(), []
    for iid, ns in notes_by.items():
        if roles.get(iid) not in ("pad", "chords", "lead", "arp", "sampler"):
            continue
        for pid in sorted({pid for pid, _ in ns}):
            at = defaultdict(list)
            for q, n in ns:
                if q == pid:
                    at[tick(n["at"])].append(midi(n["key"]))
            seq = []
            for t in sorted(at):
                if len(set(k % 12 for k in at[t])) >= 3:
                    c = chord_name(at[t])
                    if c:
                        rn = roman(c[0], c[1], tonic)
                        chords[rn] += 1
                        if not seq or seq[-1] != rn:
                            seq.append(rn)
            if len(seq) >= 2:
                progs.append(seq)
    out["chords"] = dict(chords.most_common(10))
    out["progressions"] = [" ".join(s[:8]) for s in progs[:12]]
    bass = [midi(n["key"]) for iid, ns in notes_by.items() if roles.get(iid) in ("bass", "808") for _, n in ns]
    out["bass_median"] = PC[int(st.median(bass)) % 12] + str(int(st.median(bass)) // 12 - 1) if bass else None
    # palette with pointers to the sound itself
    pal = []
    for iid, c in insts.items():
        if roles[iid] == "unused":
            continue
        e = {"role": roles[iid], "plugin": c.get("plugin") or c.get("kind"), "channel": c["ch"], "notes": len(notes_by.get(iid, [])),
             "from": str(path.resolve())}
        if c.get("path"):
            e["sample"] = Path(c["path"].replace("\\", "/")).name
        hints = (c.get("state") or {}).get("hints")
        if hints:
            e["hints"] = hints[:2]
        if c.get("mixer") is not None:
            e["insert"] = c["mixer"]
        pal.append(e)
    for c in d["samples"]:
        if c["id"] in insts:
            continue
        name = Path((c.get("path") or c["name"]).replace("\\", "/")).name
        kind = ("own bounce" if Path(name).stem.lower().startswith(path.stem.lower()[:8]) else None) or words(name, AUDIO_WORDS) \
            or ("drum hit" if words(name, DRUM_WORDS) else "other")
        pal.append({"role": "audio: " + kind, "sample": name, "channel": c["ch"], "from": str(path.resolve()),
                    **({"insert": c["mixer"]} if c.get("mixer") is not None else {})})
    out["palette"] = pal
    fx = defaultdict(list)
    for e in sorted(d["mixer"]["effects"], key=lambda e: (e["track"], e["slot"])):
        fx[e["track"]].append(e["plugin"])
    out["master"] = fx.get(0, [])
    out["master_slots"] = [e["slot"] for e in sorted(d["mixer"]["effects"], key=lambda e: e["slot"]) if e["track"] == 0]
    out["path"] = str(path.resolve())
    out["inserts"] = {r: fx[e["insert"]] for e in pal for r in [e["role"]] if e.get("insert") and fx.get(e["insert"])}
    autos = []
    for a in d["automation"]:
        t = a.get("target") or {}
        if "global" in t:
            autos.append(t["global"])
        elif "mixer" in t and "slot" in t:
            plug = next((e["plugin"] for e in d["mixer"]["effects"] if e["track"] == t["mixer"] and e["slot"] == t["slot"]), "effect")
            autos.append(f"{plug} param {t.get('param', t.get('rec'))}")
        elif "mixer" in t:
            autos.append(f"{'master' if t['mixer'] == 0 else 'insert'} {t.get('param')}")
        elif "channel" in t:
            ch = insts.get(t["channel"])
            if ch is None and str(t["channel"]).startswith("rack"):
                out["flags"].append(f"automation aimed at a channel not read: {t['channel']}")
            autos.append(f"{(ch or {}).get('plugin') or roles.get(t['channel'], 'channel')} {t.get('param', t.get('rec'))}")
    out["automation"] = autos
    out["weight"] = weight_of(path, root, nbars, any_fav)
    return out


def wsum(rows, key):
    c = Counter()
    for r in rows:
        v = key(r)
        for k in (v if isinstance(v, (list, set, tuple)) else [v]):
            if k is not None:
                c[k] += r["weight"]
    return c


def aggregate(rows: list[dict]) -> dict:
    use = [r for r in rows if r["weight"] > 0]
    W = sum(r["weight"] for r in use) or 1
    pct = lambda c, n=8: {k: round(100 * v / W) for k, v in c.most_common(n)}
    ag = {"files": len(rows), "counted": len(use), "contrast": [r["file"] for r in rows if r["weight"] == 0]}
    ag["bpm"] = pct(wsum(use, lambda r: round(r["bpm"]) if r["bpm"] else None))
    ag["key"] = pct(wsum(use, lambda r: r["key"] if r["key_fit"] >= 0.6 else None))
    ag["mode"] = pct(wsum(use, lambda r: r["key"].split()[1] if r["key"] != "?" and r["key_fit"] >= 0.6 else None))
    arranged = [r for r in use if r["bars"]]
    ag["bars"] = {"median": st.median([r["bars"] for r in arranged]) if arranged else 0,
                  "range": [min(r["bars"] for r in arranged), max(r["bars"] for r in arranged)] if arranged else None}
    sec = Counter()
    for r in use:
        for s in r["sections"]:
            sec[s] += r["weight"]
    stot = sum(sec.values()) or 1
    ag["section_bars"] = {k: round(100 * v / stot) for k, v in sec.most_common(8)}
    ag["intro_bars"] = st.median([r["intro_bars"] for r in arranged if "intro_bars" in r]) if arranged else None
    ag["first_full_bar"] = st.median([r["first_full_bar"] for r in arranged if "first_full_bar" in r]) if arranged else None
    curve = [0.0] * 10
    for r in arranged:
        dn, top = r["density"], max(r["density"]) or 1
        for i in range(10):
            seg = dn[i * len(dn) // 10:(i + 1) * len(dn) // 10] or [0]
            curve[i] += r["weight"] * st.mean(seg) / top
    tw = sum(r["weight"] for r in arranged) or 1
    ag["density_curve"] = [round(v / tw, 2) for v in curve]
    drums = {}
    for role in ("kick", "snare", "clap", "hat", "perc", "808"):
        have = [r for r in use if role in r["drums"]]
        if not have:
            continue
        w = sum(r["weight"] for r in have)
        steps = [round(sum(r["weight"] * r["drums"][role]["steps"][i] for r in have) / w, 2) for i in range(16)]
        drums[role] = {"files": len(have), "steps": steps, "line": steps_line(steps),
                       "vel_mean": round(st.mean(r["drums"][role]["vel_mean"] for r in have)),
                       "vel_sd": round(st.mean(r["drums"][role]["vel_sd"] for r in have), 1),
                       "off_grid": round(st.mean(r["drums"][role]["off_grid"] for r in have), 2)}
    ag["drums"] = drums
    ch = Counter()
    for r in use:
        for k, v in r["chords"].items():
            ch[k] += v * r["weight"]
    tot = sum(ch.values()) or 1
    ag["chords"] = {k: round(100 * v / tot) for k, v in ch.most_common(10)}
    ag["progressions"] = [p for p, _ in wsum(use, lambda r: r["progressions"]).most_common(8)]
    ag["bass"] = pct(wsum(use, lambda r: r["bass_median"]), 5)
    roles = defaultdict(Counter)
    pointers = defaultdict(list)
    for r in sorted(use, key=lambda r: -r["weight"]):
        for e in r["palette"]:
            name = e.get("plugin") if e.get("plugin") not in (None, "sampler", "audio") else e.get("sample", e.get("plugin"))
            roles[e["role"]][name] += r["weight"]
            if len(pointers[e["role"]]) < 4 and e.get("notes", 1):
                pointers[e["role"]].append({k: e[k] for k in ("plugin", "sample", "from", "channel", "hints") if k in e})
    ag["palette"] = {role: dict(c.most_common(6)) for role, c in sorted(roles.items(), key=lambda kv: -sum(kv[1].values()))}
    ag["pointers"] = dict(pointers)
    chains = wsum(use, lambda r: [tuple(r["master"])])
    ag["master"] = {" > ".join(k): round(100 * v / W) for k, v in chains.most_common(5)}
    top = next((k for k, _ in chains.most_common() if k), None)
    if top:  # the chain itself, to copy: mixer.effects [{track: 0, slot, from: {file, track: 0, slot}}]
        r = max((r for r in use if tuple(r["master"]) == top), key=lambda r: r["weight"])
        ag["pointers"]["master chain"] = [{"plugin": p, "from": {"file": r["path"], "track": 0, "slot": s}} for p, s in zip(r["master"], r["master_slots"])]
    ag["master_plugins"] = pct(wsum(use, lambda r: set(r["master"])), 10)
    ins = defaultdict(Counter)
    for r in use:
        for role, chain in r["inserts"].items():
            for p in set(chain):
                ins[role][p] += r["weight"]
    ag["inserts"] = {role: dict(c.most_common(5)) for role, c in ins.items()}
    ag["automation"] = pct(wsum(use, lambda r: set(re.sub(r" \d+$", "", a) for a in r["automation"])), 10)
    ag["flags"] = {r["file"]: r["flags"] for r in rows if r["flags"]}
    return ag


def statements(ag: dict) -> list[str]:
    s = []
    top = lambda d, n=2: ", ".join(f"{k} ({v}%)" for k, v in list(d.items())[:n])
    if ag["bpm"]:
        s.append(f"You mostly work at {top(ag['bpm'], 3)} BPM.")
    if ag["key"]:
        s.append(f"Your projects sit in {top(ag['key'], 3)}; {top(ag['mode'])} overall.")
    if ag["bars"]["median"]:
        s.append(f"An arrangement runs about {ag['bars']['median']:g} bars; its sections are {top(ag['section_bars'], 3)} bars long "
                 f"(share of all sections), and everything is first playing at once around bar {ag['first_full_bar']:g}.")
    for role in ("kick", "snare", "clap", "hat"):
        g = ag["drums"].get(role)
        if g:
            s.append(f"{role.capitalize()} on one bar of 16ths: {g['line']} (X almost always, x often, - sometimes, . rarely), velocity about {g['vel_mean']} "
                     f"give or take {g['vel_sd']:g}, {round(100 * g['off_grid'])}% of hits off the 16th grid (played in, not drawn).")
    if ag["chords"]:
        s.append(f"Chords, relative to the key: {top(ag['chords'], 4)}.")
    for role in ("bass", "808", "lead", "pad", "chords", "arp"):
        if role in ag["palette"]:
            s.append(f"{role.capitalize()}: {', '.join(list(ag['palette'][role])[:3])}.")
    if ag["master_plugins"]:
        s.append(f"On the master: {top(ag['master_plugins'], 4)}.")
    if ag["automation"]:
        s.append(f"What you automate: {top(ag['automation'], 4)}.")
    return s


def markdown(ag: dict, rows: list[dict], folder: Path) -> str:
    L = [f"# Profile of {folder.name}", "", f"{ag['files']} projects read, {ag['counted']} counted"
         + (f", {len(ag['contrast'])} kept as contrast ({', '.join(ag['contrast'])})" if ag["contrast"] else "") + ".", "",
         "## Read back", "", "Strike what is wrong; the rest is what a new piece will follow.", ""]
    L += [f"- {x}" for x in statements(ag)]
    kv = lambda d: ", ".join(f"{k} {v}%" for k, v in d.items()) or "none"
    L += ["", "## Tempo and key", "", f"- BPM: {kv(ag['bpm'])}", f"- Key (fit 0.6 or better): {kv(ag['key'])}", f"- Mode: {kv(ag['mode'])}",
          "", "## Form", "", f"- Length: median {ag['bars']['median']:g} bars, range {ag['bars']['range']}",
          f"- Section lengths in bars, share of all sections: {kv(ag['section_bars'])}",
          f"- Bars before half of the instruments are playing: median {ag['intro_bars']}; bar where everything first plays: median {ag['first_full_bar']}",
          f"- How full the arrangement is, start to end in tenths (1 = everything playing): {' '.join(f'{v:.2f}' for v in ag['density_curve'])}",
          "", "## Drums", "", "One bar of 16ths, share of bars with a hit: X 75% or more, x 40%, - 10%, . less.", "", "```"]
    for role, g in ag["drums"].items():
        L.append(f"{role:6} |{g['line']}|  vel {g['vel_mean']} +-{g['vel_sd']:g}, off grid {round(100 * g['off_grid'])}%, {g['files']} files")
    L += ["```", "", "## Harmony", "", f"- Chords relative to the key: {kv(ag['chords'])}",
          "- Common progressions: " + ("; ".join(ag["progressions"]) or "none found"), f"- Bass register: {kv(ag['bass'])}", "",
          "## Sounds", "", "Weighted counts per role. `pointers` in profile.json name the file and channel each sound lives in; project_write",
          "takes them as an instrument's state, `{from: file, channel: n}`, so a sound is reused without being decoded.", ""]
    for role, c in ag["palette"].items():
        L.append(f"- {role}: {', '.join(f'{k} {v:g}' for k, v in c.items())}")
    L += ["", "## Mixer", "", f"- Master plugins: {kv(ag['master_plugins'])}",
          "- Master chains (the most common non-empty one is in `pointers['master chain']`, ready for `mixer.effects`):"]
    L += [f"  - {k or '(empty)'}: {v}%" for k, v in ag["master"].items()]
    for role, c in ag["inserts"].items():
        L.append(f"- {role} insert: {', '.join(c)}")
    L += ["", "## Automation", "", f"- {kv(ag['automation'])}", ""]
    if ag["contrast"]:
        L += ["## Contrast", "", "Files you marked as not you, beside the totals:", ""]
        for r in rows:
            if r["weight"] == 0:
                L.append(f"- {r['file']}: {r['bpm']:g} BPM, {r['key']}, {r['bars']} bars, master {' > '.join(r['master']) or 'empty'}")
        L.append("")
    if ag["flags"]:
        L += ["## Read problems", ""] + [f"- {f}: {'; '.join(v)}" for f, v in ag["flags"].items()] + [""]
    L += ["## Projects", "", "| file | weight | BPM | key (fit) | bars | FL |", "|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (-r["weight"], r["file"])):
        L.append(f"| {r['file']} | {r['weight']:g} | {r['bpm']:g} | {r['key']} ({r['key_fit']}) | {r['bars']} | {r['fl']} |")
    return "\n".join(L) + "\n"


def build(folder: str, out_dir: str | None = None) -> dict:
    root = Path(folder).resolve()
    files = sorted(root.rglob("*.flp"))
    if not files:
        raise ValueError(f"no .flp under {root}")
    any_fav = any({p.lower() for p in f.relative_to(root).parts[:-1]} & FAV for f in files)
    rows, errors = [], {}
    for f in files:
        try:
            rows.append(one(f, root, any_fav))
        except Exception as e:
            errors[f.relative_to(root).as_posix()] = repr(e)[:200]
    ag = aggregate(rows)
    if errors:
        ag["flags"].update({k: ["not read: " + v] for k, v in errors.items()})
    out = Path(out_dir) if out_dir else Path(__file__).resolve().parent.parent / "tmp" / "profile" / root.name
    out.mkdir(parents=True, exist_ok=True)
    md = markdown(ag, rows, root)
    (out / "profile.json").write_text(json.dumps({"folder": str(root), "aggregate": ag, "projects": rows}, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "profile.md").write_text(md, encoding="utf-8")
    return {"json": str(out / "profile.json"), "md": str(out / "profile.md"), "read": len(rows), "not_read": len(errors), "profile": md}


if __name__ == "__main__":
    import os
    folder = str(Path(sys.argv[1]).resolve())
    out = str(Path(sys.argv[2]).resolve()) if len(sys.argv) > 2 else None
    os.chdir(Path(__file__).resolve().parent.parent)  # project.py opens the template relative to the repo, as the server does
    r = build(folder, out)
    print(r["profile"])
    print(f"wrote {r['json']} and {r['md']}")
