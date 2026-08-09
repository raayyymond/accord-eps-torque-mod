#!/usr/bin/env python3
"""THE STRATIFIED DIFFERENTIAL TEST: is the V84/V85-vs-V81 difference in the ~7.79 Hz ratchet line
CONCENTRATED BELOW 35 km/h, where V84/V85's damper channel is identically zero?

🛑 THE PREMISE WAS CHECKED FROM THE IMAGES FIRST, AND IT IS ONLY HALF RIGHT.
`ch0 = clamp((FactorC(speed) * FactorE(rate)) >> 10, +-ceiling)`.  Byte-read, modes 26 AND 27:

  FactorC  X = [2240, 3840, 5120, 8960] = 35 / 60 / 80 / 140 km/h   -- IDENTICAL on all builds
           Y   V81 [566, 234, 429, 908]     V84/V85 [0, 234, 429, 908]
           ⇒ differs ONLY at Y[0].  ABOVE 35 km/h FactorC IS BYTE-IDENTICAL.          ✅ as briefed

  FactorE  X   V81 [ 12, 200, 2500, 4000]   V84/V85 [ 60, 400, 2500, 4000]
           Y   V81 [  0, 539,  539,  927]   V84/V85 [  0, 140,  539,  927]
           ⇒ 🛑 FactorE differs across the WHOLE practical rate range and converges only above
             X[2] = 2500 ct = 530.5 deg/s, which never happens in normal driving.

⇒ **ABOVE 35 km/h THE TWO CONFIGURATIONS DO NOT CONVERGE.**  Worked from the LERPs:
     motor rate  60 ct (12.7 deg/s): V81 FactorE 137.6 · V84/V85   0.0  ⇒ ratio infinite
     motor rate 200 ct (42.4 deg/s): V81 FactorE 539.0 · V84/V85  57.6  ⇒ ratio  9.4x
     motor rate 400 ct (84.9 deg/s): V81 FactorE 539.0 · V84/V85 140.0  ⇒ ratio  3.9x
   So above 35 km/h V84/V85's damper is present but still **3.9-9.4x weaker** than V81's.

WHAT THAT DOES TO THE TEST.  The DIRECTION survives -- the contrast really is larger below 35 km/h
(where V84/V85's channel is EXACTLY zero because FactorC Y[0] = 0 multiplies the product to zero)
than above it (where both are non-zero).  But the high-speed arm is **NOT a clean internal control**:
it carries a 3.9-9.4x configuration difference of its own.  ⇒ **a concentrated profile SUPPORTS the
mechanism, but a FLAT profile does NOT refute it**, because the high arm is not a null arm.  That
asymmetry is stated up front so the result cannot be over-read in either direction.

CONTROLS APPLIED: pre-declared negative band 32-38 Hz measured identically in both strata; the
wheel-order filter (orders 1-4 landing inside the measured band are dropped); episode bootstrap;
per-stratum window counts printed so an underpowered arm is visible rather than scored.

Usage:
    python stratified_damper_test.py
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import retrodiction_bias_r6e as RB  # noqa: E402  -- windowing + bootstrap, reused verbatim
import score_v85_r6e_bands as SB  # noqa: E402

CIRC = 2.0805
V_SPLIT = 35.0 / 3.6                     # 9.722 m/s -- FactorC's first breakpoint
BUILDS = ["V85/r6e", "V84/r6d", "V81/r67"]
LOW_VB = [(0.0, 2.0), (2.0, 3.5), (3.5, 5.0), (5.0, 6.5), (6.5, 8.0), (8.0, 9.72)]
HIGH_VB = [(9.72, 12.0), (12.0, 15.0), (15.0, 18.0), (18.0, 22.0), (22.0, 26.0), (26.0, 32.0)]
RNG = np.random.default_rng(85_3535)
OUT = {}


def order_clean(rs, lo, hi):
    """Drop windows whose wheel order 1..4 line lands inside [lo, hi] Hz."""
    return [r for r in rs
            if not any(lo <= k * r["v"] / CIRC <= hi for k in (1, 2, 3, 4))]


def main():
    SB.register()
    W = {}
    for b in BUILDS:
        rs = [r for r in RB.windows(b) if r["arm"] == "engaged"]
        W[b] = rs
    RB.hdr("E0  EXPOSURE per stratum (engaged windows of 5.06 s), before and after the\n"
           "    wheel-order filter.  🛑 If the HIGH arm cannot carry a CI, the test is reported\n"
           "    as underpowered -- the LOW arm is NOT scored alone.")
    print(f"    {'build':10s} | {'LOW <35 km/h':>26s} | {'HIGH >=35 km/h':>26s}")
    print(f"    {'':10s} | {'all':>8s} {'ordclean':>8s} {'blk':>6s} | "
          f"{'all':>8s} {'ordclean':>8s} {'blk':>6s}")
    OUT["exposure"] = {}
    for b in BUILDS:
        lo_ = [r for r in W[b] if r["v"] < V_SPLIT]
        hi_ = [r for r in W[b] if r["v"] >= V_SPLIT]
        loc, hic = order_clean(lo_, 7.2, 8.4), order_clean(hi_, 7.2, 8.4)
        print(f"    {b:10s} | {len(lo_):8d} {len(loc):8d} {len({r['blk'] for r in loc}):6d} | "
              f"{len(hi_):8d} {len(hic):8d} {len({r['blk'] for r in hic}):6d}")
        OUT["exposure"][b] = dict(low=len(lo_), low_clean=len(loc), high=len(hi_),
                                  high_clean=len(hic),
                                  low_blk=len({r["blk"] for r in loc}),
                                  high_blk=len({r["blk"] for r in hic}))

    # =============================================================== the test ====================
    RB.hdr("E1  STRATIFIED RATIOS at the ~7.79 Hz LINE (7.2-8.4 Hz), speed-bin matched WITHIN each\n"
           "    stratum, episode-bootstrapped, wheel-order filtered.  Negative control beside it.")
    OUT["ratios"] = {}
    for key, name in (("a779", "LINE 7.2-8.4 Hz"), ("aneg", "NEG CONTROL 32-38 Hz")):
        print(f"\n  ---- {name} ----")
        print(f"    {'pair':14s} | {'LOW <35 km/h':>26s} {'bins':>4s} | "
              f"{'HIGH >=35 km/h':>26s} {'bins':>4s} | {'LOW/HIGH':>8s}")
        for A, B in (("V85/r6e", "V81/r67"), ("V84/r6d", "V81/r67"), ("V85/r6e", "V84/r6d")):
            a_lo = order_clean([r for r in W[A] if r["v"] < V_SPLIT], 7.2, 8.4)
            b_lo = order_clean([r for r in W[B] if r["v"] < V_SPLIT], 7.2, 8.4)
            a_hi = order_clean([r for r in W[A] if r["v"] >= V_SPLIT], 7.2, 8.4)
            b_hi = order_clean([r for r in W[B] if r["v"] >= V_SPLIT], 7.2, 8.4)
            rl = RB.binned_ratio(a_lo, b_lo, key, vb=LOW_VB, min_n=3)
            rh = RB.binned_ratio(a_hi, b_hi, key, vb=HIGH_VB, min_n=3)
            rr = rl[0] / rh[0] if (np.isfinite(rl[0]) and np.isfinite(rh[0]) and rh[0] > 0) \
                else np.nan
            print(f"    {A.split('/')[0]+'/'+B.split('/')[0]:14s} | "
                  f"{rl[0]:8.3f} [{rl[1]:7.3f},{rl[2]:7.3f}] {rl[3]:4d} | "
                  f"{rh[0]:8.3f} [{rh[1]:7.3f},{rh[2]:7.3f}] {rh[3]:4d} | {rr:8.3f}")
            OUT["ratios"].setdefault(key, {})[f"{A}|{B}"] = dict(
                low=list(rl), high=list(rh), low_over_high=float(rr))

    # =============================================================== finer profile ===============
    RB.hdr("E2  THE SAME RATIO IN FINER SPEED BANDS -- the shape of the profile, which is what the\n"
           "    prediction is really about.  A step at 35 km/h is the signature; a flat line is\n"
           "    ambiguous (see the header: the HIGH arm is not a null arm).")
    BANDS = [(0.0, 2.5), (2.5, 5.0), (5.0, 7.5), (7.5, 9.72), (9.72, 13.0), (13.0, 17.0),
             (17.0, 22.0), (22.0, 32.0)]
    OUT["profile"] = {}
    for A, B in (("V85/r6e", "V81/r67"), ("V84/r6d", "V81/r67")):
        print(f"\n  ---- {A.split('/')[0]} / {B.split('/')[0]} ----")
        print(f"    {'v band m/s':>12s} {'km/h':>12s} {'nA':>4s} {'nB':>4s} | "
              f"{'LINE ratio':>22s} | {'NEG ratio':>18s}")
        for lo, hi in BANDS:
            a = order_clean([r for r in W[A] if lo <= r["v"] < hi], 7.2, 8.4)
            b = order_clean([r for r in W[B] if lo <= r["v"] < hi], 7.2, 8.4)
            if len(a) < 3 or len(b) < 3:
                print(f"    {f'{lo:g}-{hi:g}':>12s} {f'{lo*3.6:.0f}-{hi*3.6:.0f}':>12s} "
                      f"{len(a):4d} {len(b):4d} |  -- insufficient --")
                continue
            rl = RB.binned_ratio(a, b, "a779", vb=[(lo, hi)], min_n=3)
            rn = RB.binned_ratio(a, b, "aneg", vb=[(lo, hi)], min_n=3)
            mark = "  <== below 35 km/h" if hi <= V_SPLIT + 1e-6 else ""
            print(f"    {f'{lo:g}-{hi:g}':>12s} {f'{lo*3.6:.0f}-{hi*3.6:.0f}':>12s} "
                  f"{len(a):4d} {len(b):4d} | {rl[0]:7.3f} [{rl[1]:6.3f},{rl[2]:6.3f}] | "
                  f"{rn[0]:6.3f} [{rn[1]:5.3f},{rn[2]:5.3f}]{mark}")
            OUT["profile"].setdefault(f"{A}|{B}", {})[f"{lo}-{hi}"] = dict(
                nA=len(a), nB=len(b), line=list(rl), neg=list(rn))

    (ROOT / "_cache_r6e" / "stratified_damper_test.json").write_text(
        json.dumps(OUT, indent=1, default=float))
    print(f"\nwrote {ROOT / '_cache_r6e' / 'stratified_damper_test.json'}")


if __name__ == "__main__":
    main()
