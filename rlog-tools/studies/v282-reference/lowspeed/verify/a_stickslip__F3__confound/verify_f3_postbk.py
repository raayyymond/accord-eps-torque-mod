"""Confound check on F3's post-breakaway claim ("torque command keeps rising after breakaway,
V282's falls") -- same dominant-route / T64B exclusions as verify_f3.py, plus a route-cluster
bootstrap CI (the original ss_analyze.py post_breakaway block reports medians with NO CI)."""
import sys, os, json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'a_stickslip'))
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..', 'a_stickslip'))
from ss_load import load_all, PRE, boot_ci

EP, W, EX, VAL = load_all()
N = len(EP)
ar = np.arange(N)
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); sj = col('sjump'); route = col('route')
A = lambda k, idx: W[k][ar, idx] * sj
BK = PRE - 3
c0 = A('cmd', np.full(N, BK))
c_p470 = A('cmd', np.full(N, BK + 50))  # +50 frames*10ms - 30ms offset = +470ms, matches ss_analyze.py dt_=50
delta = c_p470 - c0

DOMINANT_V282 = '0000006c--2bc842dbac'
V282_ROUTES = ['00000064--ce6b0b0ebb', '00000065--b9f78988bd', '0000006c--2bc842dbac']
TORQUE_FULL = ['T64', 'T64B', 'T5', 'T4']
T64B = '0000006e--6ca3e014fd'


def report(mask_t, mask_r, label):
    if mask_t.sum() < 5 or mask_r.sum() < 5:
        print(f'{label}: insufficient n (t={mask_t.sum()} r={mask_r.sum()})')
        return None
    mt, cit = boot_ci(delta[mask_t], route[mask_t], np.median)
    mr, cir = boot_ci(delta[mask_r], route[mask_r], np.median)
    print(f'{label}: torque median +470ms {mt:.4f} CI{tuple(round(x,4) for x in cit)}  n={mask_t.sum()}   '
          f'V282 median +470ms {mr:.4f} CI{tuple(round(x,4) for x in cir)}  n={mask_r.sum()}')
    return dict(torque=mt, torque_ci=cit, v282=mr, v282_ci=cir, n_t=int(mask_t.sum()), n_r=int(mask_r.sum()))


out = {}
for lo, hi in [(2, 8), (8, 15)]:
    print(f'\n=== v[{lo},{hi}) ===')
    mt_full = np.isin(g, TORQUE_FULL) & (v >= lo) & (v < hi)
    mr_full = np.isin(route, V282_ROUTES) & (v >= lo) & (v < hi)
    out[f'baseline_{lo}-{hi}'] = report(mt_full, mr_full, 'baseline (full groups)')

    mr_excl = np.isin(route, [r for r in V282_ROUTES if r != DOMINANT_V282]) & (v >= lo) & (v < hi)
    out[f'exclV282dom_{lo}-{hi}'] = report(mt_full, mr_excl, 'excl dominant V282 route')

    mt_exclB = np.isin(g, [x for x in TORQUE_FULL if x != 'T64B']) & (v >= lo) & (v < hi)
    out[f'exclT64B_{lo}-{hi}'] = report(mt_exclB, mr_full, 'excl T64B')

    mt_T4 = (g == 'T4') & (v >= lo) & (v < hi)
    out[f'T4_vs_V282excl_{lo}-{hi}'] = report(mt_T4, mr_excl, 'T4 alone vs V282 excl-dominant')

    m6c = (route == DOMINANT_V282) & (v >= lo) & (v < hi)
    out[f'T4_vs_6c_{lo}-{hi}'] = report(mt_T4, m6c, 'T4 alone vs 6c alone')

json.dump(out, open(os.path.join(os.path.dirname(__file__), 'out_f3_postbk_confound.json'), 'w'), indent=1)
