# Captures

Raw pulse durations of the **white COMM wire** of one fan coil (board `INN-FR-B20 · N276620D`, control
E4T643), taken with an ESP32 (RMT, 1 µs resolution) through a 1 kΩ / 1.5 kΩ divider on GPIO34.

Each line is an ESPHome log line and nothing else:

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
python3 tools/keys.py     captures/2026-11-25_keys_part*.log.gz      # the 7 key tails (rewrites tools/key_tails.json)
python3 tools/presses.py  captures/2026-11-25_keys_part*.log.gz      # 23 touches, when the data reacted
python3 tools/symbols.py  captures/2026-11-25_keys_part2.log.gz      # setpoint, room temperature, symbols
python3 tools/test_decoder.py --quiet captures/*.log.gz              # firmware decoder vs reference parser
```
