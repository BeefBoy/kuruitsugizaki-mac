import csv
import struct
import sys
from pathlib import Path

import config

STATE_SIZE = 2707
NAME_FIELDS = (("pack", 16, 1040), ("preset", 1041, 2065))


def directory(path: str | Path) -> tuple[int, list[tuple[str, int, int]], int]:
    with open(path, "rb") as fh:
        def take(size):
            data = fh.read(size)
            if len(data) != size:
                raise ValueError(f"truncated FLEX pack directory: {path}")
            return data

        version, count = struct.unpack(">II", take(8))
        if version != 2:
            raise ValueError(f"unsupported FLEX pack version {version}: {path}")
        entries = []
        for _ in range(count):
            length, = struct.unpack(">I", take(4))
            name = take(length).rstrip(b"\0").decode("utf-8")
            offset, size = struct.unpack(">QQ", take(16))
            entries.append((name, offset, size))
        return version, entries, fh.tell()


def apply(state213: bytes, preset_path: str) -> bytes:
    pack, separator, preset = preset_path.partition("/")
    if not separator or not pack or not preset or any(c in pack + preset for c in "\0\\/:") or pack in (".", ".."):
        raise ValueError("FLEX preset must be '<pack>/<preset>'")
    if len(state213) != STATE_SIZE:
        raise ValueError(f"FLEX state must be {STATE_SIZE} bytes, got {len(state213)}")
    fields = []
    for name, (label, start, end) in zip((pack, preset), NAME_FIELDS):
        encoded = name.encode("utf-8")
        if len(encoded) >= end - start:
            raise ValueError(f"FLEX {label} name needs {len(encoded)} UTF-8 bytes; maximum is {end - start - 1}")
        fields.append((start, end, encoded))
    path = config.path("flex_packs") / f"{pack}.flexpack"
    if not path.is_file():
        raise FileNotFoundError(f"FLEX pack does not exist: {path}")
    _, entries, _ = directory(path)
    if not any(name == f"{preset}.flexpreset" for name, _, _ in entries):
        raise ValueError(f"FLEX preset {preset!r} is not in pack {pack!r}")
    out = bytearray(state213)
    for start, end, encoded in fields:
        out[start:end] = encoded.ljust(end - start, b"\0")
    return bytes(out)


def catalog(out: str, root: Path | None = None) -> int:
    root = Path(root) if root else config.path("flex_packs")
    out = Path(out)
    rows = []
    for path in sorted(Path(root).glob("*.flexpack")):
        _, entries, _ = directory(path)
        for name, _, size in entries:
            if name.endswith(".flexpreset"):
                preset = name.removesuffix(".flexpreset")
                rows.append((path.stem, preset, size, f"{path.stem}/{preset}"))
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerow(("pack", "name", "bytes", "preset"))
        writer.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    if sys.argv[1:2] != ["catalog"] or len(sys.argv) > 3:
        raise SystemExit("usage: flex.py catalog [out.tsv]")
    print(catalog(sys.argv[2] if len(sys.argv) > 2 else "tmp/flex.tsv"), "presets")
