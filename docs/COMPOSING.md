# Composing: how to write a piece for someone

A process, not a style. What the music should be comes from the person: their projects (through `profile`), the tracks they name, and their verdict on what you render. Nothing here says what good music is. Mechanics (the piece script, positions, units, effects, render) are in `MECHANICS.md`.

## 1. Whose piece

- **They have projects:** run `profile` on the folder. Read its Read back list to them and let them strike lines; what is left is the brief's floor. Ask them to put two or three favourites in a `favourites/` folder, and anything they dislike in `negative/`, then profile again. Someone who cannot explain music can still point at a file.
- **They have none:** ask for two or three tracks they like and what the piece is for (mood, length, where it will play). Ask; do not fill gaps with your own taste.
- Write what they said, in their words, at the top of `compositions/<piece>.md`.

## 2. Brief

From the profile and their request, before any note:

- tempo, key, length;
- a form sketch: sections with lengths and what changes at each switch (the profile's section lengths, density curve and first full bar are their habits);
- which roles the piece has (the profile's palette lists the roles their projects use).

A departure from their profile is fine when they asked for it or you can say why; write which in the `.md`.

## 3. Sounds

1. **Their own sounds first.** `profile.json` `aggregate.pointers` names a file and channel for each role: `state: {from: file, channel: n}` in `project_write` brings that channel in as they saved it, plugins we cannot decode (Nexus, Omnisphere) included. `pointers['master chain']` is their most common master chain, copyable as it is into `mixer.effects`; any insert chain of theirs copies the same way (`MECHANICS.md`, Effects).
2. **Otherwise plugins they own**, by name with a preset (`plugins`, `presets`).
3. **Know where each sound sounds.** Render one note per sound and read its lowest partial and tuning before writing ranges: presets often transpose by an octave or two (FLEX's Hard 808s / 808 Clean Fuzz sounds two octaves under the written note). Once known, a shift or a detune is a choice.

## 4. Write in stages

Check each stage with a short render before the next, so a wrong sound or groove costs one stage, not the piece:

1. Drums, if their projects have them: start from the profile's grid per role, and their timing: when a large share of their hits sit off the 16th grid, they play parts in; write with offsets like theirs, not on the grid.
2. Bass, then chords (the profile's chords are relative to the key), then the lead.
3. Transitions at the section switches.
4. Effects, risers and one-shots in the gaps, if their projects use them (the palette's `audio:` roles say).

Their nearest project is a fair source of cells: `project_read` it, take a pattern, change it. Say in the `.md` which and what changed. Every part should have a reason you can state; a part nobody can explain is cut.

## 5. Mix

- Every sound on its own insert from the first draft, so each can be processed alone.
- Their master chain and the insert chains their profile shows per role.
- Faders and effects are written into the document; an unmixed piece is not finished.
- Compare loudness with `loudness.py --zwicker`, not by peak, RMS or LUFS: two masters within 0.6 dB on all three were heard clearly apart, and Zwicker put one 22% louder.

## 6. Render and compare

1. Render and run the analysis (`MECHANICS.md`). The render stops at the last note; for a tail, a flat automation clip a bar or two past the end.
2. Compare with their corpus: tempo, length, how full each section is, loudness, the spectrum of their renders where a `.wav` sits beside their projects. Inside their range, or a departure the `.md` names.
3. Listening is theirs. Record their verdict in the `.md`. What they reject belongs in their profile: a struck line, or the file moved to `negative/`.

When a piece gets a mixed verdict two rounds running, ask whether to park it, and carry forward only what they named as good.

## Checklist

- Their Read back list checked with them, or their named tracks written down.
- Tempo, key, form and roles in the `.md`, with any departure from their profile and why.
- Every sound theirs or one they own; each one's sounding octave known.
- Every sound on its own insert; faders and effects written.
- A tail, or a chosen hard cutoff.
- The render compared with their corpus, and their verdict recorded.
