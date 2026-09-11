# -*- coding: utf-8 -*-
"""studies/grind/comb_lockfrac_estimator_test.py -- WHICH LOCK-FRACTION ESTIMATOR IS RIGHT?
Subagent `combsize`, 2026-09-10.  ANALYSIS ONLY.

comb_lockfrac_adjudication.py showed the 4-8x dispute is almost entirely the ESTIMATOR (x4.09) and the
WINDOWING (x3.02), and NOT total-vs-excess (x0.98).  That locates the disagreement but does not settle
it.  Settle it the only way that cannot be argued with: build a signal whose TRUE locked fraction p is
KNOWN, run both estimators on it, and see which one recovers p.

    x(t) = sqrt(p) * a(t) * cos(theta(t) + phi)        locked  (a real, sign-changing -> lock mod pi)
         + sqrt(1-p) * (free narrowband noise in the same band)

  E1  both estimators vs known p, at the real data's sample sizes
  E2  the same, at the 20 s block size cyclekind used
  E3  the CONFOUND THAT MATTERS FOR THIS CORPUS: a FREE oscillation sitting only 0.08 Hz from the
      camera clock -- which is exactly where r39's ring is (f0 19.92 vs f_model 19.9997).  Does either
      estimator call an unrelated-but-nearby free mode "locked"?  If so, the 0.50 is not forcing.

Run: python rlog-tools/studies/grind/comb_lockfrac_estimator_test.py
Writes _scratch/comb_lockfrac_estimator_test.txt beside it.
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fvlc_lib as F                # noqa: E402
import fvlc_camera_lock as CL       # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
FM = 19.99974
RNG = np.random.default_rng(20260910)
DET = np.r_[np.arange(-0.80, -0.099, 0.05), np.arange(0.10, 0.801, 0.05)]
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def narrowband(n, f, bw=2.0):
    """a free narrowband oscillation centred on f -- filtered white noise, unit mean power."""
    x = RNG.normal(size=n + 4096)
    sos = signal.butter(4, [max(f - bw / 2, 0.5), f + bw / 2], btype="bandpass", fs=FS, output="sos")
    y = signal.sosfilt(sos, x)[4096:]
    return y / np.sqrt(np.mean(y ** 2))


def make(n, p, f_free=None, seed=None):
    """signal with TRUE locked energy fraction p.  The locked part is a real, slowly-modulated,
    SIGN-CHANGING amplitude on one phase axis -- the staircase morphology modelrate identified."""
    t = np.arange(n) / FS
    a = narrowband(n, 1.0, 1.6)                      # slow real envelope, changes sign
    loc = a * np.cos(2 * np.pi * FM * t + 0.7)
    loc /= np.sqrt(np.mean(loc ** 2))
    fre = narrowband(n, FM if f_free is None else f_free)
    x = np.sqrt(p) * loc + np.sqrt(1 - p) * fre
    return t, x


def both(z, t, m, blocks=None):
    """returns (R2 - maxfloor, R2_deb) for whole-stratum, or for blocks if given."""
    if blocks is None:
        def r2(f):
            zz = z[m]
            return float(np.abs((zz ** 2 * np.exp(-2j * 2 * np.pi * f * t[m])).sum())
                         / max(float((np.abs(zz) ** 2).sum()), 1e-300))
    else:
        def r2(f):
            return CL.r2_blocks(z, t, f, blocks)[0]
    r0 = r2(FM)
    rd = np.array([r2(FM + d) for d in DET])
    return max(r0 - rd.max(), 0.0), float(np.sqrt(max(r0 ** 2 - np.mean(rd ** 2), 0.0))), r0, float(rd.max())


def main():
    OUT.clear()
    pr("=" * 122)
    pr("WHICH LOCK-FRACTION ESTIMATOR RECOVERS THE TRUTH?  -- subagent `combsize`, 2026-09-10")
    pr("=" * 122)
    pr("A signal is built with a KNOWN locked energy fraction p and both estimators are run on it.")
    pr("  'R2 - maxfloor' is cyclekind's and mine;  'R2_deb' = sqrt(max(R2^2 - mean(R2^2_det),0)) is")
    pr("  modelrate's.  The right estimator is the one whose column tracks the p column.")
    pr("")

    pr("=" * 122)
    pr("E1  WHOLE-STRATUM, at r39's grinding sample size (182 s = 18200 samples)")
    pr("=" * 122)
    pr("%8s %12s %12s %12s %12s %12s %12s" %
       ("true p", "raw R2", "max floor", "R2-maxfloor", "err", "R2_deb", "err"))
    pr("-" * 122)
    n = 18200
    for p in (0.0, 0.05, 0.10, 0.20, 0.35, 0.50, 0.70, 0.90):
        e1, e2, r0, fl = [], [], [], []
        for _ in range(6):
            t, x = make(n, p)
            z = CL.analytic(x, FS, 18.0, 22.0)
            m = np.ones(n, bool)
            a, b, rr, ff = both(z, t, m)
            e1.append(a); e2.append(b); r0.append(rr); fl.append(ff)
        pr("%8.2f %12.4f %12.4f %12.4f %+12.4f %12.4f %+12.4f" %
           (p, np.mean(r0), np.mean(fl), np.mean(e1), np.mean(e1) - p, np.mean(e2), np.mean(e2) - p))
    pr("")

    pr("=" * 122)
    pr("E2  THE SAME, evaluated in 20 s BLOCKS (cyclekind's windowing)")
    pr("=" * 122)
    pr("%8s %12s %12s %12s %12s %12s %12s" %
       ("true p", "raw R2", "max floor", "R2-maxfloor", "err", "R2_deb", "err"))
    pr("-" * 122)
    for p in (0.0, 0.05, 0.10, 0.20, 0.35, 0.50, 0.70, 0.90):
        e1, e2, r0, fl = [], [], [], []
        for _ in range(6):
            t, x = make(n, p)
            z = CL.analytic(x, FS, 18.0, 22.0)
            blks = CL.blocks_of(np.ones(n, bool))
            a, b, rr, ff = both(z, t, None, blocks=blks)
            e1.append(a); e2.append(b); r0.append(rr); fl.append(ff)
        pr("%8.2f %12.4f %12.4f %12.4f %+12.4f %12.4f %+12.4f" %
           (p, np.mean(r0), np.mean(fl), np.mean(e1), np.mean(e1) - p, np.mean(e2), np.mean(e2) - p))
    pr("")

    pr("=" * 122)
    pr("E3  🛑 THE CONFOUND THAT MATTERS FOR THIS CORPUS -- a FREE mode 0.08 Hz from the camera clock")
    pr("=" * 122)
    pr("r39's ring f0 is 19.92 Hz; f_model is 19.9997 Hz.  They are 0.08 Hz apart -- INSIDE the")
    pr("detuning exclusion zone (|d| >= 0.10 Hz), so the measured floor contains NO reference that")
    pr("close.  If a free oscillation that near the clock reads as 'locked', then a high R2 on the ring")
    pr("is not evidence of forcing and BOTH agents' numbers are measuring proximity, not causation.")
    pr("p = 0 in every row below: there is NO locked component at all, only a free mode at f_free.")
    pr("")
    pr("%10s %10s %12s %12s %12s %14s" %
       ("f_free", "offset Hz", "obs len s", "R2-maxfloor", "R2_deb", "verdict"))
    pr("-" * 122)
    for dfree in (0.0, 0.02, 0.05, 0.08, 0.15, 0.40):
        for nn, lab in ((18200, "182"),):
            e1, e2 = [], []
            for _ in range(6):
                t, x = make(nn, 0.0, f_free=FM - dfree)
                z = CL.analytic(x, FS, 18.0, 22.0)
                a, b, _, _ = both(z, t, np.ones(nn, bool))
                e1.append(a); e2.append(b)
            m1, m2 = np.mean(e1), np.mean(e2)
            pr("%10.4f %10.2f %12s %12.4f %12.4f %14s" %
               (FM - dfree, dfree, lab, m1, m2,
                "FALSE LOCK" if m2 > 0.15 else "ok"))
    pr("")
    pr("If the 0.08 Hz row reads near zero, proximity is NOT inflating the corpus numbers over a")
    pr("182 s stratum (phase slip 0.08 x 182 = 14.5 cycles is ample decorrelation) and the measured")
    pr("lock on the ring is real.  If it reads high, the ring numbers are confounded and must be")
    pr("re-derived against a null that includes sub-0.10 Hz detunings.")
    with open(os.path.join(F.SCR, "comb_lockfrac_estimator_test.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/comb_lockfrac_estimator_test.txt")


if __name__ == "__main__":
    main()
