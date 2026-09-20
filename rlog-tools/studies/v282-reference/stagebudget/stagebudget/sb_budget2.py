# -*- coding: utf-8 -*-
"""Stage 2b: the budget on COMPARABLE legs, amplitude-stratified, with coherence gates and CIs.

WHY THIS FILE EXISTS.  sb_budget.py cuts the chain at the wire command U.  That cut is measurable but
it is NOT comparable between the builds, and the measurement says so loudly: at 0.15-0.30 Hz, 15-22
m/s, V282's leg Z->U carries -644 ms (a LEAD) and U->M +792 ms, while torque mode carries -90 and
+376.  V282's wire word is a RATE request and torque mode's is a TORQUE request, so U sits at a
different place in the differentiation chain on the two builds and the two sub-legs swap ~500 ms
between them with almost no change in their sum.  Reporting that split as "software vs plant" would
be an artefact of the wire semantics, not a finding.

So the comparable budget uses the four legs whose endpoints mean the same thing on both builds:

  L1  X  -> Z0   canceller + jerk filter   fork software (replay-validated, sb_validate)
  L2  Z0 -> Z    reference filter          fork software (replay-validated)
  L34 Z  -> M    controller + EPS + rack   the whole loop, cut at the WHEEL ANGLE
  L5  M  -> Y    wheel angle -> yaw        the vehicle.  Build-independent => the CONTROL.

The U split is still printed, gated on the command's own coherence with the demand, as a WITHIN-BUILD
diagnostic only.

MEASUREMENT.  ANALYSIS ONLY, read-only.  usage: python sb_budget2.py > out/BUDGET2-OUT.txt
"""
import sys

import numpy as np

import sb_lib as L
from sb_budget import Spec, cell, boot

C4 = ["Z0", "Z", "M", "Y"]
N4 = ["L1 canc+jerk", "L2 ref filt", "L34 loop Z->M", "L5 vehicle"]
C5 = ["Z0", "Z", "U", "M", "Y"]


def gate(c, nodes, need=0.35):
    """A leg is readable only if BOTH its endpoints are coherent with the demand, clear of the
    cell's own 95% null floor by a margin."""
    return all(c["coh"][k] >= max(need, c["flr"] + 0.05) for k in nodes)


def main():
    print("=" * 150)
    print("1.  THE COMPARABLE FOUR-LEG BUDGET, amplitude ALL.  lag ms, + = lags.  Legs sum to the total EXACTLY")
    print("    (weighted mean of per-bin phases with one weight vector); the printed closure is the arithmetic check.")
    print("    Gates: every leg endpoint's coherence with the demand must clear max(0.35, null floor + 0.05).")
    print("=" * 150)
    for f1, f2, W in L.BANDS:
        S = Spec(W)
        print()
        print(f"### BAND {f1:.2f}-{f2:.2f} Hz  (window {W:.2f} s)")
        print(f"{'speed':6s} {'group':8s} {'n/r':>8s} {'v':>5s} {'medA':>7s} | "
              + " ".join(f"{n:>13s} {'lag':>6s}" for n in N4)
              + f" | {'TOTg':>6s} {'TOTlag':>7s} {'clos':>5s} | coh Z/M/Y  gate")
        for sb in range(4):
            for grp in ("V282", "V282old", "TORQ", "TQ_J12", "T64F"):
                idx = S.sel(grp, sb)
                c = cell(S, idx, f1, f2, C4)
                if c is None or c["n"] < 8:
                    continue
                g = gate(c, C4)
                print(f"{L.SPDN[sb]:6s} {grp:8s} {c['n']:>5d}/{c['nroute']}r {c['v']:>5.1f} {c['am']:>7.4f} | "
                      + " ".join(f"{c['g'][i]:>13.3f} {c['tau'][i]*1e3:>+6.0f}" for i in range(4))
                      + f" | {c['g_end']:>6.3f} {c['t_end']*1e3:>+7.0f} "
                      f"{(np.sum(c['tau'])-c['t_end'])*1e3:>+5.0f} | "
                      + "/".join(f"{c['coh'][k]:.2f}" for k in ("Z", "M", "Y"))
                      + ("  ok" if g else "  WEAK"))
        del S

    # -------------------------------------------------------------------------------------
    print()
    print("=" * 150)
    print("2.  THE GAP LEG BY LEG, AMPLITUDE-MATCHED.  Each stratum is a fixed absolute cut on the window's")
    print("    median |model| (m/s^2), so the two builds are compared at the same demand size.  d = TQ - V282.")
    print("    CI = route-cluster bootstrap 95% on each build's own leg lag, differenced conservatively.")
    print("=" * 150)
    for f1, f2, W in L.BANDS:
        S = Spec(W)
        print()
        print(f"### BAND {f1:.2f}-{f2:.2f} Hz")
        print(f"{'speed':6s} {'amp':13s} {'cmp':7s} {'nV/nT':>10s} {'medA V/T':>14s} | "
              + " ".join(f"{n.split()[0]+' dlag':>21s}" for n in N4) + f" | {'TOT dlag':>9s}")
        for sb in range(4):
            for ai, (a1, a2) in enumerate(L.ACUT):
                iv = S.sel("V282", sb, (a1, a2))
                cv = cell(S, iv, f1, f2, C4)
                if cv is None or cv["n"] < 8 or not gate(cv, C4):
                    continue
                bv = boot(S, iv, f1, f2, lambda c: c["tau"], nodes=C4)
                for grp in ("TORQ", "TQ_J12"):
                    it = S.sel(grp, sb, (a1, a2))
                    ct = cell(S, it, f1, f2, C4)
                    if ct is None or ct["n"] < 8 or not gate(ct, C4):
                        continue
                    bt = boot(S, it, f1, f2, lambda c: c["tau"], nodes=C4)
                    d = (ct["tau"] - cv["tau"]) * 1e3
                    cells = []
                    for i in range(4):
                        s = f"{d[i]:+6.0f}"
                        if bt is not None and bv is not None:
                            s += f"[{(bt[0][i]-bv[1][i])*1e3:+5.0f},{(bt[1][i]-bv[0][i])*1e3:+5.0f}]"
                        cells.append(s)
                    print(f"{L.SPDN[sb]:6s} {L.ACUTN[ai]:13s} {grp:7s} {cv['n']:>4d}/{ct['n']:<5d} "
                          f"{cv['am']:>6.4f}/{ct['am']:<7.4f} | " + " ".join(f"{s:>21s}" for s in cells)
                          + f" | {(ct['t_end']-cv['t_end'])*1e3:>+9.0f}")
        del S

    # -------------------------------------------------------------------------------------
    print()
    print("=" * 150)
    print("3.  AMPLITUDE STRUCTURE WITHIN EACH BUILD: does a leg's lag grow at SMALL demand?")
    print("    (the residual's amplitude signature is +318 ms at small demand falling to +10 ms at large,")
    print("     8-15 m/s -- if one leg owns that, that leg is where the remedy has to act)")
    print("=" * 150)
    for f1, f2, W in L.BANDS[1:3]:
        S = Spec(W)
        print()
        print(f"### BAND {f1:.2f}-{f2:.2f} Hz")
        for sb in (1, 2, 3):
            print(f"  -- speed {L.SPDN[sb]} --")
            print(f"    {'group':8s} {'amp':13s} {'n/r':>7s} {'medA':>7s} | "
                  + " ".join(f"{n:>13s} {'lag':>6s}" for n in N4) + f" | {'TOTlag':>7s} {'TOTg':>6s} | coh Z/M/Y")
            for grp in ("V282", "TORQ", "TQ_J12", "T64F"):
                for ai, (a1, a2) in enumerate(L.ACUT):
                    idx = S.sel(grp, sb, (a1, a2))
                    c = cell(S, idx, f1, f2, C4)
                    if c is None or c["n"] < 8:
                        continue
                    print(f"    {grp:8s} {L.ACUTN[ai]:13s} {c['n']:>4d}/{c['nroute']}r {c['am']:>7.4f} | "
                          + " ".join(f"{c['g'][i]:>13.3f} {c['tau'][i]*1e3:>+6.0f}" for i in range(4))
                          + f" | {c['t_end']*1e3:>+7.0f} {c['g_end']:>6.3f} | "
                          + "/".join(f"{c['coh'][k]:.2f}" for k in ("Z", "M", "Y"))
                          + ("" if gate(c, C4) else "  WEAK"))
        del S

    # -------------------------------------------------------------------------------------
    print()
    print("=" * 150)
    print("4.  THE CONTROL: leg L5 (wheel angle -> achieved yaw) is pure vehicle and MUST be build-independent.")
    print("    If it is not, the comparison itself is contaminated.  Printed with matched speed and amplitude.")
    print("=" * 150)
    for f1, f2, W in L.BANDS:
        S = Spec(W)
        print(f"\n### BAND {f1:.2f}-{f2:.2f} Hz")
        print(f"  {'speed':6s} {'amp':13s} | " + " ".join(f"{g:>26s}" for g in ("V282", "TORQ"))
              + f" | {'d gain':>8s} {'d lag ms':>9s}")
        for sb in range(4):
            for ai, (a1, a2) in enumerate(L.ACUT):
                cv = cell(S, S.sel("V282", sb, (a1, a2)), f1, f2, C4)
                ct = cell(S, S.sel("TORQ", sb, (a1, a2)), f1, f2, C4)
                if cv is None or ct is None or cv["n"] < 8 or ct["n"] < 8:
                    continue
                if not (gate(cv, ["M", "Y"]) and gate(ct, ["M", "Y"])):
                    continue
                sv = f"g {cv['g'][3]:.3f} lag {cv['tau'][3]*1e3:+.0f} v{cv['v']:.1f} n{cv['n']}"
                st = f"g {ct['g'][3]:.3f} lag {ct['tau'][3]*1e3:+.0f} v{ct['v']:.1f} n{ct['n']}"
                print(f"  {L.SPDN[sb]:6s} {L.ACUTN[ai]:13s} | {sv:>26s} {st:>26s} | "
                      f"{ct['g'][3]/max(cv['g'][3],1e-9):>8.3f} {(ct['tau'][3]-cv['tau'][3])*1e3:>+9.0f}")
        del S

    # -------------------------------------------------------------------------------------
    print()
    print("=" * 150)
    print("5.  THE WIRE SPLIT, WITHIN-BUILD DIAGNOSTIC ONLY (not comparable across builds -- see the header).")
    print("    Printed only where the COMMAND itself is coherent with the demand (coh(X,U) >= 0.55).")
    print("=" * 150)
    for f1, f2, W in L.BANDS:
        S = Spec(W)
        print(f"\n### BAND {f1:.2f}-{f2:.2f} Hz")
        print(f"  {'speed':6s} {'group':8s} {'n':>5s} {'cohU':>5s} | {'L3 Z->U g':>10s} {'lag':>6s} | "
              f"{'L4 U->M g':>10s} {'lag':>6s} | {'L34 sum lag':>11s}")
        for sb in range(4):
            for grp in ("V282", "TORQ", "TQ_J12", "T64F", "T2"):
                c = cell(S, S.sel(grp, sb), f1, f2, C5)
                if c is None or c["n"] < 8 or c["coh"]["U"] < 0.55:
                    continue
                print(f"  {L.SPDN[sb]:6s} {grp:8s} {c['n']:>5d} {c['coh']['U']:>5.2f} | "
                      f"{c['g'][2]:>10.3f} {c['tau'][2]*1e3:>+6.0f} | {c['g'][3]:>10.3f} {c['tau'][3]*1e3:>+6.0f} | "
                      f"{(c['tau'][2]+c['tau'][3])*1e3:>+11.0f}")
        del S
    return 0


if __name__ == "__main__":
    sys.exit(main())
