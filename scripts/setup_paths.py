"""Setup's questions about paths: for each one the path already set or found is shown, Enter keeps it, or type another.
A path typed here, and the answers about the user's own projects and samples, go into kuruitsugizaki.json; a path kept
as found is left to be found again, so it follows an FL update. --yes asks nothing and keeps what is found."""
import argparse
import os
import sys
from pathlib import Path

import cli
import config as cfg

PATHS = [
    ("fl_exe", "FL Studio", "FL Studio's FL64.exe", "file"),
    ("loopmidi_exe", "loopMIDI", "loopMIDI.exe", "file"),
    ("fl_hardware", "FL Hardware folder", "FL's Settings\\Hardware folder, where the controller script goes", "dir"),
    ("plugin_db", "FL plugin database", "FL's Plugin database folder, every plugin FL has scanned", "dir"),
    ("claude_desktop_config", "Claude desktop config", "the Claude desktop app's config file", "parent"),
    ("claude_code_dir", "Claude Code profile", "the Claude Code profile folder (CLAUDE_CONFIG_DIR); another login profile is another folder", "dir"),
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
        p = cfg.claude_desktop_found()
        return str(p) if p else None
    return cfg.detect(key, data)


def ask(prompt: str) -> str:
    return cli.console.input(f"  [dim]{prompt}[/] ")


def ask_path(key: str, short: str, what: str, kind: str, data: dict, yes: bool) -> tuple[str, str, str]:
    now = found(key, data)
    if not yes:
        cli.say(f"\n[bold]{short}[/]  [dim]{what}[/]")
        cli.say(f"  {now}" if now else "  [yellow]not found[/]")
        while True:
            typed = clean(ask("Enter keeps it, or type another path:" if now else "Type its path, or Enter to skip:"))
            if not typed:
                break
            if not usable(typed, kind):
                need = "a file that exists" if kind == "file" else "a folder that exists" if kind == "dir" else "a path whose folder exists"
                cli.say(f"  [red]{typed} is not {need}[/]")
                continue
            if not same(typed, now) or key in data:
                data[key] = typed
            now = typed
            break
    status = "set" if key in data else "found" if now else "MISSING"
    return status, short, now or "not found"


def ask_answer(key: str, short: str, what: str, suggest: str | None, many: bool, data: dict, yes: bool) -> tuple[str, str, str]:
    def shown():
        now = data.get(key)
        return "none" if now == [] else "; ".join(now) if isinstance(now, list) else now
    if not yes:
        offer = shown() or suggest
        cli.say(f"\n[bold]{short}[/]  [dim]{what}[/]")
        if offer:
            cli.say(f"  {offer}")
        more = " (several: separate with ;)" if many else ""
        while True:
            typed = ask(f"Enter keeps it, type another{more}, or 'none':" if offer else
                        f"Type a path{more}, 'none' when there is none, or Enter to leave it for the first chat:").strip()
            if not typed:
                if offer and key not in data:
                    data[key] = [offer] if many else offer
                break
            if typed.lower() == "none":
                data[key] = []
                break
            paths = [clean(p) for p in typed.split(";") if p.strip()] if many else [clean(typed)]
            bad = [p for p in paths if not Path(p).is_dir()]
            if bad:
                cli.say(f"  [red]not a folder: {'; '.join(bad)}[/]")
                continue
            data[key] = paths if many else paths[0]
            break
    return ("set", short, shown()) if key in data else ("later", short, "left for the first chat")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--yes", action="store_true", help="ask nothing; keep what is found")
    a = ap.parse_args()
    data = cfg.load()
    before = dict(data)
    rows = [ask_path(key, short, what, kind, data, a.yes) for key, short, what, kind in PATHS]
    projects = cfg.documents() / "Image-Line" / "FL Studio" / "Projects"
    rows.append(ask_answer("projects_folder", "Your projects", "your own FL projects, which the model reads to learn how you write",
                           str(projects) if projects.is_dir() and any(projects.rglob("*.flp")) else None, False, data, a.yes))
    rows.append(ask_answer("sample_folders", "Your samples", "your sample folders", None, True, data, a.yes))
    if not a.yes:
        cli.say("")
    cli.rows(rows)
    saved = [key for key in data if data[key] != before.get(key)]
    for key in saved:
        cfg.put(key, data[key])
    if saved:
        cli.say(f"[dim]saved in {cfg.FILE.name}: {', '.join(saved)}[/]")


if __name__ == "__main__":
    sys.exit(main())
