#!/usr/bin/env python3
r"""studies/grind/extract_r24sign.py -- pull the CAVE's five probe bits out of 0x14A byte 4, alongside the
0x18F torsion bar / wheel rate, for the V280-rev-2 routes.

WHY: the V280 rev 2 code cave at 0xC4B34 (hash d3bb75d8, unchanged since V105) publishes FIVE bits into
0x14A byte 4, and one of them -- bit 4 -- is `gp-0x6ada < 0`, the SIGN of the r24 twist-derivative lane
output (st.h r24,-0x6ada[gp] @0x3AD5A, the same invocation that adds r24 into the aggregator).  0x14A runs
at 100 Hz, so a 20 Hz square wave on that bit is resolved 5 samples per cycle and its FUNDAMENTAL PHASE
against the wheel rate is recoverable.  That settles r24's sign on drives ALREADY TAKEN -- no build, no
drive.

Cave bit map (decoded from the flown image this session):
    byte4 bit 7 = (gp-0x6b4c  < 0)              11-slot assist sum, sign
    byte4 bit 6 = (|gp-0x6b94| >= |gp-0x4f64|)  aggregator vs a lockstep float cell
    byte4 bit 5 = (|gp-0x6ae2| >= |gp-0x6b26|)
    byte4 bit 4 = (gp-0x6ada  < 0)              *** r24 LANE OUTPUT, SIGN ***
    byte4 bit 3 = (gp-0x3680  < 0)              32-bit cell
    bits 2:0    = stock STEER_SENSOR_STATUS
CAVEAT carried from the trace: gp-0x6ada is published unconditionally, but r24 only reaches the motor sum
on the `r20 == 0` path (cmp r0,r20 / be 0x3AC78, r20 = setfe(gp-0x67ac == 1)).  The bit reports the lane's
COMPUTED value, not necessarily a value that acted.

Usage:  python extract_r24sign.py r34 [r33 r32 r31]
"""
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
for _p in [ROOT / "rlog-tools"] + [d for d in (ROOT / "rlog-tools").iterdir() if d.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from rlog_parse import read_messages  # noqa: E402

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
OUTDIR = Path(__file__).resolve().parent / "_scratch"
PREFIX = {
    "r31": "75604b0a432fdc89_00000031--a680e9b2ac",
    "r32": "75604b0a432fdc89_00000032--33a5dbbcb3",
    "r33": "75604b0a432fdc89_00000033--1948a2c354",
    "r34": "75604b0a432fdc89_00000034--e2d2d5381f",
}


def i16be(d, i):
    v = (d[i] << 8) | d[i + 1]
    return v - 65536 if v >= 32768 else v


def extract(tag):
    paths = sorted(RLOGDIR.glob(PREFIX[tag] + "--*--rlog.zst"),
                   key=lambda p: int(p.name.split("--")[2]))
    if not paths:
        raise SystemExit("no rlogs for " + tag)
    rows14, rows18, rowse4 = [], [], []
    cs = {"t": [], "v": [], "ang": []}
    for p in paths:
        try:
            stream = list(read_messages(str(p)))
        except Exception as e:      # r31 seg 10 is truncated on disk; take what parsed and move on
            print("   WARN %s: %s" % (p.name, str(e).splitlines()[0]))
            continue
        for evt in stream:
            try:
                w = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            if w == "can":
                for m in evt.can:
                    src, addr = int(m.src), int(m.address)
                    d = bytes(m.dat)
                    if src == 1 and addr == 0x18F and len(d) >= 5:
                        # wire sign, exactly as the v280 caches store it: tq = -i16be(d,0), rate = -i16be(d,2)
                        rows18.append((tm, -float(i16be(d, 0)), -float(i16be(d, 2)),
                                       float((d[4] >> 3) & 1)))
                    elif src == 1 and addr == 0x14A and len(d) >= 5:
                        rows14.append((tm, float(d[4])))
                    elif src == 129 and addr == 0x0E4 and len(d) >= 3:
                        rowse4.append((tm, float(i16be(d, 0)), float((d[2] >> 7) & 1)))
            elif w == "carState":
                c = evt.carState
                cs["t"].append(tm)
                cs["v"].append(float(c.vEgo))
                cs["ang"].append(float(c.steeringAngleDeg))
    a14 = np.array(rows14, float)
    a18 = np.array(rows18, float)
    ae4 = np.array(rowse4, float)
    t0 = a18[0, 0]
    out = dict(
        t14=a14[:, 0] - t0, b4=a14[:, 1],
        t18=a18[:, 0] - t0, tq=a18[:, 1], rate=a18[:, 2], sca=a18[:, 3],
        te4=ae4[:, 0] - t0, cmd=ae4[:, 1], req=ae4[:, 2],
        tcs=np.array(cs["t"]) - t0, vego=np.array(cs["v"]), angcs=np.array(cs["ang"]),
    )
    OUTDIR.mkdir(exist_ok=True)
    np.savez_compressed(OUTDIR / ("r24sign_" + tag + ".npz"), **out)
    print("%s: 0x14A %d frames (%.1f s, %.1f Hz)  0x18F %d  0xE4 %d  cs %d"
          % (tag, len(a14), out["t14"][-1], len(a14) / out["t14"][-1], len(a18), len(ae4), len(cs["t"])))
    b4 = out["b4"].astype(int)
    for bit, what in ((7, "gp-0x6b4c<0"), (6, "|6b94|>=|4f64|"), (5, "|6ae2|>=|6b26|"),
                      (4, "gp-0x6ada<0  (r24 SIGN)"), (3, "gp-0x3680<0")):
        v = (b4 >> bit) & 1
        print("     bit %d %-26s duty %.4f   transitions/s %.2f"
              % (bit, what, v.mean(), np.abs(np.diff(v)).sum() / out["t14"][-1]))


for t in (sys.argv[1:] or ["r34"]):
    extract(t)
