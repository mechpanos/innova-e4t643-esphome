# Hardware — the read-only tap

What is described here is what milestone 1 was reached with: an ESP32 **listening in parallel** on the
cable between the fan coil's main board and its touch display. Nothing is cut, nothing on the board is
soldered, and the ESP32 cannot drive the line.

## Before you touch anything

- **Switch the fan coil off at the mains before opening it**, and before plugging or unplugging any
  connector. There is 230 V inside.
- **Never probe a live connector with bare wire.** The contacts of the COMM connector are about 2 mm
  apart. During this project a strand once bridged two neighbours; the display went dark until the unit
  was power-cycled. Nothing was damaged, but that was luck.
- **ESP32 pins do not tolerate 5 V.** The line is 5 V logic. Always go through the divider below.
- **Do not power the ESP32 from the COMM cable.** Use its own USB supply. The +5 V on that cable feeds the
  board logic and the display, and an ESP32 with WiFi draws peaks of several hundred milliamps.

## The cable

A 4-wire cable runs from the board connector marked `COMM` to the display. Voltages against the red
wire, measured twice with a multimeter:

| wire | voltage | role | goes to |
|---|---|---|---|
| **red** | 0 V | **ground** | ESP32 `GND` |
| **black** | +5.00 V | **+5 V** | not connected |
| **white** | +4.86 V, idles high | **data** | divider → `GPIO34` |
| **yellow** | +0.12 V, idles low | no signal of its own found | not needed |

> **Red is ground and black is +5 V on this cable — the opposite of what the colours suggest.**
> Taking black for ground cost this project about two weeks of meaningless captures. Check with a
> multimeter on your own unit before connecting anything: colours and pin order may differ.

## The tap

```
 COMM cable (board ↔ display, left connected)
     red   ─────────────────────────────── GND   (ESP32)
     white ────[ 1 kΩ ]────┬────────────── GPIO34
                           │
                        [ 1.5 kΩ ]
                           │
                          GND
```

- The divider turns 5 V into 3.0 V at the pin.
- GPIO34 is an input-only pin on the classic ESP32, with no internal pull resistors — so this ESP32
  physically cannot drive the line. The divider does load it with 2.5 kΩ to ground (2 mA while the line
  is high); this line tolerated that, with board and display working normally.
- The ESP32 measures pulse durations with its RMT peripheral (1 µs resolution). One pulse on this line
  is 15.89 µs, so there is plenty of margin.

Parts: an ESP32 dev board (`esp32dev`), a 1 kΩ and a 1.5 kΩ resistor, some wire. The connector looks like
a 4-pin JST; its pitch has not been measured (2.0 mm PH or 2.5 mm XH).

How you get onto the wires is up to you and your connector: an adapter cable is the clean way, and it is
what the next phase will use. In this project the tap was made once and then left in place while the
unit was closed again.

## Firmware

- `esphome/fancoil.yaml` — decodes the line and publishes to Home Assistant.
- `esphome/raw_capture.yaml` — only logs raw pulse durations; use it first on a unit nobody has looked at.

Both expect a `secrets.yaml` next to them (see `secrets.yaml.example`). That file is git-ignored on purpose.

## What a healthy tap looks like

- `Frames per second` ≈ **31**.
- `Unparsed bursts per minute` = 0, or very close.
- `Room temperature` agrees with the display (the display rounds to whole degrees).
- Touch a key: `Key` names it, and `Setpoint (last shown)` gets a value.

If you get bursts but no frames, check the ground first (red, not black), then whether your unit's frame
differs — in that case a raw capture is exactly what this project would like to see.

## Next phase — planned, NOT tested

To find out whether the board accepts a key sent by the ESP32, the plan is to take the **display's place**
on the COMM connector, keep reading through the same divider, and pull the white wire **low** through a
transistor and a 1 kΩ series resistor (so that, if the board actively holds the line high, the current
stays below 5 mA and the line simply does not move). The ESP32 would never drive the line high.

This is a plan. It will be documented here, with what happened, when it has been tried.
