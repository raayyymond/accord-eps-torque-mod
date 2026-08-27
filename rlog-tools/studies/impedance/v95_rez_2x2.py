#!/usr/bin/env python3
r"""studies/impedance/v95_rez_2x2.py -- ENGAGED vs MANUAL x HANDS-OFF vs HANDS-ON, matched, with the mask guarded.

This is the plant-versus-firmware measurement.  The kit had only the engaged/hands-off cell; the
other three are the controls that decide whether the 6-9 Hz anti-damping belongs to the LKAS lane,
the always-on assist loop, or the plant.

🛑 RUN `studies/impedance/v95_rez_polarity_and_mask.py` FIRST.  Its CONTROL 2 is the reason this file exists: the
   kit's hands-off mask is an instantaneous threshold on the numerator of Z, it drops 39 % of
   engaged and 93 % of manual candidate windows, and it truncates 3.91x harder in the engaged arm
   than in the manual one.  Every panel below is therefore run under all four definitions.

🛑 THE RATE CONFOUND IS STRUCTURAL AND NO AMOUNT OF DRIVING FIXES IT.  Hands off with LKAS off means
   the wheel barely moves: the manual arm sits at 0.3-1.1 deg/s against 0.6-3.6 engaged.  Panel D is
   the fix -- measure Re(Z) vs rate INSIDE the engaged arm and read it off at the manual arm's own
   rate -- and it is the panel the conclusion rests on.

HEADLINE RESULT, 2026-08-12 (see `docs/STATE.md`):
    matched 5-22 m/s / |rate| < 13 deg/s, D3 mask:  ENG -3394 [-3704,-3113]  MAN -1883 [-2403,-1081]
    rate- AND speed-matched (0.6-2.5 deg/s):        ENG ~ -3000               MAN -2411 [-2788,-1500]
    => the engagement multiplier at 6-9 Hz is 1.24x and the CIs OVERLAP.  Manual hands-off is NOT
       damped; it is ~80 % as anti-damped.  But at 18-22 Hz the engaged/manual contrast is
       -1679 [-2531,-1110] vs -0 [-169,+186] within one route: the GRINDING band's anti-damping is
       entirely engagement-created.  ⇒ LKAS-gated levers own the grinding bands and own almost none
       of the micro-ratchet band.

Usage:  python studies/impedance/v95_rez_2x2.py
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import sys
from pathlib import Path
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from v95_rez_lib import (BUILD, DEFS, candidates, cell, full, hdr, passes, row)  # noqa: E402

RNG = np.random.default_rng(950820)
KEY = ("2-4", "4-6", "6-9", "9-12", "12-16", "18-22", "26-31", "32-38")
RATE_BINS = ((0.0, 0.6), (0.6, 1.2), (1.2, 2.5), (2.5, 5.0), (5.0, 13.0))


def main():
    C = candidates()

    hdr("A.  Re(Z) UNDER ALL FOUR HANDS-OFF DEFINITIONS -- matched 5-22 m/s, |rate| < 13 deg/s")
    print("    " + " " * 54 + " ".join(f"{k:>15s}" for k in KEY))
    for arm in ("ENG", "MAN"):
        print(f"\n  --- {arm} ---")
        for d in DEFS:
            print(row(f"{arm} {d}", cell(C[arm], d=d), keys=KEY, rng=RNG, nboot=300))
    print("\n  READ: 6-9 Hz and above should be INVARIANT across the four; 2-4 Hz reverses sign and")
    print("        4-6 Hz loses most of its magnitude.  That is the selection effect, priced.")

    hdr("B.  THE HEADLINE CELL, WITH CIs AND ROUTE COMPOSITION")
    res = {}
    for arm in ("ENG", "MAN"):
        for d in ("D3 MEDIAN", "D4 = D2 AND D3", "D0 STRICT"):
            res[(arm, d)] = full(f"{arm} hands-off, {d}", cell(C[arm], d=d), keys=KEY, rng=RNG)
    print()
    for d in ("D3 MEDIAN", "D4 = D2 AND D3", "D0 STRICT"):
        e, m = res.get(("ENG", d)), res.get(("MAN", d))
        if not (e and m):
            print(f"  {d:16s}  -- one arm not scoreable")
            continue
        print(f"  {d:16s} " + "  ".join(
            f"{k} ENG {e[k]['re']:+6.0f} / MAN {m[k]['re']:+6.0f} = {e[k]['re']/m[k]['re']:5.2f}x"
            for k in ("6-9", "9-12", "18-22")))

    hdr("C.  PER SPEED CELL, and PER ROUTE, and LEAVE-ONE-ROUTE-OUT on the manual arm")
    for vlo, vhi in ((0.5, 12), (12, 22), (22, 40)):
        print(f"\n  speed [{vlo},{vhi}) m/s = [{vlo*3.6:.0f},{vhi*3.6:.0f}) km/h")
        for arm in ("ENG", "MAN"):
            print(row(f"{arm} D3", cell(C[arm], vlo, vhi), keys=KEY, rng=RNG, nboot=300))
    MAN = cell(C["MAN"], 5, 22)
    byr = defaultdict(list)
    for w in MAN:
        byr[w["route"]].append(w)
    print("\n  manual arm composition, 5-22 m/s D3:  " +
          ", ".join(f"{k}({BUILD.get(k,'?')}):{len(v)}" for k, v in
                    sorted(byr.items(), key=lambda x: -len(x[1]))))
    for rt in sorted(byr, key=lambda k: -len(byr[k]))[:3]:
        print(row(f"MAN D3 minus {rt}", [w for w in MAN if w["route"] != rt], keys=KEY, rng=RNG))
        print(row(f"MAN D3 {rt} only", byr[rt], keys=KEY, rng=RNG))

    hdr("D.  🛑 THE RATE CORRECTION -- the panel the conclusion rests on")
    print("  The manual arm cannot be rate-matched by driving harder: hands off + LKAS off means the")
    print("  wheel does not move.  So measure Re(Z) vs rate INSIDE the engaged arm instead.")
    print(f"\n  {'engaged rate bin':22s} " + " ".join(f"{k:>15s}" for k in ("6-9", "9-12", "18-22")))
    for lo, hi in RATE_BINS:
        W = cell(C["ENG"], 5, 22, lo, hi)
        if len(W) < 10:
            print(f"  [{lo:4.1f},{hi:4.1f}) deg/s      n={len(W)} -- too few")
            continue
        print(row(f"[{lo:4.1f},{hi:4.1f}) deg/s", W, keys=("6-9", "9-12", "18-22"), rng=RNG,
                  nboot=400))
    print("\n  and the MANUAL arm inside the rate window it actually occupies:")
    full("MAN D3, 0.6-2.5 deg/s, 5-22 m/s", cell(C["MAN"], 5, 22, 0.6, 2.5),
         keys=("4-6", "6-9", "9-12", "12-16", "18-22"), rng=RNG)

    hdr("E.  WITHIN ONE ROUTE, ONE BUILD -- so a firmware difference cannot be the explanation")
    for rt, (vlo, vhi) in (("r66", (5, 25)), ("r73", (0.5, 12)), ("r76", (0.5, 25))):
        e, m = cell(C["ENG"], vlo, vhi), cell(C["MAN"], vlo, vhi)
        e = [w for w in e if w["route"] == rt]
        m = [w for w in m if w["route"] == rt]
        if len(m) < 8:
            continue
        print(f"\n  {rt} ({BUILD.get(rt,'?')}) {vlo}-{vhi} m/s")
        print(row("  ENGAGED", e, keys=KEY, rng=RNG, nboot=400))
        print(row("  MANUAL ", m, keys=KEY, rng=RNG, nboot=400))

    hdr("F.  GRIP -- hands-ON defined by SUSTAINED grip (press duty >= 80 %), not a torque spike")
    print("  🛑 IRREDUCIBLE: hands-on is DEFINED by high |tq|, which is the numerator of Z, so this")
    print("     arm is selected upward on |Z| by construction.  This instrument cannot cleanly")
    print("     measure grip.  The kit's band-power grip result does not share the defect.")
    for vlo, vhi in ((0.5, 8), (8, 20)):
        print(f"\n  speed [{vlo},{vhi}) m/s")
        print(row("  ENG hands-OFF D3", cell(C["ENG"], vlo, vhi), keys=KEY, rng=RNG, nboot=400))
        on = [w for w in C["ENG"] if w["duty"] >= 0.80 and vlo <= w["v"] < vhi and w["rate"] < 13]
        print(row("  ENG hands-ON duty>=80%", on, keys=KEY, rng=RNG, nboot=400))


if __name__ == "__main__":
    main()
