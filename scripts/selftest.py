"""What CI runs, and anyone can: python scripts/selftest.py. No FL needed.

1. The shipped templates parse and serialize byte-identical.
2. A project built only from what ships (the template's FLEX, samplers, an effect copied from fx.flp, routing,
   automation) has no writer warning, round-trips and reads back as written. On Windows, where FL's plugin database
   names Sytrus and 3xOsc, every example is built too.
3. profile runs over what was built.
4. The MCP server imports and lists its tools.
Exit 1 on the first failure, with what failed.
"""
import asyncio
import os
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
os.chdir(ROOT)

import flp  # noqa: E402
import project  # noqa: E402
import style  # noqa: E402
import view  # noqa: E402


def check(ok: bool, what: str):
    print(("ok    " if ok else "FAIL  ") + what)
    if not ok:
        sys.exit(1)


FACTORY = "%FLStudioFactoryData%/Data/Patches/Packs/Drums/"
PORTABLE = {
    "format": "compact", "project": {"bpm": 140, "ppq": 96, "title": "selftest"},
    "instruments": [
        {"id": "kick", "name": "kick", "kind": "sampler", "path": FACTORY + "Kicks/Jung Kick.wav", "mixer": 1},
        {"id": "hat", "name": "hat", "kind": "sampler", "path": FACTORY + "Hats/909 CH 1.wav", "mixer": 2},
        {"id": "lead", "name": "lead", "kind": "plugin", "plugin": "flex", "mixer": 3},
    ],
    "automation": [{"id": "fade", "name": "fade", "kind": "automation", "target": {"mixer": 0, "param": "vol"}, "points": [[0, 0.8], [28, 0.8], [32, 0.0]]}],
    "mixer": {"volume": {"1": 0.8, "2": 0.6, "3": 0.7}, "routes": [{"from": 1, "to": 3, "level": 0.0}],
              "effects": [{"track": 3, "slot": 0, "from": {"file": "projects/init/fx.flp", "track": 3, "slot": 0}},
                          {"track": 0, "slot": 9, "from": {"file": "projects/init/fx.flp", "track": 2, "slot": 0}}]},
    "note_cols": ["bar", "beat", "tick", "len", "key", "vel", "inst"],
    "patterns": [
        {"id": "beat", "notes": [[1, b, 0, 24, "C5", 100, "kick"] for b in (1, 2, 3, 4)] + [[1, b, t, 12, "C5", 80, "hat"] for b in (1, 2, 3, 4) for t in (0, 48)]},
        {"id": "line", "notes": [[1, 1, 0, 192, "D#4", 100, "lead"], [1, 3, 0, 96, "F#4", 100, "lead"], [1, 4, 0, 96, "A#4", 100, "lead"]]},
    ],
    "clip_cols": ["track", "bar", "beat", "tick", "len", "src", "trim?"],
    "arrangements": [{"name": "Arrangement", "clips": [[1, b, 1, 0, 384, "beat"] for b in range(1, 9)] + [[2, b, 1, 0, 384, "line"] for b in range(5, 9)] + [[3, 1, 1, 0, 3072, "a0"]]}],
}


def main():
    for f in sorted((ROOT / "projects" / "init").glob("*.flp")):
        if f.name not in ("init.flp", "fx.flp"):
            continue
        b = f.read_bytes()
        check(flp.serialize(flp.parse(b)) == b, f"{f.name} round-trips byte-identical")
    import writer
    out = ROOT / "tmp" / "selftest"
    out.mkdir(parents=True, exist_ok=True)
    raw, warn = writer.build(PORTABLE)
    check(not warn, "a project from shipped parts builds with no warning" + (f": {warn}" if warn else ""))
    (out / "portable.flp").write_bytes(raw)
    back = view.read(str(out / "portable.flp"), "compact")
    check([i["id"] for i in back["instruments"]] == ["kick", "hat", "lead"]
          and sum(len(p["notes"]) for p in back["patterns"]) == 15
          and len(back["arrangements"][0]["clips"]) == 13
          and {(e["track"], e["slot"], e["plugin"]) for e in back["mixer_effects"]} == {(3, 0, "Fruity Limiter"), (0, 9, "Fruity Limiter")}
          and back["automation"][0]["target"] == {"mixer": 0, "param": "vol"},
          "it reads back as written: instruments, notes, clips, effects, automation")
    built = [out / "portable.flp"]
    if sys.platform == "win32":
        try:
            runpy.run_path(str(ROOT / "examples" / "build.py"), run_name="__main__")
            code = 0
        except SystemExit as e:
            code = e.code or 0
        check(code == 0, "examples build with no warning")
        ex = sorted((ROOT / "projects" / "examples").glob("*.flp"))
        check(len(ex) >= 8, f"{len(ex)} example projects built")
        for f in ex:
            (out / f.name).write_bytes(f.read_bytes())
        built += [out / f.name for f in ex]
    else:
        print("skip  examples: they load Sytrus and 3xOsc by name, which needs FL's plugin database (Windows with FL)")
    for f in built:
        b = f.read_bytes()
        p = flp.serialize(flp.parse(b)) == b
        d = project.export(str(f))
        s = view.read(str(f), "summary")
        check(p and d["project"]["bpm"] and s["arrangements"], f"{f.name} round-trips and reads back")
    r = style.build(str(out))
    check(r["read"] == len(built) and r["not_read"] == 0, f"profile reads all {len(built)} built projects")
    import server
    tools = sorted(t.name for t in asyncio.run(server.mcp.list_tools()))
    check(len(tools) >= 10 and "project_write" in tools and "profile" in tools, f"server lists {len(tools)} tools: {', '.join(tools)}")


if __name__ == "__main__":
    main()
