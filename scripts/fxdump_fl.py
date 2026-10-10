import mixer, plugins

seen, out = set(), {}
for t in range(mixer.trackCount()):
    for s in range(10):
        if not plugins.isValid(t, s):
            continue
        name = plugins.getPluginName(t, s)
        if name in seen:
            continue
        seen.add(name)
        n, empty, lines = plugins.getParamCount(t, s), 0, []
        for i in range(min(n, 4096)):
            pn = plugins.getParamName(i, t, s)
            if not pn:
                empty += 1
                if empty >= 16:
                    break
                continue
            empty = 0
            lines.append("%d\t%s\t%.4f\t%s" % (i, pn, plugins.getParamValue(i, t, s), plugins.getParamValueString(i, t, s)))
        out[name] = {"at": [t, s], "count": n, "params": "\n".join(lines)}
result = out
