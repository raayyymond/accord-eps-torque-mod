"""MANDATORY POSITIVE CONTROL over all five torque routes' logged commands and masks.
Plant cases: D in {30, 60} ms x J in {8e-5, 3e-4, 1e-3} x rate feedback kfb in {0, 1e-3} (b 0.003, F 0.02, k = fork
hold map), plus two first-order actuator-lag cases (D 30 + tau 20 ms) to show what a lag reads as.
Estimator configs: the candidates that survived synth_var/synth_var2 on route 76.
usage: python control_all.py <route>   -> control_<route>.json
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eqlib as E, synth
route = sys.argv[1]
Z = np.load(f"{synth.CACHE}/{route}.npz")
t_u = Z["t_e4"]; u = -Z["e4_cmd"] / 4089.0
t_cs = Z["t_cst"]; v = Z["vego"]; press = Z["spress"] > 0.5
act = (np.interp(t_cs, Z["t_cs"], Z["cs_active"]) > 0.5) & (np.interp(t_cs, Z["t_cc"], Z["lat_active"]) > 0.5)
mask = act & ~press
del Z
rr = E.runs(mask, t_cs); t0 = t_cs[rr[0][0]] - 5.0; t1 = t_cs[rr[-1][1] - 1] + 1.0
CFGS = {
    "rate_lp4": dict(variant="rate", band=(None, 4.0), guard=5, demean_block=True),
    "rate_lp6": dict(variant="rate", band=(None, 6.0), guard=5, demean_block=True),
    "hybA_lp4": dict(variant="hyb_rateA", band=(None, 4.0), guard=5, demean_block=True),
}
cases = [(D, J, kfb, 0.0) for D in (0.030, 0.060) for J in (8e-5, 3e-4, 1e-3) for kfb in (0.0, 1e-3)]
cases += [(0.030, 8e-5, 0.0, 0.020), (0.030, 3e-4, 0.0, 0.020)]
out = dict(route=route, cases={})
for D, J, kfb, tau in cases:
    a, r, us = synth.simulate(t_u, u, t_cs, v, D, J, 0.003, 0.02, kfb=kfb, t0=t0, t1=t1, tau=tau)
    m = mask & np.isfinite(a); a = np.nan_to_num(a); r = np.nan_to_num(r)
    key = f"D{D*1e3:.0f}_J{J:g}_kfb{kfb:g}_tau{tau*1e3:.0f}"
    res = {}
    for cn, cfg in CFGS.items():
        bl, _ = E.accumulate(t_cs, a, r, v, m, t_u, us, **cfg)
        row = {}
        for bi in range(3):
            b_ = [x for x in bl if x["bin"] == bi]
            if len(b_) < 3:
                row[bi] = None; continue
            ssr, th, n = E.solve(b_); d, k = E.argmin_sub(ssr)
            row[bi] = dict(D=d, n=n, J=th[k][0], b=th[k][1], ks=th[k][2], F=th[k][3])
        res[cn] = row
    out["cases"][key] = res
    print(key, {cn: [None if row[bi] is None else round(row[bi]["D"], 1) for bi in range(3)] for cn, row in res.items()}, flush=True)
json.dump(out, open(f"control_{route}.json", "w"), indent=1)
