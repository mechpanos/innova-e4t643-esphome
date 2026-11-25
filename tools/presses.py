#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""presses.py - every key touch: how long its tail lasted and when the 56 data bits changed.

    python3 presses.py <log> [<log> ...]

The key is recognised from key_tails.json. A touch = consecutive bursts with a key tail,
until 3 consecutive frames with the idle tail. Times count from the first burst with the key tail.
"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fcwave

K = json.load(open(os.path.join(HERE, "key_tails.json"), encoding="utf-8"))
shape2name = {v["shape"]: k for k, v in K.items()}


def name(tl):
    for s, n in shape2name.items():
        if tl.startswith(s): return n
    return None


if len(sys.argv) < 2: sys.exit("usage: presses.py <log> [<log> ...]")
for path in sys.argv[1:]:
    cur = None; gap = 0
    for t, b in fcwave.load_bursts(path, with_time=True):
        p = fcwave.parse(b)
        n = name(fcwave.tailkey(p[2])) if p else None
        if p and fcwave.tailkey(p[2]) == fcwave.IDLE_TAIL:
            if cur:
                gap += 1
                if gap >= 3:
                    print(" %s  %-17s finger %.2f s (%d bursts), first data change after %s, changes at: %s" % (
                        fcwave.hhmmss(cur["t0"]), cur["n"], cur["t1"] - cur["t0"], cur["cnt"],
                        "%.2f s (%d bursts)" % cur["first"] if cur["first"] else "-", "  ".join("%.2fs" % x for x in cur["chg"])))
                    cur = None
            continue
        if n:
            if cur is None: cur = dict(t0=t, n=n, cnt=0, first=None, chg=[], last=p[1][:55])
            gap = 0
        if cur:
            cur["cnt"] += 1; cur["t1"] = t
            if p and p[1][:55] != cur["last"]:
                if cur["first"] is None: cur["first"] = (t - cur["t0"], cur["cnt"] - 1)
                cur["chg"].append(t - cur["t0"]); cur["last"] = p[1][:55]
