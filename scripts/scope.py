import argparse, subprocess
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SR = 44100


def load(p):
    raw = subprocess.run(["ffmpeg", "-v", "quiet", "-i", str(p), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)


def band(x, lo, hi):
    if lo is None and hi is None:
        return x
    X = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    keep = np.ones_like(f, bool)
    if lo:
        keep &= f >= lo
    if hi:
        keep &= f < hi
    return np.fft.irfft(X * keep[:, None], len(x), axis=0)


def ms(x):
    return (x[:, 0] + x[:, 1]) / np.sqrt(2), (x[:, 1] - x[:, 0]) / np.sqrt(2)


def stats(x):
    m, s = ms(x)
    e = m ** 2 + s ** 2
    ang = np.degrees(np.arctan2(s, np.abs(m) + 1e-15))
    w = e / (e.sum() + 1e-20)
    spread = np.sqrt(np.sum(w * ang ** 2))
    corr = np.corrcoef(x[:, 0], x[:, 1])[0, 1] if x.std() > 0 else 0
    sm = 10 * np.log10((s ** 2).sum() / ((m ** 2).sum() + 1e-20) + 1e-20)
    return spread, corr, sm, np.sum(w * ang)


def gonio(ax, x, title, res=400):
    m, s = ms(x)
    flip = m < 0
    m, s = np.where(flip, -m, m), np.where(flip, -s, s)
    lim = max(np.abs(m).max(), np.abs(s).max(), 1e-9)
    h, xe, ye = np.histogram2d(s / lim, m / lim, bins=[res, res // 2], range=[[-1, 1], [0, 1]])
    ax.imshow(np.log10(h.T + 1), origin="lower", extent=[-1, 1, 0, 1], cmap="inferno", aspect="equal")
    for a in (45, 135):
        ax.plot([0, np.cos(np.radians(a))], [0, np.sin(np.radians(a))], color="w", lw=0.4, alpha=0.5)
    sp, c, sm, bias = stats(x)
    ax.set_title(f"{title}\nangle spread {sp:.1f} deg  corr {c:+.2f}  side/mid {sm:+.1f} dB  bias {bias:+.1f} deg (+ = R)", fontsize=8)
    ax.set_xticks([-1, 0, 1], ["L", "0", "R"])
    ax.set_yticks([])


def timeline(ax, x, title, frame_ms=20, bins=181):
    n = int(SR * frame_ms / 1000)
    k = len(x) // n
    m, s = ms(x[: k * n])
    e = (m ** 2 + s ** 2).reshape(k, n)
    ang = np.degrees(np.arctan2(s, np.abs(m) + 1e-15)).reshape(k, n)
    img = np.zeros((bins, k))
    edges = np.linspace(-90, 90, bins + 1)
    for i in range(k):
        img[:, i], _ = np.histogram(ang[i], bins=edges, weights=e[i])
    img = 10 * np.log10(img + 1e-12)
    top = img.max()
    ax.imshow(img, origin="lower", aspect="auto", cmap="inferno", vmin=top - 50, vmax=top, extent=[0, k * frame_ms / 1000, -90, 90])
    ax.set_ylabel("angle deg (+ = R)")
    ax.set_title(title, fontsize=8)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("files", nargs="+")
    p.add_argument("--at", type=float, nargs="*", default=[], help="window starts in seconds")
    p.add_argument("--len", type=float, default=0.3, help="window length in seconds")
    p.add_argument("--lo", type=float, default=None)
    p.add_argument("--hi", type=float, default=None)
    p.add_argument("--out", default="tmp/scope/scope.png")
    p.add_argument("--timeline", action="store_true")
    a = p.parse_args()
    xs = [band(load(f), a.lo, a.hi) for f in a.files]
    names = [Path(f).stem for f in a.files]
    starts = a.at or [None]
    rows = len(starts) + (1 if a.timeline else 0)
    fig = plt.figure(figsize=(5 * len(xs), 3 * rows + (1.5 if a.timeline else 0)))
    r = 0
    for t in starts:
        for j, (x, nm) in enumerate(zip(xs, names)):
            ax = fig.add_subplot(rows, len(xs), r * len(xs) + j + 1)
            seg = x if t is None else x[int(t * SR): int((t + a.len) * SR)]
            gonio(ax, seg, f"{nm}" + ("" if t is None else f" @ {t:.2f}-{t + a.len:.2f} s"))
            print(f"{nm:30s} {'' if t is None else f'{t:6.2f}s'} spread {stats(seg)[0]:5.1f} deg  corr {stats(seg)[1]:+.2f}  side/mid {stats(seg)[2]:+5.1f} dB  bias {stats(seg)[3]:+5.1f}")
        r += 1
    if a.timeline:
        for j, (x, nm) in enumerate(zip(xs, names)):
            ax = fig.add_subplot(rows, len(xs), r * len(xs) + j + 1)
            timeline(ax, x, f"{nm}: stereo angle over time, energy-weighted")
    band_txt = "" if a.lo is None and a.hi is None else f"  band {a.lo or 0:.0f}-{a.hi or SR / 2:.0f} Hz"
    fig.suptitle("scope" + band_txt, fontsize=9)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(a.out, dpi=90)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
