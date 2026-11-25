#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""live.py - what the line says in the last 4 seconds of a (possibly still growing) log.

    python3 live.py <log>
"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fcwave

if len(sys.argv) < 2: sys.exit("usage: live.py <log>")
B = [(t, fcwave.parse(b)) for t, b in fcwave.load_bursts(sys.argv[1], with_time=True)]
B = [(t, p) for t, p in B if p and t]
if not B: sys.exit("no frames yet")
print("%d frames, %s ... %s" % (len(B), fcwave.hhmmss(B[0][0]), fcwave.hhmmss(B[-1][0])))
last = [p for t, p in B if t >= B[-1][0] - 4]
print("\nLAST 4 s (%d frames):" % len(last))
for d, n in collections.Counter(p[1] for p in last).most_common(4):
    print("  x%-4d %s    shows %s   fan %-6s  screen: %s   heat symbol: %s   cool symbol: %s" % (
        n, fcwave.hexs(d), fcwave.number(d), fcwave.SPEED.get(d[24:28], "?(%s)" % d[24:28]),
        "setpoint" if d[36] == "1" else "room", "lit" if d[7] == "0" else "off", "lit" if d[28] == "0" else "off"))
print("  tail:      " + "   ".join("%s x%d" % kv for kv in collections.Counter(fcwave.tailkey(p[2]) for p in last).most_common(3)))
print("  pre-pulse: " + "  ".join("%d ticks x%d" % kv for kv in sorted(collections.Counter(p[0] for p in last).items())))
