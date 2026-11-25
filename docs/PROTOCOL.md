# The COMM link — what is known

State: 25 November 2026. Everything below comes from **one** fan coil (board `INN-FR-B20 · N276620D`,
control E4T643, display `INN-FR-DU4-A`) and from listening only. Nothing has been transmitted.

Each claim carries its evidence:

| tag | meaning |
|---|---|
| **[seen]** | the person at the unit saw it on the display while the line was being captured |
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
| yellow | +0.12 V | idles low; no signal of its own found (see §10) |

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
| 29–31 | always `010` | **[line]** |
| 32–35 | always `0000` | **[line]** |
| 36 | 0 = the digits are the **room temperature**, 1 = the **setpoint** | **[seen]** |
| 37 | always 0 | **[line]** |
| 38 | always the inverse of bit 36 | **[line]** |
| 39–54 | **check field** | **[line]** — see §7 |
| 55 | equals bit 54 in every image | **[line]** |

"Always" means: in everything captured so far. Bits that never changed have no label; they may well be
symbols that were never lit (errors, keypad lock, the display being off).

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

In 23 touches, **the tail changed first** while the 56 data bits were still unchanged, and the data
followed 3 to 7 bursts later (0.09–0.22 s) **[line]**. The changed tail lasts as long as the finger is
on the key (10–71 bursts, 0.3–2.2 s), then returns to the idle tail.

The tail written as one bit per tick (high = 1), counted from its first high pulse:

| key | ticks 1–16 | continuation | waveform after the first long low (ticks) |
|---|---|---|---|
| (idle) | `0010 0000 0000 0000` | `111111 00000` then high | `H1 L2 H1 L13 H6 L5` |
| fan **auto** | `0011 0000 0000 0000` | `11 00 1` then low | `H1 L2 H2 L12 H2 L2 H1` |
| fan **night** | `0010 1000 0000 0000` | `11 0000 1` then low | `H1 L2 H1 L1 H1 L11 H2 L4 H1` |
| fan **low** | `0010 0100 0000 0000` | `11 000 111` then low | `H1 L2 H1 L2 H1 L10 H2 L3 H3` |
| fan **high** | `0010 0010 0000 0000` | `11 000 1 0 11` then low | `H1 L2 H1 L3 H1 L9 H2 L3 H1 L1 H2` |
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
order as bits 24–27. In three touches (auto twice, night) the speed bit changed 3 bursts after the touch
began. In two (high, low) only the screen changed at that point, to the setpoint, and the speed bit changed
3 frames *after the finger left* (0.60 s and 0.42 s after the start). Five touches are not enough to tell why.

**+ and − [line].**
- With the screen on room temperature, a touch only **shows** the setpoint, 3 bursts later (4 times).
  Held for 1.33 s it still only showed it.
- With the screen already on the setpoint, a touch changes it by 1 after 7 bursts (0.22–0.23 s, 11 times).
- Held for more than 0.7 s it changes a second time, 0.5 s after the first.
- Once the setpoint changed after only 3 bursts; that touch began 0.13 s after the previous one ended.

**Mode — one key that is held [seen] + [line].** Both times it was used:

| | heating → cooling | cooling → heating |
|---|---|---|
| the symbol of the **current** mode lights steadily | 0.10 s | 0.10 s |
| the mode changes | **1.60 s** | **1.57 s** |
| finger leaves | 2.23 s | 2.11 s |

A touch shorter than 1.6 s has not been tried; it might show the current mode without changing it **[unknown]**.

**Mode held for 10 s or more — automatic changeover.** The owner reports it, and the manual describes it
(§8.2.5: both symbols light together; stated as available on 4-pipe units only) — but in the chapter of
the ECA644 control, not of the E4T643 **[manual]**. Not captured **[unknown]**.

**The eighth key is on/off.** The manual says the panel has eight capacitive keys (§9.2.1) **[manual]**, and
the panel shows them: `−`, `+`, mode, on/off, and the four fan speeds (photo in the README). Seven tails
are known; the on/off key has not been captured. A prediction written down before capturing it: the
extra `1` of the known tails falls on ticks 4, 5, 6, 7 and 9, so the eighth tail may be
`0010 0001 0000 0000` (tick 8). It may also be wrong: `+` and `−` have more than one `1`.

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
- The tail of the on/off key, the frame while the display is off, the frame in automatic changeover.
- The exact on/off thresholds of the symbols.
- What happened on 25 November at 08:22: for at least 10 s the line carried narrow pulses about every 50 µs
  and no frames at all; five minutes later it was normal. The capture is in `captures/`.
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

Idles low. Captured per burst, 72% of its bursts are shorter than 100 µs and consist of 1 µs spikes, and
the long ones have the timing of the white wire. The cheapest explanation is crosstalk into a
high-impedance input. All key touches were found on the white wire, so yellow was not pursued. What it is
for is **[unknown]**.
