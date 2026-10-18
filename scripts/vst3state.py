import struct

import presets

HEAD = 80
COMPONENT = 3
CONTROLLER = 2
WRAP_STATE = 53
JUCE = b"VC2!"


def split(r53: bytes) -> tuple[bytes, list[tuple[int, bytes]]]:
    recs, i = [], HEAD
    while i + 12 <= len(r53):
        rid, n = struct.unpack_from("<IQ", r53, i)
        if n > len(r53) - i - 12:
            break
        recs.append((rid, r53[i + 12:i + 12 + n]))
        i += 12 + n
    if i != len(r53) or struct.unpack_from("<3I", r53, 0) != (1, 1, 64):
        raise ValueError("not a VST3 wrapper state: record 53 does not frame as header + <id, u64 size, data> records")
    return r53[:HEAD], recs


def join(head: bytes, recs: list[tuple[int, bytes]]) -> bytes:
    return head + b"".join(struct.pack("<IQ", rid, len(d)) + d for rid, d in recs)


def component(state213: bytes) -> bytes:
    _, recs = presets.split_wrapper(state213)
    return dict(split(dict(recs)[WRAP_STATE])[1])[COMPONENT]


def family(comp: bytes) -> str:
    if comp.startswith(b"VstW") and comp[16:20] == b"CcnK" and comp[176:180] == JUCE:
        return "juce-bank"
    if comp.startswith(JUCE):
        return "juce"
    if comp.startswith(b"#zip#"):
        return "zip"
    return "opaque"


def juce_xml(comp: bytes) -> bytes:
    v = comp.find(JUCE)
    n = struct.unpack_from("<I", comp, v + 4)[0]
    return comp[v + 8:v + 8 + n]


def root_tag(xml: bytes) -> str:
    i = 0
    while True:
        i = xml.find(b"<", i)
        if i < 0:
            return ""
        if xml[i + 1:i + 2] not in (b"?", b"!"):
            j = i + 1
            while j < len(xml) and xml[j:j + 1] not in (b" ", b">", b"/", b"\r", b"\n", b"\t"):
                j += 1
            return xml[i + 1:j].decode("utf-8", "replace")
        i += 1


def with_xml(comp: bytes, xml: bytes) -> bytes:
    v = comp.find(JUCE)
    n = struct.unpack_from("<I", comp, v + 4)[0]
    body = xml.removeprefix(b"\xef\xbb\xbf").rstrip(b"\0 \r\n\t")
    out = bytearray(comp[:v] + JUCE + struct.pack("<I", len(body)) + body + comp[v + 8 + n:])
    if family(comp) == "juce-bank":
        struct.pack_into(">I", out, 20, len(out) - 24)
        struct.pack_into(">I", out, 172, len(out) - 176)
    return bytes(out)


def convert(comp: bytes, data: bytes, source: str) -> bytes:
    fam = family(comp)
    if fam in ("juce", "juce-bank"):
        want, got = root_tag(juce_xml(comp)), root_tag(data)
        if not got or got != want:
            raise ValueError(f"{source}: root element <{got}> does not match the plugin state's <{want}>")
        return with_xml(comp, data)
    if fam == "zip" and data.startswith(b"#zip#"):
        return data
    raise ValueError(f"{source}: no converter from this file to a {fam} plugin state")


FRESH_HEAD = struct.pack("<5I", 1, 1, 64, 0, 1).ljust(HEAD, b"\0")


def fresh_component(data: bytes, source: str) -> bytes:
    body = data.removeprefix(b"\xef\xbb\xbf").rstrip(b"\0 \r\n\t")
    if body.lstrip().startswith(b"<"):
        return JUCE + struct.pack("<I", len(body)) + body + b"\0"
    if data.startswith(b"#zip#"):
        return data
    raise ValueError(f"{source}: building a plugin state from this file needs a saved instance of the plugin (config library)")


def apply_file(state213: bytes, data: bytes, source: str) -> bytes:
    head, recs = presets.split_wrapper(state213)
    if any(rid == WRAP_STATE for rid, _ in recs):
        return with_component(state213, convert(component(state213), data, source))
    r53 = join(FRESH_HEAD, [(COMPONENT, fresh_component(data, source))])
    return presets.join_wrapper(head, recs + [(WRAP_STATE, r53)])


def put_component(state213: bytes, comp: bytes) -> bytes:
    head, recs = presets.split_wrapper(state213)
    if any(rid == WRAP_STATE for rid, _ in recs):
        return with_component(state213, comp)
    return presets.join_wrapper(head, recs + [(WRAP_STATE, join(FRESH_HEAD, [(COMPONENT, comp)]))])


def with_component(state213: bytes, comp: bytes) -> bytes:
    head, recs = presets.split_wrapper(state213)
    out = []
    for rid, d in recs:
        if rid == WRAP_STATE:
            h, sub = split(d)
            d = join(h, [(r, comp if r == COMPONENT else x) for r, x in sub])
        out.append((rid, d))
    return presets.join_wrapper(head, out)
