# Composing: how to write a piece

A method from an empty project to a rendered piece. Mechanics (tools, the piece script, positions, units, samples, effects, render) are in `MECHANICS.md`; drum craft from outside sources in `DRUMS.md`. Nothing here is a law. Their verdict outranks all of this.

## 0. Stance

- **Write from nothing.** Unless asked otherwise. No existing project as a base, no channel copied for its sound, no old composition script read to learn from. A copied base drags in another piece's mixer and choices; a copied script anchors the new piece on the last one.
- **Write every note and every placement out by hand.** Every note of every part (drums, bass, melody, chords, chops, one-shot hits) and every clip in the arrangement is its own typed row. No `for`, `while` or comprehension writes a note or a clip. No list is repeated by multiplication. No function returns notes or clips. No formula, modulo, transposition or random choice picks a position, length, pitch or bar. Placing a written pattern again is allowed, one typed clip row per placement. Helpers that turn one typed row into the document's form (`P`, `at`, `note`, `clip`) are fine; a helper never decides where a row goes. The script and its JSON change only by hand edits: no regex or helper script adds, copies or moves rows. Code that writes notes or clips makes them free to add, so eighty placements cost what eight do and none of them gets weighed.
- **Measure to know, never to correct.** A render says where a note sounds and how wide and loud each section is. Detune, an octave accident, a peak past 0 dBFS are choices once known; breaking a rule never makes something wrong.
- **More does not name the dimension.** A request for more (harder, more complex, deeper) does not name the dimension. Candidates: harmony and voicing, layering and counter-lines, sound design and processing, arrangement and contrast, rhythm. Cutting up or re-placing material already written is the cheapest of these and adds the least. A request for more is answered first with more written music.
- **The work is the point.** A piece takes as many notes, parts and passes as it needs. Nothing is left out because writing it is long; choosing the smaller version because it is less to type is the failure this file exists to stop.
- **Stay away from the probable.** The first idea is the most typical one: the textbook progression, the hook over a beat, the common voicing, the genre's usual move. For each part, write in `<piece>.md` what the textbook version would be, then write something else. A bias away from the expected is wanted even when it overshoots: an odd choice can be pulled back after a verdict, and a typical one leaves nothing to pull back.

## 1. Order of work

Write starting from melodies, bass and drums

0. **Whose piece**: run `profile` first. Without a folder it reads the one saved in `projects_folder`; when none is saved, ask the user where their projects are and pass that folder, or set `projects_folder` to `none` when they have none. Ask for favourites (a `favourites/` folder) when they can name any.
1. **The piece**: tempo, tonal centre, and its core material: a cell, a sound, a drum floor or a line, whichever the piece grows from.
2. **Form**, from that material (§7).
3. **Part map**: a table of bars against parts. For each part: its register band, its rhythmic layer (held, half, quarter, 8th, 16th, free), and per section whether it moves, holds, rests or answers. Parts claim different registers and layers; where one moves, another holds.
4. **Sounds**: pick by role from `plugins`, `presets` and `samples`, measure sounding octave and tuning (§8).
5. **Variants**: write one 8-bar section in 2-3 versions that differ along one stated dimension (harmony, layering, timbre, rhythm). Render each as a short clip; the user picks, and the piece grows from the pick.
6. **Harmony and lines** (§3).
7. **Drums**, if the piece needs them (§4).
8. **SFX and texture**
9. **Levels and effects** (§9).
10. **Render and read** (§10). Write what the piece does and why in `compositions/<piece>/<piece>.md` before anyone hears it.

## 2. Tempo and meter

### Tempo

Any tempo, chosen per piece. Layers and sections relate by 0.5x, 1x, 2x: half and double time are the same tempo felt differently.

### Strong and weak positions

Every position belongs to a tier, and the tier decides what a hit there does:

| tier | written as | role |
|---|---|---|
| 1. counted beats | `P(b)` | strong: structure, downbeats, the hits the ear counts |
| 2. the "and" | `P(b, 1, 2)` | weaker: the main place for movement and offbeat shifts |
| 3. 16ths | `P(b, 1, 4)`, `P(b, 3, 4)` | on the grid but less expected: ornament, density |
| 4. 32nds and finer | `P(b, n, 8)` | off-beat; takes skill |
| 5. between grid lines (triplet and tuplet offsets against a 16th context, single-tick nudges) | `P(b, n, 3)`, `P(b, n, 6)` | the hardest tier: done well the best thing in a piece, done carelessly noise |

- **Structure on tiers 1-2, additions on 2-3.** Single 8th and 16th additions on the "and"s and 16ths hold up.
- **Tier 5 needs a reason the surrounding notes supply.** Triplet doubles dropped 32 or 16 ticks after stream hits, with nothing around them to answer, read as random keys. Say what a tier-5 hit answers or anticipates, or move it to tier 2-3.
- **The canvas collapses.** Every note placed narrows what can follow; ignoring that gives maximum entropy, which is noise. Place the structural hits first, then add, re-reading the bar after each addition.
- **Write positions as beat plus subdivision**, never ticks from the bar start: the tier shows in what you type, and an absolute tick is easy to type wrong.
- **Find where the count sits.** At a fast tempo the four counts may span two bars (at 176, one count per half note). Groupings of 3 or 5 bars come from time signature; the rest is 0.5x / 1x / 2x feel. Decide the counting grid first; the tiers are relative to it.

### Against the grid

A predictable grid and progression is one option, worth knowing how to use and how to leave. Ways out: cycles that do not match the bar (a 7-beat drum cycle over 4/4, 5-step groups over 16ths), uneven chord lengths, tempo automation, form extremes (16 bars nearly empty against 16 at full density). They work because the tiers still hold underneath.

## 3. Lines and harmony

### What good lines tend to do

- **Few pitches per cell**: a cell can live on four notes; the piece around it does not.
- **Leaps and neighbours**: 4ths, 5ths, 3rds, whole-step swaps around a note; three notes stepping one way is rare.
- **Syncopation, when it is the goal**: a dotted grid (0, 6, 12) is one way: bass and chord changes 6 sixteenths apart instead of on the beat. It sets where a note starts, not how long it lasts.
- **The bass holds by default**: few notes, each held for a bar or more, while the drums do the punctuating. Short bass hits locked to the kick are a valid choice, but a nuanced one that has to be executed well: the bass tuned to the kick, the kick's own pitch and tail, what fills the gaps. Make it on purpose, never by habit.
- **Cells restated with one substitution**: the one change is what gets heard.
- **Pedal against movement**: one voice holds while another moves, so the same note changes meaning (A#4 over E).
- **Played, not quantised**: onsets 2-22 ticks late, notes landing just before the bar line. A consistent lateness per part reads as feel; random per-note jitter does not.
- **A flat second** in minor (E in D# minor).

### What fails

- **Scale runs**: a chord tone, a leap, then the scale walked back. It sounds like an exercise.
- **A plain progression** (four equal chords in order) unless it is a deliberate transition.

### How much material

- **The ear follows the top line.** Whatever sits highest and loudest is what the listener tracks. A change under an unchanged top line (tempo, drums, chords, a new block order) is heard as the same music.
- **A piece needs new written material as it goes.** Restating a cell works inside a phrase, not across a whole piece. Each section brings something written for it: a new line, a counter-line, a changed cell, chords that move differently. Earlier material cut up or placed again does not count as new.
- **The top line changes across the piece**, in pitch, rhythm or which part carries it, unless the form says why it holds.

### Method

1. A tonal centre and the 3-5 pitches the lead mostly uses; which one is the anchor.
2. Bass roots first: few notes, each held until the next change. With a vocal, from the vocal (§6).
3. Chords with little motion between them; let a held note change meaning over a moving bass.
4. A 1-2 bar lead cell from leaps and neighbour swaps, restated with one substitution inside a phrase; each section adds material of its own (How much material).
5. Any run, trill or four-equal-chord loop is a decision to defend or remove.
6. Write a block (one to four bars) in every part before the next block, each part against the notes already in that block, and read the block back with `project_read(view="score")`. A part written alone from start to end cannot interlock with the others.

### Polyphony from two colliding lines

Two independent lines in one sound make harmony neither has alone:

- One fast and leaping: straight 8ths jumping between registers over chord and colour tones, every move a leap.
- One slow and low: a few notes in neighbour motion around one pitch, allowed to overlap.
- The same timbre for both, so they fuse into one instrument.
- Where they cross, mostly octaves, 3rds and 6ths, with 2nds and 7ths about a fifth of the time as colour. Do not correct a clash.
- Both played, not quantised: meetings a few ticks apart smear into one composite.
- Repeat the lines and move the bass and pad under them (one root per bar, alternating a step apart): the same notes read as a minor colour over one root and a lydian major 9 over the next. This holds for a phrase; across sections the lines themselves change.

## 4. Drums

### Whether the piece needs them

Drums are a judgment per piece.

### Floor, then additions

- **The floor** is a break or loop at the piece's tempo (a loop at the piece's tempo plays natively, anything else is repitched), or a stream of short one-shots. It carries the groove.
- **Split a break into attacks and bodies**: cut it at its own hits into two complementary sets of audio clips on two inserts, the first ~150 ms of each hit on one, the rest on the other. It plays as recorded, but the bodies can be filtered or distorted while the attacks stay sharp.
- **Read the floor's real timing** (`onsets.py`) and add relative to where its hits fall, not to the grid.
- **Additions make the floor denser and less predictable**: extra hits in its gaps, retriggers, stutters, a slice pitched down as a kick or up as a flam, a reversed beat. Rearranging inside is fine when it adds; a new pattern assembled from its pieces is not the point, and chopping a loop just to get a kit is wasted work. More than one break exists: reusing the same Amen piece after piece is the lazy choice, and a break of your own baked into a sample is valid.
- **Additions by tier** (§2): mostly the "and"s and 16ths; tier 4-5 only with a reason.
- **Every hit has a reason**: what it fills, answers or sets up.
- **The floor changes inside a section too**: an addition, a dropped hit or a swapped slice every few bars, so no loop carries a section unchanged.

### What reads as dead

- Equal spacing: one hit per 16th, whatever the sounds, is a metronome.
- Beat pieces in plain order: a staircase.
- Everything on strong positions while trying to sound off-beat.

### What gives movement

- **Layers a factor of 2 apart**: two loops, one twice as busy, fit without listening; which is heard as the base decides double or half time. Shift one by half a cycle so its strong hits land on the other's weak ones. A third can join at the drop.
- **A different floor per section**, the first returning for the return.
- **Phrases with stops**: a 2- or 4-bar phrase ending in hard silence, a longer stop every third phrase, a short silence at the same point inside each. A placed silence is a hit.
- **An 8th stream broken by doubles**: short dry full-band hits with digital silence between them, straight 8ths with doubles a triplet 8th or 16th apart, no backbeat emphasis, nearly mono. The doubles are tier 4-5 and follow §2.
- **SFX in the gaps**: impacts, glitch hits, risers, short noises. Without them a drum part is a pack of patterns.

### Sound and length

- **Short hits**: a sampler plays to its sample's end, so pick or cut one-shots to fit the gap.
- **Keep the wave connected** unless a gap is designed; a grain that ends long before the next hit is an accidental hole.
- **Audio clips crossfade** when they overlap on one playlist track (a kick becomes a wobble): trim each to the gap, or put the next on the next free track down. Trimming is not required for its own sake.
- **Group what will not be split** into one pattern.

## 5. Seams

A seam goes where the form needs one. A piece built as one process may have none; a block form is nothing but seams with no transitions between them.

A transition is written for its spot. What fails is reaching for one device by default, the same accelerating snare roll piece after piece. Repeating a device by choice is fine.

Ways that work:

- **Subtraction**: in the bar before the drop, cut the running loops against each other, every kept piece where it sits in the uncut loop, so the gaps make a rhythm neither loop had; then everything lands on the downbeat. It works because the bars before are rich; after a sparse section, adding more or a light off-beat push can be the answer.
- **Broken expectation**: build to a peak, take the last beat off the peak bar, bring the drop back as fragments and glitch for two bars, a full bar of silence, then the real drop.
- **A stop**: a beat or bar of silence at a phrase end; the downbeat after it is the accent.
- **Others**: a tape-stop (tempo automation down over a bar), a half-time bar, a pitch-climbing ratchet, a reversed slice, an impact on the downbeat, a filter-closed passage ending in a full stop.

## 6. Writing around a given vocal

A vocal stem cannot change, so everything else follows it.

1. **Measure its grid first**, from block onsets: a vocal at 95.0 BPM on a 96 grid drifts a bar out by the end.
2. **Map what it sings per bar** on that grid, and find its repeats.
3. **Take the roots from the vocal**, bar by bar, not from the instrumental or a drifted chord map.
4. **Every new line follows the vocal verbatim or alters it meaningfully.** A part developing on its own against it is the odd feel.
5. **Decide whether anything needs adding.** The instrumental's own bars, no drums and no pad can be the right answer.
6. **Keep the vocal at its own time and pitch relation.** Move it to a key by stretch, not resample, and by as few semitones as possible (`MECHANICS.md`, Traps).

## 7. Form

Intro, a section, a transition, a second section, an outro is the shape a piece falls into when its form is filled in rather than chosen. It is one form among many and needs a reason like any other.

### Form comes from the material

Write the core material first, then decide the form from what it can do: what can grow, what can be taken away, what can come back changed, what can collide with something else.

Write the form as one sentence about what happens over time, before any list of sections: "one break loses a piece every 16 bars until only its ghost notes are left", "two loops of different cycle lengths drift apart and line up again at the end". "Intro, build, drop, break, drop, outro" names slots, not a form.

### Shapes

- **Process**: one change runs through the whole piece (adding, subtracting, a filter, a density or tempo curve, two loops drifting in phase). There are no sections; the ear follows the change.
- **Blocks**: unrelated blocks cut against each other with no transitions, coming back in other orders and lengths.
- **Through-composed**: every part is new and nothing returns. Sound and tempo hold it together.
- **Return with change**: one idea comes back different each time (A B A' C A'').
- **Variation**: one phrase heard many times, each pass changed in one dimension.
- **Arch**: builds to the middle and unwinds in reverse order.
- **Collision**: two ideas set up apart, then played together.
- **Loop and interruptions**: one bar or phrase, broken into by events.
- **One gesture**: a single rise, collapse or decay, with no payoff section.

Every shape still needs new material (§3, How much material). In Variation, Loop and interruptions, and Process, the changes reach the top line, not only what is under it.

### Phrases and lengths

Each phrase restarts the count; its strongest point is the cadence landing on the next phrase's first beat. Lengths are uneven unless evenness is the point: 16 8 8 24 2 2 2 16 16.

### Contrast

Tools for contrast, as fast, dense styles use them:

- **Hard switches**: a new texture with its own material, switched at once.
- **Silence as a transition**: a near-silent drop, a full dropout of a few seconds, short hard gaps every 16 bars that keep a long wall alive.
- **Width as a switch**: mono walls against wide, bassless breakdowns.
- **Loudness as a sound**: walls at -6 to -12 dBFS RMS, peaks past 0 dBFS.

### Starts

No intro by default. A piece can open on its densest material, in the middle of a phrase, or on a sound that never comes back. A quiet start well under the first full section (20 dB under is fine) is one choice among these.

### Endings

No outro by default. A piece can stop mid-phrase, on a cut, on its quietest moment, or on a fragment of something earlier.

- A render stops at the last note. For a tail, use a flat automation clip on any parameter, a bar or two past the last pattern.
- Cap long audio clips at the intended end.
- The last sound is heard alone: level it on its own.

## 8. Sounds and material

### Choosing synths

- **Start from a preset.** A perfectly periodic init saw reads as machine-made.
- **Audition across instruments, not inside one.** For each role, find candidates in at least three different instruments (`presets(plugin, query)` on each), render the short list, and keep what serves the part. A piece built from one instrument's presets sounds like that instrument.
- **Instruments differ in how they make sound**, and that shows more than any preset name:

  | synthesis | instruments |
  |---|---|
  | analog-modelled, filter-led | Diva, Sylenth1, PoiZone, Sawer, SimSynth |
  | wavetable | Serum 2, Vital, Massive X |
  | FM | Sytrus, Fruity DX10 |
  | additive, resynthesis | Harmor, Harmless, Ogun (metallic) |
  | physical modelling | Sakura (strings), FL Slayer (guitar) |
  | sampled instruments | FLEX, FL Keys |

- **Instruments that list 0 presets** (Pigments, Omnisphere, Nexus, DUNE 3 and others) keep their presets inside the plugin. `presets(plugin, harvest=true)` reads them only when the plugin has a parameter named `Program`; otherwise a sound becomes usable by name once it is saved from FL's plugin menu as an `.fst`.
- **Ask what the user has and likes.** Which synths and libraries are on the machine is theirs to say, and so is which they trust; `plugins` and `presets` list what is installed and what loads.
- **Choose by role, not by meter.** A render cannot say which candidate sounds best, and a meter reading (loudest, brightest, cleanest) is no reason to keep one. Choose by what the part needs (register, attack, sustain, how far it should stand out), and name the candidates and the reason in `<piece>.md` so the user's ear can overrule it.
- **Not binary**: a weak preset can work under effects or in a small role; an unlucky pick is replaced, not mixed around.

### Know where it sounds

Render one note and read its lowest partial before writing a range. Many presets transpose by one or two octaves; FLEX's Hard 808s / 808 Clean Fuzz sounds two octaves below the written note (written G2, 24.2 Hz). Once known, the shift is yours to use.

### Detune

Measure tuning so detune is a choice. A preset a quarter tone sharp can be the best thing in the low mids. Never retune only because a meter says it is off.

### Samples and chops

- **Rough sources make good chops**; pitch-tracker failures on screams say nothing about the chop.
- **Chopped vocals work as percussion**: grains as pitched-up 16th-triplet hits, a vowel grain restruck every 32nd while diving.
- **Breaks as a sound source**: slices pitched down for kicks, up for flams, a snare ratchet climbing an octave.
- **Chop entry points**: slices of one scream that all end at its tail but start at different points give a family of related hits. Restate the phrase in a later section, then thin it.
- **A scrub by hand**: a recording cut into consecutive slices placed in order on uneven ticks reads as the sound dragged through; it suits the busiest bar of a transition.
- **Overlapping slices alternate between two playlist tracks** so they do not crossfade.
- **Render a part to keep it**: render a part with its effects, use the WAV as a sample, change or drop the effects.

## 9. Mixing

An unmixed piece is not finished: write faders and effects into the document.

### Starting levels

A starting point in dB under 0, from two mixes made by hand: bass -3, pad -4, lead -4, ostinato -6, kick -7, open hat -7, clap -8, crash -8, counter-line -10, closed hat -11, snare -11.5; master volume 12800 -> 10600. Adjust from the render to balance parts; a section's weight comes from what plays in it (below). The lead at -4 comes from mixes where it sat over a dense arrangement; a bright or saturated lead starts lower.

### Faders balance; the writing gives a section its weight

A fader balances parts that are already right. When a section sits wrong against the others (a peak no bigger than what came before it, a quiet part heavier than the peak), the cause is in what plays: which parts, their register and voicing, the sounds and their lengths, the processing. Find it and change that. Raising whatever already dominates, usually the drums, until the section's number comes out right covers the rest of the mix and drives the master limiter, which then pulls every other part down on each hit.

A section gains weight without a fader through:

- a part that carries the music, not only drums: an octave doubling, stabs in the gaps of the break;
- another written part: a counter-line, chops used as a line rather than an ornament;
- contrast before it: the section before thinner, darker or narrower;
- a mastered break loop brought down at the source and split into attacks and bodies (§4), so it sits with the music instead of over it.

A section that is too heavy is a sound or length choice to revisit, such as an 808 ringing for two bars under a kick, not a reason to turn everything else up.

### Width

There is no target width. Finished tracks run from near mono (correlation +0.94) to side/mid -8 dB with correlation +0.54. Side/mid at -16 to -19 dB reads as dual-mono; at -4 with correlation dipping below 0 it is partly out of phase. Width comes from presets with unison and detune, reverb and stereo samples, and can switch by section (§7). Read it per element with `scope.py`. Static pan is not writable yet.

### Effects

- **Reverb** can go anywhere, doesn't mean should; it often makes a sharp, dry sound more natural.
- **Sidechain** when needed: a level-0 route plus the compressor-mode Fruity Limiter on the ducked insert.
- **Loudness**: a limiter on the master and gain up. Past 0 dBFS is a sound; clipping nobody chose (long full-scale runs in one section) is not.
- **Gross Beat** for stutters, gates, half-speed and tape-stops on a bus or the master: parameters and slots in `FX.md` (slot = round(v x 35)), the unmapped pattern state in `FLP.md`.

### Effects in and out

- **Switch an effect by its mixer slot**: the mute switch and mix level are automatable. 0 or 1 for a hard switch on a bar line, a curve for an effect that grows (a bus limiter's mix 0 -> 1 over half a piece).
- **One bus for the whole mix** lets one Gross Beat or limiter act on everything.
- **Gross Beat changes slot on the next bar**: switch it at the end of the bar before.
- **Where Gross Beat hits hardest**: just before a phrase's strongest downbeat (the bar before 5, 9, or 17 once the structure is established), or a glitch right before a drop or across into it. Keep it short: left on too long it stops being fun. Choose the slot by what it measurably does (`FX.md`).

Every sound that might be processed alone gets its own insert from the first draft. Grouped by role, an EQ or saturator on that insert hits everything in it, and the first step of mastering becomes splitting them apart.

### Mastering: clarity, not level

The first failure to look for is mud: the mix sounding submerged because the low and low-mid range is crowded and the hits have no edge. It does not show on a meter. The fix is placement: the same parts, each where it does not cover another.

- **The loudest thing is the one you don't hear.** Sub energy fills meters and the limiter's budget while the ear barely registers it. Let the bass be heard through its harmonics (saturation adds them and a transient) and keep its fundamental at the level it is felt.
- **The high mids (about 1-4 kHz) are where the ear hears loudness and detail**, so a little goes a long way: a lead pushed there turns harsh before any meter shows it.
- **Width per element, both directions**: narrow what is too open (an impact so wide it reads as reverb), widen what needs space; drums placed in the panorama, not one cloud.
- **Bring quiet passages up** so detail does not drop out.
- **Leave the limiter little to do**: bring the sum in below the master and make level up there.

### Loudness is what the ear hears

Peak, RMS and LUFS can rate two masters equal while one sounds clearly louder. They do not settle which is louder; listening does.

### Measure the mix

Read a render through `render_report`: the spectrogram first, the flags second. A measurement points at a place to listen; it is not a target. A small dip, a short gap or a score inside its band is not a defect, and the fix for a thin passage is in the writing (note lengths, voicing, what sustains), not a layer added over it. Ask for detail (`--detail`, `scope.py`) only for a question the picture raised.

### Wash

Every note leaves a fading copy that still sounds under the next ones, at a middle level: neither held nor gone. It is not density. Sound held at the top is a wall; sound with a clear on and off is structure. A blur with fresh notes standing clearly above it is haze, not wash.

The report's wash flag, the `ghost %` strip under the spectrogram, and the wash table in the `.txt` (`scripts/wash.py`):

- **ghost**: a semitone cell still sounding 0.5 s after its band's last onset, 3 dB or more under that onset's peak, and not faint. Master fades and drop-outs are removed first.
- **stretches**: 4 s windows over 30% ghost, joined across gaps up to 6 s.
- **weight**: grows with length (under 10 s near 0, 20 s half, 30 s nearly full). It shrinks when ghost climbs into or falls out of the stretch faster than 2 points/s, multiplied by 2/rate: a wash drifts, while a section change jumps. Once stretches cover half the track, all count fully. **score** is the weighted share of the track: under 6 clear, 6-16 haze, over 18 wash.
- **head**: how far fresh notes stand over the ghosts, in dB. Under 12 is tagged wash, over 12 haze.

The report flags wash only from a score of 16 up; clear and haze are not reported.

The cut-offs (30%, 12 dB, 2 points/s, score 18) rest on few labelled tracks.

Causes: effects built into an instrument (FLEX, `MECHANICS.md` Traps), a reverb on every channel, a pedal held over a fast arpeggio. To find which, render one note per channel. With Δ the time between notes on that channel, the dip between notes is 60·Δ/T60 dB; under about 6 dB, the notes never separate.

### Reading someone else's chain

Reason from what changed in the wave and spectrum (level, band balance, transients, width per band, gain against input), then ask what each effect was for. An effect's name does not say what it was used for.

## 10. Render and read

1. **Read the arrangement before rendering.** `project_read(view="summary")` gives each pattern's clip count and span and each track's timeline. For each part, compare the bars written with the bars that play, and note how many bars the top line repeats unchanged. Write both into `<piece>.md`; a part that plays far more bars than were written for it is a choice the `.md` defends.
2. Render to wav and mp3 and run the analysis (`MECHANICS.md`).
3. Check the length: the render runs to the last note or automation point (§7 for a tail).
4. Read section by section against `compositions/<piece>/<piece>.md`: does each switch show in level, width, spectrum? Any bass below about 30 Hz by accident, unintended clipping, a start that is not actually quiet, a wash stretch (§9)?
5. The render is numbers and pictures; listening is the verdict, and it is the user's. Record what changes because of it.

## 11. Dropping a piece

Round after round of fixes on a piece whose hard part stays as it was rarely saves it. When a piece gets a mixed verdict two rounds running, ask the user whether to park it, and carry forward only what they named as good.

## Checklist before calling a piece done

- Every drum hit has a reason; no accidental equal spacing or staircase; tier 4-5 hits justified.
- Every note and every clip placement written out row by row in the script; no loop, comprehension, formula or edit script produced any of them.
- Runs, trills and four-equal-chord loops by choice.
- Every synth on a preset.
- Each synth role was auditioned in at least three instruments; `<piece>.md` names the candidates and why one won. One instrument playing most parts is a choice the `.md` defends.
- Every sound on its own insert.
- Faders and effects written; width read per element with `scope.py`.
- Each section's weight against the others comes from its parts and sounds; faders only balance them.
- `compositions/<piece>/<piece>.md` says what each part is for.
- The form is one sentence in `<piece>.md`. If it reads intro, section, transition, section, outro, the `.md` says why.
- `<piece>.md` says what new material each section brings; the top line changes across the piece, or the `.md` says why it holds.
