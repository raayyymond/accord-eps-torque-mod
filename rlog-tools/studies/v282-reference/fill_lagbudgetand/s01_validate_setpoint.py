"""Step 1/4 check: does the code-exact replay of the model->setpoint chain reproduce the LOGGED setpoint (cs_la_des) per route?
Variants: flown config (census) vs swapped configs, so a wrong config is detectable (negative control)."""
import sys, json, gc
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V
from lagmod import simulate_setpoint, ROUTE_CFG, COMMITS
res = {}
for rk, cfg in ROUTE_CFG.items():
    D = np.load(V.CACHE / f"{rk}.npz")
    t = D["t_cs"]; curv = D["cs_des_curv"]; sp_log = D["cs_la_des"]
    v = np.interp(t, D["t_cst"], D["vego"])
    act = (D["cs_active"] > 0.5)
    ld = np.interp(t, D["t_ld"], D["ld_delay"]) if len(D["t_ld"]) else np.full(len(t), 0.2)
    del D
    # skip first 3 s after each engage and never compare across clock gaps
    gap = np.r_[False, np.diff(t) > 0.04]
    ok = act.copy(); last = -10**9
    for k in range(len(t)):
        if not act[k] or gap[k]: last = k
        if k - last < 300: ok[k] = False
    ok &= v > 2.0
    out = {}
    variants = {"flown": (COMMITS[cfg["commit"]]["jerk_fc"], cfg["ref_rc"], ld),
                "V282-chain(1.2Hz,no ref)": (1.2, 0.0, ld),
                "T64-chain(4Hz,ref.06)": (4.0, 0.06, ld),
                "T5-chain(1.2Hz,ref.12)": (1.2, 0.12, ld),
                "flown,ld=0.20": (COMMITS[cfg["commit"]]["jerk_fc"], cfg["ref_rc"], np.full(len(t), 0.2)),
                "flown,ld=0.30": (COMMITS[cfg["commit"]]["jerk_fc"], cfg["ref_rc"], np.full(len(t), 0.3))}
    for nm, (fc, rc, ldv) in variants.items():
        sim = simulate_setpoint(curv, v, act, ldv, fc, rc)
        e = sim[ok] - sp_log[ok]
        out[nm] = dict(rms_err=float(np.sqrt(np.mean(e ** 2))), rms_sig=float(np.sqrt(np.mean(sp_log[ok] ** 2))),
                       corr=float(np.corrcoef(sim[ok], sp_log[ok])[0, 1]), p99_abs_err=float(np.percentile(np.abs(e), 99)))
    res[rk] = dict(group=V.ROUTES[rk]["group"], cfg=cfg, n=int(ok.sum()), variants=out)
    print(rk, V.ROUTES[rk]["group"], cfg, "n", ok.sum())
    for nm, d in out.items():
        print(f"   {nm:28s} rel_rms_err {d['rms_err']/d['rms_sig']:.5f}  corr {d['corr']:.6f}  p99|e| {d['p99_abs_err']:.5f}")
    del curv, sp_log, v, act, ld; gc.collect()
json.dump(res, open("s01_validate_setpoint.json", "w"), indent=1)
