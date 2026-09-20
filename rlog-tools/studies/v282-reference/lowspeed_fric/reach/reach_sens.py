"""reach sensitivity: (1) the readout index -- the measured shortfall was fitted 30 ms before breakaway,
but the resolved loop delay is 55-75 ms, so re-read everything at bk-3 / bk-6 / bk-8; (2) per-route spread
of the reach for the finalists (is any number carried by one route?)."""
import os, sys, json
import numpy as np

BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference'
sys.path.insert(0, BASE + '/lowspeed/a_stickslip'); sys.path.insert(0, BASE)
from sslib import V, T, params, band, hyst_run, hold_torque, k_of_v  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__)) + '/out'
SS = BASE + '/lowspeed/a_stickslip/out'
F_TODAY = 0.015
TQ = ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd',
      '00000076--d0b7ea7e4d', '00000075--6c8687d5bd']
LAGS = [3, 6, 8]
# (ceiling, band-rule, gate) : band-rule None = flat band value, float M = band = f/(M*k(v))
VAR = [('today 0.015/3.0', 0.015, None, 3.0), ('C1 f0.027 M1.8', 0.027, 1.8, None),
       ('C2 f0.027 M2.4', 0.027, 2.4, None), ('sym 0.033/2.0', 0.033, None, 2.0)]
rows = []
for rk in TQ:
    S_ = V.load(rk); p, fs = params(rk)
    v = np.nan_to_num(S_['v']); vv = np.maximum(v, 1.0); act = S_['active']
    sR = np.nan_to_num(S_['sR'], nan=16.33)
    angdes = -np.degrees(np.nan_to_num(S_['setpoint']) / vv ** 2 * sR * T.WB * (1 - T.SF * v ** 2))
    d_ang = np.r_[0.0, np.diff(angdes)]; d_ang[~act] = 0.0; d_ang[np.r_[True, ~act[:-1]]] = 0.0
    cmd = np.nan_to_num(S_['out']); aa_ = np.nan_to_num(S_['sa']) - np.nan_to_num(S_['aoff'])
    sched = p.get('AccordFrictionHystBand', '0') == '1'
    b_today = band(v, sched); kv = k_of_v(v)
    zt = hyst_run(d_ang, F_TODAY, b_today, act)
    g = np.clip((v - 8.0) / 4.0, 0.0, 1.0)
    Z = []
    for (nm, f, M, bflat) in VAR:
        b_c = (f / np.maximum(M * kv, 1e-6)) if M else np.full(len(v), bflat)
        fe = f + g * (F_TODAY - f); be = b_c + g * (b_today - b_c)
        z = np.zeros(len(v)); zz = 0.0
        for n in range(len(v)):
            zz = 0.0 if not act[n] else min(max(zz + d_ang[n] * fe[n] / max(be[n], 1e-3), -fe[n]), fe[n])
            z[n] = zz
        Z.append(z)
    Z = np.stack(Z, 1)
    for e in np.load(f'{SS}/{rk}_ss.npz', allow_pickle=True)['EP']:
        i0 = int(e['i0']); bk = int(e['bk']); sj = float(e['sjump'])
        r = dict(route=rk, v=float(e['v']), aa=float(e['aa']), sj=sj)
        for lg in LAGS:
            b = max(bk - lg, i0)
            r[f'cmd{lg}'] = float(cmd[b]); r[f'hold{lg}'] = float(hold_torque(aa_[b], v[b], False))
            r[f'aa{lg}'] = float(aa_[b])
            r[f'z0_{lg}'] = (Z[i0] * sj).astype(np.float32)
            r[f'zb_{lg}'] = (Z[b] * sj).astype(np.float32)
        rows.append(r)
    del S_, Z
    print('done', rk, flush=True)

cf = lambda k: np.array([r[k] for r in rows]); mf = lambda k: np.stack([r[k] for r in rows])
v = cf('v'); route = cf('route'); aa = cf('aa'); sj = cf('sj'); tw = (sj == -np.sign(aa))
N = len(rows); m = (v >= 2) & (v < 8)
res = {'readout_lag': {}, 'per_route': {}}
for lg in LAGS:
    y = cf(f'cmd{lg}') - cf(f'hold{lg}')
    X = np.vstack([sj, sj * tw.astype(float), np.ones(N)]).T
    c = np.linalg.lstsq(X[m], y[m], rcond=None)[0]
    Xi = np.vstack([sj, np.sign(cf(f'aa{lg}')), np.ones(N)]).T
    ci = np.linalg.lstsq(Xi[m], y[m], rcond=None)[0]
    d = dict(away=float(c[0]), toward=float(c[0] + c[1]), halfwidth=float(c[0] + c[1] / 2),
             centring_offset=float(-c[1] / 2), intercept_fit_Fa=float(ci[0]), intercept_fit_A_aa=float(ci[1]))
    for q, (nm, f, M, bf) in enumerate(VAR):
        z0 = mf(f'z0_{lg}')[:, q]; zb = mf(f'zb_{lg}')[:, q]
        d[nm] = dict(z0=float(np.median(z0[m])), zbk=float(np.median(zb[m])),
                     dz=float(np.median(zb[m] - z0[m])),
                     reach_vs_fitted_halfwidth=float(np.median(zb[m] - z0[m]) / (c[0] + c[1] / 2)),
                     reach_vs_0p033=float(np.median(zb[m] - z0[m]) / 0.033))
    res['readout_lag'][f'bk-{lg} ({lg*10} ms)'] = d
for q, (nm, f, M, bf) in enumerate(VAR):
    z0 = mf('z0_3')[:, q]; zb = mf('zb_3')[:, q]
    res['per_route'][nm] = {rk: dict(n=int((m & (route == rk)).sum()),
                                     reach=float(np.median((zb - z0)[m & (route == rk)]) / 0.033))
                            for rk in TQ if (m & (route == rk)).sum() >= 5}
import numpy as _np
_np.savez_compressed(OUT + '/sens_rows.npz', rows=_np.array(rows, dtype=object))
json.dump(res, open(OUT + '/reach_sens.json', 'w'), indent=1, default=float)
print(json.dumps(res, indent=1, default=lambda x: round(float(x), 4)))
