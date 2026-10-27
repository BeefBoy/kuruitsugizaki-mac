"""Wash: notes that leave a fading copy still sounding under the next ones. Works on spectro.py's semitone panel."""
import numpy as np

THR = 30.0
WIN = 4.0
GAP = 6.0
HEAD = 12.0
DRIFT = 2.0
SCORE = 18.0
HAZE = (6.0, 16.0)
# play and wait: a hit, then its tail rings out with nothing new under it until the next hit. Those seconds count half.
JUMP = 6.0      # dB the density (mean over all semitones) rises within 0.15 s: a hit
WAIT = 1.5      # s between hits, at least
DROP = 12.0     # dB the density falls from the hit's peak before the next hit
RERISE = 3.0    # dB of re-rise allowed on the way down; more means something new came in
BRIDGE = 1.0    # s: a shorter gap between two waited ones (a chord struck twice) joins them


def _flatten(r, fps):
    lvl = np.sort(r, axis=1)[:, -8:].mean(1)
    k = max(1, int(2 * fps))
    slow = np.convolve(np.pad(lvl, k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), "valid")
    return np.clip(r - (slow - slow.max())[:, None], -60, 0), lvl


def _dropouts(lvl, fps, fall=10, within=0.5, hold=2.0, texture=0.2):
    k, h = int(within * fps), int(hold * fps)
    bad = np.zeros(len(lvl), bool)
    for t in range(k, len(lvl)):
        if lvl[t - k:t].max() - lvl[t] > fall:
            bad[t:t + h] = True
    return bad if bad.mean() <= texture else np.zeros(len(lvl), bool)


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


def _waits(r, fps):
    """frames inside a waited-out gap: from a hit to the next, the density (mean dB over all semitones) falls steadily
    by DROP or more with no re-rise over RERISE, up to the next hit's attack"""
    d = np.convolve(r.mean(1), np.ones(3) / 3, "same")
    T = len(d)
    k = max(1, int(0.15 * fps))
    hits = []
    for t in range(1, T):
        if d[t] - d[max(0, t - k):t].min() >= JUMP and (not hits or t - hits[-1] > 0.4 * fps):
            hits.append(t)
    gaps = []
    for a, b in zip(hits, hits[1:] + [T]):
        if b - a < WAIT * fps:
            gaps.append((a, b, False))
            continue
        p = a + int(np.argmax(d[a:a + int(0.5 * fps)]))
        seg = d[p:max(p + 1, b - int(0.3 * fps))]   # up to the next hit's attack, which rises a little early
        rerise = float((seg - np.minimum.accumulate(seg)).max())
        gaps.append((a, b, rerise < RERISE and d[p] - seg.min() >= DROP))
    w = np.zeros(T, bool)
    for i, (a, b, ok) in enumerate(gaps):
        if ok or (b - a <= BRIDGE * fps and 0 < i < len(gaps) - 1 and gaps[i - 1][2] and gaps[i + 1][2]):
            w[a:b] = True
    return w


def analyse(r, fps):
    """r: frames x semitones, dB under the track's top, clipped to -60..0. Returns the timeline, segments and score."""
    dur = len(r) / fps
    waited = _waits(r, fps)
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
        i0, i1 = int(s * fps), int(min(e, dur) * fps)
        wait = float(waited[i0:i1].mean()) if i1 > i0 else 0.0
        y = gh[np.searchsorted(t, s - 3):np.searchsorted(t, e - WIN + 3) + 1]
        rate = (np.nanmax(y[3:] - y[:-3]) - np.nanmin(y[3:] - y[:-3])) / 6 if len(y) > 3 else 0.0
        steep = min(1.0, DRIFT / rate) if rate > 0 else 1.0
        segs.append(dict(start=s, end=e, dur=d, rate=float(rate), steep=float(steep), waited=wait,
                         weight=1.0 if cover >= 0.5 else float(_weight(d)) * steep, ghost=float(np.nanmean(gh[sel])), head=float(np.nanmedian(hd[sel])) if np.isfinite(hd[sel]).any() else float("nan")))
    whole = 100 * ghost[live].sum() / max(1, live.sum())
    return dict(t=t + WIN / 2, ghost=gh, head=hd, segs=segs, cover=100 * cover, whole=whole, waited=waited,
                score=100 * sum(s["weight"] * s["dur"] * (1 - 0.5 * s["waited"]) for s in segs) / dur if dur else 0)


def verdict(score):
    if score > SCORE:
        return "WASH"
    if score >= HAZE[1]:
        return "haze to wash"
    return "haze" if score >= HAZE[0] else "clear"


def lines(a, start=0.0, bar_s=None, first_bar=1):
    where = (lambda x: f"{start + x:.0f}s" + (f" (bar {int((start + x) / bar_s) + first_bar})" if bar_s else ""))
    out = [f"wash: ghost {a['whole']:.1f}% of sounding cells, {a['cover']:.0f}% of the track in stretches over {THR:g}%, "
           f"score {a['score']:.1f} {verdict(a['score'])} (under {HAZE[0]:g} clear, {HAZE[0]:g}-{HAZE[1]:g} haze, over {SCORE:g} wash)  (ghost = a pitch still fading 0.5 s after its last onset; score = stretches weighted by length "
           f"(under 10 s near 0, 20 s half, 30 s nearly full) and by how fast ghost climbs into and falls out of them "
           f"(a wash drifts under {DRIFT:g} points/s, a section change jumps; weight x {DRIFT:g}/rate above that), "
           f"all full once they cover half the track; seconds where a hit rings out with nothing new under its tail before the next "
           f"(play and wait) count half; head = how far fresh notes "
           f"stand over the ghosts in dB, under {HEAD:g} reads as wash, over it as a held haze)"]
    for s in a["segs"]:
        tag = "wash" if s["head"] == s["head"] and s["head"] < HEAD else "haze"
        out.append(f"  {where(s['start'])}-{where(s['end'])}  {s['dur']:.0f} s  ghost {s['ghost']:.0f}%  edges {s['rate']:.1f} pt/s  weight {s['weight']:.2f}  waited {s['waited'] * 100:.0f}%  head {s['head']:.1f} dB  {tag}")
    return out
