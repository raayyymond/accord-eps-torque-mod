"""Independent adversarial check of D2: does the V282 group's low-speed smoothness advantage
survive dropping route 0000006c--2bc842dbac (62 segments, ~65-78% of V282's dwell-jump mass)?

Re-derives directly from the per-route .npz BLK/DJ arrays (does not reuse d_matched.py / d_analyze.py
grouping code, only the column-name maps and the sa_des-based BLK columns those scripts already wrote).
"""
import sys, json
import numpy as np

HERE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/d_v282low'
sys.path.insert(0, HERE)
from d_extract import BLK_COLS  # noqa

B = {c: i for i, c in enumerate(BLK_COLS)}

V282_ROUTES = ['00000064--ce6b0b0ebb', '00000065--b9f78988bd', '0000006c--2bc842dbac']
V282OLD_ROUTES = ['00000039--f56039af87', '0000003a--283a39a1d6', '0000003c--927965c2b4']
TORQUE_ROUTES = {
    'T64': ['0000006c--68c6e94b17', '0000006d--05e83bb04f'],
    'T64B': ['0000006e--6ca3e014fd'],
    'T5': ['00000076--d0b7ea7e4d'],
    'T4': ['00000075--6c8687d5bd'],
}

def load(rk):
    D = np.load(f'{HERE}/data/{rk}.npz')
    return D['BLK'], D['DJ']

def rms(X, k):
    return float(np.sqrt(np.mean(X[:, B[k]] ** 2))) if len(X) else float('nan')

def cell(X, v0, v1, r0, r1, a0, a1):
    m = (X[:, B['v']] >= v0) & (X[:, B['v']] < v1) & (X[:, B['abs_rate_des']] >= r0) & (X[:, B['abs_rate_des']] < r1) \
        & (X[:, B['abs_des']] >= a0) & (X[:, B['abs_des']] < a1)
    return X[m]

RB = [(0, 5), (5, 15), (15, 35)]
AB = (0, 45)

print('=== per-route n and sr_18_35 RMS contribution, V282 group ===')
for vb in [(2.5, 8), (8, 15)]:
    print(f'\n-- speed {vb}')
    for rb in RB:
        rows = {}
        for rk in V282_ROUTES:
            BLK, DJ = load(rk)
            X = cell(BLK, vb[0], vb[1], rb[0], rb[1], AB[0], AB[1])
            rows[rk] = (len(X), rms(X, 'sr_18_35'))
        allX = np.concatenate([cell(load(rk)[0], vb[0], vb[1], rb[0], rb[1], AB[0], AB[1]) for rk in V282_ROUTES])
        noC = np.concatenate([cell(load(rk)[0], vb[0], vb[1], rb[0], rb[1], AB[0], AB[1]) for rk in V282_ROUTES if '6c' not in rk])
        print(f'  rate {rb}: per-route n/sr1835 = {[(rk[:8], n, round(s,3) if np.isfinite(s) else s) for rk,(n,s) in rows.items()]}')
        print(f'    pooled(all 3)  n={len(allX):4d} sr1835={rms(allX,"sr_18_35"):.3f}')
        print(f'    pooled(no 6c)  n={len(noC):4d} sr1835={rms(noC,"sr_18_35") if len(noC) else float("nan"):.3f}')

print('\n\n=== compare to torque groups (unchanged) for the same cells ===')
for vb in [(2.5, 8), (8, 15)]:
    print(f'\n-- speed {vb}')
    for rb in RB:
        for g, routes in TORQUE_ROUTES.items():
            X = np.concatenate([cell(load(rk)[0], vb[0], vb[1], rb[0], rb[1], AB[0], AB[1]) for rk in routes])
            if len(X) < 5:
                continue
            print(f'    {g:6s} rate {rb}: n={len(X):4d} sr1835={rms(X,"sr_18_35"):.3f}')

print('\n\n=== dwell-then-jump, V282 with/without route 6c ===')
for vb in [(2.5, 8), (8, 15)]:
    all_dj = []
    per_route = {}
    for rk in V282_ROUTES:
        BLK, DJ = load(rk)
        if len(DJ) == 0:
            per_route[rk] = np.zeros((0, 5))
            continue
        m = (DJ[:, 0] >= vb[0]) & (DJ[:, 0] < vb[1])
        per_route[rk] = DJ[m]
        all_dj.append(DJ[m])
    allJ = np.concatenate(all_dj) if all_dj else np.zeros((0, 5))
    noC = np.concatenate([per_route[rk] for rk in V282_ROUTES if '6c' not in rk])
    def stats(J):
        if len(J) < 5:
            return dict(n=len(J), p50=None, p90=None, frac_gt3=None)
        jj = J[:, 3]
        return dict(n=len(J), p50=float(np.percentile(jj, 50)), p90=float(np.percentile(jj, 90)), frac_gt3=float(np.mean(jj > 3)))
    print(f'  speed {vb}: ALL(3 routes) {stats(allJ)}')
    print(f'  speed {vb}: NO-6c(2 routes) {stats(noC)}')
    print(f'  speed {vb}: 6c-ONLY {stats(per_route["0000006c--2bc842dbac"])}')
    for rk in V282_ROUTES:
        print(f'    {rk}: n={len(per_route[rk])}', stats(per_route[rk]) if len(per_route[rk]) else '')

print('\n\n=== torque-mode dwell-jump for reference (unchanged) ===')
for vb in [(2.5, 8), (8, 15)]:
    for g, routes in TORQUE_ROUTES.items():
        DJs = []
        for rk in routes:
            _, DJ = load(rk)
            if len(DJ):
                m = (DJ[:, 0] >= vb[0]) & (DJ[:, 0] < vb[1])
                DJs.append(DJ[m])
        J = np.concatenate(DJs) if DJs else np.zeros((0, 5))
        if len(J) < 5:
            print(f'  {g} speed {vb}: n={len(J)} (too few)')
            continue
        jj = J[:, 3]
        print(f'  {g} speed {vb}: n={len(J)} p50={np.percentile(jj,50):.2f} p90={np.percentile(jj,90):.2f} frac_gt3={np.mean(jj>3):.3f}')
