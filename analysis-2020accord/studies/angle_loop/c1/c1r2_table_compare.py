# -*- coding: utf-8 -*-
"""c1r2_table_compare.py -- candidate rev-2 tables (all fitted >= 4 % under the factorial envelope at Kd 20 / Ki 56 /
Kp 112) scored on the goal's own tracking metric (c1r2_trackmetric, inner-loop factor) for the members that bind it,
plus the integer-walk margin.  ANALYSIS ONLY.  usage: python c1r2_table_compare.py"""
import sys
from dataclasses import replace
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lib as C, c1r2_members as M, c1r2_trackmetric as TM, harness_freq as HF, c1r2_fit_table as F  # noqa

CANDS = {   # every table >= 4 % under the FACTORIAL envelope (Kd 20, Ki_base 56, Kp_base 112)
    "7k THE C1r2 TABLE": C.VARIANTS["r2"]["knots"],
    "5k (36 B)": [(3.1, 940), (8.0, 1300), (10.0, 847), (11.75, 701), (26.9, 2041)],
    "7k DP (area)": [(3.1, 959), (5.75, 1197), (11.75, 720), (11.9, 713), (15.5, 1051), (18.0, 1396), (26.9, 2041)],
}
MEMS = ("nominal", "b_hi", "b_lo", "J_hi", "J1.0", "b_q", "b_q*J_hi", "b_q*J1.0", "b/1.9*J1.0")


def slope(v, mem, tbl):
    J, b, k, tau, ea = M.params(mem, v)
    p = HF.Plant(J=J, b=b, k=k, tau=tau)
    c = replace(C.hf_ctl(v, tbl, kd=C.KD), d=tau)
    T = lambda f: HF.C_ref(np.asarray(f), c) * p.frf(np.asarray(f)) / (1 + HF.C_fb(np.asarray(f), c) * p.frf(np.asarray(f)))  # noqa
    return TM.slope(T, v)


if __name__ == "__main__":
    vs, env = F.load_env(C.KD, C.KI_BASE)
    bound = np.floor(env * 0.96)
    for lab, kn in CANDS.items():
        ok, tbl, w = F.walk_ok(kn, vs, bound)
        g = np.array([C.cave_G(C.spd_counts(v), tbl) for v in vs])
        print(f"== {lab}: {len(kn)} knots, walk <= 0.96 env: {ok}; min margin {100 * (1 - g / env).min():.1f} %")
        print("   Kp_eff 3/6/8/10/11.9/12.5/15/17/19/22/27: " +
              str([round(C.KP_BASE * C.cave_G(C.spd_counts(v), tbl) / 256) for v in (3, 6, 8, 10, 11.9, 12.5, 15, 17, 19, 22, 27)]))
        worst = {}
        for v in (8, 10, 11.9, 12.5, 13, 15, 16, 17, 18, 19, 22, 26, 30):
            for m in MEMS:
                s = slope(v, m, tbl)
                bnd = TM.band_of(v)
                worst[bnd] = min(worst.get(bnd, (9, "", 0)), (round(s, 3), m, v))
        print("   goal-metric worst per band: " + "; ".join(f"{b}: {w[0]} ({w[1]} @ {w[2]})" for b, w in worst.items()))
