#!/usr/bin/env python3
r"""studies/impedance/v95_rez_polarity_and_mask.py -- the two CONTROLS that had to pass before any Re(Z) number counts.

Run this FIRST.  Both are controls, not measurements, and both changed an answer.

CONTROL 1 -- DOES Re(Z) > 0 ACTUALLY MEAN "DISSIPATIVE" ON THIS CAR?
    The whole `Re(Z) < 0 = the steering injects energy` result rested on a sign convention that had
    never been anchored against a case whose physics is known a priori.  The anchor is
    parameter-free and uses NO spectral estimator at all:

        mean(T * w) over MANUAL + HANDS-ON + |wheel rate| > 30 deg/s

    Turning the wheel hard, the driver MUST do net positive work against tyre scrub and column
    friction.  If this came out negative the CAN sign convention would be inverted and every Re(Z)
    sign in the kit would flip.  RESULT 2026-08-12: pooled n = 20,159 frames, mean +3859, median
    +3198, P(T*w > 0) = 0.9238, positive on all 8 routes tested across 8 builds.
    => Re(Z) > 0 = DISSIPATIVE.  Re(Z) < 0 = the column doing work on the driver's hands.

CONTROL 2 -- HOW MUCH DOES THE HANDS-OFF MASK SELECT ON THE MEASUREMENT ITSELF?
    `steeringPressed` is `|STEER_TORQUE_SENSOR| > 1200`, i.e. a threshold on the NUMERATOR of Z.
    This file proves that empirically (the flag vs a free threshold fit), then prices the
    truncation: how many candidate windows the strict mask drops per arm, and how much bigger the
    6-9 Hz torque amplitude is in the DROPPED windows than in the KEPT ones.
    RESULT: drops 39 % of engaged and 93 % of manual candidates; dropped/kept 6-9 Hz amplitude
    3.91x engaged vs 1.20x manual -- arm-asymmetric by 3.3x.

Usage:  python studies/impedance/v95_rez_polarity_and_mask.py
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

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from v95_rez_lib import (BUILD, CACHES, DEFS, NEED, STEER_THRESHOLD, base, candidates,  # noqa: E402
                         epwins, hdr, load, passes, transfer)

RNG = np.random.default_rng(950811)
LOWB = [("0.4-1", 0.4, 1.0), ("1-2", 1.0, 2.0), ("2-4", 2.0, 4.0), ("4-6", 4.0, 6.0),
        ("6-9", 6.0, 9.0), ("9-12", 9.0, 12.0)]
ANCHOR_ROUTES = ["r66", "r5e", "r70", "r6f", "r73", "r77", "r78", "r79"]


def control1():
    hdr("CONTROL 1 -- mean(T * w), the sign of the driver's own work.  NO spectral estimator.")
    print(f"  {'route':6s} {'build':12s} | {'MANUAL hands-ON, |w| > 30 deg/s':>33s} | "
          f"{'MAN hands-ON all':>18s} | {'ENG hands-OFF':>16s}")
    print(f"  {'':6s} {'':12s} | {'n':>7s} {'mean T*w':>11s} {'sign':>12s} | {'n':>8s} {'mean':>9s}"
          f" | {'n':>8s} {'mean':>7s}")
    pool = []
    for r in ANCHOR_ROUTES:
        if r not in CACHES:
            continue
        B = base(load(r))
        mov = B["v"] > 0.5
        p = B["tq"] * B["w"]                                   # counts * rad/s
        mon = (~B["lat"]) & B["press"] & mov
        big = mon & (np.abs(B["wdeg"]) > 30.0)
        eoff = B["lat"] & (~B["press"]) & mov
        pool.append(p[big])
        print(f"  {r:6s} {BUILD.get(r, '?'):12s} | {big.sum():7d} {p[big].mean():11.1f} "
              f"{'POSITIVE' if p[big].mean() > 0 else 'NEGATIVE':>12s} | {mon.sum():8d} "
              f"{p[mon].mean():9.1f} | {eoff.sum():8d} {p[eoff].mean():7.1f}")
    a = np.concatenate(pool)
    print(f"\n  POOLED: n = {len(a):,}   mean {a.mean():.1f}   median {np.median(a):.1f}   "
          f"P(T*w > 0) = {np.mean(a > 0):.4f}")
    print("  => POSITIVE ⇒ positive T*w is the driver DOING WORK on the column ⇒ Re(Z) > 0 is")
    print("     DISSIPATIVE and Re(Z) < 0 is the column doing work on the driver's hands.")

    print("\n  Re(Z) at 0.4-2 Hz, MANUAL arms -- Coulomb friction forces Re > 0 there:")
    for r in ANCHOR_ROUTES:
        if r not in CACHES:
            continue
        B = base(load(r))
        mov = B["v"] > 0.5
        for tag, m in (("MANUAL hands-ON ", (~B["lat"]) & B["press"] & mov),
                       ("MANUAL hands-OFF", (~B["lat"]) & (~B["press"]) & mov)):
            W = epwins(m, B["t"], (B["w"], B["tq"]))
            res = transfer(W, B["fs"], LOWB, rng=RNG)
            if res is None:
                print(f"    {r:5s} {tag}: {len(W):3d} windows -- NOT SCOREABLE")
                continue
            print(f"    {r:5s} {tag}: nwin {len(W):4d}  " +
                  "  ".join(f"{nm}:{res[nm]['re']:+8.0f}{'' if res[nm]['trust'] else '?'}"
                            for nm, _, _ in LOWB))
    print("    ('?' = fails the pre-declared trust gate coh2 >= 0.10 AND >= 5x shuffled)")


def control2():
    hdr("CONTROL 2a -- IS `steeringPressed` A PURE THRESHOLD ON THE NUMERATOR OF Z?")
    print("  opendbc/car/honda/carstate.py:163 -- steeringPressed = |steeringTorque| > "
          "STEER_THRESHOLD.get(fp, 1200)")
    print("  HONDA_ACCORD (10th gen) is NOT in the override dict => T = 1200.  Tested:")
    print(f"  {'route':6s} {'build':12s} | {'agree(|cs_tq|>1200)':>19s} {'best-fit T':>10s} "
          f"{'agree@best':>10s} | {'agree(|tq|>1200)':>16s}")
    for r in sorted(CACHES):
        if r == "r66x":
            continue
        z = load(r)
        if not (NEED | {"cs_tq"}) <= set(z.files):
            continue
        B = base(z)
        if len(B["t"]) < 2000:
            continue
        ct, p = B["cs_tq"], B["press"]
        Ts = np.arange(200, 2000, 10)
        best = max(Ts, key=lambda T: np.mean((ct > T) == p))
        print(f"  {r:6s} {BUILD.get(r, '?'):12s} | {np.mean((ct > STEER_THRESHOLD) == p):19.4f} "
              f"{best:10.0f} {np.mean((ct > best) == p):10.4f} | "
              f"{np.mean((np.abs(B['tq']) > STEER_THRESHOLD) == p):16.4f}")

    hdr("CONTROL 2b -- HOW MUCH AMPLITUDE DOES THE STRICT MASK TRUNCATE, AND IS IT ARM-SYMMETRIC?")
    C = candidates()
    print(f"    {'arm':4s} {'cand':>5s} " + " ".join(f"{d:>15s}" for d in DEFS))
    for arm in ("ENG", "MAN"):
        W = C[arm]
        print(f"    {arm:4s} {len(W):5d} " +
              " ".join(f"{sum(passes(w, d) for w in W):15d}" for d in DEFS))
    print(f"\n    {'arm':4s} | {'6-9 Hz |tq| KEPT':>17s} {'DROPPED':>10s} {'ratio':>7s} | "
          f"{'26-31 KEPT':>11s} {'DROPPED':>10s}")
    for arm in ("ENG", "MAN"):
        W = C[arm]
        k = [w["a69"] for w in W if passes(w, "D0 STRICT")]
        d = [w["a69"] for w in W if not passes(w, "D0 STRICT")]
        k2 = [w["a2631"] for w in W if passes(w, "D0 STRICT")]
        d2 = [w["a2631"] for w in W if not passes(w, "D0 STRICT")]
        print(f"    {arm:4s} | {np.median(k):17.0f} {np.median(d):10.0f} "
              f"{np.median(d) / max(np.median(k), 1e-9):7.2f}x | {np.median(k2):11.0f} "
              f"{np.median(d2):10.0f}")
    print("    => a ratio >> 1 means the strict mask drops exactly the high-amplitude windows.")
    print("       A DIFFERENT ratio per arm means the truncation does not cancel in the contrast.")
    return C


if __name__ == "__main__":
    control1()
    control2()
