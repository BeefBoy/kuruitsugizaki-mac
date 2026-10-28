# Installing kuruitsugizaki on macOS (fork: `macos` branch)

This branch ports kuruitsugizaki to macOS: reading and writing `.flp` projects, the profile, sample, plugin, preset and
parameter tools, the analysis scripts, and the **live link to FL** (`fl_probe`, `fl_call`, `fl_exec`, `fl_transport`).
Rendering from the harness (`fl_render`) is still Windows only. See "What does not work yet".

You need FL Studio for macOS (tested with FL Studio 2026), started and quit at least once, so that its settings exist.

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

## What works

- `project_read`, `project_write`, `profile`, `samples`, `plugins`, `presets`, `params`, `config`, `render_report`.
- `fl_install`, `fl_probe`, `fl_call`, `fl_exec`, `fl_transport` on an FL you have open.
- `project_write(open=true)` asks macOS to open the file in FL (`open -a`). Nothing confirms it loaded, and `play` is
  reported as unavailable: press play in FL, or call `fl_transport` once it has loaded.
- The standalone scripts (`chop.py`, `onsets.py`, `vox.py`, `spectro.py`, `loudness.py`...) on audio files you render
  from FL yourself.

## What does not work yet

- `fl_render`: needs FL's command-line render, unverified on macOS. Render from FL (File > Export).
- The live tools do not start FL; open it yourself. FL crash and dialog detection, and the backup of a project you
  opened yourself before the first live call, are Windows only.
- A preset that needs a saved plugin state (`Serum2`, `Vital`, `Diva`, `Sylenth1` presets by id) is made by opening the
  plugin in FL, saving and closing it through the live link; that flow starts and closes FL, so it is not ported yet.
  Plugins by name without a preset, FLEX packs, `.fst` presets and NKS presets do not need it.
- Vendor preset folders (`Krush`, `Portal`, `spiff`, `ShaperBox 3`) default to Windows locations; set `vst_presets` in
  `kuruitsugizaki.json` for macOS ones.
- AU plugins are listed (format `au`) but untested.
