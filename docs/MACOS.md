# macOS port

Upstream is Windows-only. The macOS port covers reading and writing `.flp` projects, the profile, sample, plugin, preset
and parameter tools, the live link to FL, starting and quitting FL, and rendering. `../INSTALL-macos.md` is the user-facing version of this.

## Conventions
- `config.WIN` and `config.MAC` choose platform code. Never hard-code a path: they are keys in `kuruitsugizaki.json`
  (git-ignored), found by `config._places`.
- Windows-only modules (`winreg`, `ctypes.windll`, `_winapi`, `tasklist`, `taskkill`, PowerShell) must stay importable
  but uncalled elsewhere: no top-level `import winreg` in anything the server or `doctor.py` imports on macOS.
- Windows behaviour must not change. `config._places` returns the same values as upstream on Windows; keep it that way.
- On macOS `fl_exe` is the `.app` bundle, not an executable. FL is looked for in `/Applications` and `~/Applications`;
  its process is `Contents/MacOS/OsxFL` (`flproc.pids()` uses `ps`).
- The FL plugin database is expected at `~/Documents/Image-Line/FL Studio/Presets/Plugin database`; factory presets
  inside the app bundle (`config._mac_factory_presets`). A fresh FL for Mac has no `Installed/` tree there until the
  Plugin Manager scans, so `library._db_dirs` falls back to the category tree (`Generators/<category>`), where some
  files are old presets with ASCII names; `library._fresh` re-encodes them as UTF-16.
- `%FLStudioFactoryData%` is `Contents/Resources/FL` inside the app (`config.factory_data`).
- After a Plugin Manager scan FL for Mac writes `Installed/<kind>/{Fruity,VST,VST3,AudioUnit}`; `AudioUnit` is format
  `au` (`library.DB_FORMATS`). Vital's data folder is `~/Music/Vital`, read from `~/Library/Application
  Support/vital/Vital.config` (`config._vital_data`). Vital presets by id are verified: the state FL saved carries
  `preset_name`.
- FL's settings ("registry") are `~/Library/Preferences/Image-Line/reg.xml`: the same keys as the Windows registry
  (`Software\Image-Line\FL Studio 26\...`) as XML, every value a string. FL reads it at start and rewrites it when it
  quits, so write it only with FL closed (`midisetup.RegXml`).
- Use `.venv/bin/python`, not the system Python. Check a machine with `scripts/doctor.py --live`, then
  `scripts/selftest.py`.

## Live link: SysEx over a virtual MIDI port
- FL's script sandbox refuses files, sockets and pipes, and macOS has no `DuplicateHandle`, so the Windows design
  (`ARCHITECTURE.md`, "Live link: handle injection") does not carry over. MIDI does: a controller script gets SysEx
  in `OnSysEx` and can send it with `device.midiOutSysex`.
- `scripts/coremidi.py` calls CoreMIDI through ctypes (python-rtmidi has no wheel for every Python and needs a compiler)
  and creates a virtual source and destination, both named `kuruitsugizaki`, with fixed unique IDs so FL keeps its
  settings for them. `MacLink` in `scripts/server.py` opens them when the server starts; a running FL connects to them
  within about a second.
- Framing, the same in `coremidi.py` and `fl/device_kuruitsugizaki.py`: `F0 7D 6B 7A`, way (1 to FL, 2 from FL),
  message id, chunk index, chunk count (two 7-bit bytes each), up to 240 bytes of JSON, `F7`. JSON is ASCII
  (`ensure_ascii`), so it is valid SysEx data without packing. Replies are matched by message id.
- `device.midiOutSysex` goes to the MIDI output whose port number equals the script's input's port number. Both must be
  set, and the same; `midisetup.ensure_mac` writes them.
- One controller script serves both platforms: without `_winapi` it skips the pipe in `OnIdle` and answers SysEx.

## Starting, quitting, rendering
- `flproc.launch` starts FL with `open -a <app> [file]` and waits up to 30 s for the new process (right after an FL
  exits, LaunchServices takes over 10 s). FL's executable started directly does not connect to CoreMIDI's virtual
  ports, so the live link needs `open`. `MacLink` opens its ports before FL is launched.
- `flproc.created` reads a process's start time from `ps` (seconds), which with the pid names an FL the harness owns.
- `flproc.quit_mac` asks FL to quit through `NSRunningApplication terminate` (ctypes and the Objective-C runtime), as
  the Dock's Quit does: FL saves its settings, and no Automation permission is needed. SIGTERM ends FL without that.
- FL's startup window blocks the script and quitting; it must be turned off in FL. The first start also asks for the
  microphone. Neither can be answered by the harness (no dialog detection on macOS).
- Render: `render.render_cmd` runs the app's executable (from `Info.plist`) as `-R -E<fmts> file`; FL renders and exits.
  The Windows `/R /E` form only opens the file on macOS. A render needs no live link, so the direct start is fine.
- `channels.channelCount()` counts the current filter group only; use `channelCount(True)` and
  `getChannelName(i, True)` to see every channel, as `_open` does.
- `_save_open` cannot read FL's window title on macOS (Screen Recording permission), so it saves only an FL the harness
  started; an FL the user started with unsaved changes is refused with a message.

## Not done
- Crash and dialog detection (`flproc.crashes`, `flproc.dialogs`) and the backup of a project the user opened, found by
  FL's window title (`_backup_user`): FL's API gives no path, FL keeps no file open, and its recent-files list
  (`Settings/Browser/Recent files.scr`, the `MRU` key in `reg.xml`) is written only when FL quits.
- The saved-plugin-state flow for Serum 2, Diva and Sylenth1 presets is untested on macOS (Vital works).
