"""Independent check of the finding's unsupported sub-claim: "Setpoint lag behind the model (event medians):
V282 0.05-0.07 s, T64 0.14, T5/T4 0.28." No script/JSON in s5_mechanism computes this (grepped). Recompute
from scratch: lag of the fork's shaped setpoint (angle_from_la(S['setpoint'])) behind the model demand
(angle_from_la(S['model'])), on the SAME jerk_events windows s5_04 uses, per group, split v<15 / v>=15.
"""
import json
import numpy as np
import sys
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism')
import s5lib as L
import s5ctl as C

V = L.V


def lag_gain(x, y, maxlag=80):
    n = len(x); best, lag = -np.inf, 0
    for k in range(0, maxlag + 1):
        xa, ya = x[:n - k] - x[:n - k].mean(), y[k:] - y[k:].mean()
        c = float(np.dot(xa, ya)) / max(np.linalg.norm(xa) * np.linalg.norm(ya), 1e-9)
        if c > best:
            best, lag = c, k
    return lag / 100.0, best


rows = []
for g, routes in L.GROUPS.items():
    for rk in routes:
        S = V.load(rk)
        D = np.load(V.CACHE / f'{rk}.npz'); stiff = np.interp(S['t'], D['t_lp'], D['stiff']); del D
        ev, _ = V.jerk_events(S, jerk_thr=0.5, vmin=3.0)
        roll = np.nan_to_num(S['roll']); sR = np.nan_to_num(S['sR'], nan=16.84)
        for e in ev:
            i0, i1 = e['idx'] - 150, e['idx'] + 300
            if not np.isfinite(S['sa'][i0:i1]).all() or not np.isfinite(S['setpoint'][i0:i1]).all():
                continue
            model = np.nan_to_num(S['model'][i0:i1])
            sp = np.nan_to_num(S['setpoint'][i0:i1])
            ad = np.array([C.angle_from_la(model[k], float(S['v'][i0 + k]), roll[i0 + k], sR[i0 + k], stiff[i0 + k]) for k in range(i1 - i0)])
            asp = np.array([C.angle_from_la(sp[k], float(S['v'][i0 + k]), roll[i0 + k], sR[i0 + k], stiff[i0 + k]) for k in range(i1 - i0)])
            adf, aspf = V.lowpass(ad, 5.0), V.lowpass(asp, 5.0)
            lag, corr = lag_gain(adf, aspf, maxlag=60)
            rows.append(dict(g=g, rk=rk, v=e['v'], sp_lag=lag, sp_corr=corr))
        print(g, rk, len(ev), flush=True)
        del S

out = {}
for g in L.GROUPS:
    for lo, hi, lab in [(0, 99, 'all'), (0, 15, '<15'), (15, 99, '>=15')]:
        sel = [r for r in rows if r['g'] == g and lo <= r['v'] < hi and r['sp_corr'] > 0.5]
        if len(sel) < 3:
            continue
        x = np.array([r['sp_lag'] for r in sel])
        out[f'{g}|{lab}'] = dict(n=len(sel), median=float(np.median(x)), mean=float(np.mean(x)),
                                   p25=float(np.percentile(x, 25)), p75=float(np.percentile(x, 75)))
        print(g, lab, out[f'{g}|{lab}'])

json.dump(dict(rows=rows, agg=out), open('v1_setpoint_lag.json', 'w'), indent=1)
