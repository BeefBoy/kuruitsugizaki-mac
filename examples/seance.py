"""Factory Seance: a two-minute glitchy witch house / breakcore piece, 170 BPM, D# minor.

Written by Claude Opus 5.5 (Anthropic) through kuruitsugizaki, as the full example. Every sound is FL Studio
factory content: Sytrus and 3x Osc presets, and samples from FL's own packs. Run it to write seance.json,
the compact document project_write takes; build.py turns it into an .flp. seance.md says why each part
is where it is.
"""
import json
from pathlib import Path

PPQ, BPM = 96, 170
BAR = 4 * PPQ
MS_TICK = 60000 / BPM / PPQ
BARS = 84
F = "%FLStudioFactoryData%/Data/Patches/Packs/"

SAMPLERS = [  # id, file, mixer insert
    ("kick", "Drums/Kicks/Jung Kick.wav", 1),
    ("gabber", "SFX/SFX Hardcore Kick.wav", 2),
    ("snare", "Drums/Snares/Jung Snare.wav", 3),
    ("ghost", "Drums/Snares/Industrial Snare 2.wav", 4),
    ("clap", "Drums/Percussion/Pap Clap.wav", 5),
    ("hat", "Drums/Hats/909 CH 1.wav", 6),
    ("open", "Drums/Hats/808 OH.wav", 7),
    ("ride", "Drums/Cymbals/Jung Ride.wav", 7),
    ("rim", "Drums/Snares/707 Rim.wav", 8),
    ("ice", "Drums/Percussion/FPC Ice Crack.wav", 8),
    ("sub808", "Drums/Kicks/808 Kick.wav", 9),
    ("ahh", "Vocals/Laurie Webb Ahh A.wav", 14),
    ("ooh", "Vocals/Laurie Webb Ooh C.wav", 14),
    ("mmh", "Vocals/Laurie Webb Mmh.wav", 14),
]
SYNTHS = [  # id, plugin, preset, mixer insert
    ("reese", "3x Osc", None, 10),
    ("lead", "Sytrus", "X Olbaid/Lead/Lead Supersaw 1", 11),
    ("pad", "Sytrus", "Pad/Haunted house", 12),
    ("organ", "Sytrus", "Organ/Deep", 13),
    ("bell", "Sytrus", "Bell/Glass", 13),
]
AUDIO = [  # id, file, mixer insert
    ("wait", "Vocals/Laurie Webb Wait.wav", 14),
    ("drone", "SFX/FX Holo Drone.wav", 16),
    ("choir", "SFX/FX Choir Swell.wav", 16),
    ("riser", "Risers/Riser Ghost.wv", 16),
    ("reverse", "SFX/FX Big Reverse.wav", 16),
    ("crash", "SFX/SFX Cym Crash.wav", 16),
    ("boom", "SFX/SFX Crush Explode.wav", 16),
    ("thunder", "SFX/SFX Thunder Sheet.wav", 16),
    ("zap", "SFX/SFX Electro Shock.wav", 16),
    ("spin", "SFX/FX Spin Down.wav", 16),
]
SECONDS = {"wait": 0.55, "drone": 13.72, "choir": 11.21, "riser": 7.5, "reverse": 2.48, "crash": 4.61, "boom": 1.6,
           "thunder": 2.03, "zap": 0.87, "spin": 9.99}
INST = [k for k, *_ in SAMPLERS] + [k for k, *_ in SYNTHS]
IDX = {k: i for i, k in enumerate(INST)}
SID = {k: i for i, (k, *_) in enumerate(AUDIO)}
PATS = {"drums": [], "bass": [], "lead": [], "pad": [], "keys": [], "vox": []}
ROLE = {"sub808": "bass", "reese": "bass", "lead": "lead", "pad": "pad", "organ": "keys", "bell": "keys", "ahh": "vox", "ooh": "vox", "mmh": "vox"}
clips, autos = [], []

PC = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
NAMES = list(PC)


def midi(n):
    return n if isinstance(n, int) else PC[n[:-1]] + 12 * (int(n[-1]) + 1)


def pos(token):
    """A position inside a bar as beat plus subdivision: '3', '3e', '3&', '3a', or '3+1/6' for tuplets."""
    if "+" in token:
        beat, frac = token.split("+")
        n, d = frac.split("/")
        return (int(beat) - 1) * PPQ + int(n) * PPQ // int(d)
    return (int(token[0]) - 1) * PPQ + {"": 0, "e": 24, "&": 48, "a": 72}[token[1:]]


def note(inst, bar, token, key="C4", vel=100, ln=24, late=0):
    t, k = (bar - 1) * BAR + pos(token) + late, midi(key)
    PATS[ROLE.get(inst, "drums")].append([t // BAR + 1, (t % BAR) // PPQ + 1, t % PPQ, max(6, int(ln)), f"{NAMES[k % 12]}{k // 12 - 1}", int(vel), IDX[inst]])


def hits(inst, bar, tokens, vel=100, key="C4"):
    """Several hits of one drum in one bar: 'tokens' are positions, each optionally ':velocity'."""
    for tok in tokens.split():
        p, _, v = tok.partition(":")
        note(inst, bar, p, key, int(v) if v else vel)


def clip(track, sample, bar, token="1", beats=None, start_ms=0.0):
    """An audio clip: 'beats' long from 'start_ms' into the sample (the whole sample when beats is None)."""
    t = (bar - 1) * BAR + pos(token)
    ln = int(round((SECONDS[sample] * 1000 - start_ms) / MS_TICK)) if beats is None else int(round(beats * PPQ))
    clips.append([track, t // BAR + 1, (t % BAR) // PPQ + 1, t % PPQ, ln, f"s{SID[sample]}", [int(round(start_ms)), int(round(start_ms + ln * MS_TICK))]])


def auto(name, target, points):
    """An automation clip over the whole piece; points are [bar, token, value] or [bar, token, value, tension]."""
    pts = [[((b - 1) * BAR + pos(tok)) / PPQ, v] + rest for b, tok, v, *rest in points]
    assert all(a[0] <= b[0] for a, b in zip(pts, pts[1:])), f"{name}: points out of order"
    autos.append({"id": name, "name": name, "kind": "automation", "target": target, "points": pts})


def step(bar, token, before, after):
    """Two points a hair apart: a switch on a grid line."""
    return [[bar, token, after]] if (bar, token) == (1, "1") else [_before(bar, token, before), [bar, token, after]]


def _before(bar, token, value):
    t = (bar - 1) * BAR + pos(token) - 1
    return [t // BAR + 1, f"{(t % BAR) // PPQ + 1}+{t % PPQ}/96", value]


# ---------------------------------------------------------------------------------------------- harmony
# Eight-bar cycle of roots, uneven on purpose: three bars of D#, one of E (the flat second), two of B, C#, E.
CYCLE = ["D#", "D#", "D#", "E", "B", "B", "C#", "E"]
SUB = {"D#": "G#3", "E": "A3", "B": "E4", "C#": "F#4"}          # the 808 sample sounds G1 at C4: these give D#1, E1, B1, C#2
REESE = {"D#": "D#1", "E": "E1", "B": "B0", "C#": "C#1"}        # 3x Osc sounds an octave above the written note
PADS = {"D#": ["A#4", "D#5", "F#5"], "E": ["B4", "E5", "G#5"], "B": ["B4", "D#5", "F#5"], "C#": ["C#5", "F5", "G#5"]}  # sounds an octave lower
ORGAN = {"D#": "D#4 A#4 F#4 D#5 A#4 C#5 F#4 A#4", "E": "E4 B4 G#4 E5 B4 D#5 G#4 B4",
         "B": "D#4 B4 F#4 D#5 B4 C#5 F#4 B4", "C#": "F4 C#5 G#4 F5 C#5 D#5 G#4 C#5"}
EIGHTHS = ["1", "1&", "2", "2&", "3", "3&", "4", "4&"]


def root(bar, first):
    return CYCLE[(bar - first) % 8]


def lead_motif(bar, first, up=0, vel=96):
    """The slow line: three notes a dotted quarter apart, falling to E, the flat second. One substitution per restatement."""
    i = (bar - first) % 8
    cell = [("A#4", "D#5", "C#5"), ("A#4", "F#4", "E4"), ("A#4", "D#5", "C#5"), ("A#4", "F#4", "E4"),
            ("A#4", "D#5", "F#5"), ("A#4", "F#4", "E4"), ("G#4", "C#5", "D#5"), ("B4", "G#4", "E4")][i]
    for tok, key, ln in zip(("1", "2&", "4"), cell, (132, 132, 150)):
        note("lead", bar, tok, midi(key) + up, vel, ln, late=6)


def low_line(bar, first, vel=78):
    """The second line in the same sound, slow neighbour motion around A#3; where it meets the motif is the harmony."""
    key, bars = {0: ("A#3", 2), 2: ("G#3", 1), 3: ("B3", 1), 4: ("F#3", 2), 6: ("G#3", 1), 7: ("B3", 1)}.get((bar - first) % 8, (None, 0))
    if key:
        note("lead", bar, "1", key, vel, bars * BAR + 30, late=10)


def pad_chord(bar, bars, name, vel=84):
    for key in PADS[name]:
        note("pad", bar, "1", key, vel, bars * BAR - 12)


def organ_line(bar, name, skip=(), vel=80):
    """The fast line: straight 8ths, every move a leap; 'skip' leaves holes where the drums stop."""
    for n, (tok, key) in enumerate(zip(EIGHTHS, ORGAN[name].split())):
        if n not in skip:
            note("organ", bar, tok, key, vel - (10 if n % 2 else 0), 40, late=3)


def reese_bar(bar, name, turn=None, vel=100):
    """Bass on a dotted grid (three notes per bar, six 16ths apart), ten ticks late so the kick's click comes first."""
    r = midi(REESE[name])
    for tok, key, ln in zip(("1", "2&", "4"), (r, r, turn if turn is not None else r + 12), (120, 120, 80)):
        note("reese", bar, tok, key, vel, ln, late=10)


# ---------------------------------------------------------------------------------------------- drums
def halftime_bar(bar, kind, name, stop=None):
    """Half-time floor: boom on 1, clap on 3. kind 'a' rolls the hat into the clap, 'b' into the next bar.
    stop: the beat from which the bar is silent."""
    k = {"a": "1 4&:84", "b": "1 3&:90"}[kind]
    hat = {"a": "1:92 1&:66 2:84 2&:58 2+4/6:70 2+5/6:86 3:78 3&:64 4:84 4&:66",
           "b": "1:92 1&:66 2:84 2&:64 3:78 3&:64 4:84 4&:60 4+5/8:68 4+6/8:78 4+7/8:90"}[kind]
    keep = lambda toks: " ".join(t for t in toks.split() if stop is None or int(t[0]) < stop)
    hits("kick", bar, keep(k))
    hits("clap", bar, keep("3"), 104)
    hits("hat", bar, keep(hat))
    note("sub808", bar, "1", SUB[name], 104, 300)
    if kind == "b" and (stop is None or stop > 3):
        note("sub808", bar, "3&", midi(SUB[name]) + 12, 86, 100)   # the pickup an octave up, short
    if kind == "a" and stop is None:
        hits("open", bar, "4&:70")


AMEN = {  # the Amen's four bars as 16th positions, played with one-shots: kick, main snare, ghost snare
    1: ("1 1& 3& 3a:88", "2 4", "2a:62 3e:70 4a:66"),
    2: ("1 1& 3& 3a:88", "2 4", "2a:62 3e:70 4a:66"),
    3: ("1 1& 3&", "2 4&", "2a:62 3e:70"),
    4: ("1& 1a:88 3&", "2 4&", "1e:58 2a:62 3e:70"),
}


def amen_bar(bar, n, stop=None, ride=True):
    k, s, g = AMEN[n]
    keep = lambda toks: " ".join(t for t in toks.split() if stop is None or pos(t.partition(":")[0]) < pos(stop))
    hits("kick", bar, keep(k))
    hits("snare", bar, keep(s), 106)
    hits("ghost", bar, keep(g))
    if ride:
        hits("ride", bar, keep("1:96 1&:70 2:88 2&:70 3:92 3&:70 4:88 4&:70"))
    if n == 4 and stop is None:
        hits("open", bar, "3&:92")                                 # the Amen's bar-4 crash, between beats 3 and 4


def twostep_bar(bar, kind, stop=None):
    """The second floor: kick on 1 and the and of 3, snare on 2 and 4, a 16th hat stream broken by doubles."""
    k = {"a": "1 3&", "b": "1 2&:84 3&"}[kind]
    hat = {"a": "1:92 1e:58 1&:76 1a:58 2:84 2e:58 2&:76 2+4/6:66 2a:60 3:88 3e:58 3&:76 3a:58 4:84 4e:58 4&:76 4a:62",
           "b": "1:92 1e:58 1&:76 1a:58 2:84 2e:58 2&:76 2a:58 3:88 3e:58 3&:76 3a:60 4:84 4e:60 4&:76 4+4/6:68 4+5/6:82"}[kind]
    keep = lambda toks: " ".join(t for t in toks.split() if stop is None or pos(t.partition(":")[0]) < pos(stop))
    hits("kick", bar, keep(k))
    hits("snare", bar, keep("2 4"), 106)
    hits("hat", bar, keep(hat))
    if kind == "b":
        hits("ghost", bar, keep("4a:64"))


def ratchet(bar, token, count, every, key="C4", climb=1, vel=(70, 104), inst="ghost"):
    """A restruck snare: 'count' hits 'every' ticks apart, each 'climb' semitones higher, getting louder."""
    t0 = pos(token)
    for n in range(count):
        t = t0 + n * every
        note(inst, bar + t // BAR, f"{(t % BAR) // PPQ + 1}+{t % PPQ}/96", midi(key) + n * climb, vel[0] + (vel[1] - vel[0]) * n // max(1, count - 1))


def stutter(track, bar, token, count, every_beats, start_ms=0.0, slice_ms=None, sample="wait"):
    """One vocal word cut into repeats: the same audio clip placed 'count' times, each trimmed to the gap.
    Clips alternate between two playlist tracks, because overlapping clips on one track crossfade."""
    t0 = (bar - 1) * BAR + pos(token)
    for n in range(count):
        t = t0 + int(round(n * every_beats * PPQ))
        beats = every_beats if slice_ms is None else min(every_beats, slice_ms / MS_TICK / PPQ)
        clip(track + n % 2, sample, t // BAR + 1, f"{(t % BAR) // PPQ + 1}+{t % PPQ}/96", beats, start_ms)


# ============================================================================================== the piece
# I  bars 1-8: intro. No drums: the drone, a choir swell, the vocal an octave down, the motif on a bell.
clip(11, "drone", 1, beats=32)
clip(12, "choir", 5, beats=28)
note("ahh", 3, "1", "C3", 80, BAR)
note("ooh", 6, "3", "C3", 78, BAR)
for bar, toks in ((2, [("3", "A#5"), ("4&", "D#6")]), (4, [("1&", "C#6"), ("3", "A#5"), ("4&", "F#5")]), (6, [("1", "E5")]), (8, [("1&", "A#5"), ("2a", "D#6")])):
    for tok, key in toks:
        note("bell", bar, tok, key, 84, 96)
pad_chord(5, 4, "D#", 70)
hits("clap", 7, "3:70")                                            # one far clap: the half-time backbeat before it exists
clip(17, "reverse", 7, "2", beats=7)                               # 7 beats of reverse swell, ending on the downbeat of bar 9
note("sub808", 8, "4&", "G#4", 80, 40)

# W1  bars 9-24: witch house. Half-time floor, 808, the motif, the pad ducked by the kick.
for bar in range(9, 25):
    name, i = root(bar, 9), bar - 9
    stop = {12: 4, 16: 3, 20: 4, 24: 3}.get(bar)                   # a short stop every fourth bar, a longer one every eighth
    halftime_bar(bar, "ab"[i % 2], name, stop)
    lead_motif(bar, 9)
    if i % 8 in (0, 3, 4, 6, 7):
        pad_chord(bar, {0: 3, 3: 1, 4: 2, 6: 1, 7: 1}[i % 8], name)
    if bar >= 17:
        low_line(bar, 17)
for bar, toks in ((18, "2:F#5 2&:A#5 3&:D#6"), (20, "2:F#5 2&:A#5 3&:C#6"), (22, "2:G#5 2&:C#6 3&:F6")):   # the bell answers the motif's fall by rising
    for tok in toks.split():
        p, key = tok.split(":")
        note("bell", bar, p, key, 80, 60)
note("mmh", 12, "4", "C4", 96, PPQ)                                # the vocal fills the stops
stutter(14, 16, "3", 4, 0.5, slice_ms=150)
note("ahh", 16, "3", "C3", 84, 2 * PPQ)
stutter(14, 20, "4", 4, 0.25, start_ms=60, slice_ms=80)
clip(13, "riser", 23, "3+72/96", beats=21.25)                      # 7.5 s of riser ending on bar 29
clip(17, "reverse", 23, "2", beats=7)

# G  bars 25-28: glitch bridge. The floor is gone; rim and ice in tuplets, the word cut finer each bar.
clip(16, "thunder", 25, beats=5.5)
pad_chord(25, 3, "E", 76)
note("sub808", 25, "1", SUB["E"], 104, 300)
hits("rim", 25, "1 2&:80 4:90 4+1/3:70 4+2/3:84")
hits("rim", 26, "1 1+1/5:60 1+2/5:70 1+3/5:80 1+4/5:92 3& 4a:80")  # a quintuplet: five against the beat, once
hits("ice", 26, "2 3:80")
hits("rim", 27, "1 1a:70 2&:84 3e:70 4:90")
hits("ice", 27, "1& 2a:76 3& 4+1/3:70 4+2/3:86")
stutter(14, 25, "3", 2, 0.5, slice_ms=170)
stutter(14, 26, "2", 4, 0.25, start_ms=40, slice_ms=85)
stutter(14, 26, "4", 4, 0.25, start_ms=200, slice_ms=85)
stutter(14, 27, "1", 8, 0.25, start_ms=40, slice_ms=85)
stutter(14, 27, "3", 16, 0.125, start_ms=120, slice_ms=42)         # 32nds: the word becomes a tone
clip(16, "zap", 27, "4&", beats=0.5)
note("ahh", 28, "1", "C3", 100, 3 * PPQ)                           # one long vowel, dragged down by the channel pitch clip below
hits("gabber", 28, "1:96")
ratchet(28, "3", 12, 8, "C4", 1, (60, 104), inst="ghost")          # 32nd-triplet snare climbing an octave into the silence on beat 4

# B1  bars 29-44: breakcore. An Amen played from one-shots, a reese on a dotted grid, the organ's leaping 8ths against the slow motif.
clip(18, "crash", 29, beats=12)
hits("gabber", 29, "1")
for bar in range(29, 45):
    name, i = root(bar, 29), bar - 29
    stop = {32: "4", 36: "3", 40: "3", 44: "2&"}.get(bar)
    amen_bar(bar, i % 4 + 1, stop)
    skip = {32: (6, 7), 36: (4, 5, 6, 7), 40: (4, 5, 6, 7), 44: (3, 4, 5, 6, 7)}.get(bar, ())
    organ_line(bar, name, skip)
    if stop is None:
        reese_bar(bar, name, turn=midi(REESE[name]) + (1 if i % 8 == 2 else 12))   # bar 3 of the cycle turns to the flat second instead of the octave
    else:
        note("reese", bar, "1", REESE[name], 100, 120, late=10)
    if bar >= 37:
        lead_motif(bar, 37, vel=90)
stutter(14, 32, "4", 4, 0.25, start_ms=40, slice_ms=85)             # the stop on beat 4 belongs to the voice
hits("kick", 33, "2&:80", key="A3")                                 # the kick three semitones down, in the Amen's gap
hits("kick", 35, "2&:80", key="A3")
ratchet(34, "4", 8, 12, "C4", 1)                                    # snare restruck in 32nds, a semitone up each time
clip(17, "reverse", 35, "2", beats=7)
note("mmh", 36, "3", "C4", 100, PPQ)
hits("hat", 37, "2+1/6:64 2+2/6:78")                                # 16th-triplet answers to the kick double
hits("hat", 38, "2+1/6:64 2+2/6:78")
hits("rim", 38, "4 4+1/5:64 4+2/5:74 4+3/5:84 4+4/5:96")
hits("ice", 39, "1a:80 2a:72 3a:84")
hits("gabber", 37, "1")
ratchet(40, "3", 8, 24, "C4", 0, (84, 108), inst="kick")            # 16th kick roll through the last two beats: the gabber fill
hits("gabber", 41, "1")
clip(18, "crash", 41, beats=8)
hits("ice", 42, "2e:80 2a:70 4e:84")
ratchet(43, "4", 6, 16, "C4", 2)                                    # 16th triplets, a whole tone up each time
stutter(14, 44, "3", 8, 0.125, start_ms=120, slice_ms=42)
clip(17, "reverse", 43, "2", beats=7)

# D  bars 45-52: breakdown. Drums out, the pad opens to full width, the voice an octave down and falling.
clip(16, "boom", 45, beats=4)
clip(11, "drone", 45, beats=32)
clip(12, "choir", 46, beats=28)
for bar, n in ((45, 3), (48, 1), (49, 2), (51, 1), (52, 1)):
    pad_chord(bar, n, root(bar, 45), 80)
note("sub808", 45, "1", SUB["D#"], 100, 300)
note("sub808", 49, "1", SUB["B"], 96, 300)
note("ooh", 46, "1", "C3", 96, 2 * BAR)
note("ahh", 49, "1", "C4", 90, BAR)
note("ahh", 51, "1", "C3", 96, 2 * BAR)
for bar, toks in ((45, "3:A#5 4&:D#6"), (47, "1&:C#6 3:A#5 4&:F#5"), (48, "3&:E5"), (50, "1&:A#5 2a:D#6 4:F#6"), (52, "1:E6 2&:B5")):
    for tok in toks.split():
        p, key = tok.split(":")
        note("bell", bar, p, key, 82, 96)
hits("rim", 50, "3 3+1/3:70 3+2/3:84")
hits("rim", 52, "1& 2a:76 3& 3+3/4:80 4 4+1/6:66 4+2/6:74 4+3/6:82 4+4/6:90 4+5/6:98")
clip(13, "riser", 47, "3+72/96", beats=21.25)                       # ends on bar 53
ratchet(52, "4", 12, 8, "C4", 1, (60, 108))

# B2  bars 53-76: the last stretch. A two-step floor for eight bars, then the Amen returns under it with everything on.
clip(18, "crash", 53, beats=12)
hits("gabber", 53, "1")
for n in range(19):                                                 # a 7-step rim cycle against the 4/4 bar, for eight bars
    t = (53 - 1) * BAR + n * 7 * 24
    if t < (61 - 1) * BAR:
        note("rim", t // BAR + 1, f"{(t % BAR) // PPQ + 1}+{t % PPQ}/96", "C4", 86 if n % 2 else 72)
for bar in range(53, 77):
    name, i = root(bar, 53), bar - 53
    stop = {56: "4", 60: "3", 64: "4", 68: "3", 72: "3", 76: "2"}.get(bar)
    if bar < 61:
        twostep_bar(bar, "ab"[i % 2], stop)
    else:
        amen_bar(bar, i % 4 + 1, stop)
        hits("hat", bar, " ".join(t for t in "1e:54 1a:54 2e:54 2a:56 3e:54 3a:54 4e:54 4a:58".split() if stop is None or pos(t.partition(":")[0]) < pos(stop)))
    skip = {56: (6, 7), 60: (4, 5, 6, 7), 64: (6, 7), 68: (4, 5, 6, 7), 72: (4, 5, 6, 7), 76: (2, 3, 4, 5, 6, 7)}.get(bar, ())
    organ_line(bar, name, skip, vel=86)
    if stop is None:
        reese_bar(bar, name, turn=midi(REESE[name]) + (1 if i % 8 == 2 else 12))
    else:
        note("reese", bar, "1", REESE[name], 100, 120, late=10)
    lead_motif(bar, 53, up=12 if bar >= 61 else 0, vel=94)          # the motif an octave up once the Amen is back
    if bar >= 61:
        low_line(bar, 61, vel=82)
stutter(14, 56, "4", 4, 0.25, start_ms=40, slice_ms=85)
clip(17, "reverse", 59, "2", beats=7)
stutter(14, 60, "3", 4, 0.5, slice_ms=150)
hits("gabber", 61, "1")
clip(18, "crash", 61, beats=12)
ratchet(62, "4", 8, 12, "C4", 1)
hits("kick", 63, "2&:80", key="A3")
note("mmh", 64, "4", "C4", 100, PPQ)
hits("ice", 65, "1a:80 2a:72 3a:84")
hits("hat", 66, "2+1/6:64 2+2/6:78")
ratchet(67, "4", 6, 16, "C4", 2)
note("ahh", 68, "3", "C3", 100, 2 * PPQ)                            # bar 68, beats 3-4: the tempo drops to half under one vowel
hits("gabber", 69, "1")
clip(18, "crash", 69, beats=8)
hits("rim", 70, "4 4+1/5:64 4+2/5:74 4+3/5:84 4+4/5:96")
ratchet(71, "3", 16, 12, "C4", 1, (60, 108))                        # a full octave of 32nds
stutter(14, 72, "3", 16, 0.125, start_ms=120, slice_ms=42)
clip(17, "reverse", 71, "2", beats=7)
hits("gabber", 73, "1")
hits("ice", 74, "2e:80 2a:70 4e:84")
ratchet(75, "3", 8, 24, "C4", 0, (84, 108), inst="kick")
ratchet(75, "4", 12, 8, "C4", 1, (70, 108))
clip(17, "reverse", 75, "2", beats=7)
stutter(14, 76, "2", 4, 0.25, start_ms=40, slice_ms=85)
stutter(14, 76, "3", 16, 0.125, start_ms=120, slice_ms=42)

# O  bars 77-84: outro. One hit, then the tempo and the master pitch run down under the drone and the voice while the master fader fades.
hits("gabber", 77, "1")
clip(16, "boom", 77, beats=4)
clip(18, "crash", 77, beats=12)
clip(11, "drone", 77, beats=32)
clip(12, "spin", 78, beats=20)
note("sub808", 77, "1", SUB["D#"], 104, 300)
pad_chord(77, 4, "D#", 78)
pad_chord(81, 3, "E", 70)
note("ahh", 78, "1", "C3", 96, 3 * BAR)
for tok, key in (("1", "A#5"), ("2&", "F#5"), ("4", "E5")):          # the motif once more, on the bell, ending on the flat second
    note("bell", 80, tok, key, 80, 96)
note("bell", 82, "1", "D#5", 76, 2 * BAR)

# ============================================================================================== automation
T170, T85 = (170 - 60) / 120, (85 - 60) / 120                       # tempo value = (bpm - 60) / 120
PITCH = lambda semitones: 0.5 + semitones / 96                      # channel pitch: 0.5 is centre, the knob spans four octaves each way

# global: tempo. A tape stop into the first drop, a half-time snap in bar 68, the outro running down to 100.
auto("tempo", {"global": "tempo"}, [[1, "1", T170], [28, "3", T170], [28, "4+95/96", T85, 0.6], *step(29, "1", T85, T170),
                                    *step(68, "3", T170, T85), *step(69, "1", T85, T170), [77, "2", T170], [84, "4", (100 - 60) / 120, -0.4]])
# global: master pitch. The whole mix sinks a whole tone through the outro, under the tempo running down: the screw.
auto("master pitch", {"global": "main_pitch"}, [[1, "1", 0.5], [79, "1", 0.5], [84, "4", 0.5 - 2 / 24, 0.3]])     # 0.5 in tune, +-12 semitones over the knob
# the overall level is the master insert's fader ({global: main_vol} is written but FL 2025 ignores it); the fade is the ending.
auto("master fade", {"mixer": 0, "param": "vol"}, [[1, "1", 0.8], [79, "1", 0.8], [84, "4", 0.0, 0.3]])
# mixer: fader, pan, stereo separation.
auto("atmos fader", {"mixer": 16, "param": "vol"}, [[1, "1", 0.0], [4, "1", 0.34, 0.4], [22, "4", 0.34], [23, "3", 0.5], [44, "4", 0.5], *step(45, "1", 0.5, 0.36), [47, "2", 0.36], [48, "1", 0.5],
                                                          [76, "4", 0.5], *step(77, "1", 0.5, 0.4)])
auto("ticks pan", {"mixer": 8, "param": "pan"}, [[1, "1", 0.5], *step(25, "1", 0.5, 0.15), [27, "4", 0.85], *step(29, "1", 0.85, 0.5),
                                                *step(53, "1", 0.5, 0.25), [56, "4", 0.75], [60, "4", 0.25], *step(61, "1", 0.25, 0.5)])
auto("pad width", {"mixer": 12, "param": "sep"}, [[1, "1", 0.5], *step(29, "1", 0.5, 0.85), *step(45, "1", 0.85, 0.0), *step(53, "1", 0.0, 0.85), *step(77, "1", 0.85, 0.2)])  # 1 is mono, 0 is widest
# effect knobs: the drum bus filter (EQ band 7, a high shelf at -18 dB, its corner moved), the vocal reverb's wet level.
auto("drum bus filter", {"mixer": 15, "slot": 0, "param": 13}, [[1, "1", 1.0], [25, "1", 1.0], [27, "4", 0.62, 0.3], *step(29, "1", 0.62, 1.0),
                                                                 [43, "1", 1.0], [44, "2&", 0.55], *step(53, "1", 0.55, 1.0), [75, "1", 1.0], [76, "2", 0.6], *step(77, "1", 0.6, 1.0)])
auto("vocal reverb wet", {"mixer": 14, "slot": 1, "param": 12}, [[1, "1", 0.55], [8, "4", 0.75], *step(9, "1", 0.75, 0.35), [24, "4", 0.35], [28, "4", 0.8],
                                                                  *step(29, "1", 0.8, 0.3), *step(45, "1", 0.3, 0.7), [52, "4", 0.8], *step(53, "1", 0.8, 0.3), *step(77, "1", 0.3, 0.8)])
# mixer slots: an effect's mix level and its mute switch are targets of their own.
auto("drum bus dist mix", {"mixer": 15, "slot": 1, "rec": "0x1f01"}, [[1, "1", 0.0], *step(29, "1", 0.0, 0.3), [36, "4", 0.3], [44, "1", 0.7], *step(45, "1", 0.7, 0.0),
                                                                     *step(53, "1", 0.0, 0.35), *step(61, "1", 0.35, 0.6), [76, "1", 0.9], *step(77, "1", 0.9, 0.0)])
auto("drum bus crush on", {"mixer": 15, "slot": 2, "rec": "0x1f00"}, [[1, "1", 0.0], *step(25, "1", 0.0, 1.0), *step(29, "1", 1.0, 0.0), *step(40, "3", 0.0, 1.0), *step(41, "1", 1.0, 0.0),
                                                                     *step(68, "3", 0.0, 1.0), *step(69, "1", 1.0, 0.0), *step(75, "3", 0.0, 1.0), *step(77, "1", 1.0, 0.0)])
# instrument knobs (3x Osc, indexes from docs/params/instrument_3x_osc.tsv). Held values build the patch; moving ones are the performance.
for name, index, value in (("reese osc1 saw", 1, 0.5), ("reese osc2 saw", 8, 0.5), ("reese osc3 saw", 15, 0.5), ("reese osc2 level", 6, 0.8), ("reese osc3 level", 13, 0.7),
                           ("reese osc2 octave", 9, 0.5), ("reese osc3 octave", 16, 0.25)):
    auto(name, {"channel": "reese", "param": index}, [[1, "1", value], [BARS, "4", value]])
auto("reese osc2 detune", {"channel": "reese", "param": 10}, [[1, "1", 0.56], [29, "1", 0.56], [44, "1", 0.68], *step(53, "1", 0.68, 0.56), [76, "1", 0.74]])   # 0.5 is in tune, +-100 cents: the beating speeds up through each drop
auto("reese osc3 detune", {"channel": "reese", "param": 17}, [[1, "1", 0.45], [29, "1", 0.45], [44, "1", 0.36], *step(53, "1", 0.36, 0.45), [76, "1", 0.3]])
# channel settings: pitch (the voice dragged down), volume (the lead swelling into the last stretch), pan (the bell crossing).
auto("ahh pitch", {"channel": "ahh", "param": "pitch"}, [[1, "1", PITCH(0)], [28, "2", PITCH(0)], [28, "4+95/96", PITCH(-12), 0.5], *step(29, "1", PITCH(-12), PITCH(0)),
                                                        [51, "3", PITCH(0)], [52, "4+95/96", PITCH(-7), 0.4], *step(53, "1", PITCH(-7), PITCH(0)),
                                                        [68, "3", PITCH(0)], [68, "4+95/96", PITCH(-5)], *step(69, "1", PITCH(-5), PITCH(0)), [79, "1", PITCH(0)], [80, "4+95/96", PITCH(-12), 0.3]])
auto("sub808 tuning", {"channel": "sub808", "param": "pitch"}, [[1, "1", PITCH(-0.3)], [BARS, "4", PITCH(-0.3)]])     # the sample sits about 30 cents sharp of D#: a held clip is a tuning knob
auto("lead volume", {"channel": "lead", "param": "vol"}, [[1, "1", 0.78], *step(37, "1", 0.78, 0.6), [44, "4", 0.78], *step(53, "1", 0.78, 0.7), [61, "1", 0.78]])
auto("bell pan", {"channel": "bell", "param": "pan"}, [[1, "1", 0.3], [8, "4", 0.7], [17, "1", 0.7], [24, "4", 0.3], [45, "1", 0.3], [52, "4", 0.7], [77, "1", 0.5]])

# ============================================================================================== mixer
DRUMS = range(1, 9)
mixer = {
    "volume": {"1": 0.8, "2": 0.7, "3": 1.0, "4": 0.62, "5": 0.7, "6": 0.54, "7": 0.58, "8": 0.62, "9": 0.74, "10": 0.66, "11": 0.64, "12": 0.52, "13": 0.9, "14": 0.6, "15": 0.9, "16": 0.4},
        # bus routing: every drum insert goes to insert 15 and no longer to the master. sidechain: the kick also feeds the pad's insert at level 0,
    # where a Fruity Limiter in compressor mode listens to it.
    "routes": [r for n in DRUMS for r in ({"from": n, "to": 15}, {"from": n, "to": 0, "on": False})] + [{"from": 1, "to": 12, "level": 0.0}],
    "effects": [
        {"track": 15, "slot": 0, "from": {"file": "projects/init/fx.flp", "track": 1, "slot": 0}},          # Fruity Parametric EQ 2, the bus filter
        {"track": 15, "slot": 1, "plugin": "Fruity Fast Dist", "preset": "fuzz"},
        {"track": 15, "slot": 2, "plugin": "Fruity Squeeze", "preset": "Grit"},
        {"track": 9, "slot": 0, "plugin": "Fruity Fast Dist", "preset": "warmth"},                           # harmonics, so the 808 is heard and not only metered
        {"track": 10, "slot": 0, "plugin": "Fruity Blood Overdrive", "preset": "Drive"},
        {"track": 11, "slot": 0, "plugin": "Fruity Reeverb 2", "preset": "Large Hall"},
        {"track": 12, "slot": 0, "from": {"file": "projects/init/fx.flp", "track": 3, "slot": 0}},          # Fruity Limiter, compressor mode, sidechained
        {"track": 12, "slot": 1, "plugin": "Fruity Reeverb 2", "preset": "Cathedral"},
        {"track": 13, "slot": 0, "plugin": "Fruity Delay 3", "preset": "Ping pong"},
        {"track": 13, "slot": 1, "plugin": "Fruity Reeverb 2", "preset": "Large Hall"},
        {"track": 14, "slot": 0, "plugin": "Fruity Delay 3", "preset": "Tape"},
        {"track": 14, "slot": 1, "plugin": "Fruity Reeverb 2", "preset": "Cathedral"},
        {"track": 16, "slot": 0, "plugin": "Fruity Reeverb 2", "preset": "Large Hall"},
        {"track": 0, "slot": 9, "from": {"file": "projects/init/fx.flp", "track": 2, "slot": 0}},           # Fruity Limiter on the master
    ],
}

# ============================================================================================== the document
END = BARS * BAR
doc = {
    "format": "compact",
    "project": {"bpm": BPM, "ppq": PPQ, "title": "Factory Seance", "author": "Claude Opus 5.5 (Anthropic), written through kuruitsugizaki", "genre": "witch house / breakcore",
                "comment": "A two-minute example piece. Every sound is FL Studio factory content. Source: examples/seance.py"},
    "note_cols": ["bar", "beat", "tick", "len", "key", "vel", "inst"],
    "clip_cols": ["track", "bar", "beat", "tick", "len", "src", "trim?"],
    "instruments": [{"id": k, "name": k, "kind": "sampler", "path": F + p, "mixer": mx} for k, p, mx in SAMPLERS]
                   + [{"id": k, "name": k, "kind": "plugin", "plugin": plug, "mixer": mx, **({"preset": p} if p else {})} for k, plug, p, mx in SYNTHS],
    "samples": [{"id": k, "name": k, "kind": "audio", "path": F + p, "mixer": mx} for k, p, mx in AUDIO],
    "automation": autos,
    "mixer": mixer,
    "patterns": [{"id": k, "notes": sorted(v)} for k, v in PATS.items() if v],
    "arrangements": [{"name": "Factory Seance", "clips": [[n + 1, 1, 1, 0, END, k] for n, k in enumerate(k for k, v in PATS.items() if v)] + clips
                      + [[20 + n, 1, 1, 0, END, f"a{n}"] for n in range(len(autos))]}],
}

if __name__ == "__main__":
    out = Path(__file__).with_suffix(".json")
    out.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
    print(f"{out.name}: {sum(len(v) for v in PATS.values())} notes, {len(clips)} audio clips, {len(autos)} automation clips, {BARS} bars at {BPM}")
