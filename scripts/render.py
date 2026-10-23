import argparse
import subprocess
import sys
import time
from pathlib import Path

import config


def fl_pids() -> list[int]:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq FL64.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    return [int(l.split('","')[1]) for l in out.splitlines() if l.lower().startswith('"fl64.exe"')]


def close_fl(timeout: float = 20.0) -> bool:
    pids = fl_pids()
    if not pids:
        return True
    import flproc
    for p in pids:
        subprocess.run(["taskkill", "/PID", str(p)], capture_output=True)
    t0 = time.monotonic()
    while fl_pids() and time.monotonic() - t0 < timeout:
        time.sleep(0.5)
        for p in fl_pids():
            # fl_render saved the project just before; a plugin marking it changed again since asks once more: No
            flproc.press(p, "No")
    return not fl_pids()


def mode_warning(flp: Path):
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here))
    import flp as flpmod
    p = flpmod.parse(flp.read_bytes())
    song = [int.from_bytes(e.data, "little") for e in p.events if e.id == 9]
    pats = sum(1 for e in p.events if e.id == 65)
    if song and song[0] == 0 and pats > 1:
        print(f"WARNING: {flp.name} is saved in pattern mode with {pats} patterns; the command-line render plays the current pattern only, not the song")


def project_bpm(flp: Path) -> float | None:
    """the project's base tempo (event 156, BPM x 1000); tempo automation is not read"""
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here))
    import flp as flpmod
    p = flpmod.parse(flp.read_bytes())
    return next((int.from_bytes(e.data, "little") / 1000 for e in p.events if e.id == 156), None)


def analyse(wav: Path, bpm: float | None, key: str | None = None, detail: bool = False):
    here = Path(__file__).resolve().parent
    cmd = [sys.executable, str(here / "spectro.py"), str(wav)] + (["--bpm", str(bpm)] if bpm else []) + (["--key", key] if key else []) + (["--detail"] if detail else [])
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=here.parent)
    print(r.stdout.rstrip() if r.stdout.strip() else r.stderr[-400:])


def parts_line(flp: Path) -> str | None:
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here))
    import view
    doc = view.export(str(flp))
    if not doc["arrangements"]:
        return None
    runs = []
    for s, e, ks in view.parts_per_bar(doc, doc["arrangements"][0]):
        if runs and runs[-1][2] == len(ks):
            runs[-1] = (runs[-1][0], e, len(ks))
        else:
            runs.append((s, e, len(ks)))
    return "parts sounding per bar: " + ", ".join(f"{view.bar_range(s, e)}: {n}" for s, e, n in runs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("flp")
    ap.add_argument("--formats", default="wav,mp3")
    ap.add_argument("--close", action="store_true", help="ask a running FL to close first (never forced)")
    ap.add_argument("--reopen", action="store_true", help="open the project in FL after rendering")
    ap.add_argument("--bpm", type=float, default=None, help="grid for the per-8-bar rows; default the project's base tempo")
    ap.add_argument("--key", default=None, help="the intended key, e.g. 'F minor': the log reports the pitch energy outside its scale")
    ap.add_argument("--timeout", type=float, default=900)
    ap.add_argument("--detail", action="store_true", help="the full analysis in the log instead of the summary")
    a = ap.parse_args()
    flp = Path(a.flp).resolve()
    mode_warning(flp)
    if fl_pids():
        import flproc
        theirs = [p for p in fl_pids() if p not in flproc.owned()]
        if theirs:
            sys.exit(f"an FL the user started is open (pid {', '.join(map(str, theirs))}); a command-line render hands over to "
                     "it and renders nothing, and this does not close an FL it did not start: close it, then render again")
        if not a.close:
            sys.exit("FL is open; a command-line render hands over to it and renders nothing. Pass --close.")
        if not close_fl():
            sys.exit("FL did not close within 20 s (probably a save dialog); left as is, nothing rendered")
    fmts = [f.strip().lower() for f in a.formats.split(",") if f.strip()]
    outs = [flp.with_suffix("." + f) for f in fmts]
    before = {o: o.stat().st_mtime if o.exists() else None for o in outs}
    t0 = time.monotonic()
    try:
        fl_exe = config.need("fl_exe")
    except config.Missing as e:
        sys.exit(str(e))
    import flproc
    p = subprocess.Popen([fl_exe, "/R", "/E" + ",".join(fmts), str(flp)])
    # This FL only renders. When it is done it closes, and a project that loading its plugins marked changed makes it
    # ask "Save changes?" first and wait there. The file was saved before the render, so that question is answered No;
    # an FL that still does not close once its files are written is closed.
    sizes, stable, answered = {}, None, False
    while p.poll() is None:
        if time.monotonic() - t0 > a.timeout:
            sys.exit(f"render still running after {a.timeout:.0f} s; left running")
        time.sleep(0.25)
        now = {o: o.stat().st_size for o in outs if o.exists() and o.stat().st_mtime != before[o]}
        if len(now) < len(outs) or now != sizes:
            sizes, stable = now, None
            continue
        stable = stable or time.monotonic()
        if time.monotonic() - stable < 1.0:
            continue
        title = flproc.press(p.pid, "No")
        if title and not answered:
            answered = True
            print(f"answered No to FL's {title!r} (save changes) after the render; the project was saved before it")
        if time.monotonic() - stable > 60:
            subprocess.run(["taskkill", "/F", "/PID", str(p.pid)], capture_output=True)
            print("the render's FL had not closed 60 s after writing its files; closed")
            p.wait()
            break
    took = time.monotonic() - t0
    done = [o for o in outs if o.exists() and o.stat().st_mtime != before[o]]
    print(f"FL exited {p.returncode} after {took:.1f} s; new files: {[str(o) for o in done]}")
    missing = [o for o in outs if o not in done]
    if missing:
        print(f"not written: {[str(o) for o in missing]}")
    wav = next((o for o in done if o.suffix == ".wav"), None) or next(iter(done), None)
    if wav:
        analyse(wav, a.bpm or project_bpm(flp), a.key, a.detail)
        try:
            line = parts_line(flp)
        except Exception as e:
            line = f"parts sounding per bar: not read ({type(e).__name__}: {e})"
        if line:
            print(line)
        print(f"next: render_report('{flp}') returns this with the spectrogram picture; look at it before handing the piece over")
    if a.reopen:
        flproc.launch([fl_exe, str(flp)])
        print("reopened in FL")


if __name__ == "__main__":
    main()
