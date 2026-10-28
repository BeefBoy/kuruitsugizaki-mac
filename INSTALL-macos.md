# Installing kuruitsugizaki on macOS (fork: `macos` branch)

This branch ports the **file half** of kuruitsugizaki to macOS: reading and writing `.flp` projects, the profile,
sample, plugin, preset and parameter tools, and the analysis scripts. The **live link to FL** (play/stop, parameter reads
and writes, rendering from the harness) is Windows only in this version. See "What does not work yet".

You need FL Studio 2025 for macOS, started at least once.

## Setup

```bash
./setup.sh            # asks before each step; ./setup.sh --yes asks nothing
```

It installs `uv` if missing (Homebrew, else uv's installer), builds `.venv` (`uv sync`), offers ffmpeg, adds the server to
the Claude desktop app's config (`~/Library/Application Support/Claude/claude_desktop_config.json`, old file kept as
`.bak`), and prints one line per requirement (`.venv/bin/python scripts/doctor.py`, any time). Then quit Claude with
Cmd-Q, start it again, and in a new chat ask it to read `docs/INDEX.md` in this folder and write something.

For Claude Code: `claude mcp add --scope user kuruitsugizaki -- <this folder>/.venv/bin/kuruitsugizaki`.

## What works

- `project_read`, `project_write` (writes the `.flp`), `profile`, `samples`, `plugins`, `presets`, `params`, `config`,
  `render_report`.
- `project_write(open=true)` asks macOS to open the file in FL (`open -a "FL Studio 2025.app" file.flp`). Nothing confirms
  it loaded, and `play` is reported as unavailable: press play in FL.
- The standalone scripts (`chop.py`, `onsets.py`, `vox.py`, `spectro.py`, `loudness.py`...) on audio files you render
  from FL yourself.

## What does not work yet

- `fl_install`, `fl_probe`, `fl_call`, `fl_exec`, `fl_transport`, `fl_render` answer that the live link is Windows only.
  The Windows link copies a named-pipe handle into FL's process (`_winapi`); macOS has no equivalent, so it needs a
  different transport (MIDI SysEx over an IAC bus is the usual one).
- A preset that needs a saved plugin state (`Serum2`, `Vital`, `Diva`, `Sylenth1` presets by id) is made once by opening the
  plugin in FL through the live link, so those presets fail on macOS until the link exists. Plugins by name without a
  preset, FLEX packs, `.fst` presets and NKS presets do not need it.

## Unverified on a real Mac

Written and tested on Linux with a simulated macOS layout. Check these first when you run it on a Mac:

1. `doctor.py` finds FL (`/Applications/FL Studio*.app`) and FL's factory presets inside the bundle.
2. `doctor.py` finds the **FL plugin database** (`~/Documents/Image-Line/FL Studio/Presets/Plugin database`). If it
   reports 0 plugins, FL on macOS may store or format it differently; `plugins` and by-name instruments depend on it.
3. VST/AU plugin entries in that database may carry macOS paths or ids that the parser does not expect.
4. Vendor preset folders (`Krush`, `Portal`, `spiff`, `ShaperBox 3`) default to Windows locations; set `vst_presets` in
   `kuruitsugizaki.json` for macOS ones.
