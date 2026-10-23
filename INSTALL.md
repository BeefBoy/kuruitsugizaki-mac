# Installing kuruitsugizaki

Windows only. You need FL Studio 2025 installed, and started at least once.

There are two ways. The short way is one script; the long way is the same steps by hand, for when you want to see or change each one.

## The short way

1. Put this folder somewhere you can write to, for example `C:\Users\<you>\kuruitsugizaki`. Not under `Program Files`.
2. Close FL Studio.
3. Double-click `setup.bat`.
4. When it says Ready, quit the Claude app fully (tray icon, Quit), start it again, and in a new chat ask it to read `docs/INDEX.md` in this folder and write something.

`setup.bat` says what it is about to do and asks once, then asks again before installing ffmpeg and before touching a Claude config. It uses the paths it finds (FL, loopMIDI, FL's Hardware and Plugin database folders, the Claude desktop config, the Claude Code profile); `setup.bat -Custom` shows each one and asks, Enter keeping it, and asks for your projects and sample folders too. What it does, in order:

| step | what | where it lands |
|---|---|---|
| uv | installs it if missing (winget, else uv's own installer) | your user profile |
| environment | `uv sync` | `.venv` in this folder, about 400 MB |
| loopMIDI | installs it if missing (winget, else it opens the download page and waits) | Program Files |
| ffmpeg | offers to install it if missing (winget); optional | your user profile |
| paths | the ones found are used; with `-Custom` each is shown and asked, and one you type, and your projects and sample folders, are saved | `kuruitsugizaki.json` in this folder |
| controller script | copies `fl/device_kuruitsugizaki.py` with this folder's path written in | FL's `Settings\Hardware\kuruitsugizaki` |
| MIDI port | adds a loopMIDI port named `kuruitsugizaki` | registry, `HKCU\Software\Tobias Erichsen\loopMIDI\Ports` |
| FL's MIDI setting | assigns the controller script to that port | registry, `HKCU\Software\Image-Line\FL Studio <version>\Devices\MIDI input\kuruitsugizaki` |
| Claude desktop app | adds the server under `mcpServers`; the old file is kept beside it as `.bak` | the Microsoft Store build's `claude_desktop_config.json` under `%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude`, else `%APPDATA%\Claude\claude_desktop_config.json`, or the one given with `-Custom` |
| Claude Code | if it is installed, offers `claude mcp add` | Claude Code's user config, or the profile given with `-Custom` |
| check | prints one line per requirement, then starts FL, asks it for its version and closes it again | nothing |

The port and FL's MIDI setting are skipped when an input in FL already has the script. The check alone, any time: `.venv\Scripts\python scripts\doctor.py` (add `--live` to start FL and test the link).

Running it again is safe; it changes only what is missing. From a terminal it takes `-Yes` (no questions), `-Custom` (asks for each path), `-NoLive` (do not start FL), `-NoClaudeCode`, and `-ClaudeConfig <path>` for a config file elsewhere.

## By hand

### 1. Put the folder somewhere

Anywhere you can write to, for example `C:\Users\<you>\kuruitsugizaki`. Not under `Program Files`: the server writes its settings, renders and scratch files inside this folder.

### 2. Install the tools it needs

- **uv**, which builds the Python environment. In PowerShell:
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
  uv fetches a matching Python by itself if you have none.
- **loopMIDI** (by Tobias Erichsen), a virtual MIDI port: `winget install TobiasErichsen.loopMIDI`, or its installer from the author's site. FL loads the harness's controller script only on a MIDI input port, and this provides one. You do not need to keep it open: the server starts it when it needs it.
- **ffmpeg**, used to analyse renders. In PowerShell: `winget install Gyan.FFmpeg`, then open a new terminal so it is on PATH. Without it, renders still work but come back without their analysis.

### 3. Build the environment

In a terminal, in the folder:

```powershell
uv sync
```

This creates `.venv\Scripts\kuruitsugizaki.exe`, the server.

### 4. Add the server to your MCP client

For the Claude desktop app: Settings, Developer, Edit Config (the file is `%APPDATA%\Claude\claude_desktop_config.json`). Add the server under `mcpServers`, with your folder's path and doubled backslashes:

```json
{
  "mcpServers": {
    "kuruitsugizaki": {
      "command": "C:\\Users\\<you>\\kuruitsugizaki\\.venv\\Scripts\\kuruitsugizaki.exe"
    }
  }
}
```

If the file already has an `mcpServers` block, add the `kuruitsugizaki` entry inside it. Quit the app fully and start it again. `.venv\Scripts\python scripts\doctor.py --claude` writes the same entry for you.

For Claude Code: `claude mcp add --scope user kuruitsugizaki -- C:\Users\<you>\kuruitsugizaki\.venv\Scripts\kuruitsugizaki.exe`. Any other MCP client: a stdio server whose command is that exe, no arguments.

### 5. First chat: let the model set it up

Close FL, then in a new chat ask it to set up kuruitsugizaki. It will:

1. call `config`. Paths at their standard places are found by themselves and show as `detected`: FL64.exe, loopMIDI.exe, FL's `Settings\Hardware` folder, FL's Plugin database and preset folders, FLEX packs. For anything not found it asks you; answer with the real path, it is told not to guess.
2. call `fl_install`, which copies the controller script into FL's Hardware folder, adds a loopMIDI port named `kuruitsugizaki` and assigns the script to it in FL's MIDI settings. Its answer has a `midi` entry; when that says `ok`, step 6 is already done.

The usual places:

| what | usually |
|---|---|
| FL64.exe | `C:\Program Files\Image-Line\FL Studio 2025\FL64.exe` |
| loopMIDI.exe | `C:\Program Files (x86)\Tobias Erichsen\loopMIDI\loopMIDI.exe` |
| FL's Hardware folder | `Documents\Image-Line\FL Studio\Settings\Hardware` (FL shows its user data folder under Options, File settings) |
| FLEX packs | `Documents\Image-Line\FLEX\Packs` |

### 6. The MIDI setting in FL, when `fl_install` could not make it

`fl_install` leaves this to you when FL was running, when FL has never been started, or when it cannot find FL's settings. Then:

1. Open loopMIDI and add a port with the `+` button, if it has none; the name does not matter.
2. Restart FL so it sees the port and the installed script.
3. Options, MIDI settings. In the Input list select the loopMIDI port, set **Controller type** to **kuruitsugizaki**, and enable the port.

FL remembers this. You do it once.

### 7. Check

View, Script output in FL shows a line starting `kuruitsugizaki {'api': 38`. Or ask the model to call `fl_probe`; it answers with FL's API version. Or `.venv\Scripts\python scripts\doctor.py --live`.

## Done

From here the model writes projects, opens them in FL, plays and renders them, with any plugin FL has installed (as FL's plugin manager last scanned them) and its presets. It opens FL itself when it opens a project, and leaves FL closed otherwise. Before writing music it should read the docs in `docs/`, starting at `docs/INDEX.md`; if it does not, point it there.

## When something is wrong

- **Every live call times out, or the model says FL is "still starting".** The controller script is not loaded. Run `.venv\Scripts\python scripts\doctor.py`: it names the missing part (no loopMIDI port, no input in FL with the script, the script installed for another folder).
- **You moved the folder.** Run `setup.bat` again, or: update the path in the app's config (step 4), restart the app, ask the model to run `fl_install`, then restart FL.
- **FL closed when the app closed.** FL was started by the server, and closing the app stops the server and what it started. Save your work in FL before quitting the app.
- **A project will not open.** FL holds changes it cannot save without asking you: an untitled project you edited, or a dialog that is already open. Save or discard in FL and ask again.
- **The model cannot find a preset or sample.** It only knows the folders you gave it. Ask it to show `config`, and give it the missing path.
- **A render is refused while your FL is open.** FL passes a command-line render to the FL already running and renders nothing, and the harness does not close an FL you started. Save and close FL; the next render starts and closes its own.
- **To undo the setup.** Close FL and double-click `uninstall.bat`. It removes the Claude entries, the controller script, the `kuruitsugizaki` port and FL's MIDI setting (a port you made yourself is kept, with the script unassigned), deletes the saved plugin states and moves `kuruitsugizaki.json` into `tmp/uninstall`. uv, loopMIDI, ffmpeg and `.venv` stay; delete this folder afterwards to remove the rest. `setup.bat` installs it again.
