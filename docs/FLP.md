# FLP event map

Measured facts only, each with the file and evidence it rests on. Anything without evidence is marked open.
The projects named below are the ones each fact was measured on; they are not part of this repo. `init` was an empty template with 1 channel, `key` a project with 6 channels, 2 patterns and Ozone on a mixer insert, both saved by FL 25.1.6.4997.

## Container

- `FLhd` u32 len=6, then `<hHH`: format=0, channel count, PPQ=96. Channel count is 1 in init and 6 in key, matching the channels named in `203`.
- `FLdt` u32 len, then events. Size by ID: 0-63 one byte, 64-127 two, 128-191 four, 192-255 varint length. Both files parse to exactly the chunk end and re-serialize byte-identical (init 1417 events, key 1687).

## Mapped

| id | what | evidence |
|---|---|---|
| 199 | FL version, ascii | `25.1.6.4997` in both |
| 159 | build number | 4997 in init |
| 202 | project data folder, utf16 | `<projects folder>\<name>\` in both |
| 203 | plugin display name, utf16 | channel names in rack order in key, plus `Fruity Parametric EQ 2` on an insert |
| 201 | internal plugin name, utf16 | FLEX, Fruity Wrapper, Fruity Multiband Compressor; empty for Sampler/audio channels |
| 196 | sample path, utf16 | the three .wav channels in key |
| 213 | plugin state blob | Fruity Wrapper 254607 bytes containing `Ozone 12`, `iZotope`, the .vst3 path; FLEX 2707 bytes containing `Analog Monsters by UVI` and preset name `KEY JP CP JP 70` |
| 224 | pattern notes, 24-byte records `<IHHIHHBBBBBBBB` | key: 24 notes all rack 3, 51 notes all rack 4, positions 0-2976 at PPQ 96, defaults vel 100 pan 64 fine 120 modx/y 128 |
| 204 | mixer insert name, utf16 | channel names repeated after the Ozone slot in key |
| 231 | channel filter group, utf16 | `Audio`, `Unsorted` |
| 241 | arrangement name, utf16 | `Arrangement` |
| 212 | per-plugin slot record, 52 bytes, precedes every 203. For mixer effects bytes 0-3 = mixer track, 4-7 = slot | key: Ozone 0/4, Multiband Compressor 1/3, Parametric EQ 2 3/4, matching the live FL scan (Master slot 4, track 1 slot 3, track 3 slot 4). For channels bytes 0-7 are zero; the rest is unmapped |

Note `rack` equals the channel's index in `203` order.

## Fruity Wrapper state (213 of a wrapped VST)

u32 header = 12, then records `<IQ` (u32 id, u64 length) + data. Consumes Ozone's blob exactly in key and key_2, 11 records each.

| rec | what | evidence |
|---|---|---|
| 52 | 16 bytes, `ZTSVOBOZzone...`, likely VST3 class id | only identifying 16-byte field; not confirmed |
| 54 | plugin name | `Ozone 12` |
| 55 | plugin path | `C:\Program Files\Common Files\VST3\iZotope\Ozone 12.vst3` |
| 56 | vendor | `iZotope` |
| 53 | the plugin's own state | 254283 bytes; shrank 88 bytes when Ozone's main output bypass was switched on (key -> key_2) |
| 1, 30, 31, 32, 50 | unmapped | identical between key and key_2 |
| 2 | unmapped, 25 bytes | changed between key and key_2 in bytes 1-8; editor window state is a guess |

## Serum 2 inside the wrapper (record 53)

From `init_serum_2_copies.flp`: one Serum 2 at init, one with factory preset `BA - Hidden Bottom Spread` (Serum 2.0.23). Record 53 is u32 header = 1, then sections `<IQ` (u32 id, u64 length) + data, consuming exactly on both channels.

| sec | what | evidence |
|---|---|---|
| 1 | 64 bytes, first u32 = 1, rest zero | identical on both |
| 3 | processor state: an `XferJson` container, meta tag 0 then CBOR/zstd tag 2 | meta `component: processor`; CBOR decodes to a dict of 162 module keys (Arp0, Env0, FXRack0, LFO0...), 1052 bytes compressed at init, 4704 with the preset |
| 2 | controller state: an `XferJson` container | meta `component: controller` with `presetName` ` - Init - ` and `BA - Hidden Bottom Spread`, author, description; CBOR 58 and 67 keys |
| 4 | 10496 bytes | same length on both channels; unmapped |

The container is the one a `.SerumPreset` file uses, and the `.SerumPreset` document is the two halves merged. Measured against `BA - Hidden Bottom Spread.SerumPreset` (Serum 2.0.23): a deep merge of processor + controller matches the file on 1129 of 1130 leaves, the one difference a float in the 16th digit (Env1 decay). The controller holds names: macro `name`, rack `displayName`, preset name/author/description. The merge has 91 leaves the file lacks, all `FXRack*/FX[*]/defaultPlainValues`; the file has 11 the merge lacks, `LFO1..9/plainParams`, `fileType` and one tag. The split, derived from the FL-saved BA channel against its file: the controller takes every `kUIParam*` leaf, `displayName`, `curveDisplayName`, `arpBankDisplayName`, `clipBankDisplayName`, `name` under `Macro#` and `MidiClip#`, the MidiClip grid keys (`displayLength_Beats`, `gridWidth_Beats`, `gridYOffset_Rows`, `laneTabs`, `selectedLane`) and `presetName`/`presetAuthor`/`presetDescription`; the processor takes everything else, `tags` included; `product`, `productVersion`, `url`, `vendor`, `version` go to both. With that rule the processor built from the file equals FL's on every leaf but one float in its 16th digit and the file's third tag. The controller FL saved also carries `Macro#/default` (value / 100, now written) and `FXRack#/FX[]/defaultPlainValues` (not written; Serum loads without them). Container: `XferJson\0`, u32 meta length, u32 0, meta JSON (compact, keys sorted), u32 CBOR length, u32 2, a zstd frame with content size and no checksum; the meta `hash` is the MD5 of that zstd frame. zstd level 3 reproduces the template's processor frame byte for byte. Loaded live: `BA - Hidden Bottom Spread` (mono on, B unison 5, sub on, main vol 32%, all eight macro names and values) and `808 - Basic 808` (noise on, MG Low 24, legato, porta 123 ms, macros GRIT/KICK/WIDEN), both sounding. FL shows `Prog 1` as the preset name for either.

## VST3 plugin state inside the wrapper (record 53)

An 80-byte header (u32 1, 1, 64, 0, 1, then zeros), then `<u32 id, u64 size, data>` records; frames exactly on all 22 VST3 instances in the library.

| rec | what | evidence |
|---|---|---|
| 3 | the plugin's component state, what a `.vstpreset` holds as its `Comp` chunk | replacing it alone loads a vendor preset: ValhallaVintageVerb read back all 17 values of the preset's XML |
| 2 | the controller state; 0 bytes on iZotope, absent on the JUCE plugins | FabFilter `FFed`, Pro-Q 4 `FQ4p` with the preset name |
| 4 | FL's cache of the parameter values, u32 count first | kept as the library's; FL does not push it back over a new 3 |

Component families seen:

- JUCE: `VC2!`, u32 length, the XML, then a null and `JUCEPrivateData` (bypass). Bare in spiff, Portal, Auto-Tune Pro, AME.
- The same inside a VST2-style bank: `VstW` (16 bytes: `VstW`, BE 8, BE 1, BE 0), `CcnK` at 16 with BE size = length - 24, `FBCh`, fxID at 32 (`vee3`, `tkKr`), BE chunk size at 172 = length - 176, the chunk (the `VC2!` block) from 176. Both Valhallas, Krush, TDR Kotelnikov.
- Cableguys: `#zip#` then a zlib stream (ShaperBox 3).
- Opaque here: FabFilter `FabF` (Pro-C 2, Pro-L 2) or `FFBS` (Pro-Q 4, Saturn 2), whose `.ffp` files are `FL2p` binary or `[Preset]` text; iZotope `de8a6800` + zlib; Nexus `NEXUS5`; RC-20 `COTTDigi`; Omnisphere; PSP.

## Plugin preset files (.fst)

An FLP stream (`FLhd`, `FLdt`): 199 version, optionally 159, 28, 37, then 201 the plugin's name, 212 (52 bytes), optionally 203 and channel events, and 213 the state, in the same format as a channel's or slot's 213. Files saved by FL 10 store 201 as single-byte text, later ones as UTF-16. A wrapped VST's `.fst` has 201 `Fruity Wrapper` and the whole wrapper state in 213, and lives in `Plugin presets\<Generators|Effects>\Fruity Wrapper - <name>`. All 2346 factory and user `.fst` for the library's 27 native plugins parse and round-trip.

## FL's plugin database (Installed)

`Documents\Image-Line\FL Studio\Presets\Plugin database\Installed\<Generators|Effects>\<Fruity|VST|VST3|CLAP|New>\<name>.fst`, one per plugin FL's plugin manager scanned, each with a `.nfo` text file beside it (`ps_name`, `ps_file_filename_0` the plugin file, `ps_file_vendorname_0`, `ps_file_guid_0` for VST3, `ps_file_type_0`). `New` repeats plugins found since the last scan; a `.nfo` without an `.fst` is a DLL that is not a plugin.

- A native entry: 199, 28, 201 the plugin's name, 212. No state: FL starts the plugin at its own initial state (Sytrus at Master level 69%, not its Default preset's 100%).
- A wrapped entry (VST2, VST3, CLAP): 201 `Fruity Wrapper`, 212, 203 the name, 213 a wrapper state with no record 53: 2, 50, 54 name, 55 path, 56 vendor, and 52 the VST3 class id, 51 the VST2 id, or 58 the CLAP id. FL creates the plugin fresh from it.
- Built on a template block (its 201 and 213 replaced, 213 removed for a native), every format loaded and played.

A state event belongs after its block's 212: FL gives a 213 to the plugin the latest 212 created. A preset's 213 inserted right after 201 went to the plugin in the slot before (inferred from one case: Chorus's state reached ValhallaPlate, which then did not load).

## Diff noise between two saves (key -> key_2)

- 202 project path follows the save location.
- 237 (16 bytes) reads as two f64: first ~46295, an OLE date in late September 2026; second grew. Creation date and time spent is inferred, not confirmed.
- 233 (80-byte records, 46 in key, 0 bytes in init): one u32 per record was renumbered to 1, 2, 3... on save. Playlist clips is inferred.
  FL 26 (26.1.7) writes 88-byte records: the FL 25 record's first 72 bytes, then 8 new bytes (`00000000 ffffffff` for a
  plain pattern clip), then the last 8; read by `project.item_size`, unmapped. FL 26 also drops the song-level events
  of FL 25 (156 tempo, 9, 11, 10, 17, 23, 30, 35, 37, 44, 67, 80, 146, 167, 194, 195, 200, 202, 206, 207, 237, 231) and
  writes 172, 54, 2, 16, 192 and about 50 one-byte event 0s instead; where the tempo went is not found yet (no
  120000 u32 nor 120.0 float in the file). A project FL 26 saved reads with bpm None.
- FLEX state (213) floats moved slightly on resave, e.g. 0.09 -> 0.089996, one 0.5 -> 0.6667. Plugins re-quantize their state on reload, so a state diff is not by itself a user change.
- The Ozone slot's 212 record changed one byte at offset 16, 0x40 -> 0x41. Whether that is FL mirroring the bypass is open.

## Open

- 156 = tempo x1000, confirmed: files written with 160, 185, 88 and 132 BPM read back live as `mixer.getCurrentTempo()` 160000, 185000, 88000, 132000.
- 238 and 43 occur exactly 500 times in init: guessed playlist tracks, unconfirmed.
- 42, 49, 147, 154, 165, 166, 235, 236 occur 18 times each in init: unknown.
- 225 in init, one 6924-byte blob: unknown.
- 212: bytes 8-51 unmapped; bytes 8-11 are ff ff ff ff on Sampler/audio channels and 2 on FLEX and on effects.
- Inside a plugin's own state (wrapper record 53): Serum 2 framed above; Ozone and FLEX not started.

## Save-and-diff, first measurement

`init_serum_2_copies.flp` open in FL, driven over the bridge: Serum 2 (channel 1) host index 0 `Main Vol` set from 0.5 (display `50% [-9.0 dB]`) to 0.25 (display `25% [-21.1 dB]`), saved with FPT_Save, restored, saved again. Decoded processor state before -> after: exactly one change, `Global0/plainParams` from `"default"` to `{kParamMasterVolume: 0.0625}`. Controller state and the other Serum 2 channel unchanged. So host index 0 maps to file key `Global0/kParamMasterVolume`; 0.25 -> 0.0625 is one point and does not establish the curve.

Other events that changed across that save: 237 (as before), the 212 record of both Serum 2 channels (one span each), and the second channel's 213 in two spans while its decoded processor and controller were identical, so those bytes sit outside sections 2 and 3.

## Channels, routing, playlist and automation

| id | what | evidence |
|---|---|---|
| 64 | channel start, u16 channel index; a channel block runs from 64 to the next 64 or 99 | every file |
| 0 | the channel's on switch, one byte in its block: 0 muted, 1 playing | two channels muted in their projects read 0 (a sampler and a Vital), playing ones 1; written as 1 into a copy, FL's `channels.isChannelMuted` read False, written 0, True |
| 21 | channel type: 0 sampler, 2 plugin, 4 audio clip, 5 automation clip | a saved project: FLEX/Fruity Wrapper = 2, sample paths = 4, `Tempo`/`Gross Beat` = 5 |
| 104 | mixer track the channel feeds. FL 20 has no 104 and stores it as byte event 22 in the channel block | set live with channels.setTargetFxTrack, two FL saves differing only in routing: exactly the three 104 values changed (3->4, 7->8, 12->13). 22: FL 20.0.3 and 20.7.2 files (33, str, boring); boring's Morphine has 22 = 6 and Gross Beat sits on insert 6, str's audio clip has 1 and the effect chain is on insert 1 |
| 65 / 224 | pattern index / its notes; a pattern may carry other events between them (223, unmapped) and may have no 224 | a saved project |
| 99, 241, 36, 233, (238, 43) x500 | one arrangement: index, name, ?, playlist items, 500 tracks | init has two arrangements |
| 233 | 80-byte items: u32 start ticks, u16 0x5000, u16 pattern (0x5000+n) or channel index, u32 length ticks, u32 track counted down (track = 500 - v), bytes 16-23 note-like defaults with a flag at bit 7 of byte 19, f32 x2 trim at 24, u32 item id at 32. FL 20 writes 32-byte items: the same first 32 bytes, no item id, nothing after; the reader picks the size from the FL version (event 199), and FL 21-24 are not measured | init.flp placed by hand and confirmed by the user; FL rewrites items sorted by start and renumbers ids on save. 32 bytes: `projects/33.flp`, FL 20.0.3.532, 544 bytes = 17 items, p2 every 4 bars on track 2 to bar 68, bytes 16-31 equal to the FL 25 template's |
| 226 x3 | before the channels, present with no automation; unmapped | every file |
| 227 | one per automation clip, 20 bytes: u16 channel at 2, u32 target at 8 as FL's REC event id | REC_Tempo 0x40000005, REC_Mixer_Vol 0x70001FC0 + track<<22, plugin params 0x70008000 + (track<<22 or slot<<16) + param, channel params ch<<16; checked against midi.REC_* and mixer.getTrackPluginId in FL. FL 20 puts the mixer block at 0x20000000 instead of 0x70000000: walk.flp's two `Master - Volume` clips target 0x20001FC0; only master volume is measured, the same track and slot layout is assumed, and the writer moves such ids to 0x7 |
| 234 | automation points: 21-byte header with u32 count at 17, 24-byte points (f64 beats since previous point, f64 value, f32 tension, shape byte at 23), 112-byte tail | five clips in two projects; re-encodes byte-identical |

A pattern clip's 8 bytes at 24 are not floats but i32 start and end inside the pattern, in ticks: FL wrote (0, 2880) for a clip of 2880, (576, 5952) for one cut at both ends (jackal7r). Left at the template's -1, -1, FL plays the whole pattern whatever the clip's length: a 4-bar clip of an 8-bar pattern ran all 8 bars in a render (tallow_vigil). The writer now writes (0, length), or the clip's `trim` as ticks.

Automation clip trim is in beats (Master Volume: points to 9.65 beats, trim [0, 10.18], clip 977 ticks). Audio clip trim is in milliseconds (measured below). An untrimmed audio clip plays its whole sample whatever its length says: FL rewrote 48- and 24-tick hat clips to the sample's 50 ticks on save.

### VST2 plugin state inside the wrapper

Sylenth1 and Vital templates in init.flp: wrapper record 53 = 92-byte FL prefix, then `VstW` + BE u32 8 + BE u32 1 + BE u32 0, then an fxb bank chunk: `CcnK`, BE u32 size (bytes after these 8), `FBCh`, BE version 2, fxID (`syl1`, `Vita`), BE fxVersion, BE numPrograms, 128 reserved, BE chunkSize, chunk. The prefix's u32 at offset 84 = CcnK size + 24 (Vital init: 174900 + 24 = 174924). After the chunk FL keeps 11436 more bytes (Vital init), untouched here.

Vital's chunk is JUCE's: the synth state as JSON (same top-level keys as a `.vital` file, plus `preset_name` and `tuning`; settings a superset, 781 vs 775 keys), then 17 zero bytes and `JUCEPrivateData`. Writing a `.vital` preset's JSON in place of it, with the template's tail and the three sizes fixed, loads in FL: `Abbysun` read back live with chorus on, osc 1 level 0, unison voices 1.0 (init 0.7071, 0.0). Re-framing the init chunk unchanged is byte-identical.

Sylenth1 stores a whole bank (`FBCh`). Its chunk is `1lys` + u32 3045 + a zlib stream (level 5 reproduces it byte for byte) + 60 bytes of `JUCEPrivateData`. Decompressed (518251 bytes in the template): `1lys`, u32 3045, u32 512 programs, u32 244 parameters, u32 current program, then 512 slots of 244 f32 + a 36-byte name (1012 bytes each), then 87 bytes of XML `<ProjectData bank="{SB}\FactoryBank1.fxb"/>`. A preset `.fxp` is `FPCh`, fxID `syl1`, its chunk `1lys` + 3045 + zlib of a 1032-byte program (20-byte header, 244 f32, 36-byte name), as `scripts/sylenth1.py` decodes it. Writing a program's floats and name into slot 0 with current program 0 loads it:, `Ambient Wah SSO` showed as FL's preset name and the host parameters read back in blob order (the 244 names in `profiles/sylenth1/params.json`).

### Diva inside the wrapper

Record 53 is u32 1 then `<IQ` sections, like Serum 2's: 1 (64 bytes), 3 and 2 each u32 length + the preset text, identical, then 4 = u32 2362 + 2362 u32 (0-280, 200000-202079, 400001; a parameter-id list is a guess). The text is `#pgm=<file name>\n` + the `.h2p` file bytes verbatim, trailing NULs included. Writing a factory `.h2p` there loads it: `HS Bass Nine` read back live with Output 110, Glide 7.50/6.00, ENV2 23.5/37/37/50, LFO1 delay 23 and rate 2.40, all as in the file. FL's own preset name for it reads `Program 0`.

### Mixer effects

The mixer section after the arrangements holds one group per track, in track order (master first): `236` (12 bytes, per-track header), ten slot markers `98` = 0..9, then the track's own events (235, 165, 166, 49, 154, 147, 42). An effect is a block of events placed immediately **before its slot's marker**: `201` internal name, `212` slot record (bytes 0-3 track, 4-7 slot), `155`, `128` (colour), `41`, `213` plugin state. Pro-L 2 on master slot 4 sits between `98=3` and `98=4`.

Evidence: a project before and after a mix by hand (Pro-L 2 added on 0/4 and Fruity Reeverb 2 on 2/3 and 8/4): ids 41, 128, 155, 201, 212, 213 each +3, no other mixer records changed; counting 236 groups as track numbers gives exactly (0,4), (2,3), (8,4). Copying the three blocks onto the unmixed project reproduces them byte for byte, and FL loaded the written file with `plugins.getPluginName` reading Pro-L 2 at 0/4 and Fruity Reeverb 2 at 2/3 and 8/4.

### Mixer routing and sends

- `235` in each mixer track's group is its routing array, one byte per destination track (index 0 = master), trailing zeros left out: insert 11 routed to master is `01`; routed to master and insert 10 it is `01 00 00 00 00 00 00 00 00 00 01`.
- A send level is a `225` record with REC id `0x70000000 + src<<22 + 0x2000 + dst`, value x16000 like the faders (`mixer.getRouteToLevel`). FL stores it only when the level is not the default: a sidechain-only route is level 0 ("sidechain to this track only"); plain routes in a saved project have no record and read 0.8 live.
- Records in `225` are grouped per track, not sorted overall: the track's slot records (slot in bits 16-19), then its own (0x1FC0-0x1FE2), then its sends (0x2000 + dst). A new send goes after the last same-track record with lower low-16 bits.
- Evidence: a sidechain example (insert 11 -> 10, Fruity Limiter on 10/3 as a compressor, threshold -24.3 dB, ratio 1.7:1, release 248 ms): exactly the 235 array of track 11 and one 225 record `72c0200a` = 0 changed; live `getRouteSendActive(11, 10)` 1, `getRouteToLevel` 0.0. Rebuilding the whole mixer from the pre-edit file (nine effects + this route) reproduces every mixer track group and the 225 table byte for byte, and loads live with the route and all nine effects.

### Mixer levels

| id | what | evidence |
|---|---|---|
| 225 | mixer parameter table: 12-byte records `<IIi>` = u32 0, u32 FL REC event id, i32 value. Insert volume records carry REC_Mixer_Vol = 0x70001FC0 + track<<22, value 12800 = 0 dB, stored value / 16000 = `mixer.getTrackVolume` | a project before and after a mix by hand: exactly 11 insert records and one other changed; each stored value / 16000 matched the live `getTrackVolume` to 4 places (11663 -> 0.7289, 10651 -> 0.6657), FL's dB readout -2.06 and -3.94 |
| 225 record 0x40000000 | 12800 -> 10600 in the same mix, 8000 -> 12800 in another project's autosave after a mix by hand. Read as FL's global main volume (REC_MainVol); not confirmed live, `general` exposes no main-volume getter | the two mixed projects |
| 217 | 8 bytes, two u32: 0 and 28032 in the mixed project, absent before. 28032 ticks = 73 bars of a 72-bar song, so a playlist time selection with a bar of tail is the reading; not confirmed | the mixed project |

Other 225 ids (pan, sends, slot mix) are not measured yet.

Tempo automation value = (BPM - 60) / 120, measured in FL on auto1.flp: 100.0 BPM at 0.333, 114.74 at 5.8 beats into a 0.333 -> 0.667 ramp over 16 beats. Mixer volume: REC value 12800 = 0 dB and the clip value 0.8 = 12800 / 16000.

Audio clip trim (233 bytes 24-31) is milliseconds into the sample, as two f32: a 336-tick slice has trim [1371.43, 2571.42], a span of 1200.0 ms, which is 336/96 = 3.5 beats at 175 BPM; a 432-tick slice spans 1542.86 ms = 4.5 beats. Untrimmed is -1, -1.

## FLEX state and .flexpack

- A FLEX channel's plugin state (event 213 after the FLEX plugin-name event 201) is a fixed 2707 bytes, native, not the VST wrapper. The pack name is null-padded UTF-8 at byte 16 (field up to byte 1039), the preset name at byte 1041 (field up to byte 2064); bytes 2066-2153 are another structure, non-zero even in the init template (20 non-zero bytes), and floats from byte 2179 hold knob values. Zero-filling the preset field past 2064 wiped that structure and made FL's Flex crash on load, all three instances in one render. The init template has zeros in both name fields. Measured on a project holding Hard 808s / 808 Clean Fuzz and Synthesizer Science / Aluminium Spread against an init template.
- Writing only the two names into the init state is enough for FL to load that preset from the pack: A test rendered three channels, init, names-only and FL's saved channel; names-only against saved: spectral similarity 0.998, level 1.5 dB lower (the saved channel's own knob values); init against saved 0.028.
- `<FLEX packs folder>\<pack>.flexpack` is a big-endian archive: u32 version (2), u32 entry count, then per entry u32 name length, name (null padded), u64 offset, u64 size. Entries: one `presetsIndex.presetsIndex` (obfuscated, not needed), one `pcf.pcf`, `<preset>.flexpreset` per preset, and flac samples. The pack name is the file stem.

## Gross Beat state (event 213 of its effect block)

Decoded from two saved instances (37803 and 37875 bytes); not round-tripped, nothing writes it.

- Header 49 bytes, starting `03 00 08 00`. The two differ only at bytes 12-17 (`cf 00 00 00 00 01` / `00 01 00 00 00 01`), unidentified.
- Then 72 records, Time 1-36 then Volume 1-36: a length-prefixed ASCII name; 15 bytes (`05000000 05000000` and 7 zeros); u32 3, u32 3, u32 point count; the points; a 20-byte trailer (4 bytes, 0 or 3, then 16 of `ff`).
- A point is 24 bytes: f64 delta beats, f64 value 0-1, f32 tension, 4 bytes of shape and flags (seen `02000000`, `02000001`, `040000ff`, `05000001`, `00000002`), the layout of event 234's automation points.
- Volume 1.0 is full. For time, 1.0 is real time and `(1 - value) x 8` beats back into the buffer is the reading that fits Basic 1 (hypothesis).
- Open before writing it: which shape byte is the curve type and its codes; the header fields; the trailer's `03`; whether FL reloads a hand-edited state unchanged (save, reopen, resave, diff). Method: change one control in FL, save, diff 213.
