# Examples

Small documents that each show one part of the compact format, and one full piece that uses all of them. All are written by Claude Opus 5.5 (Anthropic) through kuruitsugizaki; each project's author field says so.

Every sound is FL Studio factory content: Sytrus and 3x Osc presets, FL's own effects, and samples from FL's own packs, referenced as `%FLStudioFactoryData%/Data/Patches/Packs/...`, a path FL resolves on any install. Built and rendered with FL Studio 2025 (25.1.6). An FL edition without Sytrus or one of the effects loads that slot empty or as a demo.

Never meant to be copied for prod, for illustrative purpose only. Write your own stuff.

## Use

Hand any `.json` here to the model and ask it to write and open it (`project_write` with `open: true`), or build them all from a terminal in this folder's parent:

```bash
.venv/Scripts/python examples/build.py
```

That writes `projects/examples/<name>.flp`; open them in FL like any project. `build.py <name>` builds only that one; it exits with 1 when an example fails or the writer warns, so it doubles as a check that the format still works.

## The small ones

| file | shows |
|---|---|
| `01_notes.json` | the smallest project: one instrument, one pattern, one clip; note rows, ticks, an off-grid triplet and a late note |
| `02_instruments.json` | every way to bring in a sound: plugin by name with a preset, plugin by name with a format, the template's FLEX, a sampler, an audio clip with trims; one pattern for several instruments |
| `03_effects.json` | effects by name with presets, an effect copied with its settings from a saved project, faders, the master fader |
| `04_routing.json` | three drum inserts routed to a bus and off the master; a sidechain send at level 0 into a pad's compressor |
| `05_automation_global.json` | FL's global controls: tempo (a ramp and a tape stop), master pitch, and a fade on the master fader |
| `06_automation_mixer.json` | mixer and effect automation: fader, pan, stereo separation, an effect's parameter (an EQ band swept as a filter, a reverb's wet level), a slot's mute switch and mix |
| `07_automation_instrument.json` | instrument automation: a plugin's own knobs (3x Osc's shape, octave and detune, used to build a patch and then play it) and a channel's pitch, volume and pan |

Each file's `about` says what to listen for. The value scales the examples rely on, measured in FL:

| target | scale |
|---|---|
| `{"global": "tempo"}` | (bpm - 60) / 120 |
| `{"global": "main_pitch"}` | 0.5 in tune, +-12 semitones over the knob |
| `{"global": "main_vol"}` | written, but FL 2025 ignores it; use `{"mixer": 0, "param": "vol"}` |
| `{"mixer": t, "param": "vol"}` | 0.8 = 0 dB |
| `{"mixer": t, "param": "pan"}` | 0 left, 0.5 centre, 1 right |
| `{"mixer": t, "param": "sep"}` | 0.5 as is, 1 mono, 0 widest |
| `{"mixer": t, "slot": s, "rec": "0x1f00"}` | the slot's mute switch, 0 or 1 |
| `{"mixer": t, "slot": s, "rec": "0x1f01"}` | the slot's mix, 0 to 1 |
| `{"mixer": t, "slot": s, "param": n}` | the effect's own knob n, 0 to 1 (`docs/FX.md`, `docs/params/`) |
| `{"channel": id, "param": n}` | the plugin's own knob n, 0 to 1 (`docs/params/`) |
| `{"channel": id, "param": "pitch"}` | 0.5 in tune, +-48 semitones over the knob (0.375 is an octave down) |
| `{"channel": id, "param": "vol"}` | 0.78 is FL's default |
| `{"channel": id, "param": "pan"}` | 0 left, 0.5 centre, 1 right |

## The full piece

`seance.py` writes `seance.json`: "Factory Seance", two minutes of glitchy witch house and breakcore at 170 BPM, built from everything above. `seance.md` explains each part and why it is there; `seance.mp3` is its render, `seance.png` the spectrogram and `seance_stereo.png` the stereo image the harness made of it, and `demo.mp4` (with sound), `demo.webp` and `demo.gif` a screen recording of it playing in FL, and `seance_full.mp4` the whole piece with sound over its spectrogram and `seance_strip.mp4` over its waveform (the player at the top of the main README), a playhead moving across each. It shipped exactly as written: the person who asked for it listened, tried a master of their own, and kept this one.
