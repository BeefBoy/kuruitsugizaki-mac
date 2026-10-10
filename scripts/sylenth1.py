import csv
import json
import struct
import sys
import zlib
from collections import Counter
from pathlib import Path

import config
import presets

MAGIC = b"1lys"
N = 244
HEAD = 20
NAME_LEN = 36
SLOT = N * 4 + NAME_LEN
LEVEL = 5
PARAMS = json.loads((Path(__file__).resolve().parents[1] / "profiles" / "sylenth1" / "params.json").read_text(encoding="utf-8"))
NAMES = [PARAMS[str(i)]["name"] for i in range(N)]
IDX = {n: i for i, n in enumerate(NAMES)}
OSCS = ["A1", "A2", "B1", "B2"]
FX = ["Arp", "Chorus", "Comp", "Delay", "Dist", "EQ", "Phaser", "Reverb"]


def fxp_program(path) -> tuple[list[float], str]:
    data = Path(path).read_bytes()
    if data[:4] != b"CcnK" or data[8:12] != b"FPCh" or data[16:20] != b"syl1":
        raise ValueError(f"not a Sylenth1 FPCh preset: {data[:20]!r}")
    size = struct.unpack_from(">I", data, 56)[0]
    chunk = data[60:60 + size]
    if chunk[:4] != MAGIC:
        raise ValueError(f"chunk magic {chunk[:4]!r}")
    blob = zlib.decompress(chunk[8:])
    if len(blob) != HEAD + SLOT or struct.unpack_from("<I", blob, 12)[0] != N:
        raise ValueError(f"program blob is {len(blob)} bytes")
    params = list(struct.unpack_from(f"<{N}f", blob, HEAD))
    return params, blob[HEAD + N * 4:].split(b"\0")[0].decode("latin-1")


def bank_unpack(chunk: bytes) -> tuple[bytes, bytes, bytes]:
    if chunk[:4] != MAGIC:
        raise ValueError(f"bank chunk magic {chunk[:4]!r}")
    d = zlib.decompressobj()
    raw = d.decompress(chunk[8:])
    if struct.unpack_from("<I", raw, 12)[0] != N:
        raise ValueError("bank does not hold 244-parameter programs")
    return chunk[:8], raw, d.unused_data


def bank_pack(head: bytes, raw: bytes, tail: bytes) -> bytes:
    return head + zlib.compress(raw, LEVEL) + tail


def slot(raw: bytes, i: int) -> tuple[list[float], str]:
    o = HEAD + i * SLOT
    return list(struct.unpack_from(f"<{N}f", raw, o)), raw[o + N * 4:o + SLOT].split(b"\0")[0].decode("latin-1")


def set_slot(raw: bytes, i: int, params: list[float], name: str) -> bytes:
    b = bytearray(raw)
    o = HEAD + i * SLOT
    struct.pack_into(f"<{N}f", b, o, *params)
    b[o + N * 4:o + SLOT] = name.encode("latin-1", "replace")[:NAME_LEN].ljust(NAME_LEN, b"\0")
    struct.pack_into("<I", b, 16, i)
    return bytes(b)


def apply(r53: bytes, fxp_path: str) -> bytes:
    params, name = fxp_program(fxp_path)
    head, raw, tail = bank_unpack(presets.vst2_parts(r53)["chunk"])
    return presets.replace_chunk(r53, bank_pack(head, set_slot(raw, 0, params, name), tail))


def read(state213: bytes) -> dict:
    _, recs = presets.split_wrapper(state213)
    _, raw, _ = bank_unpack(presets.vst2_parts(dict(recs)[presets.WRAP_STATE])["chunk"])
    cur = struct.unpack_from("<I", raw, 16)[0]
    params, name = slot(raw, cur)
    return {"program": cur, "name": name, "params": dict(zip(NAMES, params))}


def enum(params: list[float], name: str) -> int:
    m = PARAMS[str(IDX[name])]["members"]
    return round(params[IDX[name]] * (m - 1))


def row(params: list[float], name: str) -> dict:
    v = lambda n: round(params[IDX[n]], 3)
    oscs = []
    for o in OSCS:
        voices = enum(params, f"Osc {o} Voices")
        if voices and params[IDX[f"Osc {o} Volume"]] > 0:
            oscs.append(f"{o}:w{enum(params, f'Osc {o} Waveform')}v{voices}o{enum(params, f'Osc {o} Octave') - 3}")
    return {
        "name": name,
        "oscs": " ".join(oscs),
        "mix_a": v("Mix A"),
        "mix_b": v("Mix B"),
        "filt_a": enum(params, "Filter A Type"),
        "filt_b": enum(params, "Filter B Type"),
        "cutoff": v("FilterCtl Cutoff"),
        "reso": v("FilterCtl Reso"),
        "amp_att": v("AmpEnv A Attack"),
        "amp_dec": v("AmpEnv A Decay"),
        "amp_sus": v("AmpEnv A Sustain"),
        "amp_rel": v("AmpEnv A Release"),
        "mono": enum(params, "Mono Legato"),
        "porta": v("Porta Time") if enum(params, "Porta Mode") else 0,
        "poly": enum(params, "Polyphony"),
        "fx": " ".join(f for f in FX if enum(params, f"Sw {f}OnOff")),
    }


def files(folders=None) -> list[Path]:
    root = config.path("sylenth1_presets")
    out = []
    for f in folders or config.get("sylenth1_folders") or ["."]:
        out += sorted((root / f).rglob("*.fxp"))
    return out


def catalog(out: str, folders=None) -> tuple[int, int]:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows, bad = [], 0
    for p in files(folders):
        base = {"folder": p.parent.relative_to(config.path("sylenth1_presets")).as_posix(), "file": p.name}
        try:
            params, name = fxp_program(p)
            rows.append({**base, **row(params, name), "error": "", "path": str(p)})
        except Exception as e:
            bad += 1
            rows.append({**base, "error": repr(e)[:120], "path": str(p)})
    fields = ["folder", "file"] + list(row([0.0] * N, "").keys()) + ["error", "path"]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows), bad


if __name__ == "__main__":
    if sys.argv[1:2] == ["catalog"]:
        n, bad = catalog(sys.argv[2] if len(sys.argv) > 2 else "tmp/sylenth1.tsv")
        print(n, "presets,", bad, "unreadable")
    else:
        params, name = fxp_program(sys.argv[1])
        print(json.dumps({"name": name, **row(params, name)}, indent=1))
