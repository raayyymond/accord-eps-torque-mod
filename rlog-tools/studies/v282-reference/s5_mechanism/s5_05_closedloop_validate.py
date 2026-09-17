"""s5_05: CLOSED-LOOP validation of the simulator (replica controller + V293 plant) against measured torque-mode drives.

For each torque route and each plant variant, the flown controller revision is simulated on the route's own exogenous inputs
(usable engaged stretches >= 10 s), and the SAME metrics are computed on measured and simulated signals over the SAME frames:
  M1  band |H| model->lateral accel, >= 15 m/s, 0.15-0.30 / 0.30-0.60 / 0.60-1.20 Hz  (v282cmp.band_H)
  M2  steering-rate RMS 1.5-3.5 Hz per speed stratum (the 2-2.7 Hz closed-loop wheel mode signature)
  M3  event-level: jerk events (thr 0.5 m/s^3, vmin 3) -> corr(theta_sim, theta_meas), lag/gain via event_metrics
The question is not "does it fit one number" but whether the sim reproduces the DIFFERENCES between revisions
(T64 vs T64B hold level; T64/T5 vs T4 observer/Ki) with the plant held fixed.
usage: python s5_05_closedloop_validate.py [variant ...]
"""
import json, sys
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism')
import s5lib as L  # noqa: E402
import s5ctl as C  # noqa: E402
import s5sim as SIM  # noqa: E402

V = L.V
VARIANTS = {
    'nominal': {},
    'J4e-5': dict(J=4e-5), 'J1.6e-4': dict(J=1.6e-4),
    'b3e-4': dict(b=0.0003), 'b1.5e-3': dict(b=0.0015),
    'F0.010': dict(F=0.010), 'F0.022': dict(F=0.022),
    'd4': dict(d=4), 'd9': dict(d=9),
    's_flat1': dict(s_v=[1.0, 1.0, 1.0, 1.0]),
    'calA': dict(F=0.022, d=9, b=0.0003), 'calB': dict(F=0.022, d=9, J=5e-5), 'calC': dict(F=0.022, d=8),
}
sel = sys.argv[1:] or list(VARIANTS)
sosb = signal.butter(4, [1.5, 3.5], btype='band', fs=100, output='sos')


def metrics(S, la_meas, la_sim, th_meas, th_sim, r_meas, r_sim, mask):
    out = {}
    for nm, f1, f2 in (('b015', 0.15, 0.30), ('b030', 0.30, 0.60), ('b060', 0.60, 1.20)):
        segm, segs = [], []
        for a, b in V.runs(mask & (S['v'] >= 15), S['t'], min_s=30):
            x = np.nan_to_num(S['model'][a:b])
            segm.append((x, la_meas[a:b])); segs.append((x, la_sim[a:b]))
        hm, hs = V.band_H(segm, f1, f2), V.band_H(segs, f1, f2)
        out[nm] = dict(meas=hm and round(hm['H'], 3), sim=hs and round(hs['H'], 3),
                       coh_meas=hm and round(hm['coh'], 2), coh_sim=hs and round(hs['coh'], 2))
    for st in L.STRATA:
        e_m = e_s = 0.0; nn = 0
        for a, b in V.runs(mask & (S['v'] >= st[0]) & (S['v'] < st[1]), S['t'], min_s=3):
            e_m += float(np.sum(signal.sosfiltfilt(sosb, r_meas[a:b]) ** 2))
            e_s += float(np.sum(signal.sosfiltfilt(sosb, r_sim[a:b]) ** 2)); nn += b - a
        out[f'hf_{st[0]:.0f}'] = dict(meas=round(np.sqrt(e_m / max(nn, 1)), 2), sim=round(np.sqrt(e_s / max(nn, 1)), 2), sec=nn / 100)
    ev, _ = V.jerk_events(S, jerk_thr=0.5, vmin=3.0)
    cors, gm, gs, lm, ls = [], [], [], [], []
    for e in ev:
        i0, i1 = e['idx'] - 150, e['idx'] + 300
        if not mask[i0:i1].all():
            continue
        cors.append(float(np.corrcoef(th_meas[i0:i1], th_sim[i0:i1])[0, 1]))
        mm = V.event_metrics(dict(model=S['model'], la_act=la_meas), i0, i1)
        ms = V.event_metrics(dict(model=S['model'], la_act=la_sim), i0, i1)
        gm.append(mm['gain']); gs.append(ms['gain']); lm.append(mm['lag']); ls.append(ms['lag'])
    out['events'] = dict(n=len(cors), corr_theta_med=cors and round(float(np.median(cors)), 3),
                         gain_meas=gm and round(float(np.median(gm)), 3), gain_sim=gs and round(float(np.median(gs)), 3),
                         lag_meas=lm and round(float(np.median(lm)), 3), lag_sim=ls and round(float(np.median(ls)), 3))
    return out


try:
    RES = json.load(open(L.OUT + 's5_05_closedloop_validate.json'))
except Exception:
    RES = {}
for vn in sel:
    P = dict(SIM.PLANT_NOMINAL); P.update(VARIANTS[vn])
    RES[vn] = {}
    for g in ('T64', 'T64B', 'T5', 'T4'):
        for rk in L.GROUPS[g]:
            S = V.load(rk)
            D = np.load(V.CACHE / f'{rk}.npz'); stiff = np.interp(S['t'], D['t_lp'], D['stiff']); del D
            mask = V.usable(S, 3.0) & np.isfinite(S['sa']) & np.isfinite(S['sr']) & np.isfinite(S['model'])
            rev = C.GROUP_REV[g]

            def mk(S_, j0, rev=rev):
                ad0 = C.angle_from_la(float(S_['setpoint'][j0]), float(S_['v'][j0]), float(np.nan_to_num(S_['roll'][j0])),
                                      float(np.nan_to_num(S_['sR'][j0], nan=16.84)), float(stiff[j0]))
                return C.Ctl(rev, rate0=float(S_['sr'][j0]), angle_des0=ad0)
            R = SIM.simulate(S, stiff, mk, P, mask)
            m2 = mask & np.isfinite(R['th'])
            met = metrics(S, np.where(m2, S['la_act'], np.nan), R['la'], S['sa'], R['th'], S['sr'], R['rate'], m2)
            RES[vn][rk] = dict(group=g, **met)
            print(vn, g, rk, json.dumps(met), flush=True)
            if vn == 'nominal':
                np.savez_compressed(L.OUT + f'_sim_nominal_{rk}.npz', **{k: x for k, x in R.items()})
            del S, R
    json.dump(RES, open(L.OUT + 's5_05_closedloop_validate.json', 'w'), indent=1)
