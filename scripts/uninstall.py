import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import winreg
from pathlib import Path

import config as cfg
import midisetup as ms

ROOT = cfg.ROOT
NAME = ms.NAME
CLAUDE = Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json"


def midi() -> list[str]:
    out = []
    key = ms.fl_key(cfg.get("fl_exe"))
    if key:
        base = rf"{key}\Devices\MIDI input"
        for n in ms.subkeys(base):
            if ms.values(rf"{base}\{n}").get("ScriptFolder") != NAME:
                continue
            if n == NAME:
                winreg.DeleteKey(ms.HKCU, rf"{base}\{n}")
                out.append(f"FL MIDI input {n!r}: removed")
            else:
                with winreg.OpenKey(ms.HKCU, rf"{base}\{n}", 0, winreg.KEY_SET_VALUE) as k:
                    winreg.SetValueEx(k, "ScriptFolder", 0, winreg.REG_SZ, "")
                    winreg.SetValueEx(k, "Type", 0, winreg.REG_SZ, "0")
                out.append(f"FL MIDI input {n!r}: script unassigned, port kept")
        if ms.values(rf"{key}\Devices\MIDI output\{NAME}"):
            winreg.DeleteKey(ms.HKCU, rf"{key}\Devices\MIDI output\{NAME}")
            out.append(f"FL MIDI output {NAME!r}: removed")
    else:
        out.append("FL's settings not found in the registry; nothing to unassign")
    if NAME in ms.values(ms.LOOP):
        was = ms.running("loopMIDI.exe")
        if was:
            subprocess.run(["taskkill", "/F", "/IM", "loopMIDI.exe"], capture_output=True)
            time.sleep(1)
        with winreg.OpenKey(ms.HKCU, ms.LOOP, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, NAME)
        if was and cfg.get("loopmidi_exe"):
            subprocess.Popen([cfg.get("loopmidi_exe")])
        out.append(f"loopMIDI port {NAME!r}: removed")
    return out or ["no FL MIDI input had the script and no loopMIDI port was named kuruitsugizaki"]


def controller() -> str:
    hw = cfg.get("fl_hardware")
    d = Path(hw) / NAME if hw else None
    if not d or not d.is_dir():
        return "controller script: not installed"
    shutil.rmtree(d)
    return f"controller script: removed {d}"


def claude_desktop(path: Path) -> str:
    if not path.exists():
        return f"Claude desktop app: no config at {path}"
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig") or "{}")
    except json.JSONDecodeError as e:
        return f"Claude desktop app: {path} is not valid JSON ({e}); left as it is"
    if NAME not in data.get("mcpServers", {}):
        return "Claude desktop app: no kuruitsugizaki entry"
    shutil.copy2(path, path.with_name(path.name + ".bak"))
    del data["mcpServers"][NAME]
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return f"Claude desktop app: entry removed, old file kept as {path.name}.bak"


def claude_code() -> str:
    exe = shutil.which("claude")
    if not exe:
        return "Claude Code: not installed"
    r = subprocess.run([exe, "mcp", "remove", "--scope", "user", NAME], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return "Claude Code: entry removed" if r.returncode == 0 else "Claude Code: no kuruitsugizaki entry"


def local(keep_config: bool) -> list[str]:
    out = []
    states = ROOT / "tmp" / "states"
    if states.is_dir():
        shutil.rmtree(states)
        out.append(f"saved plugin states: removed {states}")
    if cfg.FILE.exists() and not keep_config:
        dest = ROOT / "tmp" / "uninstall" / f"kuruitsugizaki-{time.strftime('%Y%m%d-%H%M%S')}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(cfg.FILE), dest)
        out.append(f"settings: {cfg.FILE.name} moved to {dest}")
    return out


def main():
    ap = argparse.ArgumentParser(description="Undo what setup did; uv, loopMIDI, ffmpeg and .venv stay.")
    ap.add_argument("--yes", action="store_true", help="do not ask")
    ap.add_argument("--keep-config", action="store_true", help="leave kuruitsugizaki.json in place")
    ap.add_argument("--claude-config", default=str(CLAUDE), help="the Claude desktop app's config (default %(default)s)")
    ap.add_argument("--no-claude-code", action="store_true", help="leave Claude Code's config alone")
    a = ap.parse_args()
    print(f"kuruitsugizaki uninstall. Folder: {ROOT}")
    print("It removes the controller script from FL's Hardware folder, unassigns it in FL's MIDI settings (a port setup made is")
    print("removed, a port you made is kept), removes the server from the Claude desktop app and Claude Code, deletes the saved")
    print("plugin states and moves kuruitsugizaki.json into tmp/uninstall. uv, loopMIDI, ffmpeg and .venv stay.")
    if ms.running("FL64.exe"):
        print("FL Studio is open, and it writes its MIDI settings back when it closes. Save your work, close FL, run this again.")
        sys.exit(1)
    if not a.yes and input("Go on? [Y/n] ").strip().lower() not in ("", "y", "yes"):
        sys.exit(0)
    lines = midi() + [controller(), claude_desktop(Path(a.claude_config))]
    if not a.no_claude_code:
        lines.append(claude_code())
    lines += local(a.keep_config)
    for line in lines:
        print("  " + line)
    print("Done. The server still runs in an open Claude app until it is quit fully (tray icon, Quit). setup.bat installs it again.")


if __name__ == "__main__":
    main()
