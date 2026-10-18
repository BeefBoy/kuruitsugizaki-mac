import struct
import sys
from collections import Counter
from dataclasses import dataclass, field

import pick


@dataclass
class Event:
    id: int
    data: bytes
    offset: int = -1


@dataclass
class Project:
    header: bytes
    events: list[Event]
    tail: bytes = b""
    meta: dict = field(default_factory=dict)


def fixed_size(eid: int) -> int | None:
    return 1 if eid < 64 else 2 if eid < 128 else 4 if eid < 192 else None


def varint_read(b: bytes, i: int) -> tuple[int, int]:
    n = shift = 0
    while True:
        c = b[i]
        i += 1
        n |= (c & 0x7F) << shift
        if c < 0x80:
            return n, i
        shift += 7


def varint_write(n: int) -> bytes:
    out = bytearray()
    while True:
        c, n = n & 0x7F, n >> 7
        out.append(c | 0x80 if n else c)
        if not n:
            return bytes(out)


NOTE = struct.Struct("<IHHIHHBBBBBBBB")
META = {194: "title", 195: "comment", 206: "genre", 207: "author"}
NOTE_FIELDS = ("pos", "flags", "rack", "length", "key", "group", "fine", "u1", "release", "midich", "pan", "velocity", "modx", "mody")


def notes_decode(data: bytes) -> list[dict]:
    return [dict(zip(NOTE_FIELDS, NOTE.unpack_from(data, i))) for i in range(0, len(data), NOTE.size)]


def notes_encode(notes: list[dict]) -> bytes:
    return b"".join(NOTE.pack(*(n[f] for f in NOTE_FIELDS)) for n in notes)


def parse(buf: bytes) -> Project:
    if buf[:4] != b"FLhd":
        raise ValueError("no FLhd magic")
    hlen, = struct.unpack_from("<I", buf, 4)
    header = buf[8:8 + hlen]
    i = 8 + hlen
    if buf[i:i + 4] != b"FLdt":
        raise ValueError(f"no FLdt at {i}")
    dlen, = struct.unpack_from("<I", buf, i + 4)
    i += 8
    end = i + dlen
    events = []
    while i < end:
        start, eid = i, buf[i]
        i += 1
        n = fixed_size(eid)
        if n is None:
            n, i = varint_read(buf, i)
        events.append(Event(eid, buf[i:i + n], start))
        i += n
    if i != end:
        raise ValueError(f"event stream overran data chunk: {i} vs {end}")
    fmt, channels, ppq = struct.unpack_from("<hHH", header) if hlen >= 6 else (None, None, None)
    return Project(header, events, buf[end:], {"format": fmt, "channels": channels, "ppq": ppq})


def serialize(p: Project) -> bytes:
    body = bytearray()
    for e in p.events:
        body.append(e.id)
        n = fixed_size(e.id)
        if n is None:
            body += varint_write(len(e.data))
        elif len(e.data) != n:
            raise ValueError(f"event {e.id} needs {n} bytes, has {len(e.data)}")
        body += e.data
    return (b"FLhd" + struct.pack("<I", len(p.header)) + p.header
            + b"FLdt" + struct.pack("<I", len(body)) + bytes(body) + p.tail)


def render(e: Event) -> str:
    d = e.data
    if len(d) in (1, 2, 4) and e.id < 192:
        v = int.from_bytes(d, "little")
        s = f"{v} (0x{v:x})"
        if len(d) == 4:
            s += f" f32={struct.unpack('<f', d)[0]:.6g}"
        return s
    if len(d) >= 4 and len(d) % 2 == 0 and d.endswith(b"\0\0"):
        try:
            t = d[:-2].decode("utf-16-le")
            if t.isprintable():
                return f"utf16 {t!r}"
        except UnicodeDecodeError:
            pass
    if d and d.endswith(b"\0") and all(32 <= c < 127 for c in d[:-1]):
        return f"ascii {d[:-1].decode()!r}"
    return f"[{len(d)}] {d[:48].hex(' ')}{' ...' if len(d) > 48 else ''}"


def diff(a: Project, b: Project) -> list[str]:
    import difflib
    ka = [(e.id, e.data) for e in a.events]
    kb = [(e.id, e.data) for e in b.events]
    out = []
    if a.header != b.header:
        out.append(f"header {a.header.hex(' ')} -> {b.header.hex(' ')}")
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ka, kb, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace" and i2 - i1 == j2 - j1:
            for i, j in zip(range(i1, i2), range(j1, j2)):
                ea, eb = a.events[i], b.events[j]
                if ea.id != eb.id or len(ea.data) != len(eb.data) or len(ea.data) <= 4:
                    out.append(f"~ #{i}->{j} id {ea.id}->{eb.id}  {render(ea)}  ->  {render(eb)}")
                    continue
                spans, k = [], 0
                while k < len(ea.data):
                    if ea.data[k] != eb.data[k]:
                        s = k
                        while k < len(ea.data) and ea.data[k] != eb.data[k]:
                            k += 1
                        spans.append((s, k))
                    k += 1
                out.append(f"~ #{i}->{j} id {ea.id} len {len(ea.data)}: {len(spans)} changed spans")
                for s, e in pick.even(spans, 12):
                    lo = max(0, s - 4)
                    out.append(f"    @{s}..{e}  {ea.data[lo:e + 4].hex(' ')}  ->  {eb.data[lo:e + 4].hex(' ')}")
            continue
        for i in range(i1, i2):
            out.append(f"- #{i} id {a.events[i].id}  {render(a.events[i])}")
        for j in range(j1, j2):
            out.append(f"+ #{j} id {b.events[j].id}  {render(b.events[j])}")
    return out


def main(argv: list[str]) -> int:
    cmd, paths = argv[0], argv[1:]
    if cmd == "diff":
        pa, pb = (parse(open(x, "rb").read()) for x in paths[:2])
        lines = diff(pa, pb)
        print("\n".join(lines) or "identical")
        return 0
    bad = 0
    for path in paths:
        raw = open(path, "rb").read()
        p = parse(raw)
        if cmd == "check":
            same = serialize(p) == raw
            bad += not same
            print(f"{'OK  ' if same else 'DIFF'} {len(p.events):6} events {len(raw):9} bytes  {path}")
        elif cmd == "stats":
            c = Counter(e.id for e in p.events)
            print(path, p.meta, len(p.events), "events")
            for eid, k in sorted(c.items()):
                sizes = sorted({len(e.data) for e in p.events if e.id == eid})
                print(f"  {eid:3} x{k:<4} sizes {pick.even(sizes, 6)}{f' (6 of {len(sizes)})' if len(sizes) > 6 else ''}")
        elif cmd == "dump":
            print(path, p.meta)
            for n, e in enumerate(p.events):
                print(f"{n:5} @{e.offset:<7} {e.id:3}  {render(e)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
