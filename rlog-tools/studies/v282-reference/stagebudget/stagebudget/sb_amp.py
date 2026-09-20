# -*- coding: utf-8 -*-
"""Stage 3: NAME THE RESIDUAL.  Amplitude-matched leg gaps, the amplitude structure of each leg,
the build-independence control, and the within-torque contrasts that bound how much of the
un-cuttable loop leg is software.

Definitions used throughout:
    residual  R = (end-to-end lag gap) - (L2 ref-filter lag gap) = L1 + L34 + L5 gaps.
                 This is the quantity the brief calls "+105 to +158 ms that nobody has named".

ANALYSIS ONLY, read-only.  usage: python sb_amp.py > out/AMP-OUT.txt
"""
import sys

import numpy as np

import sb_lib as L
from sb_budget import Spec, cell, boot
from sb_budget2 import C4, N4, gate

MINN = 8


def main():
    print("=" * 152)
    print("1.  THE RESIDUAL, NAMED.  Amplitude-matched cells (fixed absolute cuts on the window's median")
    print("    |model|).  R = residual after the ref filter = L1 + L34 + L5 gaps = TOT gap - L2 gap.")
    print("    exp% = share of the band's torque-mode windows that this cell carries.")
    print("=" * 152)
    for f1, f2, W in L.BANDS:
        S = Spec(W)
        tqtot = int(np.isin(S.group, L.TORQ).sum())
        print()
        print(f"### BAND {f1:.2f}-{f2:.2f} Hz")
        print(f"{'speed':6s} {'amp':14s} {'nV/nT':>9s} {'medA V/T':>14s} {'exp%':>5s} | "
              f"{'L1':>7s} {'L2 reffilt':>12s} {'L34 loop':>12s} {'L5 veh':>9s} | {'TOT':>6s} {'RESID':>6s}")
        agg = np.zeros(4); aggw = 0.0; aggt = 0.0
        for sb in range(4):
            for ai, (a1, a2) in enumerate(L.ACUT):
                iv = S.sel("V282", sb, (a1, a2))
                it = S.sel("TORQ", sb, (a1, a2))
                cv = cell(S, iv, f1, f2, C4)
                ct = cell(S, it, f1, f2, C4)
                if cv is None or ct is None or cv["n"] < MINN or ct["n"] < MINN:
                    continue
                if not (gate(cv, C4) and gate(ct, C4)):
                    continue
                d = (ct["tau"] - cv["tau"]) * 1e3
                bt = boot(S, it, f1, f2, lambda c: c["tau"], nodes=C4)
                bv = boot(S, iv, f1, f2, lambda c: c["tau"], nodes=C4)
                ex = 100.0 * ct["n"] / max(tqtot, 1)
                ci = ""
                if bt is not None and bv is not None:
                    ci = (f"  CI L2[{(bt[0][1]-bv[1][1])*1e3:+.0f},{(bt[1][1]-bv[0][1])*1e3:+.0f}] "
                          f"L34[{(bt[0][2]-bv[1][2])*1e3:+.0f},{(bt[1][2]-bv[0][2])*1e3:+.0f}]")
                print(f"{L.SPDN[sb]:6s} {L.ACUTN[ai]:14s} {cv['n']:>4d}/{ct['n']:<4d} "
                      f"{cv['am']:>6.4f}/{ct['am']:<7.4f} {ex:>5.1f} | "
                      f"{d[0]:>+7.0f} {d[1]:>+12.0f} {d[2]:>+12.0f} {d[3]:>+9.0f} | "
                      f"{d.sum():>+6.0f} {d.sum()-d[1]:>+6.0f}{ci}")
                agg += d * ct["n"]; aggw += ct["n"]; aggt += d.sum() * ct["n"]
        if aggw:
            a = agg / aggw
            print(f"{'':6s} {'EXPOSURE-WEIGHTED':14s} {'':9s} {'':14s} {'':5s} | "
                  f"{a[0]:>+7.0f} {a[1]:>+12.0f} {a[2]:>+12.0f} {a[3]:>+9.0f} | "
                  f"{a.sum():>+6.0f} {a.sum()-a[1]:>+6.0f}")
        del S

    # -------------------------------------------------------------------------------------
    print()
    print("=" * 152)
    print("2.  AMPLITUDE STRUCTURE.  Each build's own leg lags against demand size, same speed bin.")
    print("    The residual's signature is large lag at SMALL demand.  Whichever leg shows that")
    print("    inside the torque build -- and does NOT show it inside V282 -- is where it lives.")
    print("=" * 152)
    for f1, f2, W in L.BANDS[1:4]:
        S = Spec(W)
        print(f"\n### BAND {f1:.2f}-{f2:.2f} Hz")
        for sb in (1, 2, 3):
            hdr = False
            for grp in ("V282", "TORQ", "TQ_J12", "T64F", "T2"):
                rows = []
                for ai, (a1, a2) in enumerate(L.ACUT):
                    c = cell(S, S.sel(grp, sb, (a1, a2)), f1, f2, C4)
                    if c is None or c["n"] < MINN:
                        continue
                    rows.append((ai, c))
                if len(rows) < 2:
                    continue
                if not hdr:
                    print(f"  -- speed {L.SPDN[sb]} --")
                    print(f"    {'group':8s} {'amp':14s} {'n/r':>7s} {'medA':>7s} | "
                          + " ".join(f"{n:>13s}{'lag':>6s}" for n in N4)
                          + f" | {'TOT':>6s} | coh M/Y")
                    hdr = True
                for ai, c in rows:
                    print(f"    {grp:8s} {L.ACUTN[ai]:14s} {c['n']:>4d}/{c['nroute']}r {c['am']:>7.4f} | "
                          + " ".join(f"{c['g'][i]:>13.3f}{c['tau'][i]*1e3:>+6.0f}" for i in range(4))
                          + f" | {c['t_end']*1e3:>+6.0f} | "
                          + "/".join(f"{c['coh'][k]:.2f}" for k in ("M", "Y"))
                          + ("" if gate(c, C4) else " WEAK"))
                # slope of each leg's lag against log10(medA), weighted by n
                x = np.log10([c["am"] for _, c in rows]); wts = np.array([c["n"] for _, c in rows], float)
                if len(rows) >= 3 and float(np.ptp(x)) > 0.3:
                    sl = []
                    for i in range(4):
                        y = np.array([c["tau"][i] * 1e3 for _, c in rows])
                        A = np.vstack([x, np.ones_like(x)]).T
                        Wd = np.diag(wts)
                        b = np.linalg.lstsq(A.T @ Wd @ A, A.T @ Wd @ y, rcond=None)[0]
                        sl.append(b[0])
                    print(f"    {grp:8s} {'d lag / decade of demand':14s} {'':7s} {'':7s} | "
                          + " ".join(f"{'':13s}{s:>+6.0f}" for s in sl) + "  ms per 10x demand")
        del S

    # -------------------------------------------------------------------------------------
    print()
    print("=" * 152)
    print("3.  CONTROL, TIGHTENED: L5 (wheel angle -> achieved yaw) at MATCHED SPEED.  Windows are")
    print("    restricted to a narrow common speed window, because L5's own lag rises with speed and a")
    print("    2-3 m/s median mismatch between the two builds' cells fakes a difference.")
    print("=" * 152)
    NARROW = [(9.0, 13.0), (16.0, 20.0), (23.0, 28.0), (28.0, 33.0)]
    for f1, f2, W in L.BANDS:
        S = Spec(W)
        print(f"\n### BAND {f1:.2f}-{f2:.2f} Hz")
        print(f"  {'v window':10s} | {'V282 n / v / L5 gain / lag':>36s} | {'TORQ n / v / L5 gain / lag':>36s}"
              f" | {'d gain':>7s} {'d lag':>7s}")
        for lo, hi in NARROW:
            sel = lambda g: np.where(np.isin(S.group, [g] if g not in ("TORQ",) else L.TORQ)
                                     & (S.v >= lo) & (S.v < hi))[0]
            cv = cell(S, sel("V282"), f1, f2, C4)
            ct = cell(S, sel("TORQ"), f1, f2, C4)
            if cv is None or ct is None or cv["n"] < MINN or ct["n"] < MINN:
                continue
            sv = "n%d v%.1f g%.3f lag%+.0f" % (cv["n"], cv["v"], cv["g"][3], cv["tau"][3] * 1e3)
            st = "n%d v%.1f g%.3f lag%+.0f" % (ct["n"], ct["v"], ct["g"][3], ct["tau"][3] * 1e3)
            print(f"  {lo:4.0f}-{hi:<5.0f} | {sv:>36s} | {st:>36s} | "
                  f"{ct['g'][3]/max(cv['g'][3],1e-9):>7.3f} {(ct['tau'][3]-cv['tau'][3])*1e3:>+7.0f}")
        del S

    # -------------------------------------------------------------------------------------
    print()
    print("=" * 152)
    print("4.  THE CLEAN COMPARATOR.  T2 (routes 70/71) flies the V293 TORQUE EPS with NO ref filter,")
    print("    the same 1.2 Hz jerk filter and the SAME liveDelay 0.200 s as V282 -- so its L1 and L2 are")
    print("    the same software as V282's, and the whole gap it shows IS the residual, with nothing to")
    print("    divide out.  (Confound: T2 is an early fork rev -- Kp 0.3/0.85, Ki 0.15/0.30, no rate loop,")
    print("    no observer, no hold map, no hysteresis -- and r70 flew the plant FF OFF entirely.)")
    print("=" * 152)
    for f1, f2, W in L.BANDS:
        S = Spec(W)
        print(f"\n### BAND {f1:.2f}-{f2:.2f} Hz")
        print(f"  {'speed':6s} {'nV/nT':>9s} | " + " ".join(f"{n:>13s}{'dlag':>6s}" for n in N4)
              + f" | {'TOT dlag':>9s}")
        for sb in range(4):
            cv = cell(S, S.sel("V282", sb), f1, f2, C4)
            ct = cell(S, S.sel("T2", sb), f1, f2, C4)
            if cv is None or ct is None or cv["n"] < MINN or ct["n"] < MINN:
                continue
            d = (ct["tau"] - cv["tau"]) * 1e3
            r = ct["g"] / np.maximum(cv["g"], 1e-12)
            print(f"  {L.SPDN[sb]:6s} {cv['n']:>4d}/{ct['n']:<4d} | "
                  + " ".join(f"{r[i]:>13.3f}{d[i]:>+6.0f}" for i in range(4))
                  + f" | {d.sum():>+9.0f}   (gain columns are TQ/V282 ratios)")
        del S

    # -------------------------------------------------------------------------------------
    print()
    print("=" * 152)
    print("5.  WITHIN-TORQUE CONTRASTS: same V293 firmware, different fork software.  Any spread in the")
    print("    L34 leg across these rows is SOFTWARE (or road), never the EPS build.  It bounds how much")
    print("    of the un-cuttable loop leg the fork can own.  Road/route confound is NOT controlled.")
    print("      T2  Kp .3/.85 Ki .15/.30, no rate loop / observer / hold map / hysteresis (r70 FF OFF)")
    print("      T3  Kp .85 Ki .60, rate loop .0006, hyst .015, hold map, RF .12")
    print("      T4  = T3 (later commit)")
    print("      T5  Kp 1.0 Ki .30, rate loop .001, OBSERVER .6, hold map, RF .12")
    print("      T64 = T5 + hold level + friction-band schedule, jerk LP 4.0 Hz, RF .06")
    print("=" * 152)
    for f1, f2, W in L.BANDS[1:4]:
        S = Spec(W)
        print(f"\n### BAND {f1:.2f}-{f2:.2f} Hz")
        print(f"  {'speed':6s} {'rev':6s} {'n/r':>7s} {'v':>5s} {'medA':>7s} | "
              + " ".join(f"{n:>13s}{'lag':>6s}" for n in N4) + f" | {'TOT':>6s} | coh M")
        for sb in (1, 2, 3):
            for grp in ("V282", "T2", "T3", "T4", "T5", "T64F"):
                c = cell(S, S.sel(grp, sb), f1, f2, C4)
                if c is None or c["n"] < MINN:
                    continue
                print(f"  {L.SPDN[sb]:6s} {grp:6s} {c['n']:>4d}/{c['nroute']}r {c['v']:>5.1f} {c['am']:>7.4f} | "
                      + " ".join(f"{c['g'][i]:>13.3f}{c['tau'][i]*1e3:>+6.0f}" for i in range(4))
                      + f" | {c['t_end']*1e3:>+6.0f} | {c['coh']['M']:.2f}"
                      + ("" if gate(c, C4) else " WEAK"))
        del S
    return 0


if __name__ == "__main__":
    sys.exit(main())
