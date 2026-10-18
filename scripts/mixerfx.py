import struct
from pathlib import Path

import flp

TRACK = 236
SLOT = 98
ROUTE = 235
SLOT_RECORD = 212
STATE = 213


def _tracks(tail: list) -> list[tuple[int, int]]:
    starts = [i for i, e in enumerate(tail) if e.id == TRACK]
    return [(s, starts[k + 1] if k + 1 < len(starts) else len(tail)) for k, s in enumerate(starts)]


def _marker(tail: list, track: int, slot: int) -> tuple[int, int]:
    spans = _tracks(tail)
    if track >= len(spans):
        raise IndexError(f"mixer track {track}: the mixer section has {len(spans)} tracks")
    a, b = spans[track]
    prev = a
    for i in range(a + 1, b):
        e = tail[i]
        if e.id == SLOT:
            if int.from_bytes(e.data, "little") == slot:
                return prev, i
            prev = i
    raise IndexError(f"mixer track {track} has no slot {slot} marker")


MAX_INSERT = 125  # FL 2025's mixer: master, inserts 1-125, Current


def inserts(tail: list) -> int:
    """How many inserts the mixer has: its track groups less master and the Current track FL keeps last."""
    return max(0, len(_tracks(tail)) - 2)


def add_inserts(tail: list, model: list, upto: int) -> list:
    """Inserts up to upto, each a copy of the model mixer's last plain insert group, placed before the Current group as
    FL places a track added in its mixer."""
    have = inserts(tail)
    if upto <= have:
        return tail
    spans = _tracks(model)
    a, b = spans[len(spans) - 2]
    group = model[a:b]
    cur = _tracks(tail)[-1][0]
    add = [flp.Event(e.id, e.data) for _ in range(upto - have) for e in group]
    return tail[:cur] + add + tail[cur:]


def block(tail: list, track: int, slot: int) -> list:
    prev, mark = _marker(tail, track, slot)
    return tail[prev + 1:mark]


def effects(tail: list) -> list[dict]:
    out = []
    for t, (a, b) in enumerate(_tracks(tail)):
        for i in range(a, b):
            e = tail[i]
            if e.id == SLOT_RECORD and len(e.data) >= 8:
                out.append({"track": t, "slot": struct.unpack_from("<II", e.data)[1]})
    return out


_src_cache: dict[str, list] = {}


def source_tail(path: str) -> list:
    if path not in _src_cache:
        import writer
        p = flp.parse(Path(path).read_bytes())
        _src_cache[path] = writer.layout(p)["tail"]
    return _src_cache[path]


def place(tail: list, track: int, slot: int, blk: list) -> list:
    prev, mark = _marker(tail, track, slot)
    new = []
    for e in blk:
        d = bytearray(e.data)
        if e.id == SLOT_RECORD and len(d) >= 8:
            struct.pack_into("<II", d, 0, track, slot)
        new.append(flp.Event(e.id, bytes(d)))
    return tail[:prev + 1] + new + tail[mark:]


def set_route(tail: list, src: int, dst: int, on: bool = True) -> list:
    a, b = _tracks(tail)[src]
    for i in range(a, b):
        if tail[i].id == ROUTE:
            d = bytearray(tail[i].data)
            if len(d) <= dst:
                d.extend(b"\0" * (dst + 1 - len(d)))
            d[dst] = 1 if on else 0
            while not on and len(d) > 1 and d[-1] == 0:
                d.pop()
            return tail[:i] + [flp.Event(ROUTE, bytes(d))] + tail[i + 1:]
    raise KeyError(f"mixer track {src} has no routing event")


def routes(tail: list) -> list[tuple[int, int]]:
    out = []
    for t, (a, b) in enumerate(_tracks(tail)):
        for i in range(a, b):
            if tail[i].id == ROUTE:
                out += [(t, k) for k, v in enumerate(tail[i].data) if v]
    return out


def apply(tail: list, specs: list, warn: list) -> list:
    import library
    for fx in specs or []:
        src = fx.get("from")
        t, s = int(fx["track"]), int(fx["slot"])
        lib = None
        fmt = fx.get("format")
        if not src and fx.get("plugin"):
            here = block(tail, t, s)
            if any(e.id == SLOT_RECORD for e in here) and library.identity(here)["name"].lower() == str(fx["plugin"]).lower() and not fx.get("preset"):
                continue
            if not library.has(fx["plugin"], "effect", fmt):
                warn.append(f"effect {fx['plugin']!r} for track {t} slot {s}: not installed (FL's plugin database) nor in the library, and no from given; skipped")
                continue
            lib = library.find(fx["plugin"], "effect", fmt)
        if lib:
            blk = library.block(lib)
        elif src:
            s_tail = source_tail(src["file"])
            blk = block(s_tail, int(src.get("track", t)), int(src.get("slot", s)))
            if not any(e.id == SLOT_RECORD for e in blk):
                warn.append(f"effect for track {t} slot {s}: {src['file']} has no plugin at track {src.get('track')} slot {src.get('slot')}")
                continue
        else:
            continue
        if fx.get("preset"):
            entry = lib or library.find(library.identity(blk)["name"], "effect")
            blk = library.with_preset(blk, entry, fx["preset"])
        tail = place(tail, t, s, blk)
    return tail
