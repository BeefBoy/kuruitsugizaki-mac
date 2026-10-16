"""Wash: notes that leave a fading copy still sounding under the next ones. Works on spectro.py's semitone panel."""
import numpy as np

THR = 30.0
WIN = 4.0
GAP = 6.0
HEAD = 12.0


def _flatten(r, fps):
    lvl = np.sort(r, axis=1)[:, -8:].mean(1)
    k = max(1, int(2 * fps))
    slow = np.convolve(np.pad(lvl, k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), "valid")
    return np.clip(r - (slow - slow.max())[:, None], -60, 0), lvl


def _dropouts(lvl, fps, fall=10, within=0.5, hold=2.0):
    k, h = int(within * fps), int(hold * fps)
    bad = np.zeros(len(lvl), bool)
    for t in range(k, len(lvl)):
        if lvl[t - k:t].max() - lvl[t] > fall:
            bad[t:t + h] = True
    return bad


def _grid(r, fps, hold=0.5, drop=3, rise=3, faint=-36):
    T, B = r.shape
    since = np.full(B, 1e9)
    peak = np.full(B, -99.0)
    ghost = np.zeros((T, B), bool)
    fresh = np.zeros((T, B), bool)
    for t in range(2, T):
        on = r[t] - r[t - 2] > rise
        since = np.where(on, 0, since + 1)
        peak = np.where(on, r[t], np.where(since / fps < 0.15, np.maximum(peak, r[t]), peak))
        ghost[t] = (since / fps >= hold) & (r[t] <= peak - drop) & (r[t] > faint)
        fresh[t] = (since / fps < hold) & (r[t] > faint)
    return ghost, fresh


def _weight(d):
    return 1 / (1 + np.exp(-(d - 20) / 5))


def analyse(r, fps):
    """r: frames x semitones, dB under the track's top, clipped to -60..0. Returns the timeline, segments and score."""
    dur = len(r) / fps
    r, lvl = _flatten(r, fps)
    ghost, fresh = _grid(r, fps)
    live = (r > -45) & ~_dropouts(lvl, fps)[:, None]
    w, h = max(1, int(WIN * fps)), max(1, int(fps))
    t, gh, hd = [], [], []
    for i in range(0, max(1, len(r) - w + 1), h):
        L = live[i:i + w]
        G, F = ghost[i:i + w] & L, fresh[i:i + w] & L
        t.append(i / fps)
        gh.append(100 * G.sum() / L.sum() if L.sum() > 0.05 * L.size else np.nan)
        hd.append(np.percentile(r[i:i + w][F], 90) - np.percentile(r[i:i + w][G], 50) if G.sum() >= 20 and F.sum() >= 20 else np.nan)
    t, gh, hd = np.array(t), np.array(gh), np.array(hd)
    spans, cur = [], None
    for ti, v in zip(t, gh):
        if v == v and v > THR:
            if cur and ti <= cur[1] + GAP:
                cur[1] = ti + WIN
            else:
                if cur:
                    spans.append(cur)
                cur = [ti, ti + WIN]
    if cur:
        spans.append(cur)
    cover = sum(e - s for s, e in spans) / dur if dur else 0
    segs = []
    for s, e in spans:
        sel = (t >= s) & (t + WIN <= e + 1e-6)
        d = e - s
        segs.append(dict(start=s, end=e, dur=d, weight=1.0 if cover >= 0.5 else float(_weight(d)),
                         ghost=float(np.nanmean(gh[sel])), head=float(np.nanmedian(hd[sel])) if np.isfinite(hd[sel]).any() else float("nan")))
    whole = 100 * ghost[live].sum() / max(1, live.sum())
    return dict(t=t + WIN / 2, ghost=gh, head=hd, segs=segs, cover=100 * cover, whole=whole,
                score=100 * sum(s["weight"] * s["dur"] for s in segs) / dur if dur else 0)


def lines(a, start=0.0, bar_s=None, first_bar=1):
    where = (lambda x: f"{start + x:.0f}s" + (f" (bar {int((start + x) / bar_s) + first_bar})" if bar_s else ""))
    out = [f"wash: ghost {a['whole']:.1f}% of sounding cells, {a['cover']:.0f}% of the track in stretches over {THR:g}%, "
           f"score {a['score']:.1f}  (ghost = a pitch still fading 0.5 s after its last onset; score = stretches weighted by length, "
           f"under 10 s near 0, 20 s half, 30 s nearly full, all full once they cover half the track; head = how far fresh notes "
           f"stand over the ghosts in dB, under {HEAD:g} reads as wash, over it as a held haze)"]
    for s in a["segs"]:
        tag = "wash" if s["head"] == s["head"] and s["head"] < HEAD else "haze"
        out.append(f"  {where(s['start'])}-{where(s['end'])}  {s['dur']:.0f} s  ghost {s['ghost']:.0f}%  weight {s['weight']:.2f}  head {s['head']:.1f} dB  {tag}")
    return out
