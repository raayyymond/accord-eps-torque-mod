"""Independent re-derivation of D2's frame-level claims, from the cached RUNS arrays only
(no reuse of d_analyze.py / d_matched.py code). Recomputes:
  - frame-level |sr| / |rate_des| ratio where |rate_des| > 40 deg/s, below 8 m/s, per group
  - max |sr| (measured steering rate) below 8 m/s, per group
RUNS columns (from d_extract.py route()): v, sad, sadc, sa, sr, out, f, p, i, e4  (float32, 100 Hz)
"""
import sys, numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

HERE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/d_v282low'
FS = 100.0

def lp(x, fc, order=4):
    return signal.sosfiltfilt(signal.butter(order, fc, btype='low', fs=FS, output='sos'), x)

def deriv(x):
    return np.gradient(x) * FS

COLS = ['v', 'sad', 'sadc', 'sa', 'sr', 'out', 'f', 'p', 'i', 'e4']
IDX = {c: i for i, c in enumerate(COLS)}

results = {}
for rk, meta in V.ROUTES.items():
    g = meta['group']
    D = np.load(f'{HERE}/data/{rk}.npz')
    RUNS = D['RUNS']; RUNLEN = D['RUNLEN']
    o = 0
    ratios_own = []   # using x['sad'] (own build lead), matches d_extract.py's rate_des definition
    ratios_cl = []     # using x['sadc'] (common lead)
    max_sr_all = []
    for n in RUNLEN:
        r = RUNS[:, o:o+n]; o += n
        if n < 300:
            continue
        v = r[IDX['v']]; sad = r[IDX['sad']]; sadc = r[IDX['sadc']]; sr = r[IDX['sr']]
        rate_des_own = deriv(lp(sad, 2.0, 2))
        rate_des_cl = deriv(lp(sadc, 2.0, 2))
        m8 = (v >= 2.5) & (v < 8.0)
        if m8.sum() < 50:
            continue
        max_sr_all.append(np.max(np.abs(sr[m8])) if m8.sum() else np.nan)
        m40_own = m8 & (np.abs(rate_des_own) > 40)
        m40_cl = m8 & (np.abs(rate_des_cl) > 40)
        if m40_own.sum():
            ratios_own.append((np.abs(sr[m40_own]), np.abs(rate_des_own[m40_own])))
        if m40_cl.sum():
            ratios_cl.append((np.abs(sr[m40_cl]), np.abs(rate_des_cl[m40_cl])))
    if rk not in results:
        results.setdefault(g, dict(n_frames_own=0, n_frames_cl=0, ratio_own=[], ratio_cl=[], max_sr=[]))
    for sr_a, rd_a in ratios_own:
        results[g]['ratio_own'].append(sr_a / rd_a)
        results[g]['n_frames_own'] += len(sr_a)
    for sr_a, rd_a in ratios_cl:
        results[g]['ratio_cl'].append(sr_a / rd_a)
        results[g]['n_frames_cl'] += len(sr_a)
    results[g]['max_sr'].extend(max_sr_all)

print("=== Frame-level |sr|/|rate_des| where |rate_des|>40 deg/s, 2.5-8 m/s ===")
for g, d in results.items():
    if d['ratio_own']:
        allr = np.concatenate(d['ratio_own'])
        med = np.median(allr); mean = np.mean(allr)
        print(f"{g:8s} own-lead  n={len(allr):5d}  median={med:.3f}  mean={mean:.3f}")
    if d['ratio_cl']:
        allr = np.concatenate(d['ratio_cl'])
        med = np.median(allr); mean = np.mean(allr)
        print(f"{g:8s} cl-lead   n={len(allr):5d}  median={med:.3f}  mean={mean:.3f}")

print("\n=== Max |measured steering rate| per run, 2.5-8 m/s, then group max ===")
for g, d in results.items():
    ms = np.array(d['max_sr'])
    ms = ms[np.isfinite(ms)]
    if len(ms):
        print(f"{g:8s} n_runs={len(ms):3d}  max={ms.max():.1f}  p95={np.percentile(ms,95):.1f}  top5={np.sort(ms)[-5:]}")
