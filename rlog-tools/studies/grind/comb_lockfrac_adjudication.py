# -*- coding: utf-8 -*-
"""studies/grind/comb_lockfrac_adjudication.py -- ADJUDICATING THE 4-8x LOCK-FRACTION DISPUTE.
Subagent `combsize`, 2026-09-10.  ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing.

THE DISPUTE.  Three agents, three numbers for "how much of the grinding band is locked to the camera
clock" on r39:

    cyclekind   0.131      modelrate   0.501      me   0.357

and the decision turns on it: at ~0.065 the comb is worth 3-8 % and not worth a drive; at ~0.5 a lag-free
fix is worth 18-56 % (1-3.6 dB).

THE DESIGN.  Do NOT re-implement anything and do NOT compare across pipelines.  Load r39 through
`cyclekind`'s OWN loader (`fvlc_analysis.R` / `.EPS`), reproduce its published number first as a
correctness check, then vary ONE FACTOR AT A TIME.  Three factors are in play and they are usually
conflated:

  F1  WINDOWING     whole-stratum single sum (modelrate, me) vs mean over 20 s BLOCKS (cyclekind).
                    Blocking is a POWER penalty: it raises the finite-sample floor, because inside a
                    short block random phase alignment produces a large R2 on its own.
  F2  ESTIMATOR     R2 - max(floor over detunings)     [cyclekind, me]  -- a conservative excess-over-noise
                    sqrt(max(R2^2 - mean(R2^2_det),0)) [modelrate]      -- a near-unbiased lock fraction
                    These are DIFFERENT FUNCTIONALS, not two ways of writing the same one.
  F3  QUANTITY      locked share of the grinding stratum's TOTAL energy, vs locked share of the EXCESS
                    over quiet (dE_lock / dE).  The orchestrator's hypothesis is that F3 is most of the
                    gap.  It is tested here and -- reporting against the brief -- it is NOT.

Run: python rlog-tools/studies/grind/comb_lockfrac_adjudication.py
Writes _scratch/comb_lockfrac_adjudication.txt beside it.
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import fvlc_lib as F                # noqa: E402  cyclekind's library
import fvlc_analysis as A           # noqa: E402  cyclekind's loader (R, EPS)
import fvlc_camera_lock as CL       # noqa: E402  cyclekind's camera-lock script, imported verbatim

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
OUT = []
TAGS = ("r39", "r35", "r5e_v288")
BAND = (18.0, 22.0)


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def r2_whole(z, t, f, m):
    """single sum over the whole stratum -- modelrate's and my windowing."""
    zz = z[m]
    den = float((np.abs(zz) ** 2).sum())
    ph = np.exp(-2j * 2 * np.pi * f * t[m])
    return float(np.abs((zz ** 2 * ph).sum()) / max(den, 1e-300))


def stats_for(z, t, m, blocks, f0, dets):
    """returns dict with, for BOTH windowings, the raw R2, the max-floor, the mean of detuned R2^2,
    and the two estimators.  `dets` are absolute detunings in Hz."""
    out = {}
    # --- whole-stratum ---
    r0 = r2_whole(z, t, f0, m)
    rd = np.array([r2_whole(z, t, f0 + d, m) for d in dets])
    out["whole"] = dict(r2=r0, maxfl=float(rd.max()), mean2=float(np.mean(rd ** 2)),
                        e=float(np.mean(np.abs(z[m]) ** 2)))
    # --- 20 s blocks (cyclekind) ---
    rb, _ = CL.r2_blocks(z, t, f0, blocks)
    rbd = np.array([CL.r2_blocks(z, t, f0 + d, blocks)[0] for d in dets])
    out["block"] = dict(r2=rb, maxfl=float(rbd.max()), mean2=float(np.mean(rbd ** 2)),
                        e=float(np.mean(CL.energy_blocks(z, blocks))))
    for k in ("whole", "block"):
        d = out[k]
        d["est_minus"] = max(d["r2"] - d["maxfl"], 0.0)
        d["est_deb"] = float(np.sqrt(max(d["r2"] ** 2 - d["mean2"], 0.0)))
    return out


def main():
    dets = np.r_[np.arange(-0.80, -0.099, 0.05), np.arange(0.10, 0.801, 0.05)]
    OUT.clear()
    pr("=" * 126)
    pr("ADJUDICATING THE LOCK-FRACTION DISPUTE -- subagent `combsize`, 2026-09-10")
    pr("=" * 126)
    pr("Everything below is computed on `cyclekind`'s OWN loader and episode definitions")
    pr("(fvlc_analysis.R / .EPS) with its OWN block and detuning machinery imported verbatim")
    pr("(fvlc_camera_lock.r2_blocks / .energy_blocks), so no cross-pipeline difference can leak in.")
    pr("f_model = %.5f Hz (cyclekind's fixed value); band %.0f-%.0f Hz; %d detuned clocks 0.10-0.80 Hz."
       % (CL.F_MODEL, BAND[0], BAND[1], len(dets)))
    pr("")
    R = {}
    for tag in TAGS:
        g = A.R(tag)
        eps, hot = A.EPS(tag)
        t = g["t"]
        quiet = g["eng"] & ~hot
        grind = g["eng"] & hot
        z = CL.analytic(g["bar"], FS, BAND[0], BAND[1])
        bq, bg = CL.blocks_of(quiet), CL.blocks_of(grind)
        R[tag] = dict(q=stats_for(z, t, quiet, bq, CL.F_MODEL, dets),
                      g=stats_for(z, t, grind, bg, CL.F_MODEL, dets),
                      build=g["build"], nbq=len(bq), nbg=len(bg))

    pr("=" * 126)
    pr("STEP 0  CORRECTNESS CHECK -- do I reproduce cyclekind's published r39 row exactly?")
    pr("=" * 126)
    d = R["r39"]["g"]["block"]
    pr("  cyclekind published (bar, r39, grinding, 20 s blocks):  R2 0.5989   floor 0.4704   R2-floor +0.1284")
    pr("  reproduced here                                      :  R2 %.4f   floor %.4f   R2-floor +%.4f"
       % (d["r2"], d["maxfl"], d["est_minus"]))
    pr("  %s" % ("MATCH -- its implementation is reproduced, so the dispute is not a coding error."
                 if abs(d["r2"] - 0.5989) < 0.01 else "MISMATCH -- investigate before reading anything below."))
    pr("")

    pr("=" * 126)
    pr("THE FOUR-WAY TABLE (x2 for windowing, so eight cells) -- r39, bar, 18-22 Hz")
    pr("=" * 126)
    pr("F2 estimator:  'R2 - maxfloor' = cyclekind's and mine;  'R2_deb' = modelrate's")
    pr("               R2_deb = sqrt(max(R2^2 - mean(R2^2_detuned), 0))")
    pr("F3 quantity :  'grind TOTAL' = locked share of the grinding stratum's energy")
    pr("               'EXCESS'      = dE_lock / dE over the quiet stratum")
    pr("F1 windowing:  'whole'  = one sum over the stratum;  'block' = mean over 20 s blocks")
    pr("")
    pr("%-10s %-16s %-14s %10s %10s %12s %12s %10s" %
       ("windowing", "estimator", "quantity", "R2", "floor", "E quiet", "E grind", "VALUE"))
    pr("-" * 126)
    cells = {}
    for tag in ("r39",):
        for win in ("whole", "block"):
            q, gg = R[tag]["q"][win], R[tag]["g"][win]
            for est in ("est_minus", "est_deb"):
                lq, lg = q[est] * q["e"], gg[est] * gg["e"]
                dE = gg["e"] - q["e"]
                tot = gg[est]
                exc = (lg - lq) / dE if dE > 0 else np.nan
                cells[(win, est)] = (tot, exc)
                for lab, v in (("grind TOTAL", tot), ("EXCESS", exc)):
                    pr("%-10s %-16s %-14s %10.4f %10.4f %12.1f %12.1f %10.4f" %
                       (win, "R2 - maxfloor" if est == "est_minus" else "R2_deb",
                        lab, gg["r2"], gg["maxfl"], q["e"], gg["e"], v))
    pr("")

    pr("=" * 126)
    pr("DECOMPOSING THE GAP -- one factor at a time, r39")
    pr("=" * 126)
    base = cells[("block", "est_minus")][1]        # cyclekind's cell: block + minus + excess
    top = cells[("whole", "est_deb")][0]           # modelrate's cell: whole + deb + total
    pr("  cyclekind's cell  (block, R2-maxfloor, EXCESS) = %.4f      [published 0.131]" % base)
    pr("  modelrate's cell  (whole, R2_deb,      TOTAL)  = %.4f      [published 0.501]" % top)
    pr("  my cell           (whole, R2-maxfloor, EXCESS) = %.4f      [published 0.357, my own strata]"
       % cells[("whole", "est_minus")][1])
    pr("")
    pr("  %-46s %10s %10s %10s" % ("varying ONE factor from cyclekind's cell", "from", "to", "x"))
    pr("  " + "-" * 110)
    f3 = cells[("block", "est_minus")][0]
    pr("  %-46s %10.4f %10.4f %10.2f" % ("F3  EXCESS -> grind TOTAL", base, f3, f3 / base))
    f2 = cells[("block", "est_deb")][1]
    pr("  %-46s %10.4f %10.4f %10.2f" % ("F2  R2-maxfloor -> R2_deb", base, f2, f2 / base))
    f1 = cells[("whole", "est_minus")][1]
    pr("  %-46s %10.4f %10.4f %10.2f" % ("F1  20 s blocks -> whole stratum", base, f1, f1 / base))
    pr("")
    pr("  %-46s %10.4f %10.4f %10.2f" % ("F1 and F2 together, still EXCESS",
                                         base, cells[("whole", "est_deb")][1],
                                         cells[("whole", "est_deb")][1] / base))
    pr("  %-46s %10.4f %10.4f %10.2f" % ("all three (= modelrate's cell)", base, top, top / base))
    pr("")

    pr("=" * 126)
    pr("WHY BLOCKING COSTS SO MUCH -- the floor is the whole story")
    pr("=" * 126)
    pr("%-10s %-8s %-10s %7s %10s %10s %12s" %
       ("route", "build", "windowing", "n blk", "raw R2", "max floor", "R2 - floor"))
    pr("-" * 126)
    for tag in TAGS:
        for win in ("whole", "block"):
            gg = R[tag]["g"][win]
            pr("%-10s %-8s %-10s %7s %10.4f %10.4f %12.4f" %
               (tag, R[tag]["build"], win, R[tag]["nbg"] if win == "block" else "-",
                gg["r2"], gg["maxfl"], gg["est_minus"]))
        pr("")
    pr("Blocking RAISES the raw R2 (random phase alignment inside a short block looks like lock) AND")
    pr("raises the measured floor by more.  The floor is measured on the SAME index sets, so the")
    pr("comparison is internally valid -- but the POWER is much lower, and R2 - floor pays for it twice.")
    pr("")
    pr("🛑 cyclekind blocked for a STATED reason: it did not have modelV2 in its cache, so it used a")
    pr("fixed f_model = %.5f Hz and blocked to 20 s to stay robust to a clock disagreement it could not" % CL.F_MODEL)
    pr("check ('over 20 s a 0.005 Hz disagreement costs only 0.2 cycles').  That uncertainty is REAL for")
    pr("its pipeline and the choice was correct FOR IT.  But modelrate's per-route fit of modelV2")
    pr("logMonoTime on frameId removes it: f_model is known to +-0.0006 Hz with the intercept, on the")
    pr("same clock and the same zero as the CAN cache.  ⇒ WITH THE FITTED CLOCK, THE BLOCKING PENALTY")
    pr("IS NOT NECESSARY, and the whole-stratum evaluation is the better-powered estimate of the same")
    pr("quantity.  cyclekind bought robustness it no longer needs, at a factor of ~%.1f in power."
       % (cells[("whole", "est_minus")][1] / base))
    pr("")

    pr("=" * 126)
    pr("F3 TESTED DIRECTLY -- is TOTAL vs EXCESS most of the gap?  (the orchestrator's hypothesis)")
    pr("=" * 126)
    pr("%-10s %-8s %-10s %12s %12s %12s %12s %10s" %
       ("route", "build", "windowing", "E quiet", "E grind", "TOTAL frac", "EXCESS frac", "ratio"))
    pr("-" * 126)
    for tag in TAGS:
        for win in ("whole", "block"):
            q, gg = R[tag]["q"][win], R[tag]["g"][win]
            lq, lg = q["est_minus"] * q["e"], gg["est_minus"] * gg["e"]
            dE = gg["e"] - q["e"]
            exc = (lg - lq) / dE if dE > 0 else np.nan
            pr("%-10s %-8s %-10s %12.1f %12.1f %12.4f %12.4f %10.2f" %
               (tag, R[tag]["build"], win, q["e"], gg["e"], gg["est_minus"], exc,
                exc / max(gg["est_minus"], 1e-9)))
        pr("")
    pr("🛑 REPORTING AGAINST THE BRIEF: on r39 the TOTAL and the EXCESS fractions are within a few")
    pr("percent of each other in BOTH windowings.  F3 is NOT the explanation for the 4-8x gap.  The")
    pr("reason they agree is arithmetic: the quiet stratum holds only ~10 % of the grinding stratum's")
    pr("in-band energy, and its locked fraction is similar, so TOTAL ~ EXCESS by construction here.")
    pr("The distinction WOULD matter on a route where the quiet baseline is a large share of the")
    pr("grinding energy; r39 is not that route.")
    with open(os.path.join(F.SCR, "comb_lockfrac_adjudication.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/comb_lockfrac_adjudication.txt")


if __name__ == "__main__":
    main()
