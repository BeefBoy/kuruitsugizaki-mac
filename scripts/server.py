import _winapi
import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path

from mcp.server.mcpserver import MCPServer

import config as cfg

ROOT = Path(__file__).resolve().parents[1]
BOX = ROOT / "tmp" / "bridge"
MORE_DATA = 234
BOOT_WAIT = 45.0
BOOT_GIVEUP = 240.0

mcp = MCPServer("kuruitsugizaki")


class Link:
    def __init__(self):
        self.srv = None
        self.pid = None
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
        if os.environ.get("KURUITSUGIZAKI_FL_PID"):
            return int(os.environ["KURUITSUGIZAKI_FL_PID"])
        if self.pid and self.alive(self.pid):
            return self.pid
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq FL64.exe", "/FO", "CSV", "/NH"],
                             capture_output=True, text=True).stdout
        pids = [int(line.split('","')[1]) for line in out.splitlines() if line.startswith('"FL64.exe"')]
        if not pids:
            raise RuntimeError("FL64.exe is not running")
        if len(pids) > 1:
            ps = subprocess.run(["powershell", "-NoProfile", "-Command",
                                 "Get-Process FL64 | Sort-Object StartTime | Select-Object -First 1 -ExpandProperty Id"],
                                capture_output=True, text=True).stdout.strip()
            pids = [int(ps)] if ps.isdigit() else sorted(pids)
        self.pid = pids[0]
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
        subprocess.Popen([cfg.need("fl_exe")])
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
        since = time.monotonic() - BOOT["t"]
        if since > BOOT_GIVEUP:
            BOOT["t"] = None
            raise RuntimeError(f"FL was launched {since:.0f}s ago and the kuruitsugizaki controller script never answered; check it is selected in FL's MIDI settings")
        if time.monotonic() - t0 > BOOT_WAIT:
            raise RuntimeError(f"FL was launched {since:.0f}s ago and is still starting; call again")
        time.sleep(0.5)


def fl(req: dict, timeout: float = 10.0) -> dict:
    try:
        launched = _ensure_fl()
    except RuntimeError as e:
        return {"ok": False, "error": str(e)}
    try:
        res = LINK.call(req, timeout)
    except Exception as e:
        return {"ok": False, "error": f"{e!r}: is FL running with the kuruitsugizaki controller script loaded?"}
    if launched is not None and isinstance(res, dict):
        res["launched_fl_seconds"] = launched
    return res


@mcp.tool()
def test() -> str:
    return "ok"


@mcp.tool(description="Paths on this machine the server needs. No arguments: every key, its value and whether that path exists. key and value: set one. When a tool answers that a key is not set, ask the user where that thing is on their machine and set it here; never guess a path.")
def config(key: str | None = None, value: str | None = None) -> dict:
    if key is None:
        return {"file": str(cfg.FILE), "keys": cfg.status()}
    if key not in cfg.KEYS:
        return {"ok": False, "error": f"unknown key {key!r}; keys are {list(cfg.KEYS)}"}
    if value is None:
        return {key: cfg.status()[key]}
    cfg.put(key, value)
    return {"ok": True, key: cfg.status()[key]}


@mcp.tool(description="Install FL's controller script into FL's Settings\\Hardware folder (config key fl_hardware) with this folder's bridge path written in, and, unless a MIDI input in FL already has the script, make a loopMIDI port named kuruitsugizaki and assign the script to it in FL's MIDI settings (both live in the registry; FL has to be closed for that part, and the answer's midi entry says when it was not done and what to do by hand). Needed once at setup and again after this folder moves; FL picks it up on its next start.")
def fl_install() -> dict:
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


@mcp.tool(description="Report FL's scripting API version, its embedded Python version, FL's pid and the pipe handle it holds.")
def fl_probe() -> dict:
    return fl({"op": "probe"})


@mcp.tool(description="Call one FL scripting API function inside the running FL, e.g. fn='plugins.getParamName', args=[0, 5, -1]. Returns {ok, value} or {ok: false, error}.")
def fl_call(fn: str, args: list | None = None) -> dict:
    return fl({"op": "call", "fn": fn, "args": args or []})


@mcp.tool(description="Run Python inside the running FL's embedded interpreter; FL modules are importable there. Assign to `result` to return a value. out: a path (relative to the repo) to write the result to as JSON instead of returning it, for large reads; the same happens when `result` is {'__out__': path, 'data': value}, for clients whose cached schema lacks out. timeout: seconds to wait for FL, default 10.")
def fl_exec(code: str, out: str | None = None, timeout: float = 10.0) -> dict:
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
    if _fl_running():
        _save_open(path)
    else:
        _ensure_loopmidi()
    subprocess.Popen([cfg.need("fl_exe"), str(path)])
    code = "import channels\nresult = [channels.getChannelName(i, True) for i in range(channels.channelCount(True))]"
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(0.5)
        r = fl({"op": "exec", "code": code}, 5)
        if not r.get("ok"):
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
        code += "transport.setSongPos(0)\ntransport.start()\n"
    elif action == "stop":
        code += "transport.stop()\n"
    code += "result = {'playing': transport.isPlaying(), 'mode': 'song' if transport.getLoopMode() else 'pattern'}"
    return _live(code)


@mcp.tool(description="Read an FL Studio .flp. view='compact' (default): rows with pointers, the same shape project_write accepts; notes [bar, beat, tick, len_ticks, key, vel, instrument#], clips [track, bar, beat, tick, len_ticks, src, trim?] where src is a pattern id, s<N> sample, a<N> automation; unplaced patterns and parked clips are omitted unless unused=true. view='summary': per-pattern stats and a per-track arrangement timeline. view='full': exact round-trip JSON. patterns / arrangements filter by id / name.")
def project_read(path: str, view: str = "compact", patterns: list[str] | None = None, arrangements: list[str] | None = None, unused: bool = False) -> dict:
    _reload()
    import view as v
    return v.read(path, view, patterns, arrangements, unused)


def _reload():
    import importlib
    import sys as _sys
    for name in ("config", "flp", "automation", "levels", "sylenth1", "serum2", "presets", "mixerfx", "project", "vst3state", "library", "writer", "view"):
        if name in _sys.modules:
            importlib.reload(_sys.modules[name])


@mcp.tool(description="Write a project to a .flp. Accepts the compact form project_read returns (format='compact') or the full form. Set base to an existing .flp to inherit its mixer and globals (default projects/init/init.flp). Instruments need state {from: file, channel: n} or a plugin template: serum2, vital, sylenth1, diva, flex; add mixer: n to route. Samples need a path or state. Automation: target {global: tempo} | {mixer: t, param: vol|pan} | {mixer: t, slot: s, param: n} | {channel: id, param: n}, points [[beat, value, tension?]]; tempo value = (bpm-60)/120, mixer vol 0.8 = 0 dB. Keys like 'D#4' (MIDI 60 = C4), 96 ticks per beat, 4/4. Audio clips without trim play the whole sample. open=true loads it in FL; play='song' or 'pattern' starts playback.")
def project_write(doc: dict, path: str, open: bool = False, play: str | None = None) -> dict:
    _reload()
    import project
    import writer
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


@mcp.tool(description="Render a .flp to wav and mp3 beside it with render.py, then spectro and stereo stats. Saves the project open in FL first (restoring `path` if that save overwrote it), so closing FL never raises a save dialog. Runs detached and returns at once; read the log file it names. reopen=true opens the project in FL again afterwards.")
def fl_render(path: str, reopen: bool = True) -> dict:
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
    cmd = [_sys.executable, "-B", str(ROOT / "scripts" / "render.py"), str(target), "--close"] + (["--reopen"] if reopen else [])
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


@mcp.tool(description="Every plugin FL has installed (its plugin database) and every tuned instance in the optional library project: name, kind (instrument or effect), vendor, format (native, vst3, clap, vst), source (fl or library), how many presets load by name, whether it has a parameter map. query filters by name. Any of them goes into project_write by name: an instrument as {kind: plugin, plugin: <name>, preset?: <id>, format?: <format>}, an effect as mixer.effects [{track, slot, plugin: <name>, preset?: <id>, format?}]. Without preset it arrives fresh, as if dragged in from FL's browser (a library instance arrives as saved). A plugin installed in several formats is one name; native, then vst3, clap, vst is preferred unless format is given.")
def plugins(query: str | None = None) -> dict:
    def go(L):
        rows = L.summary(query)
        return {"plugin_db": str(L.db_root()), "library": str(L.lib_path()), "count": len(rows), "plugins": rows}
    return _lib(go)


@mcp.tool(description="A library plugin's presets, by id; the id goes into project_write as preset. query: words that must all appear in the id, e.g. 'bass reese'. limit caps the rows (default 200); total is always the full count.")
def presets(plugin: str, query: str | None = None, limit: int = 200) -> dict:
    def go(L):
        e = L.find(plugin)
        rows = L.presets(e, query)
        return {"plugin": e["name"], "kind": e["kind"], "total": len(rows), "presets": [r["id"] for r in rows[:max(0, int(limit))]]}
    return _lib(go)


@mcp.tool(description="A library plugin's automatable parameters as FL exposes them: index (the param of an automation target {channel: id, param: index} or {mixer: t, slot: s, param: index}), name, and what the knob's normalised value means where measured. query: words that must all appear in the name.")
def params(plugin: str, query: str | None = None) -> dict:
    def go(L):
        e = L.find(plugin)
        return {"plugin": e["name"], "kind": e["kind"], "params": L.params(e, query)}
    return _lib(go)


@mcp.tool(description="FL transport: action 'play' or 'stop'; mode 'song' or 'pattern'; pattern number to select in pattern mode.")
def fl_transport(action: str, mode: str | None = None, pattern: int | None = None) -> dict:
    return _transport(action, mode, pattern)


def main():
    os.chdir(ROOT)
    mcp.run()


if __name__ == "__main__":
    main()
