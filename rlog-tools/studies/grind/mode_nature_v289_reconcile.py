# -*- coding: utf-8 -*-
"""studies/grind/mode_nature_v289_reconcile.py -- CAN ONE PLANT CARRY BOTH THE Kp-PINNING AND V289'S 3.3 Hz MOVE?
Subagent modenat2, 2026-09-09.  Analysis only: builds nothing, flashes nothing, sends nothing.

Two measurements that a single LTI loop must explain together, both from the demand-gated re-census:
  A  V289 (a PHASE-ONLY edit: notch on S + fb pole out) moved the line 19.96 -> 16.63 Hz and left the 18-22 Hz band EMPTY
     (present-window histogram: V289 has 0 counts in the 18/19/20/21 Hz bins, against 222+279 on V282).
  B  Kp 248 -> 696, at MATCHED demand and matched hands load, moves f0 by +0.12/+0.01/+0.05/+0.15/-0.15 Hz across five idx
     strata -- ZERO to +-0.15 Hz -- while zeta falls 0.033 -> 0.018.  The clamps are NOT the reason: at the line the D clamp
     needs 32.4 deg/s and the sum clamp 42.8 deg/s of ring, and the measured ring is 3-8 deg/s p50, 7-14 deg/s p90; not one
     window in any Kp bin has any clamp binding (mode_nature_v289_kp_pinning.py).
A loop whose CROSSOVER sets the frequency cannot do B: raising Kp costs the PID 26 deg of lead (+61 -> +35 at 20 Hz) and adds
x1.52 of gain, which drags a crossover 1.4-2.7 Hz down in every family refitted to A alone.  A loop closing on a LIGHTLY DAMPED
PLANT MODE can do B (the root locus departs the plant pole nearly horizontally: zeta falls, f barely moves) but then cannot do A
-- unless the notch does not merely shift phase at 20 Hz but ANNIHILATES the loop gain there (|N| = 0.011, -39.3 dB), which
un-de-damps the plant mode and exposes a SECOND, previously stable crossing lower down.

This script tests that composite reading by refitting every family against A AND B TOGETHER, and then asks of each best fit the
four questions the reading makes falsifiable.
Run: python mode_nature_v289_reconcile.py   (writes _scratch/mode_nature_v289_reconcile.txt)
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.argv = [sys.argv[0]]
import mode_nature_v289_recensus as MN   # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = []

# measured, demand-gated (mode_nature_v289_recensus.py section 2a) and the matched-load Kp contrast
M282_F, M282_Z = 19.96, 0.029
M289_F, M289_Z = 16.63, 0.029
KP_DF, KP_DF_SIG = 0.04, 0.30          # f0(Kp 696) - f0(Kp 248) at matched load, Hz
KP_ZR, KP_ZR_SIG = 0.55, 0.45          # zeta(Kp 450-700) / zeta(Kp 240-320) = 0.018/0.033, ln-sigma
G_OFF = {10: (42.9, -35.0), 15: (41.4, -42.0)}


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def main():
    cells = {k: MN.GI.read_cells(p) for k, p in MN.IMG.items()}
    c282, c289 = cells["V282"], cells["V289"]
    R282, R289 = MN.elec(c282), MN.elec(c289, notch=True)
    R696, R248 = MN.elec(c282, kp=696), MN.elec(c282, kp=248)

    def poles(R, pl, lo=10.0, hi=30.0):
        L = MN.loop(R, pl)
        f, z, P = MN.dominant(L, lo, hi)
        return f, z, MN.unstable_any(L), P

    def band_pole(P, lo, hi):
        """the least-damped pole with damped frequency in [lo, hi], or (nan, nan)."""
        m = (P[:, 0] >= lo) & (P[:, 0] <= hi)
        if not m.any():
            return np.nan, np.nan
        k = np.argmin(P[m, 1])
        return float(P[m][k, 0]), float(P[m][k, 1])

    def err(pl):
        e = 0.0
        f2, z2, u2, _ = poles(R282, pl)
        f9, z9, u9, _ = poles(R289, pl)
        e += MN.chi2(f2, z2, M282_F, M282_Z, u2) + MN.chi2(f9, z9, M289_F, M289_Z, u9)
        fa, za, ua, _ = poles(R248, pl)
        fb, zb, ub, _ = poles(R696, pl)
        if not np.isfinite(fa) or not np.isfinite(fb):
            return 1e6
        e += ((fb - fa - KP_DF) / KP_DF_SIG) ** 2
        zr = max(zb, 1e-3) / max(za, 1e-3)
        if ub and not ua:
            zr = 1e-3
        e += ((np.log(zr) - np.log(KP_ZR)) / KP_ZR_SIG) ** 2
        for f0, (mag, phr) in G_OFF.items():
            g = pl.Gs(f0) * 1e3; phc = phr - 360 * f0 * MN.TAU_STREAM
            e += 0.3 * ((np.log(abs(g)) - np.log(mag)) / 0.4) ** 2 + 0.3 * ((np.degrees(np.angle(g)) - phc) / 20.0) ** 2
        return e

    GRIDS = {
        "smooth (no mode)": [(g0, tau, f1, None, None, None)
                             for tau in range(1, 16) for f1 in (2.0, 3.0, 5.0, 8.0, 12.0, 20.0, 30.0)
                             for g0 in np.exp(np.linspace(np.log(0.005), np.log(0.4), 30))],
        "light mode (resonant)": [(g0, tau, f1, fp, zp, None)
                                  for fp in np.arange(17.0, 23.01, 0.25) for zp in (0.008, 0.012, 0.02, 0.03, 0.045, 0.06, 0.09)
                                  for tau in (1, 2, 3, 4, 6, 8, 10) for f1 in (3.0, 8.0, 20.0)
                                  for g0 in np.exp(np.linspace(np.log(0.004), np.log(0.25), 12))],
        "smooth+mode": [(g0, tau, f1, fp, zp, None)
                        for fp in np.arange(17.0, 25.01, 0.5) for zp in (0.10, 0.15, 0.25, 0.35, 0.5)
                        for tau in (2, 4, 6, 8, 10, 13) for f1 in (3.0, 8.0, 20.0)
                        for g0 in np.exp(np.linspace(np.log(0.01), np.log(0.3), 12))],
        "weak-mode (kappa)": [(g0, tau, f1, fp, zp, kappa)
                              for fp in np.arange(17.0, 23.01, 0.5) for zp in (0.015, 0.025, 0.04, 0.07, 0.10)
                              for kappa in (0.2, 0.3, 0.5, 0.8, 1.2) for tau in (2, 4, 7, 10, 13)
                              for f1 in (5.0, 12.0, 30.0) for g0 in np.exp(np.linspace(np.log(0.015), np.log(0.15), 8))],
    }

    pr("=" * 150)
    pr("RECONCILING V289's 3.3 Hz MOVE WITH THE Kp-PINNING -- every family refitted to BOTH, and the four falsifiable questions")
    pr("  targets: V282 pole %.2f Hz / zeta %.3f ; V289 pole %.2f / %.3f ; f0(Kp696)-f0(Kp248) = %+.2f +- %.2f Hz ;" % (M282_F, M282_Z, M289_F, M289_Z, KP_DF, KP_DF_SIG))
    pr("           zeta(Kp696)/zeta(Kp248) = %.2f (ln-sigma %.2f) ; tap |G|/angle at 10 and 15 Hz at weight 0.3" % (KP_ZR, KP_ZR_SIG))
    pr("=" * 150)
    best = {}
    for fam, grid in GRIDS.items():
        bb = (1e18, None)
        for g0, tau, f1, fp, zp, kappa in grid:
            pl = MN.PlantH(g0, tau * MN.TS, f1, fp, zp, kappa, label=fam)
            e = err(pl)
            if e < bb[0]:
                bb = (e, pl)
        best[fam] = bb
        pr("  %-22s grid %6d  best chi2 %8.1f" % (fam, len(grid), bb[0]))

    pr("\n  %-22s | %-48s | %-20s | %-20s | %8s" % ("family", "best joint fit", "V282 pole f/zeta", "V289 pole f/zeta", "chi2"))
    for fam, (e, pl) in best.items():
        f2, z2, u2, _ = poles(R282, pl); f9, z9, u9, _ = poles(R289, pl)
        pr("  %-22s | %-48s | %5.2f / %+6.3f %s | %5.2f / %+6.3f %s | %8.1f" % (
            fam, "g0 %.4f tau %.0f ms f1 %g%s" % (pl.g0, 1e3 * pl.tau, pl.f1, ("" if pl.fp is None else " fp %.2f zp %.3f%s" % (pl.fp, pl.zp, "" if pl.kappa is None else " k %.1f" % pl.kappa))),
            f2, z2, "UNS" if u2 else "   ", f9, z9, "UNS" if u9 else "   ", e))
    pr("  measured                 | %-48s | %5.2f / %+6.3f     | %5.2f / %+6.3f     |" % ("", M282_F, M282_Z, M289_F, M289_Z))
    lik = np.exp(-0.5 * np.array([best[f][0] for f in best])); lik = lik / lik.sum()
    pr("  relative likelihood: " + " ; ".join("%s %.3f" % (f, l) for f, l in zip(best, lik)))

    pr("\n  THE FOUR FALSIFIABLE QUESTIONS, per best fit:")
    pr("  Q1  Kp 248 -> 696 on a V282-type loop: does f STAY (measured +0.04 +- 0.15 Hz) and does zeta FALL (measured x0.55)?")
    pr("  Q2  under V289, is the 18-22 Hz pole RE-DAMPED?  (measured: the 18-22 Hz band is EMPTY on V289 -- 0 of 1414 present windows)")
    pr("  Q3  under V289, is the least-damped pole at 16.2-17.1 Hz?")
    pr("  Q4  is |L(20 Hz)| under V282 near 1 (a crossover) or well below 1 (a de-damped plant mode)?")
    for fam, (e, pl) in best.items():
        fa, za, ua, Pa = poles(R248, pl); fb, zb, ub, Pb = poles(R696, pl)
        f9, z9, u9, P9 = poles(R289, pl)
        f9m, z9m = band_pole(P9, 18.0, 22.5)
        f2m, z2m = band_pole(Pa, 18.0, 22.5)
        L20 = MN.loop(R282, pl)(20.0); L166 = MN.loop(R282, pl)(16.63)
        pr("\n    %s  (%s)" % (fam, pl.label))
        pr("      Q1  Kp 248: %5.2f / %+6.3f %s   Kp 696: %5.2f / %+6.3f %s   -> df %+6.2f Hz (want %+.2f +- %.2f), zeta ratio %s (want %.2f)  %s" % (
            fa, za, "UNS" if ua else "   ", fb, zb, "UNS" if ub else "   ", fb - fa, KP_DF, KP_DF_SIG,
            "%.2f" % (max(zb, 1e-3) / max(za, 1e-3)) if np.isfinite(za) else "n/a", KP_ZR,
            "PASS" if (abs(fb - fa - KP_DF) <= 3 * KP_DF_SIG and not (ub and not ua)) else "FAIL"))
        pr("      Q2  V289 pole in 18-22.5 Hz: %s   %s" % (
            "none" if not np.isfinite(f9m) else "%.2f / %+.3f" % (f9m, z9m),
            "PASS (gone or re-damped)" if (not np.isfinite(f9m) or z9m > max(z2m, 0.0) + 0.005) else "FAIL (still as lightly damped as V282's %s)" % ("n/a" if not np.isfinite(z2m) else "%.3f" % z2m)))
        pr("      Q3  V289 least-damped pole %5.2f Hz  %s" % (f9, "PASS" if 16.2 <= f9 <= 17.1 else "FAIL"))
        pr("      Q4  V282 |L(20.0)| %.3f ang %+.0f ; |L(16.63)| %.3f ang %+.0f  -> the 20 Hz line is %s" % (
            abs(L20), np.degrees(np.angle(L20)), abs(L166), np.degrees(np.angle(L166)),
            "AT the loop's crossover" if abs(abs(L20) - 1) < 0.25 else "NOT at a gain crossover (|L| %.2f) -- a de-damped plant mode" % abs(L20)))
        pr("      plant: " + "  ".join("%g Hz %.1f e-3 / %+.0f" % (f0, 1e3 * abs(pl.Gs(f0)), np.degrees(np.angle(pl.Gs(f0)))) for f0 in (10, 15, 16.63, 18, 19.96, 22, 25)))
        pr("      all V282 closed-loop poles 8-40 Hz: " + ", ".join("%.2f/%+.3f" % (p[0], p[1]) for p in Pa if 8 <= p[0] <= 40))
        pr("      all V289 closed-loop poles 8-40 Hz: " + ", ".join("%.2f/%+.3f" % (p[0], p[1]) for p in P9 if 8 <= p[0] <= 40))

    json.dump({f: best[f][1].as_dict() for f in best}, open(os.path.join(SCR, "mode_nature_v289_reconcile_fits.json"), "w"), indent=1)
    with open(os.path.join(SCR, "mode_nature_v289_reconcile.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    pr("\nwrote _scratch/mode_nature_v289_reconcile.txt")


if __name__ == "__main__":
    main()
