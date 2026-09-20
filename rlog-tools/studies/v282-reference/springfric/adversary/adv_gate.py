"""ADVERSARY gate: reproduce the orchestrator's table from MY OWN loader, then show the
ALGEBRAIC IDENTITY that the CENTRE/HALF-WIDTH decomposition actually is.  Nothing is trusted
before this passes.
"""
import numpy as np
from adv_load import load, cols, PRE, BK, hold_map

EP, W, P = load()
C = cols(EP)
N = len(EP)
ar = np.arange(N)
g, v, sj, route = C['group'], C['v'], C['sjump'], C['route']
kind = C['kind']
d0 = np.maximum(C['w_d0'].astype(int), 0)
d1 = C['w_d1'].astype(int)
aa_pre = W['aa'][:, PRE]
toward = (sj == -np.sign(aa_pre)).astype(float)
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
LOW = TQ & (v >= 2) & (v < 8)


def fit4(m, idx):
    X = np.vstack([W['aa'][ar, idx], sj, sj * toward, np.ones(N)]).T[m]
    c = np.linalg.lstsq(X, W['cmd'][ar, idx][m], rcond=None)[0]
    return dict(k=c[0], away=c[1], toward=c[1] + c[2], halfwidth=c[1] + c[2] / 2,
                centring_offset=-c[2] / 2, const=c[3])


if __name__ == '__main__':
    print('=' * 80)
    print('GATE  (my loader, no ss_load / sslib import)')
    f0 = fit4(LOW, np.full(N, BK))
    exp = dict(away=0.052564, toward=0.014006, halfwidth=0.033285,
               centring_offset=0.019279, k=0.005560)
    ok = True
    for kk, want in exp.items():
        d = f0[kk] - want
        ok &= abs(d) < 5e-5
        print(f'  {kk:16s} {f0[kk]:+.7f}  want {want:+.6f}  d {d:+.2e}'
              f"  {'OK' if abs(d) < 5e-5 else '**MISMATCH**'}")
    print(f'  n {int(LOW.sum())} (145)   n_toward {int(toward[LOW].sum())} (93)'
          f"   -> GATE {'PASS' if ok and LOW.sum()==145 else 'FAIL'}")
    K, Cc = f0['k'], f0['const']

    y = (W['cmd'][ar, BK] - K * W['aa'][ar, BK] - Cc) * np.sign(aa_pre)
    aabs = np.abs(aa_pre)
    qs = np.quantile(aabs[LOW], [0, .2, .4, .6, .8, 1.0])
    print()
    print('  reproduced profile (quintiles of |aa[PRE]|):')
    print(f"  {'bin':>16s} {'n_aw':>5s} {'n_tw':>5s} {'med|aa|':>8s} {'med_away':>10s}"
          f" {'med_tow':>10s} {'CENTRE':>9s} {'HW':>9s}")
    for i in range(5):
        lo, hi = qs[i], qs[i + 1]
        m = LOW & (aabs >= lo) & (aabs <= hi if i == 4 else aabs < hi)
        ma, mt = m & (toward == 0), m & (toward == 1)
        a_, t_ = np.median(y[ma]), np.median(y[mt])
        print(f'  {lo:7.2f}-{hi:8.2f} {int(ma.sum()):5d} {int(mt.sum()):5d}'
              f' {np.median(aabs[m]):8.2f} {a_:+10.4f} {t_:+10.4f}'
              f' {(a_+t_)/2:+9.4f} {(a_-t_)/2:+9.4f}')

    print()
    print('=' * 80)
    print('WHAT THE DECOMPOSITION IS, ALGEBRAICALLY  (this is the whole attack surface)')
    print('  away episodes have sign(aa)=+sj, toward episodes sign(aa)=-sj.  Write')
    print('    R = cmd[bk] - K*aa[bk] - c      u = R*sign(aa)  (= y)')
    print('  Plant = spring S(theta) + Coulomb F.  Wheel stuck at theta requires the command,')
    print('  measured OUTWARD-positive, to satisfy   S(|th|) - F  <  u  <  S(|th|) + F.')
    print('  Breaking OUTWARD means u hit the UPPER edge: u = S(|th|)+F.')
    print('  Breaking INWARD  means u hit the LOWER edge: u = S(|th|)-F.')
    print('  So med_away = S - K|th| + F ,  med_toward = S - K|th| - F , hence')
    print('     CENTRE = S(|th|) - K*|th|        HALF-WIDTH = F')
    print('  => HALF-WIDTH flat is the Coulomb force.  CENTRE IS THE SPRING MISFIT, S(th)-K*th,')
    print('     WHICH IS ZERO AT th=0 BY CONSTRUCTION FOR ANY S AND ANY K.  The "454x span" is')
    print('     the span of a function that must vanish at the origin, divided by its own')
    print('     smallest bin.  It carries no information about whether S-K*th is a DEFICIT.')
