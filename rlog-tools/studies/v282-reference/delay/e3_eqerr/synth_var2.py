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
rr = E.runs(mask, t_cs); t0 = t_cs[rr[0][0]] - 5.0; t1 = t_cs[rr[-1][1] - 1] + 1.0
cfgs = {}
for var in ("rate", "hyb_rateA"):
    for lp in (4.0, 6.0):
        for ss, rmin in (("rate", 2.0), ("angleLP", 1.0), ("angleLP", 2.0), ("angleLP", 0.5)):
            cfgs[f"{var}_lp{lp:g}_s{ss}_r{rmin:g}"] = dict(variant=var, band=(None, lp), guard=5, demean_block=True, sgn_src=ss, rmin=rmin)
out = {}; ns = {}
for D in (0.030, 0.060):
    for J in (8e-5, 1e-3):
        a, r, us = synth.simulate(t_u, u, t_cs, v, D, J, 0.003, 0.02, t0=t0, t1=t1)
        m = mask & np.isfinite(a); a = np.nan_to_num(a); r = np.nan_to_num(r)
        key = f"D{D*1e3:.0f}_J{J:g}"
        for cn, cfg in cfgs.items():
            bl, _ = E.accumulate(t_cs, a, r, v, m, t_u, us, **cfg)
            ds = [E.argmin_sub(E.solve([x for x in bl if x["bin"] == bi])[0])[0] for bi in range(3)]
            ns[cn] = [sum(x["n"] for x in bl if x["bin"] == bi) for bi in range(3)]
            out.setdefault(cn, {})[key] = ds
        print(key, flush=True)
for cn, d in out.items():
    err = np.array([[ds[i] - float(k.split('_')[0][1:]) for i in range(3)] for k, ds in d.items()])
    print(f"{cn:30s} max|err| {np.round(np.max(np.abs(err), 0), 1)} mean {np.round(err.mean(0), 1)} n {ns[cn]}")
