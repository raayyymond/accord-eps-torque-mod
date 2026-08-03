#!/usr/bin/env python3
"""Extract ENGINE_RPM (0x17C POWERTRAIN_DATA, src 1) for the highway segments.

WHY. `highway_order_test.py` measured a 30-49.5 Hz line on all four comma-IMU axes that sits at
42-43 Hz and does NOT move while road speed runs 22 -> 35 m/s (wheel order 3 would climb
33.3 -> 47.9 Hz over the same span). A line fixed in hertz while road speed varies is exactly what
the operator reports feeling. It is ALSO exactly what an ENGINE order does in a car with a CVT,
which holds engine speed roughly constant through a wide range of road speed -- and the 2020
Accord has one. So the mode/order verdict is not finished until engine rpm has been checked.

    engine order 1  = rpm / 60 Hz          engine order 2 (4-cyl firing) = rpm / 30 Hz
    On the ~101.03 Hz IMU lattice each of those also appears at |k*101.03 +/- f|, so a true
    58.7 Hz (1761 rpm, order 2) is INDISTINGUISHABLE from an apparent 42.3 Hz.

DECODE. opendbc honda: BO_ 380 POWERTRAIN_DATA, SG_ ENGINE_RPM : 23|16@0+ (1,0) -- start bit 23,
16 bits, BIG-endian, unsigned, scale 1 => bytes [2],[3] big-endian. 🛑 The scale is verified in
`main()` against a plausibility window rather than trusted: a decode that returns 0 or > 8000 rpm
at highway cruise is rejected loudly instead of being averaged into a spectrum.

Usage:  python extract_rpm_cache.py 47 4 5 6 7 8 9 10 11 12 13 14 15 16 17
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rlog-tools"))
from rlog_parse import read_messages  # noqa: E402

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
ROUTE = {"47": "75604b0a432fdc89_00000047--3e0b6134c0",
         "3b": "75604b0a432fdc89_0000003b--a4a7f4dbf1",
         "2b": "75604b0a432fdc89_0000002b--7926e8f7e5",
         "37": "75604b0a432fdc89_00000037--6231e33f3d"}
CACHE = {"47": "_cache_r47", "3b": "_cache_r3b", "2b": "_cache_r2b", "37": "_cache_r37"}
PFX = {"47": "r47s", "3b": "r3bs", "2b": "r2bs", "37": "r37s"}


def main(tag, segs):
    out = ROOT / CACHE[tag]
    for s in segs:
        p = RLOGDIR / f"{ROUTE[tag]}--{s}--rlog.zst"
        if not p.exists():
            print(f"{tag}s{s}: MISSING {p.name}")
            continue
        t, rpm, gear, xs = [], [], [], []
        t0 = None
        for evt in read_messages(p):
            try:
                w = evt.which()
            except Exception:
                continue
            if w != "can":
                continue
            tm = evt.logMonoTime * 1e-9
            for m in evt.can:
                if int(m.src) == 1 and int(m.address) == 0x17C and len(m.dat) >= 8:
                    d = bytes(m.dat)
                    if t0 is None:
                        t0 = tm
                    t.append(tm)
                    rpm.append((d[2] << 8) | d[3])          # 23|16@0+ big-endian
                    xs.append((((d[0] << 8) | d[1]) * 0.01))  # XMISSION_SPEED, km/h
                    gear.append(d[7] & 0x0F)
        if not t:
            print(f"{tag}s{s}: no 0x17C")
            continue
        # anchor onto the SAME t=0 the .npz cache uses, so the two align sample for sample
        base = np.load(out / f"{PFX[tag]}{s}.npz")
        t0_mono = float(base["t0_mono"][0]) if "t0_mono" in base.files else t[0]
        a = np.array(t, float) - t0_mono
        r = np.array(rpm, float)
        np.savez_compressed(out / f"{PFX[tag]}{s}_rpm.npz", t=a, rpm=r,
                            xspeed=np.array(xs, float), gear=np.array(gear, float))
        ok = (r > 400) & (r < 8000)
        print(f"{tag}s{s}: n={len(r)}  rpm p05 {np.percentile(r, 5):.0f} p50 "
              f"{np.median(r):.0f} p95 {np.percentile(r, 95):.0f}  "
              f"plausible {100 * ok.mean():.1f}%  xspeed p50 {np.median(xs):.1f} km/h"
              + ("" if ok.mean() > 0.5 else "   🛑 DECODE SUSPECT"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
