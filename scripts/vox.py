import math
import sys
from pathlib import Path

import numpy as np

from spectro import SR, decode

PC = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
HOP = 441
WIN = 1764


def note(f: float) -> str:
    m = 69 + 12 * math.log2(f / 440)
    r = round(m)
    return f"{PC[r % 12]}{r // 12 - 1}{(m - r) * 100:+.0f}"


def f0_track(x: np.ndarray, fmin: float = 70, fmax: float = 900):
    lo, hi = int(SR / fmax), int(SR / fmin)
    out = []
    for k in range(0, len(x) - WIN, HOP):
        seg = x[k:k + WIN] * np.hanning(WIN)
        e = float(np.dot(seg, seg))
        if e < 1e-6:
            out.append(0.0)
            continue
        ac = np.fft.irfft(np.abs(np.fft.rfft(seg, 2 * WIN)) ** 2)[:WIN]
        ac /= ac[0]
        lag = lo + int(np.argmax(ac[lo:hi]))
        if ac[lag] < 0.55:
            out.append(0.0)
            continue
        a, b, c = ac[lag - 1], ac[lag], ac[lag + 1]
        shift = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) else 0
        out.append(SR / (lag + shift))
    return np.array(out)


def segments(path: str, start: float = 0, end: float | None = None, gate_db: float = -32, min_len: float = 0.08, dip_db: float = 10):
    st = decode(path, start, end)
    x = st.mean(axis=1)
    n = (len(x) - WIN) // HOP
    rms = np.array([np.sqrt(np.mean(x[k * HOP:k * HOP + WIN] ** 2)) for k in range(n)])
    db = 20 * np.log10(rms + 1e-9)
    f0 = f0_track(x)[:n]
    w = max(1, int(0.15 * SR / HOP))
    local = np.array([db[max(0, k - w):k + w + 1].max() for k in range(n)])
    on = (db > gate_db) & (db > local - dip_db)
    segs, i = [], 0
    while i < n:
        if on[i]:
            j = i
            while j < n and on[j]:
                j += 1
            t0, t1 = i * HOP / SR, j * HOP / SR
            if t1 - t0 >= min_len:
                v = f0[i:j][f0[i:j] > 0]
                voiced = len(v) / max(1, j - i)
                segs.append({"t0": round(t0 + start, 3), "t1": round(t1 + start, 3), "dur": round(t1 - t0, 3),
                             "peak_db": round(float(db[i:j].max()), 1), "voiced": round(voiced, 2),
                             "f0": round(float(np.median(v)), 1) if len(v) else 0.0,
                             "note": note(float(np.median(v))) if len(v) else "-",
                             "f0_spread_c": round(float(1200 * np.log2(v.max() / v.min())), 0) if len(v) > 2 else 0})
            i = j
        else:
            i += 1
    return segs, len(x) / SR


if __name__ == "__main__":
    p = sys.argv[1]
    s0 = float(sys.argv[2]) if len(sys.argv) > 2 else 0
    s1 = float(sys.argv[3]) if len(sys.argv) > 3 else None
    segs, dur = segments(p, s0, s1)
    voiced = [s for s in segs if s["voiced"] > 0.5]
    print(f"{Path(p).name}: {dur:.1f} s analysed, {len(segs)} segments, {len(voiced)} mostly voiced")
    from collections import Counter
    pcs = Counter(s["note"][:-3].rstrip("0123456789-") for s in voiced if s["note"] != "-")
    print("   pitch classes of voiced segments:", pcs.most_common(8))
    for s in segs[:40]:
        print(f"   {s['t0']:7.3f}-{s['t1']:7.3f} ({s['dur']:5.3f}s) peak {s['peak_db']:6.1f} voiced {s['voiced']:.2f} f0 {s['f0']:6.1f} {s['note']:>7} spread {s['f0_spread_c']:>5}c")
