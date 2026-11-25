#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fcwave.py - canonical frame parser, from raw pulse durations (ESP32 RMT).

FRAME STRUCTURE on the white COMM wire, as measured (see docs/PROTOCOL.md):

   [pre-pulse 0/2/3 ticks][sync 01010101][ 56 data bits ][ tail ]
                                           on the grid     other phase

  * tick = 15.89 us
  * NOT 8N1 bytes: an ideal UART receiver gets 60% stop-bit errors on it
  * the 56 data bits sit on the tick grid (edge jitter sigma ~0.45 us)
  * the tail is +0.2 tick off the grid, has twice the jitter, and its start slips
    by one whole tick in ~25% of the frames -> a different clock

Input is an ESPHome log containing `remote_receiver` raw dumps ("Received Raw: ...").
Positive values are high, negative are low, in microseconds. Plain or .gz.
"""
import re, collections, gzip
TICK, NDATA = 15.89, 56


def _open(path):
    return gzip.open(path, "rt", encoding="utf-8", errors="replace") if path.endswith(".gz") else open(path, encoding="utf-8", errors="replace")


def load_bursts(path, with_time=False, tag="remote.raw"):
    """Bursts from a log. with_time=True -> (seconds since midnight or None, [durations]).
    tag="remote.raw" is the white wire (default); tag="remote.yellow" the yellow wire (fancoil.yaml, "Raw yellow logging")."""
    TS = re.compile(r"^\[(\d\d):(\d\d):(\d\d)\.(\d+)\]")
    out, cur, ct = [], None, None
    for ln in _open(path):
        if "[" + tag + ":" not in ln: continue
        body = ln.split("]:", 1)[1]
        if "Received Raw:" in body:
            if cur: out.append((ct, cur) if with_time else cur)
            m = TS.match(ln)
            ct = (int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + int(m.group(4)) / 1000.0) if m else None
            cur = []; body = body.replace("Received Raw:", "")
        if cur is not None: cur += [int(x) for x in re.findall(r"-?\d+", body)]
    if cur: out.append((ct, cur) if with_time else cur)
    return out


def parse(b):
    """Burst -> (pre-pulse in ticks, 56 data bits as a '0'/'1' string, tail as intervals in ticks) or None."""
    if not (900 <= sum(abs(x) for x in b) <= 2200) or b[0] > 0: return None
    edges, t = [0.0], 0.0
    for x in b: t += abs(x); edges.append(t)
    # ANCHOR AT THE START OF THE BURST.
    # A burst starts either directly with the sync L1 H1 L1 H1 L1 H1 L1 H1, or with a
    # pre-pulse "L2 or L3, H1" followed by the sync. Data starts 8 ticks after the sync start.
    # When data bit 0 is 1, the last "1" of the sync merges with it into one longer high
    # pulse, so the 8th element is only checked as "at least one tick".
    one = lambda d: 0.6 * TICK <= d <= 1.45 * TICK
    if len(b) < 20: return None
    if one(abs(b[0])): start, pre = 0, 0
    elif 1.55 * TICK <= abs(b[0]) <= 3.5 * TICK and one(abs(b[1])): start, pre = 2, int(round(abs(b[0]) / TICK))
    else: return None
    if not all(one(abs(b[k])) for k in range(start, start + 7)): return None
    last = abs(b[start + 7])
    if last < 0.6 * TICK: return None
    t0 = edges[start + 8] if one(last) else edges[start + 7] + TICK
    # length check: ~37 ticks remain after the 56 bits when idle. While a key is touched
    # the tail changes and the capture ends earlier or later (31 to 45 ticks seen).
    if not (24 <= (edges[-1] - t0) / TICK - NDATA <= 48): return None
    bits = ["1"] * NDATA
    i = start + 7
    while i < len(b):
        a = int(round((edges[i] - t0) / TICK)); e = int(round((edges[i + 1] - t0) / TICK))
        if a >= NDATA: break
        if b[i] < 0:
            for k in range(max(a, 0), min(NDATA, e)): bits[k] = "0"
        i += 1
    data_end = t0 + NDATA * TICK
    tail = []
    for k in range(i, len(b)):
        s, e = max(edges[k], data_end - 2 * TICK), edges[k + 1]
        if e > s: tail.append(("H" if b[k] > 0 else "L") + "%.1f" % ((e - s) / TICK))
    return pre, "".join(bits), tail


IDLE_TAIL = "H1 L2 H1 L13 H6 L5"


def tailkey(tail):
    """The tail in whole ticks, AFTER its first long low period (which slips between 6 and 8 ticks)."""
    full = " ".join(y[0] + str(int(round(float(y[1:])))) for y in tail)
    if full.endswith("H1 L13 H6 L5") or full.endswith("H1 L12 H6 L5") or full.endswith("H1 L14 H6 L5"): return IDLE_TAIL
    for k, x in enumerate(tail):
        if x[0] == "L" and float(x[1:]) >= 4.5:
            return " ".join(y[0] + str(int(round(float(y[1:])))) for y in tail[k + 1:])
    return "?" + " ".join(y[0] + str(int(round(float(y[1:])))) for y in tail)


def tail_bits(b, p):
    """The tail as the tools classify it: 'idle', the 16 tick-bits after its first high pulse, or '-'."""
    if tailkey(p[2]) == IDLE_TAIL: return "idle"
    tot = 0; start = (p[0] + 1 if p[0] else 0) + 8 + NDATA
    for k, v in enumerate(b):
        tot += abs(v) / TICK
        if tot > start + 0.5 and v < 0 and abs(v) / TICK >= 4.5:
            s = "".join(("1" if x > 0 else "0") * int(round(abs(x) / TICK)) for x in b[k + 1:])
            a, rest = s[1:17], s[17:]
            if len(a) < 16: return "-"
            if a == "0010000000000000" and rest.startswith("11111100000"): return "idle"
            return a
    return "-"


# 7-SEGMENT DIGITS: 0 = lit. Bit positions (first bit on the wire first) inside each digit byte:
#   0=g 1=f 2=e 3=d 4=c 5=b 6=a, 7 = not a digit segment
# Order in the frame: byte 0 = tenths, byte 1 = units, byte 2 = tens.
_DIG = {frozenset((1, 2, 3, 4, 5, 6)): "0", frozenset((4, 5)): "1", frozenset((0, 2, 3, 5, 6)): "2", frozenset((0, 3, 4, 5, 6)): "3",
        frozenset((0, 1, 4, 5)): "4", frozenset((0, 1, 3, 4, 6)): "5", frozenset((0, 1, 2, 3, 4, 6)): "6", frozenset((4, 5, 6)): "7",
        frozenset((0, 1, 2, 3, 4, 5, 6)): "8", frozenset((0, 1, 3, 4, 5, 6)): "9", frozenset(): " "}
SPEED = {"0111": "auto", "1011": "night", "1101": "low", "1110": "high"}


def digit(b8): return _DIG.get(frozenset(i for i in range(7) if b8[i] == "0"), "?")
def number(bits): return digit(bits[16:24]) + digit(bits[8:16]) + "." + digit(bits[0:8])
def hexs(bits): return " ".join("%02X" % int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))
def hhmmss(t): return "%02d:%02d:%05.2f" % (t // 3600, (t % 3600) // 60, t % 60)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2: sys.exit("usage: fcwave.py <log>")
    P = [parse(b) for b in load_bursts(sys.argv[1])]
    ok = [p for p in P if p]
    print("%d bursts, %d parsed as frames (%.1f%%)" % (len(P), len(ok), 100.0 * len(ok) / max(len(P), 1)))
    D = collections.Counter(p[1] for p in ok)
    print("\n56 DATA BITS - %d distinct images:" % len(D))
    for d, n in D.most_common(8):
        print("  x%-5d %s   %s deg   fan %s" % (n, hexs(d), number(d), SPEED.get(d[24:28], d[24:28])))
    T = collections.Counter(tailkey(p[2]) for p in ok)
    print("\nTAILS (ticks, after the first long low) - %d distinct:" % len(T))
    for t, n in T.most_common(6): print("  x%-5d %s" % (n, t))
