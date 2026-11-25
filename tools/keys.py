#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""keys.py - the tail dictionary: which tail appears while each key is touched.

    python3 keys.py <log> [<log> ...]

Groups the frames whose tail is not the idle one by the 16 tick-bits that follow the
first high pulse of the tail. For each group it prints the tail in ticks, how many frames
and touches (a gap > 0.3 s starts a new touch), and the mean duration of every element in
microseconds (enough to reproduce the waveform). Writes key_tails.json next to itself.

The names come from what the board did next and from the person pressing the keys.
"""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fcwave
T = fcwave.TICK
NAMES = {
    "0011000000000000": "fan auto", "0010100000000000": "fan night", "0010010000000000": "fan low",
    "0010001000000000": "fan high", "0010000010000000": "mode (heat/cool)", "0010000001010000": "+", "0010000000111000": "-",
    "0010000000000000": "(idle)"}


def tail_elems(b):
    """The elements of a burst from the first high pulse of the tail onwards (raw us)."""
    p = fcwave.parse(b)
    if not p: return None
    tot = 0; start = (p[0] + 1 if p[0] else 0) + 8 + fcwave.NDATA      # ticks up to the end of the data
    for k, v in enumerate(b):
        tot += abs(v) / T
        if tot > start + 0.5 and v < 0 and abs(v) / T >= 4.5: return b[k + 1:]
    return None


def bits(el, n=16, skip=1):
    s = ""
    for v in el: s += ("1" if v > 0 else "0") * int(round(abs(v) / T))
    return s[skip:skip + n], s[skip + n:]


if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit("usage: keys.py <log> [<log> ...]")
    G = collections.OrderedDict()
    for path in sys.argv[1:]:
        for t, b in fcwave.load_bursts(path, with_time=True):
            el = tail_elems(b)
            if not el: continue
            a, rest = bits(el)
            if len(a) < 16: continue
            if a == "0010000000000000" and rest.startswith("11111100000"): continue      # idle
            g = G.setdefault(a, dict(n=0, times=[], rest=collections.Counter(), raw=collections.defaultdict(list), shape=collections.Counter()))
            g["n"] += 1; g["times"].append(t); g["rest"][rest[:14]] += 1
            shape = tuple(("H" if v > 0 else "L") + str(int(round(abs(v) / T))) for v in el)
            g["shape"][shape] += 1; g["raw"][shape].append(el)
    out = {}
    for a, g in G.items():
        if g["n"] < 5: continue          # single-frame capture artefacts
        touches = [g["times"][0]]
        for x, y in zip(g["times"], g["times"][1:]):
            if y - x > 0.3: touches.append(y)
        shape, cnt = g["shape"].most_common(1)[0]
        raws = g["raw"][shape]; avg = [round(sum(abs(r[i]) for r in raws) / len(raws), 1) for i in range(len(shape))]
        print("%-18s ticks 1-16: %s %s   continuation: %s" % (NAMES.get(a, "?"), a[:8], a[8:], g["rest"].most_common(1)[0][0]))
        print("    tail: %s   (%d frames, %d touches: %s)" % (" ".join(shape), g["n"], len(touches), " ".join(fcwave.hhmmss(t) for t in touches[:12])))
        print("    us:   %s" % " ".join(("+" if s[0] == "H" else "-") + str(v) for s, v in zip(shape, avg)))
        out[NAMES.get(a, a)] = dict(bits=a, shape=" ".join(shape), us=[(v if s[0] == "H" else -v) for s, v in zip(shape, avg)], frames=g["n"], touches=len(touches))
    json.dump(out, open(os.path.join(HERE, "key_tails.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
