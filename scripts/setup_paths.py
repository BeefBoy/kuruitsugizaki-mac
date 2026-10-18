"""Setup's questions about paths: for each one the path already set or found is shown, Enter keeps it, or type another.
A path typed here, and the answers about the user's own projects and samples, go into kuruitsugizaki.json; a path kept
as found is left to be found again, so it follows an FL update. --yes asks nothing and keeps what is found."""
import argparse
import os
import sys
from pathlib import Path

import config as cfg

PATHS = [
    ("fl_exe", "FL Studio's FL64.exe", "file"),
    ("loopmidi_exe", "loopMIDI.exe", "file"),
    ("fl_hardware", "FL's Settings\\Hardware folder (the controller script goes here)", "dir"),
    ("plugin_db", "FL's Plugin database folder (every plugin FL has scanned)", "dir"),
    ("claude_desktop_config", "the Claude desktop app's config file", "parent"),
    ("claude_code_dir", "the Claude Code profile folder (CLAUDE_CONFIG_DIR; another login profile is another folder)", "dir"),
]


def clean(text: str) -> str:
    return os.path.expandvars(os.path.expanduser(text.strip().strip('"').strip("'")))


def same(a: str | None, b: str | None) -> bool:
    return bool(a and b) and os.path.normcase(os.path.normpath(a)) == os.path.normcase(os.path.normpath(b))


def usable(p: str, kind: str) -> bool:
    path = Path(p)
    return path.is_file() if kind == "file" else path.is_dir() if kind == "dir" else path.parent.is_dir()


def found(key: str, data: dict) -> str | None:
    if data.get(key):
        return data[key]
    if key == "claude_desktop_config":
        p = cfg._places(data)[key][0]
        return str(p) if p.parent.is_dir() else None
    return cfg.detect(key, data)


def ask_path(key: str, what: str, kind: str, data: dict, yes: bool) -> None:
    now = found(key, data)
    if yes:
        print(f"{what}: {now or 'not found'}")
        return
    while True:
        hint = f"{now}\n  Enter keeps it, or type another path: " if now else "not found.\n  Type its path, or Enter to skip: "
        typed = clean(input(f"{what}: {hint}"))
        if not typed:
            return
        if not usable(typed, kind):
            need = "a file that exists" if kind == "file" else "a folder that exists" if kind == "dir" else "a path whose folder exists"
            print(f"  {typed} is not {need}.")
            continue
        if not same(typed, now) or key in data:
            data[key] = typed
        return


def ask_answer(key: str, question: str, suggest: str | None, many: bool, data: dict, yes: bool) -> None:
    now = data.get(key)
    shown = "none" if now == [] else "; ".join(now) if isinstance(now, list) else now or suggest
    if yes:
        print(f"{question}: {shown if now is not None else 'left for the first chat'}")
        return
    while True:
        hint = (f"{shown}\n  Enter keeps it, type another" if shown else "\n  Type a path") + (" (several: separate with ;)" if many else "") + \
               ", 'none' when there is none" + ("" if shown else ", or Enter to leave it for the first chat") + ": "
        typed = input(f"{question}: {hint}").strip()
        if not typed:
            if shown and now is None:
                data[key] = [shown] if many else shown
            return
        if typed.lower() == "none":
            data[key] = []
            return
        paths = [clean(p) for p in typed.split(";") if p.strip()] if many else [clean(typed)]
        bad = [p for p in paths if not Path(p).is_dir()]
        if bad:
            print(f"  not a folder: {'; '.join(bad)}")
            continue
        data[key] = paths if many else paths[0]
        return


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--yes", action="store_true", help="ask nothing; keep what is found")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    data = cfg.load()
    before = dict(data)
    print("Paths. Each shows what is set or was found.")
    for key, what, kind in PATHS:
        ask_path(key, what, kind, data, a.yes)
    projects = cfg.documents() / "Image-Line" / "FL Studio" / "Projects"
    ask_answer("projects_folder", "Your own FL projects, which the model reads to learn how you write",
               str(projects) if projects.is_dir() and any(projects.rglob("*.flp")) else None, False, data, a.yes)
    ask_answer("sample_folders", "Your sample folders", None, True, data, a.yes)
    for key in data:
        if data[key] != before.get(key):
            cfg.put(key, data[key])
            print(f"saved {key} in {cfg.FILE.name}")


if __name__ == "__main__":
    sys.exit(main())
