"""Independent re-derivation of the core numbers (bypass s5_04/s5_07's saved rows; recompute from cache with a
fresh script) for T64 vs V282 at v>=15 m/s: ang_lag (xcorr of wheel angle behind model-implied angle) and hf
(2-10 Hz steer-rate RMS, v282cmp.steer_hf) on v282cmp.jerk_events(thr=0.5, vmin=3) windows [-1.5,+3.0]s,
matched to v>=15 only (no demand-rate matching -- a cruder check of whether the ratios are in the right
ballpark, not a replication of s5_07's matched-pair procedure).
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


def process(g, routes, vlo=15.0):
    out_lag, out_hf, n = [], [], 0
    for rk in routes:
        S = V.load(rk)
        D = np.load(V.CACHE / f'{rk}.npz'); stiff = np.interp(S['t'], D['t_lp'], D['stiff']); del D
        ev, _ = V.jerk_events(S, jerk_thr=0.5, vmin=3.0)
        roll = np.nan_to_num(S['roll']); sR = np.nan_to_num(S['sR'], nan=16.84); aoff = np.nan_to_num(S['aoff'])
        for e in ev:
            if e['v'] < vlo:
                continue
            i0, i1 = e['idx'] - 150, e['idx'] + 300
            if not np.isfinite(S['sa'][i0:i1]).all():
                continue
            model = np.nan_to_num(S['model'][i0:i1])
            ad = np.array([C.angle_from_la(model[k], float(S['v'][i0 + k]), roll[i0 + k], sR[i0 + k], stiff[i0 + k]) for k in range(i1 - i0)])
            th = S['sa'][i0:i1] - aoff[i0:i1]
            adf, thf = V.lowpass(ad, 5.0), V.lowpass(th, 5.0)
            lag, corr = lag_gain(adf, thf)
            if corr < 0.3:
                continue
            out_lag.append(lag)
            out_hf.append(V.steer_hf(S, i0, i1))
            n += 1
        del S
    return dict(n=n, ang_lag_med=float(np.median(out_lag)), hf_med=float(np.median(out_hf)),
                ang_lag_arr=out_lag, hf_arr=out_hf)


res = {}
for g in ('V282', 'T64'):
    res[g] = process(g, L.GROUPS[g])
    print(g, res[g]['n'], 'ang_lag', round(res[g]['ang_lag_med'], 3), 'hf', round(res[g]['hf_med'], 3))

print('ratio hf T64/V282:', round(res['T64']['hf_med'] / res['V282']['hf_med'], 2))
print('diff ang_lag T64-V282:', round(res['T64']['ang_lag_med'] - res['V282']['ang_lag_med'], 3))

# bootstrap CI (independent draws, not matched pairs -- cruder than s5_07's paired diff)
rng = np.random.default_rng(1)
t64, v282 = np.array(res['T64']['ang_lag_med'] and res['T64']['ang_lag_arr']), np.array(res['V282']['ang_lag_arr'])
bs = [np.median(rng.choice(t64, len(t64))) - np.median(rng.choice(v282, len(v282))) for _ in range(2000)]
print('ang_lag diff CI (unmatched bootstrap):', np.percentile(bs, 2.5), np.percentile(bs, 97.5))

hf_t, hf_v = np.array(res['T64']['hf_arr']), np.array(res['V282']['hf_arr'])
bs2 = [np.median(rng.choice(hf_t, len(hf_t))) / max(np.median(rng.choice(hf_v, len(hf_v))), 1e-9) for _ in range(2000)]
print('hf ratio CI (unmatched bootstrap):', np.percentile(bs2, 2.5), np.percentile(bs2, 97.5))

json.dump({k: {kk: vv for kk, vv in v.items() if kk not in ('ang_lag_arr', 'hf_arr')} for k, v in res.items()},
          open('v2_recompute_hf_lag.json', 'w'), indent=1)
