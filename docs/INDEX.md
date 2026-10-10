# kuruitsugizaki: index

An MCP server that reads and writes FL Studio `.flp` and drives a running FL, so a model can write music. The `.flp` format is reverse-engineered here and checked by a byte-identical round trip; projects are written from templates FL saved; the live link is a named pipe into FL's controller script. Renders come back as numbers and images, not sound. FL Studio is the first integration; the harness is meant to reach more software later.

This file points; it does not restate. Nothing behind a pointer is in context until that file is opened.

## First run

Paths on the user's machine (FL, loopMIDI, FL's Hardware folder, preset libraries) are not known in advance. Call `config` first. For every key a task needs that is not set, ask the user where that thing is on their machine and set it with `config`; never guess a path, and never search their disk for it without asking. A tool that hits an unset key answers with the key and what it is: ask, set, call again. Then `fl_install`, and the FL-side steps in `../README.md`, Setup.

## Docs

| file | charter |
|---|---|
| `../INSTALL.md` | what the user does by hand to install it, and what to check when the live link fails |
| `../README.md` | the deliverable: setup, tools, the template, the effect library, the compact JSON format, what is not written yet |
| `../examples/README.md` | a working document for each part of the format, every automation target's value scale, and a full piece written as a script; read before writing a first piece |
| `MECHANICS.md` | how a piece is built through the tools: the piece script, positions, units, samples, mixer, sounds, effects, the write / open / save / render loop. Read before writing a piece |
| `COMPOSING.md` | how to write a piece: a method, stage by stage |
| `DRUMS.md` | drum-writing research from outside sources, measured vs opinion tagged |
| `FX.md` | effects' automatable parameters as FL exposes them, with the measured value-to-unit mappings |
| `FLP.md` | the `.flp` format as decoded, each fact with the evidence it rests on |
| `NOTES.md` | traps, each with its mechanism |
| `ARCHITECTURE.md` | decisions and their reasons |

## Where work goes

- A piece: `compositions/<piece>.py` writes `compositions/<piece>.json`, built to `projects/music/<piece>.flp`; why each part is where it is goes in `compositions/<piece>.md`. Both folders are the user's and git ignores them.
- Scratch: `tmp/`, ignored.
