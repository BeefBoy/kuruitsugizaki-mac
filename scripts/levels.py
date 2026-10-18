import struct

MAIN = 0x40000000
VOL = 0x70001FC0
UNITY = 12800
SCALE = 16000


SEND = 0x70000000 + 0x2000


def track_id(t: int) -> int:
    return VOL + (int(t) << 22)


def send_id(src: int, dst: int) -> int:
    return SEND + (int(src) << 22) + int(dst)


def set_send(data: bytes, src: int, dst: int, level: float) -> bytes:
    recs = [struct.unpack_from("<IIi", data, i) for i in range(0, len(data) - 11, 12)]
    rid, val = send_id(src, dst), int(round(float(level) * SCALE))
    for k, (z, r, _) in enumerate(recs):
        if r == rid:
            recs[k] = (z, r, val)
            break
    else:
        same = [k for k, (_, r, _) in enumerate(recs) if r >> 22 == rid >> 22 and (r & 0xFFFF) < (rid & 0xFFFF)]
        pos = same[-1] + 1 if same else next((k for k, (_, r, _) in enumerate(recs) if r > rid), len(recs))
        recs.insert(pos, (0, rid, val))
    return b"".join(struct.pack("<IIi", *r) for r in recs)


def sends(data: bytes) -> list[tuple[int, int, float]]:
    out = []
    for i in range(0, len(data) - 11, 12):
        _, rid, v = struct.unpack_from("<IIi", data, i)
        if rid >= SEND and (rid & 0x3FF000) == 0x2000 and (rid >> 28) == 7:
            out.append(((rid - SEND) >> 22, rid & 0xFFF, v / SCALE))
    return out


def read(data: bytes) -> dict:
    vol, main = {}, None
    for i in range(0, len(data) - 11, 12):
        _, rid, v = struct.unpack_from("<IIi", data, i)
        if rid == MAIN:
            main = v / SCALE
        elif rid & 0x3FFFFF == VOL & 0x3FFFFF and rid >= VOL and v != UNITY:
            vol[(rid - VOL) >> 22] = v / SCALE
    return {"volume": vol, "main_volume": main}


def track_of(rid: int) -> int | None:
    """The mixer track a 0x7... record belongs to (the Current track is 501), else None."""
    return (rid - 0x70000000) >> 22 if rid >> 28 == 7 else None


def add_tracks(data: bytes, model: bytes, src: int, first: int, last: int) -> bytes:
    """Records for inserts first..last, copied from track src of the model table (a clean template's), sends left out:
    FL keeps a set of records per insert and stores a send only when one is made."""
    mine = [struct.unpack_from("<IIi", model, i) for i in range(0, len(model) - 11, 12)]
    tmpl = [(z, r & 0x3FFFFF, v) for z, r, v in mine if track_of(r) == src and (r & 0x3FF000) != 0x2000]
    recs = [struct.unpack_from("<IIi", data, i) for i in range(0, len(data) - 11, 12)]
    have = {r for _, r, _ in recs}
    # FL keeps the table in track order, 32 records an insert, the Current track's last: the new ones go after the
    # last insert's
    before = [k for k, (_, r, _) in enumerate(recs) if track_of(r) is not None and track_of(r) < first]
    at = before[-1] + 1 if before else len(recs)
    recs[at:at] = [(z, 0x70000000 + (t << 22) + low, v) for t in range(first, last + 1) for z, low, v in tmpl
                   if 0x70000000 + (t << 22) + low not in have]
    return b"".join(struct.pack("<IIi", *r) for r in recs)


def write(data: bytes, volume: dict | None, main: float | None, warn: list) -> bytes:
    b = bytearray(data)
    at = {struct.unpack_from("<I", b, i + 4)[0]: i for i in range(0, len(b) - 11, 12)}
    for t, v in (volume or {}).items():
        rid = track_id(t)
        if rid not in at:
            warn.append(f"mixer track {t}: the base mixer has no volume record for it")
            continue
        struct.pack_into("<i", b, at[rid] + 8, int(round(float(v) * SCALE)))
    if main is not None:
        if MAIN in at:
            struct.pack_into("<i", b, at[MAIN] + 8, int(round(float(main) * SCALE)))
        else:
            warn.append("the base mixer has no main volume record")
    return bytes(b)
