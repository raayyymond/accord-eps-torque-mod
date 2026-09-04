# -*- coding: utf-8 -*-
"""studies/grind/v283_lever_sizing.py -- what the V282 comparator duty does to the ranked grind loop shapes,
and the control-band test of the Ki-vs-grind question.  Subagent grind283, 2026-09-03.  Analysis only.

THE POINT.  Every row of GRINDING-DEEP-ANALYSIS-2026-09-03.md section 3 is proportional to |r24|, and |r24|
was a CLOSED FORM, never a measurement.  The V282 comparator measures it -- not directly, but through the
duty P(|r24| >= |T|), which is a monotone function of the scale.  So:

  (1) invert the measured duty for the SCALE s such that  |r24_wire| = s * |r24_closed_form(5244 arm)|.
      Two independent comparators (bit 6 against |T|, bit 5 against |aggregator|) give two estimates.
  (2) decompose the deep analysis's Re(T + r24) budget into its SERVO and r24 parts, exactly -- the table
      over-determines it (three rows check the decomposition to 0.01), because the out-lag pole moves only
      the servo and 0xC6446 moves only r24.
  (3) re-rank the shapes with the r24 part scaled by s.
  (4) price the out-lag pole's cost in the 25-50 Hz blind spot from the filter arithmetic.

WHAT THIS RESCALE ASSUMES (stated, because it is the load-bearing assumption): that the closed form's
PHASE is right and only its MAGNITUDE is wrong.  PREREG (C) is the evidence for that -- bit 4's measured
phase reproduces the closed form to -13..-18 deg at 18-22 Hz, and to +3..-4 deg at 7-8.6 Hz.  If instead
the error were in the derivative timing, the phase would be wrong too and this rescale would be void.

Run: python v283_lever_sizing.py     (writes _scratch/v283_lever_sizing.txt beside it)
"""
import os
import sys

import numpy as np
from scipy import signal, stats

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                 # noqa: E402
import v280_map_profiles as V                 # noqa: E402
from v282_r24_tap_read import read_cells, demand_live, IMG, V283_ROUTES, r24_series, band   # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
CACHE = C20.CACHE
ALL = ("r36", "r37", "r38", "r35")
GRP = {"r36": "V283", "r37": "V283", "r38": "V283", "r35": "V281r3"}
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


# --------------------------------------------------------------------------------------- the lag filter
def lag_H(a, b, f, fs=1000.0):
    """y[n] = (a*y[n-1] + b*u[n]) / 1024, DC-normalised.  pole = a/1024 at fs = 1 kHz."""
    p = a / 1024.0
    w = 2 * np.pi * np.asarray(f, float) / fs
    return (1 - p) / (1 - p * np.exp(-1j * w))


def pole_hz(a, fs=1000.0):
    return -np.log(a / 1024.0) * fs / (2 * np.pi)


def main():
    cells = {k: read_cells(p) for k, p in IMG.items()}
    G = {}
    for tag in ALL:
        print("loading %s ..." % tag, flush=True)
        g = C20.load(tag)
        g["tr"] = g["t"] - g["t"][0]
        c = cells["V283"] if tag in V283_ROUTES else cells["V281r3"]
        g["idx"], _ = demand_live(np.round(g["cmd"]), g["bar"], c)
        B = np.load(os.path.join(CACHE, tag + "_b4.npz"))
        k14, P14, tn14, _ = C20.dejitter(B["t14b"], 0.01, 100)
        b4 = B["b4"].astype(int)
        for bit in (4, 5, 6):
            g["bit%d" % bit] = np.round(np.interp(g["t"], tn14, ((b4 >> bit) & 1).astype(float)))
        G[tag] = g

    STRATA = [
        ("creep engaged hands-off (v 1-3, |bar|<400)",
         lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 3.0) & (np.abs(g["bar"]) < 400)),
        ("creep engaged hands-off (v 1-6, |bar|<400)",
         lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 6.0) & (np.abs(g["bar"]) < 400)),
        ("loaded high-angle (v 2-9, |ang|>30, idx>=68)",
         lambda g: g["eng"] & (g["vego"] >= 2.0) & (g["vego"] < 9.0) & (np.abs(g["ang"]) > 30) & (g["idx"] >= 68)),
        ("highway engaged (v > 15)", lambda g: g["eng"] & (g["vego"] > 15.0)),
        ("all engaged lateral", lambda g: g["eng"]),
    ]

    pr("=" * 150)
    pr("1. INVERTING THE COMPARATOR DUTY FOR THE r24 MAGNITUDE SCALE s   ( |r24_wire| = s * |r24_closed_form at the 5244 arm| )")
    pr("=" * 150)
    pr("  bit 6 solves P(|s*r24_cf| >= |T|) = duty ; bit 5 solves P(|s*r24_cf| >= |T + s*r24_cf|) = duty (an UPPER")
    pr("  bound on the aggregator, so bit 5's s is an UPPER bound on s).  Grid 0.02..3.0.")
    pr("  %-46s %8s %8s %9s %9s %9s %9s %9s" % ("stratum", "bit6", "bit5", "s(bit6)", "s(bit5)", "eq-arm", "|r24| p50", "sec"))
    SG = np.arange(0.02, 3.001, 0.005)
    s_est = {}
    for name, fn in STRATA:
        d6, d5, R6, T6 = [], [], [], []
        for tag in V283_ROUTES:
            g = G[tag]; m = fn(g)
            if m.sum() < 200:
                continue
            r = r24_series(g["bar"], 5244.0)
            d6.append(g["bit6"][m]); d5.append(g["bit5"][m]); R6.append(np.abs(r)[m]); T6.append(np.abs(g["T100"])[m])
        if not d6:
            continue
        d6 = np.concatenate(d6).mean(); d5 = np.concatenate(d5).mean()
        R6 = np.concatenate(R6); T6 = np.concatenate(T6)
        c6 = np.array([np.mean(s * R6 >= T6) for s in SG])
        c5 = np.array([np.mean(s * R6 >= np.abs(T6 + s * R6)) for s in SG])   # |T| already abs -> conservative
        s6 = float(SG[np.argmin(np.abs(c6 - d6))])
        s5 = float(SG[np.argmin(np.abs(c5 - d5))]) if c5.max() >= d5 else np.nan
        s_est[name] = (s6, s5)
        pr("  %-46s %8.4f %8.4f %9.2f %9.2f %9.0f %9.0f %9.1f" % (
            name, d6, d5, s6, s5, s6 * 5244, np.median(R6) * s6, len(R6) / FS))
    pr("\n  [EVIDENCE] the duty is a monotone function of s, so this inversion is unique; [BELIEF] that the")
    pr("  closed form's SHAPE (its 4-tap derivative, deadband 3, clamps) is right and only its SCALE is wrong.")
    s_use = np.median([v[0] for v in s_est.values()])
    pr("  >>> s adopted for the re-ranking: MEDIAN over strata = %.2f  (equivalent 0xC6446 arm %.0f)" % (s_use, s_use * 5244))

    # --------------------------------------------------------------------------------- decomposition
    pr("\n" + "=" * 150)
    pr("2. DECOMPOSING THE DEEP ANALYSIS'S Re(T + r24) BUDGET INTO SERVO AND r24 PARTS (exact; the table over-determines it)")
    pr("=" * 150)
    # from GRINDING-DEEP-ANALYSIS-2026-09-03.md section 3 (base row, 0xC6446->2048 row, 0xC6446->512 row)
    # Re_total(shape, gain) = Re_servo(shape) + (gain/5244) * Re_r24_5244
    # base @7 : Rs + Rr = -2.09 ; 2048 @7 : Rs + 0.3905 Rr = -0.10  ->  Rr = -3.265, Rs = +1.175
    # base @20: Rs + Rr = +3.36 ; 2048 @20: Rs + 0.3905 Rr = +1.31  ->  Rr = +3.364, Rs = -0.004
    Rr7, Rs7 = -3.265, 1.175
    Rr20, Rs20 = 3.364, -0.004
    pr("  Re_servo(as-built) @7 Hz = %+.3f ; Re_r24(5244 arm) @7 Hz = %+.3f" % (Rs7, Rr7))
    pr("  Re_servo(as-built) @20 Hz= %+.3f ; Re_r24(5244 arm) @20 Hz= %+.3f" % (Rs20, Rr20))
    pr("  CHECK against the published 0xC6446 -> 512 row (never used to fit): @7 %+.2f (table +0.85) ; @20 %+.2f (table +0.33)"
       % (Rs7 + (512 / 5244.) * Rr7, Rs20 + (512 / 5244.) * Rr20))
    # per-shape servo parts, back-solved from the published totals at the 5244 arm
    SHAPES = [
        ("as-built V283/V280r2", None, -2.09, 3.36, 5244, 1.82),
        ("out-lag pole 5->15 Hz alone (0xC63EC/EE 932/1457)", (932, 1457), -0.02, 4.96, 5244, 4.46),
        ("out-lag 5->15 Hz + 0xC6446 -> 2048", (932, 1457), 1.97, 2.91, 2048, 4.46),
        ("out-lag pole 5->10 Hz (963/986)", (963, 986), -0.69, 4.00, 5244, 3.34),
        ("fb pole 16.5->33 Hz (0xC63E8/EA 842/2814)", None, -1.62, 4.04, 5244, 2.41),
        ("0xC6446 -> 2048 alone", None, -0.10, 1.31, 2048, 1.82),
        ("0xC6446 -> 512 (the 7 Hz proposal)", None, 0.85, 0.33, 512, 1.82),
    ]
    pr("\n  RE-RANKED WITH THE MEASURED r24 SCALE s = %.2f.  Positive Re = damping.  '7 Hz' = the strong-turn stutter" % s_use)
    pr("  (loaded stratum), '20 Hz' = the creep grind.  'published' = the deep analysis's number at s = 1.")
    pr("  %-50s %9s %9s | %9s %9s | %9s" % ("shape", "Re@7 pub", "Re@7 s", "Re@20 pub", "Re@20 s", "|C|@20"))
    for nm, lag, p7, p20, gain, c20 in SHAPES:
        k = gain / 5244.0
        rs7 = p7 - k * Rr7                       # servo part, exact
        rs20 = p20 - k * Rr20
        n7 = rs7 + s_use * k * Rr7
        n20 = rs20 + s_use * k * Rr20
        pr("  %-50s %+9.2f %+9.2f | %+9.2f %+9.2f | %9.2f" % (nm, p7, n7, p20, n20, c20))
    pr("\n  READING [BELIEF, conditional on the s inversion]:")
    pr("  * with |r24| at %.0f %% of the closed form, the as-built 7 Hz net damping goes %+.2f -> %+.2f: the strong-turn"
       % (100 * s_use, -2.09, Rs7 + s_use * Rr7))
    pr("    pump is much closer to neutral than the deep analysis's ranking assumed, and 0xC6446 -> 2048 buys correspondingly less.")
    pr("  * the 20 Hz creep damping goes %+.2f -> %+.2f: r24 supplies %.0f %% of it, not 83 %%." % (
        3.36, Rs20 + s_use * Rr20, 100 * s_use * Rr20 / max(Rs20 + s_use * Rr20, 1e-9)))
    pr("  * the out-lag pole's contribution is UNCHANGED by s (it moves the servo, not r24), so it is the shape")
    pr("    whose value is LEAST sensitive to the very number the tap was built to measure.")

    # --------------------------------------------------------------------------------- HF cost
    pr("\n" + "=" * 150)
    pr("3. THE OUT-LAG POLE'S COST IN THE 25-50 Hz BLIND SPOT (no instrument on this car sees above 25 Hz:")
    pr("   the 427 tap is 50 Hz -> Nyquist 25, the 0x18F streams are 100 Hz -> 40 Hz usable)")
    pr("=" * 150)
    F = np.array([5, 7, 10, 15, 20, 22, 25, 30, 35, 40, 50, 70, 100.0])
    base = (992, 507)
    pr("  cell pair 0xC63EC/0xC63EE.  DC gain = 2b/(1024-a)/32, held at 0.990 in every candidate.")
    pr("  %-22s %8s %8s | %s" % ("cells (a/b)", "pole Hz", "DC", "  ".join("%6.0f" % f for f in F)))
    Hb = np.abs(lag_H(*base, F))
    for a, b in ((992, 507), (963, 986), (932, 1457), (896, 2032), (1008, 253)):
        H = np.abs(lag_H(a, b, F))
        pr("  %-22s %8.2f %8.3f | %s" % ("%d/%d" % (a, b), pole_hz(a), 2 * b / (1024 - a) / 32.0,
                                          "  ".join("%6.2f" % x for x in H / Hb)))
    pr("  (rows are |H_shape / H_as-built|, i.e. the multiplier this build puts on the LKAS rate PID's OUTPUT at each f)")
    pr("\n  [EVIDENCE, arithmetic] 932/1457 multiplies the PID output by x2.45 at 20 Hz, x%.2f at 30 Hz, x%.2f at 40 Hz"
       % tuple(np.abs(lag_H(932, 1457, np.array([30.0, 40.0]))) / np.abs(lag_H(*base, np.array([30.0, 40.0])))))
    pr("  and asymptotes at x%.2f.  x%.2f of that rise happens ABOVE 25 Hz, where nothing on this car can see it."
       % (1457 / 507.0 * (1024 - 992) / (1024 - 932) * 0 + (1 - 932 / 1024.) / (1 - 992 / 1024.),
          (np.abs(lag_H(932, 1457, 40.0)) / np.abs(lag_H(*base, 40.0))) / 2.448))
    pr("  963/986 (5 -> 10 Hz) is the half-dose: x%.2f at 20 Hz, x%.2f at 40 Hz, asymptote x%.2f."
       % (np.abs(lag_H(963, 986, 20.0)) / np.abs(lag_H(*base, 20.0)),
          np.abs(lag_H(963, 986, 40.0)) / np.abs(lag_H(*base, 40.0)), (1 - 963 / 1024.) / (1 - 992 / 1024.)))

    # --------------------------------------------------------------------------------- Ki control bands
    pr("\n" + "=" * 150)
    pr("4. THE Ki CONTROL-BAND TEST -- is the V283-vs-r35 creep difference SPECIFIC to 18-22 Hz (a loop effect)")
    pr("   or BROADBAND (a road/exposure difference between one route and three)?")
    pr("=" * 150)
    BANDS = [(4, 6), (6, 10), (10, 15), (15, 18), (18, 22), (22, 26), (24, 28), (30, 40)]
    W, STEP = 200, 50
    acc = {}
    for tag in ALL:
        g = G[tag]
        m = g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 3.0) & (np.abs(g["bar"]) < 400)
        for aa, bb in C20.runs(m, W):
            for s in range(aa, bb - W + 1, STEP):
                e = s + W
                key = GRP[tag]
                acc.setdefault(key, []).append([band(g["bar"][s:e], lo, hi) for lo, hi in BANDS])
    pr("  bar band amplitude (raw), hands-off engaged creep 1-3 m/s, 2 s windows step 0.5 s -- MEDIANS")
    pr("  %-10s %6s %s" % ("build", "n win", "  ".join("%9s" % ("%d-%d Hz" % b) for b in BANDS)))
    med = {}
    for k in ("V283", "V281r3"):
        A = np.array(acc[k])
        med[k] = np.median(A, axis=0)
        pr("  %-10s %6d %s" % (k, len(A), "  ".join("%9.0f" % x for x in med[k])))
    pr("  %-10s %6s %s" % ("ratio", "", "  ".join("%9.2f" % (med["V283"][i] / med["V281r3"][i]) for i in range(len(BANDS)))))
    pr("  %-10s %6s %s" % ("MW p", "", "  ".join("%9.3f" % stats.mannwhitneyu(np.array(acc["V283"])[:, i], np.array(acc["V281r3"])[:, i])[1]
                                                 for i in range(len(BANDS)))))
    pr("\n  READING: if the 18-22 Hz ratio stands out from the OTHER bands, Ki touched the loop at 20 Hz; if every")
    pr("  band moves together, the difference is exposure/road, and prereg (f) 'unchanged' survives.")

    with open(os.path.join(SCR, "v283_lever_sizing.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote", os.path.join(SCR, "v283_lever_sizing.txt"))


if __name__ == "__main__":
    main()
