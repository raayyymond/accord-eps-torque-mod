# -*- coding: utf-8 -*-
"""a13 -- (e) the goal metric's direction, my own closed form: |alpha / 0xE4 count| = |(2 pi f)^2 Ptheta FF / (1 + L_in)|
at the operating point (idx0 -> FF local slope and Kp(idx0) for the trim), candidate / V294, every member, speeds,
idx 4 / 30 / 60 / 90, at 0.5 / 1 / 2 / 3 / 5 Hz; plus the phase change.  (Linear, sliding: friction's amplitude
dependence -- the 'flatness' -- is not in a linear number; the ratio at small idx IS the small-signal gain change.)"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/plant")
import adv_lib as A  # noqa: E402
import adv_lin as AL  # noqa: E402
import adv_outer as AO  # noqa: E402
import v294_plant as VP  # noqa: E402

sfc = np.load(os.path.join(HERE, "a1_surface.npz"))
S294, Sc = sfc["S294"].astype(float), sfc["Sc"].astype(float)
KPC = A.table(A.CAND_X, A.CAND_Y)
fam = VP.family()
f = np.array([0.5, 1.0, 2.0, 3.0, 5.0])
out = open(os.path.join(HERE, "a13_alpha_cmd_out.txt"), "w")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.write(s + "\n")


def acmd(J, b, k, kp, slope, tau):
    Ac, Bc, cs, _ = AL.plant_cont(J, b, k)
    s = 2j * np.pi * f
    Pth = AL.plant_frf(Ac, Bc, cs, f) * np.exp(-s * tau * AL.DT)
    Lin = AL.inner_L(dict(AO.LANE_BASE, kp=kp), Ac, Bc, cs, f, tau=tau)
    zi = np.exp(-s * AL.DT)
    Hl = (507 / 1024.0) * (1 + zi) / (32.0 * (1 - (992 / 1024.0) * zi))
    Hl0 = (507 / 1024.0) * 2 / (32.0 * (1 - 992 / 1024.0))
    return s ** 2 * Pth * slope * Hl / Hl0 / (1 + Lin)


P("ratio |alpha/cmd| cand / V294 (and phase change deg) at f = %s Hz" % f)
allr = []
for nm in ("nominal", "J_lo", "J_hi", "J_hi2", "b_lo", "b_hi", "ms_free", "light_b"):
    for v in (3.1, 8.0, 17.0, 26.9):
        p = fam[nm].at(v)
        row = []
        for i0 in (4, 30, 60, 90):
            a = acmd(p.J, p.b, p.k, 960.0, AO.slope_at(S294, i0), p.tau_ms)
            c = acmd(p.J, p.b, p.k, float(KPC[i0]), AO.slope_at(Sc, i0), p.tau_ms)
            r = np.abs(c) / np.abs(a)
            ph = np.degrees(np.angle(c / a))
            allr.append((nm, v, i0, r, ph))
            row.append("idx %2d: %s (%s deg)" % (i0, " ".join("%.2f" % x for x in r), " ".join("%+.0f" % x for x in ph)))
        P("  %-8s v %4.1f | %s" % (nm, v, " | ".join(row)))
for i0 in (4, 30, 60, 90):
    rs = np.array([a[3] for a in allr if a[2] == i0])
    ps = np.array([a[4] for a in allr if a[2] == i0])
    P("idx %2d over all members/speeds: ratio min %.3f max %.3f ; phase change %+.1f..%+.1f deg" % (i0, rs.min(), rs.max(), ps.min(), ps.max()))
out.close()
