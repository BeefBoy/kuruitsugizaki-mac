import json
import struct
from pathlib import Path

WRAP_STATE = 53


def split_wrapper(data: bytes) -> tuple[bytes, list[tuple[int, bytes]]]:
    head, recs, i = data[:4], [], 4
    while i + 12 <= len(data):
        rid, n = struct.unpack_from("<IQ", data, i)
        recs.append((rid, data[i + 12:i + 12 + n]))
        i += 12 + n
    if i != len(data):
        raise ValueError(f"wrapper state does not frame exactly: stopped at {i} of {len(data)}")
    return head, recs


def join_wrapper(head: bytes, recs: list[tuple[int, bytes]]) -> bytes:
    return head + b"".join(struct.pack("<IQ", rid, len(d)) + d for rid, d in recs)


def vst2_parts(r53: bytes) -> dict:
    v = r53.find(b"VstW")
    c = v + 16
    if r53[c:c + 4] != b"CcnK" or r53[c + 8:c + 12] != b"FBCh":
        raise ValueError("record 53 is not a VstW + CcnK/FBCh bank chunk")
    size = struct.unpack_from(">I", r53, c + 4)[0]
    csize = struct.unpack_from(">I", r53, c + 156)[0]
    return {"v": v, "c": c, "size": size, "csize": csize, "chunk": r53[c + 160:c + 160 + csize], "after": r53[c + 8 + size:]}


def replace_chunk(r53: bytes, chunk: bytes) -> bytes:
    p = vst2_parts(r53)
    v, c = p["v"], p["c"]
    size = 152 + len(chunk)
    prefix = bytearray(r53[:v])
    struct.pack_into("<I", prefix, 84, size + 24)
    ccnk = bytearray(r53[c:c + 160])
    struct.pack_into(">I", ccnk, 4, size)
    struct.pack_into(">I", ccnk, 156, len(chunk))
    return bytes(prefix) + r53[v:c] + bytes(ccnk) + chunk + p["after"]


def vital_chunk(template_chunk: bytes, preset: dict) -> bytes:
    _, end = json.JSONDecoder().raw_decode(template_chunk.decode("latin-1"))
    return json.dumps(preset, separators=(",", ":")).encode("utf-8") + template_chunk[end:]


def load_vital(path: str) -> dict:
    p = json.loads(Path(path).read_text(encoding="utf-8"))
    p.setdefault("preset_name", Path(path).stem)
    return p


def diva_sections(r53: bytes) -> tuple[bytes, list[tuple[int, bytes]]]:
    head, sections = split_wrapper(r53)
    if head != struct.pack("<I", 1):
        raise ValueError("Diva state must have header 1")
    for sid in (3, 2):
        parts = [d for rid, d in sections if rid == sid]
        if len(parts) != 1:
            raise ValueError(f"Diva state must have exactly one section {sid}")
        d = parts[0]
        if len(d) < 4 or struct.unpack_from("<I", d)[0] != len(d) - 4:
            raise ValueError(f"Diva section {sid} preset length does not match its payload")
    return head, sections


def replace_diva(r53: bytes, text: bytes) -> bytes:
    head, sections = diva_sections(r53)
    payload = struct.pack("<I", len(text)) + text
    return join_wrapper(head, [(rid, payload if rid in (3, 2) else d) for rid, d in sections])


def read_diva(state213: bytes) -> bytes:
    _, recs = split_wrapper(state213)
    _, sections = diva_sections(dict(recs)[WRAP_STATE])
    return dict(sections)[3][4:]


def apply(plugin: str, state213: bytes, preset_path: str) -> bytes:
    if plugin == "flex":
        import flex
        return flex.apply(state213, preset_path)
    head, recs = split_wrapper(state213)
    out = []
    for rid, d in recs:
        if rid == WRAP_STATE:
            if plugin == "vital":
                d = replace_chunk(d, vital_chunk(vst2_parts(d)["chunk"], load_vital(preset_path)))
            elif plugin == "diva":
                path = Path(preset_path)
                d = replace_diva(d, f"#pgm={path.name}\n".encode("utf-8") + path.read_bytes())
            elif plugin == "sylenth1":
                import sylenth1
                d = sylenth1.apply(d, preset_path)
            elif plugin == "serum2":
                import serum2
                d = serum2.apply(d, preset_path)
            else:
                raise ValueError(f"presets for {plugin!r} are not supported yet")
        out.append((rid, d))
    return join_wrapper(head, out)


def read_vital(state213: bytes) -> dict:
    _, recs = split_wrapper(state213)
    r53 = dict(recs)[WRAP_STATE]
    obj, _ = json.JSONDecoder().raw_decode(vst2_parts(r53)["chunk"].decode("utf-8", "replace"))
    return obj
