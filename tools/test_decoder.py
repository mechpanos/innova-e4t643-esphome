#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_decoder.py - checks the firmware decoder against the captures, on a PC.

    python3 test_decoder.py <log> [<log> ...]          # comparison + what the firmware would publish
    python3 test_decoder.py --quiet <log> [...]        # comparison only

Files with MEMORY RECORDINGS (tag "rec") are accepted too: the bursts of the white wire are taken, and each
recording starts 100 s after the previous one (the time in the listing is then counted from the start of the first).

Compiles test_decoder.cpp (which includes ../esphome/fancoil_decode.h, the very code that runs
on the ESP32) and compares EVERY burst with fcwave.py: frame or not, pre-pulse, the 56 bits,
idle tail or key tail. Then prints what the firmware would have published to Home Assistant,
with the time of the capture. Exit code 1 on any difference. Needs g++.
"""
import sys, os, subprocess, tempfile, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fcwave, rec
hh = lambda ms: fcwave.hhmmss(ms / 1000.0)

quiet = "--quiet" in sys.argv
logs = [a for a in sys.argv[1:] if not a.startswith("--")]
if not logs: sys.exit("usage: test_decoder.py [--quiet] <log> [<log> ...]")
exe = os.path.join(tempfile.gettempdir(), "fancoil_test_decoder")
subprocess.check_call(["g++", "-O2", "-std=c++17", "-Wall", "-I", os.path.join(HERE, "..", "esphome"), os.path.join(HERE, "test_decoder.cpp"), "-o", exe])
bad = 0
sets = []
for path in logs:
    B = [(t, b) for t, b in fcwave.load_bursts(path, with_time=True) if t is not None and b]
    if B: sets.append((path, B))
    # memory recordings: the white wire only, 100 s per recording
    B = [(i * 100 + t / 1e6, v) for i, r in enumerate(rec.load(path)) for s_, ch, t, v in r["bursts"] if ch == "W" and v]
    if B: sets.append((path + "  [memory recordings]", B))
for path, B in sets:
    inp = "\n".join("%d %s" % (round(t * 1000), " ".join(map(str, b))) for t, b in B) + "\n"
    out = subprocess.run([exe], input=inp, capture_output=True, text=True, check=True).stdout.split("\n")
    F = [l.split(" ") for l in out if l.startswith("F ")]
    E = [l for l in out if l.startswith("E ")]
    S = [l for l in out if l.startswith("S ")]
    assert len(F) == len(B), (len(F), len(B))
    n_ok = diff_parse = diff_tail = 0; ex = []
    tails = collections.Counter()
    for (t, b), f in zip(B, F):
        p = fcwave.parse(b)
        if bool(p) != (f[2] == "1") or (p and (p[0] != int(f[3]) or p[1] != f[4])):
            diff_parse += 1
            if len(ex) < 5: ex.append("  PARSE DIFFERS %s: python=%s  c++=%s" % (hh(round(t * 1000)), p and (p[0], fcwave.hexs(p[1])), f[2:5]))
            continue
        if not p: continue
        n_ok += 1
        pt = fcwave.tail_bits(b, p)
        if pt != f[5]:
            diff_tail += 1
            if len(ex) < 5: ex.append("  TAIL DIFFERS %s: python=%s  c++=%s" % (hh(round(t * 1000)), pt, f[5]))
        tails[f[5]] += 1
    bad += diff_parse + diff_tail
    print("%s\n  %d bursts, %d frames, parse differences: %d, tail differences: %d   %s" % (
        os.path.basename(path), len(B), n_ok, diff_parse, diff_tail, " ".join(S)))
    for e in ex: print(e)
    print("  tails (c++): " + "  ".join("%s x%d" % kv for kv in tails.most_common(12)))
    if not quiet:
        print("  WHAT THE FIRMWARE WOULD PUBLISH:")
        img = 0
        for e in E:
            _, ms, what = e.split(" ", 2)
            if what.startswith("image"): img += 1; continue      # twice a second while a symbol blinks
            print("    %s  %s" % (hh(int(ms)), what))
        print("    (+ %d image changes)" % img)
sys.exit(1 if bad else 0)
