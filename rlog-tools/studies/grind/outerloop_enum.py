# -*- coding: utf-8 -*-
"""outerloop_enum.py -- enumerate message types + publish rates in ONE segment, and the CAN
address/src census for the steering-angle channel openpilot actually feeds LatControlTorque.
Subagent `echoloop`, 2026-09-10.  ANALYSIS ONLY."""
import glob, os, sys, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
RLOGS = os.path.join(KIT, "analysis-2020accord", "rlogs")
sys.path.insert(0, os.path.join(KIT, "rlog-tools"))
import zstandard
from cereal import log as clog

PREFIX = sys.argv[1] if len(sys.argv) > 1 else "75604b0a432fdc89_00000062--1c7daa54e8"
SEG = sys.argv[2] if len(sys.argv) > 2 else "5"
p = glob.glob(os.path.join(RLOGS, "%s--%s--rlog.zst" % (PREFIX, SEG)))[0]
with open(p, "rb") as fh:
    data = zstandard.ZstdDecompressor().stream_reader(fh).read()
it = clog.Event.read_multiple_bytes(data)
tmin = {}; tmax = {}; n = collections.Counter()
can = collections.Counter()
while True:
    try: evt = next(it)
    except StopIteration: break
    except Exception as e: print("truncated", str(e)[:60]); break
    try: w = evt.which()
    except Exception: continue
    tm = evt.logMonoTime * 1e-9
    n[w] += 1
    tmin.setdefault(w, tm); tmax[w] = tm
    if w == "can":
        for m in evt.can:
            can[(m.src, m.address)] += 1
print("=== message types (count, Hz over segment span) ===")
for w, c in n.most_common():
    span = tmax[w] - tmin[w]
    print("  %-34s %7d  %8.2f Hz" % (w, c, c / span if span > 0 else float("nan")))
span = tmax["can"] - tmin["can"]
print("\n=== CAN (src,addr) census, top 40, Hz ===")
for (s, a), c in can.most_common(40):
    print("  src=%-4d addr=0x%03X (%4d)  %7d  %8.2f Hz" % (s, a, a, c, c / span))
print("\n=== STEERING_SENSORS 0x156=342 on every src ===")
for (s, a), c in sorted(can.items()):
    if a == 342:
        print("  src=%d  n=%d  %.2f Hz" % (s, c, c / span))

print("\n=== FULL (src,addr) census sorted by addr ===")
for (s, a), c in sorted(can.items(), key=lambda kv: (kv[0][1], kv[0][0])):
    print("  0x%03X (%5d) src=%-4d n=%7d  %8.2f Hz" % (a, a, s, c, c / span))
