# name=kuruitsugizaki
import json
import os
import sys

import _winapi

import general

BOX = ""
MORE_DATA = 234
st = {"h": None, "name": None, "buf": b"", "tick": 0, "err": None}


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


def OnInit():
    print("kuruitsugizaki", probe())


def OnDeInit():
    drop()


def OnIdle():
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
