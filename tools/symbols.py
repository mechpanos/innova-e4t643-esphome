#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""symbols.py - setpoint, room temperature and the two symbols (bit 7 heating, bit 28 cooling) over time.

    python3 symbols.py <log> [<log> ...]

One row every time setpoint, room temperature or a symbol changes. The setpoint is the last
one shown (bit 36 = 1); the room temperature is the last frame with bit 36 = 0. Also marks
the start and end of the mode key.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fcwave, timeline

MODE_TAIL = "H1 L2 H1 L5 H1 L7 H2 L3 H1 L3 H2"
if len(sys.argv) < 2: sys.exit("usage: symbols.py <log> [<log> ...]")
sp = room = last = modekey = None
for path in sys.argv[1:]:
    print("==", os.path.basename(path))
    for t, key, n, pp, raw, te in timeline.rows(path):
        if key is None: continue
        d, tl = key
        if tl.startswith(MODE_TAIL):
            if modekey is None: modekey = t; print(" %s  mode key touched" % fcwave.hhmmss(t))
            mk_end = te
        elif modekey is not None and tl == fcwave.IDLE_TAIL:
            print(" %s  mode key released (%.2f s)" % (fcwave.hhmmss(mk_end), mk_end - modekey)); modekey = None
        try: v = float(fcwave.number(d + "0"))
        except ValueError: continue
        if d[36] == "1": sp = v
        else: room = v
        st = (sp, room, d[7], d[28])
        if st != last:
            diff = (sp - room) if (sp is not None and room is not None) else None
            print(" %s  setpoint %s  room %s  set-room %s   heat(bit7)=%s  cool(bit28)=%s  %s" % (
                fcwave.hhmmss(t), sp, room, "%+.1f" % diff if diff is not None else "  ? ", "LIT" if d[7] == "0" else "off",
                "LIT" if d[28] == "0" else "off", "[screen shows setpoint]" if d[36] == "1" else ""))
        last = st
