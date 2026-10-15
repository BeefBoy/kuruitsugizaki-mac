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

**Swing** is the MPC's [M 1]: every second 16th of an 8th pair is delayed, and the percentage is the first 16th's share of the pair, so the late 16th lands `48 x swing` ticks after its 8th:

| swing | 50% | 54% | 57% | 58% | 62% | 66% | 70% | 74% |
|---|---|---|---|---|---|---|---|---|
| late 16th at | 24 | 26 | 27 | 28 | 30 | 32 (8th triplet) | 34 | 36 |

8th-note swing uses the 96-tick pair: 57% puts the offbeat 8th at 55 instead of 48.

## 1. General craft

### 1.1 Grid, micro-timing and humanisation

Studies:

- **Quantized grooves as well as expert timing.** Fully quantized patterns got the highest groove ratings and large deviations the lowest (Frühauf et al.; Davies et al., 2013) [M 8]. Two expert bass-and-drum performances scaled from 0% to over 100% of their microtiming: quantized and original rated "equally high", exaggerated timing lost groove and raised irritation (Senn et al. 2016) [M 7].
- Listeners do not reliably detect deviations up to 30 ms (Butterfield) [M 8], about 9 ticks at 180 BPM.
- Against that, expert listeners moved most to "tight but non-zero" microtiming and little to quantized music, while still rating it high (Kilchenmann and Senn 2015) [M 7, 8].
- **Correlated, not random.** Human timing errors drift (1/f-like). Listeners preferred correlated humanising over white-noise per-beat offsets, which is what DAW humanise does (Hennig et al. 2011) [M 9].
- **Size.** Porcaro's one-hand 16th hats on "I Keep Forgettin'": mean 157 ms, SD 8.7 ms (5.5% of a 16th, about 1.3 ticks), consecutive intervals anticorrelated (r = -0.48). A drummer on a metronome at 180 BPM: SD 15.6 ms [M 10].
- **Laid-back snare**: 17.4 ms late on average at 96 BPM [M 11], 5 ticks at 180.

Practitioners, who disagree:

- Linn [P 1]: random timing and late snares never did "much good"; with swing and dynamics right, notes work best "at exactly the perfect time slots".
- J Dilla lesson [P 21, (1)]: a constant offset per voice held every bar, e.g. kick on the click, snare 30 ms late, hat 30 ms early.
- Drunk-drummer grooves [P 16]: positions from quintuplet, sextuplet and septuplet grids instead of nudging. Two hats on quintuplets 1 and 4 split the beat 3:2, on septuplets 4:3. Flams add drag.
- Splice [P 15]: about ±1 tick of random humanise at 96 PPQ, then re-quantize kicks and crashes that land together.
- Chopped breaks: kick and snare on the grid [P 22], or keep the break's own positions and "resist the urge to quantize everything" [P 20].

### 1.2 Swing

- 50% is straight, 66% the triplet. At 90 BPM 62% "will feel looser" than 66%; on straight 16ths 54% loosens the feel "without it sounding like swing" [P 1].
- Per voice: kick and snare "MPC 3000 8ths 57", hats "16th 74" [P 17]; hats at 15%, 57% and 35% [P 25].
- "Shook Ones Pt. II": kicks at 1.2.4 and 1.4.4 sit "halfway between that grid line and the next" while the 8ths stay straight [M 26, (1)].
- Trap is "sequenced straight, without swing" [P 27].

### 1.3 Velocity, accents and ghost notes

- **Accents repeat.** Porcaro's hats run "high-low-medium-low-very high-low-medium-low", the very high on the snare; one 2-bar phrase's amplitudes correlate 0.88 with the next [M 10]. Equal velocities are "a bad drum machine"; vary note-repeat pressure "from light to medium continuously and somewhat randomly" [P 1].
- **Hierarchy** [P 15]: hat loudest on 1, then 3, then 2 and 4, offbeats quietest. Kick and snare vary only slightly. Fills alternate like two hands. Do not copy one bar's velocities to every bar.
- **Amen** [M 6]: the first kick of the double before beat 4 is "slightly quieter than the second"; the bar's last snare is below the main ones but "not quite down the level of a ghost note"; the ride is "full strength eighth-notes".
- **Ghost notes** [M 14]: "very softly between the 'main' notes", usually snare, for "a subtle 16th-note feel around a strong back beat" (Amen, "Cold Sweat", "Rosanna").
- **Drill velocities** [P 28]: main hits 100, second hat of each group 87, the bar-1 pickup hat 52, last kick 96, percussion 91.
- **Call and response** [P 29]: in a fill, low then high; the snare answers the kick.
- In the harness velocity is a per-note field (default 100). How much it changes a sampler's level depends on the channel's velocity tracking: check the render [here].

### 1.4 Syncopation and density

- Medium syncopation drew the most wish to move, an inverted U [M 12]. Groove tracked event density, beat salience and syncopation, not microtiming size [M 8].
- A kick or snare under most bass notes and chord changes [P 22, 29].

### 1.5 Phrase length and where variation goes

- **Amen** [M 5, 6]: bars 1-2 the same; bar 3 holds the beat-4 snare back half a beat and drops the kick double; bar 4 leaves beat 1 empty, moves the double to the start and puts a crash between beats 3 and 4, "a very unusual way of marking the end of the phrase".
- Porcaro: the 2-bar phrase is the unit, drift above it, alternation below it [M 10].
- A 2-bar cell looped to 4 or 16 bars with the last bar or last two beats replaced [P 28, 30].
- RP Boo: "I got tracks that are on the three". Moving where "one" feels is a variation as strong as a fill [P 31].

### 1.6 Fills, hard stops and silence

- A fill marks a section end. The house fill is 16th snares rising in velocity, swung by delaying every second one [P 32].
- Dropout fills: only the snare plays under the fill [P 32], or the last two beats of 16 bars go silent and a snare fill plays alone [P 30].

### 1.7 Triplets, tresillo and polyrhythmic overlays

- **Tresillo 3+3+2** [M 19; P 18, 37]: 16th steps 0, 3, 6 per half bar or across a bar. Drill hats run "two spaces, two spaces and one space repeated", from grime [P 18].
- Trap hats use "double-time, triple-time, and similarly divided" subdivisions [M 13].
- **Odd meters over 4/4**: Venetian Snares mostly in 7/4 [M 23; P 24]; master meters of 5, 7, 11, 13, or 8 grouped 2+3+3 [P 12]; DnB in 5/4 with each chord and bass note on a kick or snare [P 29].

### 1.8 How a hit's length and tail change the groove

- **Attack and duration move perceived timing** [M 33]: fast, short sounds have a narrow "beat bin" at the onset; slow, long ones a wide flat one, heard later and looser. A boomy kick on the grid feels late, a click kick tight.
- FL samplers "continue to play after note release unless you activate the Volume envelope" [M 34].
- Tutorials trim tails routinely: the drill snare's tail, and the open hat gated so the next note cuts it [P 18]; trap clap decay about 280 ms [P 27]; the kick trimmed with a short fade-out [P 38]; IDM stutters shortened because "the decay can build-up during the stuttered 32nd-note" passages [P 25].
- **Choke**: all hats in one group, so a closed or pedal hat kills the open one [P 35]. In FL, Cut / Cut by (2.7) [M 34].

### 1.9 Layering, and when not to

- **Kick under a break** [P 38], 86 BPM with the break at double speed: a trimmed kick one-shot at -4.8 dB; the break high-passed at 214 Hz, cut at 303 Hz, low-passed at 4.84 kHz, and sidechained from the kick at 4.85:1 for about 8 dB.
- **Snare plus clap** [P 36]: a weighty snare (160-200 Hz body) with a high-passed, slightly reverbed clap on beat 3.
- **One-shots on the break's timing** [P 20]: copy its kick and snare positions to new one-shots, add one hit in bar 4, steal ghost notes from the hat pattern onto a quiet clap, keep the break underneath EQed and flanged.
- **Not**: more than two kit pieces at once besides kick and pedal hat, or closed hats under crashes [P 15]; percussion while nothing else plays [P 36]. Cajon layers were low-cut at about 100 Hz [P 36]. Two sounds on one tick double the level and smear the attack if their onsets differ by a few ms: layer different bands or pick one [here].

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

Sources [M 6, 39, 40, 41, 42].

**The Amen as a grid** [M 5, 6], 16th steps per bar, ride on every 8th:

```
bar 1-2  K  x.x.......xx....   0, 2, 10, 11
         S  ....x..x.x..x..x   4, 7, 9, 12, 15
bar 3    K  x.x.......x.....   0, 2, 10
         S  ....x..x.x....x.   4, 7, 9, 14
bar 4    K  ..xx......x.....   2, 3, 10
         S  .x..x..x.x....x.   1, 4, 7, 9, 14
         crash [M 6] or open hat [M 5] at 10
```

Hardly any hits sit on the grid, and the timbre does as much work as the placement [M 5]. The disruptive moves are the beat-4 snare held back in bars 3-4 (step 12 to 14) and the bar-4 pickup at step 1 [P 5].

**Repitching to tempo** [here]: semitones = `12 x log2(target / source)`.

| from | to 160 | 170 | 174 | 180 | 200 | 211 |
|---|---|---|---|---|---|---|
| Amen at 137 | +2.69 | +3.74 | +4.14 | +4.73 | +6.55 | +7.48 |
| VEC1 at 140 | +2.31 | +3.36 | +3.76 | +4.35 | +6.17 | +7.10 |

The sampler plays C4 at the original speed. Whole semitones give a slightly wrong tempo (E4 on a 140 break is 176.4 BPM, F4 186.9): fine for slices retriggered on the grid, not for a loop left running.

### 2.2 Slicing

- Cut at a zero crossing, "the last possible millisecond before a drum hit is audible"; with bleed, cut "wherever you want" and fade in from zero [P 12].
- FL's declick: "Transient (no bleeding)" keeps the attack with a 10 ms filtered fade-out, "Generic" uses 20 ms fades, "Smooth" 100 ms [M 34]. `chop.py` fades both ends.
- Breakcore producers either rearrange breaks or "merely distort and loop" them [M 43].

### 2.3 Retriggers, stutters and rolls

- Note repeat [P 12, (1)]: hats rolled at 1/16, sped to 1/64, back to 1/8, "all fluidly"; changing pitch while holding it gives a stutter.
- Trap rolls [P 27]: the last two 8th hats of a 2-bar clip become three 32nds each, middles quieter: `672, 684, 696` and `720, 732, 744`, middles at 70-80% [here].
- IDM [P 25]: more density gives "fast 32nd-note glitched textures". Shorten decays first and keep a "stable beat in the background".

### 2.4 Flams

- A grace note just before the main hit; drunk-drummer beats use many [P 16, 37].
- No source gives a gap [here]: at 180, 2-5 ticks (7-17 ms) reads as one thick hit, 6-8 ticks (21-28 ms) as two. The grace note quieter and, on a sampled snare, higher.

### 2.5 Reverse and pitch

- A reversed section of the break with the shaker reversed in the same place [P 38]; "reverse this part and pan it the other way" [P 24].
- "Drum patterns as melody lines, pitching individual drum hits" [P 69].

### 2.6 Repitch versus stretch

- Repitch moves speed and pitch together: the sampler default and the jungle tradition [M 39]. Stretch keeps pitch, and its artefacts can be the sound: a break through Kontakt's stretch "to lock the tempo and make it a ringy, pitched percussion thing" [P 69, (1)].
- A 112 BPM break set to half its tempo so it plays at twice the speed, then +3 semitones [P 38].

### 2.7 Choke and monophonic playback

FL manual [M 34]:

- **Cut / Cut by**: a channel with Cut = n silences every channel with Cut by = n; the closed hat cuts the open.
- **Mono**: one note at a time; overlaps slide and release the old note.
- **Max polyphony**: the oldest notes "stop playing immediately"; the manual prefers Cut groups for single-voice playback.
- **Gate**: truncates long notes, only with a Volume envelope on.

### 2.8 Tails and ghosts inside a break

- A transient shaper's Sustain cleans the room out of vintage breaks [P 63]. Against that, the Amen's character is "the tails and the body of each hit" [P 5, (1)]. Keep the tail on the hit that carries identity, cut the ones that only mark time [here].
- The Amen's pickups (snares on steps 7, 9, 15) sit below the main snares on 4 and 12 [M 5, 6].

## 3. Flavours

Skeletons marked [here] are illustrations. Positions in ticks from the bar start (0-383) or a 2-bar start (0-767).

### 3.1 Breakcore

- "very complex and intricate breakbeats" at high tempo, most often the Amen. Heavy: distorted hardcore, metal, industrial. Light: mash-up, happy hardcore, rave; Shitmat's "mashcore" [M 43].
- Venetian Snares: mostly 7/4 with many tuplets; early work dense within OctaMED's limits, later Renoise work orchestral [M 23; P 24]. Imitators went for "offbeat DnB rhythms punctuated with gabber kicks and snare roll fills"; Funk's own favours "a shifting, off-kilter pulse with lots of ornamentation, like you might find in Jazz" [P 24].
- Grid: 16ths, 32nds, tuplets, odd meters [P 12, 24].
- Skeleton [here], 180 BPM, additions over an Amen at +4.73 st: bar 1, an Amen kick slice at -4 st on 132; bar 2, the snare restruck at 348, 356, 364, 372, each +2 st; bar 3, beat 3 reversed (192-288); bar 4 silent from 336, then an impact and a gabber-style kick on the downbeat.
- Mistakes [P 24]: glitch plugins ("all produce the same sound in the end"), never chopping your own breaks, odd meters that sound "wonky" rather than intended.

### 3.2 Jungle and drum & bass

- Tempo 160-180: about 130 in 1990-91, 155-165 by 1993, 170-180 since 1996 [M 52]; 174 most common [P 58, 22]; early jungle 160 [P 59]. Halftime at DnB tempo is "drumstep" [M 52].
- Two-step [P 58, 59]: kick 0 and 240 ("the 'and' of beat 3"), snare 96 and 288, ghosts and hats in the rest. Jungle keeps the break audible; DnB moved to individual kick and snare hits [P 59].
- Amen jungle [P 37]: a chopped Amen over an 808 or sub, "don't be shy with syncopation", the snare varied in rhythm and timbre, 16th hats, open hats between fills. A sampled 808 played on a keyboard became the sub [P 68].
- Neurofunk: "less focus on live drums", a "higher bar for precision" in transients [P 59].
- The shaker sidechained to the drum group [P 38].
- Mistakes [P 22]: the break untouched as the whole part; over-chopping; kick and snare not landing with the bass.

### 3.3 Drill 'n' bass and IDM

- "frenzied, irregular beats", "jungle by non-junglists for non-junglists", "double-time drum 'n' bass with impossible-to-dance-to rhythms": Luke Vibert, Aphex Twin, Squarepusher, µ-Ziq [M 44].
- Random steps, density, pitch, flam and pan per step over a stable backbeat; shuffle per voice; 32nd bursts with short decays [P 25]. No fixed tempo [P 75].
- Mistake: randomness with no anchor [P 25].

### 3.4 Footwork and juke

- 150-165 BPM, 160 typical. Juke is four-to-the-floor ghetto house; footwork is "more rhythmically abstract", with beat skips and full/half-time switches [M 45].
- "beat-skipping kick drums, pounding rapidly (and at times very sparsely)", crackling snares and claps, 808 sounds, pitched vocal chops, heavy sub [M 45].
- Kick as bass [P 67]: an 808 at maximum decay played chromatically, the click filtered at about 119 Hz (0.22 ms attack, 9.86 ms decay).
- Skeleton [here], 160 BPM: kick on the 8th-triplet lattice 0, 64, 128, then 216 and 240, nothing on beat 4; claps 96 and 288; 16th-triplet hats in beat 3 only (192-272 every 16); vocal chops at 320 and 352. Next 2 bars half time (clap at 192 only).

### 3.5 Gabber, hardcore, speedcore, frenchcore

- Tempo: gabber 140-190 [M 46]; hardcore 160-200+ [M 49]; frenchcore about 200 (180-220+) [M 50]; speedcore 300-600, splittercore 600-1000, extratone above 1000, where kicks fuse into a tone [M 47].
- Distorted, saw-like kicks [M 46, 49], overdriven toward square waves in speedcore [M 47]; frenchcore adds a distorted offbeat bass and pitched kicks [M 50].
- Skeleton [here], 190 BPM: kick on every beat, each cut by the next (the tail is the bass); offbeat bass at 48, 144, 240, 336; open hats on the offbeats; a 16th kick roll through the last beat before a drop. Overlapping kick tails are the mistake.

### 3.6 Hardbass

- 150-175 BPM, "donk" basslines, heavy kicks, chants; from pumping house, bouncy techno and hardstyle, and UK hard house's "offbeat bass stabs" [M 48, 51].
- Skeleton [here]: kick on every beat, donk on the offbeat 8ths, clap 96 and 288, hats on the offbeat 16ths.

### 3.7 Dubstep and halftime

- 132-142 BPM, mostly 140; snare or clap on beat 3 [M 53; P 59].
- Digital Mystikz style [P 36]: a 32-division grid; kick simple with "some offbeats towards the end", the last quieter; snare plus clap at 192; hats and shaker syncopated, pausing "on the 3rd beat"; a delay-fed acoustic snare once per 2 bars.

### 3.8 Trap

- 130-200 BPM with half-time drums [P 27], typically 140 [M 13]; Detroit and Flint at 210+ in double time [P 60].
- Closed 8th hats, the last two of a 2-bar clip as 32nd rolls (2.3) [P 27].
- The 808 "follows the kick, but doesn't land on it at the same time" [P 61].

### 3.9 Hyperpop and digicore

- "excessive compression and distortion", "stadium-sized trap beats processed and distorted to near-destruction", resampling for a "choppy 'stop-and-start' feel" [M 54; P 62]. Digicore was called glitchcore early on [M 55].
- NI's 2-bar pattern at 205 BPM [P 30]: snare 192, 576; kick 0, 288, 672, 720; hats every 8th plus 312 and 504; kick and snare fuzzed, hats clean on their own channel (-2.9 / +1.2 dB); at bar 16 the last two beats cut and a snare fill alone.

### 3.10 Glitch

- 80-130 BPM, "chopped-up samples, stuttering digital effects... glitch sounds deployed in place of or alongside conventional percussion" [M 56]. Its roots are skipping CDs (Oval, Yasunao Tone) [M 56]: a stutter that jumps back, not a clean 32nd roll.

### 3.11 Others

- Jersey club [P 37]: about 170 BPM; kick 0, 96, then a tresillo at 192, 264, 336.
- 5/4 DnB [P 29]: kick on 1 of each bar, then "3 and" in bar 1 and "3 and" plus "4 and" in bar 2; 8th hats with random velocity of 15-20.

## Sources

"via archive" is web.archive.org.

1. Attack Magazine, "Roger Linn On Swing, Groove & The Magic Of The MPC's Timing". https://www.attackmagazine.com/features/interview/roger-linn-swing-groove-magic-mpc-timing/
5. Ethan Hein, "Building the Amen break" (2023), with comments. https://www.ethanhein.com/wp/2023/building-the-amen-break/
6. MusicRadar, "How to program an Amen-style break" (2016). https://www.musicradar.com/tuition/tech/how-to-program-an-amen-style-break-637374
7. Senn et al., "The Effect of Expert Performance Microtiming on Listeners' Experience of Groove", Frontiers in Psychology 2016, results. https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2016.01487/full
8. The same article, introduction: its summary of Butterfield, Madison, Frühauf, Davies, Kilchenmann and Senn. Frühauf itself returned 403.
9. Hennig et al., "The Nature and Perception of Fluctuations in Human Musical Rhythms", PLoS ONE 2011. https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0026457
10. Räsänen et al., "Fluctuations of Hi-Hat Timing and Dynamics in a Virtuoso Drum Track", PLoS ONE 2015. https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0127902
11. Carter and von Appen, "Measuring the Myth", citing Danielsen et al. 2015. https://tnp.mtsnys.org/vol49-50/carter_von_appen
12. Gearspace, "Venetian Snares/Breakcore Production methods" (via archive). https://web.archive.org/web/2026/https://gearspace.com/board/electronic-music-instruments-and-electronic-music-production/1125569-venetian-snares-breakcore-production-methods.html
13. Wikipedia, "Trap music". https://en.wikipedia.org/wiki/Trap_music
14. Wikipedia, "Ghost note". https://en.wikipedia.org/wiki/Ghost_note
15. Splice, "How to humanize your MIDI drums". https://splice.com/blog/humanize-your-drums/
16. Attack Magazine, "Drunk Drummer-Style Grooves". https://www.attackmagazine.com/technique/beat-dissected/drunk-drummer-style-grooves/
17. Attack Magazine, "90s Boom Bap Hip Hop". https://www.attackmagazine.com/technique/beat-dissected/90s-boom-bap-hip-hop/
18. Attack Magazine, "UK Drill". https://www.attackmagazine.com/technique/beat-dissected/uk-drill/
19. Wikipedia, "UK drill". https://en.wikipedia.org/wiki/UK_drill
20. Attack Magazine, "Skee Mask". https://www.attackmagazine.com/technique/beat-dissected/skee-mask/
21. Drum.town, "J Dilla Time-Feel". https://drum.town/lessons/hiphop-j-dilla/
22. EDMProd, "How to make Jungle music". https://www.edmprod.com/how-to-make-jungle-music/
23. Wikipedia, "Venetian Snares". https://en.wikipedia.org/wiki/Venetian_Snares
24. Reddit r/breakcore, "how to venetian snares" (via archive). https://web.archive.org/web/2024/https://www.reddit.com/r/breakcore/comments/108k6mj/how_to_venetian_snares/
25. Attack Magazine, "Stuttered IDM Hi-Hats With Audiomodern Playbeat 3". https://www.attackmagazine.com/technique/tutorials/stuttered-idm-hi-hats-with-audiomodern-playbeat-3/
26. Native Instruments, "Hip hop drums 101". https://blog.native-instruments.com/hip-hop-drums-101/
27. Native Instruments, "How to make a trap beat". https://blog.native-instruments.com/how-to-make-a-trap-beat/
28. Native Instruments, "How to make a drill beat". https://blog.native-instruments.com/drill/
29. Attack Magazine, "Programming Drum 'n' Bass In 5/4". https://www.attackmagazine.com/technique/beat-dissected/programming-drum-n-bass-in-5-4-time-signature/
30. Native Instruments, "Hyperpop production 101". https://blog.native-instruments.com/hyperpop/
31. Native Instruments, "RP Boo: Production, Chicago, and finishing tracks". https://blog.native-instruments.com/rp-boo-production-chicago-and-finishing-tracks/
32. Native Instruments, "Must-know drum fills". https://blog.native-instruments.com/drum-fills/
33. Danielsen et al., "Where is the beat in that note?", JEP:HPP 2019, abstract. https://pubmed.ncbi.nlm.nih.gov/30802130/
34. Image-Line, FL Studio manual, Channel Settings Misc and Channel Sampler. https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/chansettings_misc.htm https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/chansettings_sampler.htm
35. Attack Magazine, "Live Hi-Hats". https://www.attackmagazine.com/technique/beat-dissected/live-hi-hats/
36. Attack Magazine, "Drum Programming: Mystik Dubstep". https://www.attackmagazine.com/technique/beat-dissected/mystik-dubstep/
37. Splice, "How to make drum patterns for different genres". https://splice.com/blog/drum-patterns-different-genres/
38. Attack Magazine, "Slicing Breakbeats Like Nia Archives". https://www.attackmagazine.com/technique/beat-dissected/slicing-breakbeats-like-nia-archives/
39. Wikipedia, "Amen break". https://en.wikipedia.org/wiki/Amen_break
40. WhoSampled, "Top 10 Iconic Drum & Bass / Jungle Breakbeats" (via archive). https://web.archive.org/web/2023/https://www.whosampled.com/news/2015/03/05/top-10-iconic-drum-bass-jungle-breakbeats/
41. Wikipedia, "Funky Drummer". https://en.wikipedia.org/wiki/Funky_Drummer
42. Wikipedia, "Apache (instrumental)". https://en.wikipedia.org/wiki/Apache_(instrumental)
43. Wikipedia, "Breakcore". https://en.wikipedia.org/wiki/Breakcore
44. Wikipedia, "Drill 'n' bass". https://en.wikipedia.org/wiki/Drill_%27n%27_bass
45. Wikipedia, "Footwork (genre)". https://en.wikipedia.org/wiki/Footwork_(genre)
46. Wikipedia, "Gabber". https://en.wikipedia.org/wiki/Gabber
47. Wikipedia, "Speedcore" (flagged "expert needed" on tempo). https://en.wikipedia.org/wiki/Speedcore
48. Wikipedia, "Hardbass". https://en.wikipedia.org/wiki/Hardbass
49. Wikipedia, "Hardcore (electronic dance music genre)". https://en.wikipedia.org/wiki/Hardcore_(electronic_dance_music_genre)
50. Wikipedia, "Frenchcore". https://en.wikipedia.org/wiki/Frenchcore
51. Wikipedia, "UK hard house". https://en.wikipedia.org/wiki/UK_hard_house
52. Wikipedia, "Drum and bass". https://en.wikipedia.org/wiki/Drum_and_bass
53. Wikipedia, "Dubstep". https://en.wikipedia.org/wiki/Dubstep
54. Wikipedia, "Hyperpop". https://en.wikipedia.org/wiki/Hyperpop
55. Wikipedia, "Digicore". https://en.wikipedia.org/wiki/Digicore
56. Wikipedia, "Glitch (music)". https://en.wikipedia.org/wiki/Glitch_(music)
58. EDMProd, "What is Drum and Bass?". https://www.edmprod.com/what-is-drum-and-bass/
59. Splice, "What is drum and bass music?". https://splice.com/blog/what-is-drum-and-bass-music/
60. Splice, "What is trap music?". https://splice.com/blog/what-is-trap-music/
61. Splice, "How to make a trap beat in FL Studio". https://splice.com/blog/how-to-make-trap-beat-fl-studio/
62. EDMProd, "Hyperpop explained". https://www.edmprod.com/hyperpop/
63. EDMProd, "Transient shaper". https://www.edmprod.com/transient-shaper/
67. MusicRadar, "How to make a Juke-style pitched 808 kick pattern". https://www.musicradar.com/tuition/tech/how-to-make-a-juke-style-pitched-808-kick-pattern-554083
68. Attack Magazine, "Creating 808-Style Basslines For Jungle, Trap And Footwork". https://www.attackmagazine.com/technique/tutorials/creating-808-style-basslines-for-jungle-trap-and-footwork/
69. Native Instruments, "Jungle revivalist Sully sketches out haunting atmospherics". https://blog.native-instruments.com/sketches-sully/
75. EDMProd, "How to make IDM beats". https://www.edmprod.com/how-to-make-idm-beats/
