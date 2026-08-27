#!/usr/bin/env python3
r"""studies/sessions/v77/v77_dose_math.py -- the damper DOSE at 5 mph, the 150% target, and whether 4 breakpoints reach it.

WHAT THIS IS
------------
Exact integer arithmetic, mirroring `FUN_00034350` line for line, answering six questions:

  Q1  what "dose = 137" actually IS, and a from-the-bytes reproduction of the kit's dose table
  Q2  V75's (and V74's, V76's) damper output at 5 mph = 8.04672 km/h, as a function of rate
  Q3  the 150% target: dose number, implied k, loop gain vs V75 (faulted) and V76
  Q4  can FOUR breakpoints express it with a TRUE ReLU on BOTH factors?
  Q5  what N > 4 breakpoints would buy, numerically
  Q6  the loop-gain step, band by band, vs V74 (flew) and V76

The evaluator mirror itself is `studies/sessions/v76/v76_surface.py` (imported, not re-implemented) -- every arithmetic
line there carries the instruction address it mirrors.  Tables are byte-read LITTLE-ENDIAN from the
plain images; nothing about them is hard-coded here.

SPEED SCALE -- confirmed, not assumed  [EVIDENCE]
  `model/eps_lkas_chain_model.py:773`  COUNTS_PER_KMH = 64.0625, from FUN_000522fe (`x*41 >> 6` on a
  0.01 km/h raw value).  Anchor: stock FactorC mode-26 X[0] = 2240 counts, byte-read, and
  2240 / 64.0625 = 34.966 km/h -- the kit's "35.00 km/h" knee.  `studies/sessions/v76/v76_surface.py` uses a round 64.0;
  the two DISAGREE by 0.098% and BOTH map 5 mph to the SAME index, so nothing here turns on it:
      5 mph = 8.04672 km/h ->  x64.0625 = 515.49 -> 515 counts
                               x64.0    = 515.00 -> 515 counts
  RATE scale: gp-0x6ac0 = 4.7121 counts per deg/s (`model/eps_lkas_chain_model.py:1364`).

CEILING -- why 512 and not 512..1024  [EVIDENCE, model/eps_lkas_chain_model.py:928-936]
  ceiling = LERP(gp-0x6ac2, 0xC77A0[mode]), X=[300,800] Y=[512,1024] identical in all 26 modes.
  gp-0x6ac2 is a SIGN-GATED BACK-DRIVE detector (FUN_00041464 writes |motor rate|>>10 only when
  sign(motor rate) != sign(gp-0x6b98), else 0).  In ordinary same-sign driving the index is 0, the
  LERP hard-clamps to Y[0] and the ceiling sits on 512.  => size everything against 512.
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
import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import v76_surface as VS                                                        # noqa: E402
from v76_surface import Surface, lerp, u16, read_rec                            # noqa: E402

ROOT = VS.ROOT
# add the two images v76_surface does not know about
VS.IMAGES["v76"] = ROOT / "_v76_v38base_relu_damper_plain_image.bin"
VS.IMAGES["v73"] = ROOT / "_v73_plain_image.bin"

MODE = VS.MODE_ENGAGED          # 26 -- engaged.  mode 24 (manual) is byte-stock on every build here.
CPK_MODEL = 64.0625             # eps_lkas_chain_model.COUNTS_PER_KMH  (FUN_000522fe)
CPK_SURF = 64.0                 # v76_surface.SPEED_CTS_PER_KMH
RPD = VS.RATE_CTS_PER_DEGS      # 4.7121 counts per deg/s
CEIL_FLOOR = VS.CEILING_FLOOR   # 512
R_OP = 99                       # THE dose rate: measured in-burst p50, 21.0 deg/s
MPH_KMH = 1.609344
FIVE_MPH_KMH = 5 * MPH_KMH      # 8.04672
FIVE_MPH_CT = int(FIVE_MPH_KMH * CPK_MODEL)     # 515

BUILDS = ("stock", "v38", "v74", "v75", "v76")
OUT_JSON = Path(__file__).resolve().parents[3] / "_scratch/out/_v77_dose.json"
J = {}


def hdr(s):
    print("\n" + "=" * 108)
    print(s)
    print("=" * 108)


def kmh_ct(kmh, cpk=CPK_MODEL):
    return int(round(kmh * cpk))


def surf(build, mode=MODE, **kw):
    return Surface(build, mode, **kw)


def k_closed(s):
    """k = d(dose)/d(rate) on FactorE's FIRST segment, at the speed where FactorC = C_Y0.

    From v76_surface PART 1 (282,150-point exhaustive check):  dose(r) = k*(r - E_X0) exactly, with
        k = ((C * E_Y1) >> 10) / (E_X1 - E_X0)                  [E_Y0 = 0 on every build here]
    so k is simultaneously the ramp slope, the loop gain and the per-count slew coefficient."""
    C = s.XY("C")[1][0]
    X, Y = s.XY("E")
    assert Y[0] == 0, "k_closed assumes E_Y[0] == 0"
    return ((C * Y[1]) >> 10) / (X[1] - X[0])


def k_at_speed(s, speed_ct, truncated=False):
    """The same k with FactorC evaluated at an arbitrary speed (C_Y0 is only its creep value).

    🛑 TWO FORMS ARE IN CIRCULATION IN THE KIT'S OWN DOCS, and they differ by up to 0.5%:
        truncated:  ((C * E_Y1) >> 10) / (E_X1 - E_X0)   -- HANDOFF §3's build table (V75 1.580,
                    V76 1.3866, V74 0.5799).  The >>10 truncation is a DC bias, not a slope.
        float:      C * (E_Y1 - E_Y0)/(E_X1 - E_X0) / 1024  -- HANDOFF §4's risk table
                    (V74 0.529/0.423/0.317/0.482, V76 1.393).
    The FLOAT form is the correct incremental gain; the truncated one under-reads by <= 1024/(C*..).
    Both are reported so each handoff number is reproducible."""
    C = s.factorC(speed_ct)
    X, Y = s.XY("E")
    if truncated:
        return ((C * Y[1]) >> 10) / (X[1] - X[0])
    return C * (Y[1] - Y[0]) / (X[1] - X[0]) / 1024


# =====================================================================================================
# Q1 -- WHAT "DOSE" IS, AND THE TABLE REPRODUCED FROM THE BYTES
# =====================================================================================================
def q1():
    hdr("Q1 -- THE DEFINITION OF DOSE, AND THE HANDOFF TABLE REPRODUCED FROM THE FLOWN BYTES")
    print("""
  DEFINITION  [EVIDENCE -- read out of v76_surface.validate(), reproduced below from the images]

      dose  ==  |gp-0x6bd0|  the 16-bit value STORED by `st.h` at 0x3475C, in RAW COUNTS,
                evaluated at   |steering/motor rate| = 99 counts  ( = 21.0 deg/s, the measured
                in-burst p50 ), in ENGAGED mode 26, with seed = 1024 (gp-0x698a, pinned),
                FactorC's gate gp-0x67f4 == 1, and back-drive index gp-0x6ac2 = 0 (=> ceiling 512).

      It is ONE POINT on a 2-D surface, not the surface.  The full surface is
          dose(speed, rate) = clamp( ((((1024*B)>>10 * C(speed))>>10 * D)>>10 * E(rate))>>10, ceiling )
      with B = D = 1024 flat-unity in mode 26 (byte-verified below), so
          dose(speed, rate) = min( (C(speed) * E(rate)) >> 10 , 512 )        [sign stripped]

      1 count of gp-0x6bd0 = 1/1024 in the float mirror (Q10; FUN_000347b8 multiplies by 0.0009765625).
      The kit has NO conversion from gp-0x6bd0 to N.m -- dose is reported in raw counts only.

  The handoff's per-speed row is  dose(speed, 99)  at speeds 5 / 20 / 35 / 60 / 80 / 140 km/h,
  and "k(creep)" is the ramp slope of the SAME surface at creep speed, NOT a dose.
""")
    S = {b: surf(b) for b in BUILDS}
    ok = True

    print("  mode-26 tables, byte-read LITTLE-ENDIAN from the plain images:")
    for b in BUILDS:
        _, _, cx, cy = S[b].rec["C"]
        _, _, ex, ey = S[b].rec["E"]
        print("    %-6s FactorC X=%-26s Y=%-24s  FactorE X=%-24s Y=%s" % (b, cx, cy, ex, ey))
    print("    B/D flat unity (mode 26): B set=%s  D set=%s   ceiling fallback tp+0x7158 = %d"
          % (sorted({S["v75"].factorB(i) for i in range(0, 40000, 97)}),
             sorted({S["v75"].factorD(i) for i in range(0, 40000, 97)}),
             S["stock"].ceil_fallback))
    _, _, cex, cey = S["stock"].rec["CEIL"]
    print("    ceiling LERP table X=%s Y=%s  ->  at gp-0x6ac2 = 0 the ceiling is %d"
          % (cex, cey, S["stock"].ceiling(0)))

    SPEEDS = [5, 20, 35, 60, 80, 140]
    WANT = {"stock": (0.0, [0, 0, 0, 3, 6, 14]),
            "v38":   (0.0, [0, 0, 0, 3, 6, 14]),
            "v74":   (0.580, [50, 50, 50, 27, 50, 106]),
            "v75":   (1.580, [137, 137, 137, 56, 104, 220]),
            "v76":   (1.387, [137, 137, 137, 137, 137, 220])}

    print("\n  THE TABLE, recomputed from the bytes (dose = |gp-0x6bd0| at rate 99 ct = 21.0 deg/s):")
    print("    %-7s %9s | %s" % ("build", "k(creep)", " ".join("%7d" % v for v in SPEEDS)))
    print("    " + "-" * 86)
    rows = {}
    for b in BUILDS:
        s = S[b]
        k = k_closed(s) if s.XY("E")[1][1] else 0.0
        got = [s.mag(kmh_ct(v), R_OP) for v in SPEEDS]
        wk, wd = WANT[b]
        good = (got == wd) and abs(k - wk) < 0.001
        ok &= good
        rows[b] = dict(k=k, dose=got)
        print("    %-7s %9.4f | %s   [%s]  handoff k=%.3f dose=%s"
              % (b, k, " ".join("%7d" % v for v in got), "MATCH" if good else "*** MISMATCH ***",
                 wk, wd))

    print("\n  => the kit's record %s" % ("REPRODUCES BIT-FOR-BIT from the flown bytes. [EVIDENCE]"
                                          if ok else "*** DOES NOT REPRODUCE -- see mismatches ***"))
    print("  ⚠ one nuance the printed table hides: the 5/20/35 km/h columns are equal on V74/V75/V76")
    print("     because 5 and 20 km/h are BELOW FactorC X[0] = 2240 ct and take the Y[0] HARD CLAMP")
    print("     (0x3451E cmp / 0x34520 bh -> 0x34522 ld.hu 0x0[r10]).  35 km/h = 2240 ct hits the")
    print("     clamp too -- the compare is STRICT (`idx > X[0]`), so idx == X[0] is still Y[0].")
    J["q1"] = dict(definition_rate_counts=R_OP, definition_rate_degs=R_OP / RPD,
                   mode=MODE, seed=1024, ceiling_at_backdrive0=S["stock"].ceiling(0),
                   speeds_kmh=SPEEDS, rows=rows, reproduces=bool(ok),
                   tables={b: dict(C=S[b].XY("C"), E=S[b].XY("E")) for b in BUILDS})
    return S, ok


# =====================================================================================================
# Q2 -- V75 AT 5 MPH
# =====================================================================================================
def q2(S):
    hdr("Q2 -- THE DAMPER AT 5 mph = 8.04672 km/h = 515 COUNTS")
    print("""
  SPEED-COUNT CONVERSION, and where it is confirmed:
      model/eps_lkas_chain_model.py:773   COUNTS_PER_KMH = 64.0625, from FUN_000522fe (`x*41 >> 6` on a
                                    0.01 km/h raw value) -- NOT a clean 64.
      anchor                        stock FactorC mode-26 X[0] = 2240 ct (byte-read) and
                                    2240 / 64.0625 = 34.966 km/h == the kit's "35.00 km/h" knee.
      studies/sessions/v76/v76_surface.py:95             uses a round 64.0.  0.098% apart; BOTH give 515 counts at 5 mph,
                                    so no result here depends on the choice.
          5 mph = 8.04672 km/h  ->  515.49 ct (64.0625)   /   515.00 ct (64.0)   ->  index 515
""")
    print("  5 mph = %d counts.  FactorC X[0] = %d ct on every build => 515 is BELOW the first knot"
          % (FIVE_MPH_CT, S["stock"].XY("C")[0][0]))
    print("  => FactorC takes the Y[0] HARD CLAMP at 5 mph, so dose(5 mph, r) == dose(creep, r)")
    print("     EXACTLY, on every build in the table.  FactorC values at 515 ct:")
    for b in BUILDS:
        print("       %-6s C(515) = %-5d  (== C_Y[0] = %d)" % (b, S[b].factorC(FIVE_MPH_CT),
                                                               S[b].XY("C")[1][0]))

    print("\n  (2a) THE FULL CURVE at 5 mph: |gp-0x6bd0| vs |rate|, from the flown bytes")
    print("       %7s %9s | %7s %7s %7s %7s   %s"
          % ("rate ct", "deg/s", "stock", "V74", "V75", "V76", "note"))
    print("       " + "-" * 82)
    RATES = [0, 12, 25, 50, 60, 75, 94, 99, 119, 127, 150, 200, 246, 300, 400, 600,
             1200, 1941, 2500, 4000, 8000, 12998, 12999]
    curve = {b: [] for b in BUILDS}
    for r in RATES:
        vals = {b: S[b].mag(FIVE_MPH_CT, r) for b in BUILDS}
        for b in BUILDS:
            curve[b].append(vals[b])
        note = ""
        if r == R_OP:
            note = "<= THE DOSE POINT"
        if r == 12999:
            note = "<= |rate| >= 0x32C9 gate -> DOSE FORCED 0 (0x345FA/0x34612)"
        if vals["v75"] == CEIL_FLOOR or vals["v76"] == CEIL_FLOOR:
            note = note or "<= at the 512 ceiling"
        print("       %7d %9.1f | %7d %7d %7d %7d   %s"
              % (r, r / RPD, vals["stock"], vals["v74"], vals["v75"], vals["v76"], note))

    print("\n  (2b) THE SCALARS")
    q2j = {}
    for b in ("v74", "v75", "v76"):
        s = S[b]
        k = k_closed(s)
        d = s.mag(FIVE_MPH_CT, R_OP)
        X, Y = s.XY("E")
        # where the surface first touches the 512 ceiling at this speed
        rail = next((r for r in range(0, 0x32C9) if s.mag(FIVE_MPH_CT, r) >= CEIL_FLOOR), None)
        peak = max(s.mag(FIVE_MPH_CT, r) for r in range(0, 0x32C9))
        q2j[b] = dict(dose_at_5mph=d, k=k, E=[X, Y], C_Y0=s.XY("C")[1][0],
                      rail_rate_ct=rail, peak=peak)
        print("       %-4s dose(5 mph, 99 ct) = %-4d counts    k = %.4f ct/ct    "
              "E_X=[%d,%d] E_Y1=%d  C_Y0=%d" % (b.upper(), d, k, X[0], X[1], Y[1], s.XY("C")[1][0]))
        print("            ramp holds to rate %d ct (%.0f deg/s); supremum over the legal rate "
              "domain = %d%s" % (X[1], X[1] / RPD, peak,
                                 "  (== the 512 ceiling)" if peak == CEIL_FLOOR else ""))
        if rail is not None:
            print("            first touches the 512 ceiling at rate %d ct = %.0f deg/s"
                  % (rail, rail / RPD))

    print("""
  🛑 THE SCALAR THE OPERATOR MEANS BY "V75'S DAMPER DOSE AT 5 mph" IS **137 COUNTS** of gp-0x6bd0,
     at |rate| = 99 ct = 21.0 deg/s.  [EVIDENCE -- byte-read tables, integer mirror, and it is the
     same number the V76 handoff prints in the 5 km/h column, because 5 mph and 5 km/h and 20 km/h
     and 35 km/h are all inside FactorC's Y[0] clamp and therefore all give the same dose.]
  ⚠ "137" is NOT the damper at 5 mph -- it is the damper at 5 mph AT ONE RATE.  Along rate, V75 at
     5 mph runs 0 -> 137 (99 ct) -> 297 (200 ct, where its E_Y1 = E_Y2 PLATEAU starts) -> flat 297
     all the way to 2500 ct -> 512 (the ceiling) at 4000 ct.  Any "150%" statement is really a
     statement about the RAMP SLOPE k, because dose(r) = k*(r - E_X0): pinning 137 at r = 99 pins k.
""")
    J["q2"] = dict(five_mph_kmh=FIVE_MPH_KMH, five_mph_counts=FIVE_MPH_CT,
                   cpk_model=CPK_MODEL, cpk_surface=CPK_SURF, rates=RATES,
                   curve=curve, scalars=q2j,
                   headline="V75 dose at 5 mph = 137 counts of gp-0x6bd0 at 99 ct rate")
    return q2j


# =====================================================================================================
# Q3 -- THE 150% TARGET
# =====================================================================================================
def q3(S):
    hdr("Q3 -- THE 150% TARGET:  1.50 x V75's 5 mph DOSE")
    d75 = S["v75"].mag(FIVE_MPH_CT, R_OP)
    d76 = S["v76"].mag(FIVE_MPH_CT, R_OP)
    d74 = S["v74"].mag(FIVE_MPH_CT, R_OP)
    target_exact = 1.50 * d75
    print("  (a) THE DOSE NUMBER")
    print("      V75 at 5 mph, 99 ct  = %d counts" % d75)
    print("      1.50 x %d            = %.1f  ->  the integer surface can deliver 205 or 206;"
          % (d75, target_exact))
    print("                              206 is %.2f%%, 205 is %.2f%%.  I size on **206**."
          % (100 * 206 / d75, 100 * 205 / d75))
    print("      for reference: V74 = %d (37.2%% of V75), V76 = %d (100%% of V75)" % (d74, d76))

    print("\n  (b) THE IMPLIED k   -- from the proven identity  dose(r) = k*(r - E_X0)")
    print("      k = dose / (r - E_X0),  r = %d, and E_X0 >= 0 is the ONLY free lever on the ratio."
          % R_OP)
    print("        %-14s %8s %10s %10s %10s" % ("E_X0", "k(206)", "k(205)", "vs V75", "vs V76"))
    k75, k76, k74 = k_closed(S["v75"]), k_closed(S["v76"]), k_closed(S["v74"])
    kbest = None
    for ex0 in (0, 6, 12, 20, 30):
        k206, k205 = 206 / (R_OP - ex0), 205 / (R_OP - ex0)
        if ex0 == 0:
            kbest = k206
        print("        E_X0 = %-7d %8.4f %10.4f %9.3fx %9.3fx"
              % (ex0, k206, k205, k206 / k75, k206 / k76))
    print("      => the ARITHMETIC MINIMUM is k = 206/99 = %.4f at E_X0 = 0.  Nothing in these two"
          % kbest)
    print("         tables can deliver 206 counts at 99 ct of rate for less loop gain than that.")

    print("\n  (c) WHAT THAT MEANS FOR LOOP GAIN")
    print("      %-26s %8s %10s" % ("build", "k(creep)", "vs 150% surface"))
    for nm, k in (("stock / V38", 0.0), ("V74  (flew; then faulted)", k74),
                  ("V75  (HARD-FAULTED)", k75), ("V76  (flew)", k76),
                  ("150% surface, E_X0 = 0", kbest)):
        print("      %-26s %8.4f %10s" % (nm, k, "--" if k == kbest else
                                          ("n/a" if k == 0 else "%.3fx" % (kbest / k))))
    print("""
      [EVIDENCE] the 150%% surface sits **%.1f%% ABOVE the k of the build that hard-faulted (V75)**
      and **%.1f%% above V76's**.  V75's k was 1.5798 and it faulted; V76's is 1.3866 and it flew.
      The 150%% surface is the FIRST point in this lineage above V75's loop gain.
      ⚠ [BELIEF, and the kit's own conclusion] k is NOT the established fault-risk metric -- the
      hard-fault mechanism was pinned to the FRICTION lane crossing a 512-count monitor ceiling
      (`0xC407E` vs `0xC4004`), which a V38 base closes by construction and which no FactorC/FactorE
      value touches.  k is the GATE-2 loop-gain metric, not the DTC-0x1d metric.  Raising k past
      V75's is a stability question, not a re-opening of the fault.
""" % (100 * (kbest / k75 - 1), 100 * (kbest / k76 - 1)))

    # the cheapest concrete realisation: V76 with E_Y[1] scaled
    print("  (d) THE CHEAPEST REALISATION -- V76 with FactorE Y[1] alone")
    CX, CY = S["v76"].XY("C")
    EX, EY = S["v76"].XY("E")
    img = VS.load("v76")
    best = None
    for ey1 in range(EY[1], 900):
        cand = Surface(img=img, override={"C": (CX, CY), "E": (EX, [0, ey1, max(ey1, EY[2]), EY[3]])})
        if cand.mag(FIVE_MPH_CT, R_OP) == 206:
            best = (ey1, cand)
            break
    ey1, cand = best
    kc = ((CY[0] * ey1) >> 10) / (EX[1] - EX[0])
    print("      FactorE Y[1] %d -> %d  (ONE u16 cell, 2 bytes, at 0xD7818)   =>  dose = %d, k = %.4f"
          % (EY[1], ey1, cand.mag(FIVE_MPH_CT, R_OP), kc))
    print("      plateau still removed (Y1 %d < Y2 %d)? %s ; Y monotone? %s"
          % (ey1, EY[2], ey1 < EY[2], all(a <= b for a, b in zip([0, ey1, EY[2], EY[3]],
                                                                 [ey1, EY[2], EY[3], 1 << 20]))))
    print("      dose by speed (5/20/35/60/80/140 km/h): %s"
          % [cand.mag(kmh_ct(v), R_OP) for v in (5, 20, 35, 60, 80, 140)])
    J["q3"] = dict(v75_dose=d75, target_exact=target_exact, target_int=206,
                   k_min=kbest, k_v74=k74, k_v75=k75, k_v76=k76,
                   ratio_vs_v75=kbest / k75, ratio_vs_v76=kbest / k76,
                   cheapest=dict(E_Y1=ey1, k=kc, tables=dict(C=[CX, CY],
                                                             E=[EX, [0, ey1, EY[2], EY[3]]])))
    return 206, kbest, cand


# =====================================================================================================
# Q4 -- CAN 4 BREAKPOINTS EXPRESS A TRUE ReLU ON BOTH FACTORS AT 150%?
# =====================================================================================================
# used-index-range definitions
RANGES = {
    "GATE":     dict(smax=0x7D00 - 1, rmax=0x32C9 - 1,
                     note="the firmware's own gates: FactorC bypassed at speed >= 0x7D00 (499.5 km/h); "
                          "FactorE forces dose 0 at |rate| >= 0x32C9 (2731 deg/s)"),
    "TABLE":    dict(smax=8960, rmax=4000,
                     note="the stock tables' own spans (140 km/h / 849 deg/s)"),
    "OBSERVED": dict(smax=8960, rmax=1941,
                     note="140 km/h and route-5d max steering rate 412 deg/s (kit RULE 8)"),
}


def relu_table(anchor_x, anchor_y, mults):
    """A 4-point table that is EXACTLY a ReLU through the ORIGIN of the index, pinned so that the
    LERP returns `anchor_y` EXACTLY at index `anchor_x`.

    Construction: knee at X[0] = 0, and X[i] = anchor_x * mults[i-1], Y[i] = anchor_y * mults[i-1].
    Every knot is then exactly on the line y = (anchor_y/anchor_x)*x, and because the first knot is
    an INTEGER MULTIPLE of anchor_x the truncating `divq` at 0x34560 returns anchor_y with zero
    error at the anchor:
        num = Y[1]*(anchor_x - 0) = anchor_y*m1*anchor_x ;  den = X[1] = anchor_x*m1
        q   = num/den = anchor_y   EXACTLY, no truncation.
    Returns None on u16 overflow / non-strict X."""
    X = [0] + [anchor_x * m for m in mults]
    Y = [0] + [anchor_y * m for m in mults]
    if any(X[i] >= X[i + 1] for i in range(3)):
        return None
    if X[-1] > 0xFFFF or Y[-1] > 0xFFFF:
        return None
    return X, Y


def is_true_relu(X, Y, idx_lo, idx_hi):
    """Strict test of the operator's definition over [idx_lo, idx_hi]:
       one knee, one constant slope, NO flat floor > 0, NO plateau/saturation inside the range."""
    fail = []
    if Y[0] != 0:
        fail.append("Y[0]=%d != 0 -> a FLAT FLOOR of %d over [0, X0=%d]" % (Y[0], Y[0], X[0]))
    # knots collinear through (X[0], 0)?
    for i in (1, 2, 3):
        if Y[i] * (X[1] - X[0]) != Y[1] * (X[i] - X[0]):
            fail.append("knot %d off the line through (X0,0): Y=%d, line gives %.3f"
                        % (i, Y[i], Y[1] * (X[i] - X[0]) / (X[1] - X[0])))
    # plateau above X[3] inside the used range?
    if X[3] <= idx_hi:
        fail.append("PLATEAU at Y[3]=%d over [%d, %d] -- X[3]=%d is inside the used range (<= %d)"
                    % (Y[3], X[3], idx_hi, X[3], idx_hi))
    if any(Y[i] > Y[i + 1] for i in range(3)):
        fail.append("Y not monotone")
    return fail


def add_only_dose(cand, base, smax, rmax, sstep=8, rstep=8):
    """The V76 guard, on the DOSE SURFACE: |gp-0x6bd0| must never DROP below the base anywhere."""
    worst, at, n = 0, None, 0
    for v in range(0, smax + 1, sstep):
        for r in range(0, rmax + 1, rstep):
            n += 1
            d = base.mag(v, r) - cand.mag(v, r)
            if d > worst:
                worst, at = d, (v, r)
    return worst, at, n


def q4(S):
    hdr("Q4 -- CAN FOUR BREAKPOINTS DELIVER 150% AT 5 mph WITH A TRUE ReLU ON *BOTH* FACTORS?")
    print("""
  THE CONSTRAINT SET, as given:
    (i)   dose(515 ct, 99 ct) = 206          [1.50 x V75]
    (ii)  BOTH factors a TRUE ReLU:  y = max(0, k*(x - x0))
          one knee, one constant slope, no flat floor, NO plateau/saturation in the used index range
    (iii) E_Y[0] = 0                          [the Coulomb-relay rule]
    (iv)  add-only vs stock on the dose surface
    (v)   Y monotone non-decreasing, X strictly increasing

  FIRST, THE STRUCTURAL FACTS THAT DECIDE IT  [EVIDENCE, from the evaluator itself]
    * The evaluator ALWAYS clamps: `Y[0]` below `X[0]` (0x3451E/20/22) and `Y[n-1]` above `X[n-1]`
      (0x3452A/2C/38).  Those two clamps are structural and INDEPENDENT OF THE POINT COUNT.
      => "no plateau inside the used range" is satisfiable ONLY by pushing X[n-1] to or past the
      top of that range.  It is a RANGE requirement, not a point-count requirement.
    * A ReLU has 2 degrees of freedom (knee, slope).  A 4-point table has 8 numbers and needs only
      3 collinearity equations -- so a ReLU is EXACTLY representable in 4 points whenever the
      integer/u16 arithmetic permits.  The point count is NOT the binding constraint.
    * Y is u16.  With the knee at x0 and slope s, Y[3] = s*(X[3] - x0) <= 65535 caps the slope
      once X[3] is forced to the top of the used range.  THAT is the binding constraint.
""")
    # ---- the analytic reachability bound -------------------------------------------------------
    print("  (4a) THE ANALYTIC REACHABILITY BOUND")
    print("       C(515) = s_C*(515 - c0) <= 65535*(515 - c0)/(Smax - c0), maximal at c0 = 0")
    print("       E(99)  = s_E*( 99 - e0) <= 65535*( 99 - e0)/(Rmax - e0), maximal at e0 = 0")
    print("       dose_max(515,99) = (C(515)*E(99)) >> 10")
    print()
    print("       %-10s %8s %8s | %10s %10s %12s %10s"
          % ("range", "Smax", "Rmax", "max C(515)", "max E(99)", "max dose", "vs 206"))
    q4j = {"bound": {}}
    for nm, R in RANGES.items():
        cmax = 0xFFFF * 515 // R["smax"]
        emax = 0xFFFF * 99 // R["rmax"]
        dmax = (cmax * emax) >> 10
        q4j["bound"][nm] = dict(smax=R["smax"], rmax=R["rmax"], c515=cmax, e99=emax, dose=dmax)
        print("       %-10s %8d %8d | %10d %10d %12d %10s"
              % (nm, R["smax"], R["rmax"], cmax, emax, dmax,
                 "REACHABLE" if dmax >= 206 else "*** UNREACHABLE ***"))
    print("       => 206 is reachable under EVERY range definition, the strictest with %.2fx margin."
          % (q4j["bound"]["GATE"]["dose"] / 206))

    # ---- the constructive solution -------------------------------------------------------------
    print("\n  (4b) A CONSTRUCTIVE SOLUTION under the STRICTEST range (GATE), exact integers")
    smax, rmax = RANGES["GATE"]["smax"], RANGES["GATE"]["rmax"]
    img = VS.load("v76")
    base = S["stock"]

    # FactorC: knee at 0, knots at multiples of 515 so X[3] >= 31999 (never clamps high in-range).
    # FactorE: knee at 0, knots at multiples of  99 so X[3] >= 12998 (never clamps high in-range).
    CM = (21, 42, 63)       # 515*63 = 32445 > 31999
    EM = (44, 88, 132)      # 99*132 = 13068 > 12998
    sol = None
    for c515 in range(53, 1100):
        CT = relu_table(FIVE_MPH_CT, c515, CM)
        if CT is None:
            continue
        Cx, Cy = CT
        if Cx[-1] < smax or lerp(Cx, Cy, FIVE_MPH_CT) != c515:
            continue
        e99 = next((e for e in range(1, 0x10000) if (c515 * e) >> 10 == 206), None)
        if e99 is None:
            continue
        ET = relu_table(R_OP, e99, EM)
        if ET is None:
            continue
        Ex, Ey = ET
        if Ex[-1] < rmax or lerp(Ex, Ey, R_OP) != e99:
            continue
        cand = Surface(img=img, override={"C": (Cx, Cy), "E": (Ex, Ey)})
        if cand.mag(FIVE_MPH_CT, R_OP) != 206:
            continue
        if is_true_relu(Cx, Cy, 0, smax) or is_true_relu(Ex, Ey, 0, rmax):
            continue
        w, at, n = add_only_dose(cand, base, smax, rmax, 64, 16)
        if w:
            continue
        sol = dict(C=[Cx, Cy], E=[Ex, Ey], dose=cand.mag(FIVE_MPH_CT, R_OP),
                   addonly_worst=w, addonly_at=at, addonly_n=n, surf=cand,
                   c515=c515, e99=e99)
        break

    if sol is None:
        print("       *** no solution found in the constructive family ***")
        J["q4"] = q4j
        return None

    print("       FactorC  X = %s" % sol["C"][0])
    print("                Y = %s     knee 0, slope %d/%d = %.6f per speed count"
          % (sol["C"][1], sol["c515"], FIVE_MPH_CT, sol["c515"] / FIVE_MPH_CT))
    print("       FactorE  X = %s" % sol["E"][0])
    print("                Y = %s   knee 0, slope %d/%d = %.4f per rate count"
          % (sol["E"][1], sol["e99"], R_OP, sol["e99"] / R_OP))
    print("       C(515) = %d   E(99) = %d   dose(515,99) = %d  ✅"
          % (sol["c515"], sol["e99"], sol["dose"]))
    print("       true-ReLU C over [0,%d]: %s      true-ReLU E over [0,%d]: %s"
          % (smax, "PASS", rmax, "PASS"))
    print("       E_Y[0] = 0: PASS      X strict: PASS      Y monotone: PASS")
    print("       add-only vs stock on the dose surface: worst DROP = %d counts over %s points  %s"
          % (sol["addonly_worst"], "{:,}".format(sol["addonly_n"]),
             "PASS" if sol["addonly_worst"] == 0 else "*** FAIL ***"))
    print("\n  🛑 ANSWER TO Q4: **YES.** All five constraints are simultaneously satisfiable in four")
    print("     breakpoints, exactly, in integers, under the STRICTEST reading of 'used index range'.")
    print("     The point count was never the obstacle -- a ReLU is 2 degrees of freedom and a")
    print("     4-point table has 8 numbers.  [EVIDENCE: the table above, evaluated on the mirror.]")

    # ---- and now the price -----------------------------------------------------------------------
    print("""
  (4c) 🛑 AND HERE IS WHAT IT COSTS -- the constraint that DOES break, and by how much.

       A true-ReLU FactorC is proportional to SPEED.  Its knee must sit below 515 ct or the dose at
       5 mph is zero, so
           C(v) / C(515) = (v - c0) / (515 - c0)   >=   v / 515      (minimal at c0 = 0)
       and the dose surface inherits the same ratio.  With dose(515, 99) pinned at 206 the dose at
       any higher speed is FORCED:""")
    cand = sol["surf"]
    print("       %8s %8s | %10s %10s %12s %14s"
          % ("km/h", "ct", "C(v)", "dose@99", "x the 512 cap", "rails above"))
    rows = []
    for kmh in (5 * MPH_KMH, 20, 35, 45, 60, 80, 100, 120, 140):
        v = kmh_ct(kmh)
        c = cand.factorC(v)
        raw = (c * sol["e99"]) >> 10            # pre-ceiling dose
        rail = next((r for r in range(0, 0x32C9) if cand.mag(v, r) >= CEIL_FLOOR), None)
        rows.append(dict(kmh=kmh, ct=v, C=c, dose_raw=raw, rail_ct=rail))
        print("       %8.1f %8d | %10d %10d %12.1fx %10s"
              % (kmh, v, c, raw, raw / CEIL_FLOOR,
                 "--" if rail is None else "%d ct = %.1f deg/s" % (rail, rail / RPD)))
    v140 = kmh_ct(140)
    print("""
       [EVIDENCE, and it is PARAMETER-FREE]  dose(v,99) = (C(v)*E(99))>>10 and C(v) = s_C*v with the
       knee at 0, so   dose(v,99) / dose(515,99) = v / 515   EXACTLY, whatever s_C and E(99) are.
       The %.2fx speed ratio %d/515 is fixed by the ReLU geometry alone.  ANY true-ReLU FactorC
       (4-point OR N-point) delivering 206 counts at 5 mph delivers %.0f counts of RAW dose at
       140 km/h -- %.2fx the 512 ceiling.  Choosing a different C(515) does not move it one count.
       The output is therefore CEILING-RAILED above ~%.0f deg/s at 140 km/h and ~%.0f deg/s at 60.
""" % (v140 / FIVE_MPH_CT, v140, 206 * v140 / FIVE_MPH_CT, 206 * v140 / FIVE_MPH_CT / CEIL_FLOOR,
       rows[-1]["rail_ct"] / RPD,
       next(r["rail_ct"] for r in rows if abs(r["kmh"] - 60) < 0.1) / RPD))
    print("""
       🛑 A railed damper with a sign taken from a DIFFERENT cell (gp-0x6abe, 0x3469E-0x346A2) is
       exactly the Coulomb relay that rule (iii) exists to forbid: constant magnitude 512, sign
       flipping at every rate zero crossing, describing function 4*512/(pi*A) unbounded as the
       oscillation amplitude falls.  Forbidding it at E_Y[0] and then re-creating it at the ceiling
       is the same hazard by another route.

       ⇒ The constraint that breaks is NOT one of the five as written.  It is the SIXTH, implicit
         one -- "the damper must not saturate".  Raw dose vs the 512 ceiling: %.2fx at 140 km/h,
         %.2fx at 60 km/h, %.2fx at 5 mph (i.e. it is at the edge already at the design point).
""" % (rows[-1]["dose_raw"] / CEIL_FLOOR,
       next(r["dose_raw"] for r in rows if abs(r["kmh"] - 60) < 0.1) / CEIL_FLOOR,
       rows[0]["dose_raw"] / CEIL_FLOOR))

    # the feasible envelope under the strictest range
    lo = next(c for c in range(1, 2000)
              if any((c * e) >> 10 == 206 for e in range(1, 0xFFFF // EM[-1] + 1)))
    hi = max(c for c in range(1, 0xFFFF // CM[-1] + 1)
             if any((c * e) >> 10 == 206 for e in range(1, 0xFFFF // EM[-1] + 1)))
    print("       ⊕ the FEASIBLE ENVELOPE under the GATE range is narrow: C(515) in [%d, %d] and"
          % (lo, hi))
    print("         E(99) <= %d (u16 / %d).  The solution above takes the SMALLEST feasible C(515),"
          % (0xFFFF // EM[-1], EM[-1]))
    print("         which is the least-bad choice -- and it still rails.  [EVIDENCE]")
    q4j["envelope"] = dict(c515_lo=lo, c515_hi=hi, e99_max=0xFFFF // EM[-1])
    # what a NON-ReLU FactorC costs instead
    print("  (4d) THE SAME 150% DOSE WITHOUT A ReLU FactorC -- for comparison, in the same 4 points")
    EX, EY = S["v76"].XY("E")
    ey1 = J["q3"]["cheapest"]["E_Y1"]
    alt = Surface(img=img, override={"C": S["v76"].XY("C"),
                                     "E": (EX, [0, ey1, EY[2], EY[3]])})
    print("       (V76's flat FactorC [566,566,566,908] + FactorE Y[1] %d -> %d)" % (EY[1], ey1))
    print("       %8s %8s | %10s %10s %12s %14s"
          % ("km/h", "ct", "C(v)", "dose@99", "x the 512 cap", "rails above"))
    alt_rails = []
    for kmh in (5 * MPH_KMH, 20, 35, 45, 60, 80, 100, 120, 140):
        v = kmh_ct(kmh)
        c = alt.factorC(v)
        raw = (c * lerp(EX, [0, ey1, EY[2], EY[3]], R_OP)) >> 10
        rail = next((r for r in range(0, 0x32C9) if alt.mag(v, r) >= CEIL_FLOOR), None)
        if rail is not None:
            alt_rails.append(rail)
        print("       %8.1f %8d | %10d %10d %12.2fx %10s"
              % (kmh, v, c, raw, raw / CEIL_FLOOR,
                 "--" if rail is None else "%d ct = %.1f deg/s" % (rail, rail / RPD)))
    w, at, n = add_only_dose(alt, base, 8960, 4000, 64, 16)
    print("       add-only vs stock: worst drop %d over %s points  %s"
          % (w, "{:,}".format(n), "PASS" if w == 0 else "FAIL"))
    relu_rails = [r["rail_ct"] for r in rows if r["rail_ct"] is not None]
    print("       => FLAT-C realisation of the SAME 150% dose: earliest rail over 5 mph..140 km/h")
    print("          is %d ct = %.0f deg/s.   ReLU-C realisation: %d ct = %.0f deg/s.  Ratio %.1fx."
          % (min(alt_rails), min(alt_rails) / RPD, min(relu_rails), min(relu_rails) / RPD,
             min(alt_rails) / min(relu_rails)))
    q4j["flatC_earliest_rail_ct"] = min(alt_rails)
    q4j["reluC_earliest_rail_ct"] = min(relu_rails)
    q4j["flatC_addonly_worst"] = w

    q4j["solution"] = dict(C=sol["C"], E=sol["E"], dose=sol["dose"],
                           addonly_worst=sol["addonly_worst"], rows=rows)
    J["q4"] = q4j
    return sol


# =====================================================================================================
# Q5 -- WHAT WOULD MORE BREAKPOINTS BUY?
# =====================================================================================================
def q5(S, sol):
    hdr("Q5 -- WHAT WOULD N > 4 BREAKPOINTS BUY?  (numerically)")
    img = VS.load("v76")
    smax, rmax = RANGES["GATE"]["smax"], RANGES["GATE"]["rmax"]
    print("""
  (5a) FOR A PURE ReLU: **EXACTLY ZERO.**  [EVIDENCE, constructive -- Q4b is the witness]
       A ReLU is 2 degrees of freedom.  A 4-point record carries 8 (4 X + 4 Y) and spends 3 on
       collinearity, leaving 5 spare.  Q4b exhibits an exact-integer true ReLU on BOTH factors,
       spanning the full gated index range, with zero add-only violations.  There is nothing an
       N-point table could add to a shape that 4 points already represent EXACTLY.
       The two clamps (Y[0] below X[0], Y[n-1] above X[n-1]) are structural and do not depend on n,
       and the u16 slope cap Y[n-1] = s*(X[n-1]-X[0]) <= 65535 does not depend on n either.

  (5b) FOR SHAPE FREEDOM: N - 1 independent slope segments.  n=4 gives THREE.
       Count the segments each candidate shape needs:""")
    shapes = [
        ("pure ReLU (knee + line)", 1, "4 pts: EXPRESSIBLE (Q4b)"),
        ("ReLU then hold (knee, plateau)", 2, "4 pts: EXPRESSIBLE"),
        ("ReLU, hold, high-speed rise", 3, "4 pts: EXPRESSIBLE -- this is the V76 shape's dual"),
        ("ReLU, hold, rise, taper (grind-2 sep. at BOTH ends)", 4, "4 pts: **NOT** expressible"),
        ("ReLU, hold, rise, taper, second hold", 5, "4 pts: **NOT** expressible"),
    ]
    print("       %-54s %10s   %s" % ("shape", "segments", "with n = 4"))
    for nm, seg, verd in shapes:
        print("       %-54s %10d   %s" % (nm, seg, verd))
    print("       => n = 4 is sufficient for every shape this session has proposed, and binds only")
    print("          at FOUR-segment shapes.  n = 5 buys the first of those; n = 6 the second.")

    print("\n  (5c) THE ONE MEASURABLE GAIN: how close can you get to 'ReLU at 5 mph AND bounded")
    print("       at 140 km/h'?  Metric = raw dose at 140 km/h, 99 ct, holding dose(515,99) = 206.")
    print("       Lower is better; 512 is the ceiling, so <= 512 means 'never rails at 99 ct'.")
    print()
    EX, EY = S["v76"].XY("E")
    ey1 = J["q3"]["cheapest"]["E_Y1"]
    Ecand = (EX, [0, ey1, EY[2], EY[3]])
    e99 = lerp(*Ecand, idx=R_OP)
    v140 = kmh_ct(140)

    def raw140(Cx, Cy):
        return (lerp(Cx, Cy, v140) * e99) >> 10

    rows = []
    # n=4, pure ReLU
    rows.append(("n=4  pure ReLU C (Q4b geometry)", sol["C"][0], sol["C"][1], "1 segment, TRUE ReLU",
                 0.0))
    # n=4, ReLU-to-5mph then hold then stock rise -- 3 segments, needs C(515)=566 for THIS E
    c515 = next(c for c in range(1, 4096) if (c * e99) >> 10 == 206)
    Cx4 = [0, FIVE_MPH_CT, 5120, 8960]
    Cy4 = [0, c515, c515, 908]
    rows.append(("n=4  ReLU->hold->stock rise", Cx4, Cy4, "3 segments, ReLU only to 5 mph",
                 FIVE_MPH_CT))
    # n=4, V76 flat
    rows.append(("n=4  V76 flat floor (no ReLU)", *S["v76"].XY("C"), "flat floor 566, then rise",
                 None))
    print("       %-34s %8s %10s %12s %10s"
          % ("FactorC", "C(140)", "raw@99", "x 512 cap", "dose@5mph"))
    for nm, Cx, Cy, note, knee in rows:
        cand = Surface(img=img, override={"C": (Cx, Cy), "E": Ecand})
        r = raw140(Cx, Cy)
        print("       %-34s %8d %10d %11.2fx %10d   %s"
              % (nm, lerp(Cx, Cy, v140), r, r / CEIL_FLOOR, cand.mag(FIVE_MPH_CT, R_OP), note))
    r_pure, r_hold = raw140(sol["C"][0], sol["C"][1]), raw140(Cx4, Cy4)
    print("""
       => the CONCRETE numeric gain from more points is NOT more ReLU -- it is the ability to keep
          a ReLU knee AND bound the high-speed end.  With n = 4 you can already do
          ReLU -> hold -> rise (3 segments), which drops the 140 km/h raw dose from %d to %d,
          a **%.1fx** reduction, and takes the surface from %.2fx the ceiling to %.2fx.
          n = 5 would add ONE more slope change -- enough to also taper FactorE above the
          grind-#2 band while keeping its ReLU knee, which n = 4 cannot do simultaneously.
       => [EVIDENCE] the point count buys ONE extra slope change per point.  It buys NOTHING for
          a pure ReLU.  Anyone proposing a table re-point should be asked which FOURTH segment
          they need; if they cannot name it, n = 4 is enough.
""" % (r_pure, r_hold, r_pure / max(1, r_hold), r_pure / CEIL_FLOOR, r_hold / CEIL_FLOOR))
    J["q5"] = dict(pure_relu_gain=0,
                   segments_per_n={n: n - 1 for n in (4, 5, 6, 7, 8)},
                   raw140_pure_relu=raw140(sol["C"][0], sol["C"][1]),
                   raw140_relu_hold=raw140(Cx4, Cy4),
                   raw140_v76flat=raw140(*S["v76"].XY("C")),
                   relu_hold_C=[Cx4, Cy4])
    return Cx4, Cy4, Ecand


# =====================================================================================================
# Q6 -- GATE 2 / RISK, BAND BY BAND
# =====================================================================================================
def q6(S, sol, relu_hold, Ecand):
    hdr("Q6 -- GATE 2 / RISK: THE LOOP-GAIN STEP, BAND BY BAND")
    img = VS.load("v76")
    Cx4, Cy4 = relu_hold
    ey1 = J["q3"]["cheapest"]["E_Y1"]
    EX, EY = S["v76"].XY("E")

    cands = [
        ("stock/V38", S["stock"].XY("C"), S["stock"].XY("E")),
        ("V74 (flew)", S["v74"].XY("C"), S["v74"].XY("E")),
        ("V75 (FAULTED)", S["v75"].XY("C"), S["v75"].XY("E")),
        ("V76 (flew)", S["v76"].XY("C"), S["v76"].XY("E")),
        ("150% flat-C", S["v76"].XY("C"), (EX, [0, ey1, EY[2], EY[3]])),
        ("150% ReLU-C hold", (Cx4, Cy4), Ecand),
        ("150% pure ReLU", tuple(sol["C"]), tuple(sol["E"])),
    ]
    BANDS = [(0, 5), (5, 15), (15, 35), (35, 45), (45, 55), (55, 65), (65, 80)]
    print("""
  k(v) = FactorC(v) * slope_E / 1024, evaluated at the BAND MIDPOINT -- the same construction that
  reproduces the V76 handoff's §4 V74 column (0.529 / 0.423 / 0.317 / 0.482).  Verified below.
  🛑 The handoff's 3.10x headline is TIME-WEIGHTED over route 61's engaged speed histogram
  (286.4 s = 47.3% of engaged driving at 35-80 km/h).  I do not have that histogram here, so the
  weighted totals below use the handoff's own band durations: 93.0 / 79.2 / 55.6 / 58.5 s.
  🛑 For the "150% pure ReLU" row, k is the UNCLAMPED slope.  That surface is CEILING-RAILED at
  those speeds (Q4c), so its k is not a linear loop gain at all -- it is a relay.  The row is
  printed to show the scale of the mismatch, NOT as a gain that could be flown.
""")
    DUR = {(35, 45): 93.0, (45, 55): 79.2, (55, 65): 55.6, (65, 80): 58.5}
    print("  %-20s %s" % ("band mid (km/h)", " ".join("%9.1f" % ((a + b) / 2) for a, b in BANDS)))
    print("  " + "-" * 104)
    ks = {}
    for nm, C, E in cands:
        s = Surface(img=img, override={"C": tuple(C), "E": tuple(E)})
        row = []
        for a, b in BANDS:
            v = kmh_ct((a + b) / 2)
            row.append(k_at_speed(s, v))
        ks[nm] = row
        print("  %-20s %s" % (nm, " ".join("%9.4f" % x for x in row)))

    print("\n  VERIFICATION against the V76 handoff §4's published numbers (float form,")
    print("  band midpoints converted at the handoff's own 64.0 counts/km-h -- see note below):")
    allok = True
    v74s = Surface(img=img, override={"C": tuple(S["v74"].XY("C")), "E": tuple(S["v74"].XY("E"))})
    for i, (a, b) in enumerate(BANDS):
        if (a, b) in DUR:
            want = {(35, 45): 0.529, (45, 55): 0.423, (55, 65): 0.317, (65, 80): 0.482}[(a, b)]
            got = k_at_speed(v74s, kmh_ct((a + b) / 2, CPK_SURF))
            good = abs(got - want) < 0.0006
            allok &= good
            print("    %2d-%2d km/h   V74 k got %.4f  handoff %.3f   %s"
                  % (a, b, got, want, "MATCH" if good else "*** MISMATCH ***"))
    got76 = ks["V76 (flew)"][3]
    good = abs(got76 - 1.393) < 0.0006
    allok &= good
    print("    V76 k (flat band)  got %.4f  handoff 1.393   %s"
          % (got76, "MATCH" if good else "*** MISMATCH ***"))
    print("    ⚠ the handoff's §3 build table quotes the TRUNCATED form for the same builds")
    print("      (V74 0.580, V75 1.580, V76 1.3866): %.4f / %.4f / %.4f here.  Two forms, both in"
          % (k_at_speed(S["v74"], 0, True), k_at_speed(S["v75"], 0, True),
             k_at_speed(S["v76"], 0, True)))
    print("      the same document, up to 0.5% apart.  Neither is wrong; quote which one you mean.")
    print("    ⚠ SPEED SCALE: the main table above uses 64.0625 ct/km-h (the golden model); the")
    print("      handoff used 64.0.  The ONLY cell that moves is V74 at 72.5 km/h (4644 vs 4640 ct,")
    print("      FactorC 356 vs 355): k %.4f vs %.4f.  No conclusion turns on it."
          % (k_at_speed(v74s, kmh_ct(72.5)), k_at_speed(v74s, kmh_ct(72.5, CPK_SURF))))
    print("    => the band construction %s" % ("REPRODUCES the handoff. [EVIDENCE]" if allok
                                               else "*** DOES NOT reproduce ***"))

    print("\n  THE STEP, band by band  (ratio of k):")
    for ref in ("V74 (flew)", "V76 (flew)"):
        print("\n    vs %s:" % ref)
        print("    %-20s %s" % ("band", " ".join("%9s" % ("%d-%d" % b) for b in BANDS)))
        for nm in ("V76 (flew)", "150% flat-C", "150% ReLU-C hold", "150% pure ReLU"):
            if nm == ref:
                continue
            row = [(ks[nm][i] / ks[ref][i]) if ks[ref][i] else float("inf") for i in range(len(BANDS))]
            print("    %-20s %s" % (nm, " ".join("%8.2fx" % x for x in row)))

    print("\n  TIME-WEIGHTED over the handoff's 35-80 km/h band durations (286.4 s, 47.3% of engaged):")
    tot = sum(DUR.values())
    print("    %-20s %10s %10s %10s" % ("build", "k_tw", "vs V74", "vs V76"))
    tw = {}
    for nm, _, _ in cands:
        acc = 0.0
        for i, (a, b) in enumerate(BANDS):
            if (a, b) in DUR:
                acc += ks[nm][i] * DUR[(a, b)]
        tw[nm] = acc / tot
    for nm in [c[0] for c in cands]:
        print("    %-20s %10.4f %9.2fx %9.2fx"
              % (nm, tw[nm],
                 tw[nm] / tw["V74 (flew)"] if tw["V74 (flew)"] else float("inf"),
                 tw[nm] / tw["V76 (flew)"] if tw["V76 (flew)"] else float("inf")))
    print("""
    handoff cross-check: V74 k_tw = 0.449, V76 k_tw = 1.393, step 3.10x -- reproduced above.

  🛑 THE HONEST STATEMENT ON RISK
    * The 150%% surface is a **%.2fx** time-weighted step over V74 across 35-80 km/h, and a
      **%.2fx** step over V76.  V76 itself was already 3.10x V74 there.
    * It is the FIRST point in this lineage ABOVE V75's creep loop gain (k %.4f vs 1.5798, both in
      the truncated form so they are comparable), and
      V75 hard-faulted.  [BELIEF] the fault mechanism was pinned to the FRICTION lane and a V38
      base closes it, so this is a GATE-2 stability exposure, not a re-opened DTC-0x1d exposure --
      but the two have never been separated ON THE CAR.
    * Two hard faults in two days.  V76 has one flight.  n = 1 is not a safety record.
    * ⚠ the "ReLU-C hold" middle option is NOT free either: putting a ReLU knee at 0 costs damping
      BELOW 5 mph -- 0.46x V76 in the 0-5 km/h band -- which is where V62's measured grind fix
      lives.  It buys the ReLU shape at the price of the one band with a positive on-car result.
    * The lowest-risk realisation of "150%% at 5 mph" is the FLAT-FactorC one (one u16 cell,
      FactorE Y[1] 300 -> %d).  It is a single-variable step off a build that flew.
      The pure-ReLU realisation adds a second, much larger variable (a speed-proportional FactorC)
      that rails the ceiling at 3 deg/s at 140 km/h and has NO precedent on this car.
""" % (tw["150% flat-C"] / tw["V74 (flew)"],
       tw["150% flat-C"] / tw["V76 (flew)"],
       J["q3"]["k_min"], ey1))
    J["q6"] = dict(bands=BANDS, k=ks, time_weighted=tw, durations={str(k): v for k, v in DUR.items()})


def main():
    S, ok = q1()
    q2(S)
    q3(S)
    sol = q4(S)
    if sol is None:
        print("\n*** Q4 found no constructive solution; Q5/Q6 skipped ***")
    else:
        Cx4, Cy4, Ecand = q5(S, sol)
        q6(S, sol, (Cx4, Cy4), Ecand)
    OUT_JSON.write_text(json.dumps(J, indent=1, default=str), encoding="utf-8")
    print("\nwrote %s" % OUT_JSON)


if __name__ == "__main__":
    main()
