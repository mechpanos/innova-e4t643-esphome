# Captures

Raw pulse durations of the COMM cable of one fan coil (board `INN-FR-B20 · N276620D`, control E4T643),
taken with an ESP32 (RMT, 1 µs resolution): the **white** wire through a 1 kΩ / 1.5 kΩ divider on GPIO34
and, in the files of the evening of 25 November, also the **yellow** wire through a second divider on GPIO35.

There are three kinds of file. Every line is an ESPHome log line and nothing else.

## 1. Raw dumps of the white wire (`remote.raw`)

```
[08:46:31.510][I][remote.raw:035]: Received Raw: -33, 17, -16, 16, -15, 17, ...
```

Positive = high, negative = low, microseconds. The timestamp is local time of day at the computer that
recorded the log. Receiver settings: `filter: 2us`, `idle: 300us` — a burst ends after 300 µs without an
edge, so one burst is one frame. ESPHome's raw dump does not print the last element of each burst (the
idle gap that ended it).

| file | when | what |
|---|---|---|
| `2026-11-24_idle.log.gz` | 24 Nov, 3 min | nobody touching anything; 5,640 frames, two images alternating (a symbol blinking) |
| `2026-11-25_0822_no_frames.log.gz` | 25 Nov 08:22, 10 s | **no frames at all**: narrow pulses about every 50 µs. Unexplained |
| `2026-11-25_keys_part1.log.gz` | 25 Nov 08:27–08:39 | 22,586 frames; two fan-speed touches |
| `2026-11-25_keys_part2.log.gz` | 25 Nov 08:39–09:03 | 46,989 frames; the full round of keys below |
| `2026-11-25_1109_fancoil_firmware.log.gz` | 25 Nov 11:09, 40 s | produced by `fancoil.yaml` itself through its "Raw pulse logging" switch |

Lines other than the raw dumps (boot messages, network details) were removed before publishing.

## 2. Memory recordings of both wires (`rec`)

Made by the button "Record to memory" of `fancoil.yaml`: the ESP32 stores every burst of both wires in RAM
and prints them afterwards. Read them with `tools/rec.py`.

```
[21:44:54.250][I][rec:351]: START 30000 ms, memory 86592 bytes (largest free block 110592), fits about 23 s
[21:45:12.430][I][rec:371]: END (MEMORY FULL) after 18149 ms: white 570 bursts, yellow 1949 bursts, 86490 bytes
[21:45:12.430][I][rec:380]: 0 Y 5202:-3,44,-5,1,-40,1,-46,2|1 W 13135:-15,17,-15,17,-15,16,-16,16,...
[21:45:43.650][I][rec:399]: DONE 2519 bursts
```

`<seq> <W|Y> <µs since the start>:values` — `W` white, `Y` yellow, lower case = continuation of the same
burst. The time is when the main loop **received** the burst (good to a few ms), not its first edge. A burst
is capped at 200 values. White: `filter: 2us`; yellow: `filter: 1us`; both `idle: 300us`.

The unit these were taken from runs a build with Greek log texts. The three header lines (`START`, `END`,
`DONE`) were rewritten into the wording of the firmware published here, numbers unchanged; the burst
lines are untouched.

| file | when | what |
|---|---|---|
| `2026-11-25_recording_idle.log.gz` | 25 Nov 15:50 | 22.4 s, nobody at the unit: 703 frames, 2,276 yellow bursts, none missing — the baseline |
| `2026-11-25_recordings_keys.log.gz` | 25 Nov 21:44–22:12 | seven recordings with the owner at the unit, listed below |

| # | started | what the owner did | length | missing |
|---|---|---|---|---|
| 1 | 21:44:54 | `+` (shows 24), `+` (25), `−` (24), fan low — memory was full before the touch on auto | 18.1 s | 0 |
| 2 | 21:52:52 | mode held 2 s (→ cooling), pause, mode held 2 s (→ heating) | 22.1 s | 34 bursts (0.26 s, at 1.8 s, before any touch) |
| 3 | 21:55:33 | on/off held 2 s (display goes dark), pause, on/off held 2 s (back on) | 23.8 s | 0 |
| 4 | 22:01:26 | fan high, fan low, fan auto | 21.9 s | 0 |
| 5 | 22:06:03 | fan night, fan auto | 15.7 s | 0 |
| 6 | 22:08:41 | mode held 10.6 s (heating → cooling → automatic changeover) | 17.9 s | 0 |
| 7 | 22:11:22 | mode held 10.7 s (automatic changeover → heating) | 19.8 s | 0 |

All seven ended because the memory was full. It fills in about 4 s once the fan motor starts (the yellow
wire gets busy), which is why recordings 1, 5, 6 and 7 are shorter.

## 3. Raw dump of the yellow wire (`remote.yellow`)

| file | when | what |
|---|---|---|
| `2026-11-25_fan_test_yellow.log.gz` | 25 Nov 22:22–22:55 | 269,993 bursts of the yellow wire, logged live through the switch "Raw yellow logging" |

Same line format as the white dumps, with the tag `remote.yellow`; load it with
`fcwave.load_bursts(path, with_time=True, tag="remote.yellow")`. The live stream lost 15–20% of its lines
while the fan was running (the on-board counter saw more bursts than arrived). The white wire was decoded
on the ESP32 at the same time; these are the key touches it reported, with the owner's notes:

| time | step | what the owner heard |
|---|---|---|
| until 22:42 | heating mode, fan auto, setpoint 23, room 23.3 — no demand | fan stopped |
| 22:42:02–05 | `+` up to **26** (heating symbol lights 22:42:09) | **two relay clicks**, fan starts |
| 22:44:04 | fan **low** | no click, fan slows down |
| 22:45:45 | fan **high** | no click, fan speeds up |
| 22:47:22 | fan **auto** | no click, fan slows down |
| 22:49:00–04 | `−` down to **22** (heating symbol goes out 22:49:08) | **one click**, fan stops |
| 22:50:53–56 | `+` up to **24** | nothing (the room was at 24 by then) |

## What was done at the unit — the ground truth

This is what the owner reported doing and seeing, in the order it was done. The line agrees with it step by step
(`python3 tools/timeline.py captures/2026-11-25_keys_part2.log.gz 08:46:00`).

**Part 1.** Idle, the display shows room temperature 23, fan speed low. One touch on a fan-speed key: the
display showed the setpoint (24) and the new speed (auto), then went back to showing 23. A second touch:
the speed changed to high.

**Part 2.** Start: idle, display shows 22, fan speed high.

1. fan speed to **low** (setpoint untouched, 24)
2. once idle again, fan speed to **night**
3. `+` once (only shows the setpoint), `+` again → **25**
4. `−` down to **23**; meanwhile the room temperature dropped to 21
5. setpoint to **21**, then **22**, then **20**
6. **mode key** → cooling; the cooling symbol started blinking (waiting for cold water)
7. setpoint up: **21, 22, 23, 24, 25**, then down to **24**
8. **mode key** → heating, fan speed to **auto**, stop

In several captures a symbol blinks: the unit wants to run and waits for hot water. On 25 November the
heat source had been switched off by the owner.

## Reproducing the numbers in the documents

```bash
python3 tools/fcwave.py   captures/2026-11-24_idle.log.gz            # 5,640 bursts, 5,640 frames, 3 images
python3 tools/keys.py     captures/2026-11-25_keys_part*.log.gz      # 7 key tails (rewrites tools/key_tails.json WITHOUT on/off, which comes from recording 3)
python3 tools/presses.py  captures/2026-11-25_keys_part*.log.gz      # 23 touches, when the data reacted
python3 tools/symbols.py  captures/2026-11-25_keys_part2.log.gz      # setpoint, room temperature, symbols
python3 tools/test_decoder.py --quiet captures/*.log.gz              # firmware decoder vs reference parser
python3 tools/rec.py      captures/2026-11-25_recordings_keys.log.gz   # the seven recordings; add --frames for every frame
```
