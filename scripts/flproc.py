import ctypes
import json
import re
import subprocess
import time
from ctypes import wintypes
from pathlib import Path

OWNED = Path(__file__).resolve().parents[1] / "tmp" / "bridge" / "owned.json"


class Ambiguous(RuntimeError):
    pass


def pids() -> list[int]:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq FL64.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True, stdin=subprocess.DEVNULL).stdout
    return [int(line.split('","')[1]) for line in out.splitlines() if line.lower().startswith('"fl64.exe"')]


def created(pid: int) -> int | None:
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, pid)
    if not h:
        return None
    try:
        t = [wintypes.FILETIME() for _ in range(4)]
        if not k.GetProcessTimes(h, *(ctypes.byref(x) for x in t)):
            return None
        return (t[0].dwHighDateTime << 32) | t[0].dwLowDateTime
    finally:
        k.CloseHandle(h)


def _load() -> dict:
    try:
        return json.loads(OWNED.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(data: dict):
    OWNED.parent.mkdir(parents=True, exist_ok=True)
    OWNED.write_text(json.dumps(data), encoding="utf-8")


def owned() -> list[int]:
    data = _load()
    alive = {p: t for p, t in data.items() if created(int(p)) == t}
    if alive != data:
        _save(alive)
    return [int(p) for p, _ in sorted(alive.items(), key=lambda kv: kv[1])]


def launch(args: list[str], wait: float = 10.0) -> list[int]:
    before = set(pids())
    subprocess.Popen(args)
    t0 = time.monotonic()
    new = []
    while not new and time.monotonic() - t0 < wait:
        time.sleep(0.25)
        new = [p for p in pids() if p not in before]
    data = {str(p): created(p) for p in owned()}
    data.update({str(p): created(p) for p in new})
    _save(data)
    return new


def cmdline(pid: int) -> str:
    out = subprocess.run(["powershell", "-NoProfile", "-Command", f"(Get-CimInstance Win32_Process -Filter 'ProcessId={int(pid)}').CommandLine"],
                         capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return out.stdout.strip()


def recent(fl_exe: str | None) -> list[str]:
    import midisetup
    key = midisetup.fl_key(fl_exe)
    vals = midisetup.values(rf"{key}\MRU") if key else {}
    return [v for k, v in sorted(vals.items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 1 << 30) if isinstance(v, str)]


def project_file(pid: int, title: str, fl_exe: str | None, projects: Path | None = None) -> tuple[Path | None, str]:
    name = title.rsplit(" - FL Studio", 1)[0].strip() if " - FL Studio" in title else ""
    if not name:
        return None, "untitled project: nothing on disk to copy"
    want = Path(name if name.lower().endswith(".flp") else name + ".flp").name
    mru = recent(fl_exe)
    cands = re.findall(r'"([^"]+\.flp)"', cmdline(pid), re.I) + ([name] if "/" in name or "\\" in name else []) + mru
    for c in cands:
        p = Path(c)
        if p.name.lower() == want.lower() and p.is_file():
            return p, "found"
    dirs = list(dict.fromkeys(Path(m).parent for m in mru))
    found = [d / want for d in dirs if (d / want).is_file()]
    if not found and projects and projects.is_dir():
        found = list(projects.rglob(want))
    if found:
        found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return found[0], "found by name" + (f"; {len(found) - 1} more of that name, newest taken" if len(found) > 1 else "")
    return None, f"{want}: FL gives no path, and no file of that name is in its recent folders or Projects folder"


def choose(pid: int | None = None) -> tuple[int, str]:
    running = pids()
    if not running:
        raise RuntimeError("FL64.exe is not running")
    if pid:
        if pid not in running:
            raise RuntimeError(f"FL pid {pid} (KURUITSUGIZAKI_FL_PID) is not running; open: {running}")
        return pid, "harness" if pid in owned() else "user"
    mine = [p for p in owned() if p in running]
    if mine:
        return mine[-1], "harness"
    if len(running) == 1:
        return running[0], "user"
    raise Ambiguous(f"{len(running)} FL instances are open (pids {running}) and none was started by the harness, so none is picked: close the ones not to be used, or name one with KURUITSUGIZAKI_FL_PID")
