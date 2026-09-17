"""Independent re-run of C0 (baseline) and C4 (Smith) on the calC plant, T64 routes only (6c,6d) to keep RAM/time bounded.
Compares against s5_09_candidates.json's stored numbers to check reproducibility of the two decision-critical rows.
One route loaded at a time; deleted before the next. Writes JSON result next to this script.
"""
import json, sys
import numpy as np
from scipy import signal

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism')
import v282cmp as V  # noqa: E402
import s5ctl as C  # noqa: E402
import s5sim as SIM  # noqa: E402
# import the ORIGINAL candidates module unmodified -- reuse its Cand class + CANDS dict, do not fork the logic
import s5_09_candidates as S9  # noqa: E402

ROUTES = ['0000006c--68c6e94b17', '0000006d--05e83bb04f']  # T64 only (drop T4/75 to cut time)
PLANT = dict(SIM.PLANT_NOMINAL); PLANT.update(F=0.022, d=8)
sos210 = signal.butter(4, [2.0, 10.0], btype='band', fs=100, output='sos')


def run(cn):
    extra, opts = S9.CANDS[cn]
    rows = []; bandsegs = []
    for rk in ROUTES:
        S = V.load(rk)
        g = V.ROUTES[rk]['group']
        rev = C.GROUP_REV[g]
        D = np.load(V.CACHE / f'{rk}.npz')
        stiff = np.interp(S['t'], D['t_lp'], D['stiff']); del D
        mask = V.usable(S, 3.0) & np.isfinite(S['sa']) & np.isfinite(S['sr']) & np.isfinite(S['model'])

        def mk(S_, j0, rev=rev):
            ad0 = C.angle_from_la(float(S_['setpoint'][j0]), float(S_['v'][j0]), float(np.nan_to_num(S_['roll'][j0])),
                                  float(np.nan_to_num(S_['sR'][j0], nan=16.84)), float(stiff[j0]))
            return S9.Cand(rev, rate0=float(S_['sr'][j0]), angle_des0=ad0, extra=extra, opts=opts)
        R = SIM.simulate(S, stiff, mk, PLANT, mask)
        m2 = mask & np.isfinite(R['th'])
        roll = np.nan_to_num(S['roll']); sR = np.nan_to_num(S['sR'], nan=16.84); aoff = np.nan_to_num(S['aoff'])
        ev, _ = V.jerk_events(S, jerk_thr=0.5, vmin=3.0)
        for e in ev:
            i0, i1 = e['idx'] - 150, e['idx'] + 300
            if not m2[i0:i1].all():
                continue
            model = np.nan_to_num(S['model'][i0:i1])
            ad = np.array([C.angle_from_la(model[q], float(S['v'][i0 + q]), roll[i0 + q], sR[i0 + q], stiff[i0 + q]) for q in range(i1 - i0)])
            th = R['th'][i0:i1] - aoff[i0:i1]
            lg, gn = S9.lag_gain(V.lowpass(ad, 5), V.lowpass(th, 5))
            rows.append(dict(v=e['v'], ang_lag=lg,
                             hf=float(np.sqrt(np.mean(signal.sosfiltfilt(sos210, R['rate'][i0:i1]) ** 2)))))
        for a, b in V.runs(m2 & (S['v'] >= 15), S['t'], min_s=30):
            bandsegs.append((np.nan_to_num(S['model'][a:b]), R['la'][a:b]))
        del S, R
    out = {}
    for vb in ((3, 8), (8, 15), (15, 99)):
        sl = [r for r in rows if vb[0] <= r['v'] < vb[1]]
        if len(sl) < 3:
            continue
        out[f'v{vb[0]}-{vb[1]}'] = dict(n=len(sl), ang_lag=round(float(np.median([r['ang_lag'] for r in sl])), 3),
                                        hf=round(float(np.median([r['hf'] for r in sl])), 3))
    for nm, f1, f2 in (('b030', 0.30, 0.60),):
        h = V.band_H(bandsegs, f1, f2)
        out[nm] = h and round(h['H'], 3)
    return out


if __name__ == '__main__':
    res = {}
    for cn in ('C0_rev64', 'C4_v282_emul_smith'):
        res[cn] = run(cn)
        print(cn, json.dumps(res[cn]), flush=True)
    json.dump(res, open('rerun_c0_c4_result.json', 'w'), indent=1)
