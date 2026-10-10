# Effects: parameters as FL exposes them

What each effect's automatable parameters are, read live from FL with `fxdump_fl.py` (run through `fl_exec`). An automation clip targets one of these by `{"mixer": insert, "slot": slot, "param": index}`; its points are the normalised value 0..1 shown here. The value and display columns are sample points of each knob's scale, read from whatever project the effect sat in. They are not settings to reuse, and an effect's name does not say what it was used for.

How to read one live: `plugins.getParamCount(t, s)`, `getParamName(i, t, s)`, `getParamValue(i, t, s)`, `getParamValueString(i, t, s)`. A wrapped VST reports 4240 parameters whatever it has; the dump stops after 16 empty names. A display read in the same `fl_exec` as a set returns the previous value (NOTES), so mapping a value to its display takes one call per value, each reading the previous set.

## Measured mappings

- **Fruity Parametric EQ 2, band freq:** f = 20 Hz x 1000^v (v 0.1667 = 63 Hz, 0.5 = 632 Hz, 0.7222 = 2936 Hz, 0.8333 = 6324 Hz, read from FL's display).
- **Fruity Parametric EQ 2, band level:** dB = 36 x (v - 0.5): 0.5 = 0 dB, 0 = -18 dB, 1 = +18 dB.
- **Gross Beat, Time slot and Volume slot:** FL quantises to round(v x 35) / 35; index 0 is Empty. Read from saved clip values: time 10 Basic 10, 11 Basic 11, 17 Complex 6; volume 18 1/4 Dynamic, 27 Tremelo Fst. Index k is slot T(k+1) / V(k+1) in §Gross Beat factory slots. A slot number names a slot in the copied instance's bank, not a fixed effect.
- **Automation clip range:** FL stores every effect-knob clip with range 0..12800 in event 219. The writer does the same for every target but tempo.

## Fruity Parametric EQ 2 (36)

| index | name |
|---|---|
| 0-6 | Band 1-7 level |
| 7-13 | Band 1-7 freq |
| 14-20 | Band 1-7 width (0.3878 = 39%, 0.6122 = 61%) |
| 21-27 | Band 1-7 type (0.7143 Low shelf, 0.8571 Peaking, 1.0 High shelf) |
| 28-34 | Band 1-7 order (0.5 = 2, 0.1667 = Steep 6) |
| 35 | Main level (0.5 = 0.0 dB) |

## Gross Beat (9)

| index | name | sample |
|---|---|---|
| 0 | Time slot | 0.2857 Basic 10 |
| 1 | Volume slot | 0.0 Empty |
| 2 | Time mix | 1.0 100% |
| 3 | Volume mix | 1.0 100% |
| 4 | Volume smoothing attack | 0.1765 2.00 ms |
| 5 | Volume smoothing release | 0.1674 3.66 ms |
| 6 | Volume envelope tension | 0.5 0% |
| 7 | Hold delay (bar repeat) | 0.0 |
| 8 | Time offset (scratching) | 1.0 -000:00:000 |

Mute / solo is not a parameter: target `0x70431f00` (insert 1, slot 3, low word 0x1f00), values 0 / 1.

## Gross Beat factory slots

Decoded from two saved instances: the same 72 in both, in saved-state order, assumed to be the UI order.

- **Time:** T1 Empty; T2-T12 Basic 1-11; T13-T24 Complex 1-12; T25-T36 Chaos 1-12.
- **Volume:** V1 Empty; V2-V8 2 Beat, 1 Beat, 1/2 Bt, 1/3 Bt, 1/4 Bt, 1/6 Bt, 1/8 Bt Gate; V9-V12 Trance Gt 1-4 (V9's points: 32nd on/off with some longer gaps); V13-V14 Saw Gate 1-2; V15-V17 1st Step, 1st Stp Fade, 2 Step Gate; V18 Off Beat; V19-V22 1/4 Dynamic, 1/4 Swing, 1/4 Gate Out, 1/4 Gate In; V23-V24 Spd Up Gate, Slw Dn Gate; V25-V26 End Fade, End Gate; V27-V28 Tremelo Slw, Tremelo Fst; V29-V32 Sidechain, Drum Loop, Copter, AM; V33-V36 Fade In, Fade Out, Fade Out In, Mute.

The state itself is in FLP.md, Gross Beat state.

## Fruity Limiter (18)

| index | name | sample |
|---|---|---|
| 0 | Gain | 0.5 0.0 dB |
| 1 | Soft saturation threshold | 1.0 0.0 dB |
| 2 | Limiter ceiling | 0.5 0.0 dB |
| 3 | Limiter attack time | 0.1115 2.00 ms |
| 4 | Limiter attack curve | 0.2857 3 |
| 5 | Limiter release time | 0.5 85.53 ms |
| 6 | Limiter release curve | 0.2857 3 |
| 7 | Limiter peak window | 0.2882 10.00 ms |
| 8 | Comp threshold | 1.0 0.0 dB |
| 9 | Comp ratio | 0.5 1:1.0 |
| 10 | Comp knee | 0.5 0% |
| 11 | Comp attack time | 0.0 0.00 ms |
| 12 | Comp release time | 0.6666 248.22 ms |
| 13 | Comp curve | 0.0 |
| 14 | Comp RMS window | 0.065 1.00 ms |
| 15 | Noise gain | 0.0 -INF dB |
| 16 | Noise threshold | 0.288 -18.0 dB |
| 17 | Noise release time | 0.9435 1406.45 ms |

## Fruity Reeverb 2 (15)

| index | name | sample |
|---|---|---|
| 0 | Low cut | 0.0272 100 Hz |
| 1 | High cut | 0.2546 6.0 kHz |
| 2 | Predelay | 0.0 0 ms |
| 3 | Room size | 0.1616 17 |
| 4 | Diffusion | 1.0 100 |
| 5 | Decay time | 0.0201 0.5 s |
| 6 | High damping | 0.1157 3.0 kHz |
| 7 | Bass multiplier | 0.25 90% |
| 8 | Crossover | 0.1544 330 Hz |
| 9 | Stereo separation | 0.5 Original |
| 10 | Dry level | 0.8 100% |
| 11 | Early reflection level | 0.8 100% |
| 12 | Wet level | 0.6 75% |
| 13 | Mod Speed | 0.334 33% |
| 14 | Mod Depth | 0.0 0% |

## Fruity Fast Dist (5)

0 Pre amp (0.5 = 67%), 1 Threshold (1.0 = 100%), 2 Distortion type (0.0 = A), 3 Mix level (1.0 = 100%), 4 Post gain (1.0 = 100%).

## Fruity Multiband Compressor (28)

| index | name | sample |
|---|---|---|
| 0 | Master volume | 0.5 0.0 dB |
| 1 | Limiter | 0.0 OFF |
| 2 | Filter type | 0.0 BW IIR |
| 3 / 11 / 20 | High / Mid / Low band state | 0.0 ON |
| 4 | H Freq | 0.8498 9237 Hz |
| 12, 13 | M Freq H, M Freq L | 0.8498 9237 Hz, 0.3243 300 Hz |
| 21 | L Freq | 0.3243 300 Hz |
| 5 / 14 / 22 | H / M / L Output | 0.3333 0.0 dB |
| 6 / 15 / 23 | H / M / L Threshold | 0.7 -18.0 dB, 0.7458 -15.3 dB |
| 7 / 16 / 24 | H / M / L Ratio | 0.5 2.0:1 |
| 8 / 17 / 25 | H / M / L Attack | 0.0991 10.0 ms |
| 9 / 18 / 26 | H / M / L Release | 0.0909 100.0 ms |
| 10 / 19 / 27 | H / M / L Knee | 0.8 80% |

## HalfTime (VST wrapper, 4240 reported)

Real controls among "X (Reserved)" placeholders: 4 Power On, 8 Loop Length, 12 Mode, 16 Fade In, 17 Fade Out, 20 Smooth Length, 24 Split Low, 25 Split High, 26 Solo Band, 28 Mix. Its display strings are the raw value (0.56, 0.33), so a value's meaning has to come from its UI or a render.

## Soundgoodizer

Reports 0 parameters to the scripting API: not automatable this way.

## FabFilter Pro-L 2 (VST wrapper)

0 Gain (0.1332 = +4.00 dB), 2 Lookahead (0.036 = 0.180 ms), 3 Attack (0.4072 = 275.0 ms), 4 Release (0.3878 = 400.0 ms), 5 Channel Link Transients (0.375 = 75%), 6 Channel Link Release (0.5 = 100%), 7 Channel Link Center, 8 Channel Link LFE, 11 Dithering, 12 Noise Shaping, 13 Filter DC Offset, 14 Side Chain Triggering, 17 Bypass, 18 Output Level (1.0 = 0.00 dBTP), 20 Receive Midi, 32 Host Bypass. Indices 1, 9, 10, 15, 16, 19 and 21-31 have no name.

## Ozone 12 modules (VST wrapper)

All three share 0-5 GAIN Input/Output L/R (0.9351 = 0.00 dB) and 6 Global Bypass.

- **Stabilizer:** 7 STBL Bypass, 8 Tame Transients On/Off, 9-17 Stereo/Main Amount, Speed (Shape Mode), Smoothing, Sensitivity, Speed (Cut Mode), Low / Mid / High Amount, Bypass; 18-26 the same for Aux.
- **Maximizer:** 7 MAX Bypass, 8 Input Gain, 9 Output Level, 10 Link Input Gain and Output Level, 11 Character, 12 Upward Compression Amt (0.204 = 2.04 dB), 13 Soft Clip On/Off, 14 Soft Clip Mix, 15 Soft Clip Mode, 16 Transient Shaping Amt, 17 Stereo Ind. Sustain Amt, 18 Stereo Ind. Transient Amt, 19 Link Stereo Amounts.
- **Imager:** 7 IMG Bypass, 8 Global Amount, 9 Stereo/Main Enable Stereoizer, 10 Stereoizer Delay (1.0 = 20 ms), 11-14 Band 1-4 Width Percent (0.5 = 0; 0.3994 = -20.12, 0.8462 = 69.23, so width = 200 x (v - 0.5)), 15 Recover Sides Gain, 16 Stereo/Main Bypass; 17-24 the same for Aux.

Ozone displays use a decimal comma ("0,00 dB").

## Youlean Loudness Meter 2

Only 1 Bypass. A meter, nothing to automate.

## Slot-level targets (any effect)

Every mixer slot has two automatable switches outside the plugin's own parameters: mute / solo, target `{"mixer": t, "slot": s, "rec": "0x1f00"}` (0 or 1), and the slot's mix level, `{"mixer": t, "slot": s, "rec": "0x1f01"}` (0..1). `automation.encode_target` writes both. They are how effects come in and out.

## Gross Beat, measured slot by slot

Probe: one saved instance on an Amen bar plus a 440 Hz sine, each slot for one bar. Time maps show which 1/32 of the dry bar plays at each 1/32 (`0123...v` is dry). Volume rows show gain against dry per 1/32 (`#` open, `+` -6, `.` -15, `_` -25, space shut).

Time (index: what it did):
- 1 Basic 1, 3, 17: a 16th-pair stutter mid-bar (`898989`), the rest dry.
- 2, 11: the first beat repeated (`0123 0123`), a stutter on the last beat.
- 6, 7, 22, 24: holds and freezes (`4444`, `oooooooo`), a slice frozen to the bar's end.
- 8: the last beat reversed (`nmlkjihg`).
- 20, 21: 8ths reshuffled, the bar's first 16th re-fired at irregular points (`0145ab89...`, `0123016789...`).
- 25: a reversed fragment mid-bar (`fedc`).
- 26: most slices doubled, a half-speed read.
- 27: frozen on the snare, pitch down.
- 28-30, 34: pitch up by 900-2400 cents, a speed-up or rewind.
- 31: gated and stuttered.

Volume (index: shape): 1 shut for beat 2.5-3; 2 quarter-note gate, half of each beat; 3 and 5 8th and 32nd chops; 6, 7, 31 light tremolo; 14 "1st Step" the first 16th then silence; 15 "1st Stp Fade" the first 16th, silence, a swell back; 16 three hits then silence; 17 "Off Beat"; 21 and 32 "Fade In" across the bar; 28 "Sidechain" a swell into every beat; 33 "Fade Out"; 34 "Fade Out In"; 24, 25 no change at this source. In every row the last beat measured open; not explained, possibly the mid-bar switching of the probe.

From Image-Line's manual: Gross Beat works on a two-bar rolling buffer, so a time slot switched on right after a section change can replay the previous section. Its time envelope is a delay against the playhead: flat plays normally, falling half a beat per beat is half speed, one beat per beat a pause, two a reverse; a tape stop is a curve bending toward the pause slope. Trigger Sync (when a new slot takes effect: next bar at 4 beats, immediately when Off) and Position Sync (where in the envelope it starts) are settings of the saved state, not automatable parameters; switching at the end of the previous bar is Trigger Sync at 4 beats. Its own Time mix is better than an external dry/wet for avoiding phase problems.
