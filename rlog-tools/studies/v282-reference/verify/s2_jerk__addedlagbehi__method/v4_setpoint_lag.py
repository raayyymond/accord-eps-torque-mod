"""Check the model-to-setpoint lag claim: how many events actually go into that median (corr>0.5 filter)?
Reimplement lag_in_trace exactly and report n and the raw distribution, not just the filtered median."""
import sys, json, glob
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import numpy as np
from scipy import signal

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s2_jerk/_out'
VBINS = [(3, 8), (8, 15), (15, 22), (22, 40)]
def vbin(v):
    for i, (a, b) in enumerate(VBINS):
        if a <= v < b: return i
    return -1

rows, tr = [], {}
for f in sorted(glob.glob(f'{OUT}/events_*.npz')):
    D = np.load(f, allow_pickle=True)
    r = json.loads(str(D['rows']))
    base = len(rows)
    for q, x in enumerate(r):
        x['uid'] = base + q; x['vb'] = vbin(x['v'])
    rows += r
    for k in D.files:
        if k == 'rows': continue
        if len(r): tr.setdefault(k, []).append(D[k])
tr = {k: np.concatenate(v, 0) for k, v in tr.items()}

def lp(x, fc=3.0):
    return signal.sosfiltfilt(signal.butter(2, fc, fs=100, output='sos'), x, axis=-1)

def lag_in_trace(x, y, lo=-60, hi=80):
    yy = y[80:270] - y[80:270].mean(); best = (-2, 0)
    for L in range(lo, hi + 1):
        a, b = 80 - L, 270 - L
        if a < 0 or b > len(x): continue
        xx = x[a:b] - x[a:b].mean(); den = np.sqrt(np.dot(xx, xx) * np.dot(yy, yy))
        c = np.dot(xx, yy) / den if den > 0 else 0
        if c > best[0]: best = (c, L)
    return best[1] / 100.0, best[0]

for g in ('V282', 'T64'):
    for sn, vbs in (('8-15', [1]), ('>=15', [2, 3])):
        R = [r for r in rows if r['group'] == g and r['vb'] in vbs]
        U = [r['uid'] for r in R]
        L = [lag_in_trace(tr['model'][u], lp(tr['setpoint'][u])) for u in U]
        good = [a for a, c in L if c > 0.5]
        allc = [c for a, c in L]
        print(f"{g} {sn}: n_events={len(U)}  n_corr>0.5={len(good)}  median(good)={np.median(good) if good else float('nan'):.3f}  "
              f"median(all)={np.median([a for a,c in L]):.3f}  corr median={np.median(allc):.3f}")
