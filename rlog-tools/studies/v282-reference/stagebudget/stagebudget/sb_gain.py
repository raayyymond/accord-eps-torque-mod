# -*- coding: utf-8 -*-
"""Stage 6: the GAIN side of the budget, and WHERE ALONG THE CHAIN the demand stops explaining the motion.

Two questions the lag budget does not answer:

(1) REGIME B (0.60-1.20 Hz, large demand) is an excess |H| 1.20 -> 2.15 with the timing BETTER.  Which
    leg's gain carries it?

(2) About 45% of regime B's excess error power is INCOHERENT with the demand.  Incoherent motion has to
    ENTER somewhere.  Tracking gamma^2(X, node) node by node along the chain localises the injection:
    a collapse between Z and M puts it in the loop/plant, a collapse between M and Y puts it in the
    road/vehicle/sensor.  gamma^2 can only fall along a chain driven by one exogenous input, so the
    node-to-node DROP is the injection at that leg (it also falls from estimator variance, so the
    same quantity is printed for V282 as the reference for how much drop is "normal").

ANALYSIS ONLY, read-only.  usage: python sb_gain.py > out/GAIN-OUT.txt
"""
import sys

import numpy as np

import sb_lib as L
from sb_budget import Spec, cell, boot
from sb_budget2 import C4, N4, gate

C5 = ["Z0", "Z", "U", "M", "Y"]
MINN = 8


def main():
    print("=" * 150)
    print("1.  LEG GAIN RATIOS, TORQUE / V282, AMPLITUDE-MATCHED.  The product of the four ratios is the")
    print("    end-to-end |H| ratio up to the band-averaging closure error, printed as 'clos'.")
    print("=" * 150)
    for f1, f2, W in L.BANDS:
        S = Spec(W)
        print(f"\n### BAND {f1:.2f}-{f2:.2f} Hz")
        print(f"{'speed':6s} {'amp':14s} {'nV/nT':>9s} | " + " ".join(f"{n.split()[0]+' x':>9s}" for n in N4)
              + f" | {'|H| V':>6s} {'|H| T':>6s} {'|H| x':>6s} {'clos':>6s}")
        for sb in range(4):
            for ai, (a1, a2) in enumerate(L.ACUT):
                iv = S.sel("V282", sb, (a1, a2)); it = S.sel("TORQ", sb, (a1, a2))
                cv = cell(S, iv, f1, f2, C4); ct = cell(S, it, f1, f2, C4)
                if cv is None or ct is None or cv["n"] < MINN or ct["n"] < MINN:
                    continue
                if not (gate(cv, C4) and gate(ct, C4)):
                    continue
                r = ct["g"] / np.maximum(cv["g"], 1e-12)
                he = ct["g_end"] / max(cv["g_end"], 1e-9)
                print(f"{L.SPDN[sb]:6s} {L.ACUTN[ai]:14s} {cv['n']:>4d}/{ct['n']:<4d} | "
                      + " ".join(f"{r[i]:>9.3f}" for i in range(4))
                      + f" | {cv['g_end']:>6.3f} {ct['g_end']:>6.3f} {he:>6.3f} {float(np.prod(r))/max(he,1e-9):>6.3f}")
        del S

    print()
    print("=" * 150)
    print("2.  WHERE THE DEMAND STOPS EXPLAINING THE MOTION.  gamma^2(X, node) along the chain, and the")
    print("    DROP at each leg.  A drop is motion injected at that leg that the demand does not explain.")
    print("=" * 150)
    for f1, f2, W in L.BANDS:
        S = Spec(W)
        print(f"\n### BAND {f1:.2f}-{f2:.2f} Hz")
        print(f"{'speed':6s} {'group':8s} {'amp':14s} {'n':>5s} | "
              + " ".join(f"g2({k}){'':1s}" for k in ("Z0", "Z", "U", "M", "Y"))
              + " | " + " ".join(f"drop {k:>3s}" for k in ("L1", "L2", "L3", "L4", "L5")))
        for sb in range(4):
            for grp in ("V282", "TORQ", "T2", "T64F"):
                for ai, (a1, a2) in enumerate(L.ACUT):
                    c = cell(S, S.sel(grp, sb, (a1, a2)), f1, f2, C5)
                    if c is None or c["n"] < MINN:
                        continue
                    g2 = [1.0] + [c["coh"][k] for k in C5]
                    dr = [g2[i] - g2[i + 1] for i in range(5)]
                    print(f"{L.SPDN[sb]:6s} {grp:8s} {L.ACUTN[ai]:14s} {c['n']:>5d} | "
                          + " ".join(f"{c['coh'][k]:>7.3f}" for k in C5)
                          + " | " + " ".join(f"{d:>+8.3f}" for d in dr))
        del S

    print()
    print("=" * 150)
    print("3.  CLOSURE CENSUS over every readable cell: the lag budget's closure error (sum of legs minus")
    print("    the directly measured end-to-end lag) and the gain budget's (product of band-mean leg gains")
    print("    over the band-mean end-to-end |H|).  The lag closure is exact BY CONSTRUCTION; this is the")
    print("    arithmetic check.  The gain closure is a real averaging error and is reported as a spread.")
    print("=" * 150)
    lagc, gainc, ncell = [], [], 0
    for f1, f2, W in L.BANDS:
        S = Spec(W)
        for sb in range(4):
            for grp in ("V282", "V282old", "TORQ", "T2", "T3", "T4", "T5", "T64F"):
                for ai in range(len(L.ACUT)):
                    c = cell(S, S.sel(grp, sb, L.ACUT[ai]), f1, f2, C4)
                    if c is None or c["n"] < MINN or not gate(c, C4):
                        continue
                    lagc.append((np.sum(c["tau"]) - c["t_end"]) * 1e3)
                    gainc.append(float(np.prod(c["g"])) / max(c["g_end"], 1e-9))
                    ncell += 1
        del S
    lagc = np.array(lagc); gainc = np.array(gainc)
    print(f"  cells: {ncell}")
    print(f"  LAG closure error  ms : max|.| {np.abs(lagc).max():.3e}   p99 {np.percentile(np.abs(lagc),99):.3e}"
          f"   -> exact to floating point, as constructed")
    print(f"  GAIN closure ratio    : median {np.median(gainc):.3f}  p5 {np.percentile(gainc,5):.3f}  "
          f"p95 {np.percentile(gainc,95):.3f}  max {gainc.max():.3f}")
    print("  (the gain ratio departs from 1 only because a product of band-MEAN gains is not the band-mean")
    print("   of the product; the per-BIN product is exact, see sb_extract's self-test)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
