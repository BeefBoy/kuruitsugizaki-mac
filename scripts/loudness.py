import argparse, math, subprocess

import numpy as np

SR = 44100


def load(p, sr=SR, ch=2):
    raw = subprocess.run(["ffmpeg", "-v", "quiet", "-i", str(p), "-f", "f32le", "-ac", str(ch), "-ar", str(sr), "-"], capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
    return x.reshape(-1, ch) if ch > 1 else x


def kweight(x, fs=SR):
    f0, G, Q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    K = math.tan(math.pi * f0 / fs)
    Vh = 10 ** (G / 20)
    Vb = Vh ** 0.4996667741545416
    a0 = 1 + K / Q + K * K
    b1 = [(Vh + Vb * K / Q + K * K) / a0, 2 * (K * K - Vh) / a0, (Vh - Vb * K / Q + K * K) / a0]
    a1 = [1, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0]
    f0, Q = 38.13547087602444, 0.5003270373238773
    K = math.tan(math.pi * f0 / fs)
    d = 1 + K / Q + K * K
    a2 = [1, 2 * (K * K - 1) / d, (1 - K / Q + K * K) / d]
    b2 = [1, -2, 1]
    from scipy.signal import lfilter
    return lfilter(b2, a2, lfilter(b1, a1, x, axis=0), axis=0)


def lufs(x):
    y = kweight(x)
    n, hop = int(0.4 * SR), int(0.1 * SR)
    z = np.array([np.mean(np.sum(y[i:i + n] ** 2, axis=1)) for i in range(0, len(y) - n, hop)])
    l = -0.691 + 10 * np.log10(z + 1e-20)
    g = z[l > -70]
    rel = -0.691 + 10 * np.log10(g.mean()) - 10
    integ = -0.691 + 10 * np.log10(z[(l > -70) & (l > rel)].mean())
    n3 = int(3 * SR)
    st = np.array([-0.691 + 10 * np.log10(np.mean(np.sum(y[i:i + n3] ** 2, axis=1)) + 1e-20) for i in range(0, len(y) - n3, hop)])
    st = st[st > integ - 20]
    lra = np.percentile(st, 95) - np.percentile(st, 10) if len(st) > 2 else 0.0
    return integ, l.max(), lra


def true_peak(x):
    from scipy.signal import resample_poly
    return 20 * np.log10(np.abs(resample_poly(x, 4, 1, axis=0)).max() + 1e-12)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("files", nargs="+")
    a = p.parse_args()
    for f in a.files:
        x = load(f)
        i, m, lra = lufs(x)
        tp = true_peak(x)
        rms = 10 * np.log10(np.mean(x ** 2) + 1e-20)
        print(f"{f}\n  integrated {i:6.1f} LUFS  max momentary {m:6.1f}  LRA {lra:4.1f} LU  true peak {tp:+5.2f} dBTP  rms {rms:6.1f} dBFS  PLR {tp - i:4.1f}")


if __name__ == "__main__":
    main()
