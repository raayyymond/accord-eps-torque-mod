"""Adversarial verification of finding D2 (d_v282low low-speed target table).
Independently reproduces two sub-claims from cached per-route .npz (RUNS array)
that had no saved script/output in d_v282low/: the frame-level |sr|/|demand rate|
ratio for |demand rate|>40 deg/s, and the ceiling on measured steering rate below
15 m/s, using sr5 = 5 Hz low-pass (matching d_extract.py's own peak_rate_meas
definition) so the method matches the rest of the pipeline.

Run from: rlog-tools/studies/v282-reference/lowspeed/d_v282low (uses its data/*.npz cache).
"""
import sys, numpy as np
sys.path.insert(0, '.')
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V
from scipy import signal

FS = 100.0
def lp(x, fc, order=4):
    return signal.sosfiltfilt(signal.butter(order, fc, btype='low', fs=FS, output='sos'), x)

GROUPS = {}
for rk, m in V.ROUTES.items():
    GROUPS.setdefault(m['group'], []).append(rk)

print('group  n_frames  median_ratio(|sr5|/|rate_des|, demand>40)   max|sr5| below 15 m/s')
for g in ('V282', 'V282old', 'T64', 'T64B', 'T5', 'T4'):
    rks = GROUPS.get(g, [])
    max_rate = 0.0
    all_ratio = []
    for rk in rks:
        d = np.load(f'data/{rk}.npz')
        RUNS, RUNLEN = d['RUNS'], d['RUNLEN']
        v, sad, sadc, sa, sr, out, f, p, i_, e4 = RUNS
        o = 0
        for n in RUNLEN:
            sl = slice(o, o + n); o += n
            if n < 50:
                continue
            vv = v[sl]
            m = (vv >= 2.5) & (vv < 15)
            if m.sum() < 20:
                continue
            sr5 = lp(sr[sl], 5.0, 2)
            rate_des = np.gradient(lp(sad[sl], 2.0, 2)) * FS
            mm = m & (np.abs(rate_des) > 40)
            if mm.sum():
                all_ratio.append(np.abs(sr5[mm]) / np.maximum(np.abs(rate_des[mm]), 1e-6))
            max_rate = max(max_rate, np.max(np.abs(sr5[m])) if m.sum() else 0.0)
    med = float(np.median(np.concatenate(all_ratio))) if all_ratio else float('nan')
    n = sum(len(x) for x in all_ratio)
    print(f'{g:8s} {n:6d}  {med:.3f}  {max_rate:.1f}')
