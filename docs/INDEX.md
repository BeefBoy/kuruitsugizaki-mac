# kuruitsugizaki

A music MCP for FL Studio: it writes whole projects (`.flp`) and drives a running FL, so a model can make music for
someone. The model cannot hear. A render comes back as numbers and pictures; the person listens, and their ears are
the only verdict.

## Writing a piece

**1. Preference.** Read `compositions/PREFERENCE.md`: what the person likes and rejects, in their words, gathered
from every verdict they have given. If such doc doesn't exist, it was not written yet.

**2. `COMPOSING.md`.** A general method, written before this person said how their music should go: the order of
work, what went wrong in earlier pieces and the rules that came out of it, measured mixing levels and widths, how to
read a render. Where it and their preference disagree, the preference wins.

**3. Their projects.** Open the ones that matter and read them in full (`project_read`): their drum programming,
their lines, how a track is built from start to end. `profile` lists their projects with tempo, key and length, so you
know which to open.

**4. What to make sound with.** Every plugin on the machine (`plugins`, `presets`); an instrument channel from one of
their projects, copied with its sound (`state: {from, channel}`); their sample library (`samples`); FL's factory content when they have none. Effects
are chosen and set for this piece.

**5. `MECHANICS.md`.** How the harness builds a piece: the piece script, positions, units, samples, mixer, effects,
automation, and the write / open / render loop. `../examples/README.md` has one small working document per feature
and every automation scale; `../README.md`, "Project JSON, compact form", has every field.

**6. The work.** A part at a time, the way a producer works by ear: write it, render it, look at what it actually
does, change it, go on. The render is your only ear: where each note really sounds, what is crowded or empty, whether
a section lifts or sits flat, how wide and loud it is. Numbers cannot tell a dull melody or a lifeless drum part from
a good one; say what you could not judge rather than calling it done.

**7. Where it goes.** `compositions/<piece>/<piece>.py` writes `compositions/<piece>/<piece>.json`, built to
`projects/music/<piece>.flp`; both folders are the person's and git ignores them. `compositions/<piece>/<piece>.md`: its first line is the form in one sentence (`COMPOSING.md` §7), then, written
as you go: each part, what it is, where it came from, what else was tried, what a render changed, and what you did
not check; their verdict goes at its end. Scratch goes in `tmp/`.

Content of compositions/ is not for your read unless its yours file created fresh or PREFERENCE.md doc.
The first line of each earlier `compositions/<piece>/<piece>.md`, the form sentence, may be read before choosing a form, and nothing past it.
Forbidden unless told otherwise E:\dev\kuruitsugizaki\examples\seance.md
E:\dev\kuruitsugizaki\examples\seance.py

## Work on the server itself, not on music

`FLP.md` (the format) and `ARCHITECTURE.md` (why it is built this way).
