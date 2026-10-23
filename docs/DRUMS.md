# Drums: how to write them note by note

Craft research for placing every hit at 96 PPQ in 4/4 on FL samplers, which play a sample to its end whatever the note length. Tags: **[M]** measured or documented; **[P]** a producer's or tutorial's opinion; **(1)** one source only; **[here]** written for this file (arithmetic, illustrations). Where sources disagree, both sides are given. The user's verdicts outrank all of it.

## Units at 96 PPQ [here]

| value | ticks | at 140 BPM | at 174 | at 180 | at 211 |
|---|---|---|---|---|---|
| beat (quarter) | 96 | 428.6 ms | 344.8 | 333.3 | 284.4 |
| 8th | 48 | 214.3 | 172.4 | 166.7 | 142.2 |
| 8th triplet | 32 | 142.9 | 114.9 | 111.1 | 94.8 |
| 16th | 24 | 107.1 | 86.2 | 83.3 | 71.1 |
| quintuplet 16th (5 per beat) | 19.2 | 85.7 | 69.0 | 66.7 | 56.9 |
| 16th triplet (6 per beat) | 16 | 71.4 | 57.5 | 55.6 | 47.4 |
| septuplet 16th (7 per beat) | 13.7 | 61.2 | 49.3 | 47.6 | 40.6 |
| 32nd | 12 | 53.6 | 43.1 | 41.7 | 35.5 |
| 32nd triplet | 8 | 35.7 | 28.7 | 27.8 | 23.7 |
| 64th | 6 | 26.8 | 21.6 | 20.8 | 17.8 |
| 1 tick | 1 | 4.46 | 3.59 | 3.47 | 2.96 |

Positions are 16th steps 0-15 (tick = step x 24) or ticks from the bar start (0-383; 0-767 over two bars).

**Swing** is the MPC's [M]: every second 16th of an 8th pair is delayed, and the percentage is the first 16th's share of the pair, so the late 16th lands `48 x swing` ticks after its 8th:

| swing | 50% | 54% | 57% | 58% | 62% | 66% | 70% | 74% |
|---|---|---|---|---|---|---|---|---|
| late 16th at | 24 | 26 | 27 | 28 | 30 | 32 (8th triplet) | 34 | 36 |

8th-note swing uses the 96-tick pair: 57% puts the offbeat 8th at 55 instead of 48.

## 1. General craft

### 1.1 Grid, micro-timing and humanisation

Studies:

- **Quantized grooves as well as expert timing.** Fully quantized patterns got the highest groove ratings and large deviations the lowest (Frühauf et al.; Davies et al., 2013) [M]. Two expert bass-and-drum performances scaled from 0% to over 100% of their microtiming: quantized and original rated "equally high", exaggerated timing lost groove and raised irritation (Senn et al. 2016) [M].
- Listeners do not reliably detect deviations up to 30 ms (Butterfield) [M], about 9 ticks at 180 BPM.
- Against that, expert listeners moved most to "tight but non-zero" microtiming and little to quantized music, while still rating it high (Kilchenmann and Senn 2015) [M].
- **Correlated, not random.** Human timing errors drift (1/f-like). Listeners preferred correlated humanising over white-noise per-beat offsets, which is what DAW humanise does (Hennig et al. 2011) [M].
- **Size.** Porcaro's one-hand 16th hats on "I Keep Forgettin'": mean 157 ms, SD 8.7 ms (5.5% of a 16th, about 1.3 ticks), consecutive intervals anticorrelated (r = -0.48). A drummer on a metronome at 180 BPM: SD 15.6 ms [M].
- **Laid-back snare**: 17.4 ms late on average at 96 BPM [M], 5 ticks at 180.

Practitioners, who disagree:

- Linn [P]: random timing and late snares never did "much good"; with swing and dynamics right, notes work best "at exactly the perfect time slots".
- J Dilla lesson [P, (1)]: a constant offset per voice held every bar, e.g. kick on the click, snare 30 ms late, hat 30 ms early.
- Drunk-drummer grooves [P]: positions from quintuplet, sextuplet and septuplet grids instead of nudging. Two hats on quintuplets 1 and 4 split the beat 3:2, on septuplets 4:3. Flams add drag.
- Splice [P]: about ±1 tick of random humanise at 96 PPQ, then re-quantize kicks and crashes that land together.
- Chopped breaks: kick and snare on the grid [P], or keep the break's own positions and "resist the urge to quantize everything" [P].

### 1.2 Swing

- 50% is straight, 66% the triplet. At 90 BPM 62% "will feel looser" than 66%; on straight 16ths 54% loosens the feel "without it sounding like swing" [P].
- Per voice: kick and snare "MPC 3000 8ths 57", hats "16th 74" [P]; hats at 15%, 57% and 35% [P].
- "Shook Ones Pt. II": kicks at 1.2.4 and 1.4.4 sit "halfway between that grid line and the next" while the 8ths stay straight [M, (1)].
- Trap is "sequenced straight, without swing" [P].

### 1.3 Velocity, accents and ghost notes

- **Accents repeat.** Porcaro's hats run "high-low-medium-low-very high-low-medium-low", the very high on the snare; one 2-bar phrase's amplitudes correlate 0.88 with the next [M]. Equal velocities are "a bad drum machine"; vary note-repeat pressure "from light to medium continuously and somewhat randomly" [P].
- **Hierarchy** [P]: hat loudest on 1, then 3, then 2 and 4, offbeats quietest. Kick and snare vary only slightly. Fills alternate like two hands. Do not copy one bar's velocities to every bar.
- **Amen** [M]: the first kick of the double before beat 4 is "slightly quieter than the second"; the bar's last snare is below the main ones but "not quite down the level of a ghost note"; the ride is "full strength eighth-notes".
- **Ghost notes** [M]: "very softly between the 'main' notes", usually snare, for "a subtle 16th-note feel around a strong back beat" (Amen, "Cold Sweat", "Rosanna").
- **Drill velocities** [P]: main hits 100, second hat of each group 87, the bar-1 pickup hat 52, last kick 96, percussion 91.
- **Call and response** [P]: in a fill, low then high; the snare answers the kick.
- In the harness velocity is a per-note field (default 100). How much it changes a sampler's level depends on the channel's velocity tracking: check the render [here].

### 1.4 Syncopation and density

- Medium syncopation drew the most wish to move, an inverted U [M]. Groove tracked event density, beat salience and syncopation, not microtiming size [M].
- A kick or snare under most bass notes and chord changes [P].

### 1.5 Phrase length and where variation goes

- **Amen** [M]: bars 1-2 the same; bar 3 holds the beat-4 snare back half a beat and drops the kick double; bar 4 leaves beat 1 empty, moves the double to the start and puts a crash between beats 3 and 4, "a very unusual way of marking the end of the phrase".
- Porcaro: the 2-bar phrase is the unit, drift above it, alternation below it [M].
- A 2-bar cell looped to 4 or 16 bars with the last bar or last two beats replaced [P].
- RP Boo: "I got tracks that are on the three". Moving where "one" feels is a variation as strong as a fill [P].

### 1.6 Fills, hard stops and silence

- A fill marks a section end. The house fill is 16th snares rising in velocity, swung by delaying every second one [P].
- Dropout fills: only the snare plays under the fill [P], or the last two beats of 16 bars go silent and a snare fill plays alone [P].

### 1.7 Triplets, tresillo and polyrhythmic overlays

- **Tresillo 3+3+2** [M; P]: 16th steps 0, 3, 6 per half bar or across a bar. Drill hats run "two spaces, two spaces and one space repeated", from grime [P].
- Trap hats use "double-time, triple-time, and similarly divided" subdivisions [M].
- **Odd meters over 4/4**: Venetian Snares mostly in 7/4 [M; P]; master meters of 5, 7, 11, 13, or 8 grouped 2+3+3 [P]; DnB in 5/4 with each chord and bass note on a kick or snare [P].

### 1.8 How a hit's length and tail change the groove

- **Attack and duration move perceived timing** [M]: fast, short sounds have a narrow "beat bin" at the onset; slow, long ones a wide flat one, heard later and looser. A boomy kick on the grid feels late, a click kick tight.
- FL samplers "continue to play after note release unless you activate the Volume envelope" [M].
- Tutorials trim tails routinely: the drill snare's tail, and the open hat gated so the next note cuts it [P]; trap clap decay about 280 ms [P]; the kick trimmed with a short fade-out [P]; IDM stutters shortened because "the decay can build-up during the stuttered 32nd-note" passages [P].
- **Choke**: all hats in one group, so a closed or pedal hat kills the open one [P]. In FL, Cut / Cut by (2.7) [M].

### 1.9 Layering, and when not to

- **Kick under a break** [P], 86 BPM with the break at double speed: a trimmed kick one-shot at -4.8 dB; the break high-passed at 214 Hz, cut at 303 Hz, low-passed at 4.84 kHz, and sidechained from the kick at 4.85:1 for about 8 dB.
- **Snare plus clap** [P]: a weighty snare (160-200 Hz body) with a high-passed, slightly reverbed clap on beat 3.
- **One-shots on the break's timing** [P]: copy its kick and snare positions to new one-shots, add one hit in bar 4, steal ghost notes from the hat pattern onto a quiet clap, keep the break underneath EQed and flanged.
- **Not**: more than two kit pieces at once besides kick and pedal hat, or closed hats under crashes [P]; percussion while nothing else plays [P]. Cajon layers were low-cut at about 100 Hz [P]. Two sounds on one tick double the level and smear the attack if their onsets differ by a few ms: layer different bands or pick one [here].

## 2. Breaks and chopping

### 2.1 Classic breaks

| break | what it gives |
|---|---|
| Amen (The Winstons, 1969) | kick, snare, ride; bars 1-2 straight, 3-4 displaced; about 137 BPM; the jungle break |
| Think (Lyn Collins) | several break sections, one of tambourine only |
| Hot Pants (Bobby Byrd) | a prominent tambourine line; hardcore |
| Apache (Incredible Bongo Band) | percussion-heavy, delicate at 150+ |
| Funky Drummer (James Brown) | ghost-note funk |
| Cold Sweat (James Brown) | rolling hi-hats |
| Funky Mule (Ike Turner) | tough rolls; hardcore and tear-out |
| Tighten Up (James Brown) | crashing hats |
| Tramen (DJ Trace / Dom) | built from Amen, Tighten Up and The Flow; darker, techier DnB |

**The Amen as a grid** [M], 16th steps per bar, ride on every 8th:

```
bar 1-2  K  x.x.......xx....   0, 2, 10, 11
         S  ....x..x.x..x..x   4, 7, 9, 12, 15
bar 3    K  x.x.......x.....   0, 2, 10
         S  ....x..x.x....x.   4, 7, 9, 14
bar 4    K  ..xx......x.....   2, 3, 10
         S  .x..x..x.x....x.   1, 4, 7, 9, 14
         crash [M] or open hat [M] at 10
```

Hardly any hits sit on the grid, and the timbre does as much work as the placement [M]. The disruptive moves are the beat-4 snare held back in bars 3-4 (step 12 to 14) and the bar-4 pickup at step 1 [P].

**Repitching to tempo** [here]: semitones = `12 x log2(target / source)`.

| from | to 160 | 170 | 174 | 180 | 200 | 211 |
|---|---|---|---|---|---|---|
| Amen at 137 | +2.69 | +3.74 | +4.14 | +4.73 | +6.55 | +7.48 |
| VEC1 at 140 | +2.31 | +3.36 | +3.76 | +4.35 | +6.17 | +7.10 |

The sampler plays C4 at the original speed. Whole semitones give a slightly wrong tempo (E4 on a 140 break is 176.4 BPM, F4 186.9): fine for slices retriggered on the grid, not for a loop left running.

### 2.2 Slicing

- Cut at a zero crossing, "the last possible millisecond before a drum hit is audible"; with bleed, cut "wherever you want" and fade in from zero [P].
- FL's declick: "Transient (no bleeding)" keeps the attack with a 10 ms filtered fade-out, "Generic" uses 20 ms fades, "Smooth" 100 ms [M]. `chop.py` fades both ends.
- Breakcore producers either rearrange breaks or "merely distort and loop" them [M].

### 2.3 Retriggers, stutters and rolls

- Note repeat [P, (1)]: hats rolled at 1/16, sped to 1/64, back to 1/8, "all fluidly"; changing pitch while holding it gives a stutter.
- Trap rolls [P]: the last two 8th hats of a 2-bar clip become three 32nds each, middles quieter: `672, 684, 696` and `720, 732, 744`, middles at 70-80% [here].
- IDM [P]: more density gives "fast 32nd-note glitched textures". Shorten decays first and keep a "stable beat in the background".

### 2.4 Flams

- A grace note just before the main hit; drunk-drummer beats use many [P].
- No source gives a gap [here]: at 180, 2-5 ticks (7-17 ms) reads as one thick hit, 6-8 ticks (21-28 ms) as two. The grace note quieter and, on a sampled snare, higher.

### 2.5 Reverse and pitch

- A reversed section of the break with the shaker reversed in the same place [P]; "reverse this part and pan it the other way" [P].
- "Drum patterns as melody lines, pitching individual drum hits" [P].

### 2.6 Repitch versus stretch

- Repitch moves speed and pitch together: the sampler default and the jungle tradition [M]. Stretch keeps pitch, and its artefacts can be the sound: a break through Kontakt's stretch "to lock the tempo and make it a ringy, pitched percussion thing" [P, (1)].
- A 112 BPM break set to half its tempo so it plays at twice the speed, then +3 semitones [P].

### 2.7 Choke and monophonic playback

FL manual [M]:

- **Cut / Cut by**: a channel with Cut = n silences every channel with Cut by = n; the closed hat cuts the open.
- **Mono**: one note at a time; overlaps slide and release the old note.
- **Max polyphony**: the oldest notes "stop playing immediately"; the manual prefers Cut groups for single-voice playback.
- **Gate**: truncates long notes, only with a Volume envelope on.

### 2.8 Tails and ghosts inside a break

- A transient shaper's Sustain cleans the room out of vintage breaks [P]. Against that, the Amen's character is "the tails and the body of each hit" [P, (1)]. Keep the tail on the hit that carries identity, cut the ones that only mark time [here].
- The Amen's pickups (snares on steps 7, 9, 15) sit below the main snares on 4 and 12 [M].

## 3. Flavours

Skeletons marked [here] are illustrations. Positions in ticks from the bar start (0-383) or a 2-bar start (0-767).

### 3.1 Breakcore

- "very complex and intricate breakbeats" at high tempo, most often the Amen. Heavy: distorted hardcore, metal, industrial. Light: mash-up, happy hardcore, rave; Shitmat's "mashcore" [M].
- Venetian Snares: mostly 7/4 with many tuplets; early work dense within OctaMED's limits, later Renoise work orchestral [M; P]. Imitators went for "offbeat DnB rhythms punctuated with gabber kicks and snare roll fills"; Funk's own favours "a shifting, off-kilter pulse with lots of ornamentation, like you might find in Jazz" [P].
- Grid: 16ths, 32nds, tuplets, odd meters [P].
- Skeleton [here], 180 BPM, additions over an Amen at +4.73 st: bar 1, an Amen kick slice at -4 st on 132; bar 2, the snare restruck at 348, 356, 364, 372, each +2 st; bar 3, beat 3 reversed (192-288); bar 4 silent from 336, then an impact and a gabber-style kick on the downbeat.
- Mistakes [P]: glitch plugins ("all produce the same sound in the end"), never chopping your own breaks, odd meters that sound "wonky" rather than intended.

### 3.2 Jungle and drum & bass

- Tempo 160-180: about 130 in 1990-91, 155-165 by 1993, 170-180 since 1996 [M]; 174 most common [P]; early jungle 160 [P]. Halftime at DnB tempo is "drumstep" [M].
- Two-step [P]: kick 0 and 240 ("the 'and' of beat 3"), snare 96 and 288, ghosts and hats in the rest. Jungle keeps the break audible; DnB moved to individual kick and snare hits [P].
- Amen jungle [P]: a chopped Amen over an 808 or sub, "don't be shy with syncopation", the snare varied in rhythm and timbre, 16th hats, open hats between fills. A sampled 808 played on a keyboard became the sub [P].
- Neurofunk: "less focus on live drums", a "higher bar for precision" in transients [P].
- The shaker sidechained to the drum group [P].
- Mistakes [P]: the break untouched as the whole part; over-chopping; kick and snare not landing with the bass.

### 3.3 Drill 'n' bass and IDM

- "frenzied, irregular beats", "jungle by non-junglists for non-junglists", "double-time drum 'n' bass with impossible-to-dance-to rhythms": Luke Vibert, Aphex Twin, Squarepusher, µ-Ziq [M].
- Random steps, density, pitch, flam and pan per step over a stable backbeat; shuffle per voice; 32nd bursts with short decays [P]. No fixed tempo [P].
- Mistake: randomness with no anchor [P].

### 3.4 Footwork and juke

- 150-165 BPM, 160 typical. Juke is four-to-the-floor ghetto house; footwork is "more rhythmically abstract", with beat skips and full/half-time switches [M].
- "beat-skipping kick drums, pounding rapidly (and at times very sparsely)", crackling snares and claps, 808 sounds, pitched vocal chops, heavy sub [M].
- Kick as bass [P]: an 808 at maximum decay played chromatically, the click filtered at about 119 Hz (0.22 ms attack, 9.86 ms decay).
- Skeleton [here], 160 BPM: kick on the 8th-triplet lattice 0, 64, 128, then 216 and 240, nothing on beat 4; claps 96 and 288; 16th-triplet hats in beat 3 only (192-272 every 16); vocal chops at 320 and 352. Next 2 bars half time (clap at 192 only).

### 3.5 Gabber, hardcore, speedcore, frenchcore

- Tempo: gabber 140-190 [M]; hardcore 160-200+ [M]; frenchcore about 200 (180-220+) [M]; speedcore 300-600, splittercore 600-1000, extratone above 1000, where kicks fuse into a tone [M].
- Distorted, saw-like kicks [M], overdriven toward square waves in speedcore [M]; frenchcore adds a distorted offbeat bass and pitched kicks [M].
- Skeleton [here], 190 BPM: kick on every beat, each cut by the next (the tail is the bass); offbeat bass at 48, 144, 240, 336; open hats on the offbeats; a 16th kick roll through the last beat before a drop. Overlapping kick tails are the mistake.

### 3.6 Hardbass

- 150-175 BPM, "donk" basslines, heavy kicks, chants; from pumping house, bouncy techno and hardstyle, and UK hard house's "offbeat bass stabs" [M].
- Skeleton [here]: kick on every beat, donk on the offbeat 8ths, clap 96 and 288, hats on the offbeat 16ths.

### 3.7 Dubstep and halftime

- 132-142 BPM, mostly 140; snare or clap on beat 3 [M; P].
- Digital Mystikz style [P]: a 32-division grid; kick simple with "some offbeats towards the end", the last quieter; snare plus clap at 192; hats and shaker syncopated, pausing "on the 3rd beat"; a delay-fed acoustic snare once per 2 bars.

### 3.8 Trap

- 130-200 BPM with half-time drums [P], typically 140 [M]; Detroit and Flint at 210+ in double time [P].
- Closed 8th hats, the last two of a 2-bar clip as 32nd rolls (2.3) [P].
- The 808 "follows the kick, but doesn't land on it at the same time" [P].

### 3.9 Hyperpop and digicore

- "excessive compression and distortion", "stadium-sized trap beats processed and distorted to near-destruction", resampling for a "choppy 'stop-and-start' feel" [M; P]. Digicore was called glitchcore early on [M].
- NI's 2-bar pattern at 205 BPM [P]: snare 192, 576; kick 0, 288, 672, 720; hats every 8th plus 312 and 504; kick and snare fuzzed, hats clean on their own channel (-2.9 / +1.2 dB); at bar 16 the last two beats cut and a snare fill alone.

### 3.10 Glitch

- 80-130 BPM, "chopped-up samples, stuttering digital effects... glitch sounds deployed in place of or alongside conventional percussion" [M]. Its roots are skipping CDs (Oval, Yasunao Tone) [M]: a stutter that jumps back, not a clean 32nd roll.

### 3.11 Others

- Jersey club [P]: about 170 BPM; kick 0, 96, then a tresillo at 192, 264, 336.
- 5/4 DnB [P]: kick on 1 of each bar, then "3 and" in bar 1 and "3 and" plus "4 and" in bar 2; 8th hats with random velocity of 15-20.