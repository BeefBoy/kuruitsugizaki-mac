import json
import re
import struct
import sys
from pathlib import Path

import flp
import automation as auto
import levels
import library
import mixerfx
import presets
from project import KINDS, TEMPLATES, item_templates, text, wrapper

PLUGIN_TEMPLATES = {"serum2": "Serum2", "vital": "Vital", "sylenth1": "Sylenth1", "diva": "Diva(x64)", "flex": "FLEX"}
PITCH = {n: i for i, n in enumerate("C C# D D# E F F# G G# A A# B".split())}
FLAT = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#", "Cb": "B", "Fb": "E"}
PATTERN_IDS = {65, 224}
ARR_IDS = {99, 241, 36, 233, 238, 43}
NOTE_BASE = {"flags": 16384, "group": 0, "fine": 120, "u1": 0, "release": 64, "midich": 0, "pan": 64, "velocity": 100, "modx": 128, "mody": 128}


def midi(key) -> int:
    if isinstance(key, int):
        return key
    m = re.fullmatch(r"([A-Ga-g])([#b]?)(-?\d+)", key.strip())
    if not m:
        raise ValueError(f"bad note name {key!r}")
    name = m.group(1).upper() + m.group(2)
    name = FLAT.get(name, name)
    shift = -12 if m.group(1).upper() + m.group(2) == "Cb" else 0
    return PITCH[name] + (int(m.group(3)) + 1) * 12 + shift


def ticks(at, ppq: int, beats: int = 4) -> int:
    if isinstance(at, int):
        return at
    bar, beat, tick = (list(at) + [1, 0])[:3] if len(at) < 3 else at
    return ((bar - 1) * beats + (beat - 1)) * ppq + tick


def layout(p: flp.Project) -> dict:
    ev = p.events
    ids = [e.id for e in ev]
    c0 = ids.index(64)
    p0 = next((i for i in range(c0) if ids[i] == 65), c0)
    p1 = next((i for i in range(p0, c0) if ids[i] in (226, 227)), c0)
    a0 = ids.index(99)
    chans, i = [], c0
    while i < a0:
        j = i + 1
        while j < a0 and ids[j] != 64:
            j += 1
        chans.append(ev[i:j])
        i = j
    arrs, i = [], a0
    while i < len(ev) and ids[i] == 99:
        j = i + 1
        while j < len(ev) and ids[j] in ARR_IDS and ids[j] != 99:
            j += 1
        arrs.append(ev[i:j])
        i = j
    return {"prefix": ev[:p0], "patterns": ev[p0:p1], "middle": ev[p1:c0], "channels": chans, "arrangements": arrs, "tail": ev[i:]}


_cache: dict[str, tuple] = {}


def load(path: str):
    if path not in _cache:
        p = flp.parse(Path(path).read_bytes())
        _cache[path] = (p, layout(p))
    return _cache[path]


def block_of(path: str, channel: int) -> list[flp.Event]:
    _, lay = load(path)
    for b in lay["channels"]:
        if int.from_bytes(b[0].data, "little") == channel:
            return b
    raise KeyError(f"no channel {channel} in {path}")


def template_block(kind: str, plugin: str | None = None) -> list[flp.Event]:
    _, lay = load(TEMPLATES)
    for b in lay["channels"]:
        k = next((KINDS.get(int.from_bytes(e.data, "little")) for e in b if e.id == 21), None)
        if k != kind:
            continue
        if kind != "plugin":
            return b
        internal = next((text(e) for e in b if e.id == 201 and len(e.data) > 2), "")
        st = next((e.data for e in b if e.id == 213), b"")
        name = wrapper(st).get(54, b"").decode("latin-1") if internal == "Fruity Wrapper" else internal
        if name == PLUGIN_TEMPLATES.get(plugin, plugin):
            return b
    hint = "; any other installed plugin is found by name in FL's plugin database or the library, listed by the plugins tool" if kind == "plugin" else ""
    raise KeyError(f"no {kind} template {plugin!r} in {TEMPLATES}; it holds {template_plugins()}{hint}")


def template_plugins() -> list[str]:
    _, lay = load(TEMPLATES)
    have = []
    for b in lay["channels"]:
        if next((KINDS.get(int.from_bytes(e.data, "little")) for e in b if e.id == 21), None) != "plugin":
            continue
        internal = next((text(e) for e in b if e.id == 201 and len(e.data) > 2), "")
        st = next((e.data for e in b if e.id == 213), b"")
        name = wrapper(st).get(54, b"").decode("latin-1") if internal == "Fruity Wrapper" else internal
        have.append(next((k for k, v in PLUGIN_TEMPLATES.items() if v == name), name))
    return have


def utf16(s: str) -> bytes:
    return s.encode("utf-16-le") + b"\0\0"


def library_entry(c: dict) -> dict | None:
    name = str(c.get("plugin") or "")
    fmt = c.get("format")
    if not name or (name.lower().replace(" ", "") in PLUGIN_TEMPLATES and not fmt):
        return None
    return library.find(name, "instrument", fmt) if library.has(name, "instrument", fmt) else None


def channel_block(c: dict, index: int) -> list[flp.Event]:
    st = c.get("state") or {}
    lib = library_entry(c) if c["kind"] == "plugin" else None
    if "from" in st:
        src = block_of(st["from"], st["channel"])
    elif lib:
        src = library.block(lib)
        if c.get("preset"):
            src = library.with_preset(src, lib, c["preset"])
    elif c["kind"] == "plugin":
        src = template_block("plugin", (st.get("template") or c.get("template") or c.get("plugin", "")).lower().replace(" ", ""))
    elif c["kind"] == "automation":
        src = block_of(*auto.TEMPLATE) if auto.TEMPLATE else template_block("automation")
    else:
        src = template_block(c["kind"])
    out = [flp.Event(e.id, e.data) for e in src]
    out[0].data = index.to_bytes(2, "little")
    on = next((e for e in out[:12] if e.id == 0 and len(e.data) == 1), None)
    if on is not None and ("from" in st or "muted" in c):
        # a channel copied by pointer arrives playing even when its source was muted; muted: true keeps it off
        on.data = b"\0" if c.get("muted") else b"\1"
    if c.get("path") and not any(e.id == 196 for e in out):
        at20 = max((i for i, e in enumerate(out) if e.id == 20), default=len(out) - 1)
        out.insert(at20 + 1, flp.Event(196, utf16(c["path"])))
    for e in out:
        if e.id == 203 and (c.get("name") or c.get("id")):
            # without a name a channel kept its template's: every unnamed automation clip read "Tempo" in FL
            e.data = utf16(c.get("name") or c["id"])
        if e.id == 196 and c.get("path"):
            e.data = utf16(c["path"])
        if e.id == 104 and "mixer" in c:
            e.data = int(c["mixer"]).to_bytes(len(e.data), "little")
        if e.id == 213 and c.get("preset") and not (lib and "from" not in st):
            e.data = library.preset_state(lib, c["preset"]) if lib else presets.apply(str(c.get("plugin", "")).lower(), e.data, c["preset"])
        if e.id == 219 and c.get("_new_clip") and isinstance(c.get("target"), dict) and len(e.data) >= 8:
            e.data = struct.pack("<II", *((1250, 4250) if c["target"].get("global") == "tempo" else (0, 12800))) + e.data[8:]
        if e.id == 234 and isinstance(c.get("points"), list):
            e.data = auto.encode_points(c["points"], {k: c[k] for k in ("raw_head", "raw_tail") if k in c})
    return out


def build(doc: dict) -> tuple[bytes, list[str]]:
    song_mode = doc.get("project", {}).get("song_mode")
    if doc.get("format") == "compact":
        import view
        doc = view.from_compact(doc)
        doc["automation"] = [dict(a, _new_clip=True) for a in doc.get("automation", [])]
        if song_mode is None:
            song_mode = True
    warn = []
    base = doc.get("base") or doc.get("project", {}).get("base") or TEMPLATES
    bp, lay = load(base)
    ppq = bp.meta["ppq"]
    if doc.get("project", {}).get("ppq", ppq) != ppq:
        raise ValueError(f"ppq {doc['project']['ppq']} differs from base {ppq}; changing PPQ is not supported")
    chans = doc.get("instruments", []) + doc.get("samples", []) + doc.get("automation", [])
    if any("ch" in c for c in chans):
        chans = sorted(chans, key=lambda c: c.get("ch", 1 << 30))
    index = {c["id"]: i for i, c in enumerate(chans)}
    events = [flp.Event(e.id, e.data) for e in lay["prefix"]]
    bpm = doc.get("project", {}).get("bpm")
    if bpm is not None:
        for e in events:
            if e.id == 156:
                e.data = int(round(bpm * 1000)).to_bytes(4, "little")
    for e in events:
        key = flp.META.get(e.id)
        if key and doc.get("project", {}).get(key) is not None:
            e.data = utf16(str(doc["project"][key]))
    if song_mode is not None:
        for e in events:
            if e.id == 9:
                e.data = (1 if song_mode else 0).to_bytes(len(e.data), "little")
    nd = {**NOTE_BASE, **doc.get("note_defaults", {})}
    pat_index = {}
    used = set()
    for pt in doc.get("patterns", []):
        m = re.fullmatch(r"p(\d+)", str(pt["id"]))
        k = pt.get("index") or (int(m.group(1)) if m else None)
        if k is not None:
            pat_index[pt["id"]] = k
            used.add(k)
    nxt = max(used, default=0)
    for pt in doc.get("patterns", []):
        if pt["id"] not in pat_index:
            nxt += 1
            pat_index[pt["id"]] = nxt
    for pt in doc.get("patterns", []):
        k = pat_index[pt["id"]]
        notes = []
        for n in pt.get("notes", []):
            if n["inst"] not in index:
                raise KeyError(f"pattern {pt['id']}: unknown instrument {n['inst']!r}")
            rec = {f: n.get(f, nd[f]) for f in flp.NOTE_FIELDS if f not in ("pos", "length", "key", "rack", "velocity")}
            rec.update(pos=ticks(n["at"], ppq), length=int(n["len"]), key=midi(n["key"]), rack=index[n["inst"]], velocity=int(n.get("vel", nd["velocity"])))
            notes.append(rec)
        raw = pt.get("unmapped", [])
        events.append(flp.Event(65, k.to_bytes(2, "little")))
        events += [flp.Event(x["id"], bytes.fromhex(x["hex"])) for x in raw if x["where"] == "before"]
        notes.sort(key=lambda r: r["pos"])
        if notes or pt.get("note_event", True):
            events.append(flp.Event(224, flp.notes_encode(notes)))
        events += [flp.Event(x["id"], bytes.fromhex(x["hex"])) for x in raw if x["where"] == "after"]
        if pt.get("name"):
            warn.append(f"pattern {pt['id']}: names are not written yet (event 193 is unconfirmed)")
    events += [flp.Event(e.id, e.data) for e in lay["middle"] if e.id != 227]
    for i, c in enumerate(chans):
        if c["kind"] != "automation":
            continue
        if "target_id" in c:
            tid = int(str(c["target_id"]), 16) if isinstance(c["target_id"], str) else int(c["target_id"])
            if auto.PLUG20 <= tid < 0x30000000:
                tid += auto.PLUG - auto.PLUG20
        elif "target" in c:
            tid = auto.encode_target(c["target"], index)
        else:
            raise ValueError(f"automation {c['id']!r} needs a target")
        events.append(flp.Event(227, auto.link(i, tid, c.get("raw_link"))))
    for i, c in enumerate(chans):
        events += channel_block(c, i)
    tpl = item_templates()
    base_arrs = lay["arrangements"]
    for ai, arr in enumerate(doc.get("arrangements") or [{"name": "Arrangement", "clips": []}]):
        src = base_arrs[ai] if ai < len(base_arrs) else base_arrs[0]
        recs = []
        clips = arr.get("clips", [])
        if not any("item" in c for c in clips):
            clips = sorted(clips, key=lambda c: (ticks(c["at"], ppq), int(c["track"])))
        for ci, clip in enumerate(clips, 1):
            if clip.get("automation") and "trim" not in clip and "item" not in clip:
                clip = dict(clip, trim=[0.0, int(clip["len"]) / ppq])
            if "pattern" in clip:
                pid = clip["pattern"]
                m = re.fullmatch(r"p(\d+)", str(pid))
                if pid not in pat_index and not m:
                    raise KeyError(f"clip refers to unknown pattern {pid!r}")
                ref, r = 0x5000 + pat_index.get(pid, int(m.group(1)) if m else 0), bytearray(tpl["pattern"])
            else:
                cid = clip.get("audio") or clip.get("automation") or clip.get("channel")
                ref, r = index[cid], bytearray(tpl["channel"])
            struct.pack_into("<IHHII", r, 0, ticks(clip["at"], ppq), 0x5000, ref, int(clip["len"]), 500 - int(clip["track"]))
            r[19] = (r[19] | 0x80) if clip.get("flag_b19") else (r[19] & 0x7F)
            if "pattern" in clip:
                # start and end inside the pattern, in ticks; with the template's -1/-1 FL plays the whole pattern
                # whatever the clip's length, so a clip shorter than its pattern would run on past its end
                lo, hi = clip.get("trim") or (0, int(clip["len"]))
                struct.pack_into("<ii", r, 24, int(lo), int(hi))
            elif "trim" in clip:
                struct.pack_into("<ff", r, 24, *clip["trim"])
            for key, off in (("raw16", 16), ("raw24", 24), ("raw36", 36)):
                if key in clip:
                    b = bytes.fromhex(clip[key])
                    r[off:off + len(b)] = b
            struct.pack_into("<I", r, 32, int(clip.get("item", ci)))
            recs.append(bytes(r))
        for e in src:
            d = e.data
            if e.id == 99:
                d = ai.to_bytes(len(e.data), "little")
            elif e.id == 241:
                d = utf16(arr.get("name", f"Arrangement {ai + 1}"))
            elif e.id == 233:
                d = b"".join(recs)
            events.append(flp.Event(e.id, d))
        if not any(e.id == 233 for e in src):
            warn.append(f"base arrangement {ai} has no 233 event; clips not written")
    mix = (doc.get("mixer") or {}).get("from")
    tail = load(mix)[1]["tail"] if mix else lay["tail"]
    mx = doc.get("mixer") or {}
    tail = [flp.Event(e.id, e.data) for e in tail]
    if mx.get("effects"):
        tail = mixerfx.apply(tail, mx["effects"], warn)
    for r in mx.get("routes") or []:
        tail = mixerfx.set_route(tail, int(r["from"]), int(r["to"]), r.get("on", True))
    events += tail
    if mx.get("volume") or mx.get("main_volume") is not None or mx.get("routes"):
        for e in events:
            if e.id == 225:
                e.data = levels.write(e.data, mx.get("volume"), mx.get("main_volume"), warn)
                for r in mx.get("routes") or []:
                    if int(r["to"]) != 0 and r.get("on", True) and r.get("level") is not None:
                        e.data = levels.set_send(e.data, int(r["from"]), int(r["to"]), r["level"])
    header = bytearray(bp.header)
    struct.pack_into("<H", header, 2, len(chans))
    return flp.serialize(flp.Project(bytes(header), events, bp.tail)), warn


if __name__ == "__main__":
    doc = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    doc = doc.get("args", doc)
    raw, warn = build(doc)
    Path(sys.argv[2]).write_bytes(raw)
    print(f"wrote {sys.argv[2]}: {len(raw)} bytes", *warn, sep="\n  ")
