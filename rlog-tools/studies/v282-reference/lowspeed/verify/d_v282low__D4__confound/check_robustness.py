import sys, json
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/d_v282low')
from d_common import *
from d_extract import bp

R = load_all()
TAU = 3

def beq_component(runs, vb, col):
    num = 0.0; den = 0.0
    for r in runs:
        if r.shape[1] < 400: continue
        srb = bp(r[4].astype(float), 1.8, 3.5)
        m = (r[0] >= vb[0]) & (r[0] < vb[1]); m[:100] = False; m[-100:] = False
        m[:TAU] = False
        idx = np.nonzero(m)[0]
        if len(idx) < 50: continue
        xb = bp(r[col].astype(float), 1.8, 3.5)
        num += float(np.sum(xb[idx - TAU] * srb[idx]))
        den += float(np.sum(srb[idx] ** 2))
    if den < 1e-6:
        return None, den
    return -num / den, den

out = {}
for g in ['T64', 'T64B', 'T5', 'T4']:
    runs = sum([split_runs(R[k]) for k in R if R[k]['group'] == g], [])
    for vb in [(2.5, 8), (8, 15)]:
        per_run = []
        for r in runs:
            b, den = beq_component([r], vb, 5)
            if b is not None and den > 50:   # need enough band energy in this run alone
                per_run.append((b, den))
        out[f'{g}|{vb[0]}-{vb[1]}'] = dict(n_runs=len(per_run),
                                            vals=[round(b,6) for b,d in per_run],
                                            dens=[round(d,2) for b,d in per_run])
        if per_run:
            bs = np.array([b for b,d in per_run]); ds = np.array([d for b,d in per_run])
            wmean = float(np.sum(bs*ds)/np.sum(ds))
            print(g, vb, 'n_runs=%d' % len(per_run), 'weighted_mean=%+.2e' % wmean,
                  'unweighted_mean=%+.2e' % bs.mean(), 'sign_frac_pos=%.2f' % float((bs>0).mean()),
                  'min=%+.2e max=%+.2e' % (bs.min(), bs.max()))
        else:
            print(g, vb, 'NO RUNS with enough band energy')

json.dump(out, open(f'{sys.path[0]}/per_run_beq.json', 'w'), indent=1)
