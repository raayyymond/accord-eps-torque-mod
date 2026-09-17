"""s5_04: matched high-desired-jerk events, V282 (rate servo) vs torque mode, in the STEERING-ANGLE domain, plus the torque-mode
command decomposition (replica components from s5_03, validated corr 0.996-0.999 vs logged out).

Events: v282cmp.jerk_events(jerk_thr=0.5, vmin=3) (0.8 finds too few), window [-1.5, +3.0] s.  Strata: v 3-8 / 8-15 / >=15,
|jerk| 0.5-1 / 1-2 / >=2 m/s^3.  Per event (desired angle ad = the fork's own angle_des of the MODEL's demand, VehicleModel
with liveParameters roll/sR/stiffness; theta = sa - angleOffset):
  ang_lag   xcorr lag of theta behind ad (0-0.8 s);  ang_gain  regression of theta on lag-aligned ad (demeaned);
  ang_err   rms(theta - ad) normalised by the ad swing (unaligned: what the car feels);  rate_lag / rate_gain the same on
  d/dt (5 Hz LP);  hf  steering-rate RMS 2-10 Hz (v282cmp.steer_hf);  la_* event_metrics with la_act and la_pose.
Torque routes only: required torque on the DESIRED trajectory with the identified plant (s5_02 fit, per stratum:
  J ad'' + b ad' + s hold0(ad) + F tanh(ad'/2)) vs the feedforward the fork supplied, split into hold/move/hyst/rl/dob, P, I.
"""
import json, sys
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism')
import s5lib as L  # noqa: E402
import s5ctl as C  # noqa: E402

V = L.V
PL = json.load(open(L.OUT + 's5_02_plant_ident.json'))
VB = [(3, 8), (8, 15), (15, 99)]
JB = [(0.5, 1.0), (1.0, 2.0), (2.0, 99)]


def plant_par(v):
    key = '3-8' if v < 8 else '8-15' if v < 15 else '15-22' if v < 22 else '22-40'
    return PL[key]


def lag_gain(x, y, maxlag=80):
    n = len(x); best, lag = -np.inf, 0
    for k in range(0, maxlag + 1):
        xa, ya = x[:n - k] - x[:n - k].mean(), y[k:] - y[k:].mean()
        c = float(np.dot(xa, ya)) / max(np.linalg.norm(xa) * np.linalg.norm(ya), 1e-9)
        if c > best:
            best, lag = c, k
    xa, ya = x[:n - lag] - x[:n - lag].mean(), y[lag:] - y[lag:].mean()
    return lag / 100.0, float(np.dot(xa, ya) / max(np.dot(xa, xa), 1e-9)), best


rows = []
for g, routes in L.GROUPS.items():
    for rk in routes:
        S = V.load(rk)
        D = np.load(V.CACHE / f'{rk}.npz'); stiff = np.interp(S['t'], D['t_lp'], D['stiff']); del D
        Rp = None
        if g.startswith('T'):
            Rp = np.load(L.OUT + f'_replica_{rk}.npz')
        ev, _ = V.jerk_events(S, jerk_thr=0.5, vmin=3.0)
        roll = np.nan_to_num(S['roll']); sR = np.nan_to_num(S['sR'], nan=16.84); aoff = np.nan_to_num(S['aoff'])
        for e in ev:
            i0, i1 = e['idx'] - 150, e['idx'] + 300
            if not np.isfinite(S['sa'][i0:i1]).all():
                continue
            model = np.nan_to_num(S['model'][i0:i1])
            ad = np.array([C.angle_from_la(model[k], float(S['v'][i0 + k]), roll[i0 + k], sR[i0 + k], stiff[i0 + k]) for k in range(i1 - i0)])
            th = S['sa'][i0:i1] - aoff[i0:i1]
            adf, thf = V.lowpass(ad, 5.0), V.lowpass(th, 5.0)
            adr, thr = V.deriv(adf), V.deriv(thf)
            swing = max(np.ptp(ad), 1e-3)
            al, ag, ac = lag_gain(adf, thf)
            rl_, rg, rc = lag_gain(adr, thr)
            r = dict(g=g, rk=rk, v=e['v'], jerk=abs(e['jerk_peak']), la_peak=e['la_peak'], ad_swing=float(swing),
                     ad_rate_pk=float(np.max(np.abs(adr))), th_rate_pk=float(np.max(np.abs(thr))),
                     ang_lag=al, ang_gain=ag, ang_corr=ac, ang_err=float(np.sqrt(np.mean((th - ad) ** 2)) / swing),
                     ang_err_deg=float(np.sqrt(np.mean((th - ad - np.mean(th - ad)) ** 2))),
                     rate_lag=rl_, rate_gain=rg, rate_corr=rc, hf=V.steer_hf(S, i0, i1),
                     lat_delay=float(np.nanmedian(S['lat_delay'][i0:i1])))
            for key in ('la_act', 'la_pose'):
                if np.isfinite(S[key][i0:i1]).all():
                    em = V.event_metrics(S, i0, i1, ach_key=key)
                    r[key + '_gain'] = em['gain']; r[key + '_lag'] = em['lag']; r[key + '_rough'] = em['jerk_rough']
            if Rp is not None and np.isfinite(Rp['out'][i0:i1]).all():
                LAF = 14.0
                P = plant_par(e['v'])
                acc = V.deriv(V.lowpass(adr, 5.0))
                h0 = np.array([C.hold_torque(ad[k], float(S['v'][i0 + k]), False) for k in range(i1 - i0)])
                req = P['J'] * acc + P['b'] * adr + P['s'] * h0 + P['F'] * np.tanh(adr / 2.0)    # +left
                comp = {k: -Rp[k][i0:i1] / LAF for k in ('hold', 'move', 'hyst', 'rl', 'dob', 'p', 'i')}   # +left torque
                ffL = comp['hold'] + comp['move'] + comp['hyst'] + comp['rl'] + comp['dob']
                out = S['out'][i0:i1]
                dreq = req - req[:50].mean()
                # transient content: component change over the window projected on the required change
                den = float(np.dot(dreq, dreq))
                for k, x in comp.items():
                    r['share_' + k] = float(np.dot(x - x[:50].mean(), dreq) / max(den, 1e-12))
                r['share_out'] = float(np.dot(out - out[:50].mean(), dreq) / max(den, 1e-12))
                # dynamic part only (what the rate servo supplied on V282): inertia + viscous + friction
                dyn = P['J'] * acc + P['b'] * adr + P['F'] * np.tanh(adr / 2.0)
                r['req_dyn_rms'] = float(np.std(dyn)); r['req_hold_rms'] = float(np.std(P['s'] * h0))
                r['ff_move_rms'] = float(np.std(comp['move'])); r['inertia_rms'] = float(np.std(P['J'] * acc))
                r['fb_rms'] = float(np.std(comp['p'] + comp['i']))
                # timing: lag of the fork's total command behind the required torque
                lg, gn, cc = lag_gain(dreq, out - out[:50].mean(), maxlag=60)
                r['cmd_lag_vs_req'] = lg; r['cmd_gain_vs_req'] = gn; r['cmd_corr_vs_req'] = cc
                lg, gn, cc = lag_gain(dreq, ffL - ffL[:50].mean(), maxlag=60)
                r['ff_lag_vs_req'] = lg; r['ff_gain_vs_req'] = gn
            rows.append(r)
        print(g, rk, len(ev), flush=True)
        del S, Rp

json.dump(rows, open(L.OUT + 's5_04_events_rows.json', 'w'))

# ---- aggregate: medians with bootstrap CI over events, plus per-route medians
rng = np.random.default_rng(0)
KEYS = ['lat_delay', 'ang_lag', 'ang_gain', 'ang_err', 'ang_err_deg', 'rate_lag', 'rate_gain', 'rate_corr', 'hf', 'la_act_gain', 'la_act_lag',
        'la_pose_gain', 'la_pose_lag', 'la_act_rough', 'share_hold', 'share_move', 'share_hyst', 'share_rl', 'share_dob', 'share_p',
        'share_i', 'share_out', 'cmd_lag_vs_req', 'cmd_gain_vs_req', 'ff_lag_vs_req', 'ff_gain_vs_req', 'req_dyn_rms',
        'req_hold_rms', 'inertia_rms', 'ff_move_rms', 'fb_rms']
agg = {}
for g in L.GROUPS:
    for vb in VB:
        for jb in [(0.5, 99)] + JB:
            sel = [r for r in rows if r['g'] == g and vb[0] <= r['v'] < vb[1] and jb[0] <= r['jerk'] < jb[1]]
            if len(sel) < 3:
                continue
            key = f'{g}|v{vb[0]}-{vb[1]}|j{jb[0]}-{jb[1]}'
            a = dict(n=len(sel), routes={rk: sum(1 for r in sel if r['rk'] == rk) for rk in set(r['rk'] for r in sel)},
                     v_med=float(np.median([r['v'] for r in sel])), jerk_med=float(np.median([r['jerk'] for r in sel])),
                     ad_rate_pk_med=float(np.median([r['ad_rate_pk'] for r in sel])))
            for k in KEYS:
                x = np.array([r[k] for r in sel if k in r and np.isfinite(r[k])])
                if len(x) < 3:
                    continue
                bs = [np.median(rng.choice(x, len(x))) for _ in range(500)]
                a[k] = [round(float(np.median(x)), 4), round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)]
            agg[key] = a
json.dump(agg, open(L.OUT + 's5_04_events_agg.json', 'w'), indent=1)
for k, a in agg.items():
    if '|j0.5-99' in k:
        print(k, 'n', a['n'], a['routes'], 'v', round(a['v_med'],1), 'j', round(a['jerk_med'],2), 'adr', round(a['ad_rate_pk_med'],1), {kk: a.get(kk) for kk in ('lat_delay', 'ang_lag', 'ang_gain', 'ang_err', 'ang_err_deg', 'rate_lag', 'rate_gain', 'hf', 'la_act_gain', 'la_act_lag', 'la_pose_gain', 'la_pose_lag', 'la_act_rough')})
        if k.startswith('T'):
            print('    decomposition', {kk: a.get(kk) for kk in ('share_hold', 'share_move', 'share_hyst', 'share_rl', 'share_dob', 'share_p', 'share_i', 'share_out', 'cmd_lag_vs_req', 'cmd_gain_vs_req', 'ff_lag_vs_req', 'ff_gain_vs_req', 'req_dyn_rms', 'req_hold_rms', 'inertia_rms', 'ff_move_rms', 'fb_rms')})
