import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from project import export

GRIDS = (("1/4", 96), ("1/8", 48), ("1/16", 24), ("1/32", 12), ("1/8T", 32), ("1/16T", 16))


def tick(at, ppq=96):
    return ((at[0] - 1) * 4 + (at[1] - 1)) * ppq + at[2]


def midi(key: str) -> int:
    names = "C C# D D# E F F# G G# A A# B".split()
    i = 2 if key[1:2] == "#" else 1
    return names.index(key[:i]) + (int(key[i:]) + 1) * 12


def grid_of(t: int) -> tuple[str, int]:
    for g, s in GRIDS[:3]:
        if t % s == 0:
            return g, 0
    for g, s in GRIDS[4:]:
        if t % s == 0:
            return g, 0
    best = min(((g, t - round(t / s) * s) for g, s in GRIDS[:3] + GRIDS[4:]), key=lambda x: abs(x[1]))
    return best


def timing(notes) -> dict:
    c, offs = Counter(), []
    for n in notes:
        g, off = grid_of(tick(n["at"]))
        if off:
            c["off"] += 1
            offs.append(abs(off))
        else:
            c["triplet" if g.endswith("T") else "straight"] += 1
    total = sum(c.values()) or 1
    out = {k: round(100 * v / total) for k, v in c.items()}
    if offs:
        out["off_median_ticks"] = sorted(offs)[len(offs) // 2]
    return out


def bars(t: int, ppq=96) -> float:
    return round(t / (4 * ppq), 2)


def summarize(doc: dict) -> dict:
    ppq = doc["project"]["ppq"]
    used = Counter(n["inst"] for p in doc["patterns"] for n in p["notes"])
    clips_by_src = Counter()
    for a in doc["arrangements"]:
        for c in a["clips"]:
            clips_by_src[c.get("pattern") or c.get("audio") or c.get("automation") or c.get("channel")] += 1
    out = {"project": {k: doc["project"][k] for k in ("bpm", "ppq")},
           "instruments": [], "samples": [], "automation": [], "patterns": [], "arrangements": [],
           "mixer_effects": defaultdict(list)}
    for c in doc["instruments"]:
        row = {"id": c["id"], "plugin": c.get("plugin", c["kind"]), "mixer": c.get("mixer"), "notes": used.get(c["id"], 0)}
        if c["name"] != c.get("plugin"):
            row["name"] = c["name"]
        if c.get("state", {}).get("hints"):
            row["preset_hints"] = c["state"]["hints"][:2]
        out["instruments"].append(row)
    for c in doc["samples"]:
        out["samples"].append({"id": c["id"], "file": Path(c.get("path", "").replace("\\", "/")).name, "mixer": c.get("mixer"), "clips": clips_by_src.get(c["id"], 0)})
    for c in doc["automation"]:
        pts = c.get("points") or []
        vals = [p["value"] for p in pts]
        out["automation"].append({"id": c["id"], "target": c.get("target"), "points": len(pts),
                                  "range": [round(min(vals), 3), round(max(vals), 3)] if vals else None,
                                  "clips": clips_by_src.get(c["id"], 0)})
    for p in doc["patterns"]:
        ns = p["notes"]
        row = {"id": p["id"], "clips": clips_by_src.get(p["id"], 0), "notes": len(ns)}
        if p.get("name"):
            row["name"] = p["name"]
        if ns:
            keys = [midi(n["key"]) for n in ns]
            lo, hi = min(keys), max(keys)
            row.update({
                "span_bars": bars(p["len_from_notes"], ppq),
                "inst": dict(Counter(n["inst"] for n in ns)),
                "keys": [next(n["key"] for n in ns if midi(n["key"]) == lo), next(n["key"] for n in ns if midi(n["key"]) == hi)],
                "vel": [min(n["vel"] for n in ns), max(n["vel"] for n in ns)],
                "len_ticks": [min(n["len"] for n in ns), max(n["len"] for n in ns)],
                "timing_pct": timing(ns),
                "pitch_classes": dict(Counter(n["key"].rstrip("-0123456789") for n in ns).most_common(7)),
            })
        out["patterns"].append(row)
    for a in doc["arrangements"]:
        tracks = defaultdict(list)
        end = 0
        for c in sorted(a["clips"], key=lambda c: (c["track"], tick(c["at"]))):
            src = c.get("pattern") or c.get("audio") or c.get("automation") or c.get("channel")
            s = tick(c["at"], ppq)
            e = s + c["len"]
            end = max(end, e)
            tracks[c["track"]].append(f"{src}@{bars(s, ppq) + 1:g}-{bars(e, ppq) + 1:g}")
        out["arrangements"].append({"name": a["name"], "length_bars": bars(end, ppq), "clips": len(a["clips"]),
                                    "tracks": {t: (v if len(v) <= 12 else v[:12] + [f"... {len(v) - 12} more"]) for t, v in sorted(tracks.items())}})
    for fx in doc["mixer"]["effects"]:
        out["mixer_effects"][fx["track"]].append(fx["plugin"])
    out["mixer_effects"] = dict(out["mixer_effects"])
    return out


def read(path: str, view: str = "summary", patterns: list[str] | None = None, arrangements: list[str] | None = None,
         unused: bool = False) -> dict:
    doc = export(path)
    if view == "summary":
        return summarize(doc)
    if patterns:
        doc["patterns"] = [p for p in doc["patterns"] if p["id"] in patterns]
    if arrangements:
        doc["arrangements"] = [a for a in doc["arrangements"] if a["name"] in arrangements]
    if view == "compact":
        return to_compact(doc, unused=unused or bool(patterns))
    return doc


PARKED = 1 << 31
NOTE_COLS = ["bar", "beat", "tick", "len", "key", "vel", "inst"]
CLIP_COLS = ["track", "bar", "beat", "tick", "len", "src", "trim?"]


def to_compact(doc: dict, unused: bool = False) -> dict:
    inst = [c["id"] for c in doc["instruments"]]
    ii = {k: i for i, k in enumerate(inst)}
    si = {c["id"]: i for i, c in enumerate(doc["samples"])}
    ai = {c["id"]: i for i, c in enumerate(doc["automation"])}
    placed = {c.get("pattern") for a in doc["arrangements"] for c in a["clips"]}
    keep = lambda c: {k: v for k, v in c.items() if k in ("id", "name", "plugin", "mixer", "path", "target", "state", "kind", "ch")}
    out = {"format": "compact", "project": {k: doc["project"][k] for k in ("bpm", "ppq", "source", "title", "author", "genre", "comment") if k in doc["project"]},
           "note_cols": NOTE_COLS, "clip_cols": CLIP_COLS,
           "instruments": [keep(c) for c in doc["instruments"]],
           "samples": [keep(c) for c in doc["samples"]],
           "automation": [dict(keep(c), points=[[round(p["beat"], 6), round(p["value"], 6)] + ([p["tension"]] if p.get("tension") else [])
                                                  for p in c.get("points") or []]) for c in doc["automation"]],
           "patterns": [], "arrangements": [], "mixer_effects": doc.get("mixer", {}).get("effects", [])}
    lv = {k: doc.get("mixer", {}).get(k) for k in ("volume", "main_volume", "routes")}
    if lv["volume"] or lv["main_volume"] is not None or lv["routes"]:
        out["mixer"] = {k: v for k, v in lv.items() if v not in (None, [], {})}
    skipped = []
    for p in doc["patterns"]:
        if not unused and p["id"] not in placed:
            skipped.append(f"{p['id']}({len(p['notes'])})")
            continue
        row = {"id": p["id"], "notes": [[*n["at"], n["len"], n["key"], n["vel"], ii.get(n["inst"], n["inst"])] for n in p["notes"]]}
        if p.get("name"):
            row["name"] = p["name"]
        out["patterns"].append(row)
    if skipped:
        out["unplaced_patterns_omitted"] = skipped
    for a in doc["arrangements"]:
        rows, parked = [], 0
        for c in a["clips"]:
            t = tick(c["at"])
            if t >= PARKED:
                parked += 1
                continue
            src = c.get("pattern") or (f"s{si[c['audio']]}" if "audio" in c else f"a{ai[c['automation']]}" if "automation" in c else c.get("channel"))
            r = [c["track"], *c["at"], c["len"], src]
            if "trim" in c:
                r.append([round(x, 4) for x in c["trim"]])
            rows.append(r)
        entry = {"name": a["name"], "clips": rows}
        if parked:
            entry["parked_clips_omitted"] = parked
        out["arrangements"].append(entry)
    return out


def from_compact(c: dict) -> dict:
    inst = c["instruments"]
    doc = {k: v for k, v in c.items() if k not in ("format", "note_cols", "clip_cols", "patterns", "arrangements", "automation", "mixer_effects")}
    doc["automation"] = [dict({k: v for k, v in a.items() if k != "points"},
                              points=[{"beat": p[0], "value": p[1], **({"tension": p[2]} if len(p) > 2 else {})} for p in a.get("points", [])])
                         for a in c.get("automation", [])]
    doc["patterns"] = [{"id": p["id"], "name": p.get("name"),
                        "notes": [{"at": r[0:3], "len": r[3], "key": r[4], "vel": r[5], "inst": inst[r[6]]["id"] if isinstance(r[6], int) else r[6]}
                                  for r in p["notes"]]} for p in c.get("patterns", [])]
    samples, autos = c.get("samples", []), c.get("automation", [])
    doc["arrangements"] = []
    for a in c.get("arrangements", []):
        clips = []
        for r in a["clips"]:
            src = r[5]
            clip = {"track": r[0], "at": r[1:4], "len": r[4]}
            if isinstance(src, str) and src[:1] == "s" and src[1:].isdigit():
                clip["audio"] = samples[int(src[1:])]["id"]
            elif isinstance(src, str) and src[:1] == "a" and src[1:].isdigit():
                clip["automation"] = autos[int(src[1:])]["id"]
            else:
                clip["pattern"] = src
            if len(r) > 6 and r[6] is not None:
                clip["trim"] = r[6]
            clips.append(clip)
        doc["arrangements"].append({"name": a["name"], "clips": clips})
    return doc


if __name__ == "__main__":
    print(json.dumps(read(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "summary"), indent=1, ensure_ascii=False))
