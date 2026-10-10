import struct
import sys


def read(path: str):
    b = open(path, "rb").read()
    i, fmt, data = 12, None, None
    while i + 8 <= len(b):
        cid, sz = b[i:i + 4], struct.unpack("<I", b[i + 4:i + 8])[0]
        if cid == b"fmt ":
            fmt = struct.unpack("<HHIIHH", b[i + 8:i + 24])
        if cid == b"data":
            data = b[i + 8:i + 8 + sz]
        i += 8 + sz + (sz & 1)
    tag, ch, rate, _, align, bits = fmt
    n = len(data) // align
    if tag == 3 or (tag == 0xFFFE and bits == 32):
        vals = struct.unpack(f"<{n * ch}f", data[:n * align])
    elif bits == 16:
        vals = [v / 32768 for v in struct.unpack(f"<{n * ch}h", data[:n * align])]
    elif bits == 24:
        vals = [int.from_bytes(data[k:k + 3], "little", signed=True) / 8388608 for k in range(0, n * align, 3)]
    else:
        raise ValueError(f"format {tag} bits {bits}")
    mono = [sum(vals[k:k + ch]) / ch for k in range(0, len(vals), ch)]
    return rate, mono, tag, bits


def onsets(path: str, win_ms: float = 5.0, ratio: float = 2.2, floor: float = 0.02):
    rate, x, tag, bits = read(path)
    w = max(1, int(rate * win_ms / 1000))
    env, zcr = [], []
    for k in range(0, len(x) - w, w):
        seg = x[k:k + w]
        env.append(sum(abs(v) for v in seg) / w)
        zcr.append(sum(1 for a, b in zip(seg, seg[1:]) if (a < 0) != (b < 0)) / w)
    hits, last = [], -999
    for k in range(2, len(env)):
        prev = max(1e-6, (env[k - 1] + env[k - 2]) / 2)
        if env[k] > floor and env[k] / prev > ratio and k - last > 12:
            peak = max(env[k:k + 8])
            z = sum(zcr[k:k + 10]) / 10
            hits.append((round(k * win_ms, 1), round(peak, 3), round(z * rate / 2)))
            last = k
    return rate, len(x) / rate, tag, bits, hits


if __name__ == "__main__":
    for p in sys.argv[1:]:
        rate, dur, tag, bits, hits = onsets(p)
        print(p.split("/")[-1], f"{dur:.3f}s rate {rate} fmt {tag}/{bits}", len(hits), "hits")
        for t, pk, z in hits:
            print(f"   {t:8.1f} ms  peak {pk:.3f}  zc_hz {z}")
