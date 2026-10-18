# Architecture: what was decided and why

## Scope

- **A standalone MCP server.** It needs nothing but FL, loopMIDI and its own folder.
- **The model does not listen, it measures.** Renders come back as numbers and images: `render.py` exports wav and mp3 through FL's command line and runs the analysis on them; `spectro.py`, `loudness.py`, `scope.py`, `waveshape.py` read them. The person listens and decides.
- **Measurement describes, it does not judge.** A quarter tone of detune or a 7-beat cycle over 4/4 is reported as what is there, never as an error to correct.
- **Music first, synth parameters later.** The Serum 2 host-parameter mapping (`serum2.py`, `nudgemap.py`, `profiles/serum2/`) works and is parked; presets are how sounds are chosen.
- **A piece is a whole piece**: one to two minutes with a form, not an 8-bar loop.

## The .flp format is reverse-engineered here

No third-party parser. Every mapping in `FLP.md` carries the measurement it rests on.

**Test: byte-identical round trip.** `.flp -> JSON -> .flp` must reproduce the original bytes. It is the only check that proves nothing unmapped is being reset; it caught a note-order change, dropped clip bytes, a flag rule and a pattern with an extra event, each of which would otherwise have altered a user's project silently.

## Writing: templates, not synthesis

A written project takes its globals, the unmapped section before the channels, arrangement track blocks and mixer from a **base** file FL wrote, and copies each channel block from a file FL wrote (a project of the user's, or the template). Only mapped fields are generated. Every byte whose meaning is not known comes from something FL produced, so FL loads it; the risk is confined to fields that have been measured.

Unmapped bytes are carried, not reset: per-pattern extra events, playlist item bytes that differ from the template, the item flag.

The shipped template and effect library were themselves written this way and then opened and saved by FL, so every byte in them is FL's.

## Two routes into FL

- **File route** for anything structural: notes, channels, plugins, patterns, playlist, automation. FL's MIDI scripting API (version 38 in FL 25.1.6) has no call to add a channel, load a plugin, write notes into a pattern or load a preset.
- **Live route** for what the API does have: transport, parameter reads and writes, mixer queries, saving. Used for measuring (routing, automation targets, value scales) and for play and stop.

## Live link: handle injection

Forced by FL. FL's script sandbox refuses to create sockets, files, directories, named pipes and shared memory, and `_winapi` hides some of those refusals by returning an invalid handle instead of raising. Using a handle is not refused. So the MCP server creates a named pipe, copies one end into FL's process with `DuplicateHandle`, and names the handle in a file under `tmp/bridge/` that FL finds with `os.listdir`, the one filesystem call it allows. FL then only peeks, reads and writes. The FL pid is in the file name so a stale file cannot be adopted.

Which FL the server works with is a rule, not a pick by process id: a pid named in `KURUITSUGIZAKI_FL_PID`, else an FL the harness started (each is recorded with its creation time in `tmp/bridge/owned.json`), else the only FL running even when the user started it; with several FLs and none the harness's, nothing is picked. Every live result names the FL and who started it, and the harness closes only FLs it started. Before acting on an FL the user started, the server copies the project it has open to `tmp/backups/`, found by the name in FL's window title since FL's API gives no path. His words: "we dont want to mess with fl opened by user randomly, its fine anyway, just needs to be as decision, not a random pick based on ids."

The controller script cannot read a config file, so `fl_install` writes the bridge folder's path into the installed copy.

FL loads a controller script only on a MIDI input that has it as controller type, and its scripting API cannot set that. Both halves are registry values, so `fl_install` writes them (`scripts/midisetup.py`): loopMIDI's port list, and FL's entry for that input. It uses a port of its own, named `kuruitsugizaki`, so no port the user already has is touched, and it does nothing when an input already has the script. FL writes its device settings back when it closes, so this is done with FL closed.

The server remembers the FL process it connected to, and prefers the oldest FL64.exe when there are several, because opening a project launches a second FL64.exe that hands the file over and lingers.

## Paths belong to the user's machine

No path is in the code. FL, loopMIDI, FL's Hardware folder, the template and the preset libraries are keys in `kuruitsugizaki.json`, which git ignores. A key is needed only when a tool uses it, and a tool that finds it unset says which key and what it is, so the model asks the user rather than guessing.

## Timing: exact ticks

Notes are `[bar, beat, tick]` plus a length in ticks at 96 PPQ. No per-pattern grid: played parts sit off even a 1/64 grid by single ticks, and a grid would snap exactly the offsets that carry the feel.

## Patterns hold several instruments

A note names its instrument and a pattern is not tied to one, because a pattern that layers two sounds is common in real projects.

## Tool shape

- One call writes a whole project, and reading and writing share one shape, so a read project can be edited and written back.
- The compact form: rows under a column header, instruments and sources by pointer. Two full arrangements measured read at 13 KB and 47 KB.

## Plugins by name

- The source is FL's own plugin database: one entry per installed plugin (a native one its name, a wrapped one its path and id). Put into a template block it makes FL create the plugin fresh, as dragging it in from the browser does; the block is FL's, only the name and identity are swapped in. Nothing has to be prepared.
- An optional library project holds tuned instances, reused as saved and preferred over a fresh one of the same name.
- A plugin installed in several formats is one name: library first, then native, vst3, clap, vst; `format` picks one.
- Paths are looked for at their standard places first and asked only when not found.
- A preset is one event: the plugin state, 213, swapped into the copied block. The slot record, 212, stays the library's.
- Presets come from `.fst` files FL saved, for any plugin, and from vendor preset files where the plugin's state family has a converter (JUCE XML, Cableguys `#zip#`), named per plugin in `vst_presets`; a JUCE plugin needs no saved instance for that.
- A preset that needs a saved instance of its plugin loads into one FL saved: the first time, `project_write` opens the plugin by name in FL, saves, and keeps the state in `tmp/states/`. Nothing about the user's own projects is required. His words: "we should be agnostic". NKS files carry the plugin's state whole and need none.
- Parameter maps are generated files under `docs/params/`, read live and swept on a copy of the library, so a model can address any knob by index without reading the plugin.

## Deciding, not scripting

The harness is for the model deciding where each note goes. Generator scripts are allowed as a tool; writing the compact JSON note by note and calling `project_write` is the other mode, and both stay.

## Audio trim is optional

An untrimmed audio clip plays its whole sample; no warning is raised for it.
