#!/usr/bin/env python3
"""v78_surface_designspace.py -- the reachable (C_Y0, E_X0, E_X1, FactorC shape) design space.

Every candidate is scored on:
  k          ramp-regime incremental gain   ((C_Y0*E_Y1)>>10) / (E_X1 - E_X0)     [the GATE-2 scalar]
  M          the plateau magnitude          (C_Y0*E_Y1)>>10                        [ratchet damping]
  dose@r     the delivered damper counts at creep at rate r                        [grind performance]
and gated on the build scripts' OWN hard guards, each named where it is violated.

Guards, quoted from source:
  G1  build_v75_tva.derive_lever_cy0  : "ADD-ONLY: new = max(old, min(TARGET, cap))" -- C_Y0 may
      only RISE relative to the base image.
  G2  build_v75_tva.derive_lever_ex1  : "assert x1_new <= ex[1]" -- E_X1 may only move LEFT.
  G3  build_v74_tva                   : "E_X0_MIN_SAFE = 12 ... assert E_X0_NEW >= E_X0_MIN_SAFE".
  G4  build_v75_tva.FACTOR_E_Y_FROZEN : FactorE's whole Y row is frozen.
  G5  strict X monotonicity           : X[0] < X[1] < X[2] < X[3].
  G6  build_v75_tva._no_clip_ok       : every point the edit RAISES must stay <= ceiling floor 512,
      AND assert_no_clip additionally requires the GLOBAL peak to be unchanged.
"""
import math
import os
import struct
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                           r"C:\Users\dudei\Desktop\Projects\accord-firmwares")) / "analysis-2020accord"
STOCK = (ROOT / "stock_fw_dump" / "code.bin").read_bytes()
V74 = (ROOT / "_v74_engagedcols_x0_12_addonly_plain_image.bin").read_bytes()
V75 = (ROOT / "_v75_CY0.566-EX1.200_magprobe_plain_image.bin").read_bytes()

FACTOR_C_PTRS, FACTOR_E_PTRS, CEILING_PTRS = 0xC9E9C, 0xC9F84, 0xC77A0
LIVE_MODE = 26
SPEED_CTS_PER_KMH, RATE_CTS_PER_DEGS = 64.0, 4.7121
FLOOR = 512


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def rec(b, base):
    n = u16(b, base)
    return (list(struct.unpack_from(f"<{n}h", b, base + 2)),
            list(struct.unpack_from(f"<{n}h", b, base + 2 + 2 * n)))


def lerp_int(x, xs, ys):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for j in range(len(xs) - 1):
        if xs[j] <= x <= xs[j + 1]:
            s = xs[j + 1] - xs[j]
            return ((ys[j + 1] - ys[j]) * (x - xs[j])) // s + ys[j] if s else ys[j]
    return ys[-1]


CB = u32(STOCK, FACTOR_C_PTRS + 4 * LIVE_MODE)
EB = u32(STOCK, FACTOR_E_PTRS + 4 * LIVE_MODE)
CX, _ = rec(STOCK, CB)
EX_S, EY_S = rec(STOCK, EB)
CY_S = rec(STOCK, CB)[1]
CX_74, CY_74 = rec(V74, CB)
EX_74, EY_74 = rec(V74, EB)
CX_75, CY_75 = rec(V75, CB)
EX_75, EY_75 = rec(V75, EB)
EY = EY_75                      # frozen: [0, 539, 539, 927]

SPEEDS = list(range(0, 14001, 32))
RATES = list(range(0, 4501, 20))


def no_clip(cx, cy, ex, ey, base_cx, base_cy, base_ex, base_ey):
    """(passes, worst_raised, global_peak). Base = V74, the last build that flew clean."""
    cs = [lerp_int(v, cx, cy) for v in SPEEDS]
    es = [lerp_int(r, ex, ey) for r in RATES]
    bc = [lerp_int(v, base_cx, base_cy) for v in SPEEDS]
    be = [lerp_int(r, base_ex, base_ey) for r in RATES]
    peak = (max(cs) * max(es)) >> 10
    worst = 0
    ok = True
    for ci, cbv in zip(cs, bc):
        for ei, ebv in zip(es, be):
            now = (ci * ei) >> 10
            if now > ((cbv * ebv) >> 10):
                if now > worst:
                    worst = now
                if now > FLOOR:
                    ok = False
    base_peak = (max(bc) * max(be)) >> 10
    return ok, worst, peak, base_peak


def dose(cy0, ex, cy_rest, r, v=0):
    cy = [cy0] + cy_rest
    return (lerp_int(v, CX, cy) * lerp_int(r, ex, EY)) >> 10


SHAPES = {
    "V75 as flown   [Y1=234,Y2=429]": [234, 429, 908],
    "half-fill      [Y1=429,Y2=429]": [429, 429, 908],
    "monotone       [Y1=566,Y2=566]": [566, 566, 908],
}


def main():
    print("=" * 118)
    print("PART 4 -- THE DESIGN SPACE.   mode 26, FactorC @0x%05X, FactorE @0x%05X" % (CB, EB))
    print("  FactorE Y row FROZEN at %s (guard G4).  Ceiling floor %d." % (EY, FLOOR))
    print("  k* is bracketed in (0.580, 1.580] by V74 (clean, 1011 s) and V75 (faulted).")
    print("=" * 118)

    r99, r127, r94 = 99, 127, int(round(20 * RATE_CTS_PER_DEGS))
    print(f"\n  reference rates: 99 ct = {99/RATE_CTS_PER_DEGS:.1f} deg/s (measured in-burst p50), "
          f"127 ct = {127/RATE_CTS_PER_DEGS:.1f} deg/s (6-9 Hz arm), {r94} ct = 20.0 deg/s "
          "(the handoff's 'sustained drag' probe)")

    rows = []
    for shape_name, cy_rest in SHAPES.items():
        for cy0 in (429, 470, 500, 530, 566):
            for ex0 in (0, 6, 12):
                for ex1 in (200, 240, 260, 280, 300, 320, 350, 400):
                    ex = [ex0, ex1, EX_75[2], EX_75[3]]
                    cy = [cy0] + cy_rest
                    M = (cy0 * EY[1]) >> 10
                    k = M / (ex1 - ex0)
                    ok, worst, peak, bpeak = no_clip(CX, cy, ex, EY, CX_74, CY_74, EX_74, EY_74)
                    g = []
                    if cy0 < CY_74[0]:
                        g.append("G1(C_Y0<V74)")
                    if cy_rest[0] < CY_74[1] or cy_rest[1] < CY_74[2]:
                        g.append("G1(shape down)")
                    if ex1 > 400:
                        g.append("G2")
                    if ex0 < 12:
                        g.append("G3(X0<12)")
                    if not (ex0 < ex1 < ex[2] < ex[3]):
                        g.append("G5")
                    if not ok:
                        g.append("G6(no-clip)")
                    if peak != bpeak:
                        g.append("G6(peak moved %d->%d)" % (bpeak, peak))
                    rows.append(dict(shape=shape_name, cy0=cy0, ex0=ex0, ex1=ex1, M=M, k=k,
                                     d99=dose(cy0, ex, cy_rest, r99),
                                     d127=dose(cy0, ex, cy_rest, r127),
                                     d20=dose(cy0, ex, cy_rest, r94),
                                     d60=(lerp_int(3840, CX, cy) * lerp_int(r99, ex, EY)) >> 10,
                                     peak=peak, guards=",".join(g) or "-"))

    v75 = [r for r in rows if r["shape"].startswith("V75") and r["cy0"] == 566
           and r["ex0"] == 12 and r["ex1"] == 200][0]
    v74k = ((CY_74[0] * EY_74[1]) >> 10) / (EX_74[1] - EX_74[0])

    print("\n" + "-" * 118)
    print("  (4a) THE RATE-AXIS DESIGN SPACE.  k, M and creep dose depend ONLY on (C_Y0, E_X0, E_X1)")
    print("       -- the FactorC SHAPE (Y[1], Y[2]) cannot change any of them, because C = C_Y0 for")
    print("       every speed below X[0] = 2240 ct = 35 km/h.  Shape is a SEPARATE axis: table (4a2).")
    print("       'grind%' = dose@99ct as a fraction of V75-as-flown's 137.")
    print("-" * 118)
    print(f"  {'C_Y0':>5} {'E_X0':>5} {'E_X1':>5} {'X1 deg/s':>9} {'M':>4} {'k':>7} "
          f"{'dB/V74':>7} {'d@99':>5} {'d@127':>6} {'d@20dps':>8} {'grind%':>7}  {'guards'}")
    seen = set()
    for r in sorted(rows, key=lambda r: r["k"]):
        key = (r["cy0"], r["ex0"], r["ex1"])
        if key in seen or not (0.55 <= r["k"] <= 1.60):
            continue
        if not r["shape"].startswith("V75"):
            continue
        seen.add(key)
        db = 20 * math.log10(r["k"] / v74k)
        print(f"  {r['cy0']:>5} {r['ex0']:>5} {r['ex1']:>5} {r['ex1']/RATE_CTS_PER_DEGS:>9.1f} "
              f"{r['M']:>4} {r['k']:>7.4f} {db:>+7.2f} {r['d99']:>5} {r['d127']:>6} {r['d20']:>8} "
              f"{100 * r['d99'] / v75['d99']:>6.0f}%  {r['guards']}")

    print("\n" + "-" * 118)
    print("  (4a2) THE FactorC SHAPE AXIS -- affects the 35-140 km/h band ONLY, never creep, never k")
    print("-" * 118)
    print(f"  {'FactorC Y':28} {'dip':>18} {'d@60km/h,99ct':>14} {'d@80km/h,99ct':>14} "
          f"{'peak':>6}  guards")
    for shape_name, cy_rest in SHAPES.items():
        cy = [566] + cy_rest
        dips = [(i + 1, cy[i] - cy[i + 1]) for i in range(3) if cy[i + 1] < cy[i]]
        ok, worst, peak, bpeak = no_clip(CX, cy, EX_75, EY, CX_74, CY_74, EX_74, EY_74)
        g = []
        if not ok:
            g.append("G6(no-clip: raises a point above 512)")
        if peak != bpeak:
            g.append(f"G6(peak {bpeak}->{peak})")
        d60 = (lerp_int(3840, CX, cy) * lerp_int(99, EX_75, EY)) >> 10
        d80 = (lerp_int(5120, CX, cy) * lerp_int(99, EX_75, EY)) >> 10
        ds = ", ".join(f"idx{i}: -{d}" for i, d in dips) or "NONE (monotone)"
        print(f"  {str(cy):28} {ds:>18} {d60:>14} {d80:>14} {peak:>6}  {','.join(g) or '-'}")

    print("\n" + "-" * 118)
    print("  (4b) THE OPERATOR'S TWO REQUESTS, evaluated against the guards")
    print("-" * 118)
    for name, cy0, ex0, ex1, shape in (
            ("as flown V75                       ", 566, 12, 200, "V75 as flown   [Y1=234,Y2=429]"),
            ("V75 + 'extend FactorE X[0] to 0'   ", 566, 0, 200, "V75 as flown   [Y1=234,Y2=429]"),
            ("V75 + 'remove the FactorC dip' (C) ", 566, 12, 200, "half-fill      [Y1=429,Y2=429]"),
            ("V75 + 'shape C like E' (monotone)  ", 566, 12, 200, "monotone       [Y1=566,Y2=566]"),
            ("BOTH requests + monotone           ", 566, 0, 200, "monotone       [Y1=566,Y2=566]"),
            ("BOTH requests + half-fill          ", 566, 0, 200, "half-fill      [Y1=429,Y2=429]")):
        r = [x for x in rows if x["shape"] == shape and x["cy0"] == cy0 and x["ex0"] == ex0
             and x["ex1"] == ex1][0]
        print(f"  {name} k={r['k']:.4f} ({20*math.log10(r['k']/v74k):+.2f} dB vs V74)  "
              f"M={r['M']}  d@99={r['d99']}  d@20dps={r['d20']}  d@60km/h,99ct={r['d60']}  "
              f"guards: {r['guards']}")

    print("\n" + "-" * 118)
    print("  (4c) WHERE THE no-clip GUARD ACTUALLY BINDS on the monotone shape")
    print("-" * 118)
    for cy2 in (429, 470, 500, 530, 566, 600):
        cy = [566, min(566, cy2), cy2, 908]
        ok, worst, peak, bpeak = no_clip(CX, cy, [12, 200, 2500, 4000], EY,
                                         CX_74, CY_74, EX_74, EY_74)
        # first speed at which the RAISED surface exceeds the floor
        first = None
        for v in SPEEDS:
            c = lerp_int(v, CX, cy)
            cb = lerp_int(v, CX, CY_74)
            if c > cb and ((c * 927) >> 10) > FLOOR:
                first = v
                break
        print(f"    C_Y = {str(cy):24} no-clip={'PASS' if ok else 'FAIL'}  peak={peak} "
              f"(V74 {bpeak})  first offending speed = "
              f"{'--' if first is None else f'{first} ct = {first/SPEED_CTS_PER_KMH:.1f} km/h'}")
    print("\n    ⇒ the binding corner is (that speed, rate >= 4000 ct) where E = E_Y3 = 927.")
    print("      A C value above 566 there gives (C*927)>>10 > 512 = the ceiling floor.")

    print("\n" + "-" * 118)
    print("  (4d) k as a function of E_X1 for each C_Y0, at E_X0 = 12 and at E_X0 = 0")
    print("-" * 118)
    print(f"  {'E_X1':>6} {'deg/s':>7} | " + " | ".join(
        f"C_Y0={c}      " for c in (429, 470, 500, 530, 566)))
    print(f"  {'':>6} {'':>7} | " + " | ".join("X0=12   X0=0 " for _ in range(5)))
    for ex1 in (200, 220, 240, 260, 280, 300, 320, 340, 360, 380, 400):
        cells = []
        for c in (429, 470, 500, 530, 566):
            M = (c * EY[1]) >> 10
            cells.append(f"{M/(ex1-12):6.3f} {M/ex1:6.3f}")
        print(f"  {ex1:>6} {ex1/RATE_CTS_PER_DEGS:>7.1f} | " + " | ".join(cells))


if __name__ == "__main__":
    main()
