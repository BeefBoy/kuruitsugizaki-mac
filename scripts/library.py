import csv
import re
from pathlib import Path

import config as cfg
import flp
import mixerfx
from project import text, wrapper

ROOT = Path(__file__).resolve().parents[1]
PARAMS = ROOT / "docs" / "params"
NAME = 201
STATE = 213
LABEL = 203
DB_FORMATS = {"Fruity": "native", "VST3": "vst3", "CLAP": "clap", "VST": "vst"}
RANK = {"native": 0, "vst3": 1, "clap": 2, "vst": 3}
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
    return p if (p / "Installed").is_dir() else None


def _format(path: bytes) -> str:
    p = path.lower()
    return "vst3" if p.endswith(b".vst3") else "clap" if p.endswith(b".clap") else "vst"


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


def _db_dirs(root: Path) -> list[tuple[Path, str, str]]:
    return [(root / "Installed" / k / f, kind, fmt) for k, kind in (("Generators", "instrument"), ("Effects", "effect"))
            for f, fmt in DB_FORMATS.items() if (root / "Installed" / k / f).is_dir()]


def _scan_db(root: Path) -> list[dict]:
    out = []
    for d, kind, fmt in _db_dirs(root):
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
            else:
                name, vendor = nm, "Image-Line"
            if name:
                out.append({"name": name, "kind": kind, "vendor": vendor, "format": fmt, "source": "fl", "fst": str(f), "alias": f.stem})
    return out


def entries() -> list[dict]:
    lib, db = lib_path(), db_root()
    key = (str(lib), lib.stat().st_mtime_ns if lib else 0, str(db), max((d.stat().st_mtime_ns for d, _, _ in _db_dirs(db)), default=0) if db else 0)
    # Every tool call reloads this module, which replaces _cache with a new dict; a call running in parallel can
    # find its cache emptied between writing and reading it. So read once, build into locals, return the local.
    hit = _cache.get("entries")
    if _cache.get("key") == key and hit is not None:
        return hit
    own = _scan_library(lib) if lib else []
    seen = {(e["kind"], e["name"].lower(), e["format"]) for e in own}
    fl = [e for e in (_scan_db(db) if db else []) if (e["kind"], e["name"].lower(), e["format"]) not in seen]
    allx = own + fl
    for e in allx:
        e["id"] = slug(e["name"])
    _cache.clear()
    _cache.update(key=key, entries=allx)
    return allx


def _rank(e: dict) -> tuple:
    return (0 if e["source"] == "library" else 1, RANK.get(e["format"], 9))


def find(query: str, kind: str | None = None, fmt: str | None = None) -> dict:
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
        raise KeyError(f"{query!r} matches {len(names)} plugins: {names[:12]}")
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
    nm = next(x.data for x in evs if x.id == NAME)
    st = next((x.data for x in evs if x.id == STATE), None)
    out = []
    for x in tpl:
        if x.id == NAME:
            out.append(flp.Event(NAME, nm))
        elif x.id == STATE:
            if st is not None:
                out.append(flp.Event(STATE, st))
        elif x.id == LABEL and e["kind"] == "instrument":
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


def _vendor(e: dict) -> list[dict]:
    spec = (cfg.get("vst_presets") or {}).get(e["name"])
    if not spec or e["format"] == "native":
        return []
    ext = spec.get("ext", "").lower()
    dirs = spec.get("dirs", {})
    out = []
    for tag, d in (dirs.items() if isinstance(dirs, dict) else (("", x) for x in dirs)):
        p = Path(d)
        if not p.is_dir():
            continue
        pre = f"{tag}/" if tag else ""
        for f in sorted(p.rglob("*")):
            if f.is_file() and (not ext or f.suffix.lower() == ext):
                out.append({"id": pre + f.relative_to(p).with_suffix("").as_posix(), "path": str(f)})
    return out


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
    _cache[ck] = out
    return out


def presets(e: dict, query: str | None = None) -> list[dict]:
    rows = catalog(e)
    if not query:
        return rows
    words = query.lower().split()
    return [r for r in rows if all(w in r["id"].lower() for w in words)]


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
        raise KeyError(f"preset {preset!r} for {e['name']} is ambiguous: {[r['id'] for r in hit][:10]}")
    raise KeyError(f"no preset {preset!r} for {e['name']}; presets(plugin, query) searches its {len(rows)}")


def preset_state(e: dict, preset: str) -> bytes:
    f = resolve_preset(e, preset)
    if f.suffix.lower() != ".fst":
        import vst3state
        st = next(x.data for x in block(e) if x.id == STATE)
        return vst3state.apply_file(st, f.read_bytes(), f.name)
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


def summary(query: str | None = None) -> list[dict]:
    out = []
    for e in entries():
        if query and query.lower() not in e["name"].lower():
            continue
        row = {k: e[k] for k in ("name", "kind", "vendor", "format", "source")}
        row["presets"] = len(catalog(e))
        row["params"] = param_file(e).exists()
        out.append(row)
    return out
