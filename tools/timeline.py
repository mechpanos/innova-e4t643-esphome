#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""timeline.py - what changed on the line, and when.

    python3 timeline.py <log> [HH:MM:SS]

One row every time the first 55 data bits or the tail class change. The 56th bit is
ignored: in ~1% of the frames the tail starts one tick early and covers it.
Bursts that are not frames are printed as NOT A FRAME.
"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fcwave


def rows(path, since=None):
    """[t_start, (55 bits, tail class) or None, frame count, Counter(pre-pulse), raw or None, t_end]"""
    t0 = 0
    if since: h, m, s = since.split(":"); t0 = int(h) * 3600 + int(m) * 60 + float(s)
    out = []
    for t, b in fcwave.load_bursts(path, with_time=True):
        if t is None or t < t0: continue
        p = fcwave.parse(b)
        if not p:
            if len(b) >= 20: out.append([t, None, 1, None, " ".join(("H" if v > 0 else "L") + str(round(abs(v) / fcwave.TICK)) for v in b), t])
            continue
        key = (p[1][:55], fcwave.tailkey(p[2]))
        if out and out[-1][1] == key: out[-1][2] += 1; out[-1][3][p[0]] += 1; out[-1][5] = t
        else: out.append([t, key, 1, collections.Counter({p[0]: 1}), None, t])
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit("usage: timeline.py <log> [HH:MM:SS]")
    for t, key, n, pp, raw, te in rows(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None):
        if key is None: print(" %s  NOT A FRAME: %s" % (fcwave.hhmmss(t), raw[:220])); continue
        d, tl = key
        print(" %s %6.1f s x%-5d %s  %s  [%s|%s] pre:%s  tail: %s" % (
            fcwave.hhmmss(t), te - t, n, fcwave.hexs(d + "0"), fcwave.number(d + "0"), fcwave.SPEED.get(d[24:28], d[24:28]), d[28:32],
            dict(sorted(pp.items())), "idle" if tl == fcwave.IDLE_TAIL else "KEY " + tl))
