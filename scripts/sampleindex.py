"""An index of sample folders, kept in tmp/samples/index/: every audio file under a folder with its size and modified time,
all from listing folders, no file opened. A later call stats each folder and relists only those whose modified time moved
(a file added, removed or renamed in it). A file's length is read from its header only when asked for (lengths), and kept."""
import hashlib
import json
import os
import re
import struct
from pathlib import Path

import pick

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "tmp" / "samples" / "index"
AUDIO = {".wav", ".wv", ".flac", ".aif", ".aiff", ".mp3", ".ogg"}
WV_RATES = [6000, 8000, 9600, 11025, 12000, 16000, 22050, 24000, 32000, 44100, 48000, 64000, 88200, 96000, 192000]
_CACHE: dict[str, dict] = {}


def seconds(path) -> float | None:
    """Length from the file's header: WAV, AIFF, FLAC, WavPack. None for anything else or a header it cannot read."""
    try:
        with open(path, "rb") as f:
            head = f.read(12)
            if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
                byterate = None
                while len(h := f.read(8)) == 8:
                    cid, size = h[:4], struct.unpack("<I", h[4:])[0]
                    if cid == b"fmt ":
                        byterate = struct.unpack("<HHIIHH", f.read(16))[3]
                        f.seek(size - 16 + (size & 1), 1)
                    elif cid == b"data":
                        return size / byterate if byterate else None
                    else:
                        f.seek(size + (size & 1), 1)
                return None
            if head[:4] == b"FORM" and head[8:12] in (b"AIFF", b"AIFC"):
                while len(h := f.read(8)) == 8:
                    cid, size = h[:4], struct.unpack(">I", h[4:])[0]
                    if cid == b"COMM":
                        c = f.read(18)
                        frames = struct.unpack(">I", c[2:6])[0]
                        exp, mant = struct.unpack(">HQ", c[8:18])
                        rate = mant * 2.0 ** ((exp & 0x7FFF) - 16383 - 63)
                        return frames / rate if rate else None
                    f.seek(size + (size & 1), 1)
                return None
            if head[:4] == b"fLaC":
                si = f.read(4 + 34)[4:]
                x = int.from_bytes(si[10:18], "big")
                rate, total = x >> 44, x & ((1 << 36) - 1)
                return total / rate if rate and total else None
            if head[:4] == b"wvpk":
                b = head + f.read(20)
                low = struct.unpack("<I", b[12:16])[0]
                idx = (struct.unpack("<I", b[24:28])[0] >> 23) & 0xF
                if idx < len(WV_RATES) and low != 0xFFFFFFFF:
                    return (low + (b[11] << 32)) / WV_RATES[idx]
    except (OSError, struct.error):
        pass
    return None


def _file(root: Path) -> Path:
    slug = re.sub(r"[^\w.-]+", "_", root.name)[:40] or "root"
    return DIR / f"{slug}-{hashlib.sha1(str(root).lower().encode()).hexdigest()[:8]}.json"


def _save(idx: dict) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    _file(Path(idx["root"])).write_text(json.dumps({"root": idx["root"], "dirs": idx["dirs"]}, ensure_ascii=False), encoding="utf-8")


def load(root, refresh: bool = False) -> dict:
    """{root, dirs: {rel: {mtime, files: {name: [size, mtime] or [size, mtime, seconds]}, subdirs, links}}, relisted}.
    rel uses / and '' is the root. links are the subdirs that are symlinks or junctions."""
    root = Path(root)
    key = str(root).lower()
    old = {}
    if not refresh:
        if key in _CACHE:
            old = _CACHE[key]["dirs"]
        elif _file(root).exists():
            try:
                old = json.loads(_file(root).read_text(encoding="utf-8")).get("dirs", {})
            except (OSError, ValueError):
                old = {}
    new, seen, relisted = {}, set(), 0
    stack = [("", os.path.realpath(root).lower())]
    while stack:
        rel, real = stack.pop()
        if real in seen:
            continue
        seen.add(real)
        d = root / rel if rel else root
        try:
            mt = os.stat(d).st_mtime_ns
        except OSError:
            continue
        prev = old.get(rel)
        if prev and prev.get("mtime") == mt:
            new[rel] = prev
        else:
            relisted += 1
            was = (prev or {}).get("files", {})
            files, subs, links = {}, [], []
            try:
                entries = list(os.scandir(d))
            except OSError:
                entries = []
            for e in entries:
                try:
                    if e.is_dir():
                        subs.append(e.name)
                        if e.is_symlink() or e.is_junction():
                            links.append(e.name)
                    elif os.path.splitext(e.name)[1].lower() in AUDIO:
                        st = e.stat()
                        w = was.get(e.name)
                        files[e.name] = w if w and w[0] == st.st_size and w[1] == st.st_mtime_ns else [st.st_size, st.st_mtime_ns]
                except OSError:
                    continue
            new[rel] = {"mtime": mt, "files": files, "subdirs": sorted(subs, key=str.lower), "links": links}
        links = set(new[rel].get("links", []))
        for s in new[rel]["subdirs"]:
            child = f"{rel}/{s}" if rel else s
            stack.append((child, os.path.realpath(d / s).lower() if s in links else f"{real}\\{s.lower()}"))
    idx = {"root": str(root), "dirs": new, "relisted": relisted}
    if relisted or set(new) != set(old):
        _save(idx)
    _CACHE[key] = idx
    return idx


def lengths(idx: dict, rows: list[tuple], save: bool = True) -> dict:
    """Seconds for (rel dir, name) rows, read from the header the first time and kept in the index (written to disk
    unless save is False; then idx["unsaved"] is set and the caller saves)."""
    root, out, read = Path(idx["root"]), {}, 0
    for rel, name in rows:
        f = idx["dirs"].get(rel, {}).get("files", {}).get(name)
        if f is None:
            continue
        if len(f) < 3:
            s = seconds(root / rel / name if rel else root / name)
            f.append(round(s, 3) if s is not None else None)
            read += 1
        out[(rel, name)] = f[2]
    if read and save:
        save_index(idx)
    elif read:
        idx["unsaved"] = True
    return out


def save_index(idx: dict) -> None:
    _save(idx)
    idx.pop("unsaved", None)


def totals(idx: dict, rel: str) -> dict:
    """Audio files and folders under rel, all levels."""
    files = folders = 0
    pre = rel + "/" if rel else ""
    for k, v in idx["dirs"].items():
        if k == rel or k.startswith(pre):
            files += len(v["files"])
            folders += k != rel
    return {"files": files, "folders": folders}


def tree(idx: dict, rel: str, cap: int) -> tuple[dict, int]:
    """The folders below rel at every level, {path below rel: audio files through all its levels}, at most cap of them:
    whole levels from the shallowest, and the level that does not fit shared out across its parents by pick.grouped, so
    every parent shows some of its folders; and how many folders there are in all."""
    pre = rel + "/" if rel else ""
    below = [k for k in idx["dirs"] if k != rel and k.startswith(pre)]
    count = dict.fromkeys(below, 0)
    for k in below:
        n = len(idx["dirs"][k]["files"])
        if not n:
            continue
        parts = k[len(pre):].split("/")
        for i in range(1, len(parts) + 1):
            count[pre + "/".join(parts[:i])] += n
    levels: dict[int, list[str]] = {}
    for k in below:
        levels.setdefault(k.count("/"), []).append(k)
    order: list[str] = []
    for depth in sorted(levels):
        level = sorted(levels[depth], key=str.lower)
        left = cap - len(order)
        if len(level) <= left:
            order += level
            continue
        by_parent: dict[str, list[str]] = {}
        for k in level:
            by_parent.setdefault(k.rsplit("/", 1)[0] if "/" in k else "", []).append(k)
        order += pick.grouped(list(by_parent.values()), left)
        break
    return {k[len(pre):]: count[k] for k in sorted(order, key=str.lower)}, len(below)


def search(idx: dict, under: str = "", words: list[str] | None = None) -> list[tuple]:
    """(rel dir, name) under rel whose path below the root holds every word, case-insensitive."""
    pre = under + "/" if under else ""
    words = [w.lower() for w in words or []]
    out = []
    for k, v in idx["dirs"].items():
        if not (k == under or k.startswith(pre)) or not v["files"]:
            continue
        here = re.sub(r"[/\\_\-.]+", " ", k.lower())
        need = [w for w in words if w not in here]
        for name in v["files"]:
            if need:
                text = re.sub(r"[_\-.]+", " ", name.lower())
                if any(w not in text for w in need):
                    continue
            out.append((k, name))
    return sorted(out, key=lambda r: (r[0].lower(), r[1].lower()))
