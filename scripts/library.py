import csv
import fnmatch
import json
import os
import re
import zlib
from pathlib import Path

import config as cfg
import flp
import mixerfx
from project import text, wrapper

ROOT = Path(__file__).resolve().parents[1]
PARAMS = ROOT / "docs" / "params"
STATES = ROOT / "tmp" / "states"
harvester = None
NAME = 201
STATE = 213
LABEL = 203
DB_FORMATS = {"Fruity": "native", "VST3": "vst3", "CLAP": "clap", "VST": "vst", "AU": "au"}
RANK = {"native": 0, "vst3": 1, "clap": 2, "vst": 3, "au": 4}
LOADERS = {("serum2", "vst3"): "serum2", ("vital", "vst3"): "vital", ("sylenth1", "vst3"): "sylenth1", ("diva(x64)", "vst3"): "diva", ("flex", "native"): "flex"}
LOADER_FILES = {"serum2": ("serum2_presets", ".SerumPreset"), "vital": ("vital_presets", ".vital"), "diva": ("diva_presets", ".h2p"), "sylenth1": ("sylenth1_presets", ".fxp")}
_cache: dict = {}


def name_text(e) -> str:
    d = e.data
    if len(d) % 2 == 0 and d.endswith(b"\0\0"):
        return d.decode("utf-16-le", "replace").rstrip("\0")
    return d.decode("latin-1").rstrip("\0")


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _abs(v) -> Path:
    p = Path(v)
    return p if p.is_absolute() else ROOT / p


def lib_path() -> Path | None:
    v = cfg.get("library")
    if not v:
        return None
    p = _abs(v)
    return p if p.exists() else None


def db_root() -> Path | None:
    v = cfg.get("plugin_db")
    if not v:
        return None
    p = _abs(v)
    return p if (p / "Installed").is_dir() or (p / "Generators").is_dir() else None


def _format(path: bytes) -> str:
    p = path.lower()
    return "vst3" if p.endswith(b".vst3") else "clap" if p.endswith(b".clap") else "au" if p.endswith(b".component") else "vst"


def identity(blk: list) -> dict:
    internal = next((text(e) for e in blk if e.id == NAME and len(e.data) > 2), "")
    st = next((e.data for e in blk if e.id == STATE), b"")
    if internal == "Fruity Wrapper" and st:
        w = wrapper(st)
        return {"name": w.get(54, b"").decode("latin-1"), "vendor": w.get(56, b"").decode("latin-1"), "format": _format(w.get(55, b""))}
    return {"name": internal, "vendor": "Image-Line", "format": "native"}


def _scan_library(path: Path) -> list[dict]:
    import writer
    _, lay = writer.load(str(path))
    out = []
    for blk in lay["channels"]:
        kind = next((int.from_bytes(e.data, "little") for e in blk if e.id == 21), None)
        if kind != 2:
            continue
        label = next((text(e) for e in blk if e.id == LABEL and len(e.data) > 2), "")
        out.append({**identity(blk), "kind": "instrument", "label": label, "channel": int.from_bytes(blk[0].data, "little"), "source": "library"})
    for fx in mixerfx.effects(lay["tail"]):
        blk = mixerfx.block(lay["tail"], fx["track"], fx["slot"])
        out.append({**identity(blk), "kind": "effect", "track": fx["track"], "slot": fx["slot"], "source": "library"})
    return out


def _db_dirs(root: Path) -> list[tuple[Path, str, str | None]]:
    # FL's Plugin Manager writes Installed/<kind>/<format>. Before its first scan (a fresh FL for Mac has none) only the
    # category tree <kind>/<category> exists; its format is read from each file (None).
    if not (root / "Installed").is_dir():
        return [(d, kind, None) for k, kind in (("Generators", "instrument"), ("Effects", "effect"))
                for d in sorted((root / k).iterdir()) if d.is_dir()] if (root / "Generators").is_dir() else []
    return [(root / "Installed" / k / f, kind, fmt) for k, kind in (("Generators", "instrument"), ("Effects", "effect"))
            for f, fmt in DB_FORMATS.items() if (root / "Installed" / k / f).is_dir()]


def _scan_db(root: Path) -> list[dict]:
    out, seen = [], set()
    for d, kind, fmt0 in _db_dirs(root):
        for f in sorted(d.glob("*.fst")):
            try:
                evs = flp.parse(f.read_bytes()).events
            except Exception:
                continue
            nm = next((name_text(e) for e in evs if e.id == NAME), "")
            st = next((e.data for e in evs if e.id == STATE), None)
            if not nm:
                continue
            if nm == "Fruity Wrapper":
                if not st:
                    continue
                w = wrapper(st)
                name, vendor = w.get(54, b"").decode("latin-1"), w.get(56, b"").decode("latin-1")
                fmt = fmt0 or _format(w.get(55, b""))
            else:
                name, vendor, fmt = nm, "Image-Line", fmt0 or "native"
            if name and (fmt0 or (kind, name.lower(), fmt) not in seen):
                seen.add((kind, name.lower(), fmt))
                out.append({"name": name, "kind": kind, "vendor": vendor, "format": fmt, "source": "fl", "fst": str(f), "alias": f.stem})
    return out


def _hider(db: Path | None, hide: list):
    names, pats = set(), []
    for h in hide:
        h = str(h).strip().lower()
        if h.startswith("category:"):
            cat = h.split(":", 1)[1].strip()
            if db and cat:
                names |= {f.stem.lower() for k in ("Generators", "Effects") if (db / k / cat).is_dir() for f in (db / k / cat).glob("*.fst")}
        elif h.split(":", 1)[0] in RANK and ":" in h:
            fmt, p = h.split(":", 1)
            pats.append((fmt, p.strip()))
        elif h:
            pats.append((None, h))
    def hidden(e: dict) -> bool:
        ns = [n for n in (e["name"].lower(), e.get("alias", "").lower()) if n]
        return any(n in names or any(f in (None, e["format"]) and fnmatch.fnmatchcase(n, p) for f, p in pats) for n in ns)
    return hidden


def entries() -> list[dict]:
    lib, db = lib_path(), db_root()
    hide = list(cfg.get("hide_plugins") or [])
    key = (str(lib), lib.stat().st_mtime_ns if lib else 0, str(db), max((d.stat().st_mtime_ns for d, _, _ in _db_dirs(db)), default=0) if db else 0, tuple(map(str, hide)))
    # Every tool call reloads this module, which replaces _cache with a new dict; a call running in parallel can
    # find its cache emptied between writing and reading it. So read once, build into locals, return the local.
    hit = _cache.get("entries")
    if _cache.get("key") == key and hit is not None:
        return hit
    own = _scan_library(lib) if lib else []
    seen = {(e["kind"], e["name"].lower(), e["format"]) for e in own}
    hidden = _hider(db, hide)
    fl = [e for e in (_scan_db(db) if db else []) if (e["kind"], e["name"].lower(), e["format"]) not in seen and not hidden(e)]
    allx = own + fl
    for e in allx:
        e["id"] = slug(e["name"])
    _cache.clear()
    _cache.update(key=key, entries=allx)
    return allx


def _rank(e: dict) -> tuple:
    return (0 if e["source"] == "library" else 1, RANK.get(e["format"], 9))


def find(query: str, kind: str | None = None, fmt: str | None = None, prefer: str | None = None) -> dict:
    q = query.strip().lower()
    pool = [e for e in entries() if (kind is None or e["kind"] == kind) and (fmt is None or e["format"] == fmt.lower())]
    tests = (lambda e: e["name"].lower() == q, lambda e: e["id"] == slug(q), lambda e: e.get("alias", "").lower() == q,
             lambda e: e.get("label", "").lower() == q, lambda e: q in e["name"].lower())
    for test in tests:
        hit = [e for e in pool if test(e)]
        if not hit:
            continue
        names = sorted({e["name"] for e in hit})
        if len({(e["kind"], e["name"].lower()) for e in hit}) == 1:
            return min(hit, key=_rank)
        if len({e["name"].lower() for e in hit}) == 1:
            if prefer in {e["kind"] for e in hit}:
                return min((e for e in hit if e["kind"] == prefer), key=_rank)
            raise KeyError(f"{names[0]!r} is both an instrument and an effect; pass kind='instrument' or kind='effect'")
        raise KeyError(f"{query!r} matches {len(names)} plugins: {_some(names, 12)}")
    where = " or ".join(x for x in ("FL's plugin database" if db_root() else "", "the library" if lib_path() else "") if x) or "nowhere: neither FL's plugin database (config plugin_db) nor a library (config library) was found"
    raise KeyError(f"{query!r} is not in {where}; plugins(query) lists what is")


def has(query: str, kind: str | None = None, fmt: str | None = None) -> bool:
    try:
        find(query, kind, fmt)
        return True
    except (KeyError, cfg.Missing, FileNotFoundError):
        return False


def _templates() -> dict:
    import writer
    from project import TEMPLATES
    tpl = _cache.get("tpl")
    if tpl is None:
        _, lay = writer.load(TEMPLATES)
        inst = next((b for b in lay["channels"] if next((int.from_bytes(e.data, "little") for e in b if e.id == 21), None) == 2), None)
        fx = None
        p = _abs(cfg.get("effect_template") or "projects/init/fx.flp")
        if p.exists():
            _, flay = writer.load(str(p))
            first = next(iter(mixerfx.effects(flay["tail"])), None)
            if first:
                fx = mixerfx.block(flay["tail"], first["track"], first["slot"])
        tpl = _cache["tpl"] = {"instrument": inst, "effect": fx, "effect_file": str(p)}
    return tpl


def _fresh(e: dict) -> list:
    tpl = _templates()[e["kind"]]
    if tpl is None:
        what = "a plugin channel in the template (config template)" if e["kind"] == "instrument" else f"an effect in {_templates()['effect_file']} (config effect_template)"
        raise KeyError(f"cannot build {e['name']}: no {what} to build it on")
    evs = flp.parse(Path(e["fst"]).read_bytes()).events
    # Older .fst files (some in FL for Mac's category tree) store the name in ASCII; a project wants UTF-16.
    nm = name_text(next(x for x in evs if x.id == NAME)).encode("utf-16-le") + b"\0\0"
    st = next((x.data for x in evs if x.id == STATE), None)
    out = []
    for x in tpl:
        if x.id == NAME:
            out.append(flp.Event(NAME, nm))
        elif x.id == STATE:
            if st is not None:
                out.append(flp.Event(STATE, st))
        elif x.id == LABEL:
            out.append(flp.Event(LABEL, e["name"].encode("utf-16-le") + b"\0\0"))
        else:
            out.append(flp.Event(x.id, x.data))
    return out


def block(e: dict) -> list:
    if e["source"] != "library":
        return _fresh(e)
    import writer
    if e["kind"] == "instrument":
        return writer.block_of(str(lib_path()), e["channel"])
    _, lay = writer.load(str(lib_path()))
    return mixerfx.block(lay["tail"], e["track"], e["slot"])


def _roots() -> list[tuple[str, Path]]:
    out = []
    for key, tag in (("fl_presets", ""), ("fl_user_presets", "user/")):
        v = cfg.get(key)
        if v and _abs(v).is_dir():
            out.append((tag, _abs(v)))
    return out


def _folder(root: Path, e: dict) -> Path | None:
    sub = root / ("Generators" if e["kind"] == "instrument" else "Effects")
    if not sub.is_dir():
        return None
    want = e["name"].lower() if e["format"] == "native" else f"fruity wrapper - {e['name'].lower()}"
    return next((d for d in sub.iterdir() if d.is_dir() and d.name.lower() == want), None)


def _vendor_defaults() -> dict:
    pd = Path(os.environ.get("ProgramData", r"C:\ProgramData"))
    ad = Path(os.environ.get("APPDATA", ""))
    return {"Krush": {"ext": ".tkpreset", "dirs": {"": str(pd / "Tritik" / "Krush")}},
            "Portal": {"ext": ".xml", "dirs": {"": str(pd / "Output" / "Portal" / "Presets")}},
            "spiff_x64": {"ext": ".preset", "dirs": {"": str(pd / "oeksound" / "spiff" / "Presets")}},
            "ShaperBox 3": {"ext": ".dat", "dirs": {"": str(ad / "Cableguys" / "ShaperBox3")}, "names": "inside"}}


def _program_name(f: Path) -> str | None:
    try:
        b = f.read_bytes()
        i = b.find(b"x\x9c")
        d = zlib.decompressobj().decompress(b[i:], 1 << 16) if b.startswith(b"#zip#") and i >= 0 else b
    except (OSError, zlib.error):
        return None
    m = re.search(rb"ProgramName\x00\x01.\x05([^\x00]*)\x00", d, re.S)
    return m.group(1).decode("utf-8", "replace") if m else None


def _vendor(e: dict) -> list[dict]:
    if e["format"] == "native":
        return []
    spec = (cfg.get("vst_presets") or {}).get(e["name"]) or _vendor_defaults().get(e["name"])
    if not spec:
        return []
    ext = spec.get("ext", "").lower()
    dirs = spec.get("dirs", {})
    out, seen = [], set()
    for tag, d in (dirs.items() if isinstance(dirs, dict) else (("", x) for x in dirs)):
        p = Path(d)
        if not p.is_dir():
            continue
        pre = f"{tag}/" if tag else ""
        for f in sorted(p.rglob("*")):
            if not f.is_file() or (ext and f.suffix.lower() != ext):
                continue
            if spec.get("names") == "inside":
                name = _program_name(f)
                if not name:
                    continue
                rid, k = pre + name, 2
                while rid.lower() in seen:
                    rid, k = f"{pre}{name} ({k})", k + 1
            else:
                rid = pre + f.relative_to(p).with_suffix("").as_posix()
            seen.add(rid.lower())
            out.append({"id": rid, "path": str(f)})
    return out


def loader(e: dict) -> str | None:
    return LOADERS.get((e["name"].lower(), e["format"])) if e["kind"] == "instrument" else None


def _loader_roots(key: str) -> list[Path]:
    if key == "flex":
        v = cfg.get("flex_packs")
        return [_abs(v)] if v and _abs(v).is_dir() else []
    return cfg.roots(LOADER_FILES[key][0])


def _files(roots: list[Path], pattern: str, folders=None) -> list[dict]:
    out = []
    for root in roots:
        pre = f"{root.name}/" if len(roots) > 1 else ""
        subs = [root / f for f in folders or [] if (root / f).is_dir()] or [root]
        for sub in subs:
            out += [{"id": pre + f.relative_to(root).with_suffix("").as_posix(), "path": str(f)} for f in sorted(sub.rglob(pattern)) if f.is_file()]
    return out


def _loader_rows(key: str) -> list[dict]:
    roots = _loader_roots(key)
    if not roots:
        return []
    if key == "flex":
        import flex
        out = []
        for p in sorted(roots[0].glob("*.flexpack")):
            try:
                _, ents, _ = flex.directory(p)
            except (ValueError, OSError):
                continue
            out += [{"id": f"{p.stem}/{n.removesuffix('.flexpreset')}", "path": f"{p.stem}/{n.removesuffix('.flexpreset')}"} for n, _, _ in ents if n.endswith(".flexpreset")]
        return out
    return _files(roots, "*" + LOADER_FILES[key][1], cfg.get("sylenth1_folders") if key == "sylenth1" else None)


def _nks_index() -> dict:
    hit = _cache.get("nks")
    if hit is not None:
        return hit
    import nks
    idx: dict = {}
    for row in _files(cfg.roots("nks_presets"), "*.nksf"):
        try:
            h = nks.header(row["path"])
        except Exception:
            continue
        for k in h["keys"]:
            idx.setdefault(k, []).append(row)
    _cache["nks"] = idx
    return idx


def _nks_rows(e: dict) -> list[dict]:
    if e["format"] != "vst3":
        return []
    import nks
    if e["source"] == "library":
        st = next((x.data for x in block(e) if x.id == STATE), b"")
    else:
        st = next((x.data for x in flp.parse(Path(e["fst"]).read_bytes()).events if x.id == STATE), b"")
    try:
        r52 = dict(wrapper_recs(st)).get(52)
    except ValueError:
        r52 = None
    idx, seen, out = _nks_index(), set(), []
    for k in nks.keys_for(r52, e["name"]):
        for row in idx.get(k, []):
            if row["path"] not in seen:
                seen.add(row["path"])
                out.append(row)
    return out


def wrapper_recs(st: bytes) -> list:
    import presets as P
    return P.split_wrapper(st)[1] if st else []


def _loader_path(key: str, preset: str) -> str:
    if key != "flex":
        p = Path(preset)
        for c in (p, ROOT / p):
            if c.is_file():
                return str(c)
    rows = _loader_rows(key)
    ext = "" if key == "flex" else LOADER_FILES[key][1].lower()
    want = preset.strip().replace("\\", "/").lower().removesuffix(ext).strip() if ext else preset.strip().lower()
    hit = [r for r in rows if r["id"].strip().lower() == want]
    if not hit:
        hit = [r for r in rows if r["id"].rsplit("/", 1)[-1].strip().lower() == want.rsplit("/", 1)[-1].strip()]
    if len(hit) == 1:
        return hit[0]["path"]
    if hit:
        raise KeyError(f"preset {preset!r} is ambiguous, {len(hit)} match: {_some([r['id'] for r in hit], 10)}")
    if key == "flex" and "/" in preset:
        return preset
    where = ", ".join(str(r) for r in _loader_roots(key)) or f"nowhere: no default folder found and config {'flex_packs' if key == 'flex' else LOADER_FILES[key][0]} is not set"
    raise KeyError(f"no preset {preset!r} in {where}; presets(plugin, query) searches its {len(rows)}")


def loader_preset(key: str, state: bytes, preset: str) -> bytes:
    import presets as P
    if key not in LOADER_FILES and key != "flex":
        return P.apply(key, state, preset)
    return P.apply(key, state, _loader_path(key, preset))


def programs_dir(e: dict) -> Path:
    return STATES / f"{e['kind']}_{e['id']}_{e['format']}.programs"


def _program_rows(e: dict) -> list[dict]:
    f = programs_dir(e) / "index.json"
    if not f.exists():
        return []
    out, seen = [], set()
    for r in json.loads(f.read_text(encoding="utf-8")):
        rid, k = r["name"], 2
        while rid.lower() in seen:
            rid, k = f"{r['name']} ({k})", k + 1
        seen.add(rid.lower())
        out.append({"id": rid, "path": str(programs_dir(e) / r["file"])})
    return out


def refresh(e: dict) -> bytes:
    import shutil
    f = STATES / f"{e['kind']}_{e['id']}_{e['format']}.bin"
    f.unlink(missing_ok=True)
    shutil.rmtree(programs_dir(e), ignore_errors=True)
    return saved_state(e)


def saved_state(e: dict) -> bytes:
    if e["source"] == "library":
        return next(x.data for x in block(e) if x.id == STATE)
    f = STATES / f"{e['kind']}_{e['id']}_{e['format']}.bin"
    if f.exists():
        return f.read_bytes()
    if harvester is None:
        raise KeyError(f"a {e['name']} preset loads into a saved instance of it, and none is cached in {STATES}; one is made once by opening {e['name']} in FL, which project_write does through the MCP server")
    st = harvester(e)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(st)
    return st


def catalog(e: dict) -> list[dict]:
    ck = ("catalog", e["kind"], e["name"], e["format"])
    hit = _cache.get(ck)
    if hit is not None:
        return hit
    out = []
    for tag, root in _roots():
        d = _folder(root, e)
        if d is None:
            continue
        for f in sorted(d.rglob("*.fst")):
            out.append({"id": tag + f.relative_to(d).with_suffix("").as_posix(), "path": str(f)})
    out += _vendor(e)
    if loader(e):
        out += _loader_rows(loader(e))
    out += _nks_rows(e)
    out += _program_rows(e)
    _cache[ck] = out
    return out


def presets(e: dict, query: str | None = None) -> list[dict]:
    rows = catalog(e)
    if not query:
        return rows
    words = query.lower().split()
    return [r for r in rows if all(w in r["id"].lower() for w in words)]


def _some(items: list, n: int) -> str:
    import pick
    return ", ".join(map(str, pick.even(items, n))) + (f" ({n} of {len(items)}, spread from first to last)" if len(items) > n else "")


def spread(rows: list[dict], n: int, seed: int | None = None) -> list[dict]:
    """n rows across their folders (the id up to its last /), by pick.grouped."""
    import random
    import pick
    if len(rows) <= n:
        return rows
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r["id"].rsplit("/", 1)[0] if "/" in r["id"] else "", []).append(r)
    return pick.grouped(list(groups.values()), n, random.Random(seed) if seed is not None else None)


def resolve_preset(e: dict, preset: str) -> Path:
    p = Path(preset)
    if p.is_absolute() and p.is_file():
        return p
    rows = catalog(e)
    want = preset.strip().lower().removesuffix(".fst")
    hit = [r for r in rows if r["id"].lower() == want]
    if not hit:
        hit = [r for r in rows if r["id"].lower().rsplit("/", 1)[-1] == want.rsplit("/", 1)[-1]]
    if len(hit) == 1:
        return Path(hit[0]["path"])
    if not rows:
        raise KeyError(f"{e['name']} has no presets: none saved from FL as .fst and no vendor folder in config vst_presets; it loads in its initial state")
    if hit:
        raise KeyError(f"preset {preset!r} for {e['name']} is ambiguous, {len(hit)} match: {_some([r['id'] for r in hit], 10)}")
    raise KeyError(f"no preset {preset!r} for {e['name']}; presets(plugin, query) searches its {len(rows)}")


def preset_state(e: dict, preset: str) -> bytes:
    if loader(e):
        return loader_preset(loader(e), saved_state(e), preset)
    f = resolve_preset(e, preset)
    if f.suffix.lower() == ".bin" and STATES in f.parents:
        return f.read_bytes()
    if f.suffix.lower() == ".nksf":
        import nks
        import vst3state
        return vst3state.put_component(next(x.data for x in block(e) if x.id == STATE), nks.component(f))
    if f.suffix.lower() != ".fst":
        import vst3state
        return vst3state.apply_file(saved_state(e), f.read_bytes(), f.name)
    evs = flp.parse(f.read_bytes()).events
    names = [name_text(x) for x in evs if x.id == NAME and len(x.data) > 2]
    st = next((x.data for x in evs if x.id == STATE), None)
    if st is None:
        raise ValueError(f"{f} holds no plugin state")
    name = names[0] if names else ""
    if name == "Fruity Wrapper":
        name = wrapper(st).get(54, b"").decode("latin-1")
    if name and name.lower() != e["name"].lower():
        raise ValueError(f"{f} is a {name} preset, not {e['name']}")
    return st


def _state_at(blk: list, kind: str) -> int:
    tpl = _templates()[kind] or blk
    ids = [x.id for x in tpl]
    if STATE not in ids:
        return len(blk)
    later = set(ids[ids.index(STATE) + 1:]) - set(ids[:ids.index(STATE)])
    start = max((k for k, x in enumerate(blk) if x.id in (NAME, 212)), default=0) + 1
    return next((k for k in range(start, len(blk)) if blk[k].id in later), len(blk))


def with_preset(blk: list, e: dict, preset: str) -> list:
    st = preset_state(e, preset)
    if not any(x.id == STATE for x in blk):
        i = _state_at(blk, e["kind"])
        blk = blk[:i] + [flp.Event(STATE, b"")] + blk[i:]
    return [flp.Event(x.id, st if x.id == STATE else x.data) for x in blk]


def param_file(e: dict) -> Path:
    return PARAMS / f"{e['kind']}_{e['id']}.tsv"


def params(e: dict, query: str | None = None) -> list[dict]:
    f = param_file(e)
    if not f.exists():
        raise KeyError(f"{e['name']} has no parameter map yet ({f.name}); scripts/params_fl.py makes one")
    with f.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    if query:
        words = query.lower().split()
        rows = [r for r in rows if all(w in r["name"].lower() for w in words)]
    return rows


def summary(query: str | None = None, native: bool = False) -> list[dict]:
    out = []
    for e in entries():
        if query and query.lower() not in e["name"].lower():
            continue
        if not native and e["format"] == "native":
            continue
        row = {k: e[k] for k in ("name", "kind", "vendor", "format", "source")}
        row["presets"] = len(catalog(e))
        row["params"] = param_file(e).exists()
        out.append(row)
    return out
