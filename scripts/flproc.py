import ctypes
import json
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
