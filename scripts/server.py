import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

import config as cfg
import flproc

try:
    import _winapi
except ImportError:  # not Windows: the file tools work, the live link to FL does not
    _winapi = None

NO_LIVE = "the live link to FL needs Windows with FL Studio installed"
ROOT = Path(__file__).resolve().parents[1]
BOX = ROOT / "tmp" / "bridge"
MORE_DATA = 234
BOOT_WAIT = 45.0
BOOT_GIVEUP = 240.0

mcp = MCPServer("kuruitsugizaki")
READ = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
LIVE = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
RAW = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=False)


class Link:
    def __init__(self):
        self.srv = None
        self.pid = None
        self.who = None
        self.seq = 0
        self.lock = threading.Lock()

    @staticmethod
    def alive(pid: int) -> bool:
        try:
            h = _winapi.OpenProcess(0x1000, False, pid)
        except OSError:
            return False
        try:
            return _winapi.GetExitCodeProcess(h) == 259
        finally:
            _winapi.CloseHandle(h)

    def fl_pid(self) -> int:
        if self.pid and self.alive(self.pid):
            return self.pid
        env = os.environ.get("KURUITSUGIZAKI_FL_PID")
        self.pid, self.who = flproc.choose(int(env) if env else None)
        return self.pid

    def close(self):
        if self.srv is not None:
            try:
                _winapi.CloseHandle(self.srv)
            except OSError:
                pass
        self.srv = None

    def open(self):
        self.close()
        pid = self.fl_pid()
        name = rf"\\.\pipe\kuruitsugizaki-{os.getpid()}-{time.time_ns()}"
        srv = _winapi.CreateNamedPipe(name, _winapi.PIPE_ACCESS_DUPLEX,
                                      _winapi.PIPE_TYPE_MESSAGE | _winapi.PIPE_READMODE_MESSAGE | _winapi.PIPE_WAIT,
                                      1, 1 << 20, 1 << 20, 0, _winapi.NULL)
        cli = _winapi.CreateFile(name, _winapi.GENERIC_READ | _winapi.GENERIC_WRITE, 0, _winapi.NULL,
                                 _winapi.OPEN_EXISTING, 0, _winapi.NULL)
        try:
            _winapi.ConnectNamedPipe(srv)
        except OSError as e:
            if e.winerror != 535:
                raise
        _winapi.SetNamedPipeHandleState(cli, _winapi.PIPE_READMODE_MESSAGE, None, None)
        proc = _winapi.OpenProcess(_winapi.PROCESS_DUP_HANDLE, False, pid)
        try:
            remote = _winapi.DuplicateHandle(_winapi.GetCurrentProcess(), cli, proc, 0, False,
                                             _winapi.DUPLICATE_SAME_ACCESS)
        finally:
            _winapi.CloseHandle(proc)
            _winapi.CloseHandle(cli)
        BOX.mkdir(parents=True, exist_ok=True)
        for old in BOX.glob(f"h-{pid}-*"):
            old.unlink(missing_ok=True)
        (BOX / f"h-{pid}-{time.time_ns():020d}-{remote}").touch()
        self.srv = srv

    def recv(self) -> bytes:
        avail, _ = _winapi.PeekNamedPipe(self.srv)
        data, err = _winapi.ReadFile(self.srv, avail)
        buf = data
        while err == MORE_DATA:
            _, left = _winapi.PeekNamedPipe(self.srv)
            data, err = _winapi.ReadFile(self.srv, left)
            buf += data
        return buf

    def call(self, req: dict, timeout: float) -> dict:
        with self.lock:
            self.seq += 1
            req = {**req, "id": self.seq}
            for attempt in (0, 1):
                try:
                    if self.srv is None:
                        self.open()
                    _winapi.WriteFile(self.srv, json.dumps(req).encode())
                    break
                except OSError:
                    self.close()
                    if attempt:
                        raise
            deadline = time.monotonic() + timeout
            while True:
                if _winapi.PeekNamedPipe(self.srv)[0]:
                    res = json.loads(self.recv())
                    if res.get("id") == self.seq:
                        return res
                elif time.monotonic() > deadline:
                    raise TimeoutError(f"no reply from FL in {timeout}s")
                else:
                    time.sleep(0.005)


LINK = Link()


BOOT = {"t": None}
HARVEST = {"replace": False}
BACKED: set = set()
NOT_OPEN = "FL is not running, and it is not started just for this: open a project in it with project_write(open=true), or ask the user to open one"


def _ensure_loopmidi() -> bool:
    if _running("loopMIDI.exe"):
        return False
    subprocess.Popen([cfg.need("loopmidi_exe")])
    t0 = time.monotonic()
    while not _running("loopMIDI.exe") and time.monotonic() - t0 < 10:
        time.sleep(0.25)
    time.sleep(1.5)
    return True


def _ensure_fl() -> float | None:
    _ensure_loopmidi()
    if not _fl_running():
        flproc.launch([cfg.need("fl_exe")])
        LINK.close()
        LINK.pid = None
        BOOT["t"] = time.monotonic()
    if BOOT["t"] is None:
        return None
    t0 = time.monotonic()
    while True:
        try:
            LINK.call({"op": "probe"}, 3)
            took = round(time.monotonic() - BOOT["t"], 1)
            BOOT["t"] = None
            return took
        except TimeoutError:
            pass
        except Exception:
            LINK.close()
            if not LINK.alive(LINK.pid or 0):
                LINK.pid = None
        crash = _crashed()
        if crash:
            BOOT["t"] = None
            raise RuntimeError(f"while FL was starting: {crash}")
        since = time.monotonic() - BOOT["t"]
        if since > BOOT_GIVEUP:
            BOOT["t"] = None
            raise RuntimeError(f"FL was launched {since:.0f}s ago and the kuruitsugizaki controller script never answered; check it is selected in FL's MIDI settings")
        if time.monotonic() - t0 > BOOT_WAIT:
            raise RuntimeError(f"FL was launched {since:.0f}s ago and is still starting; call again")
        time.sleep(0.5)


def fl(req: dict, timeout: float = 10.0, launch: bool = False) -> dict:
    if _winapi is None:
        return {"ok": False, "error": NO_LIVE}
    if not launch and not _fl_running():
        return {"ok": False, "error": NOT_OPEN}
    try:
        launched = _ensure_fl()
    except RuntimeError as e:
        return {"ok": False, "error": str(e)}
    backup = None
    try:
        if LINK.fl_pid() and LINK.who == "user":
            backup = _backup_user(LINK.pid)
    except flproc.Ambiguous as e:
        return {"ok": False, "error": str(e)}
    except Exception:
        pass
    try:
        res = LINK.call(req, timeout)
    except flproc.Ambiguous as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        crash = _crashed(LINK.pid) or _dialog(LINK.pid)
        if crash:
            return {"ok": False, "error": crash}
        return {"ok": False, "error": f"{e!r}: is FL running with the kuruitsugizaki controller script loaded?"}
    if isinstance(res, dict):
        res["fl"] = {"pid": LINK.pid, "started_by": LINK.who}
        if backup:
            res["backup"] = backup
        if launched is not None:
            res["launched_fl_seconds"] = launched
    return res


@mcp.tool(annotations=LIVE, description=(
    "The paths on this machine the server needs (FL, loopMIDI, FL's Hardware folder, preset libraries), stored in "
    "kuruitsugizaki.json. Call it first in a new install, and whenever another tool answers that a key is not set. "
    "No arguments: every key with its value or the path detected for it, and whether that path exists. key alone: that "
    "key. key and value: set it. Never guess a path or search the disk for one: ask the user where it is, then set it."))
def config(key: Annotated[str | None, Field(description="a key name, as the no-argument call lists them, e.g. 'fl_exe'")] = None,
           value: Annotated[str | None, Field(description="the path to set for key; omit to read the key")] = None) -> dict:
    if key is None:
        return {"file": str(cfg.FILE), "keys": cfg.status()}
    if key not in cfg.KEYS:
        return {"ok": False, "error": f"unknown key {key!r}; keys are {list(cfg.KEYS)}"}
    if value is None:
        return {key: cfg.status()[key]}
    cfg.put(key, value)
    return {"ok": True, key: cfg.status()[key]}


@mcp.tool(annotations=WRITE, description=(
    "Set up the live link to FL. Needed once per install, and again after this folder moves. Close FL first. "
    "It does two things: "
    "1) writes FL's controller script into FL's Settings\\Hardware folder (config key fl_hardware), with this folder's "
    "bridge path in it, replacing an older copy; "
    "2) unless a MIDI input in FL already has the script, makes a loopMIDI port named kuruitsugizaki and assigns the "
    "script to it in FL's MIDI settings. Both live in the registry, which FL rewrites when it closes; if FL was open, "
    "the answer's midi entry says so and what to do by hand. "
    "Returns {ok, installed, bridge, changed, midi, next}. Then start FL and call fl_probe to see the script answer. "
    "Windows with FL Studio only."))
def fl_install() -> dict:
    if _winapi is None:
        return {"ok": False, "error": NO_LIVE}
    try:
        hw = cfg.path("fl_hardware")
    except cfg.Missing as e:
        return {"ok": False, "error": str(e)}
    if not hw.is_dir():
        return {"ok": False, "error": f"{hw} does not exist; ask the user for FL's Settings\\Hardware folder and set fl_hardware"}
    src = (ROOT / "fl" / "device_kuruitsugizaki.py").read_bytes()
    body = re.sub(rb"(?m)^BOX = .*$", f"BOX = {BOX.as_posix()!r}".encode(), src, count=1)
    dest = hw / "kuruitsugizaki" / "device_kuruitsugizaki.py"
    dest.parent.mkdir(exist_ok=True)
    same = dest.exists() and dest.read_bytes() == body
    dest.write_bytes(body)
    import midisetup
    midi = midisetup.ensure(cfg.get("fl_exe"), cfg.get("loopmidi_exe"))
    return {"ok": True, "installed": str(dest), "bridge": BOX.as_posix(), "changed": not same, "midi": midi,
            "next": "Restart FL if it was running; fl_probe answers once the script is loaded." if midi["ok"] else
                    "In FL: Options > MIDI settings, select the loopMIDI input port, set its controller type to kuruitsugizaki. Restart FL if it was running."}


@mcp.tool(annotations=LIVE, description=(
    "Check the live link to FL: returns FL's scripting API version, its embedded Python version, FL's pid and the pipe "
    "handle it holds, or an error saying what is missing. Call it first when a live tool (fl_exec, fl_call, "
    "fl_transport, project_write with open) fails, and after fl_install. When FL is closed it starts it (and loopMIDI) to "
    "test the link and closes it again: launched_fl_seconds says how long FL took, closed_fl that it was closed. Reads "
    "nothing from the project. Windows with FL Studio only."))
def fl_probe() -> dict:
    was = _fl_running()
    res = fl({"op": "probe"}, launch=True)
    if not was and _fl_running():
        _close_fl()
        res["closed_fl"] = True
    return res


def _dialog(pid: int | None) -> str | None:
    if not pid:
        return None
    found = flproc.dialogs(pid, ROOT / "tmp" / "fl_dialogs")
    if not found:
        return None
    what = "; ".join(f"'{d['title']}' ({d['class']}), picture {d.get('picture')}" for d in found)
    return (f"FL (pid {pid}) is showing a dialog, and the controller script cannot answer until it is closed: {what}. "
            "Nothing more is sent to FL while it is up.")


def _crashed(pid: int | None = None) -> str | None:
    for fpid, info in flproc.crashes().items():
        if pid is not None and fpid != pid:
            continue
        mine = fpid in flproc.owned()
        if mine:
            flproc.reap(fpid)
            LINK.close()
            LINK.pid = None
        cause = ", ".join(f"{k} {v}" for k, v in info.items() if k != "werfault") or "cause not in the Application log yet"
        return (f"FL (pid {fpid}) crashed: {cause}. " + ("It was started by the harness, so it, its crash handler and the Windows crash dialog were closed." if mine
                else "The user started it, so its crash dialog is left open."))
    return None


def _backup_user(pid: int) -> dict | None:
    import shutil
    title = _fl_title()
    if (pid, title) in BACKED:
        return None
    BACKED.add((pid, title))
    path, why = flproc.project_file(pid, title, cfg.get("fl_exe"), cfg.documents() / "Image-Line" / "FL Studio" / "Projects")
    if path:
        dest = ROOT / "tmp" / "backups" / f"{path.stem}-{time.strftime('%Y%m%d-%H%M%S')}.flp"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        out = {"of": str(path), "to": str(dest), "how": why}
    else:
        out = {"not_made": why}
    try:
        if LINK.call({"op": "exec", "code": "import general\nresult = general.getChangedFlag()"}, 5).get("value"):
            out["unsaved_changes"] = "FL holds changes the copy on disk does not have"
    except Exception:
        pass
    with open(ROOT / "tmp" / "backups" / "backups.log", "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": time.strftime("%Y-%m-%d %H:%M:%S"), "pid": pid, "title": title, **out}) + "\n")
    return out


def _close_fl(timeout: float = 30.0):
    mine = [p for p in flproc.owned() if p in flproc.pids()]
    for p in mine:
        note = _dialog(p)
        if note:
            raise RuntimeError(f"FL was not closed: {note}")
    if mine:
        try:
            if _live("import general\nresult = general.getChangedFlag()"):
                _live("import transport, midi\nresult = transport.globalTransport(midi.FPT_Save, 1)")
                t0 = time.monotonic()
                while _live("import general\nresult = general.getChangedFlag()") and time.monotonic() - t0 < 10:
                    time.sleep(0.25)
        except RuntimeError:
            pass
    for p in mine:
        subprocess.run(["taskkill", "/PID", str(p)], capture_output=True)
    t0 = time.monotonic()
    while any(p in flproc.pids() for p in mine) and time.monotonic() - t0 < timeout:
        time.sleep(0.5)
    LINK.close()
    LINK.pid = None
    left = [p for p in mine if p in flproc.pids()]
    if left:
        raise RuntimeError(f"FL did not close within {timeout:.0f}s: " + (" ".join(filter(None, (_dialog(p) for p in left))) or "no dialog found"))


@mcp.tool(annotations=RAW, description=(
    "Call one function of FL's scripting API inside the running FL and return what it returns: {ok, value} or "
    "{ok: false, error}. For a single read or change, e.g. a parameter name or a mixer level of the open project. Use "
    "fl_exec for several calls or logic; use project_read and project_write for anything the .flp file holds, which "
    "need no FL. A setter changes the open project as an edit by hand would; nothing is saved. Needs FL open; it is "
    "not started for this. "
    "Windows with FL Studio only."))
def fl_call(fn: Annotated[str, Field(description="module.function as FL's API names it, e.g. 'plugins.getParamName'")],
            args: Annotated[list | None, Field(description="its positional arguments, e.g. [0, 5, -1]")] = None) -> dict:
    return fl({"op": "call", "fn": fn, "args": args or []})


@mcp.tool(annotations=RAW, description=(
    "Run Python inside the running FL's embedded interpreter, where FL's modules (channels, mixer, plugins, transport, "
    "patterns, general ...) import. For live reads or changes that need several calls or logic; one call is simpler with "
    "fl_call. Returns {ok, value} with what the code assigns to `result`, or {ok: false, error} with the traceback. FL's "
    "sandbox refuses files, sockets and pipes. Changes act on the open project and are not saved. Needs FL open; "
    "it is not started for this. Windows with FL Studio only."))
def fl_exec(code: Annotated[str, Field(description="Python source; assign the answer to `result`")],
            out: Annotated[str | None, Field(description="write the result as JSON to this path (relative to the repo) and return only its size, for large reads; also when `result` is {'__out__': path, 'data': value}")] = None,
            timeout: Annotated[float, Field(description="seconds to wait for FL's answer")] = 10.0) -> dict:
    res = fl({"op": "exec", "code": code}, float(timeout))
    v = res.get("value")
    if not out and isinstance(v, dict) and isinstance(v.get("__out__"), str):
        out = v["__out__"]
        res = {**res, "value": v.get("data")}
    if not out or not res.get("ok"):
        return res
    dest = Path(out) if Path(out).is_absolute() else ROOT / out
    dest.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(res.get("value"), ensure_ascii=False, indent=1)
    dest.write_text(body, encoding="utf-8")
    v = res.get("value")
    return {"ok": True, "out": str(dest), "bytes": len(body.encode("utf-8")), "type": type(v).__name__,
            "len": len(v) if isinstance(v, (list, dict, str)) else None}


def _live(code: str, timeout: float = 5.0):
    r = fl({"op": "exec", "code": code}, timeout)
    if not r.get("ok"):
        raise RuntimeError(r.get("error"))
    return r["value"]


def _running(image: str) -> bool:
    if os.name != "nt":
        return False
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {image}", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    return f'"{image.lower()}"' in out.lower()


def _fl_running() -> bool:
    return _running("FL64.exe")


def _fl_title() -> str:
    import ctypes
    from ctypes import wintypes
    user, found = ctypes.windll.user32, []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def each(h, _):
        pid, buf = wintypes.DWORD(), ctypes.create_unicode_buffer(512)
        user.GetWindowThreadProcessId(wintypes.HWND(h), ctypes.byref(pid))
        user.GetClassNameW(wintypes.HWND(h), buf, 512)
        if pid.value == LINK.pid and buf.value == "TFruityLoopsMainForm":
            user.GetWindowTextW(wintypes.HWND(h), buf, 512)
            found.append(buf.value)
        return True

    user.EnumWindows(each, 0)
    return found[0] if found else ""


def _save_open(protect: Path | None = None, timeout: float = 5.0) -> dict:
    if not _fl_running():
        return {"saved": False, "reason": "FL not running"}
    before = protect.read_bytes() if protect and protect.exists() else None
    _live("import transport\ntransport.stop()\nresult = 0")
    title = _fl_title()
    if title and " - " not in title:
        if _live("import general\nresult = general.getChangedFlag()"):
            raise RuntimeError("FL holds an untitled project with unsaved changes, and saving it would stop at a Save as dialog; ask the user to save it under a name in FL or discard it, then call again")
        return {"saved": False, "reason": "untitled project without changes"}
    _live("import transport, midi\nresult = transport.globalTransport(midi.FPT_Save, 1)")
    t0 = time.monotonic()
    while _live("import general\nresult = general.getChangedFlag()") and time.monotonic() - t0 < timeout:
        time.sleep(0.25)
    if _live("import general\nresult = general.getChangedFlag()"):
        raise RuntimeError("FL still reports unsaved changes after saving; a save dialog may be open")
    res = {"saved": True}
    if before is not None and protect.read_bytes() != before:
        protect.write_bytes(before)
        res["restored"] = str(protect)
    return res


def _open(path: Path, names: list[str], timeout: float = 120.0) -> dict:
    running = flproc.pids()
    if len(running) > 1:
        raise RuntimeError(f"{len(running)} FL instances are open (pids {running}); FL opens a file in the newest one, not a chosen one, so close the others and call again")
    if running:
        _save_open(path)
        subprocess.Popen([cfg.need("fl_exe"), str(path)])
    else:
        _ensure_loopmidi()
        flproc.launch([cfg.need("fl_exe"), str(path)])
    code = "import channels\nresult = [channels.getChannelName(i, True) for i in range(channels.channelCount(True))]"
    t0 = checked = time.time()
    while time.time() - t0 < timeout:
        time.sleep(0.5)
        r = fl({"op": "exec", "code": code}, 5)
        if not r.get("ok"):
            if "crashed" in str(r.get("error")):
                raise RuntimeError(f"while opening {path.name}: {r['error']}")
            if "dialog" in str(r.get("error")):
                raise RuntimeError(f"while opening {path.name}: {r['error']}")
            if time.time() - checked > 2:
                checked = time.time()
                crash = _crashed() or next((d for d in (_dialog(p) for p in flproc.pids()) if d), None)
                if crash:
                    raise RuntimeError(f"while opening {path.name}: {crash}")
            LINK.close()
            if not LINK.alive(LINK.pid or 0):
                LINK.pid = None
        elif r["value"] == names:
            return {"opened": str(path), "seconds": round(time.time() - t0, 1)}
    raise TimeoutError(f"FL did not show the project's channels within {timeout}s")


def _transport(action: str, mode: str | None = None, pattern: int | None = None) -> dict:
    code = "import transport, patterns\n"
    if mode:
        code += f"if transport.getLoopMode() != {1 if mode == 'song' else 0}:\n    transport.setLoopMode()\n"
    if pattern:
        code += f"patterns.jumpToPattern({int(pattern)})\n"
    if action == "play":
        code += "transport.setSongPos(0)\nif not transport.isPlaying():\n    transport.start()\n"  # start() toggles: a second play would pause
    elif action == "stop":
        code += "transport.stop()\n"
    code += "result = {'playing': transport.isPlaying(), 'mode': 'song' if transport.getLoopMode() else 'pattern'}"
    return _live(code)


@mcp.tool(annotations=READ, description=(
    "Read one FL Studio .flp file into JSON; FL need not run and the file is not changed. Use it to see what a project "
    "holds, to take parts from it, or to check what project_write wrote. For the style across many projects use "
    "profile; for the project open in FL right now, fl_exec. Views: 'summary' (start here: instruments, per-pattern "
    "stats, a per-track arrangement timeline, mixer effects); 'compact' (default: every note and clip as rows, the same "
    "shape project_write accepts; notes [bar, beat, tick, len_ticks, key, vel, instrument#], clips [track, bar, beat, "
    "tick, len_ticks, src, trim?] where src is a pattern id, s<N> a sample, a<N> an automation clip); 'full' (exact, "
    "round-trips byte for byte; large). Fails with the parser's error on a file that is not an .flp."))
def project_read(path: Annotated[str, Field(description="the .flp file, absolute or relative to the repo")],
                 view: Annotated[str, Field(description="'compact', 'summary' or 'full'")] = "compact",
                 patterns: Annotated[list[str] | None, Field(description="only these pattern ids (compact and full)")] = None,
                 arrangements: Annotated[list[str] | None, Field(description="only these arrangements, by name")] = None,
                 unused: Annotated[bool, Field(description="also list patterns not placed in the playlist and parked clips")] = False) -> dict:
    _reload()
    import view as v
    return v.read(path, view, patterns, arrangements, unused)


def _reload():
    import importlib
    import sys as _sys
    for name in ("config", "flp", "automation", "levels", "sylenth1", "serum2", "presets", "mixerfx", "project", "vst3state", "library", "writer", "view", "style"):
        if name in _sys.modules:
            importlib.reload(_sys.modules[name])
    import library
    library.harvester = _harvest


def _harvest(e: dict) -> bytes:
    import flp
    import mixerfx
    import project
    import writer
    was = _fl_running()
    if was and not HARVEST["replace"]:
        raise RuntimeError(f"a {e['name']} preset needs a saved state of {e['name']}, made once by opening it in FL, and FL has a project open that this write does not replace: write with open=true, or close FL and write again")
    out = ROOT / "tmp" / "states" / f"{e['kind']}_{e['id']}_{e['format']}.flp"
    spec = {"plugin": e["name"], "format": e["format"]}
    doc = {"patterns": [], "arrangements": [{"name": "A", "clips": []}]}
    tag = f"harvest {e['id']}"
    if e["kind"] == "instrument":
        doc["instruments"] = [{"id": tag, "kind": "plugin", **spec}]
    else:
        doc["instruments"] = [{"id": tag, "kind": "sampler"}]
        doc["mixer"] = {"effects": [{"track": 1, "slot": 0, **spec}]}
    raw, _ = writer.build(doc)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)
    back = project.export(str(out))
    _open(out.resolve(), [c["name"] for c in sorted(back["instruments"] + back["samples"] + back["automation"], key=lambda c: c["ch"])])

    def saved() -> bytes:
        before = out.stat().st_mtime_ns
        _live("import transport, midi\nresult = transport.globalTransport(midi.FPT_Save, 1)")
        t0 = time.monotonic()
        while out.stat().st_mtime_ns == before and time.monotonic() - t0 < 20:
            time.sleep(0.1)
        if out.stat().st_mtime_ns == before:
            raise RuntimeError(f"FL did not save {out} within 20 s, so {e['name']}'s state could not be read")
        lay = writer.layout(flp.parse(out.read_bytes()))
        if e["kind"] == "instrument":
            blk = next(b for b in lay["channels"] if next((int.from_bytes(x.data, "little") for x in b if x.id == 21), None) == 2)
        else:
            blk = mixerfx.block(lay["tail"], 1, 0)
        s = next((x.data for x in blk if x.id == 213), None)
        if s is None:
            raise RuntimeError(f"FL saved no state for {e['name']} in {out}")
        return s

    st = saved()
    try:
        _harvest_programs(e, saved, (0, -1) if e["kind"] == "instrument" else (1, 0))
    finally:
        if not was and not HARVEST["replace"]:
            _close_fl()
    return st


def _harvest_programs(e: dict, saved, loc: tuple[int, int], cap: int = 128) -> int:
    import library
    i, s = loc
    n, prog = _live(f"import plugins\nresult = (plugins.getPresetCount({i}, {s}), next((k for k in range(plugins.getParamCount({i}, {s})) if plugins.getParamName(k, {i}, {s}) == 'Program'), None))", 30)
    if not n or n < 2 or prog is None:
        return 0
    d = library.programs_dir(e)
    d.mkdir(parents=True, exist_ok=True)
    index, seen = [], set()
    for k in range(min(n, cap)):
        _live(f"import plugins\nplugins.setParamValue({k} / {n - 1}, {prog}, {i}, {s})\nresult = 0")
        time.sleep(0.3)
        name = str(_live(f"import plugins\nresult = plugins.getParamValueString({prog}, {i}, {s})")).strip()
        state = saved()
        if not name or state in seen:
            continue
        seen.add(state)
        f = d / f"{k:03d}.bin"
        f.write_bytes(state)
        index.append({"name": name, "file": f.name, "program": k})
    (d / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(index)


@mcp.tool(annotations=WRITE, description=(
    "Write a project document to an .flp file, replacing any file at path. This is how a piece gets made.\n\n"
    "The document: the compact form project_read returns, or its full form. The field reference is README.md, "
    "'Project JSON, compact form'; examples/README.md has a working document per feature. Read one before a first write.\n\n"
    "Sounds:\n"
    "- an instrument is a plugin by name (see plugins) with an optional preset, or a channel copied from a saved project, "
    "state {from: file, channel: n};\n"
    "- an effect is mixer.effects {track, slot, plugin} or one copied, {track, slot, from: {file, track, slot}}.\n\n"
    "Units that are easy to get wrong: 96 ticks per beat, 4/4; keys like 'D#4' with MIDI 60 = C4; mixer volume 0.8 = 0 dB; "
    "a tempo automation value is (bpm - 60) / 120.\n\n"
    "Without open, FL need not run. With open or play, FL first saves the project it has open (so no dialog appears), "
    "then opens this one.\n\n"
    "Returns the file read back (channels, notes per pattern, clips per arrangement) and the writer's warnings; read them."))
def project_write(doc: Annotated[dict, Field(description="the project document, compact or full")],
                  path: Annotated[str, Field(description="the .flp to write, absolute or relative to the repo; pieces go to projects/music/<piece>.flp")],
                  open: Annotated[bool, Field(description="open it in FL afterwards, launching FL if needed")] = False,
                  play: Annotated[str | None, Field(description="'song' or 'pattern': open it and start playback")] = None) -> dict:
    _reload()
    import project
    import writer
    HARVEST["replace"] = bool(open or play)
    raw, warn = writer.build(doc)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    saved = None
    if (open or play) and _fl_running():
        try:
            saved = _save_open()
        except RuntimeError as e:
            return {"open_error": str(e)}
    out.write_bytes(raw)
    back = project.export(str(out))
    res = {"wrote": str(out), "bytes": len(raw), "warnings": warn,
           "channels": [c["name"] for c in back["instruments"] + back["samples"] + back["automation"]],
           "patterns": {p["id"]: len(p["notes"]) for p in back["patterns"]},
           "clips": {a["name"]: len(a["clips"]) for a in back["arrangements"]}}
    if saved:
        res["saved_open_project"] = saved
    if open or play:
        names = sorted((c for c in back["instruments"] + back["samples"] + back["automation"]), key=lambda c: c["ch"])
        try:
            res.update(_open(out.resolve(), [c["name"] for c in names]))
        except (RuntimeError, TimeoutError) as e:
            res["open_error"] = str(e)
            return res
    if play:
        res["transport"] = _transport("play", play)
    return res


@mcp.tool(annotations=WRITE, description=(
    "Render an .flp to audio: a .wav and .mp3 beside it (replacing earlier ones), then spectrogram and stereo "
    "statistics, so the result can be read as numbers and pictures. Call it after project_write to check a piece. FL "
    "renders from the command line, so the FL that is open is saved first (path itself is restored if that save "
    "overwrote it) and closed. Runs detached and returns at once with the log file to read for the results and file "
    "names; a 2-minute piece takes under a minute. Windows with FL Studio only."))
def fl_render(path: Annotated[str, Field(description="the .flp to render")],
              reopen: Annotated[bool, Field(description="open the project in FL again when done")] = True,
              key: Annotated[str | None, Field(description="the key the piece is written in, e.g. 'F minor' or 'G#m'; "
                                                           "the log then says how much pitch energy falls outside its scale")] = None) -> dict:
    target = Path(path).resolve()
    if not target.exists():
        return {"ok": False, "error": f"{target} does not exist"}
    try:
        cfg.need("fl_exe")
    except cfg.Missing as e:
        return {"ok": False, "error": str(e)}
    try:
        saved = _save_open(target)
    except RuntimeError as e:
        return {"ok": False, "error": str(e)}
    logs = ROOT / "tmp" / "render_logs"
    logs.mkdir(parents=True, exist_ok=True)
    log = logs / f"{target.stem}-{time.strftime('%H%M%S')}.log"
    import sys as _sys
    cmd = ([_sys.executable, "-B", str(ROOT / "scripts" / "render.py"), str(target), "--close"] + (["--reopen"] if reopen else [])
           + (["--key", key] if key else []))
    with open(log, "w", encoding="utf-8") as fh:
        subprocess.Popen(cmd, cwd=str(ROOT), stdin=subprocess.DEVNULL, stdout=fh, stderr=subprocess.STDOUT,
                         creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    LINK.close()
    LINK.pid = None
    return {"ok": True, "rendering": str(target), "log": str(log), "saved_open_project": saved}


def _lib(fn):
    _reload()
    import library
    try:
        return fn(library)
    except (KeyError, ValueError, cfg.Missing) as e:
        return {"ok": False, "error": str(e.args[0]) if e.args else str(e)}


@mcp.tool(annotations=READ, description=(
    "List the plugins this machine has: every plugin in FL's plugin database, and every tuned instance in the optional "
    "library project. Call it to choose instruments and effects before project_write; then presets for a plugin's "
    "presets, params for its automatable parameters. Each row: name, kind (instrument or effect), vendor, format (native, "
    "vst3, clap, vst), source (fl or library), how many presets load by name, whether it has a parameter map. Any of "
    "them goes into project_write by name: an instrument as {kind: plugin, plugin: <name>, preset?, format?}, an effect "
    "as mixer.effects [{track, slot, plugin: <name>, preset?, format?}]; without a preset it arrives as if dragged in "
    "fresh from FL's browser, a library instance as saved. A plugin installed in several formats is one name (native, "
    "then vst3, clap, vst unless format is given). By default it lists only VST3 and CLAP plugins; native=true adds "
    "FL's own. Reads files only; FL need not run."))
def plugins(query: Annotated[str | None, Field(description="keep names containing this text, case-insensitive, e.g. 'serum'; omit for all")] = None,
            native: Annotated[bool, Field(description="true also lists FL's own (native) plugins")] = False) -> dict:
    def go(L):
        rows = L.summary(query, native)
        res = {"plugin_db": str(L.db_root()), "library": str(L.lib_path()), "count": len(rows), "plugins": rows}
        if not native:
            res["note"] = "FL's own plugins are not listed; native=true lists them"
        return res
    return _lib(go)


@mcp.tool(annotations=READ, description=(
    "List the presets that load by name for one plugin; an id goes into project_write as an instrument's or effect's "
    "preset. Call it after plugins, when choosing a sound. Returns {plugin, kind, total, presets}; total counts every "
    "match, and when there are more than limit the list is an even spread across the preset folders, each folder an "
    "equal share, not the first ones. A plugin name that matches nothing or several "
    "plugins returns {ok: false, error} naming the candidates. Reads files only; FL need not run."))
def presets(plugin: Annotated[str, Field(description="the plugin's name as plugins lists it; a unique part of it works")],
            query: Annotated[str | None, Field(description="words that must all appear in the id, case-insensitive, any order, e.g. 'bass reese'")] = None,
            limit: Annotated[int, Field(description="at most this many ids")] = 200,
            harvest: Annotated[bool, Field(description="first read the plugin's built-in presets from FL (opens it there once, about a second per preset); for a plugin whose presets live inside it, not in files")] = False,
            kind: Annotated[str | None, Field(description="'instrument' or 'effect', for a name that is both (Serum2); without it the instrument is taken")] = None) -> dict:
    def go(L):
        e = L.find(plugin, kind, prefer="instrument")
        if harvest:
            HARVEST["replace"] = False
            L.refresh(e)
        rows = L.presets(e, query)
        picked = L.spread(rows, max(0, int(limit)))
        res = {"plugin": e["name"], "kind": e["kind"], "total": len(rows), "presets": [r["id"] for r in picked]}
        notes = []
        if len(picked) < len(rows):
            folders = len({r["id"].rsplit("/", 1)[0] if "/" in r["id"] else "" for r in rows})
            notes.append(f"an even spread of {len(picked)} of {len(rows)} across {folders} folders, each folder an equal share; query narrows")
        other = "effect" if e["kind"] == "instrument" else "instrument"
        if not kind and L.has(e["name"], other):
            notes.append(f"{e['name']} is also an {other}; kind='{other}' lists that one")
        if notes:
            res["note"] = "; ".join(notes)
        return res
    return _lib(go)


@mcp.tool(annotations=READ, description="A plugin's automatable parameters, for writing automation: each one's index (the param of an automation target {channel: id, param: index} or {mixer: t, slot: s, param: index}), its name, and what its normalised value means where measured (FL's display at 0, .25, .5, .75 and 1, so a value can be picked for a wanted Hz, dB or %). Call it before automating a plugin or effect knob. It answers only for plugins with a parameter map (plugins shows which); for any other, read names live with fl_call('plugins.getParamName', ...). Not for choosing a sound: plugins lists what is installed, presets a plugin's presets. Reads files only; FL need not run.")
def params(plugin: Annotated[str, Field(description="the plugin's name as plugins lists it; a unique part of it works")],
           query: Annotated[str | None, Field(description="words that must all appear in the parameter name, case-insensitive, e.g. 'filter cutoff'")] = None,
           kind: Annotated[str | None, Field(description="'instrument' or 'effect', for a name that is both; without it the instrument is taken")] = None) -> dict:
    def go(L):
        e = L.find(plugin, kind, prefer="instrument")
        return {"plugin": e["name"], "kind": e["kind"], "params": L.params(e, query)}
    return _lib(go)


@mcp.tool(annotations=LIVE, description="Play or stop whatever project is open in the running FL, to hear it; it changes nothing in any file. action 'play' jumps to the start and plays (from the start, not from where it stopped; called while playing, it restarts from the start). action 'stop' stops playback. mode 'song' plays the arrangement, 'pattern' loops one pattern (pattern: its number, selected first); without mode FL keeps the one it has. Needs FL open with a project; it is not started for this: open one with project_write(open=true), which can also start playback itself (play='song'). Returns {playing, mode}. To get audio out, use fl_render, which saves and closes FL instead. Windows with FL Studio only.")
def fl_transport(action: Annotated[str, Field(description="'play' or 'stop'")],
                 mode: Annotated[str | None, Field(description="'song' or 'pattern'; omit to keep FL's")] = None,
                 pattern: Annotated[int | None, Field(description="in pattern mode, the pattern number to select first")] = None) -> dict:
    if not _fl_running():
        return {"ok": False, "error": NOT_OPEN}
    return _transport(action, mode, pattern)


@mcp.tool(annotations=LIVE, description=(
    "List a person's projects from a folder of their .flp files; for one project's contents use project_read. Reads "
    "every .flp under the folder, subfolders included, and changes none of them; FL need not run; about 2 s for 80 "
    "projects. Returns a table of the projects: tempo, key, "
    "arrangement length in bars, so you know which to open and read in full with project_read; it "
    "decides nothing. Also written as profile.md and profile.json to tmp/profile/<folder name>/. Projects that fail to "
    "read are listed, not fatal; a folder with no .flp returns {ok: false, error}."))
def profile(folder: Annotated[str, Field(description="the folder of .flp projects, absolute or relative to the repo")]) -> dict:
    _reload()
    import style
    try:
        r = style.build(folder)
    except (ValueError, OSError) as e:
        return {"ok": False, "error": str(e)}
    return {"md": r["md"], "json": r["json"], "read": r["read"], "not_read": r["not_read"], "profile": r["profile"]}


def main():
    os.chdir(ROOT)
    mcp.run()


if __name__ == "__main__":
    main()
