# -*- coding: utf-8 -*-
"""rj2_probe.py -- lens robust-joint: the linear scorer on a handful of one-knot moves around V294 (+ V293 as the control)
to see the magnitudes and the directions before the joint grid.  ANALYSIS ONLY."""
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rj_lin as RL  # noqa: E402
import rj_cands as RC  # noqa: E402
from rj_lin import H  # noqa: E402


def main():
    ctx = RL.Ctx()
    b0 = RC.base()
    bc = RL.base_cache(ctx, b0)
    t0 = time.time()
    ev0 = RL.evaluate(ctx, b0, bc)
    print("V294 eval %.2f s" % (time.time() - t0))
    probes = [("V294", b0), ("V293 (C=0)", b0.replace(fb_clamp=0, name="V293c")),
              ("t2", RC.make(t=2)), ("t3", RC.make(t=3)), ("t4", RC.make(t=4)), ("t0.5", RC.make(t=0.5)),
              ("g1.2", RC.make(g=1.2)), ("g1.4", RC.make(g=1.4)), ("g0.9", RC.make(g=0.9)),
              ("fb1.0", RC.make(f_fb=1.0)), ("fb4", RC.make(f_fb=4.0)), ("fb8", RC.make(f_fb=8.0)),
              ("lag3.5", RC.make(f_lag=3.5)), ("lag10", RC.make(f_lag=10.0)), ("lag14", RC.make(f_lag=14.0)),
              ("kd48", RC.make(kd=48)), ("lowboost", RC.make(sched="lowboost")), ("turnboost", RC.make(sched="turnboost")),
              ("g1.2 t2", RC.make(g=1.2, t=2)), ("g1.2 t2 lag10", RC.make(g=1.2, t=2, f_lag=10)),
              ("g1.3 t3 lag10", RC.make(g=1.3, t=3, f_lag=10))]
    keys = ("HF_P", "HF_T", "stress_rel", "in_Ms", "in_GM", "in_L13", "out_gm_rel", "out_ms_bad", "out_gm_min", "out_gm_lb_hwy",
            "jerk_worst", "jerk_best", "jerk_nom", "jerk_lb", "loose_lo_worst", "loose_lo_nom", "loose_hw_worst", "loose_hw_nom",
            "track_worst", "track_nom", "track_R2_nom12", "track_slope_nom12", "ffdel_nom8", "track_nom8", "track_nom17", "track_lb27")
    for nm, c in probes:
        t0 = time.time()
        ev = RL.evaluate(ctx, c, bc)
        S = RC.summarise(ev, ev0)
        print("-- %-16s (%.2fs) %s  diff %s" % (nm, time.time() - t0, "FEAS" if S["feasible"] else "INFEAS %s" % S["fails"],
                                              {k: v[1] for k, v in c.diff(b0).items()}))
        print("   " + "  ".join("%s %.3g" % (k, S[k]) for k in keys) + "  J %.3f" % RC.objective(S))
    # V294's own outer margins, worst per member at highway, for the record
    print("\nV294 outer GM (relay on, idx 10) by member x speed:")
    for nm in RL.M_OUTER:
        print("  %-9s " % nm + " ".join("%5.1f" % ev0["outer"][(nm, v, 10, True)]["GM"] for v in RL.SPEEDS)
              + "   Ms " + " ".join("%4.2f" % ev0["outer"][(nm, v, 10, True)]["Ms"] for v in RL.SPEEDS)
              + "   act/plan(0.1-0.3Hz) " + " ".join("%4.2f" % ev0["outer"][(nm, v, 10, True)]["track"] for v in RL.SPEEDS)
              + "   FF-only " + " ".join("%4.2f" % ev0["outer"][(nm, v, 10, True)]["ffdel"] for v in RL.SPEEDS))


if __name__ == "__main__":
    main()
