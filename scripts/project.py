import json
import re
import struct
import sys
from pathlib import Path

import config
import flp
import automation as auto
import levels
import mixerfx

KINDS = {0: "sampler", 2: "plugin", 4: "audio", 5: "automation"}
PITCH = "C C# D D# E F F# G G# A A# B".split()
NOTE_FIELDS = ("pan", "fine", "release", "modx", "mody", "flags", "group", "u1", "midich")
PATTERN_BASE = 0x5000
ITEM = 80
TEMPLATES = config.get("template")
_item_tpl = {}


def item_templates() -> dict:
    if not _item_tpl:
        p = flp.parse(Path(TEMPLATES).read_bytes())
        for e in p.events:
            if e.id == 233:
                for i in range(0, len(e.data), ITEM):
                    r = e.data[i:i + ITEM]
                    kind = "pattern" if struct.unpack_from("<H", r, 6)[0] >= PATTERN_BASE else "channel"
                    _item_tpl.setdefault(kind, r)
    return _item_tpl


def u(e: flp.Event) -> int:
    return int.from_bytes(e.data, "little")


def text(e: flp.Event) -> str:
    return e.data[:-2].decode("utf-16-le", "replace") if e.data.endswith(b"\0\0") else e.data.decode("utf-16-le", "replace")


def slug(name: str, taken: set) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "ch"
    base, n = s, 2
    while s in taken:
        s, n = f"{base}_{n}", n + 1
    taken.add(s)
    return s


def key_name(k: int) -> str:
    return f"{PITCH[k % 12]}{k // 12 - 1}"


def at(t: int, ppq: int, beats: int = 4) -> list[int]:
    bar, r = divmod(t, ppq * beats)
    beat, tick = divmod(r, ppq)
    return [bar + 1, beat + 1, tick]


def item_size(version: str | None) -> int:
    """Bytes per playlist item (event 233): FL 20 writes the first 32 bytes of the FL 25 layout."""
    major = int(version.split(".")[0]) if version else 25
    return 32 if major < 21 else ITEM


def wrapper(data: bytes) -> dict:
    out, i = {}, 4
    while i + 12 <= len(data):
        rid, n = struct.unpack_from("<IQ", data, i)
        out[rid] = data[i + 12:i + 12 + n]
        i += 12 + n
    return out


def _routes(tail: list, rec225: bytes) -> list[dict]:
    lv = {(s, d): v for s, d, v in levels.sends(rec225)}
    return [{"from": s, "to": d, "level": lv.get((s, d))} for s, d in mixerfx.routes(tail) if d != 0]


def export(path: str) -> dict:
    raw = Path(path).read_bytes()
    p = flp.parse(raw)
    ev, ppq = p.events, p.meta["ppq"]
    first_arr = next((n for n, e in enumerate(ev) if e.id == 241), len(ev))
    starts = [n for n, e in enumerate(ev[:first_arr]) if e.id == 64]
    taken, channels = set(), []
    for k, n in enumerate(starts):
        blk = ev[n:starts[k + 1] if k + 1 < len(starts) else first_arr]
        kind = next((KINDS.get(u(e), u(e)) for e in blk if e.id == 21), None)
        name = next((text(e) for e in blk if e.id == 203), f"channel {u(ev[n])}")
        ch = {"id": slug(name, taken), "name": name, "kind": kind, "ch": u(ev[n])}
        internal = next((text(e) for e in blk if e.id == 201 and len(e.data) > 2), None)
        state = next((e.data for e in blk if e.id == 213), None)
        if internal == "Fruity Wrapper" and state:
            w = wrapper(state)
            ch["plugin"] = w.get(54, b"").decode("latin-1")
            ch["vendor"] = w.get(56, b"").decode("latin-1")
            ch["format"] = "vst3" if w.get(55, b"").lower().endswith(b".vst3") else "vst"
        elif internal:
            ch["plugin"] = internal
            ch["vendor"] = "Image-Line"
            ch["format"] = "native"
        if state and kind == "plugin":
            hints = [s.decode() for s in re.findall(rb"[ -~]{6,}", state[:4096])][:3]
            ch["state"] = {"from": path, "channel": u(ev[n]), "bytes": len(state)}
            if internal != "Fruity Wrapper" and hints:
                ch["state"]["hints"] = hints
        elif kind in ("audio", "automation", "sampler"):
            ch["state"] = {"from": path, "channel": u(ev[n])}
        sample = next((text(e) for e in blk if e.id == 196), None)
        if sample:
            ch["path"] = sample
        route = next((u(e) for e in blk if e.id == 104), next((u(e) for e in blk if e.id == 22), None))
        if route is not None:
            ch["mixer"] = route
        channels.append(ch)
    by_index = {c["ch"]: c for c in channels}
    ids_by_index = {k: v["id"] for k, v in by_index.items()}
    links = {}
    for e in ev[:starts[0] if starts else first_arr]:
        if e.id == 227 and len(e.data) >= 12:
            links[struct.unpack_from("<H", e.data, 2)[0]] = e.data
    for n, c in zip(starts, channels):
        if c["kind"] != "automation":
            continue
        blk = ev[n:]
        pts = next((e.data for e in blk[:80] if e.id == 234), None)
        if pts is not None:
            c["points"], extra = auto.decode_points(pts)
            c.update(extra)
        r = links.get(c["ch"])
        if r is not None:
            tid = struct.unpack_from("<I", r, 8)[0]
            c["target"] = auto.decode_target(tid, ids_by_index)
            c["target_id"] = hex(tid)
            if auto.link(c["ch"], tid) != r:
                c["raw_link"] = r.hex()
    allnotes = [n for e in ev[:first_arr] if e.id == 224 for n in flp.notes_decode(e.data)]
    defaults = {f: max(set(n[f] for n in allnotes), key=[n[f] for n in allnotes].count) for f in NOTE_FIELDS} if allnotes else {}
    patterns, order, cur, seen224 = {}, [], None, False
    region_end = next((i for i, e in enumerate(ev) if e.id in (226, 227, 64)), first_arr)
    for e in ev[:region_end]:
        if e.id == 65:
            cur = u(e)
            seen224 = False
            if cur not in patterns:
                patterns[cur] = {"id": f"p{cur}", "name": None, "notes": [], "_had224": False}
                order.append(cur)
        elif cur is None:
            continue
        elif e.id == 193:
            patterns[cur]["name"] = text(e)
        elif e.id != 224:
            patterns[cur].setdefault("unmapped", []).append({"id": e.id, "hex": e.data.hex(), "where": "after" if seen224 else "before"})
        elif e.id == 224:
            seen224 = True
            patterns[cur]["_had224"] = True
            for n in flp.notes_decode(e.data):
                note = {"at": at(n["pos"], ppq), "len": n["length"], "key": key_name(n["key"]),
                        "vel": n["velocity"], "inst": by_index.get(n["rack"], {}).get("id", f"rack{n['rack']}")}
                for f, d in defaults.items():
                    if n[f] != d:
                        note[f] = n[f]
                patterns[cur]["notes"].append(note)
    for pt in patterns.values():
        if not pt.pop("_had224"):
            pt["note_event"] = False
        end = max((n["at"][0] - 1) * 4 * ppq + (n["at"][1] - 1) * ppq + n["at"][2] + n["len"] for n in pt["notes"]) if pt["notes"] else 0
        pt["len_from_notes"] = end
    version = next((e.data[:-1].decode() for e in ev if e.id == 199), None)
    size = item_size(version)
    arrangements, arr = [], None
    for n, e in enumerate(ev[first_arr:], first_arr):
        if e.id == 241:
            arr = {"name": text(e), "clips": []}
            arrangements.append(arr)
        elif e.id == 233 and arr is not None:
            if len(e.data) % size:
                raise ValueError(f"{path}: FL {version} playlist is {len(e.data)} bytes, not a multiple of {size}-byte items")
            for i in range(0, len(e.data), size):
                r = e.data[i:i + size]
                pos, base, ref, length, track = struct.unpack_from("<IHHII", r)
                clip = {"track": 500 - track, "at": at(pos, ppq), "len": length}
                if size == ITEM:
                    clip["item"] = struct.unpack_from("<I", r, 32)[0]
                if ref >= PATTERN_BASE:
                    clip["pattern"] = f"p{ref - PATTERN_BASE}"
                    tpl = item_templates()["pattern"]
                else:
                    c = by_index.get(ref, {})
                    clip[c.get("kind") or "channel"] = c.get("id", f"rack{ref}")
                    lo, hi = struct.unpack_from("<ff", r, 24)
                    if (lo, hi) != (-1.0, -1.0):
                        clip["trim"] = [lo, hi]
                    tpl = item_templates()["channel"]
                if r[19] & 0x80:
                    clip["_flag_b19"] = True
                t16 = bytearray(tpl[16:24])
                t16[3] = (t16[3] & 0x7F) | (r[19] & 0x80)
                if r[16:24] != t16:
                    clip["raw16"] = r[16:24].hex()
                if size == ITEM and r[36:80] != tpl[36:80]:
                    clip["raw36"] = r[36:80].hex()
                if ref >= PATTERN_BASE and r[24:32] != tpl[24:32]:
                    clip["raw24"] = r[24:32].hex()
                arr["clips"].append(clip)
    flags = [c.pop("_flag_b19", False) for a in arrangements for c in a["clips"]]
    i = 0
    for a in arrangements:
        for c in a["clips"]:
            if flags[i]:
                c["flag_b19"] = True
            i += 1
    mixer = []
    for n, e in enumerate(ev[first_arr:], first_arr):
        if e.id == 212 and len(e.data) >= 8:
            track, slot = struct.unpack_from("<II", e.data)
            nm = next((text(x) for x in ev[n + 1:n + 4] if x.id == 203), None)
            internal = next((text(x) for x in ev[n - 2:n] if x.id == 201 and len(x.data) > 2), None)
            fx = {"track": track, "slot": slot, "plugin": nm or internal}
            if internal == "Fruity Wrapper":
                st = next((x.data for x in ev[n:n + 8] if x.id == 213), b"")
                fx["plugin"] = wrapper(st).get(54, b"").decode("latin-1") or nm
            mixer.append(fx)
    return {
        "project": {"source": path, "bpm": next((u(e) / 1000 for e in ev if e.id == 156), None), "ppq": ppq,
                    "time_sig": "unmapped (4/4 assumed for bar math)", "fl_version": version,
                    **{k: text(e) for e in ev[:starts[0] if starts else first_arr] for i, k in flp.META.items() if e.id == i and text(e)}},
        "instruments": [c for c in channels if c["kind"] in ("sampler", "plugin")],
        "samples": [c for c in channels if c["kind"] == "audio"],
        "automation": [c for c in channels if c["kind"] == "automation"],
        "note_defaults": defaults,
        "patterns": [patterns[k] for k in order],
        "arrangements": arrangements,
        "mixer": {"effects": mixer, **levels.read(next((e.data for e in ev if e.id == 225), b"")),
                  "routes": _routes(ev[first_arr:], next((e.data for e in ev if e.id == 225), b"")), "insert_names": "unmapped"},
    }


if __name__ == "__main__":
    doc = export(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    s = json.dumps(doc, indent=1, ensure_ascii=False)
    if out:
        out.write_text(s, encoding="utf-8")
        print(f"wrote {out}: {len(s)} chars")
    else:
        print(s)
