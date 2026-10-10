import builtins
import channels
import mixer
import plugins

SKIP = ("midi cc", "program", "preset", "bank", "patch", "browse", "reserved")


def _locs(only=None, skip=()):
    out = []
    for c in range(channels.channelCount(True)):
        if plugins.isValid(c, -1, True):
            out.append(((c, -1, True), [c, -1], plugins.getPluginName(c, -1, False, True)))
    for t in range(mixer.trackCount()):
        for s in range(10):
            if plugins.isValid(t, s):
                out.append(((t, s), [t, s], plugins.getPluginName(t, s)))
    return [x for x in out if (only is None or x[2] in only) and x[2] not in skip]


def _named(a):
    n = plugins.getParamCount(*a)
    empty = 0
    for i in range(min(n, 4096)):
        nm = plugins.getParamName(i, *a)
        if not nm:
            empty += 1
            if n >= 4096 and empty >= 64:
                break
            continue
        empty = 0
        yield i, nm


def _sweepable(nm):
    low = nm.lower()
    return not any(w in low for w in SKIP)


def _kz_dump(out, only=None, skip=()):
    data = []
    for a, at, name in _locs(only, skip):
        rows = [[i, nm, round(plugins.getParamValue(i, *a), 6), plugins.getParamValueString(i, *a)] for i, nm in _named(a)]
        data.append({"at": at, "plugin": name, "count": plugins.getParamCount(*a), "rows": rows})
    return {"__out__": out, "data": data}


def _kz_sweep(v, phase, only=None, skip=()):
    x = v if phase != "nudge" else (v + 0.001 if v < 1 else v - 0.001)
    count = 0
    for a, at, name in _locs(only, skip):
        for i, nm in _named(a):
            if not _sweepable(nm):
                continue
            if len(a) == 3:
                plugins.setParamValue(x, i, a[0], -1, 0, True)
            else:
                plugins.setParamValue(x, i, a[0], a[1])
            count += 1
    return {"phase": phase, "value": x, "params": count}


def _kz_read(out, only=None, skip=()):
    data = {}
    for a, at, name in _locs(only, skip):
        data["%d,%d" % tuple(at)] = [[i, round(plugins.getParamValue(i, *a), 6), plugins.getParamValueString(i, *a), nm] for i, nm in _named(a) if _sweepable(nm)]
    return {"__out__": out, "data": data}


builtins._kz_dump = _kz_dump
builtins._kz_sweep = _kz_sweep
builtins._kz_read = _kz_read
result = "defined _kz_dump(out, only, skip), _kz_sweep(v, phase, only, skip), _kz_read(out, only, skip)"
