# Composing: how to write a piece

A method from an empty project to a rendered piece. Mechanics (tools, the piece script, positions, units, samples, effects, render) are in `MECHANICS.md`; drum craft from outside sources in `DRUMS.md`. Nothing here is a law. Their verdict outranks all of this.

## 0. Stance

- **Write from nothing.** Unless asked otherwise. No existing project as a base, no channel copied for its sound, no old composition script read to learn from. A copied base drags in another piece's mixer and choices; a copied script anchors the new piece on the last one.
- **Write every drum hit and bass note out by hand.** The piece script places no drum hit or bass note through code: no `for` or `while` over bars or steps, no function that returns a pattern, no formula, modulo or random choice that picks a position, length or pitch. Each hit and each note is its own row. A written bar or phrase may be placed again whole as a pattern clip; a bar that differs is written as its own bar. Code that places notes makes them free to add, so they pile up without being weighed.
- **Every drum hit is there for something**: it fills, answers or sets up (§4).
- **Measure to know, never to correct.** A render says where a note sounds and how wide and loud each section is. Detune, an octave accident, a peak past 0 dBFS are choices once known; breaking a rule never makes something wrong.
- **Write a whole piece**: one to two minutes with a form, not an 8-bar loop.
- **More does not name the dimension.** A request for more (harder, more complex, deeper) does not name the dimension. Candidates: harmony and voicing, layering and counter-lines, sound design and processing, arrangement and contrast, rhythm.

## 1. Order of work

Write in stages and check each before the next, so a wrong sound or groove is caught cheaply:

0. **Whose piece**: when the person has projects of their own, run `profile` on their folder first and read its Read back list to them; what they keep sets the tempo, key, form, drum grid and sounds below, and its pointers bring their own sounds in without decoding them. Ask for favourites (a `favourites/` folder) when they can name any.
1. **The piece**: tempo, tonal centre, a form sketch: sections, lengths, where each switch happens and what kind (§7).
2. **Sounds**: pick from the catalogs by role, render a short test, measure each one's sounding octave and tuning (§8).
3. **Harmony and lines** (§3).
4. **Drums**, if the piece needs them (§4).
5. **Transitions**, each for its own spot (§5).
6. **SFX and texture** in the gaps.
7. **Levels and effects** (§9).
8. **Render and read** (§10). Write what the piece does and why in `compositions/<piece>.md` before anyone hears it.

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

- **Few pitches**: a lead can live on four notes for 32 bars.
- **Leaps and neighbours**: 4ths, 5ths, 3rds, whole-step swaps around a note; three notes stepping one way is rare.
- **Syncopation, when it is the goal**: a dotted grid (0, 6, 12) is one way: bass and chord changes 6 sixteenths apart instead of on the beat. It sets where a note starts, not how long it lasts.
- **The bass holds by default**: few notes, each held for a bar or more, while the drums do the punctuating. Short bass hits locked to the kick are a valid choice, but a nuanced one that has to be executed well: the bass tuned to the kick, the kick's own pitch and tail, what fills the gaps. Make it on purpose, never by habit.
- **Cells restated with one substitution**: the one change is what gets heard.
- **Pedal against movement**: one voice holds while another moves, so the same note changes meaning (A#4 over E).
- **Played, not quantised**: onsets 2-22 ticks late, notes landing just before the bar line. A consistent lateness per part reads as feel; random per-note jitter does not.
- **A flat second** in minor (E in D# minor).

### What fails

- **Scale runs**: a chord tone, a leap, then the scale walked back. It sounds like an exercise.
- **A two-note trill** for a whole cell.
- **A plain progression** (four equal chords in order) unless it is a deliberate transition.
- **Nothing unexpected anywhere.** The unexpected can be a sound, a chord, a stop, a drop or a transition. It does not have to be a displaced hit.

### Method

1. A tonal centre and the 3-5 pitches the lead mostly uses; which one is the anchor.
2. Bass roots first: few notes, each held until the next change. With a vocal, from the vocal (§6).
3. Chords with little motion between them; let a held note change meaning over a moving bass.
4. A 1-2 bar lead cell from leaps and neighbour swaps, restated with one substitution; the larger change at a section switch.
5. Any run, trill or four-equal-chord loop is a decision to defend or remove.

### Polyphony from two colliding lines

Two independent lines in one sound make harmony neither has alone:

- One fast and leaping: straight 8ths jumping between registers over chord and colour tones, every move a leap.
- One slow and low: a few notes in neighbour motion around one pitch, allowed to overlap.
- The same timbre for both, so they fuse into one instrument.
- Where they cross, mostly octaves, 3rds and 6ths, with 2nds and 7ths about a fifth of the time as colour. Do not correct a clash.
- Both played, not quantised: meetings a few ticks apart smear into one composite.
- Repeat the lines and move the bass and pad under them (one root per bar, alternating a step apart): the same notes read as a minor colour over one root and a lydian major 9 over the next.

An arp that worked: the voicing an octave up, one note per 16th, voice index `(3 * s + s // 4) mod 4` at step `s`.

## 4. Drums

### Whether the piece needs them

Drums are a judgment per piece, not a default. Over a vocal they can pull against it, and leaving them out can be the right call.

### Floor, then additions

- **The floor** is a break or loop at the piece's tempo (a loop at the piece's tempo plays natively, anything else is repitched), or a stream of short one-shots. It carries the groove.
- **Split a break into attacks and bodies**: cut it at its own hits into two complementary sets of audio clips on two inserts, the first ~150 ms of each hit on one, the rest on the other. It plays as recorded, but the bodies can be filtered or distorted while the attacks stay sharp.
- **Read the floor's real timing** (`onsets.py`) and add relative to where its hits fall, not to the grid.
- **Additions make the floor denser and less predictable**: extra hits in its gaps, retriggers, stutters, a slice pitched down as a kick or up as a flam, a reversed beat. Rearranging inside is fine when it adds; a new pattern assembled from its pieces is not the point, and chopping a loop just to get a kit is wasted work. More than one break exists: reusing the same Amen piece after piece is the lazy choice, and a break of your own baked into a sample is valid.
- **Additions by tier** (§2): mostly the "and"s and 16ths; tier 4-5 only with a reason.
- **Every hit has a reason**: what it fills, answers or sets up.

### What reads as dead

- Equal spacing: one hit per 16th, whatever the sounds, is a metronome.
- Beat pieces in plain order: a staircase.
- Everything on strong positions while trying to sound off-beat.
- One edit per bar on a straight floor.
- A march: single hits on a repeated 2-bar pattern.

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

## 5. Transitions and drops

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

### Phrases reset the count

Each phrase (16 bars, or 8, 24, 32, or a chain like 16 8 8 24 2 2 2 16 16) restarts the count; its strongest point is the cadence landing on the next phrase's first beat. Plan phrase lengths first; the seams are where drops, stops and glitches go.

### Contrast

Tools for contrast, as fast, dense styles use them:

- **Hard switches**: a new texture every 15-20 s, switched at once.
- **Silence as a transition**: a near-silent drop, a full dropout of a few seconds, short hard gaps every 16 bars that keep a long wall alive.
- **Width as a switch**: mono walls against wide, bassless breakdowns.
- **Loudness as a sound**: walls at -6 to -12 dBFS RMS, peaks past 0 dBFS.

Sketch the form as sections with what each changes: texture, density, width, register, tempo feel, drum floor, or only notes.

### Starts

- An intro has its own idea (a texture, a fragment of what comes later, a rise from silence), not one pattern to start from.
- Save the loudest sound; a quiet intro well under the first full section (20 dB under is fine) works.

### Endings

- A render stops at the last note. For a tail, a flat automation clip on any parameter a bar or two past the last pattern.
- A hard cutoff can be the design; choose it.
- Cap long audio clips at the intended end.
- The last sound is heard alone: level it on its own.

## 8. Sounds and material

### Choosing synths

- **Start from a preset.** A perfectly periodic init saw reads as machine-made.
- **Ask what the user has and likes.** Which synths and libraries are on the machine is theirs to say, and so is which they trust; the catalogs (`MECHANICS.md`) list what each library holds.
- **Choose by sound, not numbers**: a preset or sample that measures clean is not thereby good. Render candidates and keep what serves the part.
- **Not binary**: a weak preset can work under effects or in a small role; an unlucky pick is replaced, not mixed around.

### Know where it sounds

Render one note and read its lowest partial before writing a range. Many presets transpose by one or two octaves; FLEX's Hard 808s / 808 Clean Fuzz sounds two octaves below the written note (written G2, 24.2 Hz). Once known, the shift is yours to use.

### Detune

Measure tuning so detune is a choice. A preset a quarter tone sharp can be the best thing in the low mids. Never retune only because a meter says it is off.

### Samples and chops

- **Rough sources make good chops**; pitch-tracker failures on screams say nothing about the chop.
- **Chopped vocals work as percussion**: grains as pitched-up 16th-triplet hits, a vowel grain restruck every 32nd while diving.
- **Breaks as a sound source**: slices pitched down for kicks, up for flams, a snare ratchet climbing an octave.
- **A stutter wants a short grain**; a long vowel at 32nds on a sampler becomes one cloud.
- **Chop entry points**: slices of one scream that all end at its tail but start at different points give a family of related hits. Restate the phrase in a later section, then thin it.
- **A scrub by hand**: a recording cut into consecutive slices placed in order on uneven ticks reads as the sound dragged through; it suits the busiest bar of a transition.
- **Overlapping slices alternate between two playlist tracks** so they do not crossfade.
- **Render a part to keep it**: render a part with its effects, use the WAV as a sample, change or drop the effects.

## 9. Mixing

An unmixed piece is not finished: write faders and effects into the document.

### Starting levels

A starting point in dB under 0, from two mixes made by hand: bass -2, pad -4, lead -4, ostinato -6, kick -7, open hat -7, clap -8, crash -8, counter-line -10, closed hat -11, snare -11.5; master volume 12800 -> 10600. Adjust from the render.

### Width

There is no target width. Finished tracks run from near mono (correlation +0.94) to side/mid -8 dB with correlation +0.54. Side/mid at -16 to -19 dB reads as dual-mono; at -4 with correlation dipping below 0 it is partly out of phase. Width comes from presets with unison and detune, reverb and stereo samples, and can switch by section (§7). Read it per element with `scope.py`. Static pan is not writable yet.

### Effects

- **Reverb** can go anywhere; it often makes a sharp, dry sound more natural.
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
- **Lift the high mids** (about 1-4 kHz), where the ear hears loudness and detail.
- **Width per element, both directions**: narrow what is too open (an impact so wide it reads as reverb), widen what needs space; drums placed in the panorama, not one cloud.
- **Bring quiet passages up** so detail does not drop out.
- **Leave the limiter little to do**: bring the sum in below the master and make level up there.

### Loudness is what the ear hears

Peak, RMS and LUFS can call two masters equal within 0.6 dB while one is clearly louder. Zwicker (ISO 532-1, `loudness.py --zwicker`) put the louder one 22% up, in 630 Hz-4.4 kHz. Compare masters by that, never by peak.

### Measure the mix

Read per section: RMS, side/mid, correlation, the bass's lowest partial, where each part sits in the spectrogram; `scope.py` for width per moment and band. Correct from those, the way an assistant EQ would.

### Reading someone else's chain

Reason from what changed in the wave and spectrum (level, band balance, transients, width per band, gain against input), then ask what each effect was for. An effect's name does not say what it was used for.

## 10. Render and read

1. Render to wav and mp3 and run the analysis (`MECHANICS.md`).
2. Check the length: the render runs to the last note or automation point (§7 for a tail).
3. Read section by section against `compositions/<piece>.md`: does each switch show in level, width, spectrum? Any bass below about 30 Hz by accident, unintended clipping, a start that is not actually quiet?
4. The render is numbers and pictures; listening is the verdict, and it is the user's. Record what changes because of it.

## 11. Dropping a piece

Round after round of fixes on a piece whose hard part stays as it was rarely saves it. When a piece gets a mixed verdict two rounds running, ask the user whether to park it, and carry forward only what they named as good.

## Checklist before calling a piece done

- Every drum hit has a reason; no accidental equal spacing or staircase; tier 4-5 hits justified.
- Every drum hit and bass note written out row by row in the script; no code computes any of them.
- Runs, trills and four-equal-chord loops only by choice.
- Every synth on a preset, its sounding octave measured.
- Every sound on its own insert.
- Faders and effects written; width read per element with `scope.py`.
- No mud: every part audible where it was written, the bass heard and not only metered, loudness compared by ear model.
- SFX where the drums leave gaps.
- A tail, or a chosen hard cutoff.
- `compositions/<piece>.md` says what each part is for.
