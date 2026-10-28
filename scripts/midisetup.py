import re
import subprocess
import sys
import time
from pathlib import Path

try:
    import winreg
except ImportError:  # macOS: FL keeps the same keys in reg.xml (RegXml)
    winreg = None

NAME = "kuruitsugizaki"
HKCU = winreg.HKEY_CURRENT_USER if winreg else None
LOOP = r"Software\Tobias Erichsen\loopMIDI\Ports"
BY_HAND = "by hand: loopMIDI, add a port with +; FL, Options > MIDI settings, select that port in Input, enable it, controller type kuruitsugizaki"


class RegXml:
    """FL for Mac's registry: ~/Library/Preferences/Image-Line/reg.xml, <Key Name> and <Value Name Type> elements under
    Key1/HKEY_CURRENT_USER, every value a string (Type 2). FL reads it at start and rewrites it when it closes."""
    FILE = Path.home() / "Library" / "Preferences" / "Image-Line" / "reg.xml"

    def __init__(self):
        import xml.etree.ElementTree as ET
        self.ET = ET
        self.tree = ET.parse(self.FILE) if self.FILE.exists() else None

    def key(self, path: str, make: bool = False):
        if self.tree is None:
            return None
        k = self.tree.getroot()
        for name in ["Key1", "HKEY_CURRENT_USER", *path.split("\\")]:
            sub = next((c for c in k.findall("Key") if c.get("Name") == name), None)
            if sub is None:
                if not make:
                    return None
                sub = self.ET.SubElement(k, "Key", Name=name)
            k = sub
        return k

    def values(self, path: str) -> dict:
        k = self.key(path)
        return {} if k is None else {v.get("Name"): v.text or "" for v in k.findall("Value")}

    def subkeys(self, path: str) -> list[str]:
        k = self.key(path)
        return [] if k is None else [c.get("Name") for c in k.findall("Key")]

    def set(self, path: str, pairs):
        k = self.key(path, make=True)
        for name, value in pairs:
            v = next((x for x in k.findall("Value") if x.get("Name") == name), None)
            if v is None:
                v = self.ET.SubElement(k, "Value", Name=name, Type="2")
            v.text = value or None

    def save(self):
        import shutil
        shutil.copy2(self.FILE, self.FILE.with_suffix(".xml.bak"))
        self.ET.indent(self.tree, "  ")
        body = self.ET.tostring(self.tree.getroot(), encoding="unicode").replace(" />", "/>")  # as FL writes it
        self.FILE.write_text('<?xml version="1.0" encoding="utf-8"?>\n' + body + "\n", encoding="utf-8")


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
    if sys.platform != "win32":
        import flproc
        return bool(flproc.pids(image))
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {image}", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    return f'"{image.lower()}"' in out.lower()


def fl_key(fl_exe: str | None, sub=subkeys) -> str | None:
    folder = (Path(fl_exe).parent.name if winreg else Path(fl_exe).stem) if fl_exe else ""  # macOS: fl_exe is the .app
    m = re.search(r"FL Studio (\d+)", folder) if fl_exe else None
    key = rf"Software\Image-Line\FL Studio {int(m.group(1)) % 100}" if m else None
    return key if key and sub(key) else None


def state(fl_exe: str | None) -> dict:
    key = fl_key(fl_exe)
    ins = {n: values(rf"{key}\Devices\MIDI input\{n}") for n in subkeys(rf"{key}\Devices\MIDI input")} if key else {}
    return {"loopmidi_ports": list(values(LOOP)), "fl_settings": key,
            "assigned": [n for n, v in ins.items() if v.get("ScriptFolder") == NAME and v.get("Enabled") == "1"]}


def state_mac(fl_exe: str | None, reg: RegXml | None = None) -> dict:
    reg = reg or RegXml()
    key = fl_key(fl_exe, reg.subkeys)
    dev = rf"{key}\Devices" if key else None
    inp = reg.values(rf"{dev}\MIDI input\{NAME}") if key else {}
    out = reg.values(rf"{dev}\MIDI output\{NAME}") if key else {}
    ok = inp.get("ScriptFolder") == NAME and inp.get("Enabled") == "1" and inp.get("Port") not in (None, "", "-1") and out.get("Port") == inp.get("Port")
    return {"fl_settings": key, "input": inp, "output": out, "paired": inp.get("Port") if ok else None}


def ensure_mac(fl_exe: str | None) -> dict:
    """The input that the server's virtual port feeds gets the script; the output it listens on, the same port number,
    since on macOS the script's replies come back as MIDI. With FL closed: FL rewrites reg.xml when it closes."""
    by_hand = ("by hand: FL, Options > MIDI settings; Input kuruitsugizaki: enable it, controller type kuruitsugizaki, "
               "a port number; Output kuruitsugizaki: the same port number")
    reg = RegXml()
    s = state_mac(fl_exe, reg)
    key, inp, out = s["fl_settings"], s["input"], s["output"]
    if not key:
        return {"ok": False, "error": f"FL's settings ({reg.FILE}) were not found; start FL once, close it and call fl_install again, or {by_hand}"}
    if s["paired"]:
        return {"ok": True, "changed": False, "port": NAME, "fl_port_number": s["paired"]}
    dev = rf"{key}\Devices"
    if running("FL64.exe"):
        return {"ok": False, "error": f"FL is running and writes its MIDI settings when it closes; quit FL and call fl_install again, or {by_hand}"}
    used = {reg.values(rf"{dev}\{d}\{n}").get("Port") for d in ("MIDI input", "MIDI output") for n in reg.subkeys(rf"{dev}\{d}") if n != NAME}
    mine = inp.get("Port") if inp.get("Port") not in (None, "-1") else None
    number = mine if mine and mine not in used else next(str(n) for n in range(10, 256) if str(n) not in used)
    reg.set(rf"{dev}\MIDI input\{NAME}", (("Type", "-3"), ("ScriptFolder", NAME), ("IDString", "-"),
                                          ("ConnectionCounter", inp.get("ConnectionCounter") or "0"), ("Port", number), ("Enabled", "1")))
    reg.set(rf"{dev}\MIDI output\{NAME}", (("Port", number), ("Sync", out.get("Sync") or "0"),
                                           ("SendAllNotesOff", out.get("SendAllNotesOff") or "1"), ("IDString", "-")))
    reg.save()
    return {"ok": True, "changed": True, "port": NAME, "fl_port_number": number, "settings": str(reg.FILE)}


def ensure(fl_exe: str | None, loopmidi_exe: str | None) -> dict:
    if winreg is None:
        return ensure_mac(fl_exe)
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
