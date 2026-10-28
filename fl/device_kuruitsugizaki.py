# name=kuruitsugizaki
import json
import os
import sys

try:
    import _winapi
except ImportError:  # macOS: no pipe; requests arrive as SysEx on this script's MIDI input (OnSysEx)
    _winapi = None

import device
import general

BOX = ""
MORE_DATA = 234
st = {"h": None, "name": None, "buf": b"", "tick": 0, "err": None, "mid": None, "parts": {}}
# SysEx framing, as scripts/coremidi.py: F0 7D 6B 7A, way (1 to FL, 2 from FL), message id, chunk index, chunk count
# (two 7-bit bytes each), then ASCII JSON, F7.
HEAD = bytes((0xF0, 0x7D, 0x6B, 0x7A))
CHUNK = 240


def probe():
    return {"api": general.getVersion(), "python": sys.version, "pid": os.getpid(), "handle": st["h"]}


def handle(raw):
    rid = None
    try:
        req = json.loads(raw)
        rid = req.get("id")
        op = req["op"]
        if op == "probe":
            val = probe()
        elif op == "call":
            mod, fn = req["fn"].split(".", 1)
            val = getattr(__import__(mod), fn)(*req.get("args", []))
        elif op == "exec":
            scope = {}
            exec(req["code"], scope)
            val = scope.get("result")
        else:
            raise ValueError("unknown op " + repr(op))
        return {"id": rid, "ok": True, "value": val}
    except Exception as e:
        return {"id": rid, "ok": False, "error": repr(e)}


def drop():
    h = st["h"]
    st.update(h=None, buf=b"")
    if h is not None:
        try:
            _winapi.CloseHandle(h)
        except Exception:
            pass


def adopt():
    if not BOX:
        return
    mine = "h-%d-" % os.getpid()
    names = sorted(n for n in os.listdir(BOX) if n.startswith(mine))
    if not names or names[-1] == st["name"]:
        return
    drop()
    st.update(h=int(names[-1].split("-")[3]), name=names[-1])


def pump():
    avail, _ = _winapi.PeekNamedPipe(st["h"])
    if not avail:
        return False
    data, err = _winapi.ReadFile(st["h"], avail)
    st["buf"] += data
    if err == MORE_DATA:
        return True
    raw, st["buf"] = st["buf"], b""
    _winapi.WriteFile(st["h"], json.dumps(handle(raw), default=repr).encode())
    return True


def frames(mid, data):
    n = max(1, -(-len(data) // CHUNK))
    return [HEAD + bytes((2, mid >> 7 & 127, mid & 127, i >> 7, i & 127, n >> 7, n & 127)) + data[i * CHUNK:(i + 1) * CHUNK] + b"\xf7"
            for i in range(n)]


def OnSysEx(event):
    s = bytes(event.sysex)
    if len(s) < 12 or s[:4] != HEAD or s[4] != 1:
        return
    event.handled = True
    mid, i, n = s[5] << 7 | s[6], s[7] << 7 | s[8], s[9] << 7 | s[10]
    if mid != st["mid"] or i == 0:
        st.update(mid=mid, parts={})
    st["parts"][i] = s[11:-1]
    if len(st["parts"]) < n:
        return
    raw = b"".join(st["parts"].get(k, b"") for k in range(n))
    st.update(mid=None, parts={})
    for f in frames(mid, json.dumps(handle(raw), default=repr).encode()):
        device.midiOutSysex(f)


def OnInit():
    print("kuruitsugizaki", probe())


def OnDeInit():
    drop()


def OnIdle():
    if _winapi is None:
        return
    st["tick"] += 1
    try:
        if st["h"] is None or st["tick"] % 25 == 0:
            adopt()
        for _ in range(64):
            if st["h"] is None or not pump():
                break
        st["err"] = None
    except Exception as e:
        drop()
        if getattr(e, "winerror", None) in (109, 232):
            return
        if repr(e) != st["err"]:
            st["err"] = repr(e)
            import traceback
            print("kuruitsugizaki pipe error", traceback.format_exc())
