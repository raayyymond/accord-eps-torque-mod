#!/usr/bin/env python3
r"""The 20-28 Hz mode across the WHOLE recent ladder, and the engagement test for the ~23 Hz line.

Every modern cache r7d..r85 is a 4x LKAS gain build with LEVER B ARMED (BUILD-LINEAGE: "V100 (on
car) gate 0xFB ARMED 512/5244 = V88", and V89..V100 are all V88-descended).  r95 is the only 8x
build and the only Lever-B-dead one.  So if the mode sits at ~21 Hz on every 4x route and at ~23 Hz
only on r95, the shift is V101's, not drive-to-drive noise.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NFFT, HOP = 256, 128
win = np.hanning(NFFT)

LADDER = [("7d", "V94"), ("7e", "V96"), ("7f", "V96"), ("80", "V97"),
          ("81", "V98"), ("82", "V99"), ("85", "V100"), ("95", "V101")]


def hdr(s):
    print("\n" + "=" * 100)
    print(s)
    print("=" * 100)


def segs_of(route):
    p = L.AN / ("_cache_r" + route)
    out = []
    for f in sorted(p.glob("r" + route + "s*.npz")):
        out.append(int(f.stem[len("r" + route + "s"):]))
    return sorted(out)


hdr("THE 20-28 Hz MODE ACROSS THE LADDER -- engaged, 5-65 km/h, median spectrum of column torque")
print("   %-6s %-6s %7s %7s   %-24s %-24s" % ("route", "build", "segs", "win", "tq peak 20-28 Hz",
                                              "rate_c peak 20-28 Hz"))
for route, build in LADDER:
    p = L.AN / ("_cache_r" + route)
    if not p.exists():
        print("   r%-5s %-6s  (no cache)" % (route, build))
        continue
    segs = segs_of(route)
    L.ROUTES[route] = dict(build=build, cache=p, pfx="r" + route + "s", segs=tuple(segs),
                           gain=0, clamp=0, leverB=None, idcode=0, bits="")
    try:
        recs = L.sel(L.windows(route, NFFT, HOP, engaged=True, keep_raw=True), vlo=5, vhi=65)
    except Exception as exc:                                   # noqa: BLE001
        print("   r%-5s %-6s  LOAD FAILED: %s" % (route, build, exc))
        continue
    if len(recs) < 10:
        print("   r%-5s %-6s %7d %7d   (too few windows)" % (route, build, len(segs), len(recs)))
        continue
    cells = []
    for ch in ("tq", "rate_c"):
        P = [L.psd(r["_blk"][ch][r["_sl"]], L.FS, win)[1] for r in recs]
        f = L.psd(recs[0]["_blk"][ch][recs[0]["_sl"]], L.FS, win)[0]
        pm = np.median(np.asarray(P), axis=0)
        m = (f >= 20) & (f <= 28)
        i = int(np.argmax(pm[m]))
        fpk = f[m][i]
        loc = (f >= fpk - 2.5) & (f <= fpk + 2.5)
        cells.append("%6.1f Hz  prom %5.2f" % (fpk, pm[m][i] / np.median(pm[loc])))
    print("   r%-5s %-6s %7d %7d   %-24s %-24s"
          % (route, build, len(segs), len(recs), cells[0], cells[1]))

hdr("ENGAGEMENT TEST for the ~23 Hz line -- shape (22-26)/(32-38), ENGAGED vs MANUAL, within route")
print("   The operator: \"It only occurs during LKAS command.\"  A within-route engaged/manual ratio")
print("   removes every between-drive confound.  (r85 and r95 manual time is 0-10 km/h only, so the")
print("   speeds are NOT matched -- this is a directional test, not a calibrated one.)")
for route, build in (("85", "V100"), ("95", "V101")):
    L.ROUTES[route]["segs"] = tuple(segs_of(route))
    E = L.sel(L.windows(route, NFFT, HOP, engaged=True), vlo=0, vhi=65)
    M = L.sel(L.windows(route, NFFT, HOP, engaged=False), vlo=0, vhi=65)
    print("\n   r%s %s   engaged win=%d  manual win=%d" % (route, build, len(E), len(M)))
    for ch in ("tq", "rate_c", "cs_ang"):
        out = []
        for bn in ("18-22", "22-26", "26-31"):
            def shape(recs):
                v = [r[ch + "|" + bn] / r[ch + "|32-38"] for r in recs
                     if r.get(ch + "|32-38", 0) > 0]
                return np.median(v) if v else np.nan
            out.append("%s %5.2f" % (bn, shape(E) / shape(M)))
        print("      %-8s eng/man shape ratio:  %s" % (ch, "   ".join(out)))

print("\n[done]")
