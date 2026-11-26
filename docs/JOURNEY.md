# The journey so far

A short, honest history — including the two weeks spent analysing something that did not exist. The
dead ends are listed on purpose: they are the parts most likely to save someone else time.

## The starting point (10 November 2026)

An installation with a mix of Innova fan coils. One has the ESE645/EDA649 control with a documented
Modbus RTU port. The others have the on-board touch control **E4T643** on a board labelled `INN-FR-B20 · N276620D`,
and that board has no RS485 terminals at all — not even the footprint for the terminal block.

The only thing that leaves the board towards the user interface is a 4-wire cable on a connector marked
`COMM`. The idea: whatever the display can tell the board, an ESP32 on that cable should be able to tell it too.

## Dead end 1 — "COMM is Modbus" 

The sister controls speak Modbus, so the first guess was that the display talks Modbus to the board.
Captured with a UART and checked: **0 valid Modbus CRCs in 4,107 frames**, and no ASCII framing either.
COMM is not Modbus.

## Dead end 2 — the wrong ground

For the first twelve days the ESP32's ground was on the black wire, because black is ground. On this cable it
is not: **red is ground, black is +5 V**. A multimeter settled it on 22 November, in two independent
rounds of measurements. Everything captured before that was referenced to the supply rail.

Along the way it also turned out that the two signal wires were not on the ESP32 pins the configuration
assumed; a scan over 17 pins found where the signals really were.

## Dead end 3 — "it is a UART at 62500 baud" (the expensive one)

From the start the white wire was read with a UART, in the end at 62500 baud 8N1. It returned
clean-looking bytes: stable frames, a header, a body, a trailer. Two weeks of analysis were built on them:

- two "message types" alternating 50/50, read as a question-and-answer dialogue between two talkers,
- a header of "variable length", frames of 8 or 9 bytes,
- "20 bits change per degree of setpoint", read as an encoded or scrambled payload,
- byte "families" and a mapping table.

None of it was real.

**Phase 0 (24 November) — the first crack.** Looking at the raw order of frames instead of statistics
showed that the "dialogue" was one stream alternating between two pictures every half second: something
on the display was blinking. And the same piece of waveform appeared *shifted by a few bits* between
frames, straddling what the UART took for start and stop bits — which cannot happen with real bytes.

**Phase 1 (24 November) — measure, do not guess.** The UART was replaced by raw pulse-duration capture
with the ESP32's RMT peripheral. Result:

- an ideal 8N1 receiver run over the real waveform gets the stop bit wrong on **60%** of its bytes;
- the true structure is `pre-pulse · sync 01010101 · 56 bits · tail`, with a tick of 15.89 µs;
- a simulated UART that resynchronises on the next falling edge after a framing error reproduces
  **exactly** the bytes that had been analysed for two weeks.

With the correct alignment the two "message types" differ in **six bits**, not in every byte, and the fan
speed sits in four adjacent bits. The "encoded payload" had been produced entirely by the receiver.

The lesson, which is now a comment at the top of the capture firmware: **on an unknown bus, measure
pulses. Do not try baud rates.** A UART will happily hand you bytes from a signal that contains none.

## Phase 2 (25 November) — labels on real bits

With the owner standing at the unit and a capture running, the method was: read the line first, say what
it shows, and only then hear what the display shows.

| read from the line, said first | what the owner then reported | |
|---|---|---|
| fan speed low | "the speed is low" | ✅ |
| after one touch: auto | "it showed the new speed, auto" | ✅ |
| a different image for 20 s after the touch | "it showed the setpoint, 24, before going back to 23" | ✅ |
| after a second touch: high | "it changed to high" | ✅ |
| the display shows "23.1" | "the display shows no decimals" | ❌ |
| the tail of the "night" key will have its extra bit on tick 5 (written before looking) | it did | ✅ |

The wrong one is kept in the table deliberately. The line does carry a third digit that behaves like
tenths of a degree; the display does not show it; why is not known, and nobody here will pretend to know.

Other things that fell out of that morning:

- The parser itself had a wrong assumption baked in — "the first data bit is always 0" — true only for the
  two images of Phase 1. On 25 November it found zero frames in a perfectly good signal until it was
  re-anchored on the start of the burst.
- **Key touches are in the tail**, and they get there before the data reacts. Seven keys, seven tails.
- The fan speeds are four separate keys, not one key that cycles — an assumption that had survived
  until the four different tails appeared.
- The last bits of the frame are a linear check field, but not a plain CRC of any width from 8 to 19.
- One unexplained event: at 08:22 the line carried no frames for at least ten seconds. Five minutes
  later everything was normal. It is in the captures, and it is still unexplained.

## 25 November, later — the manual, the firmware, Home Assistant

- Cross-checking with Innova's installation manual confirmed how the heating and cooling symbols behave,
  and exposed two things the captures had not: the panel is said to have **eight** keys (seven are known),
  and no threshold is documented for the symbols — while the line shows there is one.
- Two numbers stated earlier the same day turned out wrong when measured touch by touch and were
  corrected: the mode key acts after 1.6 s (not 1.4 s), and the fan speed does not always change 0.1 s
  after the touch.
- The decoder was written as plain C++, run on a PC against 75,215 captured frames with zero differences
  from the Python reference, then flashed. On the ESP32: 31.4 frames per second, nothing rejected.
- Home Assistant discovered the device and shows the fan coil's state. **Milestone 1.**

## 25 November, evening — the eighth key, and what the yellow wire is not

One question had to be closed before trying to write: the yellow wire had only ever been looked at while
nothing was happening. If it took part in transmitting a key, a tail injected on the white wire alone
might fail for the wrong reason.

**Getting both wires at once took three attempts.**

1. Log both live: the log stream (a slow wireless link to the computer) carried 25 of the 31 white frames
   per second, then 18. The capture was useless.
2. Blame the serial port and switch it off: it got worse. That version of the explanation died; the
   bottleneck was the network path.
3. Record into the ESP32's RAM with no printing, and print afterwards at a rate the stream can carry. That
   worked: every burst numbered, none missing. It holds about 22 s — or about 4 s once the fan starts,
   which we only understood later.

**With the owner at the unit, seven recordings:**

| written down beforehand | what the line showed | |
|---|---|---|
| the on/off key will have its extra bit on tick 8: `0010 0001 0000 0000` | exactly that | ✅ |
| if yellow takes part in a key, something will appear on it that is not on white | nothing, for all eight keys | closed |

Also captured for the first time: the display going dark and the board carrying on at 31 frames a second;
the mode key held for ten seconds, where at 10.02 s both symbols light (automatic changeover), twice; and a
bit that had been "constant" in 75,215 frames changing after the unit was switched off and on.

**Then the yellow wire did something after all** — bursts several times longer, a few seconds after
some of the changes, never at the touch itself. The owner's hunch: it flares when the fan relay pulls in,
more so on the high speed. A second kind of capture (yellow alone, live, no time limit) and a seven-minute
test with the owner listening settled most of it: the wire is about fifteen times busier **for as long as
the fan motor runs**, not at the click; there are clicks only at start and stop; the texture differs
between speeds. So the hunch was right in substance and wrong in one detail, and it came from the person
who knows the appliance, not from the data.

**Mistakes made that evening, and caught:**

- A counter that reports the *mean of a minute* was read as an instantaneous value, and "the episodes last
  40–85 s" was said out loud. All that is actually known is "less than two minutes".
- "The yellow wire follows the fan speed you select" was declared dead on the strength of one recording in
  which nothing moved. In the longer test the texture does differ per speed. What that one recording means
  is still open — it is listed as a contradiction in PROTOCOL.md, not explained away.
- The burst rates of the live log were quoted before noticing that the log loses 15–20% of its lines
  exactly when the wire is busy.

**Milestone 2.** The key dictionary is complete, and the next experiment needs only the white wire.

## 26 November — the firmware catches up (milestone 2b)

The evening's findings went into the decoder: the on/off key by name, automatic changeover, bit 29 as a
value of its own instead of an "unexpected bit", and the display-off state. The last one needed a decision.
With the display off the receiver delivers each frame in two pieces, and the obvious fix — a longer idle
limit, so the frame arrives whole — would have changed how every burst is cut, away from the settings all
the captures were taken with. So the receiver stayed as it is and the decoder learned to recognise the
pair instead. It was replayed on a PC over the recordings and over every older capture before it went on
the ESP32.

The yellow wire got a use after all, a modest one: an experimental "fan running" from how busy it is. The
first replay said the fan had stopped in the middle of the test. It had not: the log stream had stalled
for a few seconds, and the rule was reading a hole in the log as a quiet wire. The rule now needs three quiet
seconds, and the lesson was already on the list below.

What is **not** known: none of the new states has been watched on the live unit yet. And in the first
minutes after the flash the heating symbol was lit while the yellow wire was quiet — the same picture as the
one recording that does not fit — with nobody there to listen.

## What was overturned — so nobody looks for it again

| claim | what overturned it |
|---|---|
| ~~COMM carries Modbus~~ | 0 of 4,107 CRCs |
| ~~red = +5 V, black = ground~~ | multimeter |
| ~~the yellow wire is a UART / a clock / Manchester~~ | per burst it is spikes and crosstalk from the white wire |
| ~~the frames are 62500 baud 8N1 bytes~~, and everything derived from the byte view | raw pulses: 60% stop-bit errors for an ideal receiver |
| ~~two talkers in a dialogue~~ / ~~two message types~~ | one picture that changes when a symbol blinks |
| ~~the payload is encoded~~ | an artefact of the UART; in real bits two images differ by 6 bits |
| ~~no checksum~~ | that test was done on UART bytes; in real bits there is a linear check field |
| ~~the first data bit is always 0~~ | true only for the first two images seen |
| ~~fan speed is one key that cycles~~ | four different tails; the owner confirms four keys |
| ~~the display shows tenths~~ | the owner sees whole degrees |
| ~~the heating symbol turns on exactly at setpoint > room~~ | with the setpoint 0.1–0.2 above the room it stayed off for 30 s |
| ~~bits 29–31 are always `010`~~ | bit 29 flips when the unit is switched on with its key, and back at the first setpoint change |
| ~~the yellow wire might take part in transmitting a key~~ | eight keys, the same activity with and without a key tail |
| ~~the yellow wire flares at the relay click~~ | it stays busy for as long as the fan runs; speed changes give no click and no flare |
| ~~the fan-speed bit changes 0.1 s after the touch~~ (as a general rule) | per key, 11 touches: auto and night at once, high and low when the finger leaves |
| ~~the tap is a 1 kΩ / 1.5 kΩ divider~~ (in these documents until 26 November) | the owner: one 10 kΩ in series per wire. The divider was a plan that was written down as if it had been built; with it falls "the line tolerated a 2.5 kΩ load" |
| ~~the serial port is why lines get lost with two raw dumps~~ | with the serial port off it was worse; the network path was the limit |

## How we work now

- **Raw pulses first.** Every capture is kept as pulse durations; every tool reads those.
- **Blind readings.** What the line says is written down before the person at the unit speaks.
- **Outcomes decided in advance.** Before an experiment, write what each possible result will mean.
- **Kill the version, not the idea.** When something fails, say which exact version failed and what is
  still open. The recurring mistake in this project was a conclusion wider than its evidence.
- **Every claim carries its evidence** — seen by eye, on the line, in the manual, or inferred.
- **Know what a number is before quoting it.** A mean over a minute is not an instant, and a log that drops
  lines under load undercounts exactly the interesting part.
- **A plan is not a record.** A drawing of what should be built is not evidence of what was built. This
  project's own hardware page described a divider that never existed, until the owner said "I do not have
  that resistor".
- **Listen to the person who lives with the appliance.** Their hunches are cheap to test and often right.
