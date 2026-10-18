import re
import subprocess
import time
import winreg
from pathlib import Path

NAME = "kuruitsugizaki"
HKCU = winreg.HKEY_CURRENT_USER
LOOP = r"Software\Tobias Erichsen\loopMIDI\Ports"
BY_HAND = "by hand: loopMIDI, add a port with +; FL, Options > MIDI settings, select that port in Input, enable it, controller type kuruitsugizaki"


def values(path: str) -> dict:
    try:
        with winreg.OpenKey(HKCU, path) as k:
            return dict(winreg.EnumValue(k, i)[:2] for i in range(winreg.QueryInfoKey(k)[1]))
    except FileNotFoundError:
        return {}


def subkeys(path: str) -> list[str]:
    try:
        with winreg.OpenKey(HKCU, path) as k:
            return [winreg.EnumKey(k, i) for i in range(winreg.QueryInfoKey(k)[0])]
    except FileNotFoundError:
        return []


def running(image: str) -> bool:
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {image}", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    return f'"{image.lower()}"' in out.lower()


def fl_key(fl_exe: str | None) -> str | None:
    m = re.search(r"FL Studio (\d+)", Path(fl_exe).parent.name) if fl_exe else None
    key = rf"Software\Image-Line\FL Studio {int(m.group(1)) % 100}" if m else None
    return key if key and subkeys(key) else None


def state(fl_exe: str | None) -> dict:
    key = fl_key(fl_exe)
    ins = {n: values(rf"{key}\Devices\MIDI input\{n}") for n in subkeys(rf"{key}\Devices\MIDI input")} if key else {}
    return {"loopmidi_ports": list(values(LOOP)), "fl_settings": key,
            "assigned": [n for n, v in ins.items() if v.get("ScriptFolder") == NAME and v.get("Enabled") == "1"]}


def ensure(fl_exe: str | None, loopmidi_exe: str | None) -> dict:
    s = state(fl_exe)
    if s["assigned"]:
        return {"ok": True, "changed": False, "port": s["assigned"][0]}
    if not loopmidi_exe:
        return {"ok": False, "error": "loopMIDI is not installed; install it and call fl_install again"}
    key = s["fl_settings"]
    if not key:
        return {"ok": False, "error": f"FL's settings were not found in the registry; start FL once, close it and call fl_install again, or {BY_HAND}"}
    if running("FL64.exe"):
        return {"ok": False, "error": f"FL is running and writes its MIDI settings when it closes; close FL and call fl_install again, or {BY_HAND}"}
    made = NAME not in s["loopmidi_ports"]
    if made:
        import flproc
        was = running("loopMIDI.exe")
        ours = bool(flproc.owned(flproc.LOOP_OWNED))
        if was:
            subprocess.run(["taskkill", "/F", "/IM", "loopMIDI.exe"], capture_output=True)
            time.sleep(1)
        with winreg.CreateKey(HKCU, LOOP) as k:
            winreg.SetValueEx(k, NAME, 0, winreg.REG_DWORD, 1)
        if was and ours:
            flproc.launch([loopmidi_exe], image="loopMIDI.exe", path=flproc.LOOP_OWNED)
        elif was:
            subprocess.Popen([loopmidi_exe])
    paired = values(rf"{key}\Devices\MIDI output\{NAME}").get("Port")
    used = {values(rf"{key}\Devices\{d}\{n}").get("Port") for d in ("MIDI input", "MIDI output") for n in subkeys(rf"{key}\Devices\{d}") if (d, n) != ("MIDI output", NAME)}
    number = paired if paired and paired != "-1" and paired not in used else next(str(n) for n in range(10, 256) if str(n) not in used)
    with winreg.CreateKey(HKCU, rf"{key}\Devices\MIDI input\{NAME}") as k:
        for name, value in (("Type", "-3"), ("ScriptFolder", NAME), ("IDString", "-"), ("ConnectionCounter", "0"), ("Port", number), ("Enabled", "1")):
            winreg.SetValueEx(k, name, 0, winreg.REG_SZ, value)
    return {"ok": True, "changed": True, "port": NAME, "loopmidi_port_created": made, "fl_port_number": number}
