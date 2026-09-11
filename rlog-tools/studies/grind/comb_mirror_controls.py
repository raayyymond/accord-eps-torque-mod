# -*- coding: utf-8 -*-
"""studies/grind/comb_mirror_controls.py -- CONTROLS FOR THE COMB ABLATION.  Subagent `combsize`.
ANALYSIS ONLY.  2026-09-10.

comb_mirror_sizing.py C2 reports the comb's attributable delivery as (in-phase ablation energy minus
quadrature ablation energy).  That number is only worth anything if the METHOD returns ~0 when there
is no comb.  This file is the attempt to make it fail.

  K1  DETUNED-CLOCK NULL.  Repeat the whole ablation against reference clocks detuned by 0.10-0.80 Hz
      from f_model.  There is no line there, so the in-phase and quadrature ablations must deliver
      THE SAME amount and the net must collapse to the noise floor.  If a detuned clock returns a net
      comparable to the real clock, the C2 number is an artefact and must be withdrawn.
  K2  BAND-WIDTH SENSITIVITY.  Does the answer depend on the half-width chosen for the comb band?
  K3  ACCUMULATION.  What the comb's delivered counts become under the analytic phase-locked ceiling
      1/(1-exp(-2 pi zeta)) = 6.00, and at |cos psi| < 1 -- the same ceiling slewburst applied to the
      echo, so the two candidates are compared on identical terms.  Also states plainly why the C2
      FEEDBACK leg must NOT be multiplied by that ceiling as well (it IS the regeneration, measured).

Run: python rlog-tools/studies/grind/comb_mirror_controls.py
Writes _scratch/comb_mirror_controls.txt beside it.
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import burst_onset_triggers as B              # noqa: E402
import burst_echo_sizing as ES                # noqa: E402
import grind_incident_r35 as GI               # noqa: E402
import comb_mirror_sizing as CM               # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FS1K = 100.0, 1000.0
OUT = []
ZETA = 0.029
CEIL = 1.0 / (1.0 - np.exp(-2 * np.pi * ZETA))


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def net_at(g, fref, hw, wins, lo, hi):
    """run the in-phase / quadrature ablation against an arbitrary reference clock frequency fref."""
    z = CM.analytic(g["cmd"], fref - hw, fref + hw)
    _, grind = CM.strata(g)
    t, ic = g["t"], g["icept"]
    slope = 1.0 / fref                       # the reference clock's period
    phi = CM.lock_phase(z, t, ic, slope, grind)
    xin, xqu = CM.split_locked(z, t, ic, slope, phi)
    vin, vqu = [], []
    for a0, b0, p0 in wins:
        S0 = GI.simulate(g, a0, b0, g["cells"])
        for arr, acc in ((xin, vin), (xqu, vqu)):
            g2 = dict(g); g2["cmd"] = g["cmd"] - arr
            acc.append(ES.band_amp(GI.simulate(g2, a0, b0, g["cells"])["T"] - S0["T"], lo, hi, FS1K))
    mi, mq = float(np.median(vin)), float(np.median(vqu))
    return mi, mq, float(np.sqrt(max(mi ** 2 - mq ** 2, 0.0)))


def main():
    G = {}
    for tag in ("r39", "r63_v289"):
        print("loading %s ..." % tag, flush=True)
        g = B.load_route(tag)
        lo, hi = B.BAND[tag]
        g["f0"] = B.ring_f0(g, lo, hi)
        g["env"] = B.demod_env(g["bar"], g["f0"], FS)
        on, pk, amp, thi, tlo = B.find_onsets(g["env"], g["eng"])
        g["on"], g["pk"], g["amp"] = on, pk, amp
        fm, sl, ic, M = CM.model_clock(tag)
        g["f_model"], g["slope"], g["icept"] = fm, sl, ic
        G[tag] = g

    OUT.clear()
    pr("=" * 118)
    pr("CONTROLS FOR THE COMB ABLATION -- subagent `combsize`, 2026-09-10")
    pr("=" * 118)
    pr("")
    pr("=" * 118)
    pr("K1  DETUNED-CLOCK NULL -- the attempt to make the method fail")
    pr("=" * 118)
    pr("Same ablation, same windows, same measure, against reference clocks where NO line exists.")
    pr("A valid method returns in-phase == quadrature (net ~ 0) at every detuning.  If a detuned clock")
    pr("returns a net comparable to f_model, the C2 headline is an artefact and is WITHDRAWN.")
    pr("")
    pr("%-10s %10s %9s %10s %10s %10s %10s" %
       ("route", "clock", "detune", "in-phase", "quadrature", "NET", "net/T_total"))
    pr("-" * 118)
    for tag in ("r39", "r63_v289"):
        g = G[tag]
        lo, hi = B.BAND[tag]
        wins = ES.loud_windows(g)
        T0 = float(np.median([ES.band_amp(GI.simulate(g, a0, b0, g["cells"])["T"], lo, hi, FS1K)
                              for a0, b0, p0 in wins]))
        nulls = []
        for d in (0.0, -0.60, -0.37, -0.17, 0.17, 0.37, 0.60):
            mi, mq, net = net_at(g, g["f_model"] + d, CM.COMB_HW, wins, lo, hi)
            tagl = "f_model" if d == 0.0 else "detuned"
            pr("%-10s %10s %+9.2f %10.2f %10.2f %10.2f %10.3f" %
               (tag, tagl, d, mi, mq, net, net / T0))
            if d != 0.0:
                nulls.append(net)
        pr("%-10s %10s %9s %10s %10s %10.2f %10.3f   <== NULL FLOOR (max over 6 detunings)" %
           (tag, "", "", "", "", max(nulls), max(nulls) / T0))
        pr("")

    pr("=" * 118)
    pr("K2  BAND-WIDTH SENSITIVITY")
    pr("=" * 118)
    pr("%-10s %10s %10s %10s %10s" % ("route", "half-width", "in-phase", "quadrature", "NET"))
    pr("-" * 118)
    for tag in ("r39", "r63_v289"):
        g = G[tag]
        lo, hi = B.BAND[tag]
        wins = ES.loud_windows(g)
        for hw in (1.0, 1.5, 2.5):
            mi, mq, net = net_at(g, g["f_model"], hw, wins, lo, hi)
            pr("%-10s %10.1f %10.2f %10.2f %10.2f" % (tag, hw, mi, mq, net))
        pr("")

    pr("=" * 118)
    pr("K3  ACCUMULATION -- putting the comb and the echo on identical terms")
    pr("=" * 118)
    pr("slewburst's echo rows were quoted with the analytic phase-locked accumulation ceiling")
    pr("1/(1-exp(-2*pi*zeta)) = %.2f at zeta = %.3f, degraded by |cos psi| at a phase offset psi" % (CEIL, ZETA))
    pr("against the ring VELOCITY.  The comb must be quoted the same way or the comparison is rigged.")
    pr("")
    pr("%-10s %12s %12s %14s %14s %s" %
       ("route", "COMB net", "T_total", "x6.00 ceiling", "ratio", "verdict at psi = 0 (best case)"))
    pr("-" * 118)
    for tag, net, T0 in (("r39", 7.51, 57.21), ("r5e_v288", 2.50, 52.61),
                         ("r62_v289", 1.30, 66.00), ("r63_v289", 1.73, 125.86)):
        c = CEIL * net
        pr("%-10s %12.2f %12.2f %14.2f %14.3f %s" %
           (tag, net, T0, c, c / T0,
            "SUFFICIENT" if c >= T0 else "SHORT by x%.1f" % (T0 / c)))
    pr("")
    pr("degradation with the phase offset psi against the ring velocity (r39, the clean V282 row):")
    pr("  %-8s %s" % ("psi", "  ".join("%5d deg" % p for p in (0, 30, 45, 60, 90))))
    pr("  %-8s %s" % ("ceiling", "  ".join("%9.2f" % (CEIL * abs(np.cos(np.radians(p))))
                                           for p in (0, 30, 45, 60, 90))))
    pr("  %-8s %s" % ("-> ratio", "  ".join("%9.3f" % (CEIL * abs(np.cos(np.radians(p))) * 7.51 / 57.21)
                                            for p in (0, 30, 45, 60, 90))))
    pr("")
    pr("🛑 AND THE DOUBLE-COUNT WARNING, stated so nobody applies the ceiling twice.  The C2 FEEDBACK")
    pr("leg is the mirror's MEASURED regeneration: it is how much in-band torque the loop produces from")
    pr("the ring that is already in the wheel rate.  The x%.2f analytic ceiling is a MODEL OF THAT SAME" % CEIL)
    pr("REGENERATION.  So the ceiling belongs on the EXOGENOUS drive (the comb, the echo, a capped")
    pr("step) and must NOT also be applied to the feedback leg.  Multiplying both would count the")
    pr("loop's gain twice.")
    with open(os.path.join(B.SCR, "comb_mirror_controls.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/comb_mirror_controls.txt")


if __name__ == "__main__":
    main()
