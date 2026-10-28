Read `docs/INDEX.md` first. It is the only index.

# This copy: the macOS fork (branch `macos`)

Upstream (whatanaiceguy/kuruitsugizaki, MIT) is Windows-only. This copy ports the **file half** to macOS: reading and
writing `.flp` projects, and the profile, sample, plugin, preset and parameter tools. The **live link to FL** is still
Windows-only. It was written and tested on Linux with a simulated macOS layout, never on a real Mac. You are on one now,
with FL Studio installed, so the first job is to verify what could only be simulated. `INSTALL-macos.md` has the user-facing
version of this.

## Verify first
1. `./setup.sh` (or `uv sync`), then `.venv/bin/python scripts/doctor.py`. Report every line. The ones that matter:
   - **FL Studio**: found as an app bundle in `/Applications` or `~/Applications`. `fl_exe` on macOS is the `.app`, not an executable.
   - **FL plugin database**: expected at `~/Documents/Image-Line/FL Studio/Presets/Plugin database`. "0 plugins" means FL for
     Mac stores or formats it differently: look at what is in that folder and fix `scripts/library.py`. `plugins` and
     every by-name instrument depend on it.
   - Factory presets: looked for inside the app bundle (`config._mac_factory_presets`); the layout was guessed, so check it.
2. `.venv/bin/python scripts/selftest.py` must pass. Its examples step is skipped unless the plugin database names Sytrus
   and 3xOsc, so on this Mac it may run for the first time: report any failure, do not skip it.
3. Write a small project (README "Project JSON, compact form"; `examples/` has one per feature) and open it with
   `open -a "<FL app>" file.flp` (`project_write(open=true)` does the same). Confirm FL loads it with the right notes,
   channels and tempo.

## Conventions in this fork
- `config.WIN` and `config.MAC` choose platform code. Never hard-code a path: they are keys in `kuruitsugizaki.json`
  (git-ignored), found by `config._places`.
- Windows-only modules (`winreg`, `ctypes.windll`, `_winapi`, `tasklist`, `taskkill`, PowerShell) must stay importable
  but uncalled elsewhere: no top-level `import winreg` in anything the server or `doctor.py` imports on macOS.
- Windows behaviour must not change. `config._places` returns the same values as upstream on Windows; keep it that way.
- Without the live link every live tool answers `NO_LIVE` (`scripts/server.py`); `flproc.pids()` uses `ps` on macOS.

## Not done: the live link on macOS
- Why it is hard: FL's script sandbox refuses files, sockets and pipes. The Windows link creates a named pipe and copies a
  handle into FL's process with `DuplicateHandle` (`_winapi`); the controller script then only reads and writes it. See
  `docs/ARCHITECTURE.md` ("Live link: handle injection"), `fl/device_kuruitsugizaki.py`, and `Link` in `scripts/server.py`.
  macOS has no equivalent.
- Candidate replacement: MIDI SysEx over an IAC Driver bus, as `flapi` and ae5n/fl-mcp do. The controller script handles
  `OnSysEx` and replies with `device.midiOutSysex`; the server side uses `python-rtmidi` or `mido`. Needs message chunking.
  FL also loads a controller script only on a MIDI input that has it assigned, and its settings location on macOS is unknown:
  find it (the Windows version writes the registry, `scripts/midisetup.py`) or make it a documented manual step.
- Depends on the link: `fl_probe`, `fl_call`, `fl_exec`, `fl_transport`, and preset loading that needs a saved plugin
  state (Serum 2, Vital, Diva, Sylenth1 by id). `fl_render` also needs FL's command-line render, unverified on macOS.

## Working here
- Use `.venv/bin/python`, not the system Python.
- Never edit an `.flp` in place. Build with the writer, read back with `project_read`. The byte-identical round trip
  (`docs/ARCHITECTURE.md`) is the invariant; `selftest.py` checks it.
- This folder is a zip export, not a git repo. `git init` first if commits are wanted. Do not push to upstream.
- Work directly and report findings tersely; fix what is clearly broken instead of asking.
