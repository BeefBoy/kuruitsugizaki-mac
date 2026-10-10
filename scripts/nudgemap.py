import json
import os
import shutil
import sys
import time
from pathlib import Path

import flp
import serum2
from server import fl

LO, HI = 0.25, 0.75
SKIP = ("bank", "program", "preset", "patch", "midi cc")
EMPTY_RUN = 16
SENTINELS = 12


def ex(code: str, timeout: float = 120.0):
    r = fl({"op": "exec", "code": code}, timeout)
    if not r.get("ok"):
        raise RuntimeError(r.get("error"))
    return r["value"]


def snapshot(ch: int) -> dict:
    return ex(f"import plugins\nn = plugins.getParamCount({ch})\n"
              f"result = {{'n': n, 'names': [plugins.getParamName(p, {ch}) for p in range(n)], "
              f"'vals': [plugins.getParamValue(p, {ch}) for p in range(n)]}}")


def bound(names: list[str]) -> int:
    for p in range(len(names)):
        if all(not (names[q] or "").strip() for q in range(p, min(len(names), p + EMPTY_RUN))):
            return p
    return len(names)


def scan(ch: int, eligible: list[int], sentinels: list[int]) -> list[dict]:
    code = f"""import plugins
ch, elig, sent = {ch}, {eligible!r}, {sentinels!r}
names0 = dict((s, plugins.getParamName(s, ch)) for s in sent)
hits = []
for p in elig:
    orig = plugins.getParamValue(p, ch)
    for v in ({LO}, {HI}):
        plugins.setParamValue(v, p, ch)
        moved = [s for s in sent if plugins.getParamName(s, ch) != names0[s]]
        plugins.setParamValue(orig, p, ch)
        if moved:
            hits.append({{'p': p, 'v': v, 'moved': moved}})
            break
result = hits
"""
    return ex(code, 300)


def park(ch: int, values: dict[int, float], sentinels: list[int], names: list[str]) -> dict:
    code = f"""import plugins
ch, vals = {ch}, {json.dumps({str(k): v for k, v in values.items()})}
stuck = []
for k, v in vals.items():
    p = int(k)
    plugins.setParamValue(v, p, ch)
    if abs(plugins.getParamValue(p, ch) - v) > 1e-4:
        stuck.append(p)
sent = {json.dumps({str(s): names[s] for s in sentinels})}
result = {{'stuck': stuck, 'moved': [int(s) for s, n in sent.items() if plugins.getParamName(int(s), ch) != n]}}
"""
    return ex(code, 300)


def save_and_wait(path: Path) -> bool:
    m0 = path.stat().st_mtime_ns
    ex("import transport, midi\nresult = transport.globalTransport(midi.FPT_Save, 1)")
    for _ in range(100):
        time.sleep(0.1)
        if path.stat().st_mtime_ns != m0 and ex("import general\nresult = general.getChangedFlag()") == 0:
            time.sleep(0.3)
            return True
    return False


def state(path: Path, name: str) -> dict:
    for c in serum2.channels(flp.parse(path.read_bytes())):
        if c["name"] == name:
            return {**{"P" + k: v for k, v in serum2.leaves(c["processor"])},
                    **{"C" + k: v for k, v in serum2.leaves(c["controller"])}}
    raise KeyError(name)


def run(project: str, ch: int, chname: str, out: str) -> None:
    path = Path(project)
    work = Path("tmp/nudgemap")
    work.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    snap = snapshot(ch)
    names, vals = [n or "" for n in snap["names"]], snap["vals"]
    b = bound(names)
    eligible = [p for p in range(b) if names[p].strip() and not any(s in names[p].lower() for s in SKIP)]
    skipped = [(p, names[p]) for p in range(b) if names[p].strip() and p not in eligible]
    print(f"getParamCount {snap['n']}, plugin block 0..{b - 1}, eligible {len(eligible)}, skipped by name {skipped}")
    step = max(1, len(eligible) // SENTINELS)
    sentinels = eligible[::step][:SENTINELS]
    hits = scan(ch, eligible, sentinels)
    print(f"scan {time.time() - t0:.1f}s: {len(hits)} repointers {[(h['p'], names[h['p']], h['v']) for h in hits]}")
    rep = {h["p"] for h in hits}
    eligible = [p for p in eligible if p not in rep]
    sentinels = [s for s in sentinels if s not in rep]
    shutil.copy(path, work / "before.flp")
    base = state(work / "before.flp", chname)
    bits = max(1, (len(eligible) - 1).bit_length())
    plans = [("L", lambda k: 0), ("H", lambda k: 1)]
    plans += [(f"b{j}", (lambda j: lambda k: (k >> j) & 1)(j)) for j in range(bits)]
    plans += [("c_par", lambda k: bin(k).count("1") & 1), ("c_mod3", lambda k: int(k % 3 == 0))]
    states, parked = {}, {}
    for tag, f in plans:
        pattern = {p: (HI if f(k) else LO) for k, p in enumerate(eligible)}
        r = park(ch, pattern, sentinels, names)
        ok = save_and_wait(path)
        shutil.copy(path, work / f"{tag}.flp")
        states[tag] = state(work / f"{tag}.flp", chname)
        parked[tag] = {k: f(k) for k in range(len(eligible))}
        print(f"  {tag:7} saved={ok} stuck={len(r['stuck'])} moved={r['moved']} keys={len(states[tag])}  {time.time() - t0:.1f}s")
    park(ch, {p: vals[p] for p in eligible}, sentinels, names)
    save_and_wait(path)
    after = state(path, chname)
    restore_diff = [k for k in set(base) | set(after) if base.get(k, "<absent>") != after.get(k, "<absent>")]
    print(f"restored: {len(restore_diff)} leaves differ from before {sorted(restore_diff)[:8]}")
    A = "<absent>"
    keys = sorted(set().union(*[set(s) for s in states.values()]))
    mapping, odd, dead = {}, [], 0
    for key in keys:
        vl, vh = states["L"].get(key, A), states["H"].get(key, A)
        if vl == vh:
            dead += 1
            continue
        seen, bad = {}, False
        for tag in states:
            v = states[tag].get(key, A)
            seen[tag] = 1 if v == vh else 0 if v == vl else None
        if any(x is None for x in seen.values()):
            odd.append((key, "third value", {t: states[t].get(key, A) for t in states}))
            continue
        k = sum(seen[f"b{j}"] << j for j in range(bits))
        if k >= len(eligible) or any(seen[c] != parked[c][k] for c in ("c_par", "c_mod3")):
            odd.append((key, f"check failed k={k}", seen))
            continue
        p = eligible[k]
        mapping.setdefault(p, []).append({"key": key, "lo": vl, "hi": vh})
    unmapped = [(p, names[p]) for p in eligible if p not in mapping]
    print(f"keys {len(keys)}: {dead} unresponsive, {sum(len(v) for v in mapping.values())} mapped to {len(mapping)} params, {len(odd)} odd")
    print(f"eligible params with no key: {len(unmapped)}")
    res = {"project": project, "channel": ch, "lo": LO, "hi": HI, "block": b, "repointers": hits,
           "mapping": {str(p): {"name": names[p], "default_norm": vals[p], "keys": v} for p, v in sorted(mapping.items())},
           "unmapped": unmapped, "odd": odd, "restore_diff": sorted(restore_diff)}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(res, indent=1, default=repr), encoding="utf-8")
    print(f"wrote {out} in {time.time() - t0:.1f}s")


def canary_ref(ch: int, canaries: list[int], xs: list[float]) -> dict:
    ref = {}
    for x in xs:
        for c in canaries:
            ex(f"import plugins\nplugins.setParamValue({x}, {c}, {ch})\nresult = 0")
            time.sleep(0.06)
            ref[(c, x)] = ex(f"import plugins\nresult = plugins.getParamValueString({c}, {ch})")
    return ref


def settled_displays(ch: int, group: list[int], x: float, canaries: list[int], ref: dict, log: list) -> dict:
    order = [canaries[0]] + group[:len(group) // 2] + [canaries[1]] + group[len(group) // 2:] + [canaries[2]]
    wiggle = x - 1e-3 if x >= 0.5 else x + 1e-3
    for v in (x, wiggle, x):
        ex(f"import plugins\nfor q in {order!r}:\n    plugins.setParamValue({v}, q, {ch})\nresult = 0")
        time.sleep(0.06)
    t0 = time.time()
    while time.time() - t0 < 1.0:
        time.sleep(0.05)
        got = ex(f"import plugins\nresult = [plugins.getParamValueString(c, {ch}) for c in {canaries!r}]")
        if all(g == ref[(c, x)] for g, c in zip(got, canaries)):
            return ex(f"import plugins\nresult = dict((p, plugins.getParamValueString(p, {ch})) for p in {group!r})")
    if len(group) == 1:
        log.append((x, group[0]))
        return {group[0]: None}
    mid = len(group) // 2
    out = {}
    for half in (group[:mid], group[mid:]):
        ex(f"import plugins\nfor q in {group + canaries!r}:\n    plugins.setParamValue(0.5, q, {ch})\nresult = 0")
        time.sleep(0.05)
        out.update(settled_displays(ch, half, x, canaries, ref, log))
    return out


def run_curves(project: str, ch: int, chname: str, hostmap: str, out: str, steps: int = 16, canaries: tuple = (205, 1, 440)) -> None:
    path = Path(project)
    work = Path("tmp/nudgemap")
    hm = json.loads(Path(hostmap).read_text(encoding="utf-8"))
    params = sorted(int(p) for p in hm["mapping"])
    snap = snapshot(ch)
    names, vals = [n or "" for n in snap["names"]], snap["vals"]
    sentinels = params[::max(1, len(params) // SENTINELS)][:SENTINELS]
    xs = [i / steps for i in range(steps + 1)]
    t0 = time.time()
    canaries = list(canaries)
    ref = canary_ref(ch, canaries, xs)
    others = [p for p in params if p not in canaries]
    curves = {p: [] for p in params}
    unreadable = []
    for i, x in enumerate(xs):
        r = park(ch, {p: x for p in params}, sentinels, names)
        ok = save_and_wait(path)
        shutil.copy(path, work / f"curve_{i:02d}.flp")
        st = state(work / f"curve_{i:02d}.flp", chname)
        disp = settled_displays(ch, others, x, canaries, ref, unreadable)
        for c in canaries:
            disp[c] = ref[(c, x)]
        for p in params:
            d = disp.get(p, disp.get(str(p)))
            curves[p].append([x, None if d is None else d.strip(),
                              {k["key"]: st.get(k["key"], "<absent>") for k in hm["mapping"][str(p)]["keys"]}])
        print(f"  x={x:.4f} saved={ok} stuck={len(r['stuck'])} moved={r['moved']} unreadable so far={len(unreadable)}  {time.time() - t0:.1f}s")
    hm_init = {int(p): v["default_norm"] for p, v in hm["mapping"].items()}
    park(ch, {p: hm_init.get(p, vals[p]) for p in params}, sentinels, names)
    save_and_wait(path)
    res = {"canaries": canaries, "unreadable": [(x, p, names[p]) for x, p in unreadable],
           "params": {p: {"name": hm["mapping"][str(p)]["name"], "default_norm": vals[p], "points": curves[p]} for p in params}}
    Path(out).write_text(json.dumps(res, indent=1, default=repr), encoding="utf-8")
    print(f"wrote {out}: {len(params)} params x {len(xs)} points in {time.time() - t0:.1f}s; unreadable {res['unreadable']}")


if __name__ == "__main__":
    if sys.argv[1] == "curves":
        run_curves(sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5], sys.argv[6])
    else:
        run(sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4])
