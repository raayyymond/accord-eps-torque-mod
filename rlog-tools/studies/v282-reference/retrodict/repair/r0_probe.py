# -*- coding: utf-8 -*-
"""r0 -- data probe: signs, rates, engagement, and the r71 limit cycle.

One route at a time (RAM ~2.5 GB).
"""
import sys
from pathlib import Path
import numpy as np

CACHE = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v282ref")
DT = 0.01


def grid(rt):
    D = np.load(CACHE / f"{rt}.npz", allow_pickle=True)
    t0 = max(D["t_cs"][0], D["t_cst"][0], D["t_cc"][0])
    t1 = min(D["t_cs"][-1], D["t_cst"][-1], D["t_cc"][-1])
    t = np.arange(t0, t1, DT)
    g = {}
    for src, names in (("t_cs", ["cs_err", "cs_p", "cs_i", "cs_f", "cs_out", "cs_sat", "cs_la_act",
                                 "cs_la_des", "cs_active", "cs_curv", "cs_des_curv"]),
                       ("t_cst", ["vego", "sa_deg", "sr_deg", "spress", "storque"]),
                       ("t_cc", ["lat_active", "cc_torque"]),
                       ("t_lp", ["sR", "stiff", "roll"])):
        for n in names:
            if n in D.files:
                g[n] = np.interp(t, D[src], D[n])
    g["t"] = t
    D.close()
    return g


if __name__ == "__main__":
    rt = sys.argv[1] if len(sys.argv) > 1 else "00000071--f2c9d073a3"
    g = grid(rt)
    eng = (g["lat_active"] > 0.5) & (g["spress"] < 0.5)
    print(rt, "n=", len(g["t"]), "engaged hands-off frac", eng.mean())
    for lo, hi in ((15, 22), (22, 99), (0, 99)):
        m = eng & (g["vego"] >= lo) & (g["vego"] < hi)
        print(f"  v {lo}-{hi}: {m.sum()*DT:8.1f} s   med v {np.median(g['vego'][m]) if m.sum() else 0:5.1f}")
    m = eng & (g["vego"] >= 15)
    if m.sum() > 1000:
        # sign checks
        A = np.polyfit(g["sa_deg"][m], g["cs_la_act"][m], 1)
        r = np.corrcoef(g["sa_deg"][m], g["cs_la_act"][m])[0, 1]
        print(f"  cs_la_act = {A[0]:+.5f} * sa_deg {A[1]:+.4f}   r={r:.4f}  (c = measurement per deg)")
        A2 = np.polyfit(g["sa_deg"][m], g["cs_curv"][m], 1)
        print(f"  cs_curv   = {A2[0]:+.6f} * sa_deg  r={np.corrcoef(g['sa_deg'][m], g['cs_curv'][m])[0,1]:.4f}")
        # error identity: cs_err vs (la_des - la_act)
        e0 = g["cs_la_des"] - g["cs_la_act"]
        print(f"  corr(cs_err, la_des-la_act) = {np.corrcoef(g['cs_err'][m], e0[m])[0,1]:.4f}"
              f"   slope {np.polyfit(e0[m], g['cs_err'][m], 1)[0]:.4f}")
        print(f"  cs_p / cs_err  median = {np.median(g['cs_p'][m] / np.where(np.abs(g['cs_err'][m])>1e-3, g['cs_err'][m], np.nan)):.4f}")
        print(f"  rms cs_out {np.std(g['cs_out'][m]):.4f}  rms sa {np.std(g['sa_deg'][m]):.2f} deg"
              f"  rms err {np.std(g['cs_err'][m]):.4f}")
