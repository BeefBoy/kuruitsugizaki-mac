# Listener: an audio model reads every render

## What

Every render is also sent to an audio model on OpenRouter, and `render_report` returns what it says it hears beside
the spectrogram: the sections with timestamps, what repeats and for how long, what changes between repeats, how many
parts play at once, and whether it sounds generic or distinctive. It is on by default. The default listener is
`qwen/qwen3.8-omni-flash`; `google/gemini-4-argon` is the second opinion, asked for by name.

## Why

- The model writing a piece cannot hear. The spectrogram and the report give level, bands, width and key; they do not
  say whether the music changes, whether a part repeats unchanged, or what it sounds like. A listener answers those in
  words, between renders, without the user having to react to each one.
- A listener's answer is a claim, not a measurement. It is read against the score view and the report, never acted on
  alone.

## What is known

- `scripts/listen.py` sends one or more audio files as base64 mp3 (`input_audio`) with a fixed seven-question prompt,
  key `OPENROUTER_API_KEY` from the environment or from the `.env` file `--env` names, and writes each answer to
  `tmp/listen/<stem>/<model>.md` with `results.json` (time, tokens, cost, errors). Its default is the five models
  below. A connection SSL drops is retried twice.
- Measured on two tracks, 62.7 s and 41.1 s, against what each holds:

  | model | what it gets right | what it gets wrong | cost per track |
  |---|---|---|---|
  | `google/gemini-4-argon` | the timeline: tempo or its half, key, loop length, each section change and the end within a second | counts fewer parts than play; once named chords the bass does not show; missed short dropouts and vocal chops | $0.016-0.017 |
  | `qwen/qwen3.8-omni-flash` | tempo (134 exact; 100 for a 199 track), the stops and the changes, vocal chops | the key once; counts 3-5 parts | $0.001 |
  | `xiaomi/mimo-v2.5` | key, the chord progression by name | its clock drifts: a 41 s track reported as 49 s | $0.001 |
  | `xiaomi/mimo-v2.6-pro` | key | length, tempo, an invented stop | $0.002-0.003 |
  | `google/gemini-3.8-flash` | vocal chops | key and tempo on both tracks, a section change missed, parts invented | $0.011-0.014 |

- Every listener undercounts the parts playing at once: 3-6 against about 7. So far "generic" from them has meant
  "loops", and "distinctive" has meant the sound, not the writing.
- Through this OpenRouter account: `meta/muse-spark-open` and `thinkingmachines/inkling` and `inkling-small` are
  refused by its guardrail and provider settings, free models by its training setting; `openai/gpt-audio` and
  `gpt-audio-mini` answer without listening.

## How

1. `listen.py` exposes `listen(audio, models) -> list[dict]` for the server; the command line stays.
2. Config keys: `listeners` (a model id or a list; default `qwen/qwen3.8-omni-flash`; `none` switches it off) and
   `openrouter_env` (the `.env` file holding the key, asked once when neither it nor the environment has one).
3. `render.py`, after the analysis, sends the mp3 it just wrote to each listener and appends the answers to the render
   log; `render_report` returns them between the short report and the spectrogram.
4. COMPOSING §10: read the listener next to the spectrogram, check each of its claims against the score view and the
   report, and act only on what they confirm.

## Open

- Calibration: whether a listener tells the person's tracks from model-written ones, unlabelled. Needs tracks with a
  known author.
- Argon as the default instead of qwen: the more accurate timeline at about 16 times the price.
- Two renders in one request (A/B), for the variants step.
- Whether asking for the parts section by section fixes the undercount.
