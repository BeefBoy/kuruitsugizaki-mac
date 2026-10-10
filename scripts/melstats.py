import sys
from collections import Counter, defaultdict

sys.path.insert(0, "scripts")
import project

PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(name: str) -> int:
    i = 1
    pc = PC[name[0]]
    while name[i] in "#b":
        pc += 1 if name[i] == "#" else -1
        i += 1
    return pc + 12 * (int(name[i:]) + 1)


def tick(at) -> int:
    b, beat, t = at
    return (b - 1) * 384 + (beat - 1) * 96 + t


def load(f: str):
    d = project.export(f"projects/{f}.flp")
    names = {c["id"]: (c["name"], c.get("plugin") or c["kind"]) for c in d["instruments"]}
    pats = {}
    for p in d["patterns"]:
        rows = defaultdict(list)
        for n in p["notes"]:
            rows[n["inst"]].append((tick(n["at"]), n["len"], midi(n["key"]), n["vel"]))
        pats[p["id"]] = {k: sorted(v) for k, v in rows.items()}
    return d, names, pats


def overview(f: str):
    d, names, pats = load(f)
    print("==", f, d["project"].get("bpm"), "patterns", len(pats), "arr", [(a["name"], len(a["clips"])) for a in d["arrangements"]])
    agg = defaultdict(lambda: {"n": 0, "lo": 999, "hi": 0, "poly": 0, "pats": 0})
    for pid, rows in pats.items():
        for inst, ns in rows.items():
            a = agg[inst]
            a["n"] += len(ns)
            a["pats"] += 1
            a["lo"] = min(a["lo"], min(m for _, _, m, _ in ns))
            a["hi"] = max(a["hi"], max(m for _, _, m, _ in ns))
            a["poly"] = max(a["poly"], max(sum(1 for s2, l2, _, _ in ns if s2 <= s < s2 + l2) for s, _, _, _ in ns))
    for inst, a in sorted(agg.items(), key=lambda x: -x[1]["n"]):
        nm, pl = names.get(inst, ("?", "?"))
        print(f"  {inst[:18]:18} {nm[:24]:24} {str(pl)[:12]:12} notes {a['n']:4} midi {a['lo']}-{a['hi']} maxpoly {a['poly']} pats {a['pats']}")


NM = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def nm(m: int) -> str:
    return f"{NM[m % 12]}{m // 12 - 1}"


def dump(f: str):
    d, names, pats = load(f)
    print("==", f, d["project"].get("bpm"))
    for pid, rows in pats.items():
        for inst, ns in rows.items():
            print(f" [{pid}] {inst}")
            line = []
            for s, l, m, v in ns:
                pos = f"{s // 384 + 1}.{(s % 384) / 24:g}"
                line.append(f"{pos}:{nm(m)}/{l / 24:g}")
            for i in range(0, len(line), 12):
                print("   ", " ".join(line[i:i + 12]))


if __name__ == "__main__":
    fn = dump if sys.argv[1] == "dump" else overview
    for f in sys.argv[2:]:
        fn(f)
