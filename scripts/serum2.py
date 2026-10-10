import csv
import hashlib
import json
import struct
import sys
from pathlib import Path

import cbor2
import zstandard

import config
import flp
import presets

UI = {"displayName", "curveDisplayName", "arpBankDisplayName", "clipBankDisplayName", "displayLength_Beats", "gridWidth_Beats", "gridYOffset_Rows", "laneTabs", "selectedLane"}
SHARED = ("product", "productVersion", "url", "vendor", "version")
PRESET_META = ("presetAuthor", "presetDescription", "presetName")
DROP = {"fileType", "component", "presetHasBeenEdited", "selectedPresetPath"}


def records(data: bytes, start: int = 4) -> dict[int, bytes]:
    out, i = {}, start
    while i + 12 <= len(data):
        rid, n = struct.unpack_from("<IQ", data, i)
        out[rid] = data[i + 12:i + 12 + n]
        i += 12 + n
    return out


def xfer_unpack(d: bytes) -> tuple[dict, dict]:
    if d[:9] != b"XferJson\x00":
        raise ValueError("not an XferJson container")
    i, parts = 9, {}
    while i + 8 <= len(d):
        n, tag = struct.unpack_from("<II", d, i)
        parts[tag] = d[i + 8:i + 8 + n]
        i += 8 + n
        if tag == 2:
            break
    raw = zstandard.ZstdDecompressor().decompress(parts[2], max_output_size=1 << 28)
    return json.loads(parts[0]), cbor2.loads(raw)


def channels(p: flp.Project) -> list[dict]:
    out, name = [], None
    for n, e in enumerate(p.events):
        if e.id == 203:
            name = e.data[:-2].decode("utf-16-le")
        elif e.id == 213 and len(e.data) > 4:
            wrap = records(e.data)
            if wrap.get(54, b"").startswith(b"Serum2") and 53 in wrap:
                state = records(wrap[53])
                pm, pd = xfer_unpack(state[3])
                cm, cd = xfer_unpack(state[2])
                out.append({"event": n, "name": name, "processor": pd, "controller": cd, "pmeta": pm, "cmeta": cm})
    return out


def leaves(x, pre=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from leaves(v, f"{pre}/{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from leaves(v, f"{pre}[{i}]")
    else:
        yield pre, x


def xfer_pack(meta: dict, obj, level: int = 3) -> bytes:
    raw = cbor2.dumps(obj)
    comp = zstandard.ZstdCompressor(level=level, write_content_size=True, write_checksum=False).compress(raw)
    m = json.dumps(dict(sorted({**meta, "hash": hashlib.md5(comp).hexdigest()}.items())), separators=(",", ":")).encode("utf-8")
    return b"XferJson\x00" + struct.pack("<II", len(m), 0) + m + struct.pack("<II", len(raw), 2) + comp


def is_ui(key: str, top: str) -> bool:
    return key.startswith("kUIParam") or key in UI or (key == "name" and top.startswith(("Macro", "MidiClip")))


def split(x, top: str = ""):
    if isinstance(x, dict):
        p, c = {}, {}
        for k, v in x.items():
            t = top or k
            if is_ui(k, t):
                c[k] = v
                continue
            pv, cv = split(v, t)
            p[k] = pv
            if cv:
                c[k] = cv
        return p, c
    if isinstance(x, list):
        parts = [split(v, top) for v in x]
        cs = [c for _, c in parts]
        return [p for p, _ in parts], (cs if any(cs) else None)
    return x, None


def split_preset(o: dict, ptemplate: dict, ctemplate: dict) -> tuple[dict, dict]:
    proc, ctrl = {"component": "processor"}, {"component": "controller"}
    for k, v in o.items():
        if k in DROP or k in SHARED or k in PRESET_META:
            continue
        if is_ui(k, k):
            ctrl[k] = v
            continue
        p, c = split(v, k)
        if k in ptemplate or any(True for _ in leaves(p)):
            proc[k] = p
        if c:
            ctrl[k] = c
        elif k in ctemplate:
            ctrl[k] = ctemplate[k]
        if k.startswith("Macro") and "kParamValue" in pp(v) and isinstance(ctrl.get(k), dict):
            ctrl[k] = {"default": pp(v)["kParamValue"] / 100, **ctrl[k]}
    for k in SHARED:
        proc[k] = ctrl[k] = o.get(k, ptemplate.get(k))
    for k in PRESET_META:
        ctrl[k] = o.get(k, "")
    ctrl["presetHasBeenEdited"] = False
    return proc, ctrl


def apply(r53: bytes, preset_path: str) -> bytes:
    _, o = xfer_unpack(Path(preset_path).read_bytes())
    head, secs = presets.split_wrapper(r53)
    d = dict(secs)
    pmeta, pt = xfer_unpack(d[3])
    cmeta, ct = xfer_unpack(d[2])
    proc, ctrl = split_preset(o, pt, ct)
    cmeta = {**cmeta, **{k: ctrl[k] for k in PRESET_META}}
    out = {3: xfer_pack(pmeta, proc), 2: xfer_pack(cmeta, ctrl)}
    return presets.join_wrapper(head, [(i, out.get(i, b)) for i, b in secs])


def merge(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        return {k: merge(a.get(k), b.get(k)) if k in a and k in b else a.get(k, b.get(k)) for k in {**a, **b}}
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [merge(x, y) for x, y in zip(a, b)]
    return a if b is None or b == {} else b if a is None else a


def read(state213: bytes) -> dict:
    _, recs = presets.split_wrapper(state213)
    s = records(dict(recs)[presets.WRAP_STATE])
    _, p = xfer_unpack(s[3])
    _, c = xfer_unpack(s[2])
    return merge(p, c)


def pp(node) -> dict:
    v = (node or {}).get("plainParams", {})
    return v if isinstance(v, dict) else {}


def row(o: dict) -> dict:
    oscs = []
    for i, label in enumerate("ABCNS"):
        node = o.get(f"Oscillator{i}", {})
        p = pp(node)
        if not p.get("kParamEnable", 1.0 if i == 0 else 0.0):
            continue
        kinds = [k for k, v in node.items() if k != "plainParams" and v != {"plainParams": "default"}]
        kind = kinds[0] if kinds else ""
        src = next((Path(str(v)).stem for k, v in (node.get(kind) or {}).items() if k.startswith("relativePath")), "")
        oscs.append(f"{label}:{kind.rstrip('0123456789').replace('Osc', '')}{'(' + src + ')' if src else ''}u{int(p.get('kParamUnison', 1))}o{int(p.get('kParamOctave', 0))}")
    filters = [str(pp(o.get(f"VoiceFilter{i}")).get("kParamType", "default")) for i in (0, 1) if pp(o.get(f"VoiceFilter{i}")).get("kParamEnable")]
    fx = [next((k[2:] for k in f if k.startswith("FX")), "?") for r in range(3) for f in (o.get(f"FXRack{r}") or {}).get("FX", [])]
    return {
        "name": o.get("presetName", ""),
        "author": o.get("presetAuthor", ""),
        "tags": " ".join(o.get("tags") or []),
        "oscs": " ".join(oscs),
        "filters": " ".join(filters),
        "fx": " ".join(fx),
        "mono": int(pp(o.get("Global0")).get("kParamMonoToggle", 0)),
        "macros": " | ".join(str(o.get(f"Macro{i}", {}).get("name", "")) for i in range(8) if o.get(f"Macro{i}", {}).get("name")),
        "description": str(o.get("presetDescription", "")).replace("\n", " ")[:80],
    }


def catalog(out: str, root: Path | None = None) -> tuple[int, int]:
    root = Path(root) if root else config.path("serum2_presets")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows, bad = [], 0
    for p in sorted(Path(root).rglob("*.SerumPreset")):
        base = {"folder": p.parent.relative_to(root).as_posix(), "file": p.stem}
        try:
            rows.append({**base, **row(xfer_unpack(p.read_bytes())[1]), "error": "", "path": str(p)})
        except Exception as e:
            bad += 1
            rows.append({**base, "error": repr(e)[:120], "path": str(p)})
    fields = ["folder", "file"] + list(row({}).keys()) + ["error", "path"]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows), bad


def diff(a, b) -> list[tuple[str, object, object]]:
    la, lb = dict(leaves(a)), dict(leaves(b))
    return [(k, la.get(k, "<absent>"), lb.get(k, "<absent>")) for k in sorted(set(la) | set(lb)) if la.get(k, "<absent>") != lb.get(k, "<absent>")]


if __name__ == "__main__":
    if sys.argv[1:2] == ["catalog"]:
        n, bad = catalog(sys.argv[3] if len(sys.argv) > 3 else "tmp/serum2.tsv", Path(sys.argv[2]) if len(sys.argv) > 2 else None)
        print(n, "presets,", bad, "unreadable")
    else:
        print(json.dumps(row(xfer_unpack(Path(sys.argv[1]).read_bytes())[1]), indent=1))
