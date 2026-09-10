# -*- coding: utf-8 -*-
"""studies/grind/basepick_effective_kd.py -- score each option at the Kd its OWN REGIME actually delivers.
Agent `basepick`, 2026-09-09.  Analysis only: builds nothing, flashes nothing, sends nothing.

`basepick_v290.py` scored the small-signal columns at Kd = Y[0] and the authority columns at Kd = Y[3] = 128.
Both are idealisations.  `basepick_kd_reach.py` measured the DELIVERED mean Kd per regime off the wire:

    regime                 row S delivers (r62 / r63 / r5e)
    cruise                 96.0 / 96.1 / 96.0     -- the full dose
    ALL engaged           101.4 / 102.0 / 102.7
    GRINDING episodes     106.5 / 118.9 / 115.5   -- only a THIRD of the dose
    capped step (pkR)     124.9 / 122.8 / 123.6   -- authority nearly untouched
    full-lock turn (gate) 124.8 / 121.4 / 124.3   -- gate nearly untouched, but NOT exactly 128

This file interpolates the metrics on a fine Kd grid and reads each column off at the regime's delivered Kd.
That is the honest reading, and it is neither the optimistic nor the pessimistic idealisation.

Run:  python basepick_effective_kd.py   -> _scratch/basepick_effective_kd.txt
"""
import json
import os
import sys

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

import design290b_candidates as D    # noqa: E402
import reconcile_v290 as RC          # noqa: E402
import basepick_v290 as BP           # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


# measured delivered mean Kd under row S (Y[0..2]=96, Y[3]=128), from basepick_kd_reach.py
DELIVERED_S = {
    "cruise":    (96.0, 96.1, 96.0),
    "engaged":   (101.4, 102.0, 102.7),
    "grinding":  (106.5, 118.9, 115.5),
    "cappedstep": (124.9, 122.8, 123.6),
    "fulllock":  (124.8, 121.4, 124.3),
}
# and under row S' (Y[0..2]=112)
DELIVERED_Sp = {
    "cruise":    (112.0, 112.0, 112.0),
    "engaged":   (114.7, 115.0, 115.3),
    "grinding":  (117.3, 123.5, 121.7),
    "cappedstep": (126.4, 125.4, 125.8),
    "fulllock":  (126.4, 124.7, 126.2),
}

GRID = [128, 126, 124, 122, 120, 118, 116, 114, 112, 108, 104, 100, 96]


def main():
    c, c282 = D.cells()
    BP.C282 = c282
    fam, stab, burst = RC.load_family()
    BP.SUBP = [D.mkplant(p) for p in burst]
    el0 = RC.ElecP(c282)
    BP.BSUB = [D.metrics(el0, pl, None) for pl in BP.SUBP]

    bases = [("A  V282 base", c282, False), ("B  V289 base", c, True), ("D  C base (fb notch 21.5 Q1.5, fb 40)", c282, "fb")]
    curves = {}
    pr("basepick_effective_kd -- metrics on a fine Kd grid, %d burst-consistent fits" % len(BP.SUBP))
    for lab, cb, kind in bases:
        pr("")
        pr("=" * 120)
        pr("%s" % lab)
        pr("  %4s | %7s %7s %7s | %6s | %6s %6s | %6s | %6s" % ("Kd", "z_w", "z_med", "f@z_w", "Ms_w", "pkR_m", "pkR_w", "gate73", "PM_w"))
        rows = []
        for kd in GRID:
            if kind == "fb":
                el = BP.notch_fb(cb, 21.5, 1.5, 40.0, kd)
            else:
                el = RC.ElecP(BP.kd_cells(cb, kd), notch289=bool(kind))
            s = BP.agg(el, el0, BP.SUBP, BP.BSUB)
            pf = D.plant_free(el, el0)
            rows.append(dict(kd=kd, gate=pf["gate"], **s))
            pr("  %4d | %+7.4f %+7.4f %7.2f | %6.1f | %6.3f %6.3f | %6.4f | %+6.1f"
               % (kd, s["z_w"], s["z_med"], s["f_at_w"], s["Ms_w"], s["pkR_med"], s["pkR_w"], pf["gate"], s["pm_w"]))
        curves[lab] = rows

    # ---- read each regime off the curve at its delivered Kd -----------------------------------------
    def interp(rows, key, kd):
        x = np.array([r["kd"] for r in rows], float)[::-1]
        y = np.array([r[key] for r in rows], float)[::-1]
        return float(np.interp(kd, x, y))

    for tag, DEL in (("row S  (Y[0..2] = 96)", DELIVERED_S), ("row S' (Y[0..2] = 112)", DELIVERED_Sp)):
        pr("")
        pr("=" * 150)
        pr("EFFECTIVE-Kd READING -- %s.  Each column read at the mean Kd that regime actually delivers" % tag)
        pr("(r62 / r63 / r5e_v288).  This is the number to quote, not the Y[0] or the Y[3] idealisation.")
        pr("=" * 150)
        pr("  %-40s | %-26s | %-26s | %-26s" % ("base", "GRINDING  z_w (Kd)", "capped step pkR_med (Kd)", "full-lock gate73 (Kd)"))
        for lab, rows in curves.items():
            g = ["%.4f@%.0f" % (interp(rows, "z_w", k), k) for k in DEL["grinding"]]
            p = ["%.3f@%.0f" % (interp(rows, "pkR_med", k), k) for k in DEL["cappedstep"]]
            t = ["%.4f@%.0f" % (interp(rows, "gate", k), k) for k in DEL["fulllock"]]
            pr("  %-40s | %-26s | %-26s | %-26s" % (lab, " ".join(g), " ".join(p), " ".join(t)))
        pr("  cruise (idx p50 3, 94-100 %% of its time at Y[0]) gets the FULL dose: read the Kd = Y[0] row above.")

    json.dump(curves, open(os.path.join(SCR, "basepick_effective_kd.json"), "w"), indent=0, default=float)
    open(os.path.join(SCR, "basepick_effective_kd.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/basepick_effective_kd.txt")


if __name__ == "__main__":
    main()
