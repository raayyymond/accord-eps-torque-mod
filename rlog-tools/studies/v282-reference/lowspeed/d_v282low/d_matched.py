"""Demand-matched block table below 8 m/s and 8-15: bins of mean |d sa_des/dt| (deg/s) x |sa_des| (<45, >=45).
Per bin: pooled RMS angle error (common lead), error / rms-demand-rate proxy, 2-10 and 1.8-3.5 Hz steer-rate RMS; route-cluster
bootstrap; then V282-weighted pooled ratios (each torque bin reweighted to V282's bin occupancy)."""
import json, numpy as np
from d_common import *
rng = np.random.default_rng(5)
R = load_all()
RB = [(0, 5), (5, 15), (15, 35), (35, 80), (80, 400)]
AB = [(0, 45), (45, 400)]
def rms(X, k): return float(np.sqrt(np.mean(X[:, B[k]] ** 2)))
res = {}
for vb in [(2.5, 8), (8, 15)]:
    for g in GROUPS:
        per = [R[k]['BLK'] for k in R if R[k]['group'] == g]
        for rb in RB:
            for ab in AB:
                Xs = []
                for X in per:
                    m = (X[:, B['v']] >= vb[0]) & (X[:, B['v']] < vb[1]) & (X[:, B['abs_rate_des']] >= rb[0]) & (X[:, B['abs_rate_des']] < rb[1]) \
                        & (X[:, B['abs_des']] >= ab[0]) & (X[:, B['abs_des']] < ab[1])
                    Xs.append(X[m])
                n = sum(len(x) for x in Xs)
                if n < 5:
                    continue
                A = np.concatenate(Xs)
                row = dict(n=n, rate=float(np.mean(A[:, B['abs_rate_des']])), err=rms(A, 'err_rms_cl'), sr210=rms(A, 'sr_2_10'), sr1835=rms(A, 'sr_18_35'), srlt1=rms(A, 'sr_lt1'))
                reps = []
                Xn = [x for x in Xs if len(x)]
                for _ in range(500):
                    pk = rng.integers(0, len(Xn), len(Xn))
                    C = np.concatenate([Xn[p][rng.integers(0, len(Xn[p]), len(Xn[p]))] for p in pk])
                    reps.append((rms(C, 'err_rms_cl'), rms(C, 'sr_18_35')))
                reps = np.array(reps)
                row['err_ci'] = np.percentile(reps[:, 0], [2.5, 97.5]).tolist(); row['sr1835_ci'] = np.percentile(reps[:, 1], [2.5, 97.5]).tolist()
                res[f'{vb[0]}-{vb[1]}|{rb[0]}-{rb[1]}|{ab[0]}-{ab[1]}|{g}'] = row
json.dump(res, open(f'{HERE}/d_matched.json', 'w'), indent=1)
for vb in ['2.5-8', '8-15']:
    print('\n== speed', vb)
    for rb in RB:
        for ab in AB:
            ks = [f'{vb}|{rb[0]}-{rb[1]}|{ab[0]}-{ab[1]}|{g}' for g in GROUPS]
            if not any(k in res for k in ks):
                continue
            print(f' rate {rb} ang {ab}')
            for g, k in zip(GROUPS, ks):
                if k in res:
                    r = res[k]
                    print(f"   {g:8s} n{r['n']:4d} rate {r['rate']:5.1f} err {r['err']:5.2f} [{r['err_ci'][0]:.2f},{r['err_ci'][1]:.2f}]  sr2-10 {r['sr210']:5.2f}  sr1.8-3.5 {r['sr1835']:5.2f} [{r['sr1835_ci'][0]:.2f},{r['sr1835_ci'][1]:.2f}]  sr<1 {r['srlt1']:5.1f}")
