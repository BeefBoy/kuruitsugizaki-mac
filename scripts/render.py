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
    for p in pids:
        subprocess.run(["taskkill", "/PID", str(p)], capture_output=True)
    t0 = time.monotonic()
    while fl_pids() and time.monotonic() - t0 < timeout:
        time.sleep(0.5)
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


def analyse(wav: Path, bpm: float | None):
    here = Path(__file__).resolve().parent
    cmd = [sys.executable, str(here / "spectro.py"), str(wav)] + (["--bpm", str(bpm)] if bpm else [])
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=here.parent)
    print(r.stdout.splitlines()[0] if r.stdout else r.stderr[-400:])
    import numpy as np
    sys.path.insert(0, str(here))
    from spectro import decode
    x = decode(str(wav))
    m, s = x[:, 0] + x[:, 1], x[:, 0] - x[:, 1]
    a = np.abs(x)
    pk = a.max()
    runs = int(np.sum((a[1:] >= pk * 0.999) & (a[:-1] >= pk * 0.999)))
    print(f"side/mid {10 * np.log10((s ** 2).sum() / (m ** 2).sum()):.1f} dB  consecutive full-scale samples {runs}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("flp")
    ap.add_argument("--formats", default="wav,mp3")
    ap.add_argument("--close", action="store_true", help="ask a running FL to close first (never forced)")
    ap.add_argument("--reopen", action="store_true", help="open the project in FL after rendering")
    ap.add_argument("--bpm", type=float, default=None)
    ap.add_argument("--timeout", type=float, default=900)
    a = ap.parse_args()
    flp = Path(a.flp).resolve()
    mode_warning(flp)
    if fl_pids():
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
    p = subprocess.Popen([fl_exe, "/R", "/E" + ",".join(fmts), str(flp)])
    while p.poll() is None:
        if time.monotonic() - t0 > a.timeout:
            sys.exit(f"render still running after {a.timeout:.0f} s; left running")
        time.sleep(0.25)
    took = time.monotonic() - t0
    done = [o for o in outs if o.exists() and o.stat().st_mtime != before[o]]
    print(f"FL exited {p.returncode} after {took:.1f} s; new files: {[str(o) for o in done]}")
    missing = [o for o in outs if o not in done]
    if missing:
        print(f"not written: {[str(o) for o in missing]}")
    wav = next((o for o in done if o.suffix == ".wav"), None) or next(iter(done), None)
    if wav:
        analyse(wav, a.bpm)
    if a.reopen:
        subprocess.Popen([fl_exe, str(flp)])
        print("reopened in FL")


if __name__ == "__main__":
    main()
