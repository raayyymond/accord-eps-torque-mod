# -*- coding: utf-8 -*-
"""as9_alpha.py -- (e) the goal metric, closed form, MY transfer functions: alpha/cmd (deg/s^2 per 0xE4 count) with the
inner trim loop closed, 1-8 Hz; "complex-gain R^2" = the share of the response a single complex gain explains,
R^2 = |mean H|^2 / mean |H|^2 (best constant G = mean H in least squares), with uniform-linear and log-frequency weights.
Every member x speed, V293 (b 0) / V294 / A; plus the 1-3 Hz and 3-8 Hz sub-bands and |H| at 1/2/3/5/8 Hz."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord/studies/v295/plant"))
import advlib as A
import as4_outer_lib as OL
import v294_plant as VP

c294 = A.read_cells("V294")
cells = {"V293": dict(c294, b=0), "V294": c294, "A": dict(c294, b=1106)}
fam = VP.family()


def alpha_cmd(c, p, f):
    f = np.asarray(f, float)
    s = 2j * np.pi * f
    zoh1k = np.exp(-1j * np.pi * f * 1e-3) * np.sinc(f * 1e-3)
    zoh100 = np.exp(-1j * np.pi * f * 0.01) * np.sinc(f * 0.01)
    Lin = A.inner_L(c, p, f)
    return s ** 2 * A.plant_theta_per_u(p, f) * zoh1k / (1 + Lin) * OL.ff_lane(c, f) * zoh100


def r2(H, w):
    w = w / w.sum()
    G = np.sum(w * H)
    return float(abs(G) ** 2 / np.sum(w * np.abs(H) ** 2))


fl = np.linspace(1, 8, 701)
fg = np.logspace(0, np.log10(8), 701)
print("R^2 of a single complex gain, 1-8 Hz [linear weights | log weights]; then 1-3 / 3-8 Hz (linear): V293 / V294 / A")
worst = []
for name in ("nominal", "J_lo", "J_hi", "J_hi2", "b_lo", "b_hi", "F_hi", "ms_free", "light_b"):
    for v in (3.1, 8.0, 12.0, 17.0, 26.9):
        a = fam[name].arrays_at(np.array([v]))
        p = dict(J=float(a["J"][0]), b=float(a["b"][0]), k=float(a["k"][0]), tau_ms=fam[name].tau_ms, w=3)
        out = {}
        for k, c in cells.items():
            Hl = alpha_cmd(c, p, fl); Hg = alpha_cmd(c, p, fg)
            m13 = fl <= 3; m38 = fl >= 3
            out[k] = (r2(Hl, np.ones_like(fl)), r2(Hg, 1 / fg), r2(Hl[m13], np.ones(m13.sum())), r2(Hl[m38], np.ones(m38.sum())),
                      np.abs(alpha_cmd(c, p, np.array([1, 2, 3, 5, 8.0]))))
        worst.append((name, v, out["A"][0] - out["V294"][0], out["A"][1] - out["V294"][1], out["A"][2] - out["V294"][2], out["A"][3] - out["V294"][3]))
        print("  %-8s %4.1f | lin %.3f/%.3f/%.3f | log %.3f/%.3f/%.3f | 1-3 %.3f/%.3f/%.3f | 3-8 %.3f/%.3f/%.3f | |H| V294 %s A %s" % (
            name, v, out["V293"][0], out["V294"][0], out["A"][0], out["V293"][1], out["V294"][1], out["A"][1],
            out["V293"][2], out["V294"][2], out["A"][2], out["V293"][3], out["V294"][3], out["A"][3],
            np.round(out["V294"][4], 2), np.round(out["A"][4], 2)))
print("\nA - V294 change in R^2: 1-8 Hz linear min %+.3f max %+.3f ; log min %+.3f max %+.3f ; 1-3 Hz min %+.3f max %+.3f ; 3-8 Hz min %+.3f max %+.3f" % (
    min(w[2] for w in worst), max(w[2] for w in worst), min(w[3] for w in worst), max(w[3] for w in worst),
    min(w[4] for w in worst), max(w[4] for w in worst), min(w[5] for w in worst), max(w[5] for w in worst)))
print("cases where A lowers the 1-8 Hz R^2 (linear) by > 0.005:", [(w[0], w[1], round(w[2], 3)) for w in worst if w[2] < -0.005])
print("cases where A lowers the 1-3 Hz R^2 by > 0.005:", [(w[0], w[1], round(w[4], 3)) for w in worst if w[4] < -0.005])
