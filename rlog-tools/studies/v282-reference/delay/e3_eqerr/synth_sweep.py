"""Estimator-configuration sweep on the positive control (simulate once per plant case, try configs)."""
import sys, json, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eqlib as E
from synth import simulate, CACHE
route = sys.argv[1]
Z = np.load(f"{CACHE}/{route}.npz")
t_u = Z["t_e4"]; u = -Z["e4_cmd"] / 4089.0
t_cs = Z["t_cst"]; v = Z["vego"]; press = Z["spress"] > 0.5
act = (np.interp(t_cs, Z["t_cs"], Z["cs_active"]) > 0.5) & (np.interp(t_cs, Z["t_cc"], Z["lat_active"]) > 0.5)
mask = act & ~press
rr = E.runs(mask, t_cs); t0 = t_cs[rr[0][0]] - 5.0; t1 = t_cs[rr[-1][1] - 1] + 1.0
configs = {
 "bp0.3-6_g0": dict(band=(0.3, 6.0), guard=0, demean_block=False),
 "bp0.5-8_g0": dict(band=(0.5, 8.0), guard=0, demean_block=False),
 "lp6_g5_dm": dict(band=(None, 6.0), guard=5, demean_block=True),
 "lp8_g5_dm": dict(band=(None, 8.0), guard=5, demean_block=True),
 "lp10_g5_dm": dict(band=(None, 10.0), guard=5, demean_block=True),
 "lp8_g10_dm_r3": dict(band=(None, 8.0), guard=10, demean_block=True, rmin=3.0),
}
out = {}
for D in (0.030, 0.060):
    for (J, b, F) in ((8e-5, 0.003, 0.02), (1e-3, 0.003, 0.02), (3e-4, 0.003, 0.02)):
        for kfb in (0.0, 1e-3):
            a, r, us = simulate(t_u, u, t_cs, v, D, J, b, F, kfb=kfb, t0=t0, t1=t1)
            m = mask & np.isfinite(a); a = np.nan_to_num(a); r = np.nan_to_num(r)
            key = f"D{int(D*1e3)} J{J:g} kfb{kfb:g}"
            line = key
            for cn, cfg in configs.items():
                bl, _ = E.accumulate(t_cs, a, r, v, m, t_u, us, variant="rate", **cfg)
                ds = []
                for bi in range(3):
                    b_ = [x for x in bl if x["bin"] == bi]
                    ds.append(E.argmin_sub(E.solve(b_)[0])[0] if len(b_) > 2 else np.nan)
                ds.append(E.argmin_sub(E.solve(bl)[0])[0])
                out.setdefault(cn, {})[key] = ds
                line += f" | {cn} " + "/".join(f"{d:.0f}" for d in ds)
            print(line, flush=True)
json.dump(out, open(f"synth_sweep_{route}.json", "w"), indent=1)
