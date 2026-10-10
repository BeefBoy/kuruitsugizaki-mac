"""Build the examples into projects/examples/<name>.flp.

python examples/build.py            every example
python examples/build.py 04_routing  only the ones named

A .py example is run first, to write its .json. Exit status 1 when any example fails or the writer warns.
Open a built project in FL by double-clicking it, or ask the model to open it (project_write with open=true).
"""
import json
import os
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "scripts"))
os.chdir(ROOT)

import writer  # noqa: E402


def main(names: list[str]) -> int:
    for py in sorted(HERE.glob("*.py")):
        if py.name != "build.py" and (not names or py.stem in names):
            runpy.run_path(str(py), run_name="__main__")
    out_dir = ROOT / "projects" / "examples"
    out_dir.mkdir(parents=True, exist_ok=True)
    bad = 0
    for js in sorted(HERE.glob("*.json")):
        if names and js.stem not in names:
            continue
        try:
            raw, warnings = writer.build(json.loads(js.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"{js.stem}: FAILED {e!r}")
            bad += 1
            continue
        out = out_dir / f"{js.stem}.flp"
        out.write_bytes(raw)
        print(f"{js.stem}: {out.relative_to(ROOT)} ({len(raw)} bytes){'; warnings: ' + '; '.join(warnings) if warnings else ''}")
        bad += bool(warnings)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
