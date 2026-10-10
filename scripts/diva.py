import csv
import re
import sys
from pathlib import Path

import config



def parse(text: str) -> tuple[dict, dict]:
    meta = dict(re.findall(r"^(\w+):\s*\n'(.*?)'", text.split("*/", 1)[0], re.M | re.S)) if text.lstrip().startswith("/*@Meta") else {}
    body = text.split("$$$$", 1)[0]
    secs, cur = {}, None
    for line in body.splitlines():
        if line.startswith("#cm="):
            cur = secs.setdefault(line[4:].strip(), {})
        elif cur is not None and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            cur[k.strip()] = v.strip().strip("'")
        elif line.startswith("#") and "=" in line and cur is not None:
            k, v = line[1:].split("=", 1)
            cur["#" + k] = v.strip()
    return meta, secs


def row(text: str) -> dict:
    meta, s = parse(text)
    g = lambda sec, k: s.get(sec, {}).get(k, "")
    fx = [g(f"FX{i}", "Module") for i in (1, 2) if g("main", f"#FX{i}") not in ("", "0")]
    return {
        "bank": meta.get("Bank", ""),
        "author": meta.get("Author", ""),
        "usage": meta.get("Usage", "").replace("\\r\\n", " / ").replace("\n", " ")[:80],
        "osc": g("OSC", "Model"),
        "vcf": g("VCF1", "Model"),
        "cutoff": g("VCF1", "Freq"),
        "res": g("VCF1", "Res"),
        "hpf": g("HPF", "Freq"),
        "mode": g("VCC", "Mode"),
        "voices": g("VCC", "Voices"),
        "trsp": g("VCC", "Trsp"),
        "env2": "/".join(g("ENV2", k) for k in ("Atk", "Dec", "Sus", "Rel")),
        "arp": g("ARP", "OnOff"),
        "fx": " ".join(fx),
    }


def catalog(out: str, root: Path | None = None) -> tuple[int, int]:
    root = Path(root) if root else config.path("diva_presets")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows, bad = [], 0
    for p in sorted(root.rglob("*.h2p")):
        base = {"folder": p.parent.relative_to(root).as_posix(), "name": p.stem}
        try:
            rows.append({**base, **row(p.read_text(encoding="utf-8", errors="replace")), "error": "", "path": str(p)})
        except Exception as e:
            bad += 1
            rows.append({**base, "error": repr(e)[:120], "path": str(p)})
    fields = ["folder", "name"] + list(row("").keys()) + ["error", "path"]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows), bad


if __name__ == "__main__":
    n, bad = catalog(sys.argv[2] if len(sys.argv) > 2 else "tmp/diva.tsv")
    print(n, "presets,", bad, "unreadable")
