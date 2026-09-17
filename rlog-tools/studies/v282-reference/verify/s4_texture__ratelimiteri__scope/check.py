"""Adversarial SCOPE check on s4_texture 'rate-limiter-is-not-the-jerk'.
Finer speed/angle grid + softer (near-miss) thresholds, using the already-extracted FR frame tables.
Read-only: loads s4_texture/data/*.npz, does not touch v282cmp.py or s4_texture/*.
"""
import sys, glob, json
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import numpy as np
import v282cmp as V

D_DIR = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s4_texture/data'
GROUPS = ['V282', 'V282old', 'T64', 'T64B', 'T5', 'T4']
routes = {g: [rk for rk, m in V.ROUTES.items() if m['group'] == g] for g in GROUPS}

SPD = [(0,5),(5,8),(8,15),(15,40)]
ANG = [(0,5),(5,15),(15,45),(45,90),(90,999)]
THRS = [60, 80, 100, 120]

for g in GROUPS:
    FR = []
    for rk in routes[g]:
        D = np.load(f'{D_DIR}/{rk}.npz', allow_pickle=True)
        FR.append(D['FR'])
    F = np.concatenate(FR, axis=1)
    v, ang, de4, e4a, sra = F[0], F[1], F[2], F[3], F[4]
    print(f'=== {g}  total frames {F.shape[1]}')
    for s0, s1 in SPD:
        for a0, a1 in ANG:
            m = (v >= s0) & (v < s1) & (ang >= a0) & (ang < a1)
            n = int(m.sum())
            if n < 200:
                continue
            row = [round(100*np.mean(de4[m] >= t), 4) for t in THRS]
            print(f'  v{s0}-{s1} a{a0}-{a1}  n={n:7d}  pct>=60/80/100/120 = {row}')
