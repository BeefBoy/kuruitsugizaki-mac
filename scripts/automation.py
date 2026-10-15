import struct

import config

TEMPLATE = tuple(config.get("automation_template") or ()) or None
HEAD = bytes.fromhex("0100000040000000000400000003000000")
TAIL = bytes.fromhex(
    "01000000ffffffffffffffffffffffffffffffff80000000800000000000000080000000"
    "0500000003000000010000000000000000000000000000000000f03f0000000000000000"
    "0100000000000000fffffffffffffffffffffffffbb20000000000000000000000000000"
    "00000000"
)
LINK = bytes.fromhex("00000000000000000000000008000000d5010000")
PLUG, MIXER_VOL, MIXER_PAN, MIXER_SEP = 0x70000000, 0x1FC0, 0x1FC1, 0x1FC2
PLUG20 = 0x20000000  # FL 20's mixer base; only master volume measured (walk.flp)
CHAN = {"vol": 0x0, "pan": 0x1, "fcut": 0x2, "fres": 0x3, "pitch": 0x4, "mute": 0x7, "fxtrack": 0x8}
GLOBAL = {"tempo": 0x40000005, "main_vol": 0x40000000, "main_pitch": 0x40000002}


def decode_points(d: bytes) -> tuple[list[dict], dict]:
    n = struct.unpack_from("<I", d, 17)[0]
    pts, beat = [], 0.0
    for i in range(n):
        dt, value, tension = struct.unpack_from("<ddf", d, 21 + 24 * i)
        pad, shape = d[41 + 24 * i:44 + 24 * i], d[44 + 24 * i]
        beat = beat + dt if i else dt
        p = {"beat": beat, "value": value}
        if tension:
            p["tension"] = tension
        if shape not in (0, 2) or (i == 0 and shape) or (i and shape == 0):
            p["shape"] = shape
        if pad != b"\0\0\0":
            p["raw_pad"] = pad.hex()
        pts.append(p)
    extra = {}
    if d[:17] != HEAD:
        extra["raw_head"] = d[:17].hex()
    tail = d[21 + 24 * n:]
    if tail != TAIL:
        extra["raw_tail"] = tail.hex()
    prev = 0.0
    for i, p in enumerate(pts):
        dt = struct.unpack_from("<d", d, 21 + 24 * i)[0]
        if (p["beat"] - prev if i else p["beat"]) != dt:
            p["dt"] = dt
        prev = p["beat"]
    return pts, extra


def encode_points(pts: list[dict], extra: dict | None = None) -> bytes:
    extra = extra or {}
    out = bytearray(bytes.fromhex(extra["raw_head"]) if "raw_head" in extra else HEAD)
    out += struct.pack("<I", len(pts))
    prev = 0.0
    for i, p in enumerate(pts):
        dt = p.get("dt", p["beat"] - prev if i else p["beat"])
        prev = p["beat"]
        shape = p.get("shape", 0 if i == 0 else 2)
        out += struct.pack("<ddf", dt, float(p["value"]), float(p.get("tension", 0.0)))
        out += bytes.fromhex(p["raw_pad"]) if "raw_pad" in p else b"\0\0\0"
        out.append(shape & 0xFF)
    out += bytes.fromhex(extra["raw_tail"]) if "raw_tail" in extra else TAIL
    return bytes(out)


def decode_target(eid: int, channel_ids: dict) -> dict:
    for k, v in GLOBAL.items():
        if eid == v:
            return {"global": k}
    base = PLUG if PLUG <= eid < 0xF0000000 else PLUG20 if PLUG20 <= eid < 0x30000000 else None
    if base is not None:
        rel = eid - base
        track, slot, low = rel >> 22, (rel >> 16) & 0x3F, rel & 0xFFFF
        if low >= 0x8000:
            return {"mixer": track, "slot": slot, "param": low - 0x8000}
        name = {MIXER_VOL: "vol", MIXER_PAN: "pan", MIXER_SEP: "sep"}.get(low)
        if name and slot == 0:
            return {"mixer": track, "param": name}
        return {"mixer": track, "slot": slot, "rec": hex(low)}
    if eid < 0x40000000:
        ch, low = eid >> 16, eid & 0xFFFF
        cid = channel_ids.get(ch, f"rack{ch}")
        if low >= 0x8000:
            return {"channel": cid, "param": low - 0x8000}
        name = {v: k for k, v in CHAN.items()}.get(low)
        return {"channel": cid, "param": name} if name else {"channel": cid, "rec": hex(low)}
    return {"rec": hex(eid)}


def encode_target(t: dict, channel_index: dict) -> int:
    if "global" in t:
        return GLOBAL[t["global"]]
    if "mixer" in t:
        base = PLUG + (int(t["mixer"]) << 22) + (int(t.get("slot", 0)) << 16)
        if "rec" in t:
            return base + int(t["rec"], 16)
        p = t["param"]
        if isinstance(p, int):
            return base + 0x8000 + p
        return base + {"vol": MIXER_VOL, "pan": MIXER_PAN, "sep": MIXER_SEP}[p]
    if "channel" in t:
        c = t["channel"]
        base = (c if isinstance(c, int) else channel_index[c]) << 16
        if "rec" in t:
            return base + int(t["rec"], 16)
        p = t["param"]
        return base + (0x8000 + p if isinstance(p, int) else CHAN[p])
    if "rec" in t:
        return int(t["rec"], 16)
    raise ValueError(f"cannot encode automation target {t!r}")


def link(channel: int, target_id: int, raw: str | None = None) -> bytes:
    r = bytearray(bytes.fromhex(raw) if raw else LINK)
    struct.pack_into("<H", r, 2, channel)
    struct.pack_into("<I", r, 8, target_id)
    return bytes(r)
