import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

FX = ["chorus", "compressor", "delay", "distortion", "eq", "flanger", "phaser", "reverb", "filter_fx"]


def row(path: Path) -> dict:
    p = json.loads(path.read_text(encoding="utf-8"))
    s = p.get("settings", {})
    oscs = [i for i in (1, 2, 3) if s.get(f"osc_{i}_on", 0)]
    uni = max((s.get(f"osc_{i}_unison_voices", 1) for i in oscs), default=0)
    return {
        "name": path.stem,
        "style": p.get("preset_style", ""),
        "author": p.get("author", ""),
        "oscs": len(oscs),
        "sample": int(bool(s.get("sample_on", 0))),
        "unison": int(uni),
        "fx": " ".join(f for f in FX if s.get(f"{f}_on", 0)),
        "macros": " | ".join(p.get(f"macro{i}", "") for i in range(1, 5) if p.get(f"macro{i}")),
        "comments": (p.get("comments") or "").replace("\n", " ")[:80],
        "path": str(path),
    }


def build(folder: str, out: str):
    rows = []
    for f in sorted(Path(folder).glob("*.vital")):
        try:
            rows.append(row(f))
        except Exception as e:
            rows.append({"name": f.stem, "style": "UNREADABLE", "comments": repr(e)[:80], "path": str(f)})
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter="\t", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return rows


if __name__ == "__main__":
    rows = build(sys.argv[1], sys.argv[2])
    by = defaultdict(list)
    for r in rows:
        by[r.get("style") or "-"].append(r["name"])
    print(len(rows), "presets ->", sys.argv[2])
    for k, v in sorted(by.items(), key=lambda x: -len(x[1])):
        print(f"== {k} ({len(v)})")
        print("   " + " | ".join(v))
