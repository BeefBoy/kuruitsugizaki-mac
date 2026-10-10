# Traps

Each with its mechanism where one is known. Measured on FL 25.1.6, scripting API 38, Python 3.12.1 inside FL.

## FL's script sandbox and the live link

- FL refuses `socket.socket()`, `os.mkdir`, `open()` for read and write, `os.replace` and `os.remove` from a controller script, all as SystemError "returned NULL without setting an exception". `os.listdir` works. The modules import fine, so an import check proves nothing. Why FL does this is not established.
- `ctypes` does not load at all: FL runs controller scripts in subinterpreters and `_ctypes` refuses them. Any native shim would have to be a multi-phase-init extension that declares subinterpreter support.
- `_winapi.CreateNamedPipe` and `_winapi.CreateFile` look like they work in FL and do not: they return 18446744073709551615, INVALID_HANDLE_VALUE, without raising. Inferred from CPython's `_winapi`: on an audit refusal it returns that value and raises only if the hook set an exception, and FL's hook sets none. A pipe self-test can read True only because `CloseHandle(-1)` closes the current-process pseudo handle and succeeds. Check the returned handle, never the absence of an exception.
- Works in FL: use of an existing handle with `_winapi.PeekNamedPipe`, `ReadFile`, `WriteFile`, `CloseHandle`, plus `os.listdir` and `os.getpid`. The live link rests on that (`ARCHITECTURE.md`). Named `mmap` is refused (SystemError) and `os.open` fails with TypeError.
- FL cannot create `tmp/bridge`; the server creates it.
- A broken pipe (109) or no data (232) in the script means the MCP server went away; the script drops the handle and adopts the next announced one.
- The controller script loads only when its MIDI input port exists, and the port is loopMIDI's. Without loopMIDI running, FL starts fine, the script never loads, nothing adopts the announced handle, and every request times out with no error anywhere: FL up in under 5 s, the server reporting "still starting" for minutes. The server starts loopMIDI before it launches FL.
- The installed controller script holds the bridge folder's path, written in by `fl_install`. After this folder moves, the server announces handles where FL no longer looks and every request times out; FL's script output shows the listdir error. Run `fl_install` again and restart FL. Read from the code, not observed.

## Automation targets and fresh plugins

- `{"global": "main_vol"}` (FL's REC_MainVol, 0x40000000, the id FL's `midi` module gives) is written correctly and does nothing in FL 2025: a clip fading it left the level unchanged in a render and in live playback. The overall level is the master insert's fader, `{"mixer": 0, "param": "vol"}`. `{"global": "main_pitch"}` (REC_MainPitch) works: 0.5 in tune, +-12 semitones.
- Channel pitch automation spans four octaves each way: 0.25 sounded two octaves down, 0.75 two up, on a synth and on a sampler alike.
- A fresh 3x Osc, loaded by name with no preset, is a sine an octave above the written note. Its shape knobs step through sine, triangle, square, saw, rounded saw, noise and custom at round(v x 6).
- A fresh FL Keys loaded by name with no preset rendered silent.
- FL's window title shows the project's title when one is set (`<title> - FL Studio 2025`), the file name otherwise, and only `FL Studio 2025` for an untitled project.
- Note names take sharps and flats on the seven letters; `E#` and `B#` are not accepted, write `F` and `C`.

## Setup: the MIDI port and FL's MIDI setting

- loopMIDI keeps its ports in `HKCU\Software\Tobias Erichsen\loopMIDI\Ports`, one DWORD 1 per port name, and reads them when it starts: a value added there while it is closed is a port the next time it runs.
- FL keeps each MIDI input in `HKCU\Software\Image-Line\FL Studio <nn>\Devices\MIDI input\<port name>` (`<nn>` is 25 for FL Studio 2025), as strings: `Type` -3 and `ScriptFolder` the script's folder name for a scripted controller, `Enabled` 1, `Port` the port number, `IDString` `-`, `ConnectionCounter`. An entry written there for a port FL has never seen loads the script on FL's next start; FL adds the matching `MIDI output` entry itself. FL writes these keys when it closes, so an edit made while it runs is lost.
- winget ids: `TobiasErichsen.loopMIDI`, `astral-sh.uv`, `Gyan.FFmpeg`.

## FL's scripting API

- `plugins.getParamValueString` reads a host cache that refreshes only after the script yields, so a display read in the same tick as its set returns the previous value, which looks plausible. Over the bridge a set and a read belong in different requests, never one `fl_exec`.
- `getParamCount` returns 4240 for a wrapped VST whatever the plugin has: the plugin's block, then empty names up to 4095, then FL's 144 MIDI pseudo-parameters at 4096+. Setting those sends real MIDI, including CC 120, 121, 123. Bound the block by a run of empty names (16 works), not by name matching; 16 of the 144 are not called `MIDI CC`.
- Serum 2 repoints host indices when an oscillator engine changes, and `Bank` (Sylenth1: `Program`) loads a patch when set. Watch sentinel names across a run and skip anything that moves them.
- `setParamValue` not raising is not the value landing; read it back with `getParamValue`.
- FL accepts out-of-range normalised values and reads them back; the plugin clamps what it stores.
- `transport.globalTransport(midi.FPT_Save, 1)` (FPT_Save = 92) saves the open project from a script; `general.getChangedFlag()` goes 1 -> 0 within 0.5 s. A save of an unchanged project is not observable (the flag stays 0). Nothing found exposes the open project's path; `general.getProjectTitle()` is title metadata.
- Setting a plugin's host parameters back does not restore its file state: on Serum 2, 34 state leaves differed afterwards (defaults written explicitly). Same sound, different bytes; an exact restore writes the saved state back.
- Display text goes stale for every parameter changed in the same batch as a mode switch. On Serum 2, parking all 455 mapped parameters at 0.0 left their displays stale for over 3 s, traced to `A Warp Mode` reaching `Off` in that batch. What works: park, then set x+-0.001 and back to x in two later batches before reading.
- `channels.getChannelName(i)` and `channels.channelCount()` count within the channel group selected in the rack; pass `True` (`getChannelName(i, True)`, `channelCount(True)`) for all channels. The local index raises Index out of range on a project whose selected group is smaller than the rack. The same holds for `channels.setTargetFxTrack(i, t)` and `getTargetFxTrack(i)`.
- A mixer insert past `mixer.trackCount()` does not exist, and routing a channel there is silent, not an error: it reads back live as name `""`, volume 0.0. Pick inserts below `trackCount`.
- `mixer.getTrackPeaks` inside one `fl_exec` that sleeps in a loop reads 0.0 throughout: the script holds FL's thread and the meters do not update. Start playback in one call, read peaks in later calls.

## Opening, saving, rendering

- Command-line render (`FL64.exe /R /Ewav,mp3 <file.flp>`) does nothing while FL is already open: the second FL64.exe exits 0, no file is written, and the running FL is left changed. It behaves like opening a file, which hands over to the running instance. A render needs FL closed; `render.py --close` asks it to close and never forces it.
- A command-line render plays what the project was saved to play: song mode the arrangement, pattern mode only the current pattern. Event 9 in the header is the switch (1 song, 0 pattern). The writer saves compact documents in song mode and `render.py` warns on a multi-pattern file saved in pattern mode.
- A render stops at the last note or automation point; an empty last bar is not exported. For a tail, a flat automation clip on any parameter a bar or two past the last pattern.
- Saving the open project with FPT_Save writes it over its own file. When that file was just rewritten on disk (write, then save, then render), the save puts FL's old copy back and the render plays it. `_save_open` in `server.py` snapshots the file first and restores it. FL also marks a reopened project changed while idle, so closing it raises a save dialog; the harness always saves before closing or opening.
- FL refuses to open another project over unsaved changes with a dialog nothing here can answer, and switching song or pattern mode or moving the play position already counts as a change. `project_write` refuses to open in that state and says so.
- FPT_Save on an untitled project opens FL's Save as dialog, and every call after it fails with "Operation unsafe at current time" until someone closes the dialog. A freshly started FL is in exactly that state. `_save_open` skips the save when the project is untitled and unchanged, and refuses with a message when it is untitled and changed. Untitled is read from FL's main window title, `FL Studio 2025` against `<file>.flp - FL Studio 2025`; `ui.getProgTitle()` returns `FL Studio 2025` either way.
- A change made through the scripting API (a channel volume set with `channels.setChannelVolume`) does not raise `general.getChangedFlag()`, so the flag is not evidence that nothing was edited.
- Opening a `.flp` by launching FL64.exe with the path hands it to the running FL, and that second FL64.exe lingers for a while. Anything that looks FL up by process name sees two. The link keeps to the pid it connected to and prefers the oldest.
- FL resaves a project it has open: the file on disk changes after a while even with nobody editing it. Treat a `.flp` FL has had open as FL's copy; rebuild from the piece's JSON to get the written file.
- FL's split render (export with split mixer tracks) writes `<stem>/<stem>_Insert N.wav` per insert plus `<stem>_Master.wav`; a renamed insert is written under its name. An insert whose sounds were moved elsewhere still writes a silent file. Stems are post-insert and pre-master, so master minus the sum of stems is what the master chain did.

## The format and the writer

- An automation clip's range lives in its channel's event `219`: two u32, min and max, in the target's raw units. Tempo clips use 1250..4250; FL stores every other clip, faders and effect knobs included, at 0..12800, where the clip value is the fader or knob value (0.80 = 0 dB on a fader). The writer writes those ranges on every new clip. A clip carrying the tempo range on a fader sits 13-30 dB low.
- FL expects a pattern's notes in event 224 sorted by position. A note stored after a later one is a ghost: drawn, never played; clicking it in the piano roll makes FL re-insert it in order. The writer sorts notes (a stable sort, so FL-saved files still round-trip).
- A compact document's clip `src` of `s<N>` or `a<N>` is read as a sample or automation pointer, so an instrument or pattern called `s1` breaks `from_compact` with IndexError. Name them otherwise.
- `view.read(..., 'compact')` drops a pattern clip's start offset inside the pattern. A clip that starts playing a pattern from its middle is read as starting from the pattern's tick 0, so building it back plays the wrong notes there. Use `view="full"` for such projects.
- With the shipped template as base, insert 17 takes no fader: `writer.build` warns "mixer track 17: the base mixer has no volume record for it", and a volume automation clip aimed at it did nothing either; an audio clip there played at full level under a clip held at 0. Why the clip does not reach the fader was not looked into. Usable inserts are 1-16.
- `project_read` and `project_write` reload only `flp`, `automation`, `levels`, `sylenth1`, `serum2`, `presets`, `mixerfx`, `project`, `writer`, `view`. `importlib.reload` re-runs a module but leaves the modules it imports as cached, so an edit to `flex.py`, `diva.py` or `config.py` stays invisible to the running server until an MCP restart. Read from the code, not observed failing.
- `uv add` fails while the MCP server runs: it reinstalls the project and `.venv\Scripts\kuruitsugizaki.exe` is locked (os error 32). `uv add --no-sync` then `uv pip install` works.
- A FLEX instance crashes FL on load when its state is written wrong: zero-filling the preset-name field past byte 2064 wiped the structure after it (`FLP.md`, FLEX state).
- Unverified, from the FL manual: a sampler channel with its Volume envelope on makes note length count, and Cut / Cut by groups let one channel silence another; a channel copied whole with `state: {from}` would carry both. Also unverified: the writer writes a per-note `pan` field. Both worth one test before relying on grain lengths for stutters.

## Plugins and presets

- Event 212 of a channel or effect block is the slot record (on an effect: insert and slot, then window geometry and flags). Every `.fst` carries its own, some with uninitialised bytes in it; a preset takes the state, 213, only.
- `.fst` files saved by older FL versions store the plugin name (201) as single-byte text, newer ones as UTF-16; read it as UTF-16 only when the length is even and it ends in a double null.
- A command-line render of a project holding many VSTs can write its wav and mp3 and then leave FL running, responding and busy, ignoring a normal close; a forced kill ends it and the render script then finishes.
- Some plugins never refresh their display strings over the API (iZotope Ozone 12 returns its saved display whatever the value), some expose generic slots that display their own index (Omnisphere's `Param N`), and module-based ones display nothing for an empty module (Distructor). A value set through the API still lands; only the display misleads.
- A state event (213) written before its block's slot record (212) is applied to the previous plugin, which can then fail to load. A preset's state goes where the template block has it.
- `project_write(open=True)` to the path FL already has open does not reload it; write to a new path.
- "Vital" and "Serum 2" mean the template channels unless `format` is given.
- A new tool or argument in `server.py` reaches a client only in a session started after the server restarts. `fl_exec`'s in-band `{'__out__': path, 'data': value}` works through an old schema.

## Sound and measurement

- FL's sampler plays a sample to its end whatever the note length (default settings): 24 hits of a 2.2 s vowel at 32nds became one long cloud. For a stutter, cut a short grain.
- Chroma below C2 is not trustworthy at N_FFT 16384 / 44.1 kHz: bins are 2.7 Hz apart and C1-C#1 is 1.9 Hz, so a 32.7 Hz 808 (C1 within 8 cents) once read as C#. Chroma starts at C2 and bins split linearly between neighbouring semitones.
- Python's `wave` rejects 32-bit float WAV (format 3, common for tuned 808s) and FL's compressed pack WAVs (format 26447) with "unknown format". `onsets.py` reads PCM and float from the RIFF chunks itself; ffprobe reads anything.
- A mixer `sep` clip at 1.0 merges to mono (side/mid -120 dB, correlation +1.00) and at 0.0 widens; level and pitch unchanged.
- Peak, unweighted RMS and LUFS do not rank masters the way the ear does when the low end differs. Two masters measured within 0.6 dB on all three were heard as clearly different in loudness; Zwicker (ISO 532-1 time-varying, mosqito) gave 43.9 against 53.7 sone. Mechanism: K-weighting's high-pass sits at 38 Hz and barely discounts a 46 Hz sub, while the ear's sensitivity there is far lower; energy moved from the sub to 1-3 kHz leaves LUFS flat and raises heard loudness. `loudness.py --zwicker` takes about a minute per 25 s file.
- An effect parameter's normalised value and its unit are not linear and differ per plugin: Parametric EQ 2 freq is 20 Hz x 1000^v, its level 36 x (v - 0.5) dB, Gross Beat's slots round(v x 35). Read the display string (`getParamValueString`) for the unit; the mappings found so far are in `FX.md`. Soundgoodizer reports 0 parameters.
- A copied Parametric EQ 2 band is not transparent at its extreme setting: a high shelf at -18 dB with its corner at 20 kHz (value 1.0) still took 4.3 dB off 16-20 kHz and 0.7 dB off 12-16 kHz of a whole mix. Automate the band's level back to 0 dB (value 0.5) outside the move; with that, the render matched the version without the EQ to 0.0 dB in every band.
- A copied effect starts from its saved state: the EQ in `projects/init/fx.flp` sits at a high shelf of -18 dB. What a parameter does before its first automation clip and after its last is not measured; one clip per parameter spanning the whole song, neutral except at the moves, avoids the question.
- Resample and stretch are different effects. Resample (speed and pitch together, `scipy.signal.resample_poly` by an integer ratio) suits drums brought to a piece's tempo; stretch (pitch without tempo, offline `librosa.effects.pitch_shift` with soxr_hq) suits a vocal moved to a key, and a stretch of 2 semitones kept a 6.4 s vocal's length exactly and landed within 4 cents in the render. Resampling a vocal moves it down or up with its speed, which is rarely what is wanted. The writer cannot set FL's per-clip stretch mode, so both are done offline into new WAVs.
