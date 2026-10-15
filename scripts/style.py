"""A list of a person's projects from a folder of .flp: tempo, key and arrangement length of each, so a
model knows which projects to open and read in full. Reads only; writes profile.md and profile.json to
tmp/profile/<folder name>/.
"""
import json
import math
import re
import sys
from pathlib import Path

import flp
import project
from view import PARKED, midi, tick

BAR = 384
KITS = {"FPC", "Addictive Drums 2", "Kickstart 2", "Battery 4", "Fruity slicer", "Slicex"}
DRUM = r"kick|kck|\bbd\b|bassdrum|808|snare|snr|\bsd\b|\brim|clap|clp|\b[foc]?hats?\b|hihat|hi hat|\bhh\b|\boh\b|\bch\b|shaker|crash|\bride\b|cymbal|perc|\btoms?\b|conga|bongo"
PROFILES = {  # Krumhansl-Kessler
    "major": [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88],
    "minor": [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17],
}
PC = "C C# D D# E F F# G G# A A# B".split()


def key_of(pcs: list[float]) -> tuple[str, float]:
    if sum(pcs) == 0:
        return "?", 0.0
    best = ("?", -2.0)
    for mode, prof in PROFILES.items():
        for t in range(12):
            x = pcs[t:] + pcs[:t]
            mx, my = sum(x) / 12, sum(prof) / 12
            num = sum((a - mx) * (b - my) for a, b in zip(x, prof))
            den = math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in prof)) or 1
            if num / den > best[1]:
                best = (f"{PC[t]} {mode}", num / den)
    return best[0], round(best[1], 2)


def drum(c: dict) -> bool:
    if (c.get("plugin") or "") in KITS:
        return True
    name = (Path((c.get("path") or "").replace("\\", "/")).name + " " + c.get("name", "")).lower().replace("_", " ").replace("-", " ")
    return c.get("kind") in ("sampler", "audio") and bool(re.search(DRUM, name))


def one(path: Path, root: Path) -> dict:
    raw = path.read_bytes()
    d = project.export(str(path))
    out = {"file": path.relative_to(root).as_posix(), "bpm": d["project"].get("bpm"),
           "flags": [] if flp.serialize(flp.parse(raw)) == raw else ["does not round-trip"]}
    chans = {c["id"]: c for c in d["instruments"] + d["samples"]}
    pcs = [0.0] * 12
    for pt in d["patterns"]:
        for n in pt["notes"]:
            c = chans.get(n["inst"])
            if c is not None and not drum(c):
                pcs[midi(n["key"]) % 12] += n["len"]
    out["key"], out["key_fit"] = key_of(pcs)
    arrs = sorted(d["arrangements"], key=lambda a: -len(a["clips"]))
    clips = [c for c in (arrs[0]["clips"] if arrs else []) if tick(c["at"]) < PARKED]
    bad = [c for c in clips if not 1 <= c["track"] <= 500 or c["len"] > BAR * 2000]
    if bad:
        out["flags"].append(f"{len(bad)} clips off the playlist or absurdly long")
    end = max((tick(c["at"]) + c["len"] for c in clips if c not in bad), default=0)
    out["bars"] = math.ceil(end / BAR)
    out["path"] = str(path.resolve())
    return out


def markdown(rows: list[dict], errors: dict, root: Path) -> str:
    L = [f"# Projects in {root.name}", "", f"{len(rows)} read" + (f", {len(errors)} not read" if errors else "") + ".", "",
         "## Projects", "", "| file | BPM | key (fit) | bars |", "|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: r["file"].lower()):
        flag = f" ({'; '.join(r['flags'])})" if r["flags"] else ""
        L.append(f"| {r['file']}{flag} | {r['bpm']:g} | {r['key']} ({r['key_fit']}) | {r['bars']} |")
    for f, e in sorted(errors.items()):
        L.append(f"| {f} (not read: {e}) | | | |")
    return "\n".join(L) + "\n"


def build(folder: str, out_dir: str | None = None) -> dict:
    root = Path(folder).resolve()
    files = sorted(root.rglob("*.flp"))
    if not files:
        raise ValueError(f"no .flp under {root}")
    rows, errors = [], {}
    for f in files:
        try:
            rows.append(one(f, root))
        except Exception as e:
            errors[f.relative_to(root).as_posix()] = repr(e)[:200]
    out = Path(out_dir) if out_dir else Path(__file__).resolve().parent.parent / "tmp" / "profile" / root.name
    out.mkdir(parents=True, exist_ok=True)
    md = markdown(rows, errors, root)
    (out / "profile.json").write_text(json.dumps({"folder": str(root), "projects": rows, "not_read": errors}, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "profile.md").write_text(md, encoding="utf-8")
    return {"json": str(out / "profile.json"), "md": str(out / "profile.md"), "read": len(rows), "not_read": len(errors), "profile": md}


if __name__ == "__main__":
    import os
    folder = str(Path(sys.argv[1]).resolve())
    out = str(Path(sys.argv[2]).resolve()) if len(sys.argv) > 2 else None
    os.chdir(Path(__file__).resolve().parent.parent)  # project.py opens the template relative to the repo, as the server does
    r = build(folder, out)
    print(r["profile"])
    print(f"wrote {r['json']} and {r['md']}")
