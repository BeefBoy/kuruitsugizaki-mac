import argparse
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SR = 44100
N_FFT = 16384
HOP = 2048
LO_MIDI, HI_MIDI = 24, 96
CHROMA_LO = 36
PC = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
INFRA_WARN = 0.05  # share of energy below 20 Hz; glass_vertebrae's drops carried 16-18%


def decode(path: str, start: float = 0.0, end: float | None = None) -> np.ndarray:
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start)]
    if end is not None:
        cmd += ["-t", str(end - start)]
    cmd += ["-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "pipe:1"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)


def stft_power(x: np.ndarray) -> np.ndarray:
    pad = np.concatenate([np.zeros(N_FFT // 2), x, np.zeros(N_FFT)])
    win = np.hanning(N_FFT)
    n = max(1, (len(pad) - N_FFT) // HOP)
    out = np.empty((n, N_FFT // 2 + 1), dtype=np.float32)
    for i in range(0, n, 128):
        idx = np.arange(i, min(n, i + 128))[:, None] * HOP + np.arange(N_FFT)[None, :]
        out[i:i + len(idx)] = np.abs(np.fft.rfft(pad[idx] * win, axis=1)) ** 2
    return out


def band_matrix(centers_midi: np.ndarray, width: float) -> np.ndarray:
    f = np.fft.rfftfreq(N_FFT, 1 / SR)
    M = np.zeros((len(f), len(centers_midi)), dtype=np.float32)
    m = 69 + 12 * np.log2(np.maximum(f, 1e-9) / 440)
    pos = (m - centers_midi[0]) / width
    for i in range(1, len(f)):
        p = pos[i]
        if p < -0.5 or p > len(centers_midi) - 0.5:
            continue
        lo = int(np.floor(p))
        frac = p - lo
        if 0 <= lo < len(centers_midi):
            M[i, lo] += 1 - frac
        if 0 <= lo + 1 < len(centers_midi):
            M[i, lo + 1] += frac
    return M


def db(p: np.ndarray) -> np.ndarray:
    return 10 * np.log10(np.maximum(p, 1e-12))


def correlation(st: np.ndarray, frames: int) -> np.ndarray:
    out = np.zeros(frames)
    for i in range(frames):
        seg = st[i * HOP:i * HOP + N_FFT // 4]
        if len(seg) < 64:
            break
        l, r = seg[:, 0], seg[:, 1]
        d = np.sqrt((l * l).sum() * (r * r).sum())
        out[i] = (l * r).sum() / d if d > 1e-12 else 0
    return out


def analyse(path: str, start: float, end: float | None, bpm: float | None, out: Path, first_bar: int):
    st = decode(path, start, end)
    mono = st.mean(axis=1)
    dur = len(mono) / SR
    P = stft_power(mono)
    t = np.arange(len(P)) * HOP / SR + start
    semis = np.arange(LO_MIDI, HI_MIDI + 1)
    S = P @ band_matrix(semis, 1.0)
    logc = np.linspace(69 + 12 * np.log2(20 / 440), 69 + 12 * np.log2(20000 / 440), 240)
    L = P @ band_matrix(logc, logc[1] - logc[0])
    chroma = np.zeros((len(P), 12))
    for j, m in enumerate(semis):
        if m >= CHROMA_LO:
            chroma[:, m % 12] += S[:, j]
    k = max(1, int(0.25 * SR / HOP))
    kern = np.ones(k) / k
    chroma_s = np.apply_along_axis(lambda c: np.convolve(c, kern, mode="same"), 0, chroma)
    chroma_n = chroma_s / np.maximum(chroma_s.max(axis=1, keepdims=True), 1e-12)
    rms = np.array([np.sqrt(np.mean(mono[i * HOP:i * HOP + HOP] ** 2) + 1e-12) if i * HOP < len(mono) else 1e-6 for i in range(len(P))])
    peak = np.array([np.max(np.abs(st[i * HOP:i * HOP + HOP])) if i * HOP < len(st) else 0 for i in range(len(P))])
    corr = correlation(st, len(P))

    width = min(40, max(14, dur / 5))
    fig, ax = plt.subplots(5, 1, figsize=(width, 16), sharex=True, gridspec_kw={"height_ratios": [5, 2.2, 3, 1.3, 1]})
    sd = db(S.T)
    top = np.percentile(sd, 99.5)
    ax[0].imshow(sd, aspect="auto", origin="lower", cmap="magma", vmin=top - 60, vmax=top,
                 extent=[t[0], t[-1], LO_MIDI - 0.5, HI_MIDI + 0.5], interpolation="nearest")
    ax[0].set_yticks([m for m in semis if m % 12 == 0])
    ax[0].set_yticklabels([f"C{m // 12 - 1}" for m in semis if m % 12 == 0])
    ax[0].set_ylabel("semitones")
    ax[1].imshow(chroma_n.T, aspect="auto", origin="lower", cmap="viridis", vmin=0, vmax=1,
                 extent=[t[0], t[-1], -0.5, 11.5], interpolation="nearest")
    ax[1].set_yticks(range(12))
    ax[1].set_yticklabels(PC)
    ax[1].set_ylabel("chroma")
    ld = db(L.T)
    lt = np.percentile(ld, 99.5)
    ax[2].imshow(ld, aspect="auto", origin="lower", cmap="inferno", vmin=lt - 70, vmax=lt,
                 extent=[t[0], t[-1], 0, len(logc)], interpolation="nearest")
    ticks = [30, 60, 120, 250, 500, 1000, 2000, 4000, 8000, 16000]
    ax[2].set_yticks([np.interp(69 + 12 * np.log2(h / 440), logc, np.arange(len(logc))) for h in ticks])
    ax[2].set_yticklabels([f"{h}" if h < 1000 else f"{h // 1000}k" for h in ticks])
    ax[2].set_ylabel("Hz")
    ax[3].plot(t, 20 * np.log10(rms), lw=0.8, label="rms dBFS")
    ax[3].plot(t, 20 * np.log10(np.maximum(peak, 1e-6)), lw=0.6, alpha=0.6, label="peak dBFS")
    ax[3].set_ylim(-60, 1)
    ax[3].legend(loc="lower right", fontsize=8)
    ax[3].grid(alpha=0.3)
    ax[4].plot(t, corr, lw=0.8, color="teal")
    ax[4].axhline(0, color="grey", lw=0.5)
    ax[4].set_ylim(-1.05, 1.05)
    ax[4].set_ylabel("L/R corr")
    ax[4].set_xlabel("seconds")
    rows = []
    if bpm:
        bar_s = 240 / bpm
        b0 = int(np.ceil((start - 1e-9) / bar_s))
        b = b0
        while b * bar_s <= t[-1]:
            x = b * bar_s
            for a in ax:
                a.axvline(x, color="white" if a in ax[:3] else "grey", lw=0.4 if b % 4 else 0.9, alpha=0.5)
            if b % 4 == 0:
                ax[0].text(x, HI_MIDI, f"{b + first_bar}", color="white", fontsize=8, va="top")
            sel = (t >= x) & (t < x + bar_s)
            if sel.sum() >= 2:
                c = chroma[sel].sum(axis=0)
                share = c / max(c.sum(), 1e-12)
                topk = np.argsort(share)[::-1][:3]
                r = rms[sel]
                rows.append(f"bar {b + first_bar:3}  {' '.join(f'{PC[i]:2}{share[i] * 100:3.0f}%' for i in topk)}   rms {20 * np.log10(np.sqrt(np.mean(r ** 2))):6.1f} dBFS  corr {corr[sel].mean():+.2f}")
            b += 1
    fig.suptitle(f"{Path(path).name}  {start:.1f}-{start + dur:.1f} s" + (f"  {bpm} BPM" if bpm else ""), fontsize=11)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=100)
    plt.close(fig)
    integ = 20 * np.log10(np.sqrt(np.mean(mono ** 2)) + 1e-12)
    print(f"{out}  {dur:.1f} s  rms {integ:.1f} dBFS  peak {20 * np.log10(np.max(np.abs(st)) + 1e-12):.1f} dBFS  corr mean {corr.mean():+.2f}")
    f = np.fft.rfftfreq(N_FFT, 1 / SR)
    infra = float(P[:, f < 20].sum() / max(P.sum(), 1e-12))
    print(f"below 20 Hz {infra * 100:.1f}% of the energy" + (
        f"  WARNING: inaudible energy above {INFRA_WARN * 100:g}%; it costs the limiter headroom. A sound may sit octaves "
        f"under its written note: render one note of each low sound and read its lowest partial" if infra > INFRA_WARN else ""))
    for r in rows:
        print(r)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=None)
    ap.add_argument("--bpm", type=float, default=None)
    ap.add_argument("--first-bar", type=int, default=1)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    name = Path(a.path).stem + (f"_{a.start:g}-{a.end:g}" if a.end else "")
    analyse(a.path, a.start, a.end, a.bpm, Path(a.out) if a.out else Path("tmp/spectro") / f"{name}.png", a.first_bar)
