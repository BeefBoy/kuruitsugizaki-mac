# Writing a piece: the mechanics

How a piece is built through the tools. How to write is `COMPOSING.md`, drum craft `DRUMS.md`, the compact JSON fields `../README.md`. Nothing below is taste.

Learn the plumbing here, not from an old composition script: a script carries its piece's musical choices along with its plumbing, and reading it anchors the next piece on the last one.

## Tools

Signatures as `scripts/server.py` defines them:

| tool | does |
|---|---|
| `config(key=None, value=None)` | the machine paths: no arguments lists them with whether each exists; `key` and `value` set one. Ask the user for any unset path a task needs |
| `fl_install()` | writes the controller script into FL's Hardware folder with the bridge path and, with FL closed and unless an input in FL already has the script, makes a loopMIDI port named `kuruitsugizaki` and assigns the script to it in FL's MIDI settings. Read its `midi` entry: when that is not `ok` it says what the user has to do |
| `project_write(doc, path, open=False, play=None)` | compact or full JSON -> `.flp`. Returns `wrote`, `bytes`, **`warnings`**, `channels`, `patterns` (notes per pattern), `clips` (per arrangement). Read `warnings`: a skipped insert or an unmapped field is reported there and nowhere else. `open` saves what FL has open first, then loads the new file, starting loopMIDI and FL if they are closed; it returns `open_error` instead when FL holds unsaved changes it cannot save. `play`: `song` or `pattern` |
| `project_read(path, view="compact", patterns=None, arrangements=None, unused=False)` | `.flp` -> JSON. `compact` is the shape `project_write` takes; `summary` gives per-pattern stats and a per-track timeline; `full` is the exact round-trip form. Unplaced patterns and parked clips are left out unless `unused` |
| `fl_render(path, reopen=True, key=None)` | saves FL's open project (restoring `path` if that save overwrote it), then starts `render.py <path> --close [--reopen] [--key K]` detached and returns at once with the log file, `tmp/render_logs/<stem>-<hhmmss>.log`. The log reports level and width, pitch against `key` (classes sounding per moment, energy outside the scale, where the tonic ranks), bass tuning, band balance, wash stretches (`COMPOSING.md` §9, Wash), and a row per 8 bars at the project's base tempo |
| `fl_exec(code)` | Python inside the running FL; the value assigned to `result` comes back |
| `fl_call(fn, args=None)` | one FL API function, e.g. `fn='plugins.getParamName', args=[0, 5, -1]`; returns `{ok, value}` or `{ok: false, error}` |
| `fl_transport(action, mode=None, pattern=None)` | `play` / `stop`; `song` / `pattern`; a pattern number in pattern mode |
| `fl_probe()` | FL's API version, its Python, its pid and the pipe handle it holds |

**What reloads without a restart:** `project_read` and `project_write` re-import `flp`, `automation`, `levels`, `sylenth1`, `serum2`, `presets`, `mixerfx`, `project`, `writer`, `view` on every call. Anything else needs an MCP restart: `server.py`, `config.py`, `flex.py`, `diva.py`. A tool added in `server.py` may not appear until a new session, because a client keeps the tool list it started with.

Killing the MCP server's process tree also kills FL and loopMIDI when it launched them. The next live call starts both again.

## The piece script

One file per piece, `compositions/<piece>.py`, writes `compositions/<piece>.json`, which becomes `projects/music/<piece>.flp`. The script and its JSON are the record; FL may resave the `.flp`. Why each part is where it is goes in `compositions/<piece>.md`.

Skeleton (plumbing only; every list in it is per piece):

```python
import json, re, subprocess
from pathlib import Path

PPQ, BPM = 96, 174
BAR = 4 * PPQ
EIGHTH, SIXT = PPQ // 2, PPQ // 4
MS_TICK = 60000 / BPM / PPQ
FX = str(Path("projects/init/fx.flp").resolve()).replace("\\", "/")

SAMPLERS = [("K", "<path to a kick>.wav", 1)]
SYNTHS = [("bass", "serum2", "<path to a .SerumPreset>", 4)]
AUDIO = []
INST = [k for k, *_ in SAMPLERS] + [k for k, *_ in SYNTHS]
IDX = {k: i for i, k in enumerate(INST)}
SID = {k: i for i, (k, *_) in enumerate(AUDIO)}
PATS = {"drums": [], "bass": []}
clips = []

PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6,
      "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

def midi(n):
    if isinstance(n, int):
        return n
    m = re.fullmatch(r"([A-G][#b]?)(-?\d)", n)
    return PC[m.group(1)] + 12 * (int(m.group(2)) + 1)

def P(beat, n=0, d=1):
    return (beat - 1) * PPQ + n * PPQ // d

def pos(token):
    return P(int(token[0])) + {"": 0, "e": SIXT, "&": EIGHTH, "a": 3 * SIXT}[token[1:]]

def at(bar, p=0):
    return (bar - 1) * BAR + int(p)

def note(pat, inst, bar, p, ln, key, vel):
    t, k = at(bar, p), midi(key)
    PATS[pat].append([t // BAR + 1, (t % BAR) // PPQ + 1, t % PPQ, max(6, int(ln)),
                      f"{NAMES[k % 12]}{k // 12 - 1}", int(vel), IDX[inst]])

def clip(track, bar, p, ln, sid, src_ms):
    t = at(bar, p)
    clips.append([track, t // BAR + 1, (t % BAR) // PPQ + 1, t % PPQ, int(ln), f"s{sid}",
                  [int(round(src_ms)), int(round(src_ms + ln * MS_TICK))]])

def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout)
```

Drums and bass are written out row by row. A helper such as `note()` writes the row it is given; it never decides where a row goes (COMPOSING §0).

The document at the end:

```python
doc = {
    "format": "compact",
    "project": {"bpm": BPM, "ppq": PPQ},
    "note_cols": ["bar", "beat", "tick", "len", "key", "vel", "inst"],
    "clip_cols": ["track", "bar", "beat", "tick", "len", "src", "trim?"],
    "instruments": [{"id": k, "name": k, "kind": "sampler", "path": p, "mixer": mx} for k, p, mx in SAMPLERS]
                   + [{"id": k, "name": k, "kind": "plugin", "plugin": plug, "preset": p, "mixer": mx} for k, plug, p, mx in SYNTHS],
    "samples": [{"id": k, "name": k, "kind": "audio", "path": p, "mixer": mx} for k, p, mx in AUDIO],
    "automation": [],
    "mixer": {"volume": {}, "main_volume": 0.8, "routes": [], "effects": []},
    "patterns": [{"id": k, "notes": v} for k, v in PATS.items() if v],
    "arrangements": [{"name": "<piece>", "clips": clips}],
}
Path("compositions/<piece>.json").write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
```

Run it from the repo root with the repo's environment: `.venv/Scripts/python compositions/<piece>.py`.

**Notes always go through a pattern; patterns go on the playlist as clips.** A pattern can hold any number of instruments. Placing a whole-song pattern once at bar 1 (`[track, 1, 1, 0, length, pattern_id]`) and writing notes at their bars is the simplest arrangement; separate patterns placed several times is the other. `base` left out means the `template` key. Instrument and pattern ids must not look like `s<N>` or `a<N>`: a clip `src` of that shape is read as a sample or automation pointer.

### Positions: beat plus subdivision

A position is the beat it belongs to plus a fraction of a beat, never a tick counted from the bar start; reasoning from absolute ticks is where positions get typed wrong.

| written | is |
|---|---|
| `P(3)` | beat 3 |
| `P(3, 1, 2)`, `pos("3&")` | the "and" of 3 |
| `P(2, 1, 4)`, `pos("2e")` / `P(2, 3, 4)`, `pos("2a")` | the second and fourth 16th of beat 2 |
| `P(1, 1, 3)`, `P(1, 2, 3)` | 8th-triplet positions inside beat 1 |
| `P(4, 1, 6)` | the first 16th-triplet step after beat 4 |
| `P(2, 1, 8)` | a 32nd after beat 2 |

Written so, the denominator names the tier a hit sits on (`COMPOSING.md` §2): 1 the beat, 2 the "and", 4 the 16ths, anything finer the off-beat tiers. `at(bar, p)` turns bar plus position into absolute ticks for the helpers; nothing is typed in absolute ticks by hand.

## Units

- 96 ticks per beat, 4/4, `BAR` = 384. Bars and beats 1-based, ticks 0-based.
- 8th 48, 16th 24, 8th triplet 32, 16th triplet 16, 32nd 12.
- ms per tick = `60000 / BPM / 96`. A sample of `s` seconds spans `s * BPM / 60 * 96` ticks.
- Keys: MIDI 60 = C4. FL's own UI calls it C5.
- Mixer fader: stored scale, 0.8 = 0 dB. Not dB. FL's fader curve is not derived here; read dB live with `mixer.getTrackVolume(t, 1)`.
- Automation values: tempo = (bpm - 60) / 120; mixer volume 0.8 = 0 dB. Points are `[beat, value, tension?]` in beats from the clip start.

## Samples

The user's sample folders are theirs to name; ask where they are. Large libraries hold thousands of files per folder: list one folder level at a time, never recursively. `samples.py <folder>` (one folder, not recursive) writes `tmp/samples/<folder>.tsv`: duration, channels, BPM and key from the name, peak, RMS, side/mid, onsets per second, spectral centroid. FL's own drums are under FL's install folder, `Data\Patches\Packs\Drums\`.

**Formats:** Python's `wave` reads PCM only. Tuned 808s are often 32-bit float (format tag 3); FL's pack WAVs are compressed (tag 26447). `dur()` (ffprobe) reads anything; `onsets.py` reads PCM 16/24 and float from the RIFF chunks itself.

**Two ways to use a sample, both by `path`:**

- `kind: sampler` (an instrument): notes trigger it, C4 = original pitch, re-pitching moves speed and formant together. It plays to the sample's end whatever the note length (default settings). One-shots and chops; cut a source into short WAVs first with `chop.py` (fades at both ends, optionally reversed).
- `kind: audio` (in `samples`): playlist clips `[track, bar, beat, tick, len, "s<N>", [start_ms, end_ms]]`. Risers, long FX, loops. **Segment chops need no files:** the same sample placed many times, each clip with its own `trim`, is a slice. An untrimmed clip plays its whole sample whatever its `len` says. Two clips overlapping on one playlist track crossfade, so spread overlapping slices over several tracks, or trim each to the gap before the next hit.

## Mixer layout

- The template has master + inserts 1-17, no effects, no names, all at 0.8. Insert 17 takes no fader there: a volume clip aimed at it does nothing and an audio clip on it plays at full level; use 1-16. An instrument routed past `mixer.trackCount()` is silent with no error; check after opening with `channels.getTargetFxTrack(i, True)`.
- Every sound on its own insert. Grouping by role leaves nothing processable alone.
- Inserts at 0 dB are left out of `mixer.volume` on read.

## Sounds that load

`plugin` takes a plugin the template holds: `serum2` and `flex` in the shipped one; `vital`, `sylenth1` and `diva` with a template of the user's that holds them (`../README.md`, The template). `preset` is a file path, except for FLEX, which takes `"<pack>/<preset>"`, e.g. `"Hard 808s/808 Clean Fuzz"`. A plugin with no `preset` loads its init state. Serum 1 `.fxp` do not load.

Catalogs, one row per preset, built into `tmp/` from the library folders in `config`:

| built by | default output | selector column |
|---|---|---|
| `serum2.py catalog [folder] [out.tsv]` | `tmp/serum2.tsv` | `path` |
| `flex.py catalog [out.tsv]` | `tmp/flex.tsv` | `preset` (the full `<pack>/<preset>`) |
| `diva.py catalog [out.tsv]` | `tmp/diva.tsv` | `path` |
| `sylenth1.py catalog [out.tsv]` | `tmp/sylenth1.tsv` | `path` |
| `catalog.py <Vital preset folder> <out.tsv>` | | `path` |

Run them from the repo root with `.venv/Scripts/python scripts/<script>`. Choose from these, not from an old script.

**Before writing a range, know the preset's transpose and tuning** (`COMPOSING.md` §8): several presets sound one or two octaves below the written note, and Sytrus `Bass/Sub bass` three (written D#4 sounds D#1). Check the lowest partial in a one-note render. The render log says how much of the energy sits below 20 Hz and warns over 5%: that is a sound written octaves too low (one piece carried 16-18% in its drops; finished mixes of a user's ran 0-2.6%).

**A channel copied with `state: {from, channel}` arrives switched on**, even when it was muted in its source project; many saved projects have muted channels. `muted: true` on the instrument keeps it off.

## Effects, sidechain, levels

Effects are copied with their settings from a project FL saved: `mixer.effects: [{"track": t, "slot": s, "from": {"file": FX, "track": ft, "slot": fs}}]`. The shipped library is `projects/init/fx.flp`; placement there means nothing:

| from track/slot | effect |
|---|---|
| 1/0 | Fruity Parametric EQ 2 (saved with a high shelf at -18 dB) |
| 2/0 | Fruity Limiter |
| 3/0 | Fruity Limiter in compressor mode, set for sidechain ducking |
| 4/0 | Fruity Reeverb 2 |
| 5/0 | Fruity Multiband Compressor |
| 6/0 | Soundgoodizer |
| 7/0 | Gross Beat (its pattern state is not mapped; `FLP.md`, Gross Beat state) |

Any project the user saved in FL is a library too: `project_read` with `view="summary"` lists its effects per insert.

**Sidechain:** route the trigger insert to the ducked one at level 0, `mixer.routes: [{"from": 1, "to": 4, "level": 0.0}]`, and copy the 3/0 limiter into the ducked insert's first slot. `"on": false` removes a route.

**Master limiter:** the 2/0 limiter into master slot 9. Past 0 dBFS is allowed as a sound (`COMPOSING.md` §9).

**Faders:** `mixer.volume: {insert: value}`; `main_volume` 0.8 is the template's.

**Not writable yet:** static pan and sends, pattern names, time signature, an effect FL never saved anywhere.

## Write, open, save, render

1. Run the script; it writes the JSON.
2. Build the `.flp`, one of two ways:
   - `project_write(doc=<the JSON>, path="projects/music/<piece>.flp", open=True)`. Read `warnings`. It returns `open_error` when FL holds unsaved changes.
   - For a large document, build locally so the JSON never passes through a tool call, from the repo root:
     ```python
     import json, sys
     from pathlib import Path
     sys.path.insert(0, "scripts")
     import writer
     raw, warnings = writer.build(json.loads(Path("compositions/<piece>.json").read_text(encoding="utf-8")))
     Path("projects/music/<piece>.flp").write_bytes(raw)
     print(warnings)
     ```
     No tool opens an existing `.flp` without writing it. Render it straight away (`fl_render` reopens it in FL afterwards).
3. If anything sounds missing, check routing live: `fl_exec` with `channels.getTargetFxTrack(i, True)` per channel.
4. Render with `fl_render(path="projects/music/<piece>.flp")`. It saves FL's open project first, so closing FL never stops at a dialog, then runs `render.py <flp> --close --reopen` detached and returns the log path under `tmp/render_logs/`. Read that log for the result. Until the log shows the render finished, make no live call: a live call finds FL closed and says so. `render.py` also takes `--formats` (default `wav,mp3`) and `--bpm` (bar lines in the spectrogram). FL's split-mixer-tracks export must be off.
5. The render writes `.wav` and `.mp3` beside the project and prints spectro and stereo stats. Look at `tmp/spectro/*.png`, whose bottom strip is ghost % over time (wash, `COMPOSING.md` §9); `waveshape.py` to compare renders when texture is the question; `scope.py <wav>... [--at s] [--lo Hz --hi Hz] [--timeline]` for width per moment and per band; `loudness.py <wav>... --zwicker` for loudness as heard.

The render is numbers and pictures, not sound. The user listens; their verdict decides what changes.

## Traps

- **An empty last bar is not exported.** FL's render stops at the last note. For a tail: an automation clip on any parameter, left flat, extended a bar or two past the last pattern; it changes nothing and the render runs to its end. A note held into the bar works too. A hard cutoff is sometimes the design. Cap long audio clips at the intended end either way.
- **A sampler plays its whole sample through any stop:** a two-bar loop on a sampler cannot be cut by a stop in its second bar. Place such notes clear of stops, or use an audio clip, which can be trimmed.
- **Save before opening another project.** `project_write(open=True)` and `fl_render` do it; anything else that closes FL or opens a file should save through the bridge first.
- **FL resaves a project it has open.** Treat anything in `projects/music/` as FL's copy; rebuild from `compositions/` to get the written file.
- **Don't name an instrument or pattern `s1`, `a2` and the like.** In a compact document a clip `src` of `s<N>` or `a<N>` is read as a sample or automation pointer.
- **The compact view drops a clip's start offset inside its pattern.** A clip that starts playing a pattern from its middle reads back as starting from the pattern's start; use `view="full"` for such projects.
- **A copied Parametric EQ 2 is not neutral.** The one in `projects/init/fx.flp` is a high shelf at -18 dB and still took 4.3 dB off 16-20 kHz at its extreme setting; automate the band's level to 0.5 (0 dB) outside the move.
- **A vocal to a key: stretch, not resample.** The writer cannot set FL's per-clip stretch mode, so shift it offline (`librosa.effects.pitch_shift`) into a new WAV; resampling changes its speed too.
- **FLEX arrives with its own delay and reverb on.** Loaded by preset name, every FLEX channel came up with Delay on (ping pong, mix 50%, feedback 63%) and Reverb on (mix 50%): a ~10 s tail on every note, only 8-12 dB down 2 s after note-off. Switch them off per channel with flat automation clips, `{"channel": id, "param": n}`: 37 Delay switch, 38 Reverb switch, 25 Delay mix, 30 Reverb mix (all 0). Dry, the Essential Strings, Winds and Pianos fall silent within 0.5 s of note-off.
- **Scratch goes in the repo's `tmp/`.**
