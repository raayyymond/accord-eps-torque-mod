#!/usr/bin/env python3
"""studies/sessions/v89/v89_b1_damper_surface.py -- read the base-assist damper surface off the FLOWN V88 image.

    ch0 = clamp( (FactorC(speed) * FactorE(rate)) >> 10 , +/- ceiling )     [gp-0x6bd0]

Two MULTIPLICATIVE dead zones are on record:
    FactorC  Y[0] = 0  below X[0] = 2240 counts = 34.97 km/h     (the SPEED dead zone)
    FactorE  Y[0] = 0  below X[0] =   12 counts = 12.73 deg/s    (the RATE  dead zone)

and the point of this script is a claim about the KIT'S OWN TEST HISTORY, not about Honda:

  * the `FactorE X[0]` lever was WITHDRAWN AS "STRUCTURALLY VACUOUS" (builds/v80_v107/build_v86b_tva.py header)
    because FactorC was 0 at creep -- zero times anything is zero.
  * the `FactorC Y[0]` lever WAS tested, as V86B on route 70 -- but V86B lifted Y[0] to the
    record's OWN Y[3] (908 / 875), i.e. it flattened the SPEED axis to full authority, while the
    RATE dead zone was still in force and still zero below 12.73 deg/s.

=> NEITHER TEST EVER HAD BOTH DEAD ZONES OPEN. That is exactly BUILD-LINEAGE RULE 5
   ("a null is only a null if the lever was in force"), applied to a PRODUCT of two gates.

The operator's own symptom split lands on the rate gate:
    micro-ratcheting = engaged + spinning the wheel AT ALL     -> |rate| at or below ~12.7 deg/s
    ratcheting       = engaged + spinning the wheel QUICKLY    -> |rate| above it

This script prints, from the image bytes, the full 2-D surface and the duty of each dead zone
against route 73's measured engaged (speed, rate) distribution -- i.e. how much of the operator's
symptom regime the damper is structurally absent from.
"""
from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3].parent
FW = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                         r"C:/Users/dudei/Desktop/Projects/accord-firmwares"))
IMG_DIR = FW / "analysis-2020accord"

FACTOR_B_PTRS, FACTOR_C_PTRS = 0xC9CCC, 0xC9E9C
FACTOR_D_PTRS, FACTOR_E_PTRS = 0xC9DB4, 0xC9F84
CEILING_PTRS = 0xC77A0
MODES = [24, 26, 27, 25]          # 24 = manual, 26 = engaged, 27 = engaged2, 25 for reference

# counts -> physical, from the record
KMH_PER_CT = 35.0 / 2240.0        # FactorC X[0] = 2240 ct = 34.97 km/h
# 🛑 FactorE X[0] is 60 counts, NOT 12. The record's "12.73 deg/s" is the PHYSICAL value of
# X[0]; "12" was the proposed EDITED count in the withdrawn V86B variant. Read from the image:
# X = [60, 400, 2500, 4000] ct = [12.7, 84.9, 530.4, 848.7] deg/s.
DEGS_PER_CT = 12.73 / 60.0        # FactorE X[0] = 60 ct = 12.73 deg/s


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def rec_any(b, base):
    n = u16(b, base)
    assert 1 <= n <= 16, f"record @0x{base:05X} declares count {n}"
    xs = list(struct.unpack_from(f"<{n}h", b, base + 2))
    ys = list(struct.unpack_from(f"<{n}h", b, base + 2 + 2 * n))
    return n, xs, ys


def factor_rec(b, ptrs, mode):
    return u32(b, ptrs + mode * 4)


def lerp_int(x, n, xs, ys):
    """Honda's integer LERP, saturating at both ends. Mirrors the firmware's own clamp-then-lerp."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[n - 1]:
        return ys[n - 1]
    for i in range(n - 1):
        if xs[i] <= x < xs[i + 1]:
            dx = xs[i + 1] - xs[i]
            return ys[i] + ((ys[i + 1] - ys[i]) * (x - xs[i])) // dx
    return ys[n - 1]


def main():
    imgs = sorted(IMG_DIR.glob("_v88_*_plain_image.bin"))
    if not imgs:
        print(f"no V88 image under {IMG_DIR}")
        return
    img = imgs[0].read_bytes()
    print(f"image: {imgs[0].name}  ({len(img)} B)")

    print("\n" + "=" * 88)
    print("THE DAMPER SURFACE ON THE FLOWN V88, read from its own bytes")
    print("=" * 88)
    tables = {}
    for label, ptrs in (("FactorC (SPEED)", FACTOR_C_PTRS), ("FactorE (RATE)", FACTOR_E_PTRS),
                        ("FactorB", FACTOR_B_PTRS), ("FactorD", FACTOR_D_PTRS)):
        print(f"\n  {label}   ptr array 0x{ptrs:05X}")
        for m in MODES:
            rec = factor_rec(img, ptrs, m)
            n, xs, ys = rec_any(img, rec)
            tables.setdefault(label, {})[m] = (n, xs, ys, rec)
            unit = ("km/h" if "SPEED" in label else "deg/s" if "RATE" in label else "")
            phys = ""
            if "SPEED" in label:
                phys = "  = " + "/".join(f"{x*KMH_PER_CT:.0f}" for x in xs) + " km/h"
            elif "RATE" in label:
                phys = "  = " + "/".join(f"{x*DEGS_PER_CT:.1f}" for x in xs) + " deg/s"
            print(f"    mode {m:2d} @0x{rec:05X}  n={n}  X={xs}{phys}")
            print(f"                            Y={ys}")

    print("\n  ceiling  ptr array 0x%05X" % CEILING_PTRS)
    for m in MODES:
        rec = factor_rec(img, CEILING_PTRS, m)
        n, xs, ys = rec_any(img, rec)
        print(f"    mode {m:2d} @0x{rec:05X}  n={n}  X={xs}  Y={ys}")

    # ---------------------------------------------------------------- the 2-D surface
    print("\n" + "=" * 88)
    print("ch0 = (FactorC(speed) * FactorE(rate)) >> 10   -- MODE 26 (engaged), V88 bytes")
    print("=" * 88)
    nC, xC, yC, _ = tables["FactorC (SPEED)"][26]
    nE, xE, yE, _ = tables["FactorE (RATE)"][26]
    speeds_kmh = [2, 5, 10, 20, 30, 34, 36, 45, 60, 80, 100]
    rates_degs = [1, 3, 6, 10, 12, 14, 20, 40, 80, 150]
    print(f"  {'':>10s}" + "".join(f"{r:>7.0f}" for r in rates_degs) + "   <- |rate| deg/s")
    for kmh in speeds_kmh:
        sp_ct = int(round(kmh / KMH_PER_CT))
        c = lerp_int(sp_ct, nC, xC, yC)
        row = ""
        for rd in rates_degs:
            rt_ct = int(round(rd / DEGS_PER_CT))
            e = lerp_int(rt_ct, nE, xE, yE)
            row += f"{(c * e) >> 10:>7d}"
        print(f"  {kmh:>6.0f} km/h" + row)
    print("  (every zero is a regime where the base-assist damper contributes NOTHING)")

    # ---------------------------------------------------------------- duty on route 73
    print("\n" + "=" * 88)
    print("HOW MUCH OF THE OPERATOR'S SYMPTOM REGIME IS THE DAMPER ABSENT FROM?")
    print("route 73 (V88), ENGAGED frames only, measured (speed, rate) distribution")
    print("=" * 88)
    z = np.load(ROOT / "_scratch/cache/r73" / "r73.npz", allow_pickle=True)
    eng = np.asarray(z["cc_lat"], float) > 0.5
    v_kmh = np.asarray(z["cs_v"], float)[eng] * 3.6
    rate = np.abs(np.asarray(z["rate_c"], float))[eng]
    n = len(v_kmh)
    speed_dead = v_kmh < 34.97
    rate_dead = rate < 12.73
    print(f"  engaged frames: {n}  ({n / 101.06:.0f} s)")
    print(f"    FactorC SPEED dead zone (<34.97 km/h) : {100*speed_dead.mean():6.2f} %")
    print(f"    FactorE RATE  dead zone (<12.73 deg/s): {100*rate_dead.mean():6.2f} %")
    print(f"    EITHER dead  => damper contributes 0  : "
          f"{100*(speed_dead | rate_dead).mean():6.2f} %")
    print(f"    BOTH live    => damper contributes >0 : "
          f"{100*(~speed_dead & ~rate_dead).mean():6.2f} %")

    print("\n  Split by the operator's own symptom regimes:")
    for lab, m in (("micro-ratcheting  (|rate| 1-13 deg/s, any speed)",
                    (rate >= 1) & (rate < 12.73)),
                   ("ratcheting        (|rate| >= 13 deg/s, any speed)", rate >= 12.73),
                   ("...of those, at parking-lot speed (<35 km/h)", (rate >= 12.73) & speed_dead),
                   ("...of those, above 35 km/h", (rate >= 12.73) & ~speed_dead)):
        if m.sum() == 0:
            print(f"    {lab:52s}  n=0")
            continue
        live = (~speed_dead & ~rate_dead)[m]
        print(f"    {lab:52s}  {m.sum()/101.06:6.1f} s   damper live on "
              f"{100*live.mean():5.1f} % of it")

    # ---------------------------------------------------------------- what V86B did
    print("\n" + "=" * 88)
    print("WHAT V86B ACTUALLY TESTED (route 70) -- and what it could not test")
    print("=" * 88)
    v86b = sorted(IMG_DIR.glob("_v86b_*_plain_image.bin"))
    if v86b:
        b = v86b[0].read_bytes()
        for label, ptrs in (("FactorC", FACTOR_C_PTRS), ("FactorE", FACTOR_E_PTRS)):
            for m in (24, 26, 27):
                n_, xs, ys = rec_any(b, factor_rec(b, ptrs, m))
                n2, xs2, ys2 = rec_any(img, factor_rec(img, ptrs, m))
                tag = "" if (xs, ys) == (xs2, ys2) else "   <<< DIFFERS FROM V88"
                print(f"  V86B {label} m{m:2d}  X={xs}  Y={ys}{tag}")
        print("\n  => V86B lifted FactorC Y[0] to the record's own Y[3] (a FLAT speed axis at full")
        print("     authority) and left FactorE untouched. The RATE dead zone below 12.73 deg/s")
        print("     was still zero on V86B, so V86B never armed the damper for the operator's")
        print("     'spinning the wheel at all' regime -- only for 'spinning it quickly'.")
    else:
        print("  (V86B image not found)")


if __name__ == "__main__":
    main()
