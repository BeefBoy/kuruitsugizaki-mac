import csv
import re
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np

import pick

AUDIO = {".wav", ".mp3", ".flac", ".ogg", ".aif", ".aiff"}
KEY = re.compile(r"(?<![A-Za-z])([A-G])\s?([#b♭♯]?)\s?(m(?:in(?:or)?)?|maj(?:or)?|\s(?:minor|major))?(?![A-Za-z])")
BPM = re.compile(r"(\d{2,3})\s?bpm", re.I)


def read_wav(path: Path):
    b = path.read_bytes()
    if b[:4] != b"RIFF" or b[8:12] != b"WAVE":
        return None
    i, fmt, data = 12, None, None
    while i + 8 <= len(b):
        cid, sz = b[i:i + 4], struct.unpack("<I", b[i + 4:i + 8])[0]
        if cid == b"fmt ":
            fmt = struct.unpack("<HHIIHH", b[i + 8:i + 24])
            if fmt[0] == 0xFFFE and sz >= 40:
                fmt = (struct.unpack("<H", b[i + 32:i + 34])[0],) + fmt[1:]
        if cid == b"data":
            data = b[i + 8:i + 8 + sz]
        i += 8 + sz + (sz & 1)
    if not fmt or data is None:
        return None
    tag, ch, rate, _, align, bits = fmt
    n = len(data) // align
    raw = data[:n * align]
    if tag == 3 and bits == 32:
        x = np.frombuffer(raw, "<f4").astype(np.float64)
    elif tag == 1 and bits == 16:
        x = np.frombuffer(raw, "<i2") / 32768.0
    elif tag == 1 and bits == 24:
        a = np.frombuffer(raw, np.uint8).reshape(-1, 3)
        x = ((a[:, 0].astype(np.int32) | (a[:, 1].astype(np.int32) << 8) | (a[:, 2].astype(np.int32) << 16)) << 8 >> 8) / 8388608.0
    elif tag == 1 and bits == 32:
        x = np.frombuffer(raw, "<i4") / 2147483648.0
    elif tag == 1 and bits == 8:
        x = (np.frombuffer(raw, np.uint8).astype(np.float64) - 128) / 128.0
    else:
        return None
    return rate, x.reshape(-1, ch), f"{tag}/{bits}"


def read_any(path: Path):
    r = read_wav(path) if path.suffix.lower() == ".wav" else None
    if r:
        return r
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", "44100", "pipe:1"], capture_output=True).stdout
    if not raw:
        return None
    return 44100, np.frombuffer(raw, "<f4").astype(np.float64).reshape(-1, 2), "ffmpeg"


def measure(path: Path) -> dict:
    r = read_any(path)
    if r is None:
        return {"name": path.name, "note": "unreadable"}
    rate, x, fmt = r
    ch = x.shape[1]
    mono = x.mean(axis=1)
    dur = len(mono) / rate
    pk = float(np.abs(x).max()) if len(x) else 0.0
    rms = float(np.sqrt(np.mean(mono ** 2))) if len(mono) else 0.0
    width = ""
    if ch >= 2:
        m, s = x[:, 0] + x[:, 1], x[:, 0] - x[:, 1]
        width = round(10 * np.log10((s ** 2).sum() / max((m ** 2).sum(), 1e-20) + 1e-20), 1)
    w = max(1, int(rate * 0.01))
    env = np.sqrt(np.convolve(mono ** 2, np.ones(w) / w, mode="valid")[::w]) if len(mono) > w else np.array([0.0])
    rise = (env[1:] > 2.2 * np.maximum(env[:-1], 1e-4)) & (env[1:] > 0.03)
    onsets = int(rise.sum())
    seg = mono[: min(len(mono), rate * 10)]
    if len(seg) > 2048:
        sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
        f = np.fft.rfftfreq(len(seg), 1 / rate)
        centroid = int((f * sp).sum() / max(sp.sum(), 1e-12))
    else:
        centroid = 0
    stem = path.stem
    bpm = BPM.search(stem)
    key = KEY.findall(re.sub(BPM, "", stem))
    return {
        "name": path.name, "dur": round(dur, 2), "ch": ch, "rate": rate, "fmt": fmt,
        "bpm": bpm.group(1) if bpm else "", "key": " ".join("".join(k).strip() for k in key[-1:]),
        "peak_db": round(20 * np.log10(pk + 1e-12), 1), "rms_db": round(20 * np.log10(rms + 1e-12), 1),
        "side_mid_db": width, "onsets_per_s": round(onsets / max(dur, 1e-3), 2), "centroid_hz": centroid,
    }


def catalog(folder: str, out: str | None = None):
    d = Path(folder)
    subdirs = sorted(p for p in d.iterdir() if p.is_dir())
    files = sorted(p for p in d.iterdir() if p.is_file() and p.suffix.lower() in AUDIO)
    rows = [measure(p) for p in files]
    out = Path(out or f"tmp/samples/{d.name}.tsv")
    out.parent.mkdir(parents=True, exist_ok=True)
    keys = ["name", "dur", "ch", "rate", "fmt", "bpm", "key", "peak_db", "rms_db", "side_mid_db", "onsets_per_s", "centroid_hz", "note"]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=keys, delimiter="\t", extrasaction="ignore")
        wr.writeheader()
        wr.writerows(rows)
    return subdirs, rows, out


if __name__ == "__main__":
    for folder in sys.argv[1:]:
        subdirs, rows, out = catalog(folder)
        durs = [r["dur"] for r in rows if "dur" in r]
        print(f"== {Path(folder).name}: {len(rows)} files -> {out}; subfolders: {[p.name for p in subdirs]}")
        if durs:
            print(f"   duration {min(durs):.2f}-{max(durs):.2f} s, median {sorted(durs)[len(durs) // 2]:.2f}; stereo {sum(1 for r in rows if r.get('ch') == 2)}/{len(rows)}; with bpm {sum(1 for r in rows if r.get('bpm'))}, with key {sum(1 for r in rows if r.get('key'))}")
        if len(rows) > 60:
            print(f"   60 of {len(rows)}, spread from first to last; all of them in {out}")
        for r in pick.even(rows, 60):
            if "dur" in r:
                print(f"   {r['name'][:52]:52} {r['dur']:7.2f}s ch{r['ch']} bpm {r['bpm'] or '-':>3} key {r['key'] or '-':>4} rms {r['rms_db']:6.1f} w {r['side_mid_db'] if r['side_mid_db'] != '' else '-':>6} on/s {r['onsets_per_s']:5.2f} c {r['centroid_hz']:>5}")
