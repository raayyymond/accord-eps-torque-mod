"""s2_jerk stage 1: extract high-desired-jerk events from every route, with sign-normalised traces + scalar metrics.

Why not V.jerk_events defaults: thr 0.8 m/s^3 / pre 1.5 / post 3.0 / vmin 5 gives 3/0/37 V282 events (thin). This
stream uses the SAME jerk definition (d/dt of the 2 Hz-lowpassed model lateral accel, local peaks, min_sep 2 s)
via V.jerk_events itself, with thr lowered to THR, vmin 3, pre 1.0, post 3.0 -- so the event definition is the
shared one, only thresholds differ. Event metrics use V.event_metrics / V.steer_hf unchanged.

usage: python s2_extract.py            -> s2_jerk/_out/events_<route>.npz  (one route in RAM at a time)
"""
import sys, json, gc
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s2_jerk/_out'
# NOTE (EVIDENCE): carState.yawRate is identically 0 on this car, so V.load()['la_yaw'] is all-zero; the independent
# measure used here is la_pose = livePose angularVelocityDevice.z * v (20 Hz, slope 1.00-1.03 vs la_act, corr 0.995).
# la_act = controlsState curvature*v^2 exactly (angle-derived), so la_act IS the steering angle in m/s^2 units.
import os
THR, VMIN, PRE, POST = 0.4, 3.0, 1.0, float(os.environ.get('S2_POST', '2.5'))
FS = V.FS
NPRE, NPOST = int(PRE * FS), int(POST * FS)
SOS_RING = signal.butter(4, [1.5, 3.5], btype='band', fs=100.0, output='sos')


def classify(model_lp, k, s):
    """onset: |a| grows away from ~0 in the jerk direction; release: |a| shrinks toward 0 without crossing;
    reversal: sign crossing with both sides >= 0.3 m/s^2. Levels: mean over [k-1.0,k-0.6] and [k+0.6,k+1.0]."""
    a0 = float(np.mean(model_lp[k - 100:k - 60])); a1 = float(np.mean(model_lp[k + 60:k + 100]))
    if np.sign(a0) != np.sign(a1) and abs(a0) >= 0.3 and abs(a1) >= 0.3:
        return 'reversal', a0, a1
    if abs(a1) >= abs(a0):
        return 'onset', a0, a1
    return 'release', a0, a1


def fixed_lag(x, y, i0, i1, lo=-50, hi=80):
    """Unbiased event lag: the ACHIEVED segment y[i0:i1] is fixed; the MODEL is taken from x[i0-L:i1-L] (the model exists
    outside the engaged window, the achieved does not need to). Pearson corr per lag over a constant-length segment, so no
    shrinking-overlap bias toward L=0 (V.event_metrics has that bias: tanh step delayed 0.25 s reads lag 0.00).
    Returns (lag s, LS gain of mean-removed y on x at that lag, corr)."""
    yy = y[i0:i1] - y[i0:i1].mean(); best = (-2, 0, 0)
    for L in range(lo, hi + 1):
        xx = x[i0 - L:i1 - L]; xx = xx - xx.mean()
        den = np.sqrt(np.dot(xx, xx) * np.dot(yy, yy))
        c = np.dot(xx, yy) / den if den > 0 else 0
        if c > best[0]:
            best = (c, L, np.dot(xx, yy) / max(np.dot(xx, xx), 1e-12))
    return best[1] / FS, float(best[2]), float(best[0])


def _control():
    t = np.arange(-3, 5.5, 0.01); out = []
    for d in (0.0, 0.1, 0.25, 0.4):
        x = np.tanh(3 * t); y = 0.9 * np.tanh(3 * (t - d))
        L, g, c = fixed_lag(x, y, 200, 550)
        assert abs(L - d) < 0.011 and abs(g - 0.9) < 0.03, (d, L, g)
        out.append((d, L, round(g, 3)))
    return out


def crossing_time(y, lvl, start):
    """first index >= start where y >= lvl (y already sign-normalised, rising)."""
    w = np.nonzero(y[start:] >= lvl)[0]
    return (start + int(w[0])) if len(w) else None


def main(routes):
    import os
    os.makedirs(OUT, exist_ok=True)
    for rk in routes:
        S = V.load(rk)
        ev, j = V.jerk_events(S, jerk_thr=THR, vmin=VMIN, pre=PRE, post=POST, min_sep=2.0)
        mlp = V.lowpass(np.nan_to_num(S['model']), 2.0)
        ylp = V.lowpass(np.nan_to_num(S['la_pose']), 3.0)
        alp = V.lowpass(np.nan_to_num(S['la_act']), 3.0)
        sa = np.nan_to_num(S['sa']); sr = np.nan_to_num(S['sr'])
        # sign-flip e4 so +cmd = +left like out; scale later per group
        e4 = -np.nan_to_num(S['e4'])
        rows, tr = [], {k: [] for k in ('model', 'setpoint', 'la_act', 'la_pose', 'sa', 'sr', 'out', 'e4', 'f', 'p', 'i', 'jerk')}
        for e in ev:
            k = e['idx']; s = float(np.sign(e['jerk_peak']))
            i0, i1 = k - NPRE, k + NPOST
            if i0 - 100 < 0 or i1 + 100 > len(mlp):
                continue
            typ, a0, a1 = classify(mlp, k, s)
            r = dict(route=rk, group=S['meta']['group'], k=k, t=e['t'], v=e['v'], jerk=abs(e['jerk_peak']), sign=s,
                     type=typ, a0=a0, a1=a1, step=abs(a1 - a0), la_peak=e['la_peak'],
                     lat_delay=float(np.nanmedian(S['lat_delay'][i0:i1])))
            for ach in ('la_act', 'la_pose'):
                m = V.event_metrics(S, i0, i1, ach_key=ach)
                for kk, vv in m.items():
                    r[f'{ach}.{kk}'] = vv
            for nm, arr in (('act', alp), ('pose', ylp)):
                L, g, c = fixed_lag(mlp, arr, i0, i1)
                r[f'{nm}.slag'] = L; r[f'{nm}.sgain'] = g; r[f'{nm}.scorr'] = c
                eb = signal.sosfiltfilt(SOS_RING, np.nan_to_num(arr - mlp)[i0 - 100:i1 + 100])[100:-100]
                r[f'{nm}.ring_pre'] = float(np.sqrt(np.mean(eb[:NPRE] ** 2)))
                r[f'{nm}.ring_post'] = float(np.sqrt(np.mean(eb[NPRE:] ** 2)))
            srb = signal.sosfiltfilt(SOS_RING, sr[i0 - 100:i1 + 100])[100:-100]
            r['sr_ring_pre'] = float(np.sqrt(np.mean(srb[:NPRE] ** 2))); r['sr_ring_post'] = float(np.sqrt(np.mean(srb[NPRE:] ** 2)))
            r['hf_2_10'] = V.steer_hf(S, i0, i1)
            r['hf_1.5_3.5_post'] = V.steer_hf(S, k, i1, 1.5, 3.5)
            r['hf_1.5_3.5_pre'] = V.steer_hf(S, i0 - 0 if i0 >= 0 else 0, k + 1, 1.5, 3.5) if k - i0 >= 64 else float('nan')
            # step timing, sign-normalised about the pre level (mean over [k-1.0,k-0.6])
            dsign = np.sign(a1 - a0) if a1 != a0 else s
            base_m = np.mean(mlp[k - 100:k - 60]); base_y = np.mean(ylp[k - 100:k - 60]); base_a = np.mean(alp[k - 100:k - 60])
            D = abs(a1 - a0)
            if D >= 0.2:
                mn = dsign * (mlp[i0:i1] - base_m) / D
                for nm, arr, base in (('pose', ylp, base_y), ('act', alp, base_a)):
                    yn = dsign * (arr[i0:i1] - base) / D
                    st = 0
                    t10m = crossing_time(mn, 0.1, st)
                    for q in (0.1, 0.5, 0.9):
                        tm = crossing_time(mn, q, st); ta = crossing_time(yn, q, st)
                        r[f'{nm}.t{int(q*100)}_model'] = (tm - NPRE) / FS if tm is not None else np.nan
                        r[f'{nm}.t{int(q*100)}'] = (ta - NPRE) / FS if ta is not None else np.nan
                        r[f'{nm}.d{int(q*100)}'] = (ta - tm) / FS if (ta is not None and tm is not None) else np.nan
                    # overshoot of the achieved step beyond the demanded step peak, and settle
                    pk_m = float(np.max(mn[NPRE:])); pk_y = float(np.max(yn[NPRE:]))
                    r[f'{nm}.step_over'] = pk_y - pk_m
                    err = np.abs(yn - mn)
                    t90 = crossing_time(yn, 0.9, NPRE - 50)
                    if t90 is None:
                        r[f'{nm}.settle'] = np.nan
                    else:
                        bad = np.nonzero(err[t90:] > 0.2)[0]
                        r[f'{nm}.settle'] = ((t90 + (bad[-1] + 1 if len(bad) else 0)) - NPRE) / FS
                        if len(bad) and bad[-1] + t90 >= len(err) - 1:
                            r[f'{nm}.settle'] = np.inf
                    # early error (first 200 ms after peak jerk, and 200-600, 600-1500, 1500-3000), normalised
                    for a_, b_ in ((0, 20), (20, 60), (60, 150), (150, 300)):
                        r[f'{nm}.err_{a_}_{b_}'] = float(np.sqrt(np.mean((yn - mn)[NPRE + a_:NPRE + b_] ** 2)))
                        r[f'{nm}.bias_{a_}_{b_}'] = float(np.mean((yn - mn)[NPRE + a_:NPRE + b_]))
            # steering angle overshoot: sign-normalised angle relative to pre, peak vs end level
            sa_n = dsign * (sa[i0:i1] - np.mean(sa[k - 100:k - 60]))
            end = float(np.mean(sa_n[-50:])); pk = float(np.max(sa_n[NPRE:]))
            r['sa_delta'] = end; r['sa_over_deg'] = pk - end  # raw angle peak-over-end (turn unwinds count too; use act.step_over for demand-relative)
            mn_raw = dsign * (mlp[i0:i1] - base_m)
            r['model_over'] = float(np.max(mn_raw[NPRE:]) - np.mean(mn_raw[-50:]))
            r['sa_pk_rate'] = float(np.max(np.abs(sr[i0:i1])))
            rows.append(r)
            for nm, arr in (('model', mlp), ('setpoint', S['setpoint']), ('la_act', S['la_act']), ('la_pose', S['la_pose']),
                            ('sa', sa), ('sr', sr), ('out', S['out']), ('e4', e4), ('f', S['f']), ('p', S['p']),
                            ('i', S['i']), ('jerk', j)):
                x = np.nan_to_num(np.asarray(arr[i0:i1], dtype=float))
                if nm in ('model', 'setpoint', 'la_act', 'la_pose', 'sa', 'out', 'e4', 'f', 'p', 'i'):
                    x = x - np.mean(x[:40])
                tr[nm].append((dsign if nm != 'jerk' else s) * x)
        np.savez_compressed(f'{OUT}/events_{rk}.npz', rows=json.dumps(rows, default=float),
                            **{k: np.asarray(v, dtype=np.float32) for k, v in tr.items()})
        from collections import Counter
        c = Counter((r['type'], 'lo' if r['v'] < 15 else 'hi') for r in rows)
        print(f"{rk} {S['meta']['group']:8s} events {len(rows):4d}  {dict(c)}", flush=True)
        del S, ev, j, mlp, ylp, alp, sa, sr, e4, tr, rows
        gc.collect()


if __name__ == '__main__':
    print('fixed_lag positive control (true, est, gain):', _control())
    main(sys.argv[1:] or list(V.ROUTES))
