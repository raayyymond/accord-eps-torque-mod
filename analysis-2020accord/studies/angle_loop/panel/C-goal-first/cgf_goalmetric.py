# -*- coding: utf-8 -*-
r"""cgf_goalmetric.py -- score the Designer-C schedule on THE GOAL'S OWN tracking metric (the kit scorer's
tracking_gain: OLS slope of actualLateralAccel on desiredLateralAccel, both 0.5 Hz zero-phase filtered), via the
weighting c1r2_trackmetric built from r71b's measured desired-lat-accel spectrum (with its +-0.028 positive control).
ANALYSIS ONLY.  The reported number is the INNER-loop factor: what the metric reads if the fork's VSR map / look-ahead /
vehicle factor were perfect (the fork supplies the DC, so we normalise T_ref by T_ref(0))."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
for _p in (str(HERE), str(AL), str(AL / "c1"), str(AL.parent / "v295" / "plant")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cgf_freq as G          # noqa: E402
import cgf_design as D        # noqa: E402
import c1r2_trackmetric as TM  # noqa: E402

SPEEDS = [8.0, 10.0, 11.9, 12.5, 15.0, 17.0, 19.0, 22.0, 26.9, 30.0]
MEMBERS = ["nominal", "b_hi", "b_lo", "J_hi", "J1.0", "b_q", "b_q*J_hi", "b_q*J1.0", "b_lo*J_hi"]


def ctl(v, ff=False):
    return G.CtlC(kp=D.kp_eff(v), ki=D.KI_BASE / 256.0 * D.G_at(v), kd=D.KD_EFF, op_hold="hold", d_hold="fresh_abe",
                  ff_gain=(1.0 if ff else 0.0))


def inner_factor(member, v, ff=False):
    c = ctl(v, ff)
    p, ea = G.member_plant(member, v)
    cc = G.replace(c, d=p.tau, extra_age=ea)
    P = G.plant_frf(p)

    def Tref_norm(f):
        Pf = p.frf(np.asarray(f, float))
        L = G.C_fb(np.asarray(f, float), cc) * Pf
        Tr = G.C_ref(np.asarray(f, float), cc) * Pf / (1 + L)
        T0 = (G.C_ref(np.array([1e-3]), cc) * p.frf(np.array([1e-3])) /
              (1 + G.C_fb(np.array([1e-3]), cc) * p.frf(np.array([1e-3]))))[0]
        return Tr / T0
    return TM.slope(Tref_norm, v)


if __name__ == "__main__":
    print("INNER-LOOP FACTOR on the goal's tracking metric (1.0 = perfect inner loop; fork supplies DC)")
    print(f"{'v':>6} " + " ".join(f"{m[:8]:>8}" for m in MEMBERS) + "   PASS(>=0.95 all)?")
    worst_overall = 1.0
    for v in SPEEDS:
        vals = [inner_factor(m, v) for m in MEMBERS]
        worst = min(vals)
        worst_overall = min(worst_overall, worst)
        print(f"{v:6.1f} " + " ".join(f"{x:8.3f}" for x in vals) + f"   {'PASS' if worst >= 0.95 else 'FAIL'} ({worst:.3f})")
    print(f"\nworst inner-loop factor over all tabulated members, bands >=8 m/s: {worst_overall:.3f}")
    print("(positive-control accuracy of the weighting +-0.028; r71b spectrum, one route -- BELIEF it is typical)")
