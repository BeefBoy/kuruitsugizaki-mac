import struct
from pathlib import Path

import msgpack

HEAD = 1 << 16


def chunks(data: bytes) -> dict[str, bytes]:
    if data[:4] != b"RIFF" or data[8:12] != b"NIKS":
        raise ValueError("not an NKS file: no RIFF/NIKS header")
    out, i = {}, 12
    while i + 8 <= len(data):
        cid, n = data[i:i + 4].decode("latin-1"), struct.unpack_from("<I", data, i + 4)[0]
        out[cid] = data[i + 8:i + 8 + n]
        i += 8 + n + (n & 1)
    return out


def _meta(d: bytes) -> dict:
    v = msgpack.unpackb(d[4:], raw=False, strict_map_key=False)
    return v if isinstance(v, dict) else {}


def header(path: str | Path) -> dict:
    with open(path, "rb") as fh:
        data = fh.read(HEAD)
        c = chunks(data)
        if "PLID" not in c or len(c["PLID"]) < 4:
            c = chunks(data + fh.read())
    plid = _meta(c["PLID"]) if "PLID" in c else {}
    info = _meta(c["NISI"]) if len(c.get("NISI", b"")) > 4 else {}
    keys = []
    uid = plid.get("VST3.uid")
    if isinstance(uid, list) and len(uid) == 4:
        keys.append(("uid", b"".join(struct.pack(">I", int(x) & 0xFFFFFFFF) for x in uid)))
    if isinstance(plid.get("VST.magic"), int):
        keys.append(("magic", struct.pack(">I", plid["VST.magic"] & 0xFFFFFFFF)))
    if plid.get("pluginName"):
        keys.append(("name", str(plid["pluginName"]).lower()))
    return {"keys": keys, "name": info.get("name") or Path(path).stem}


def component(path: str | Path) -> bytes:
    c = chunks(Path(path).read_bytes())
    if "PCHK" not in c or len(c["PCHK"]) < 4:
        raise ValueError(f"{path}: no plugin state (PCHK) in this NKS file")
    return c["PCHK"][4:]


def uid_of(r52: bytes) -> bytes:
    return r52[0:4][::-1] + r52[4:6][::-1] + r52[6:8][::-1] + r52[8:16]


def keys_for(r52: bytes | None, name: str) -> list[tuple]:
    out = [("name", name.lower())]
    if r52 and len(r52) == 16:
        u = uid_of(r52)
        out.append(("uid", u))
        if u[:3] == b"VST":
            out.append(("magic", u[3:7]))
    return out
