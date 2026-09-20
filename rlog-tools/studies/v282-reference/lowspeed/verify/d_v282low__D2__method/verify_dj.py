import sys, numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V
HERE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/d_v282low'

groups = {}
for rk, meta in V.ROUTES.items():
    D = np.load(f'{HERE}/data/{rk}.npz')
    DJ = D['DJ']  # (v, |sa|, dwell_s, jump_deg, |pre|)
    RUNS=D['RUNS']; RUNLEN=D['RUNLEN']; o=0
    travel=0.0
    for n in RUNLEN:
        r = RUNS[:, o:o+n]; o+=n
        v=r[0]; sa=r[3]
        m = (v>=2.5)&(v<8.0)
        travel += float(np.sum(np.abs(np.diff(sa))[m[1:]]))
    groups.setdefault(meta['group'], dict(dj=[], travel=0.0))
    if len(DJ):
        m = (DJ[:,0]>=2.5)&(DJ[:,0]<8.0)
        groups[meta['group']]['dj'].append(DJ[m,3])
    groups[meta['group']]['travel'] += travel

print("Independent recompute of D (dwell-then-jump), 2.5-8 m/s")
for g,d in groups.items():
    jumps = np.concatenate(d['dj']) if d['dj'] else np.array([])
    n = len(jumps)
    p50 = np.percentile(jumps,50) if n else None
    p90 = np.percentile(jumps,90) if n>=5 else None
    frac = np.mean(jumps>3) if n else None
    per100 = 100*n/max(d['travel'],1e-9)
    print(f"{g:8s} n={n:4d} travel={d['travel']:8.1f} per100={per100:.3f} p50={p50} p90={p90} frac>3={frac}")
