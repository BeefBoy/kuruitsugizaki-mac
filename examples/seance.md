# Factory Seance

A two-minute piece written by Claude Opus 5.5 (Anthropic) through kuruitsugizaki, as the full example: glitchy witch house that breaks into breakcore and back. 170 BPM, D# minor with E, the flat second, as its colour. 84 bars, 2:01. The project's title and author fields carry the same.

Every sound is FL Studio factory content, so it builds on any FL install: Sytrus and 3x Osc for synths, FL's own drum, vocal and effect packs for samples, FL's own effects. `seance.py` is the source; `seance.json` is what it writes, the document `project_write` takes; `seance.mp3` and `seance.png` are its render and spectrogram.

Nobody listened while it was written. Choices were made from the method in `docs/COMPOSING.md` and checked against measurements of renders, listed at the end. It took about 35 minutes of wall clock from the request to the last render and these notes, the seven small examples included. Afterwards the person who asked for it listened, tried a master of their own, and kept this one: it ships exactly as written, with no human edit. `demo.mp4` (with sound), `demo.webp` and `demo.gif` (silent, for pages that take only one or the other) are a screen recording of it playing in FL; `seance_stereo.png` is its stereo image (`scripts/scope.py --timeline`).

## Why D# minor

The material chose it. FL's `Holo Drone` sits on D# with its fifth, `Choir Swell` is a D#m7 chord, and the vocal one-shots land on the same notes: `Ahh A` falls F# to E (the minor third to the flat second), `Ooh C` falls F# to D#, `Mmh` rises D# to E. Witch house leans on that half step between D# and E, so the harmony is built around it.

## Form

| bars | section | what changes |
|---|---|---|
| 1-8 | intro | No drums. The drone fades in, the choir swell enters at bar 5, the vocal is played an octave down (dragged, as in chopped-and-screwed), and the bell plays fragments of the motif that comes later. One far clap at bar 7 hints at the half-time backbeat. About 6 dB under the next section. |
| 9-24 | witch house | Half-time: boom on 1, clap on 3, hats rolling into the clap in 16th triplets or into the next bar in 32nds. The 808 plays the roots. The motif enters, the pad holds the chords and ducks on every kick. A short stop every fourth bar, a longer one every eighth; the voice fills the stops. From bar 17 a second, slower line in the same synth sound runs under the motif, and the bell answers the motif's falling lines by rising. |
| 25-28 | glitch bridge | The groove is gone: rim and ice-crack hits in triplets and a quintuplet, the word "wait" cut finer each bar (8ths, 16ths, then 32nds, where it turns into a pitch), the drum bus bitcrushed and darkening. Bar 28: one long vowel while the tempo falls to half in two beats, a snare ratchet climbing an octave, then beat 4 silent. |
| 29-44 | breakcore | An Amen played from one-shots, a reese bass on a dotted grid, and an organ playing straight 8ths where every move is a leap. The motif returns at bar 37 over it. Phrases of four bars, each ending in a stop or a fill: the voice, a pitched-down kick in the Amen's gap, snare ratchets, a gabber kick roll. |
| 45-52 | breakdown | Drums out. The pad goes from narrow to its widest, the vocal an octave down and falling, the bell with the motif's fragments again, an 808 hit on two of the roots. The riser climbs into bar 53. |
| 53-76 | the last stretch | A different floor for eight bars (two-step kick, 16th hats broken by doubles, a rim cycle of seven 16ths that does not match the bar). At bar 61 the Amen returns under it, the motif moves up an octave, and the slow line comes back. Stops every four bars; bar 68 drops to half tempo for two beats under one vowel; bars 71-76 build with the densest fills. |
| 77-84 | outro | One gabber hit and a crash, then the drone, a descending spin, the vocal, and the motif once more on the bell, ending on E. The tempo runs down to 100, the master pitch sinks a whole tone, and the master fader fades it out. |

## Harmony and lines

- **Roots**: an eight-bar cycle, uneven on purpose: D# for three bars, E for one, B for two, C#, then E, which falls back to D#. COMPOSING suggests uneven chord lengths over a plain four-chord loop.
- **The motif** (`lead_motif`): three notes a dotted quarter apart, A#4 to D#5 to C#5, then A#4 to F#4 to E4, falling onto the flat second. Each time it repeats, one note changes (F#5 instead of C#5 over B; G#4, C#5 and D#5 over C#). It is played 6 ticks late throughout, a steady lateness that reads as feel.
- **Two lines in one sound**: from bar 17 a slow line in the same Sytrus supersaw moves around A#3 in neighbour steps (A#3, G#3, B3, F#3). Where it meets the motif it makes octaves, thirds and sevenths, and the harmony comes from that rather than from a chord under the motif.
- **The organ's fast line** (breakcore sections): straight 8ths, every move a leap between chord and colour tones, transposed with the root. Notes are dropped where the drums stop, so the stops are heard in it too.
- **Bass**: in the witch house section the 808 sample is pitched to the roots (it sounds as G1 at C4, so G#3 plays D#1), with an octave-up pickup every other bar. In the breakcore sections a 3x Osc reese plays three notes per bar, six 16ths apart, ten ticks late so the kick's click is heard first. On the third bar of each cycle it moves up to the flat second instead of the octave.

## Drums

- **Witch house**: in half time the backbeat is the clap on 3. The hats carry the motion and lead into the next accent: a 16th-triplet roll into the clap in one bar, a 32nd roll into the downbeat in the next.
- **Breakcore**: the Amen's kick, snare and ghost-snare positions played on FL's `Jung` kit, with 8ths on the ride. Additions have a reason each: a kick pitched three semitones down fills the Amen's gap at the "and" of 2; 32nd snare ratchets climb a semitone a hit into phrase ends; 16th-triplet hat pairs answer the kick double; a quintuplet of rims marks the end of a phrase once.
- **The second floor** (53-60): two-step kick and snare, a 16th hat stream with doubles a 16th triplet apart, and a rim every seven 16ths, a cycle that does not line up with the bar.
- **Stops**: every phrase ends in a placed silence, filled by the voice, a reverse swell or nothing at all.

## Sounds

| role | sound | why |
|---|---|---|
| motif and slow line | Sytrus `X Olbaid/Lead/Lead Supersaw 1` | a wide detuned saw at its written pitch, 0.23 s attack: soft enough for slow lines |
| pad | Sytrus `Pad/Haunted house` | dark and wide; it sounds an octave under the written notes, so chords are written an octave up |
| organ | Sytrus `Organ/Deep` | instant attack and octaves on both sides of the note: carries fast 8ths |
| bell | Sytrus `Bell/Glass` | a pure tone with a long ring, true pitch |
| reese | 3x Osc, built by automation | three saws, two of them detuned, the detune widening through each drop; also the instrument-knob example |
| 808 | `Drums/Kicks/808 Kick` on a sampler | sounds G1 about 40 cents sharp at C4; a held channel-pitch clip pulls it 30 cents down |
| drums | `Jung` kick, snare, ride; `Industrial Snare 2`; `Pap Clap`; `909 CH 1`; `808 OH`; `707 Rim`; `FPC Ice Crack`; `SFX Hardcore Kick` | short hits, each cut to fit its gap |
| voice | `Laurie Webb Ahh A`, `Ooh C`, `Mmh` on samplers; `Wait` as audio clips | samplers for pitched, dragged vowels; audio clips for stutters, because a sampler always plays to the end of its sample |
| atmosphere | `FX Holo Drone`, `FX Choir Swell`, `Riser Ghost`, `FX Big Reverse`, `SFX Cym Crash`, `SFX Crush Explode`, `SFX Thunder Sheet`, `SFX Electro Shock`, `FX Spin Down` | the drone and the choir set the key; the rest mark section changes |

## Mixer

| insert | what | effects |
|---|---|---|
| 1-8 | kick, gabber kick, snare, ghost snare, clap, hats, open hat and ride, rim and ice | none of their own; all routed to 15 and off the master |
| 9 | 808 | Fruity Fast Dist `warmth`, adding harmonics so the 808 is heard and not only metered |
| 10 | reese | Fruity Blood Overdrive `Drive` |
| 11 | lead | Fruity Reeverb 2 `Large Hall` |
| 12 | pad | Fruity Limiter in compressor mode (copied from `projects/init/fx.flp`), sidechained from the kick; Reeverb 2 `Cathedral` |
| 13 | organ and bell | Fruity Delay 3 `Ping pong`, Reeverb 2 `Large Hall` |
| 14 | voice | Fruity Delay 3 `Tape`, Reeverb 2 `Cathedral` |
| 15 | drum bus | Fruity Parametric EQ 2 (copied from fx.flp: band 7 is a high shelf at -18 dB, used as a filter by moving its corner), Fruity Fast Dist `fuzz`, Fruity Squeeze `Grit` |
| 16 | atmosphere | Reeverb 2 `Large Hall` |
| master | | Fruity Limiter (copied from fx.flp) |

The template has 17 inserts, so some sounds share one: the ride with the open hat, the rim with the ice crack, the organ with the bell. In a larger template each would get its own insert.

## Automation, one of each kind

| clip | target | what it does |
|---|---|---|
| tempo | `{"global": "tempo"}` | tape stop into the first drop, a two-beat half-time snap in bar 68, the outro slowing to 100 |
| master pitch | `{"global": "main_pitch"}` | the whole mix sinks a whole tone through the outro |
| master fade | `{"mixer": 0, "param": "vol"}` | the ending |
| atmos fader | `{"mixer": 16, "param": "vol"}` | the drone fades in, then the level is set per section |
| ticks pan | `{"mixer": 8, "param": "pan"}` | rim and ice sweep across in the bridge and the two-step section |
| pad width | `{"mixer": 12, "param": "sep"}` | normal, narrower in the drops, widest in the breakdown, wide again for the outro |
| drum bus filter | `{"mixer": 15, "slot": 0, "param": 13}` | EQ band 7's corner moves down to darken the drums into the bridge, the breakdown and the last bar |
| vocal reverb wet | `{"mixer": 14, "slot": 1, "param": 12}` | the voice dry in the drops, washed in the intro, bridge, breakdown and outro |
| drum bus dist mix | `{"mixer": 15, "slot": 1, "rec": "0x1f01"}` | the distortion grows through each breakcore section |
| drum bus crush on | `{"mixer": 15, "slot": 2, "rec": "0x1f00"}` | the bitcrusher switched in for the bridge and three fills |
| reese osc ... | `{"channel": "reese", "param": n}` | held clips build the patch from a fresh 3x Osc (three saws, levels, octave); two moving clips widen the detune through each drop |
| ahh pitch | `{"channel": "ahh", "param": "pitch"}` | the vowel dragged down an octave into the first drop, a fifth into the last stretch, a fourth in bar 68, an octave at the end |
| sub808 tuning | `{"channel": "sub808", "param": "pitch"}` | held at -30 cents: a clip used as a tuning knob |
| lead volume | `{"channel": "lead", "param": "vol"}` | the motif sits back when it first returns over the Amen |
| bell pan | `{"channel": "bell", "param": "pan"}` | the bell drifts from side to side across sections |

## Measured

From the render (`scripts/render.py`, then `loudness.py`): 121.1 s, integrated -10.4 LUFS, LRA 7.4 LU, true peak +0.2 dBTP, L/R correlation +0.46 on average. RMS by section: intro -21.1 dBFS, witch house -15.6 and -14.8, bridge -14.8, breakcore -13.4 and -12.6, breakdown -16.4 with its widest stereo (correlation +0.25), the last stretch -12.8, -12.1 and -11.7, outro -21.2, fading to silence. The 808 sounds at D#1 (39 Hz) under the witch house section. On the Amen, snare hits measure 4-7 dB above the rest of the mix in the 1-4 kHz band.

## What it does not show

- **Gross Beat** (in FL's Signature edition and up) is left out so the piece builds on more editions; `docs/FX.md` covers automating it.
- **Mixer sends at a set level** other than sidechain, and **static pan**: the harness does not write them yet. Pan here is done with automation clips.
