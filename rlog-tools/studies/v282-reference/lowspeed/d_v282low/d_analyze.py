"""d_v282low stage 2 -- the low-speed target table.

A  block cells (1.28 s): speed (2.5-8, 8-15) x demand (Q quiet |des|<15 & |rate|<10; A15 |des|>=15; R10 |rate_des|>=10)
   metrics pooled as RMS over blocks; CI = two-level bootstrap (routes, then blocks within route), B=1000.
B  command smoothness: out 2-10 Hz / out <1 Hz (unitless, survives the rate-vs-torque meaning of the output),
   and the share of the 2-10 Hz command carried by f / p / i.
C  run spectra (runs >= 6 s): coherence and |H| out -> steer rate, and demand angle -> measured angle, per band.
D  dwell-then-jump: count per 100 deg of travel and jump p50/p90.
E  rate-transient events: medians.
"""
import json
import numpy as np
from scipy import signal
from d_common import *

rng = np.random.default_rng(11)
NB = 1000
VBS = {'2.5-8': (2.5, 8), '8-15': (8, 15)}


def cellmask(X, vb, c):
    v0, v1 = VBS[vb]
    m = (X[:, B['v']] >= v0) & (X[:, B['v']] < v1)
    d, r = X[:, B['abs_des']], X[:, B['abs_rate_des']]
    return m & {'Q': (d < 15) & (r < 10), 'A15': d >= 15, 'R10': r >= 10, 'ALL': np.ones(len(X), bool)}[c]


def pooled(Xs, fn):
    return fn(np.concatenate(Xs)) if sum(len(x) for x in Xs) else np.nan


def boot(Xs, fn):
    Xs = [x for x in Xs if len(x)]
    if not Xs or sum(len(x) for x in Xs) < 8:
        return np.nan, (np.nan, np.nan), 0
    est = fn(np.concatenate(Xs)); reps = []
    for _ in range(NB):
        pick = rng.integers(0, len(Xs), len(Xs))
        reps.append(fn(np.concatenate([Xs[p][rng.integers(0, len(Xs[p]), len(Xs[p]))] for p in pick])))
    return float(est), tuple(float(q) for q in np.nanpercentile(reps, [2.5, 97.5])), int(sum(len(x) for x in Xs))


rmsc = lambda k: (lambda X: float(np.sqrt(np.mean(X[:, B[k]] ** 2))))
ratio = lambda a, b: (lambda X: float(np.sqrt(np.mean(X[:, B[a]] ** 2)) / max(np.sqrt(np.mean(X[:, B[b]] ** 2)), 1e-9)))
share = lambda a: (lambda X: float(np.mean(X[:, B[a]] ** 2) / max(np.mean(X[:, B['out_2_10']] ** 2), 1e-12)))
METRICS = {
    'err_rms_cl_deg': rmsc('err_rms_cl'),              # angle error vs model at a common 0.20 s lead
    'err_rms_deg': rmsc('err_rms'),                    # angle error vs model at each build's own lead
    'sr_2_10_degps': rmsc('sr_2_10'),                  # smoothness: steering-rate RMS 2-10 Hz
    'sr_18_35_degps': rmsc('sr_18_35'),                # the wheel-mode band
    'sr_lt1_degps': rmsc('sr_lt1'),                    # how much the wheel is intentionally moving
    'cmd_hf_over_lf': ratio('out_2_10', 'out_lt1'),    # command HF content, unitless
    'demand_hf_over_rate': ratio('rate_des_2_10', 'abs_rate_des'),
    'f_share_hf': share('f_2_10'), 'p_share_hf': share('p_2_10'), 'i_share_hf': share('i_2_10'),
    'sat_frac': lambda X: float(np.mean(X[:, B['sat']])),
}

R = load_all()
RES = dict(A={}, C={}, D={}, E={})
for vb in VBS:
    for c in ['Q', 'A15', 'R10', 'ALL']:
        for g in GROUPS:
            Xs = [R[k]['BLK'][cellmask(R[k]['BLK'], vb, c)] for k in R if R[k]['group'] == g]
            row = {}
            for mn, fn in METRICS.items():
                est, ci, n = boot(Xs, fn)
                row[mn] = dict(est=est, ci=ci, n_blocks=n)
            RES['A'][f'{vb}|{c}|{g}'] = row

# ---- C: run spectra
NPS = 256   # df 0.39 Hz


def run_spectra(runs, vb, x_key, y_key):
    v0, v1 = VBS[vb]
    Pxx = Pyy = Pxy = None; sec = 0.0
    for r in runs:
        v = r[0]
        # split the run into contiguous in-band stretches
        m = (v >= v0) & (v < v1)
        idx = np.nonzero(np.diff(np.r_[0, m.astype(int), 0]))[0].reshape(-1, 2)
        for a, b in idx:
            if b - a < NPS:
                continue
            X = dict(sad=r[1], sadc=r[2], sa=r[3], sr=r[4], out=r[5], f=r[6], p=r[7], i=r[8])
            X['rdes'] = np.gradient(X['sadc']) * 100
            x = signal.detrend(X[x_key][a:b]); y = signal.detrend(X[y_key][a:b])
            f, pxx = signal.welch(x, 100, nperseg=NPS); _, pyy = signal.welch(y, 100, nperseg=NPS); _, pxy = signal.csd(x, y, 100, nperseg=NPS)
            w = b - a
            Pxx = pxx * w if Pxx is None else Pxx + pxx * w
            Pyy = pyy * w if Pyy is None else Pyy + pyy * w
            Pxy = pxy * w if Pxy is None else Pxy + pxy * w
            fr = f; sec += w / 100
    if Pxx is None:
        return None
    outb = {}
    for lo, hi in [(0.3, 1.0), (1.0, 2.0), (2.0, 4.0), (4.0, 10.0)]:
        s = (fr >= lo) & (fr < hi)
        coh = np.abs(Pxy[s]) ** 2 / np.maximum(Pxx[s] * Pyy[s], 1e-30)
        H = np.abs(Pxy[s]) / np.maximum(Pxx[s], 1e-30)
        ph = np.degrees(np.angle(Pxy[s].sum()))
        fc = float(np.average(fr[s], weights=Pxx[s]))
        outb[f'{lo}-{hi}'] = dict(coh=float(np.average(coh, weights=Pxx[s])), H=float(np.average(H, weights=Pxx[s])), phase=float(ph),
                                   lag_s=float(-ph / 360 / fc), y_rms=float(np.sqrt(Pyy[s].sum() * (fr[1] - fr[0]) / sec)),
                                   x_rms=float(np.sqrt(Pxx[s].sum() * (fr[1] - fr[0]) / sec)))
    outb['sec'] = sec
    return outb


for g in GROUPS:
    runs = sum([split_runs(R[k]) for k in R if R[k]['group'] == g], [])
    for vb in VBS:
        for nm, (xk, yk) in {'cmd_to_rate': ('out', 'sr'), 'des_to_angle': ('sadc', 'sa'), 'desrate_to_cmd': ('rdes', 'out'),
                             'ff_to_rate': ('f', 'sr'), 'p_to_rate': ('p', 'sr')}.items():
            RES['C'][f'{vb}|{nm}|{g}'] = run_spectra(runs, vb, xk, yk)

# ---- D: dwell-then-jump
for g in GROUPS:
    for vb in VBS:
        v0, v1 = VBS[vb]
        cnt, jumps, travel = 0, [], 0.0
        per_route = []
        for k in R:
            if R[k]['group'] != g:
                continue
            DJ = R[k]['DJ']
            m = (DJ[:, 0] >= v0) & (DJ[:, 0] < v1) if len(DJ) else np.zeros(0, bool)
            tr = 0.0
            for r in split_runs(R[k]):
                mm = (r[0] >= v0) & (r[0] < v1)
                tr += float(np.sum(np.abs(np.diff(r[3]))[mm[1:]]))
            c = int(m.sum()); cnt += c; travel += tr; jumps += list(DJ[m, 3]) if c else []
            per_route.append((c, tr))
        J = np.array(jumps)
        RES['D'][f'{vb}|{g}'] = dict(n=cnt, travel_deg=travel, per100=100 * cnt / max(travel, 1e-9),
                                     jump_p50=float(np.percentile(J, 50)) if len(J) else None,
                                     jump_p90=float(np.percentile(J, 90)) if len(J) >= 5 else None,
                                     frac_jump_gt3=float(np.mean(J > 3)) if len(J) else None,
                                     per_route=[(c, round(t)) for c, t in per_route])

# ---- E: events
for g in GROUPS:
    EV = np.concatenate([R[k]['EV'] for k in R if R[k]['group'] == g and len(R[k]['EV'])])
    for vb in VBS:
        v0, v1 = VBS[vb]
        m = (EV[:, E['v']] >= v0) & (EV[:, E['v']] < v1)
        X = EV[m]
        row = dict(n=int(m.sum()), n_build=int(X[:, E['build']].sum()) if len(X) else 0)
        for c in ['dDes', 'peak_rate_des', 'peak_rate_meas', 't50_lag', 't50_lag_cl', 'rise_des', 'rise_meas', 'overrun', 'overrun_cl',
                  'err_rms_cl', 'sr_2_10', 'sr_18_35', 'n_dj', 'max_jump', 'settle_err', 'ratio_mid']:
            if len(X):
                a = np.abs(X[:, E[c]]) if c == 'dDes' else X[:, E[c]]
                row[c] = [float(np.nanpercentile(a, q)) for q in (25, 50, 75)]
        if len(X):
            row['rate_ratio'] = [float(q) for q in np.nanpercentile(X[:, E['peak_rate_meas']] / X[:, E['peak_rate_des']], [25, 50, 75])]
        RES['E'][f'{vb}|{g}'] = row

json.dump(RES, open(f'{HERE}/d_results.json', 'w'), indent=1, default=float)

# ---- print
def fmt(x):
    return 'nan' if not np.isfinite(x['est']) else f"{x['est']:.3g}[{x['ci'][0]:.3g},{x['ci'][1]:.3g}]n{x['n_blocks']}"
for vb in VBS:
    for c in ['Q', 'A15', 'R10', 'ALL']:
        print(f'\n=== A {vb} m/s  cell {c}')
        for mn in METRICS:
            print(f'  {mn:22s}', '  '.join(f"{g}:{fmt(RES['A'][f'{vb}|{c}|{g}'][mn])}" for g in GROUPS))
for vb in VBS:
    print(f'\n=== C {vb}')
    for nm in ['cmd_to_rate', 'des_to_angle', 'desrate_to_cmd', 'ff_to_rate', 'p_to_rate']:
        for g in GROUPS:
            r = RES['C'][f'{vb}|{nm}|{g}']
            if r is None:
                print(f'  {nm:15s} {g:8s} none'); continue
            print(f"  {nm:15s} {g:8s} {r['sec']:5.0f}s " + ' | '.join(f"{b}: coh {r[b]['coh']:.2f} H {r[b]['H']:.3g} lag {r[b]['lag_s']:+.3f} yrms {r[b]['y_rms']:.3g}" for b in ['0.3-1.0', '1.0-2.0', '2.0-4.0', '4.0-10.0']))
print('\n=== D dwell-then-jump')
for k, r in RES['D'].items():
    print(' ', k, {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in r.items()})
print('\n=== E events')
for k, r in RES['E'].items():
    print(' ', k, {kk: ([round(q, 3) for q in vv] if isinstance(vv, list) else vv) for kk, vv in r.items()})
