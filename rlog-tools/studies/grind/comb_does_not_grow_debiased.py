# -*- coding: utf-8 -*-
"""studies/grind/comb_does_not_grow_debiased.py -- DOES MY OWN 1e SURVIVE THE ESTIMATOR CORRECTION?
Subagent `combsize`, 2026-09-10.  ANALYSIS ONLY.

comb_lockfrac_estimator_test.py established, against a signal of KNOWN locked fraction p, that

    R2 - max(floor)   is BIASED LOW by ~0.12 (whole-stratum) and ~0.22 (20 s blocks)
    R2_deb = sqrt(max(R2^2 - mean(R2^2_detuned), 0))   tracks p to +-0.04

🛑 MY OWN 1e USED THE BIASED ONE.  `comb_does_not_grow.py` measured the camera-locked comb amplitude as
sqrt(2 * max(R2 - floor, 0) * E) and concluded the comb FALLS (x0.55-0.86) while the ring RISES
(x1.62-2.68).  But the bias in R2 - maxfloor DEPENDS ON SAMPLE SIZE, and my quiet strata are
systematically LONGER than my grinding strata -- a longer stratum has a lower floor, hence less
downward bias, hence a LARGER measured locked amplitude.  **That alone could manufacture the entire
result.**  If it did, 1e is an artefact and must be withdrawn.

This file re-runs 1e with R2_deb and reports both side by side.  It is written so it CAN come back
against me, and the verdict line says which way it came out.

Run: python rlog-tools/studies/grind/comb_does_not_grow_debiased.py
Writes _scratch/comb_does_not_grow_debiased.txt beside it.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import burst_onset_triggers as B              # noqa: E402
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


def r2_pair(z, t, ic, fm, m):
    """returns (R2 - maxfloor, R2_deb, E) on one stratum mask."""
    zz = z[m]
    tt = t[m] - ic
    den = float((np.abs(zz) ** 2).sum())

    def r2(f):
        return float(np.abs((zz ** 2 * np.exp(-2j * 2 * np.pi * tt * f)).sum()) / max(den, 1e-300))
    r0 = r2(fm)
    rd = np.array([r2(fm + d) for d in PL.DET])
    E = float(np.mean(np.abs(zz) ** 2))
    return max(r0 - rd.max(), 0.0), float(np.sqrt(max(r0 ** 2 - np.mean(rd ** 2), 0.0))), E


def amp_in(z, m):
    return float(np.sqrt(2.0 * np.mean(np.abs(z[m]) ** 2)))


def main():
    G = {}
    for tag in ROUTES:
        print("loading %s ..." % tag, flush=True)
        g = B.load_route(tag)
        lo, hi = B.BAND[tag]
        g["f0"] = B.ring_f0(g, lo, hi)
        g["env"] = B.demod_env(g["bar"], g["f0"], FS)
        on, pk, amp, thi, tlo = B.find_onsets(g["env"], g["eng"])
        fm, sl, ic, M = CM.model_clock(tag)
        g["f_model"], g["icept"] = fm, ic
        n = len(g["t"])
        hot = np.zeros(n, bool)
        for p in pk:
            hot[max(0, p - 50):min(n, p + 50)] = True
        g["hot"] = hot
        G[tag] = g

    OUT.clear()
    pr("=" * 126)
    pr("DOES 1e SURVIVE THE ESTIMATOR CORRECTION?  -- subagent `combsize`, 2026-09-10")
    pr("=" * 126)
    pr("1e concluded the camera-locked comb does NOT grow when the car grinds, using the locked")
    pr("amplitude sqrt(2 * max(R2 - floor, 0) * E).  That estimator is now known to be BIASED LOW by")
    pr("~0.12, and the bias depends on sample size -- and my quiet strata are LONGER than my grinding")
    pr("strata, which would bias the comb ratio DOWNWARD and manufacture exactly the result I reported.")
    pr("Re-run below with R2_deb, which recovers a known p to +-0.04.")
    pr("")
    pr("=" * 126)
    pr("D1'  RAW CONTRAST, both estimators side by side")
    pr("=" * 126)
    pr("%-10s %-11s %8s %8s | %9s %9s %8s | %9s %9s %8s | %9s %8s" %
       ("route", "build", "quiet s", "grind s",
        "cmbQ minus", "cmbG minus", "ratio", "cmbQ deb", "cmbG deb", "ratio", "ring ratio", "discrep"))
    pr("-" * 126)
    for tag in ROUTES:
        g = G[tag]
        lo, hi = B.BAND[tag]
        fm, ic, t = g["f_model"], g["icept"], g["t"]
        quiet = g["eng"] & ~g["hot"]
        grind = g["eng"] & g["hot"]
        zc = PL.analytic(g["cmd"], FS, fm - 1.5, fm + 1.5)
        zb = PL.analytic(g["bar"], FS, lo, hi)
        mq, dq, Eq = r2_pair(zc, t, ic, fm, quiet)
        mg, dg, Eg = r2_pair(zc, t, ic, fm, grind)
        cq_m, cg_m = np.sqrt(2 * mq * Eq), np.sqrt(2 * mg * Eg)
        cq_d, cg_d = np.sqrt(2 * dq * Eq), np.sqrt(2 * dg * Eg)
        rq, rg = amp_in(zb, quiet), amp_in(zb, grind)
        pr("%-10s %-11s %8.0f %8.0f | %9.2f %9.2f %8.2f | %9.2f %9.2f %8.2f | %9.2f %8.1f" %
           (tag, B.BUILD[tag], quiet.sum() / FS, grind.sum() / FS,
            cq_m, cg_m, cg_m / max(cq_m, 1e-9), cq_d, cg_d, cg_d / max(cq_d, 1e-9),
            rg / rq, (rg / rq) / max(cg_d / max(cq_d, 1e-9), 1e-9)))
    pr("")

    pr("=" * 126)
    pr("D2'  SPEED-MATCHED, 2 m/s bins, R2_deb -- the version that decides")
    pr("=" * 126)
    pr("%-10s %-11s %7s %12s %-17s %12s %-17s %10s" %
       ("route", "build", "n bins", "comb ratio", "  95% CI", "ring ratio", "  95% CI", "discrepancy"))
    pr("-" * 126)
    for tag in ROUTES:
        g = G[tag]
        lo, hi = B.BAND[tag]
        fm, ic, t = g["f_model"], g["icept"], g["t"]
        quiet = g["eng"] & ~g["hot"]
        grind = g["eng"] & g["hot"]
        zc = PL.analytic(g["cmd"], FS, fm - 1.5, fm + 1.5)
        zb = PL.analytic(g["bar"], FS, lo, hi)
        cr, rr, wt = [], [], []
        for v0 in np.arange(0, 34, 2.0):
            sel = (g["vego"] >= v0) & (g["vego"] < v0 + 2.0)
            a, b = quiet & sel, grind & sel
            if a.sum() < 800 or b.sum() < 800:
                continue
            _, da, Ea = r2_pair(zc, t, ic, fm, a)
            _, db, Eb = r2_pair(zc, t, ic, fm, b)
            ca, cb = np.sqrt(2 * da * Ea), np.sqrt(2 * db * Eb)
            if ca <= 0:
                continue
            cr.append(cb / ca); rr.append(amp_in(zb, b) / amp_in(zb, a)); wt.append(b.sum())
        if len(cr) < 2:
            pr("%-10s %-11s %7d  (too few bins)" % (tag, B.BUILD[tag], len(cr))); continue
        cr, rr, wt = np.array(cr), np.array(rr), np.array(wt, float)
        w = wt / wt.sum()
        pc, prr = float(cr @ w), float(rr @ w)
        bc, br = np.empty(2000), np.empty(2000)
        for s in range(2000):
            j = RNG.integers(0, len(cr), len(cr))
            ww = wt[j] / wt[j].sum()
            bc[s] = cr[j] @ ww; br[s] = rr[j] @ ww
        pr("%-10s %-11s %7d %12.2f %-17s %12.2f %-17s %10.1f" %
           (tag, B.BUILD[tag], len(cr), pc,
            "[%.2f, %.2f]" % (np.percentile(bc, 2.5), np.percentile(bc, 97.5)), prr,
            "[%.2f, %.2f]" % (np.percentile(br, 2.5), np.percentile(br, 97.5)), prr / max(pc, 1e-9)))
    pr("")
    pr("=" * 126)
    pr("VERDICT ON 1e")
    pr("=" * 126)
    pr("Compare the 'comb ratio' column here against the biased-estimator version in")
    pr("_scratch/comb_does_not_grow.txt (0.66 / 0.57 / 0.55 / 0.86, CIs excluding 1 on three routes).")
    pr("If the debiased comb ratios are still at or below ~1 while the ring ratios stay at 1.6-2.7,")
    pr("1e SURVIVES and the sample-size bias was not driving it.  If the debiased comb ratios rise to")
    pr("track the ring ratios, 1e was an artefact of my estimator and is WITHDRAWN.")
    with open(os.path.join(B.SCR, "comb_does_not_grow_debiased.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/comb_does_not_grow_debiased.txt")


if __name__ == "__main__":
    main()
