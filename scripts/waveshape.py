import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from spectro import SR, decode

ZOOMS = [5.0, 0.5, 0.05, 0.01]


def loudest(x: np.ndarray, win: float = 1.0) -> float:
    n = int(win * SR)
    c = np.concatenate([[0.0], np.cumsum((x ** 2).mean(axis=1))])
    e = c[n:] - c[:-n]
    return (int(np.argmax(e)) + n // 2) / SR


def spec(arg: str):
    if "@" in arg:
        p, t = arg.rsplit("@", 1)
        return p, float(t)
    return arg, None


def stats(x: np.ndarray) -> str:
    a = np.abs(x)
    pk = a.max()
    rms = np.sqrt((x ** 2).mean())
    near = (a >= pk * 0.98).mean() * 100
    runs = int(np.sum((a[1:] >= pk * 0.999) & (a[:-1] >= pk * 0.999)))
    return f"peak {20 * np.log10(pk + 1e-12):.2f} dBFS  rms {20 * np.log10(rms + 1e-12):.1f}  crest {20 * np.log10(pk / (rms + 1e-12)):.1f} dB  samples within 2% of peak {near:.3f}%  consecutive at peak {runs}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", help="path or path@seconds (centre); default centre is the loudest second")
    ap.add_argument("--out", default="tmp/waveshape/ab.png")
    a = ap.parse_args()
    items = []
    for f in a.files:
        p, t = spec(f)
        full = decode(p)
        c = t if t is not None else loudest(full)
        items.append((Path(p).stem, full, c))
    cols = len(items)
    fig, ax = plt.subplots(len(ZOOMS) + 1, cols, figsize=(7 * cols, 3 * (len(ZOOMS) + 1)), squeeze=False)
    for j, (name, x, c) in enumerate(items):
        print(f"{name} @ {c:.2f}s  {stats(x)}")
        for i, z in enumerate(ZOOMS):
            s = max(0, int((c - z / 2) * SR))
            e = min(len(x), s + int(z * SR))
            tt = np.arange(s, e) / SR
            axx = ax[i][j]
            axx.plot(tt, x[s:e, 0], lw=0.6 if z > 0.05 else 0.9, label="L")
            axx.plot(tt, x[s:e, 1], lw=0.6 if z > 0.05 else 0.9, alpha=0.6, label="R")
            if z <= 0.01:
                axx.plot(tt, x[s:e, 0], ".", ms=2, color="k")
            axx.set_ylim(-1.05, 1.05)
            axx.axhline(0, color="grey", lw=0.4)
            axx.set_title(f"{name}  {z * 1000:g} ms @ {c:.2f}s" if z < 1 else f"{name}  {z:g} s @ {c:.2f}s", fontsize=9)
            axx.grid(alpha=0.25)
        h = ax[len(ZOOMS)][j]
        h.hist(x.mean(axis=1), bins=401, range=(-1, 1), log=True, color="slateblue")
        h.set_title(f"{name}  sample value histogram (mono, log)", fontsize=9)
    ax[0][0].legend(loc="upper right", fontsize=7)
    fig.tight_layout()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=90)
    print(out)


if __name__ == "__main__":
    main()
