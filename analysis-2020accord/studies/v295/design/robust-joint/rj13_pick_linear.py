# -*- coding: utf-8 -*-
"""rj13_pick_linear.py -- lens robust-joint: the pick's exact b value against the pre-registered M_SAFE edges (restart
pulse <= 2 x V294's at 100 deg/s, int32 margin >= 2.0), and the linear per-member tables of the named Pareto points
(inner |L|, Ms, GM incl. delay x1.5 via tau9; outer GM/Ms by member x speed; stress-mode zeta; |P/x|, |T/x| 10-25 Hz).
M_SAFE by the harness's own functions (byte-exact lane): restart_pulse, int32_margins, m_safe (rail, sub-rail, trim cap).
ANALYSIS ONLY."""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rj_lin as RL  # noqa: E402
import rj_cands as RC  # noqa: E402
from rj_lin import H  # noqa: E402


def main():
    base = RC.base()
    r0 = H.restart_pulse(base)
    print("V294 restart pulse %s ; int32 min margin %.3f" % ({k: v["peak"] for k, v in r0.items()},
                                                           min(v["margin"] for v in H.int32_margins(base).values())))
    print("b scan (Kp 960, a 1011, C 1024): restart peak at 10/30/100/300 deg/s, ms > 50 T, int32 margin")
    for b in (1000, 1050, 1080, 1106, 1120, 1134, 1150, 1200):
        c = base.replace(fb_b=b, name="b%d" % b)
        rp = H.restart_pulse(c)
        i32 = min(v["margin"] for v in H.int32_margins(c).values())
        print("   b %4d (t %.3f): peaks %s  ms>50 %s  i32 %.3f  -> H-SAFE-3 %s, H-SAFE-2 %s"
              % (b, b / 567.0, [rp[k]["peak"] for k in rp], [rp[k]["ms_above_50"] for k in rp], i32,
                 "PASS" if rp[100.0]["peak"] <= 2 * r0[100.0]["peak"] else "FAIL", "PASS" if i32 >= 2.0 else "FAIL"))
    ctx = RL.Ctx()
    bc = RL.base_cache(ctx, base)
    pts = [("P0 V294", base), ("P1 PICK b1106", base.replace(fb_b=1106, name="P1")),
           ("P2 Kp1056 b1005", RC.make(g=1.1, t=1.95, name="P2")), ("P3 Kp1152 b921", RC.make(g=1.2, t=1.95, name="P3")),
           ("P4 Kp1152 b1181 (x H-SAFE-3)", RC.make(g=1.2, t=2.5, name="P4")), ("P5 Kp1152 b472 (FF only)", RC.make(g=1.2, t=1.0, name="P5"))]
    evs = {}
    for nm, c in pts:
        ev = RL.evaluate(ctx, c, bc)
        evs[nm] = ev
        ms = H.m_safe(c)
        print("\n== %s  diff %s" % (nm, {k: v[1] for k, v in c.diff(base).items()}))
        print("   M_SAFE rail +%d/%d  sub-rail %.4f T/wire  trim cap %d T (%.1f %%)  b/b_max %.3f  int32 min %.2f  restart %s"
              % (ms["rail_pos"], ms["rail_neg"], ms["subrail_T_per_wire"], ms["trim_cap_T"], ms["trim_cap_pct_rail"],
                 ms["b_over_bmax"], min(v["margin"] for v in ms["int32"].values()), {k: v["peak"] for k, v in ms["restart"].items()}))
        print("   HF |P/x| 20 Hz %.3f (V294 2.079, V282 44.90)  max|P/x| 10-25 x%.2f  max|T/x| 10-25 x%.2f of V294"
              % (ev["P20"], ev["HF_P_ratio"], ev["HF_T_ratio"]))
        print("   inner worst: Ms %.3f  GM %.1f  |L|1-3 %.2f  |L|3-8 %.2f" % (ev["in_Ms"], ev["in_GM"], ev["in_L13"], ev["in_L38"]))
        print("   stress zeta (f Hz, zeta): " + "  ".join("%s@%g %.1f/%.3f" % (k[0], k[1], v[0], v[1]) for k, v in ev["stress"].items()))
        print("   outer GM (relay on, idx 10) member x speed %s:" % (RL.SPEEDS,))
        for m in RL.M_OUTER:
            print("     %-8s " % m + " ".join("%5.2f" % ev["outer"][(m, v, 10, True)]["GM"] for v in RL.SPEEDS)
                  + "   Ms " + " ".join("%4.2f" % ev["outer"][(m, v, 10, True)]["Ms"] for v in RL.SPEEDS)
                  + "   jerk(1.6-3Hz |S|, idx40) " + " ".join("%4.2f" % (ev["outer"][(m, v, 40, True)]["jerk"] /
                                                               evs["P0 V294"]["outer"][(m, v, 40, True)]["jerk"]) for v in RL.SPEEDS))


if __name__ == "__main__":
    main()
