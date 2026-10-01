# -*- coding: utf-8 -*-
"""ds_d3_tune.py -- can the CASCADE (D3) meet the goal's own tracking metric (>= 0.95 in every band >= 8 m/s) at all?
The cascade's I integrates the INNER error (4 sp_r - R x): the integral of the rate feedback is a P on the MEASURED angle
(I-P structure), so the setpoint reaches the torque only through the outer P and the integral of the outer error.
This sweeps (Kp_in, Ki_in) on the fresh-operand cascade (D3b) and the held one (D3a): each pair's own gated envelope at
the explore speeds, then the goal metric (c1r2_trackmetric weights, min over the tracking members) at 0.96 x that
envelope.  ANALYSIS ONLY.  usage: python ds_d3_tune.py  (writes ds_d3_tune_out.txt)"""
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ds_model as M  # noqa: E402
import ds_gate2 as G2  # noqa: E402
import ds_explore as X  # noqa: E402

SP = [3.0, 8.0, 10.0, 11.9, 12.5, 15.0, 17.0, 19.0, 22.0, 27.0]
MEMS = ("nominal", "b_lo", "b_hi", "J_hi", "J1.0", "b_q", "b_q*J_hi", "b_q*J1.0", "b_lo*J_hi", "ms_free")


def goal_min(des, env):
    import c1r2_trackmetric as TM
    out = []
    for v in SP:
        if v < 8.0:
            continue
        G = 0.96 * env[v]
        vals = []
        for m in MEMS:
            pl, d, ea, _ = G2.member(m, v)
            dd = replace(des, G=G, d=d, extra_age=ea)
            vals.append(TM.slope(lambda f, dd=dd, pl=pl: M.loop_frf(dd, pl, np.asarray(f, float))["Tr"], v))
        out.append(min(vals))
    return out


if __name__ == "__main__":
    lines = []
    P = lambda s="": (print(s, flush=True), lines.append(s))  # noqa: E731
    t0 = time.time()
    for cop in ("fresh", "held"):
        for kp, ki in ((46, 12), (40, 20), (40, 28), (32, 24), (46, 32), (24, 12), (24, 24), (16, 16)):
            if cop == "held" and kp > 24:
                continue
            des = M.Des(f"D3 {cop} Kp{kp} Ki{ki}", kind="cascade", kp=kp, ki=ki, ka=4.0, dsrc="none", cop=cop)
            e = G2.envelope(des, members=G2.GATED, grid=SP)
            g = goal_min(des, e["env"])
            P(f"{des.name:24s} T/deg@env " + " ".join(f"{v:g}:{0.1602 * X.p_per_deg(des, e['env'][v]):3.0f}" for v in SP)
              + " | goal min >=8 m/s " + " ".join(f"{x:.3f}" for x in g) + f" | worst {min(g):.3f}"
              + f"  [{time.time() - t0:.0f}s]")
    (HERE / "ds_d3_tune_out.txt").write_text("\n".join(lines), encoding="utf-8")
