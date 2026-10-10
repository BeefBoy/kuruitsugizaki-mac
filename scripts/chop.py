import struct
from pathlib import Path

import numpy as np

from spectro import SR, decode


def write_wav(path: Path, x: np.ndarray, rate: int = SR):
    x = np.asarray(x, dtype=np.float32)
    if x.ndim == 1:
        x = x[:, None]
    ch = x.shape[1]
    data = x.tobytes()
    fmt = struct.pack("<HHIIHH", 3, ch, rate, rate * ch * 4, ch * 4, 32)
    fact = struct.pack("<I", len(x))
    body = b"WAVE" + b"fmt " + struct.pack("<I", 16) + fmt + b"fact" + struct.pack("<I", 4) + fact + b"data" + struct.pack("<I", len(data)) + data
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)


def cut(src: str, t0: float, t1: float, pre: float = 0.02, post: float = 0.05, fade_ms: float = 6, reverse: bool = False, peak_db: float | None = -3.0) -> np.ndarray:
    a = max(0.0, t0 - pre)
    x = decode(src, a, t1 + post)
    n = int(fade_ms / 1000 * SR)
    if len(x) > 2 * n and n:
        ramp = np.linspace(0, 1, n)[:, None]
        x[:n] *= ramp
        x[-n:] *= ramp[::-1]
    if reverse:
        x = x[::-1].copy()
    if peak_db is not None:
        pk = np.abs(x).max()
        if pk > 0:
            x *= 10 ** (peak_db / 20) / pk
    return x


def make(src: str, chops: dict, out_dir: str) -> dict:
    paths = {}
    for name, spec in chops.items():
        t0, t1 = spec[0], spec[1]
        opts = spec[2] if len(spec) > 2 else {}
        p = Path(out_dir) / f"{name}.wav"
        write_wav(p, cut(src, t0, t1, **opts))
        paths[name] = str(p.resolve()).replace("\\", "/")
    return paths
