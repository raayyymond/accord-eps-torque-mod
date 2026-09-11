# -*- coding: utf-8 -*-
"""fvlc_f0_controls.py -- the CONTROL that the naive "f0 vs acting Kp" regression needs.
Subagent cyclekind, 2026-09-10.  ANALYSIS ONLY.

Why this exists: acting Kp is a DETERMINISTIC function of the LKAS demand index within a build
(record 0xE5378), so a pooled regression of f0 on Kp is perfectly confounded with any dependence of
f0 on DEMAND.  Two things separate them:
  1  on the FLAT-Kp builds (V281r3/V282/V288, Kp = 248 at every index) regress f0 on demand index.
     Any slope there is a pure demand effect with ZERO gain variation behind it.
  2  the identified gain contrast is BETWEEN builds AT MATCHED DEMAND AND SPEED: inside each
     (idx bin x speed bin) cell, compare f0 on the Kp-LERP builds against f0 on the flat-Kp builds,
     and divide the difference by that cell's own Kp difference.
Run: python fvlc_f0_controls.py     (writes _scratch/fvlc_f0_controls.txt)
"""
import os
import sys

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fvlc_lib as F            # noqa: E402
import fvlc_analysis as A       # noqa: E402

OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


FLAT = ("V281r3", "V282", "V288")
LERP = ("V278r3", "V280r2")


def collect(tags):
    rows = []
    for t in tags:
        b = F.BUILD[t]
        if b == "V289":
            continue                      # the notch build is the PHASE arm, not part of the gain test
        c = F.cells(b)
        g = A.R(t)
        eps, _ = A.EPS(t)
        for a, bb, fe in eps:
            if bb - a < 40:
                continue
            im = float(np.median(g["idx"][a:bb]))
            rows.append(dict(build=b, route=t, f0=fe, idx=im, vego=float(np.median(g["vego"][a:bb])),
                             kp=float(np.interp(im, c["kp_X"], c["kp_Y"])),
                             arm="LERP" if b in LERP else "FLAT"))
    return rows


def boots(fn, rows, n=3000, seed=4):
    rng = np.random.default_rng(seed)
    v = [fn([rows[i] for i in rng.integers(0, len(rows), len(rows))]) for _ in range(n)]
    v = np.array([x for x in v if np.isfinite(x)])
    return np.percentile(v, [2.5, 97.5]) if len(v) > 10 else (np.nan, np.nan)


def main():
    tags = [t for t in F.ROUTES if os.path.exists(os.path.join(F.SCR, "fvlc_%s.pkl" % t))]
    rows = collect(tags)
    pr("FVLC -- CONTROLS FOR THE f0-vs-GAIN TEST.  %d episodes, builds %s"
       % (len(rows), sorted({r["build"] for r in rows})))
    pr("")
    pr("=" * 110)
    pr("CONTROL 1 -- f0 vs DEMAND INDEX on the FLAT-Kp builds, where Kp is 248 at every index.")
    pr("=" * 110)
    for arm, names in (("FLAT", FLAT), ("LERP", LERP)):
        R = [r for r in rows if r["build"] in names]
        if len(R) < 20:
            continue
        x = np.array([r["idx"] for r in R]); y = np.array([r["f0"] for r in R])
        sl = stats.linregress(x, y)
        lo, hi = boots(lambda rr: stats.linregress([r["idx"] for r in rr], [r["f0"] for r in rr]).slope, R)
        span = np.percentile(x, 90) - np.percentile(x, 10)
        pr("  %-5s builds %-22s n=%4d : d f0 / d idx = %+.5f [%+.5f - %+.5f] Hz/count"
           % (arm, ",".join(names), len(R), sl.slope, lo, hi))
        pr("        -> %+.2f Hz over the p10-p90 demand span (%.1f counts), r = %+.3f, p = %.3g"
           % (sl.slope * span, span, sl.rvalue, sl.pvalue))
    pr("")
    pr("  If the FLAT arm shows the same slope as the LERP arm, the pooled 'f0 rises with Kp' regression is")
    pr("  a DEMAND effect wearing Kp's clothes, and carries no information about loop gain at all.")
    pr("")
    pr("=" * 110)
    pr("CONTROL 2 -- the IDENTIFIED gain contrast: LERP vs FLAT at MATCHED demand and speed")
    pr("=" * 110)
    idxq = np.percentile([r["idx"] for r in rows], [20, 40, 60, 80])
    vq = np.percentile([r["vego"] for r in rows], [33, 67])
    for r in rows:
        r["cell"] = int(np.digitize(r["idx"], idxq)) * 3 + int(np.digitize(r["vego"], vq))

    def contrast(rr):
        num = den = w = 0.0
        for cell in range(15):
            aL = [r["f0"] for r in rr if r["cell"] == cell and r["arm"] == "LERP"]
            aF = [r["f0"] for r in rr if r["cell"] == cell and r["arm"] == "FLAT"]
            kL = [r["kp"] for r in rr if r["cell"] == cell and r["arm"] == "LERP"]
            kF = [r["kp"] for r in rr if r["cell"] == cell and r["arm"] == "FLAT"]
            if len(aL) < 4 or len(aF) < 4:
                continue
            ww = min(len(aL), len(aF))
            num += ww * (np.median(aL) - np.median(aF))
            den += ww * (np.median(kL) - np.median(kF))
            w += ww
        return (num / w, den / w, w) if w else (np.nan, np.nan, 0)

    df, dk, w = contrast(rows)
    lo, hi = boots(lambda rr: contrast(rr)[0], rows)
    pr("  cells = 5 demand quintiles x 3 speed terciles; a cell counts only with >= 4 episodes on BOTH arms.")
    pr("  matched-cell weight n = %d" % w)
    pr("  mean Kp difference LERP - FLAT, over the same cells : %+.1f counts" % dk)
    pr("  mean f0 difference LERP - FLAT, over the same cells : %+.3f Hz  [%+.3f - %+.3f]" % (df, lo, hi))
    if np.isfinite(dk) and abs(dk) > 1:
        pr("  => IDENTIFIED  d f0 / d Kp = %+.5f [%+.5f - %+.5f] Hz per Kp count"
           % (df / dk, lo / dk, hi / dk))
        pr("     over a 248 -> 696 Kp span that is %+.2f Hz [%+.2f - %+.2f]"
           % (448 * df / dk, 448 * lo / dk, 448 * hi / dk))
    pr("")
    pr("=" * 110)
    pr("CONTROL 3 -- f0 vs SPEED, within demand strata, on the FLAT-Kp builds only")
    pr("=" * 110)
    R = [r for r in rows if r["arm"] == "FLAT"]
    for q, lab in ((0, "idx < median"), (1, "idx >= median")):
        med = np.median([r["idx"] for r in R])
        S = [r for r in R if (r["idx"] < med) == (q == 0)]
        if len(S) < 20:
            continue
        x = np.array([r["vego"] for r in S]); y = np.array([r["f0"] for r in S])
        sl = stats.linregress(x, y)
        lo2, hi2 = boots(lambda rr: stats.linregress([r["vego"] for r in rr], [r["f0"] for r in rr]).slope, S)
        span = np.percentile(x, 90) - np.percentile(x, 10)
        pr("  %-14s n=%4d : d f0/d vEgo = %+.4f [%+.4f - %+.4f] Hz per m/s  -> %+.2f Hz over p10-p90 (%.1f m/s)"
           % (lab, len(S), sl.slope, lo2, hi2, sl.slope * span, span))
    pr("")
    pr("  ⚠ the detection band for these builds is 18-22 Hz, so a real excursion beyond it is censored;")
    pr("    read the speed slope as a lower bound on the magnitude of any true speed dependence.")
    with open(os.path.join(F.SCR, "fvlc_f0_controls.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/fvlc_f0_controls.txt")


if __name__ == "__main__":
    main()
