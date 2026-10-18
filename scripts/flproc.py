import ctypes
import json
import re
import struct
import subprocess
import time
from ctypes import wintypes
from pathlib import Path

OWNED = Path(__file__).resolve().parents[1] / "tmp" / "bridge" / "owned.json"
LOOP_OWNED = OWNED.with_name("owned_loopmidi.json")  # loopMIDI processes the harness started, kept apart from FL's


class Ambiguous(RuntimeError):
    pass


def pids(image: str = "FL64.exe") -> list[int]:
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {image}", "/FO", "CSV", "/NH"], capture_output=True, text=True, stdin=subprocess.DEVNULL).stdout
    return [int(line.split('","')[1]) for line in out.splitlines() if line.lower().startswith(f'"{image.lower()}"')]


def created(pid: int) -> int | None:
    """The creation time of a running process; None once it has exited, though Windows keeps an exited process's
    object, times and all, while any handle to it is open (loopMIDI's driver holds some)."""
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, pid)
    if not h:
        return None
    try:
        code = wintypes.DWORD()
        if not k.GetExitCodeProcess(h, ctypes.byref(code)) or code.value != 259:  # 259: STILL_ACTIVE
            return None
        t = [wintypes.FILETIME() for _ in range(4)]
        if not k.GetProcessTimes(h, *(ctypes.byref(x) for x in t)):
            return None
        return (t[0].dwHighDateTime << 32) | t[0].dwLowDateTime
    finally:
        k.CloseHandle(h)


def _load(path: Path = OWNED) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(data: dict, path: Path = OWNED):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def owned(path: Path = OWNED) -> list[int]:
    data = _load(path)
    alive = {p: t for p, t in data.items() if created(int(p)) == t}
    if alive != data:
        _save(alive, path)
    return [int(p) for p, _ in sorted(alive.items(), key=lambda kv: kv[1])]


def launch(args: list[str], wait: float = 10.0, image: str = "FL64.exe", path: Path = OWNED) -> list[int]:
    before = set(pids(image))
    subprocess.Popen(args)
    t0 = time.monotonic()
    new = []
    while not new and time.monotonic() - t0 < wait:
        time.sleep(0.25)
        new = [p for p in pids(image) if p not in before]
    data = {str(p): created(p) for p in owned(path)}
    data.update({str(p): created(p) for p in new})
    _save(data, path)
    return new


def windows(pid: int) -> list[tuple[int, str, str]]:
    u, out = ctypes.windll.user32, []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def each(h, _):
        p = wintypes.DWORD()
        u.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u.IsWindowVisible(h):
            c, t = ctypes.create_unicode_buffer(128), ctypes.create_unicode_buffer(512)
            u.GetClassNameW(h, c, 128)
            u.GetWindowTextW(h, t, 512)
            out.append((int(h), c.value, t.value))
        return True

    u.EnumWindows(each, 0)
    return out


def dialogs(pid: int, shots: Path | None = None) -> list[dict]:
    found = []
    for h, cls, title in windows(pid):
        if cls in ("TFruityLoopsMainForm", "TApplication"):
            continue
        d = {"title": title, "class": cls}
        if shots is not None:
            try:
                d["picture"] = str(capture(h, shots / f"{pid}-{time.strftime('%Y%m%d-%H%M%S')}-{h}.png"))
            except Exception as e:
                d["picture"] = f"not taken: {e!r}"
        found.append(d)
    return found


FL_BUTTONS = {3: ["yes", "no", "cancel"], 2: ["yes", "no"]}  # FL's own message box: text-less buttons, left to right


def press(pid: int, label: str, skip: tuple = ("TFruityLoopsMainForm", "TApplication", "TWAVRenderForm")) -> str | None:
    """Click the button named label ("No" matches "&No") in a dialog FL (pid) shows; the dialog's title, or None when
    no dialog of it has such a button. FL's own message box (TMsgForm, "Save changes to x.flp?") draws its buttons with
    no text, so there the button is the one at label's place, left to right."""
    u = ctypes.windll.user32
    for h, cls, title in windows(pid):
        if cls in skip:
            continue
        named, drawn = [], []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def each(c, _):
            t, k = ctypes.create_unicode_buffer(256), ctypes.create_unicode_buffer(64)
            u.GetWindowTextW(c, t, 256)
            u.GetClassNameW(c, k, 64)
            if t.value.replace("&", "").strip().lower() == label.lower():
                named.append(c)
            elif k.value == "TQuickFocusBtn":
                r = wintypes.RECT()
                u.GetWindowRect(c, ctypes.byref(r))
                drawn.append((r.left, c, r.right - r.left, r.bottom - r.top))
            return True

        u.EnumChildWindows(h, each, 0)
        if named:
            u.PostMessageW(named[0], 0x00F5, 0, 0)  # BM_CLICK
            return title or cls
        order = FL_BUTTONS.get(len(drawn), [])
        if cls == "TMsgForm" and label.lower() in order:
            _, b, w, hh = sorted(drawn)[order.index(label.lower())]
            at = (hh // 2) << 16 | (w // 2)
            u.PostMessageW(b, 0x0201, 1, at)  # WM_LBUTTONDOWN at the button's centre
            u.PostMessageW(b, 0x0202, 0, at)  # WM_LBUTTONUP
            return title or cls
    return None


def capture(hwnd: int, path: Path) -> Path:
    from PIL import Image
    u, g = ctypes.windll.user32, ctypes.windll.gdi32
    r = wintypes.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    hdc = u.GetWindowDC(hwnd)
    mdc = g.CreateCompatibleDC(hdc)
    bmp = g.CreateCompatibleBitmap(hdc, w, h)
    g.SelectObject(mdc, bmp)
    try:
        u.PrintWindow(hwnd, mdc, 2)
        head = struct.pack("<IiiHHIIiiII", 40, w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
        buf = ctypes.create_string_buffer(w * h * 4)
        g.GetDIBits(mdc, bmp, 0, h, buf, ctypes.create_string_buffer(head, 44), 0)
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB").save(path)
    finally:
        g.DeleteObject(bmp)
        g.DeleteDC(mdc)
        u.ReleaseDC(hwnd, hdc)
    return path


def crashes() -> dict[int, dict]:
    out = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_Process -Filter \"Name='WerFault.exe'\" | ForEach-Object { '{0} {1}' -f $_.ProcessId, $_.CommandLine }"],
                         capture_output=True, text=True, stdin=subprocess.DEVNULL).stdout
    running = set(pids())
    found = {}
    for line in out.splitlines():
        m = re.search(r"^(\d+) .*-p (\d+)", line.strip())
        if m and int(m.group(2)) in running:
            found[int(m.group(2))] = {"werfault": int(m.group(1))}
    for pid, info in found.items():
        info.update(fault(pid))
    return found


def fault(pid: int) -> dict:
    ps = ("Get-WinEvent -FilterHashtable @{LogName='Application'; Id=1000; StartTime=(Get-Date).AddMinutes(-30)} -ErrorAction SilentlyContinue | "
          f"Where-Object {{ $_.Message -match 'Faulting process id: 0x{pid:x}\\b' }} | Select-Object -First 1 -ExpandProperty Message")
    msg = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, stdin=subprocess.DEVNULL).stdout
    get = lambda label: (re.search(label + r":\s*(.+)", msg) or [None, None])[1]
    return {k: v.strip() for k, v in (("module", get("Faulting module path")), ("code", get("Exception code")), ("report", get("Report Id"))) if v}


def reap(pid: int):
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, stdin=subprocess.DEVNULL)


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
    pool = [Path(c) for c in cands] + [f for d in dirs if d.is_dir() for f in d.glob("*.flp")]
    titled = list(dict.fromkeys(p for p in pool if p.is_file() and flp_title(p) == name))
    if titled:
        titled.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return titled[0], "found by the project title FL shows" + (f"; {len(titled) - 1} more with that title, newest taken" if len(titled) > 1 else "")
    return None, f"{name}: FL gives no path, and no file of that name or project title is in its recent files, their folders or the Projects folder"


def flp_title(path: Path) -> str | None:
    try:
        with open(path, "rb") as fh:
            b = fh.read(1 << 16)
        if b[:4] != b"FLhd":
            return None
        i = 8 + struct.unpack_from("<I", b, 4)[0]
        if b[i:i + 4] != b"FLdt":
            return None
        i += 8
        while i < len(b):
            eid = b[i]
            i += 1
            if eid < 64:
                i += 1
            elif eid < 128:
                i += 2
            elif eid < 192:
                i += 4
            else:
                n = shift = 0
                while True:
                    c = b[i]
                    i += 1
                    n |= (c & 0x7F) << shift
                    shift += 7
                    if not c & 0x80:
                        break
                if eid == 194:
                    d = b[i:i + n]
                    return (d.decode("utf-16-le", "replace") if len(d) % 2 == 0 else d.decode("latin-1")).rstrip("\0")
                i += n
    except (OSError, IndexError, struct.error):
        return None
    return None


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
