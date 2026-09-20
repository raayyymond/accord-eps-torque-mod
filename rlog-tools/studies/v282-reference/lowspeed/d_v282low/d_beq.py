"""Energy sign of each command component in the 1.8-3.5 Hz band, by speed: b_eq = -<x(t - tau), rate>/<rate, rate> (x, rate both
band-passed), tau = 30 ms (measured command->wheel-accel latency). Sign convention checked first: corr(out, steering angle) on
steady torque-mode frames (a torque holds the wheel against the self-aligning spring, so out and angle share sign if +out steers +angle).
b_eq > 0: the component removes energy from the band (damps); < 0: feeds it. Units: output units per deg/s."""
import json, numpy as np
from d_common import *
from d_extract import bp, lp
R = load_all(); TAU = 3
res = {}
for g in GROUPS:
    runs = sum([split_runs(R[k]) for k in R if R[k]['group'] == g], [])
    A = np.concatenate([np.vstack([r[0], r[3], r[5]]) for r in runs], axis=1)
    big = np.abs(A[1]) > 20
    sgn = float(np.corrcoef(A[2][big], A[1][big])[0, 1])
    for vb in [(2.5, 8), (8, 15)]:
        num = {k: 0.0 for k in ['out', 'f', 'p', 'i']}; den = 0.0
        for r in runs:
            if r.shape[1] < 400: continue
            srb = bp(r[4].astype(float), 1.8, 3.5)
            m = (r[0] >= vb[0]) & (r[0] < vb[1]); m[:100] = False; m[-100:] = False
            m[:TAU] = False
            idx = np.nonzero(m)[0]
            den += float(np.sum(srb[idx] ** 2))
            for k, j in [('out', 5), ('f', 6), ('p', 7), ('i', 8)]:
                xb = bp(r[j].astype(float), 1.8, 3.5)
                num[k] += float(np.sum(xb[idx - TAU] * srb[idx]))
        res[f'{g}|{vb[0]}-{vb[1]}'] = dict(corr_out_angle=sgn, **{k: -num[k] / max(den, 1e-9) for k in num})
        print(g, vb, 'corr(out, angle) |sa|>20: %+.2f' % sgn, ' '.join(f'{k} {-num[k]/max(den,1e-9):+.2e}' for k in num))
json.dump(res, open(f'{HERE}/d_beq.json', 'w'), indent=1)
