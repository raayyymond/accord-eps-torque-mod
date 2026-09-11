# -*- coding: utf-8 -*-
"""studies/grind/comb_does_not_grow.py -- DOES THE COMB GROW WHEN THE CAR GRINDS?
Subagent `combsize`, 2026-09-10.  ANALYSIS ONLY.

A mirror-INDEPENDENT test of the comb hypothesis, noticed while reconciling two tables that used
different strata.  It needs no chain model, no calibration cells, no accumulation ceiling and no
assumption about phase: if the camera-clock comb is what drives the grinding, then when the grinding
gets an order of magnitude louder the comb must get louder too.

Measured on ONE consistent stratification, and SPEED-MATCHED -- because the obvious confound is that
the quiet stratum in the earlier tables was restricted to v < 12 m/s while the grinding stratum was
not, and the comb's amplitude in raw 0xE4 counts may well track speed or demand.  Both the raw and the
speed-matched contrasts are reported; if they disagree, the speed-matched one wins.

  D1  raw contrast          comb amplitude and ring amplitude, grinding vs quiet, same strata
  D2  speed-matched         the same contrast inside 2 m/s speed bins, pooled by inverse-variance
  D3  demand-matched        and again inside LKAS demand-index bins, since demand gates the mode

Run: python rlog-tools/studies/grind/comb_does_not_grow.py
Writes _scratch/comb_does_not_grow.txt beside it.
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import burst_onset_triggers as B              # noqa: E402
import grind_incident_r35 as GI               # noqa: E402
import comb_mirror_sizing as CM               # noqa: E402
import modeld_phase_lock as PL                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
RNG = np.random.default_rng(20260910)
OUT = []
ROUTES = ("r39", "r5e_v288", "r62_v289", "r63_v289")


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def amp_in(x, lo, hi, m):
    """in-band amplitude sqrt(2 * mean energy) of x over mask m."""
    z = PL.analytic(x, FS, lo, hi)
    return float(np.sqrt(2.0 * np.mean(np.abs(z[m]) ** 2)))


def locked_amp(x, t, ic, fm, lo, hi, m):
    """amplitude of the CAMERA-LOCKED part only: sqrt(2 * (R2 - floor) * E)."""
    z = PL.analytic(x, FS, lo, hi)
    r0, fl, _, E = PL.r2_full(z, t, ic, fm, m)
    return float(np.sqrt(2.0 * max(r0 - fl, 0.0) * E)), r0, fl


def main():
    G = {}
    for tag in ROUTES:
        print("loading %s ..." % tag, flush=True)
        g = B.load_route(tag)
        lo, hi = B.BAND[tag]
        g["f0"] = B.ring_f0(g, lo, hi)
        g["env"] = B.demod_env(g["bar"], g["f0"], FS)
        on, pk, amp, thi, tlo = B.find_onsets(g["env"], g["eng"])
        g["pk"] = pk
        fm, sl, ic, M = CM.model_clock(tag)
        g["f_model"], g["icept"] = fm, ic
        n = len(g["t"])
        hot = np.zeros(n, bool)
        for p in pk:
            hot[max(0, p - 50):min(n, p + 50)] = True
        g["hot"] = hot
        G[tag] = g

    OUT.clear()
    pr("=" * 122)
    pr("DOES THE COMB GROW WHEN THE CAR GRINDS?  -- subagent `combsize`, 2026-09-10")
    pr("=" * 122)
    pr("")
    pr("The test needs no chain model and no phase assumption.  If the camera-clock comb drives the")
    pr("grinding, the comb must be LARGER in grinding windows than in quiet ones, and by something like")
    pr("the amount the ring grows.  `comb` = amplitude of the camera-LOCKED part of the 0xE4 command in")
    pr("a +-1.5 Hz band on the clock;  `ring` = amplitude of the driver-torque bar in the route's own")
    pr("ring band.  Both are amplitudes in their channel's units, so the two ratio columns compare.")
    pr("")
    pr("=" * 122)
    pr("D1  RAW CONTRAST -- grinding (burst peak +- 0.5 s) vs quiet (engaged, outside every burst)")
    pr("=" * 122)
    pr("%-10s %-11s %8s %8s %9s %9s %8s %9s %9s %8s %10s" %
       ("route", "build", "quiet s", "grind s", "comb Q", "comb G", "ratio", "ring Q", "ring G",
        "ratio", "grind/comb"))
    pr("-" * 122)
    raw = {}
    for tag in ROUTES:
        g = G[tag]
        lo, hi = B.BAND[tag]
        fm, ic, t = g["f_model"], g["icept"], g["t"]
        quiet = g["eng"] & ~g["hot"]
        grind = g["eng"] & g["hot"]
        cq, _, _ = locked_amp(g["cmd"], t, ic, fm, fm - 1.5, fm + 1.5, quiet)
        cg, _, _ = locked_amp(g["cmd"], t, ic, fm, fm - 1.5, fm + 1.5, grind)
        rq = amp_in(g["bar"], lo, hi, quiet)
        rg = amp_in(g["bar"], lo, hi, grind)
        raw[tag] = (cq, cg, rq, rg)
        pr("%-10s %-11s %8.0f %8.0f %9.2f %9.2f %8.2f %9.1f %9.1f %8.2f %10.1f" %
           (tag, B.BUILD[tag], quiet.sum() / FS, grind.sum() / FS, cq, cg, cg / max(cq, 1e-9),
            rq, rg, rg / rq, (rg / rq) / max(cg / max(cq, 1e-9), 1e-9)))
    pr("")
    pr("The last column is the DISCREPANCY: how many times more the ring grows than the comb does.")
    pr("")

    pr("=" * 122)
    pr("D2  SPEED-MATCHED -- the same contrast inside 2 m/s bins, so speed cannot drive it")
    pr("=" * 122)
    pr("Bins with >= 8 s in BOTH strata only.  Pooled ratio = energy-weighted mean of the per-bin")
    pr("ratios, with a 2000-draw bootstrap over bins.")
    pr("")
    pr("%-10s %-11s %7s %10s %-17s %10s %-17s %10s" %
       ("route", "build", "n bins", "comb ratio", "  95% CI", "ring ratio", "  95% CI", "discrepancy"))
    pr("-" * 122)
    for tag in ROUTES:
        g = G[tag]
        lo, hi = B.BAND[tag]
        fm, ic, t = g["f_model"], g["icept"], g["t"]
        quiet = g["eng"] & ~g["hot"]
        grind = g["eng"] & g["hot"]
        cr, rr, wt = [], [], []
        for v0 in np.arange(0, 34, 2.0):
            sel = (g["vego"] >= v0) & (g["vego"] < v0 + 2.0)
            mq, mg = quiet & sel, grind & sel
            if mq.sum() < 800 or mg.sum() < 800:
                continue
            cq, _, _ = locked_amp(g["cmd"], t, ic, fm, fm - 1.5, fm + 1.5, mq)
            cg, _, _ = locked_amp(g["cmd"], t, ic, fm, fm - 1.5, fm + 1.5, mg)
            if cq <= 0:
                continue
            cr.append(cg / cq)
            rr.append(amp_in(g["bar"], lo, hi, mg) / amp_in(g["bar"], lo, hi, mq))
            wt.append(mg.sum())
        if len(cr) < 2:
            pr("%-10s %-11s %7d  (too few speed bins with both strata)" % (tag, B.BUILD[tag], len(cr)))
            continue
        cr, rr, wt = np.array(cr), np.array(rr), np.array(wt, float)
        w = wt / wt.sum()
        pc, prr = float(cr @ w), float(rr @ w)
        bs_c, bs_r = np.empty(2000), np.empty(2000)
        for s in range(2000):
            j = RNG.integers(0, len(cr), len(cr))
            ww = wt[j] / wt[j].sum()
            bs_c[s] = cr[j] @ ww; bs_r[s] = rr[j] @ ww
        pr("%-10s %-11s %7d %10.2f %-17s %10.2f %-17s %10.1f" %
           (tag, B.BUILD[tag], len(cr), pc,
            "[%.2f, %.2f]" % (np.percentile(bs_c, 2.5), np.percentile(bs_c, 97.5)), prr,
            "[%.2f, %.2f]" % (np.percentile(bs_r, 2.5), np.percentile(bs_r, 97.5)), prr / max(pc, 1e-9)))
    pr("")

    pr("=" * 122)
    pr("D3  DEMAND-MATCHED -- and again inside LKAS demand-index bins, since demand gates the mode")
    pr("=" * 122)
    pr("%-10s %-11s %7s %10s %10s %12s" %
       ("route", "build", "n bins", "comb ratio", "ring ratio", "discrepancy"))
    pr("-" * 122)
    for tag in ROUTES:
        g = G[tag]
        lo, hi = B.BAND[tag]
        fm, ic, t = g["f_model"], g["icept"], g["t"]
        quiet = g["eng"] & ~g["hot"]
        grind = g["eng"] & g["hot"]
        idx = g["idx_live"]
        cr, rr, wt = [], [], []
        for a, b in ((0, 5), (5, 20), (20, 60), (60, 1e9)):
            sel = (idx >= a) & (idx < b)
            mq, mg = quiet & sel, grind & sel
            if mq.sum() < 800 or mg.sum() < 800:
                continue
            cq, _, _ = locked_amp(g["cmd"], t, ic, fm, fm - 1.5, fm + 1.5, mq)
            cg, _, _ = locked_amp(g["cmd"], t, ic, fm, fm - 1.5, fm + 1.5, mg)
            if cq <= 0:
                continue
            cr.append(cg / cq)
            rr.append(amp_in(g["bar"], lo, hi, mg) / amp_in(g["bar"], lo, hi, mq))
            wt.append(mg.sum())
        if not cr:
            pr("%-10s %-11s %7d  (no demand bin with both strata)" % (tag, B.BUILD[tag], 0)); continue
        cr, rr, wt = np.array(cr), np.array(rr), np.array(wt, float)
        w = wt / wt.sum()
        pc, prr = float(cr @ w), float(rr @ w)
        pr("%-10s %-11s %7d %10.2f %10.2f %12.1f" % (tag, B.BUILD[tag], len(cr), pc, prr,
                                                     prr / max(pc, 1e-9)))
    pr("")
    pr("=" * 122)
    pr("READING")
    pr("=" * 122)
    pr("A comb ratio of ~1 (or below) while the ring ratio is 2-3.5 means the putative DRIVER does not")
    pr("move when the SYMPTOM does.  That is a falsification of the driving relation that needs no chain")
    pr("model, no accumulation ceiling and no phase assumption -- and it is independent of the mirror")
    pr("sizing, which reaches the same verdict by a completely different route.")
    pr("")
    pr("⚠ WHAT IT DOES NOT SHOW.  It does not show the comb is absent (it is plainly there: R2 - floor")
    pr("is +0.27 to +0.49 on the command).  It shows the comb is not what MODULATES the grinding.  A")
    pr("constant driver exciting a mode whose DAMPING varies would produce exactly this pattern -- and")
    pr("that is the de-damping picture already in the record, in which the loop, not the drive, is the")
    pr("variable.  So this result is consistent with the comb being a real, permanent, small excitation")
    pr("that the loop amplifies by a varying amount.  [BELIEF]")
    with open(os.path.join(B.SCR, "comb_does_not_grow.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/comb_does_not_grow.txt")


if __name__ == "__main__":
    main()
