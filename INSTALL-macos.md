# Installing kuruitsugizaki on macOS (fork: `macos` branch)

This branch ports kuruitsugizaki to macOS: reading and writing `.flp` projects, the profile, sample, plugin, preset and
parameter tools, the analysis scripts, the **live link to FL** (`fl_probe`, `fl_call`, `fl_exec`, `fl_transport`), and
rendering (`fl_render`). See "What does not work yet" for the rest.

You need FL Studio for macOS (tested with FL Studio 2026), started and quit at least once, so that its settings exist.
Two things in FL need you once, because the harness starts FL by itself and nothing can click for it:

- **Turn off FL's startup window** (the welcome screen it shows on launch). While it is open FL does not finish
  starting, the controller script does not answer, and FL does not quit when asked.
- **Answer macOS's microphone prompt** the first time FL asks; it also holds FL's startup until answered.

## Setup

Quit FL first, then:

```bash
./setup.sh            # asks before each step; ./setup.sh --yes asks nothing
```

It installs `uv` if missing (Homebrew, else uv's installer), builds `.venv` (`uv sync`), offers ffmpeg, installs FL's
controller script and sets up its MIDI port (below), adds the server to the Claude desktop app's config
(`~/Library/Application Support/Claude/claude_desktop_config.json`, old file kept as `.bak`), and prints one line per
requirement (`.venv/bin/python scripts/doctor.py`, any time; `--live` also asks a running FL for its API version). Then
quit Claude with Cmd-Q, start it again, and in a new chat ask it to read `docs/INDEX.md` in this folder and write
something.

For Claude Code: `claude mcp add --scope user kuruitsugizaki -- <this folder>/.venv/bin/kuruitsugizaki`.

### The live link

The server creates a virtual MIDI port named `kuruitsugizaki` (an input and an output in FL) while it runs; there is no
IAC bus or loopMIDI to set up. FL runs the harness's controller script on that input, and the script's answers go back
on the output with the same port number. `fl_install` (or `doctor.py --install`, which `setup.sh` runs) does both halves
with FL closed:

1. copies `fl/device_kuruitsugizaki.py` into `~/Documents/Image-Line/FL Studio/Settings/Hardware/kuruitsugizaki/`;
2. in FL's settings, `~/Library/Preferences/Image-Line/reg.xml` (a copy is kept as `reg.xml.bak`), gives the
   `kuruitsugizaki` input the script, enables it, and puts the input and the output on the same port number.

If `fl_install` cannot make the setting (FL open, or its settings not found), do it by hand: FL, Options > MIDI settings; Input
`kuruitsugizaki`: enable it, controller type `kuruitsugizaki`, a port number; Output `kuruitsugizaki`: **the same** port
number. A port number left at `-` on the input is the usual reason `fl_probe` times out.

FL connects to the port by itself when the server starts after it, so restarting Claude does not need an FL restart.
The harness starts FL with `open -a` (an FL started any other way does not connect to the port) and quits it as the
Dock's Quit does, so FL saves its settings.

## What works

- `project_read`, `project_write`, `profile`, `samples`, `plugins`, `presets`, `params`, `config`, `render_report`.
- `fl_install`, `fl_probe`, `fl_call`, `fl_exec`, `fl_transport`. `fl_probe` starts FL when it is closed and quits it
  again.
- `project_write(open=true, play=...)` starts FL (or opens the file in the FL the harness started), checks the channels
  loaded, and plays.
- `fl_render` and `render_report`: FL's command-line render (`OsxFL -R -Ewav,mp3 file.flp`; FL for Mac ignores the
  Windows `/R /E` form and just opens the file). An FL you started is left alone and the render refused until you
  close it, as on Windows. The analysis needs ffmpeg (`brew install ffmpeg`).
- The standalone scripts (`chop.py`, `onsets.py`, `vox.py`, `spectro.py`, `loudness.py`...).

## What does not work yet

- FL crash and dialog detection are Windows only: on macOS a crash or an open dialog shows up as FL not answering.
- The backup of a project you opened yourself, made before the first live call to your FL, is Windows only: FL gives
  no project path, keeps no file open, and its window title needs Screen Recording permission.
- On an FL you started, the harness saves nothing: with unsaved changes it asks you to save in FL first, since it
  cannot tell whether saving would stop at a Save As dialog.
- A preset that needs a saved plugin state (`Serum2`, `Vital`, `Diva`, `Sylenth1` presets by id) is made by opening the
  plugin in FL, saving and closing it; the pieces now exist on macOS but the flow is untested (none of those plugins
  was installed). Plugins by name without a preset, FLEX packs, `.fst` presets and NKS presets do not need it.
- Vendor preset folders (`Krush`, `Portal`, `spiff`, `ShaperBox 3`) default to Windows locations; set `vst_presets` in
  `kuruitsugizaki.json` for macOS ones.
- AU plugins are listed (format `au`) but untested.
