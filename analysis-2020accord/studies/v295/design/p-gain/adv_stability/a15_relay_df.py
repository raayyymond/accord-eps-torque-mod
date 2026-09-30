# -*- coding: utf-8 -*-
"""a15 -- (c) the fork's SteerFriction relay as a describing function.  get_friction is interp(e, [-0.30, 0.30],
[-f*LAF, +f*LAF]): a SATURATION of slope f*LAF/0.30 = 0.513 per unit e_lsf.  Its DF N(A) runs from 0.513 (A <= 0.30) down
to 0 (A -> inf), so the loop family is L(N) = (kp + ki-part + N)(1+lsf/kp) ... ; a relay-induced limit cycle needs
1 + L(N) = 0 for some N in [0, 0.513].  Sweep N and report min GM over N, V294 vs candidate, light_b at the drive's op
points (spring linearised at the hold angle)."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/plant")
import adv_lib as A, adv_lin as AL, adv_outer as AO
import v294_plant as VP
sfc = np.load(os.path.join(HERE, "a1_surface.npz"))
S294, Sc = sfc["S294"].astype(float), sfc["Sc"].astype(float)
KPC = A.table(A.CAND_X, A.CAND_Y)
R1 = dict(kp=0.9, ki=0.3, laf=14.0, fric=0.011)
F = np.concatenate([np.linspace(0.05, 1.0, 30), np.geomspace(1.0, 30.0, 500)[1:]])
fam = VP.family()
out = open(os.path.join(HERE, "a15_relay_df_out.txt"), "w")
def P(*a):
    s = " ".join(str(x) for x in a); print(s); out.write(s + "\n")
Ns = np.linspace(0.0, 0.513, 12)
for nm in ("light_b", "nominal", "b_lo"):
    for lab, v, th0, i294 in (("straight 22+", 26.9, 0.6, 5), ("curve 22+", 26.9, 11.0, 33), ("curve 15-19", 17.0, 18.4, 38),
                              ("straight 5-10", 8.0, 1.2, 5), ("straight 0-5", 3.1, 1.5, 5), ("low-speed turn", 3.1, 161.0, 80)):
        p = fam[nm].at(v)
        ic = AO.idx_for_torque(Sc, S294[i294])
        row = []
        for bn, S, kp, ii in (("V294", S294, 960.0, i294), ("cand", Sc, float(KPC[ic]), ic)):
            gms = [AL.margins(F, AO.outer_L(F, v, th0, p.J, p.b, p.k, AO.sat_prior(v), kp, AO.slope_at(S, ii), R1, relay_df=N, tau=p.tau_ms))["GM"] for N in Ns]
            j = int(np.argmin(gms))
            row.append("%s min GM %.2f at N %.2f (N=0: %.2f, N=0.513: %.2f)" % (bn, gms[j], Ns[j], gms[0], gms[-1]))
        P("  %-8s %-15s %s" % (nm, lab, " | ".join(row)))
out.close()
