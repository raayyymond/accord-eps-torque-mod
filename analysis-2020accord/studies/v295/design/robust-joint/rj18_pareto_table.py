# -*- coding: utf-8 -*-
"""rj18_pareto_table.py -- lens robust-joint: the named Pareto points on one table, every column from a saved output:
  linear (rj_lin, recomputed): pre-registered objective J, HF |P/x| ratio, outer GM worst-rel and light_b @ 26.9 m/s,
                                inner Ms worst, stress zeta worst-rel ; M_SAFE (harness): restart @100 deg/s, int32, trim cap
  nonlinear (rj6_sweep.json, rj15_extra.json, V294 in the same batch): tracking-gain change (min / max over members, lp),
                                hard-turn 1.6-3 Hz at 5-10 m/s and 1-3 Hz rate at 15-22 m/s (worst member over lp AND full).
ANALYSIS ONLY."""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rj_lin as RL  # noqa: E402
import rj_cands as RC  # noqa: E402
from rj_lin import H  # noqa: E402

PL = ("nominal", "light_b", "b_lo", "F_hi", "J_hi", "tau6")


def sim_cols(R, name, plants):
    dtg, hard, rmid15, rmid15_full = [], [], [], []
    for p in plants:
        for dist in ("lp", "full"):
            a = R.get("%s|%s|%s" % (dist, name, p)) or R.get("drive|%s|%s|%s" % (dist, name, p))
            b = R.get("%s|V294|%s" % (dist, p)) or R.get("drive|%s|V294|%s" % (dist, p))
            if a is None:
                continue
            hard.append(a["5-10"]["hard16"] / b["5-10"]["hard16"])
            rmid15.append(a["15-22"]["r_mid"] / b["15-22"]["r_mid"])
            if dist == "lp":
                dtg += [a[bd]["track_gain"] - b[bd]["track_gain"] for bd in ("0-5", "5-10", "15-22", "22+")]
    return (min(dtg), max(dtg)), (min(hard), max(hard)), (min(rmid15), max(rmid15)), len(set(plants))


def main():
    ctx = RL.Ctx()
    base = RC.base()
    bc = RL.base_cache(ctx, base)
    ev0 = RL.evaluate(ctx, base, bc)
    R6 = json.load(open(os.path.join(HERE, "rj6_sweep.json")))
    R15 = json.load(open(os.path.join(HERE, "rj15_extra.json")))
    pts = [("V294 (origin)", base, None, None),
           ("B  trim x1.5 (b 850)", base.replace(fb_b=850, name="B_t1.5"), R15, ("nominal", "light_b", "J_hi")),
           ("A  PICK trim x1.95 (b 1106)", base.replace(fb_b=1106, name="F1_t1.95_g1.00"), R6, PL),
           ("C  trim x1.95 + FF x1.1 (Kp 1056, b 1005)", RC.make(g=1.1, t=1.95, name="F2_t1.95_g1.10"), R6, PL),
           ("D  trim x1.95 + FF x1.2 (Kp 1152, b 921)", RC.make(g=1.2, t=1.95, name="F3_t1.95_g1.20"), R6, PL),
           ("E  trim x2.5 + FF x1.2 (Kp 1152, b 1181) [breaks H-SAFE-2/3]", RC.make(g=1.2, t=2.5, name="F6_t2.50_g1.20"), R6, PL),
           ("X  FF x1.2 only (Kp 1152, b 472) [dominated]", RC.make(g=1.2, t=1.0, name="F5_t1.00_g1.20"), R6, PL)]
    r0 = H.restart_pulse(base)[100.0]["peak"]
    print("%-58s %6s %5s %6s %6s %5s %6s | %4s %5s %5s | %-15s %-13s %-13s" % (
        "point", "J", "HF", "oGMr", "lbGM27", "inMs", "stress", "rp", "i32", "cap", "d track (lp)", "hard 5-10", "rate1-3 15-22"))
    rows = []
    for nm, c, R, plants in pts:
        ev = RL.evaluate(ctx, c, bc)
        S = RC.summarise(ev, ev0)
        rp = H.restart_pulse(c)[100.0]["peak"]
        i32 = min(v["margin"] for v in H.int32_margins(c).values())
        cap = H.m_safe(c)["trim_cap_T"]
        if R is not None:
            (t0, t1), (h0, h1), (m0, m1), n = sim_cols(R, c.name, plants)
            simtxt = "%+.3f..%+.3f   x%.2f..x%.2f   x%.2f..x%.2f  (%d members)" % (t0, t1, h0, h1, m0, m1, n)
        else:
            simtxt = "0 / x1 / x1"
        print("%-58s %+6.3f %5.2f %6.2f %6.2f %5.2f %6.2f | %4d %5.2f %5d | %s"
              % (nm, RC.objective(S), max(S["HF_P"], S["HF_T"]), S["out_gm_rel"], ev["outer"][("light_b", 26.9, 10, True)]["GM"],
                 S["in_Ms"], S["stress_rel"], rp, i32, cap, simtxt))
        rows.append(dict(point=nm, J=RC.objective(S), HF=max(S["HF_P"], S["HF_T"]), out_gm_rel=S["out_gm_rel"],
                         lbGM27=ev["outer"][("light_b", 26.9, 10, True)]["GM"], in_Ms=S["in_Ms"], stress_rel=S["stress_rel"],
                         restart100=rp, restart_cap=2 * r0, i32=i32, trim_cap=cap, sim=simtxt, feasible_linear=S["feasible"]))
    json.dump(rows, open(os.path.join(HERE, "rj18_pareto_table.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
