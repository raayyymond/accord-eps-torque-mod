"""D_act on real data: equation-error delay sweep, per route x speed bin, hands-off lateral-engaged frames.
Also: (i) the 0x14A rate channel's lag against d(angle)/dt (sensor-internal filtering), (ii) parameter stability.
usage: python real.py <route>  -> real_<route>.json, blocks_<route>.npz
"""
import sys, os, json
import numpy as np
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eqlib as E
CACHE = "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v282ref"
CFGS = {
    "rate_lp4": dict(variant="rate", band=(None, 4.0), guard=5, demean_block=True),   # PRIMARY (pre-chosen by control)
    "rate_lp6": dict(variant="rate", band=(None, 6.0), guard=5, demean_block=True),
    "hybA_lp4": dict(variant="hyb_rateA", band=(None, 4.0), guard=5, demean_block=True),
    "rate_lp4_relaxed": dict(variant="rate", band=(None, 4.0), guard=2, demean_block=True, rmin=1.0),
}
route = sys.argv[1]
Z = np.load(f"{CACHE}/{route}.npz")
t_u = Z["t_e4"]; u = -Z["e4_cmd"] / 4089.0
t_cs = Z["t_cst"]; v = Z["vego"]; press = Z["spress"] > 0.5
ang = Z["sa_deg"]; rate = Z["sr_deg"]
act = (np.interp(t_cs, Z["t_cs"], Z["cs_active"]) > 0.5) & (np.interp(t_cs, Z["t_cc"], Z["lat_active"]) > 0.5)
req = np.interp(t_cs, Z["t_e4"], Z["e4_req"]) > 0.5
mask = act & ~press & req
del Z
out = dict(route=route, engaged_handsoff_s=float(mask.sum() / 100.0))
rng = np.random.default_rng(7)
blocksave = {}
for cn, cfg in CFGS.items():
    bl, series = E.accumulate(t_cs, ang, rate, v, mask, t_u, u, keep_series=(cn == "rate_lp4"), **cfg)
    res = {}
    for bi in range(3):
        b_ = [x for x in bl if x["bin"] == bi]
        if len(b_) < 5:
            res[bi] = None; continue
        ssr, th, n = E.solve(b_)
        d, k = E.argmin_sub(ssr)
        r = dict(D=d, n=n, nblocks=len(b_), depth=float((ssr.max() - ssr.min()) / ssr.min()),
                 ssr_rel=(ssr / ssr.min()).round(5).tolist(),
                 th_opt=dict(zip(E.NAMES, th[k].tolist())),
                 th_m10=dict(zip(E.NAMES, th[max(k - 10, 0)].tolist())), th_p10=dict(zip(E.NAMES, th[min(k + 10, 120)].tolist())),
                 D_min_grid=int(E.DGRID[k]),
                 local_minima=[int(E.DGRID[i]) for i in range(1, 120) if ssr[i] < ssr[i - 1] and ssr[i] < ssr[i + 1]])
        boots = E.bootstrap([[x] for x in b_], nboot=400, seed=bi)
        r["block_boot_ci"] = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]
        r["block_boot_sd"] = float(np.std(boots))
        if cn == "rate_lp4":
            nf = E.neff_frac(series, th[k], k, bi)
            lo, hi, neff = E.curvature_ci(ssr, nf, n)
            r["neff_frac"] = nf; r["curv_ci"] = [lo, hi]
        res[bi] = r
        blocksave[f"{cn}_{bi}_XX"] = np.array([x["XX"] for x in b_]); blocksave[f"{cn}_{bi}_Xy"] = np.array([x["Xy"] for x in b_])
        blocksave[f"{cn}_{bi}_yy"] = np.array([x["yy"] for x in b_]); blocksave[f"{cn}_{bi}_n"] = np.array([x["n"] for x in b_])
    out[cn] = res
    print(cn, {bi: (None if res[bi] is None else (round(res[bi]["D"], 1), [round(c, 1) for c in res[bi]["block_boot_ci"]],
                                                   res[bi].get("curv_ci"), res[bi]["n"],
                                                   {kk: float(f"{vv:.3g}") for kk, vv in res[bi]["th_opt"].items()}))
               for bi in res}, flush=True)
    del bl, series
# (i) logged rate vs d(angle)/dt: sub-ms lag by the same fine-grid method (angle derivative is the reference)
sos = signal.butter(2, 4.0, fs=100.0, output="sos")
lagres = {}
for bi, (vlo, vhi) in enumerate(E.BINS):
    num = np.zeros(61); den1 = 0.0; den2 = np.zeros(61)
    for a, b in E.runs(mask & (v >= vlo) & (v < vhi), t_cs):
        ra = signal.sosfiltfilt(sos, np.gradient(ang[a:b]) * 100.0); rl = signal.sosfiltfilt(sos, rate[a:b])
        fine = np.arange(len(ra) * 10) / 10.0
        rli = np.interp(fine, np.arange(len(rl)), rl)
        for j, L in enumerate(range(-30, 31)):          # shift of logged rate in ms (+ = rate lags angle-derivative)
            idx = np.arange(40, len(ra) - 40) * 10 + L
            num[j] += float(np.dot(ra[40:len(ra) - 40], rli[idx])); den2[j] += float(np.dot(rli[idx], rli[idx]))
        den1 += float(np.dot(ra[40:len(ra) - 40], ra[40:len(ra) - 40]))
    if den1 > 0:
        c = num / np.sqrt(den1 * den2 + 1e-30)
        j = int(np.argmax(c)); lagres[bi] = dict(lag_ms=int(j - 30), corr=float(c[j]))
out["rate_vs_dangle_lag"] = lagres
print("rate lag vs d(angle)/dt:", lagres)
json.dump(out, open(f"real_{route}.json", "w"), indent=1)
np.savez_compressed(f"blocks_{route}.npz", **blocksave)
