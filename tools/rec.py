#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rec.py - reads the MEMORY RECORDINGS of fancoil.yaml (button "Record to memory (up to 30 s)", log tag "rec").

    python3 rec.py <log>            # a summary of every recording found in the file
    python3 rec.py <log> --frames   # also one frame of the white wire per line, with the yellow bursts next to it

For a recording the ESP32 writes every burst of the white wire (W) and of the yellow wire (Y) into RAM, with the
time its main loop received it (us from the start), and prints them when it is over:
    [rec]: START 30000 ms, memory N bytes ...
    [rec]: END (...) ...: white A bursts, yellow B bursts, ...
    [rec]: <seq> <W|Y> <us>:v,v,v|<seq> <Y> <us>:v,v,...     (several bursts per line; lower case w/y = continuation)
    [rec]: DONE M bursts
The time is when the loop RECEIVED the burst, not its first edge: good to a few ms. That is enough to tell which
yellow bursts belong to which frame of the white wire (frames are 32 ms apart), not to compare edge against edge.
A burst is capped at 200 values.
"""
import sys, os, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fcwave

LINE = re.compile(r"\[rec:\d+\]: (.*)$")
BURST = re.compile(r"^(\d+) ([WYwy]) (\d+):(.*)$")


def load(path):
    """List of recordings; each: dict(start=..., end=..., done=..., bursts=[(seq, 'W'|'Y', t_us, [values])], claimed=(white, yellow))."""
    recs, cur = [], None
    for ln in fcwave._open(path):
        m = LINE.search(ln.rstrip("\n"))
        if not m: continue
        body = m.group(1)
        if body.startswith("START"):
            cur = dict(start=body, end=None, done=None, bursts=[], claimed=None); recs.append(cur); continue
        if cur is None: continue
        if body.startswith("END"):
            cur["end"] = body
            c = re.search(r"white (\d+) bursts, yellow (\d+) bursts", body)
            if c: cur["claimed"] = (int(c.group(1)), int(c.group(2)))
            continue
        if body.startswith("DONE"): cur["done"] = body; continue
        for part in body.split("|"):            # several bursts per line
            b = BURST.match(part)
            if not b: continue
            seq, ch, t, vals = int(b.group(1)), b.group(2), int(b.group(3)), [int(x) for x in b.group(4).split(",") if x.strip()]
            if ch in "wy":
                if cur["bursts"] and cur["bursts"][-1][0] == seq: cur["bursts"][-1][3].extend(vals)
            else: cur["bursts"].append((seq, ch, t, vals))
    return recs


def frames(rec):
    """Every frame of the white wire with the yellow bursts received closer to it than to any other frame."""
    W = [(t, v) for s, ch, t, v in rec["bursts"] if ch == "W"]
    Y = [(t, v) for s, ch, t, v in rec["bursts"] if ch == "Y"]
    out = [dict(t=t, raw=v, p=fcwave.parse(v), y=[]) for t, v in W]
    if not out: return out
    k = 0
    for t, v in Y:
        while k + 1 < len(out) and abs(out[k + 1]["t"] - t) <= abs(out[k]["t"] - t): k += 1
        out[k]["y"].append((t - out[k]["t"], v))
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit("usage: rec.py <log> [--frames]")
    for i, r in enumerate(load(sys.argv[1]), 1):
        B = r["bursts"]; nw = sum(ch == "W" for _, ch, _, _ in B); ny = len(B) - nw
        seqs = [s for s, _, _, _ in B]; missing = (seqs[-1] + 1 - len(set(seqs))) if seqs else 0
        dur = (B[-1][2] - B[0][2]) / 1e6 if len(B) > 1 else 0
        print("RECORDING %d: %s" % (i, r["start"]))
        print("  %s" % r["end"]); print("  %s" % r["done"])
        print("  arrived: white %d, yellow %d bursts in %.2f s (%.1f and %.1f per s) - the ESP32 said: %s - missing: %d" % (
            nw, ny, dur, nw / dur if dur else 0, ny / dur if dur else 0, r["claimed"], missing))
        F = frames(r); ok = [f for f in F if f["p"]]
        print("  frames on the white wire: %d of %d bursts" % (len(ok), len(F)))
        keys = collections.Counter(fcwave.tailkey(f["p"][2]) for f in ok)
        print("  tails: " + "  ".join("%s x%d" % ("idle" if k == fcwave.IDLE_TAIL else k, n) for k, n in keys.most_common(5)))
        print("  yellow bursts per frame: " + "  ".join("%d->%d" % kv for kv in sorted(collections.Counter(len(f["y"]) for f in F).items())))
        if "--frames" in sys.argv:
            for f in F:
                p = f["p"]
                print("   %8.1f ms  %s  %-22s  yellow: %s" % (f["t"] / 1000.0, fcwave.hexs(p[1]) if p else "NOT A FRAME", ("idle" if fcwave.tailkey(p[2]) == fcwave.IDLE_TAIL else fcwave.tailkey(p[2])[:22]) if p else "",
                      " | ".join("%+.1fms:%s" % (dt / 1000.0, ",".join(map(str, v[:14])) + ("..." if len(v) > 14 else "")) for dt, v in f["y"])))
