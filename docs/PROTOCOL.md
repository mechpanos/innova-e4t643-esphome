# The COMM link — what is known

State: 25 November 2026, evening (milestone 2). Everything below comes from **one** fan coil (board
`INN-FR-B20 · N276620D`, control E4T643, display `INN-FR-DU4-A`) and from listening only. Nothing has been
transmitted.

Each claim carries its evidence:

| tag | meaning |
|---|---|
| **[seen]** | the person at the unit saw (or heard) it while the line was being captured |
| **[line]** | it is visible in the captures (`captures/`), reproducible with the tools |
| **[manual]** | Innova's installation manual `N420927A` rev. 10 says so |
| **[inferred]** | a conclusion from timing coincidences; not confirmed by eye |
| **[unknown]** | we do not know |

---

## 1. The cable

Four wires between the board connector `COMM` and the display. Voltages measured with a multimeter
against the red wire, unit idle:

| wire | voltage | role |
|---|---|---|
| red | 0 V | **ground** |
| black | +5.00 V | **+5 V supply** to the display |
| white | +4.86 V | **data**, idles high — everything in this document |
| yellow | +0.12 V | idles low; carries no keys, follows the fan motor (see §10) |

Red is ground and black is +5 V — the opposite of the usual convention. Logic levels are 5 V.
Order across the plug: red, white, yellow, black. The cable is marked 26 AWG.

## 2. The frame

```
[pre-pulse][ sync 01010101 ][      56 data bits      ][ turnaround ][      tail      ]
  0/2/3      8 ticks          on the tick grid           ~1.6 tick     ~35 ticks, other phase
```

| quantity | value | evidence |
|---|---|---|
| tick | **15.89 µs** (62.9 kbit/s) | grid fit over 5,640 frames, residual 0.054 bit **[line]** |
| frame rate | 31.3 frames per second | **[line]** |
| data | exactly 56 bits at a fixed position after the sync | 75,215 frames parse this way **[line]** |
| edge jitter in the data | σ ≈ 0.45 µs, ≤ 0.07 tick off the grid | **[line]** |
| tail phase | +0.2 tick off the data grid | **[line]** |
| tail jitter | σ ≈ 0.85 µs, common to all edges of the tail | **[line]** |
| tail start | slips by one whole tick in ~25% of the frames | **[line]** |

**It is not a UART.** An ideal 8N1 receiver run over the real waveform gets the stop bit wrong on 60%
of its bytes. (A real UART receiver "works" anyway and produces plausible, misleading bytes — see
[JOURNEY.md](JOURNEY.md).)

The same state produces the same frame: an image captured on 24 November reappeared bit for bit on
25 November **[line]**.

The different phase and jitter of the tail say it runs from **another clock** than the 56 data bits.
The natural reading is that the board sends the data and the display answers in the tail **[inferred]**;
who electrically drives the line during each tick of the tail has not been measured **[unknown]**.

### The pre-pulse

Before the sync there is sometimes a low pulse of 2 or 3 ticks. Whether it is present depends on the
image being sent, with one frame of delay, and its width is not constant. No rule found; who produces
it is **[unknown]**. The parser simply accepts 0, 2 or 3.

## 3. The 56 data bits

Bit 0 is the first bit after the sync. **0 = lit.** Checked on 49 distinct images.
In the hex notation used by the tools, bit 0 is the most significant bit of the first byte.

| bits | meaning | evidence |
|---|---|---|
| 0–6 | **tenths** digit, 7 segments in the order `g f e d c b a` | **[line]** — see §4 |
| 7 | **heating** symbol | **[line]** + **[manual]** — see §6 |
| 8–14 | **units** digit | **[seen]** setpoints 20–25 and room temperatures 21–23 |
| 15 | always 1 | **[line]** |
| 16–22 | **tens** digit | **[seen]** |
| 23 | always 1 | **[line]** |
| 24, 25, 26, 27 | fan speed **auto, night, low, high** | **[seen]** all four |
| 28 | **cooling** symbol | **[seen]** blinking on the display while the bit toggled |
| 29 | **not constant**: 0 in everything until the unit was switched off and on with its key | **[line]** — see §12 |
| 30–31 | always `10` | **[line]** |
| 32–35 | always `0000` | **[line]** |
| 36 | 0 = the digits are the **room temperature**, 1 = the **setpoint** | **[seen]** |
| 37 | always 0 | **[line]** |
| 38 | always the inverse of bit 36 | **[line]** |
| 39–54 | **check field** | **[line]** — see §7 |
| 55 | equals bit 54 in every image | **[line]** |

"Always" means: in everything captured so far **with the display on**. Bits that never changed have no
label; they may well be symbols that were never lit (errors, keypad lock). Bit 29 was in this list until
it changed. For the display being off see §11.

**When nobody touches the panel the frame carries the room temperature, not the setpoint.** The
setpoint is on the line only for 20 s after a key touch **[seen]** **[line]**.

## 4. The digits

Standard 7-segment patterns. With `0 = lit` and bit positions `0=g 1=f 2=e 3=d 4=c 5=b 6=a` inside each
digit byte (the 8th bit of the byte is not a segment), the bytes are:

| digit | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| byte (8th bit = 0) | `80` | `F2` | `48` | `60` | `32` | `24` | `04` | `F0` | `00` | `20` |

Byte 0 = tenths, byte 1 = units, byte 2 = tens. In the units and tens bytes the 8th bit is always 1
(bits 15 and 23), so they appear as `61`, `49` and so on. Example: `32 61 49 …` reads `23.4`.

- Units and tens match what the display showed in every case that was read out loud **[seen]**.
- The first byte always decodes to a valid digit and behaves like tenths of a degree: over 30 minutes it
  walked 23.3 → 23.4 → 23.5 → … → 23.0 → 22.9 → … in steps of 0.1, and the units digit changed from 3
  to 2 at the very frame where the first byte went from 0 to 9 **[line]**. In all setpoint images it is 0.
- **The display does not show a decimal digit [seen].** What the display does with that byte is **[unknown]**.
  We deliberately do not guess.
- A fact from the manual that may or may not be related: the room probe offset is adjustable in steps of
  0.1 °C **[manual]** §9.4.1.

## 5. Key touches travel in the tail

In 38 touches (23 in the morning session, 15 in the evening one), **the tail changed first** while the
56 data bits were still unchanged **[line]**. The changed tail lasts as long as the finger is on the key
(0.3 s to 10.7 s), then returns to the idle tail. All eight keys of the panel are now in the table.

The tail written as one bit per tick (high = 1), counted from its first high pulse:

| key | ticks 1–16 | continuation | waveform after the first long low (ticks) |
|---|---|---|---|
| (idle) | `0010 0000 0000 0000` | `111111 00000` then high | `H1 L2 H1 L13 H6 L5` |
| fan **auto** | `0011 0000 0000 0000` | `11 00 1` then low | `H1 L2 H2 L12 H2 L2 H1` |
| fan **night** | `0010 1000 0000 0000` | `11 0000 1` then low | `H1 L2 H1 L1 H1 L11 H2 L4 H1` |
| fan **low** | `0010 0100 0000 0000` | `11 000 111` then low | `H1 L2 H1 L2 H1 L10 H2 L3 H3` |
| fan **high** | `0010 0010 0000 0000` | `11 000 1 0 11` then low | `H1 L2 H1 L3 H1 L9 H2 L3 H1 L1 H2` |
| **on/off** | `0010 0001 0000 0000` | `11 000 1 00 11` then low | `H1 L2 H1 L4 H1 L8 H2 L3 H1 L2 H2` |
| **mode** (heat/cool) | `0010 0000 1000 0000` | `11 000 1 000 11` then low | `H1 L2 H1 L5 H1 L7 H2 L3 H1 L3 H2` |
| **+** | `0010 0000 0101 0000` | `11 000 1 0000 1` then low | `H1 L2 H1 L6 H1 L1 H1 L4 H2 L3 H1 L4 H1` |
| **−** | `0010 0000 0011 1000` | `11 000 1` then low | `H1 L2 H1 L7 H3 L3 H2 L3 H1` |

Mean durations in microseconds for each element are in [`tools/key_tails.json`](../tools/key_tails.json).

- The tail begins with a long low period of 6 to 8 ticks (this is the part that slips); the table starts
  after it.
- "Then low": after a key tail the line stays low for at least 300 µs — the capture's idle limit, so we
  know "at least", not how long. After the idle tail it returns high at once.
- The continuation differs per key and looks like a check field. It has not been analysed.
- The names come from what the board did next and from the person pressing the keys **[seen]**.

### Key by key

**Fan speeds — four separate keys [seen] + [line].** Four different tails, in ticks 4, 5, 6, 7, the same
order as bits 24–27. When the speed bit changes depends on the key, with no exception in 11 touches:

| key | touches | the speed bit changes |
|---|---|---|
| auto, night | 6 | 0.10 s after the touch begins (3 frames) |
| high, low | 5 | 3 frames **after the finger leaves** (0.4–0.7 s after the start) |

Why the two pairs differ is **[unknown]**. With high and low, what changes at 0.10 s is only the screen,
which switches to the setpoint.

**+ and − [line].**
- With the screen on room temperature, a touch only **shows** the setpoint, 3 bursts later (5 times).
  Held for 1.33 s it still only showed it.
- With the screen already on the setpoint, a touch changes it by 1 after 7 bursts (0.22–0.23 s, 13 times).
- Held for more than 0.7 s it changes a second time, 0.5 s after the first.
- Once the setpoint changed after only 3 bursts; that touch began 0.13 s after the previous one ended.

**Mode — one key, three behaviours [seen] + [line].**

| held for | what happens | evidence |
|---|---|---|
| a moment | the symbol of the **current** mode lights at 0.10 s and goes out again; nothing changes | the owner watched it; two touches on the line |
| **1.56–1.60 s** | heating ↔ cooling | 5 changes: 1.60, 1.57, 1.56, 1.56, 1.56 s |
| **10.02 s** | automatic changeover on — or off again | 2 changes, both at 10.02 s |

- **Automatic changeover looks like both symbols lit**: bit 7 = 0 and bit 28 = 0, also once the screen is
  back on room temperature **[line]**. The manual describes exactly that (§8.2.5, in the chapter of the
  ECA644 control, stated for 4-pipe units) **[manual]**.
- Entering it from heating, the 1.56 s step happens on the way: heating → cooling at 1.56 s → both at 10.02 s.
- Leaving it, nothing happens at 1.56 s; at 10.02 s the cooling symbol goes out and heating remains. Seen
  once, so "it always returns to heating" is not established.
- After a mode change the symbol of the new mode stays lit for 4.0 s, then follows the demand (4.0 s for
  heating, 3.97 s for cooling) **[line]**.

**On/off — the eighth key [seen] + [line].** The manual says the panel has eight capacitive keys (§9.2.1)
and the panel shows them (photo in the README). Its tail was **predicted before it was captured**: the
extra `1` of the other tails fell on ticks 4, 5, 6, 7 and 9, leaving tick 8 free, so the prediction was
`0010 0001 0000 0000`. That is what came out.

| from the touch | switching off | switching on |
|---|---|---|
| 0.09 s | the screen shows the setpoint | (the display is dark) |
| **1.55 s / 1.56 s** | the image goes dark, finger still on the key | the display lights |
| finger leaves | 1.97 s | 1.97 s |

The owner's impression is that the key needs about three seconds; on the line the change came at 1.55 s
both times. Two short touches later the same evening did not change the image. The shortest hold that
works has not been measured **[unknown]**.

## 6. The heating and cooling symbols

**Cooling = bit 28 [seen].** The owner saw the cooling symbol blink while the bit toggled 0.5 s / 0.5 s.

**Heating = bit 7 [line] + [manual].** Not watched by eye during the capture. It rests on: the bit behaves
as the manual says the heating symbol does; while the mode key was held from heating bit 7 lit, from
cooling bit 28 lit; and in an earlier capture it was the only data bit toggling every 0.5 s while the
owner reported the "waiting for hot water" indication blinking.

What the manual says **[manual]**: the heating symbol is "on with setpoint higher than room temperature,
off with lower setpoint", and the cooling symbol the reverse (§8.2.5, ECA644 chapter). The symbol of the
active function flashes and ventilation stops when the water is not at a suitable temperature (§9.4.3).
No threshold or hysteresis is given anywhere.

What the line showed **[line]** ("set − room" uses the tenths digit of §4):

| mode | set − room | symbol |
|---|---|---|
| heating | +0.5 … +3.0 | heating **on** |
| heating | −0.9 | heating went **off** 4.3 s after the setpoint change |
| heating | **+0.1 and +0.2** | heating **stayed off** for 29.6 s |
| cooling | −1.8 and −0.8 | cooling **blinking** (no cold water) |
| cooling | +0.2 | cooling went **off** 4.4 s after the setpoint change |
| cooling | +1.2 … +3.2 | both off |

- This agrees with the manual except for one row: with the setpoint 0.1–0.2 above the room temperature the
  heating symbol did not come on within 30 s, although switching off had taken 4.3 s. The same holds in
  whole degrees as the display shows them: setpoint 22, display "21".
- So the switch-on threshold of heating is not at zero. With this data it lies between +0.2 and +0.5 — or
  there is hysteresis, or a switch-on delay longer than 30 s. The data cannot tell these apart.
- **When the demand is satisfied both bits are off and the frame does not reveal the selected mode.**
  A momentary touch of the mode key reveals it without changing it (§5).

The evening session added **[line]**:

| time | setpoint | room | heating symbol | what came before |
|---|---|---|---|---|
| 21:55 | 24 | 23.5 | **on** | no mode change around that time |
| 22:11–22:15 | 24 | 23.5 | **off** for four minutes | the mode had just been set to heating again |
| 22:15:36 | 25 | 23.5 | comes on, 3 s after the setpoint change | |
| 22:15:43 | 23 | 23.5 | goes off, 4 s after | |
| 22:42:09 | 26 | 23.2 | comes on, 4.1 s after | |
| 22:49:08 | 22 | 24.1 | goes off, 4.5 s after | |

- The same difference (+0.5) gave the symbol once on and once off. That points to **hysteresis**: once off,
  it needs a larger difference to come back **[inferred]**. The two thresholds are not known; the switch-on
  one is above +0.5 and not above +1.5.
- The symbol reacts 3 to 4.5 s after a setpoint change.

## 7. The check field

- Over 49 distinct images the differences have rank 18 over GF(2), and the first 37 bits alone already
  have that rank. So bits 37–55 are a **linear (XOR) function** of the bits before them **[line]**.
- It is **not a plain CRC**: every polynomial of width 8 to 19 was tried, with the field ending at bit 53,
  54 or 55 and both bit orders for data and check — no solution.
- For reading it is not needed (the board repeats each image 31 times a second; the firmware accepts an
  image after three identical frames). It would only matter for sending a frame to the display ourselves.

If you recognise it, please open an issue. The 49 images can be regenerated from the captures.

## 8. Things we do not know

- Whether the board **accepts** a tail sent by something other than the display. This is the whole next phase.
- Who drives the line electrically during the tail, and whether the line is open-drain with a pull-up.
- The rule of the check field, of the tail continuation and of the pre-pulse.
- What bit 29 shows on the display (§12).
- The two images around switching the display off and on that the parser does not read (§11).
- The on and off thresholds of the symbols, and the shortest hold of the on/off key.
- Why the high and low keys act on release while auto and night act at once.
- What happened on 25 November at 08:22: for at least 10 s the line carried narrow pulses about every 50 µs
  and no frames at all; five minutes later it was normal. The capture is in `captures/`.
- Isolated frames with a cut-off tail (`H1 L2 H1 L2 H1`, then silence) about once a second around the
  on/off test, and for four minutes after it; none in the other recordings.
- Whether any of this is identical on a second unit.

## 9. What the display board looks like

From a photo of the rear of the display board (`INN-FR-DU4-A`, PCB marked `lae ELECTRONIC A245_1`) — see
[HARDWARE.md](HARDWARE.md). These are observations of a photo; nothing was probed.

- Two ICs marked `HC595` (8-bit shift registers), with eight 220 Ω resistors leading to **eight** pads of
  the LED module, and four small transistors next to its other **four** pads. So the LED module has 12
  connections, which is what a multiplexed display with 4 commons × 8 segments needs.
- A third IC sits among the tracks that fan out to the touch areas, and connects to the shift registers.
  Its marking is not readable in the photo.
- So the display side has logic of its own. That fits the tail having a different clock than the 56 data
  bits (§2), and it is where a reply carrying the touched key would have to come from **[inferred]**.
- The first four bytes of the frame hold exactly 32 lit/unlit positions (three digit bytes and the byte
  with the fan speeds and the cooling symbol). 4 × 8 = 32 would match the 12 connections of the LED
  module one to one. **Not verified** — it is arithmetic on a photo, not a measurement.

## 10. The yellow wire

Idles low. It was captured together with the white wire in eight memory recordings and then on its own,
continuously, for half an hour (`captures/`, 25 November). Through a divider into a digital input, so
what we have is when it crosses a threshold, not its waveform.

**It does not carry the keys [line].** Activity of the yellow wire per frame of the white wire (sum of the
durations of its bursts, median), in frames whose tail carries a key and in idle frames within ±2 s:

| key | frames with the key tail | with key | idle around |
|---|---|---|---|
| `+` | 23 | 491 µs | 486 µs |
| `−` | 14 | 354 µs | 460 µs |
| mode | 118 | 488 µs | 444 µs |
| on/off | 41 | 502 µs | 446 µs |
| fan high | 16 | 460 µs | 494 µs |
| fan low | 22 | 532 µs | 526 µs |
| fan auto | 17 + 12 | 524 and 455 µs | 512 and 492 µs |
| fan night | 9 | 496 µs | 491 µs |
| mode, held 10 s | 314 + 303 | 522 and 523 µs | 490 and 449 µs |

So the exchange between board and display — the picture one way, the key the other — is on the white
wire alone, as far as key touches go.

**At rest it ticks with the mains [line].** Bursts of about 100 µs every 10.0 ms (2,001 of 2,275 gaps),
which is twice the 50 Hz mains frequency, and not synchronous with the 32 ms frames. Only a small excess
coincides with the frames (crosstalk from the white wire).

**It gets much busier while the fan motor runs [line] + [seen].** A seven-minute test with the owner
listening at the unit (steps about 90 s apart, yellow logged continuously):

| step | what the owner heard | bursts per second (on-board counter, mean of a minute) | median burst length |
|---|---|---|---|
| before: no demand, fan stopped | — | 104 | 85 µs |
| setpoint raised to 26, fan on auto | **2 relay clicks**, fan starts | ~305 | 516 µs |
| fan low | no click, fan slows | ~283 | 758 µs |
| fan high | no click, fan speeds up | 360–396 (minutes shared with a neighbouring step) | 354 µs |
| fan auto | no click, fan slows | ~315 | 404 µs |
| setpoint lowered to 22 | **1 click**, fan stops | 104 | 79 µs |

- It rises 3 s after the heating symbol lights and drops in the same second the symbol goes out.
- Speed changes cause no gap and no spike; the texture changes (more, shorter bursts on high).
- While the fan runs the bursts have a regular texture: spikes every 48–50 µs, with 150 µs gaps.
- Total activity is roughly fifteen times the resting level (the live log lost 15–20% of its lines in that
  state, so the per-burst numbers from it are lower bounds; the counter runs on the ESP32).

**What it probably is [inferred].** Noise coupled from the fan-motor circuit into this wire, synchronous
with the mains — not data. A digital input cannot prove that; an oscilloscope would. What the wire is
*for* remains **[unknown]**.

**What does not fit yet.** In five of the memory recordings the same busy texture appeared for well under
two minutes, a few seconds after something changed (setpoint, switching on, mode), and nobody noted the fan
at those moments. And in one recording the image showed fan **high** for 7.5 s with the heating symbol lit
while yellow stayed at rest — either the fan was not turning then, or "busy = fan running" is incomplete.

**A third time, without a witness.** On 26 November, a few minutes past midnight, the heating symbol was lit
(setpoint 24, room 23.2) while yellow was at rest: 103 bursts and 23 ms of activity per second. Nobody was at
the unit to say whether the fan was turning.

**The firmware's guess.** `fancoil.yaml` publishes "Fan running (experimental)": the summed length of the
yellow bursts over each second, running when it is at least 100 ms for two seconds in a row, stopped when it
is at most 50 ms for three (at the start of the test above the seconds read 69, 98, 213 ms; at rest 17–30).
Replayed over the half-hour capture (skipping the three seconds in which the log itself delivered no lines) it
says "running" at 22:42:15 and "stopped" at 22:49:11, three seconds after the rise and the drop on the wire,
and nothing in between. It rests on one unit and one evening, and on the open question above; treat it as a
hint, not as a state.

**The resting level is not constant.** With the fan stopped the median burst length was 57–87 µs with the
screen on room temperature, 186–209 µs while it showed the setpoint, 130–140 µs earlier the same evening,
and 43 µs with the display off. Only the big jump (burst rate and total activity) is a reliable sign.

## 11. While the display is off

- **The board keeps sending, 31 frames per second [line].** The receiver splits each frame into two bursts,
  because in between the line stays at one level for longer than its 300 µs idle limit: a short one,
  `L1 H1 L1 H1 L1 H1`, and 2–3 ms later (by receive time) a long one, `L7 H2 L3 H2 L1 H3 L2 H6 L7` followed by
  the tail.
- **If the long burst starts at bit 31 [inferred]**, bits 0–30 are all 1 — nothing lit — and the rest reads
  `0 000000 11 000 11 0 111 00 11111`: bit 31 = 0, bits 32–35 = `0000`, 36 = 0, 37 = 0, 38 = 1, 55 = 54, as in
  §3. In favour: the burst is 26 ticks long, which is bits 31–55 plus the one extra tick a normal frame also
  has, and it starts with seven zeros like bits 31–37. But the length of the constant level was **not
  measured**: the receiver sees it as a gap between two bursts.
- **The display keeps answering in the tail [line].** The second touch of the on/off key is visible as the
  on/off tail in every frame while the display is dark.
- For the first 0.47 s after switching off (15 frames) the long burst is different,
  `L5 H1 L3 H1 L2 H2 L1 H3 L2 H2 L3 H2`. Not decoded.
- At switch-on, 13 frames (0.48 s) carry an image the parser rejects (54 ticks of data instead of 57):
  `L2 H1 L1 H1 L1 H1 L1 H1 L4 H1 L2 H1 L1 H1 L1 H2 L4 H1 L1 H1 L2 H1 L2 H8 L7 H1 L1 H1 L3 H3 L7 H3 L7`.
  It is not the known digits. What the display shows in that half second was not noted **[unknown]**.
- **How the firmware uses this.** A burst that looks like the short one, followed within 15 ms by one that
  looks like the long one, counts as one display-off frame; three such pairs in a row publish "unit off", and
  three identical normal frames publish "on" again. The receiver settings are unchanged. Run over the
  recordings on a PC, "off" comes 0.07 s after the line goes dark and "on" 0.06 s after it returns; in the
  75,215 frames of the other captures it never says "off". While off, a key is accepted only if its tail is
  one of the eight known ones, because the position of the tail in the long burst is an estimate.
  **Not yet seen working on the live unit.**

## 12. Bit 29

It was 0 in every image up to the evening of 25 November — 75,215 frames — and was listed as constant. Then **[line]**:

| time | what happened | bit 29 |
|---|---|---|
| 21:55:52 | first image after switching on with the on/off key | 0 → **1** |
| 21:55–22:15 | fan-speed changes, mode changes, automatic changeover, a first `+` that only shows the setpoint | stays 1 |
| 22:15:33 | the image in which the setpoint changes 24 → 25 | 1 → **0** |
| 22:17:33 | after holding the on/off key again | 0 → **1** |
| 22:42:03 | the image in which the setpoint changes 23 → 24 | 1 → **0** |

- **The rule as observed, twice each way:** it becomes 1 when the unit is switched on with its key, and returns
  to 0 at the first change of the setpoint.
- With "0 = lit" something would be missing from the display between switching on and the first setpoint
  change. The owner could not identify it **[unknown]**.
