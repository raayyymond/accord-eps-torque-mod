# -*- coding: utf-8 -*-
"""rj6_sweep.py -- lens robust-joint, STAGE 2: the NONLINEAR byte-exact closed-loop replay (harness sweep_drive, mode B,
the real-fork port, the byte-exact lane, Karnopp plant) on the stage-1 finalists, V294 in the SAME batch.

Finalists (Kp flat = 960 g, b = 567 t / g, a / C / output lag / map / e_shift UNCHANGED = V294's):
  F1 t1.95 g1.00  (trim only)          F2 t1.95 g1.10          F3 t1.95 g1.20          F4 t1.95 g1.30
  F5 t1.00 g1.20  (FF only; linear-infeasible on the outer loop: the contrast)
  F6 t2.50 g1.20  (beyond the pre-registered restart-pulse cap: the runner-up that shows what H-SAFE-3 costs)
Plants: nominal, light_b, b_lo, F_hi, J_hi, tau6 (the harness DEFAULT_PLANTS); dists lp (the loop's own behaviour; the
outer-loop numbers retrodict) and full (disturbance replay: the counterfactual on r71b's road, biased to 'no change').
Writes rj6_sweep.json.  ANALYSIS ONLY."""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rj_cands as RC  # noqa: E402
from rj_lin import H  # noqa: E402

FIN = [("F1_t1.95_g1.00", 1.00, 1.95), ("F2_t1.95_g1.10", 1.10, 1.95), ("F3_t1.95_g1.20", 1.20, 1.95),
       ("F4_t1.95_g1.30", 1.30, 1.95), ("F5_t1.00_g1.20", 1.20, 1.00), ("F6_t2.50_g1.20", 1.20, 2.50)]
PLANTS = ("nominal", "light_b", "b_lo", "F_hi", "J_hi", "tau6")


def cands():
    out = []
    for nm, g, t in FIN:
        c = RC.make(g=g, t=t, name=nm, allow_opcode=False)
        out.append(c)
    return out


def main():
    cl = cands()
    for c in cl:
        print("%-16s Kp %s b %d a %d C %d e %d lag %d/%d  problems %s  diff %s" % (
            c.name, c.kp_y[0], c.fb_b, c.fb_a, c.fb_clamp, c.e_shift, c.lag_a, c.lag_b, c.problems(),
            {k: v[1] for k, v in c.diff(RC.base()).items()}))
    res = {}
    t0 = time.time()
    for p in PLANTS:
        S = H.sweep_drive(cl, plants=(p,), dists=("lp", "full"))
        for k, v in S.items():
            res["|".join(k)] = v
        print("  plant %-8s done  %.0f s" % (p, time.time() - t0), flush=True)
    meas = H.drive_metrics(H.drive_series_measured(H.route_chunks()))
    res["measured"] = meas
    json.dump(H.to_jsonable(res), open(os.path.join(HERE, "rj6_sweep.json"), "w"), indent=1)
    print("saved rj6_sweep.json  %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
