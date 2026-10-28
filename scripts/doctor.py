import argparse
import json
import re
import shutil
import sys
from pathlib import Path

import cli
import config as cfg

import midisetup  # noqa: E402  (no winreg at import on macOS)

ROOT = cfg.ROOT
EXE = ROOT / ".venv" / ("Scripts" if cfg.WIN else "bin") / ("kuruitsugizaki.exe" if cfg.WIN else "kuruitsugizaki")
CLAUDE = cfg.claude_desktop()


def register(path: Path) -> dict:
    entry = {"command": str(EXE)}
    try:
        text = path.read_text(encoding="utf-8-sig") if path.exists() else ""
        data = json.loads(text) if text.strip() else {}
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"{path} is not valid JSON ({e}); left as it is"}
    if data.get("mcpServers", {}).get("kuruitsugizaki") == entry:
        return {"ok": True, "changed": False, "file": str(path)}
    if path.exists():
        shutil.copy2(path, path.with_name(path.name + ".bak"))
    data.setdefault("mcpServers", {})["kuruitsugizaki"] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "changed": True, "file": str(path)}


def checks(claude: Path) -> list[tuple]:
    out = []

    def row(need, name, ok, detail):
        out.append((need, name, bool(ok), str(detail)))

    fl, loop = cfg.get("fl_exe"), cfg.get("loopmidi_exe")
    row(True, "FL Studio", fl and Path(fl).exists(), fl or "not found; set fl_exe with the config tool")
    row(True, "server", EXE.exists(), EXE if EXE.exists() else "run `uv sync` in this folder")
    if cfg.WIN:
        row(True, "loopMIDI", loop and Path(loop).exists(), loop or "not installed: winget install TobiasErichsen.loopMIDI")
        hw = cfg.get("fl_hardware")
        script = Path(hw) / "kuruitsugizaki" / "device_kuruitsugizaki.py" if hw else None
        box = re.search(r"(?m)^BOX = '(.*)'", script.read_text(encoding="utf-8")) if script and script.exists() else None
        here = (ROOT / "tmp" / "bridge").as_posix()
        row(True, "controller script", box and box.group(1) == here,
            script if box and box.group(1) == here else "not installed for this folder; run fl_install" if hw else "FL's Settings\\Hardware folder not found; set fl_hardware")
        s = midisetup.state(fl)
        row(True, "loopMIDI port", s["loopmidi_ports"], ", ".join(s["loopmidi_ports"]) or "none; fl_install makes one")
        row(True, "FL MIDI setting", s["assigned"], f"script on input {s['assigned'][0]!r}" if s["assigned"] else "no input has the script; run fl_install with FL closed, or " + midisetup.BY_HAND)
    elif cfg.MAC:
        hw = cfg.get("fl_hardware")
        script = Path(hw) / "kuruitsugizaki" / "device_kuruitsugizaki.py" if hw else None
        mine = re.sub(r"(?m)^BOX = .*$", "", (ROOT / "fl" / "device_kuruitsugizaki.py").read_text(encoding="utf-8"))
        same = script and script.exists() and re.sub(r"(?m)^BOX = .*$", "", script.read_text(encoding="utf-8")) == mine
        row(True, "controller script", same, script if same else "not installed, or older than this folder's; run fl_install" if hw else "FL's Settings/Hardware folder not found; set fl_hardware")
        s = midisetup.state_mac(fl)
        row(True, "FL MIDI setting", s["paired"], f"input and output kuruitsugizaki on port {s['paired']}, the input with the script" if s["paired"] else
            "kuruitsugizaki is not set up as FL saved it; quit FL and run fl_install (doctor.py --install)")
    else:
        row(False, "live link", False, "needs FL on Windows or macOS; the file tools work without it")
    try:
        import library
        rows = library.summary(None, native=True)
        row(True, "FL plugin database", rows, f"{len(rows)} plugins, {sum(1 for r in rows if r.get('presets'))} with presets")
    except Exception as e:
        row(True, "FL plugin database", False, e)
    try:
        import writer
        raw, warn = writer.build({"format": "compact", "project": {"bpm": 140, "ppq": 96}, "instruments": [{"id": "x", "kind": "sampler", "path": "x.wav"}],
                                  "patterns": [{"id": "p", "notes": [[1, 1, 0, 96, "C4", 100, 0]]}], "arrangements": [{"name": "A", "clips": [[1, 1, 1, 0, 384, "p"]]}]})
        row(True, "template", raw, f"{cfg.get('template')} builds, {len(raw)} bytes")
    except Exception as e:
        row(True, "template", False, repr(e))
    ff = shutil.which("ffmpeg") and shutil.which("ffprobe")
    row(False, "ffmpeg", ff, ff or ("not on PATH; renders come back without their analysis: " + ("winget install Gyan.FFmpeg" if cfg.WIN else "brew install ffmpeg")))
    try:
        has = json.loads(claude.read_text(encoding="utf-8-sig")).get("mcpServers", {}).get("kuruitsugizaki", {}).get("command") == str(EXE)
    except Exception:
        has = False
    row(False, "Claude desktop app", has, claude if has else f"no entry for this folder in {claude}; doctor.py --claude adds it")
    return out


def install_rows(r: dict) -> list[tuple[str, str, str]]:
    """fl_install's answer as rows."""
    if not r.get("ok"):
        return [("failed", "controller script", r.get("error", ""))]
    out = [("made" if r["changed"] else "kept", "controller script", r["installed"])]
    m = r["midi"]
    if not m.get("ok"):
        out.append(("failed", "FL MIDI setting", m.get("error", "")))
    elif m.get("changed"):
        made = f"loopMIDI port {m['port']!r} made; " if m.get("loopmidi_port_created") else ""
        out.append(("made", "FL MIDI setting", f"{made}FL input {m['port']!r} on port {m['fl_port_number']} has the script"))
    else:
        out.append(("kept", "FL MIDI setting", f"FL input {m['port']!r} already has the script"))
    return out


def main():
    ap = argparse.ArgumentParser(description="Check this machine's setup, and optionally do the parts a script can do.")
    ap.add_argument("--install", action="store_true", help="run fl_install: the controller script, the loopMIDI port and FL's MIDI setting")
    ap.add_argument("--claude", nargs="?", const=str(CLAUDE), help="add the server to the Claude desktop app's config (default %(const)s)")
    ap.add_argument("--live", action="store_true", help="start FL if it is closed and ask the controller script for FL's API version")
    a = ap.parse_args()
    claude = Path(a.claude) if a.claude else CLAUDE
    if a.install or a.live:
        import server
    done = []
    if a.install:
        done += install_rows(server.fl_install())
    if a.claude:
        r = register(claude)
        done.append(("failed", "Claude desktop app", r["error"]) if not r["ok"] else
                    ("added" if r["changed"] else "kept", "Claude desktop app", f"{r['file']}" + ("" if r["changed"] else " (already there)")))
    if done:
        cli.rows(done)
        cli.section("Check")
    rows = checks(claude)
    if a.live and all(ok for need, _, ok, _ in rows if need):
        r = server.fl_probe()
        while not r.get("ok") and "still starting" in str(r.get("error")):
            r = server.fl_probe()
        rows.append((True, "live link", bool(r.get("ok")), f"FL answers, scripting API {r['value']['api']}" if r.get("ok") else r.get("error")))
    elif a.live:
        rows.append((True, "live link", False, "not tried; the lines marked MISSING come first"))
    cli.rows([("ok" if ok else "MISSING" if need else "optional", name, detail) for need, name, ok, detail in rows])
    sys.exit(1 if any(need and not ok for need, _, ok, _ in rows) else 0)


if __name__ == "__main__":
    main()
