import argparse
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import wash

SR = 44100
N_FFT = 16384
HOP = 2048
LO_MIDI, HI_MIDI = 24, 96
CHROMA_LO = 36
PC = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
INFRA_WARN = 0.05  # share of energy below 20 Hz; glass_vertebrae's drops carried 16-18%
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])  # Krumhansl-Kessler
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
STEPS = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10]}
BANDS = [(20, 60), (60, 250), (250, 1000), (1000, 4000), (4000, 20000)]
LIT = 0.6  # a pitch class counts as sounding when its chroma is over this share of the frame's strongest class


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


def parse_key(key: str | None) -> tuple[int, str] | None:
    """'F minor', 'F#m', 'Eb major' -> (pitch class, mode)"""
    if not key:
        return None
    k = key.strip()
    mode = "minor" if k.endswith("m") or "min" in k.lower() else "major"
    name = k.split()[0] if " " in k else k[:-1] if k.endswith("m") else k
    flats = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}
    return PC.index(flats.get(name, name)), mode


def key_fit(c: np.ndarray) -> tuple[str, float]:
    best = max((np.corrcoef(np.roll(prof, k), c)[0, 1], f"{PC[k]} {mode}")
               for k in range(12) for prof, mode in ((MAJOR, "major"), (MINOR, "minor")))
    return best[1], best[0]


def bass_track(P: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """the strongest partial between 25 and 130 Hz per frame, in fractional MIDI, and whether it is loud enough to count"""
    f = np.fft.rfftfreq(N_FFT, 1 / SR)
    lo, hi = np.searchsorted(f, 25), np.searchsorted(f, 130)
    seg = P[:, lo:hi]
    k = np.argmax(seg, axis=1)
    lp = np.log(np.maximum(seg, 1e-20))
    r = np.arange(len(P))
    a = lp[r, np.clip(k - 1, 0, seg.shape[1] - 1)]
    b = lp[r, k]
    c = lp[r, np.clip(k + 1, 0, seg.shape[1] - 1)]
    den = a - 2 * b + c
    off = np.where(np.abs(den) > 1e-9, 0.5 * (a - c) / np.where(np.abs(den) > 1e-9, den, 1), 0.0)
    hz = f[lo + k] + np.clip(off, -1, 1) * (f[1] - f[0])
    peak = seg[r, k]
    voiced = peak > np.percentile(peak, 95) * 10 ** (-25 / 10)
    return 69 + 12 * np.log2(np.maximum(hz, 1e-9) / 440), voiced


def pitch_lines(chroma: np.ndarray, chroma_n: np.ndarray, bm: np.ndarray, bv: np.ndarray, key) -> list[str]:
    tot = chroma.sum(axis=0)
    share = tot / max(tot.sum(), 1e-12)
    order = [int(i) for i in np.argsort(share)[::-1]]
    lit = (chroma_n > LIT).sum(axis=1)
    loud = chroma.sum(axis=1) > np.percentile(chroma.sum(axis=1), 20)
    name, fit = key_fit(tot)
    out = [f"pitch: {lit[loud].mean():.1f} classes sounding per moment (chroma > {LIT})  top "
           + " ".join(f"{PC[i]} {share[i] * 100:.0f}%" for i in order[:6]) + f"  best-fitting key {name} ({fit:.2f})"]
    if key:
        root, mode = key
        scale = {(root + st) % 12 for st in STEPS[mode]}
        outside = [i for i in order if i not in scale]
        out.append(f"against {PC[root]} {mode}: {sum(share[i] for i in outside) * 100:.0f}% of the pitch energy is outside the scale ("
                   + " ".join(f"{PC[i]} {share[i] * 100:.0f}%" for i in outside[:3]) + f"); the tonic ranks {order.index(root) + 1} of 12")
    if bv.sum() >= 8:
        cents = 100 * (bm[bv] - np.round(bm[bv]))
        d = np.abs(np.diff(bm))
        both = bv[1:] & bv[:-1]
        glide = (d > 0.15) & (d < 2.5) & both
        bpc = np.bincount(np.round(bm[bv]).astype(int) % 12, minlength=12) / bv.sum()
        bo = np.argsort(bpc)[::-1]
        out.append(f"bass (strongest partial 25-130 Hz): {np.mean(np.abs(cents) <= 25) * 100:.0f}% of sounding frames within 25 cents of a semitone, "
                   f"median {np.median(np.abs(cents)):.0f} cents off; moving in {glide.sum() / max(both.sum(), 1) * 100:.0f}% of frame pairs (glides, bends); on "
                   + " ".join(f"{PC[i]} {bpc[i] * 100:.0f}%" for i in bo[:4]))
    return out


def band_means(ld: np.ndarray, hz: np.ndarray, floor: float, sel=None) -> list[float]:
    x = np.maximum(ld if sel is None else ld[:, sel], floor)
    return [float(x[(hz >= lo) & (hz < hi)].mean()) for lo, hi in BANDS]


def band_hot(ld: np.ndarray, hz: np.ndarray, top: float, sel=None) -> list[float]:
    """share of each band's cells within 14 dB of the track's top: the yellow in the Hz panel"""
    x = ld if sel is None else ld[:, sel]
    return [float((x[(hz >= lo) & (hz < hi)] > top - 14).mean()) for lo, hi in BANDS]


def balance_line(ld: np.ndarray, hz: np.ndarray, top: float, loud: np.ndarray) -> str:
    """band balance over the loud part only, so intros, breakdowns and tails do not dilute it"""
    means = band_means(ld, hz, top - 70, loud)
    hot = band_hot(ld, hz, top, loud)
    lab = ["20-60", "60-250", "250-1k", "1k-4k", "4k-20k"]
    return (f"balance, loud part ({loud.mean() * 100:.0f}% of the track, frames within 10 dB of the 90th-percentile RMS): "
            + " | ".join(f"{l} {m - max(means):+.1f} dB, {h * 100:.0f}% hot" for l, m, h in zip(lab, means, hot))
            + "  (mean level per log-frequency band against the loudest band; hot = within 14 dB of the track's top, the yellow in the Hz panel)")


def _clock(x: float, bar_s: float | None, first_bar: int) -> str:
    return f"{int(x // 60)}:{int(x % 60):02d}" + (f" (bar {int(x / bar_s) + first_bar})" if bar_s else "")


def _runs(mask: np.ndarray, t: np.ndarray, least: float) -> list[tuple[float, float]]:
    out, s = [], None
    for i, m in enumerate(mask):
        if m and s is None:
            s = i
        if (not m or i == len(mask) - 1) and s is not None:
            e = i if not m else i + 1
            if t[min(e, len(t) - 1)] - t[s] >= least:
                out.append((float(t[s]), float(t[min(e, len(t) - 1)])))
            s = None
    return out


def summary(path, out, st, t, rms, corr, sd, top, infra, chroma, bm, bv, key, wa, bpm, first_bar) -> list[str]:
    bar_s = 240 / bpm if bpm else None
    when = lambda x: _clock(x, bar_s, first_bar)
    dur = len(st) / SR
    pk = float(np.max(np.abs(st)))
    mono = st.mean(axis=1)
    lines = [f"{Path(path).name}  {_clock(dur, None, 1)}  peak {20 * np.log10(pk + 1e-12):.1f} dBFS  rms {20 * np.log10(np.sqrt(np.mean(mono ** 2)) + 1e-12):.1f} dBFS",
             f"look: {out}"]
    tot = chroma.sum(axis=0)
    share = tot / max(tot.sum(), 1e-12)
    k = parse_key(key)
    if k:
        root, mode = k
        scale = {(root + s) % 12 for s in STEPS[mode]}
        lines.append(f"key: {PC[root]} {mode}, {sum(share[i] for i in range(12) if i not in scale) * 100:.0f}% of the pitch energy outside it")
    else:
        name, fit = key_fit(tot)
        lines.append(f"key: {name} fits best ({fit:.2f})")
    segs = sorted(wa["segs"], key=lambda s: -s["dur"])
    flags = []
    if wa["score"] >= wash.HAZE[1]:
        flags.append(f"wash {wa['score']:.1f} ({wash.verdict(wa['score'])})" + (f", longest stretch {when(segs[0]['start'])}-{when(segs[0]['end'])} ({segs[0]['dur']:.0f} s)" if segs else ""))
    full = np.abs(st) >= 0.999
    if pk >= 0.999 and int(np.sum(full[1:] & full[:-1])):
        flags.append(f"clipping: {int(np.sum(full[1:] & full[:-1]))} consecutive full-scale samples")
    if infra > INFRA_WARN:
        flags.append(f"{infra * 100:.0f}% of the energy below 20 Hz")
    lvl = 20 * np.log10(rms)
    p90 = np.percentile(lvl, 90)
    up = lvl > p90 - 30
    last = t[np.nonzero(up)[0][-1]] if up.any() else 0.0
    end = t[-1] + HOP / SR
    if end - last > 4:
        flags.append(f"the last {end - last:.0f} s sit more than 30 dB under the piece (from {when(last)})")
    quiet = (lvl < p90 - 40) & (t > t[0] + 1) & (t < last)
    for s, e in _runs(quiet, t, 1.5)[:3]:
        flags.append(f"near-silence {when(s)}, {e - s:.1f} s")
    for s, e in _runs(corr < -0.2, t, 1.0)[:3]:
        flags.append(f"out of phase {when(s)}, {e - s:.1f} s")
    if bv.sum() >= 8 and np.mean(np.abs(100 * (bm[bv] - np.round(bm[bv]))) <= 25) < 0.7:
        flags.append("bass often off the semitone grid (detail has the figure)")
    lines.append("flags: " + ("; ".join(flags) if flags else "none"))
    return lines


def analyse(path: str, start: float, end: float | None, bpm: float | None, out: Path, first_bar: int,
            key: str | None = None, bars: bool = False, detail: bool = False):
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
    fig, ax = plt.subplots(6, 1, figsize=(width, 18), sharex=True, gridspec_kw={"height_ratios": [5, 2.2, 3, 1.3, 1, 1.3]})
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
    wa = wash.analyse(np.clip(sd - top, -60, 0).T, SR / HOP)
    ax[5].plot(wa["t"] + start, wa["ghost"], lw=0.9, color="crimson")
    ax[5].axhline(wash.THR, color="grey", lw=0.6, ls="--")
    for sg in wa["segs"]:
        ax[5].axvspan(start + sg["start"], start + sg["end"], color="crimson", alpha=0.12, lw=0)
    ax[5].set_ylim(0, 50)
    ax[5].set_ylabel("ghost %")
    ax[5].set_xlabel("seconds")
    hz = 440 * 2 ** ((logc - 69) / 12)
    bm, bv = bass_track(P)
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
            span = 1 if bars else 8
            sel = (t >= x) & (t < x + span * bar_s)
            if (b - b0) % span == 0 and sel.sum() >= 2:
                c = chroma[sel].sum(axis=0)
                share = c / max(c.sum(), 1e-12)
                topk = np.argsort(share)[::-1][:3]
                r = rms[sel]
                bl = band_means(ld, hz, lt - 70, sel)
                bh = band_hot(ld, hz, lt, sel)
                bs = sel & bv
                grid = np.mean(np.abs(100 * (bm[bs] - np.round(bm[bs]))) <= 25) * 100 if bs.any() else float("nan")
                where = f"bar {b + first_bar:3}" + ("" if bars else f"-{b + first_bar + 7:<3}")
                rows.append(f"{where}  {' '.join(f'{PC[i]:2}{share[i] * 100:3.0f}%' for i in topk)}  sounding {(chroma_n[sel] > LIT).sum(axis=1).mean():.1f}"
                            f"  bass on-grid {grid:3.0f}%  bands {' '.join(f'{v - max(bl):+5.1f}' for v in bl)}  hot {'/'.join(f'{h * 100:.0f}' for h in bh)}"
                            f"  rms {20 * np.log10(np.sqrt(np.mean(r ** 2))):6.1f} dBFS  corr {corr[sel].mean():+.2f}")
            b += 1
    fig.suptitle(f"{Path(path).name}  {start:.1f}-{start + dur:.1f} s" + (f"  {bpm} BPM" if bpm else ""), fontsize=11)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=100)
    plt.close(fig)
    integ = 20 * np.log10(np.sqrt(np.mean(mono ** 2)) + 1e-12)
    full = [f"{out}  {dur:.1f} s  rms {integ:.1f} dBFS  peak {20 * np.log10(np.max(np.abs(st)) + 1e-12):.1f} dBFS  corr mean {corr.mean():+.2f}"]
    f = np.fft.rfftfreq(N_FFT, 1 / SR)
    infra = float(P[:, f < 20].sum() / max(P.sum(), 1e-12))
    full.append(f"below 20 Hz {infra * 100:.1f}% of the energy" + (
        f"  WARNING: inaudible energy above {INFRA_WARN * 100:g}%; it costs the limiter headroom. A sound may sit octaves "
        f"under its written note: render one note of each low sound and read its lowest partial" if infra > INFRA_WARN else ""))
    full += pitch_lines(chroma, chroma_n, bm, bv, parse_key(key))
    fr = 20 * np.log10(rms)
    full.append(balance_line(ld, hz, lt, fr > np.percentile(fr, 90) - 10))
    full += wash.lines(wa, start, 240 / bpm if bpm else None, first_bar)
    m, s = st[:, 0] + st[:, 1], st[:, 0] - st[:, 1]
    full.append(f"side/mid {10 * np.log10((s ** 2).sum() / max((m ** 2).sum(), 1e-12)):.1f} dB")
    if rows:
        full.append(f"per {'bar' if bars else '8 bars'} (a grid at {bpm:g} BPM; tempo automation is not followed): top pitch classes, classes sounding, "
                    "bass frames within 25 cents, bands 20-60/60-250/250-1k/1k-4k/4k-20k against the loudest and % hot in each, rms, corr")
    full += rows
    out.with_suffix(".txt").write_text("\n".join(full) + "\n", encoding="utf-8")
    if detail:
        print("\n".join(full))
    else:
        print("\n".join(summary(path, out, st, t, rms, corr, sd, top, infra, chroma, bm, bv, key, wa, bpm, first_bar)))
        print(f"detail: {out.with_suffix('.txt')}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=None)
    ap.add_argument("--bpm", type=float, default=None)
    ap.add_argument("--first-bar", type=int, default=1)
    ap.add_argument("--out", default=None)
    ap.add_argument("--key", default=None, help="the intended key, e.g. 'F minor' or 'G#m': reports the pitch energy outside its scale")
    ap.add_argument("--bars", action="store_true", help="rows per bar instead of per 8 bars")
    ap.add_argument("--detail", action="store_true", help="print the full report instead of the summary; it is always written beside the picture as .txt")
    a = ap.parse_args()
    name = Path(a.path).stem + (f"_{a.start:g}-{a.end:g}" if a.end else "")
    analyse(a.path, a.start, a.end, a.bpm, Path(a.out) if a.out else Path("tmp/spectro") / f"{name}.png", a.first_bar, a.key, a.bars, a.detail)
