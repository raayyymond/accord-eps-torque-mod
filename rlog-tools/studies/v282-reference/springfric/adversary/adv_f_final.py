"""ATTACK F -- last two ways to kill the intercept, plus the angle-controlled F bracket.
F1  DC BIAS.  A constant in the VEHICLE frame (road crown, roll compensation, a reconstruction
    offset in cmd = -(p+i+f)/LAF) becomes +const for theta>0 and -const for theta<0 once you
    multiply by sign(theta).  A genuine position-odd term keeps the SAME SIGN on both sides.
    Split left and right.  Also fit a free vehicle-frame constant alongside and see if the
    position intercept survives it.
F2  LEAVE-ONE-ROUTE-OUT on the intercept, the slope and F.
F3  angle-CONTROLLED F at each sample instant (the pooled median of F is biased down because the
    away and toward sets sit at different |angle|).
F4  the delivered-surface consequence: what the intercept is worth as a fraction of the standing
    hold requirement at each angle, and what a MULTIPLICATIVE lever would have to do to serve it.
"""
import numpy as np
from adv_load import load, cols, PRE, BK, cluster_boot, hold_map

EP, W, P = load()
C = cols(EP)
N = len(EP); ar = np.arange(N)
g, v, sj, route = C['group'], C['v'], C['sjump'], C['route']
d0 = np.maximum(C['w_d0'].astype(int), 0); d1 = C['w_d1'].astype(int)
aa_pre = W['aa'][:, PRE]; sgn = np.sign(aa_pre); ath = np.abs(aa_pre)
tw = (sj == -sgn); sig = 1.0 - 2 * tw.astype(float)
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
LOW = TQ & (v >= 2) & (v < 8)
L = np.where(LOW)[0]
U = W['cmd'][ar, BK] * sgn
LEVEL = {r: (P[r].get('AccordHoldLevel', '0') == '1') for r in P}

print('=' * 98)
print('F1  DC-BIAS TEST.  split by the SIDE of centre.')
print(f"    {'side':>12s} {'n aw/tw':>9s} {'med|th|':>8s} {'intercept a':>12s} {'slope b':>10s} {'F':>9s}")
for tag, m in [('LEFT  th>0', L[sgn[L] > 0]), ('RIGHT th<0', L[sgn[L] < 0])]:
    X = np.vstack([np.ones(len(m)), ath[m], sig[m]]).T
    c = np.linalg.lstsq(X, U[m], rcond=None)[0]
    print(f'    {tag:>12s} {int((~tw[m]).sum()):4d}/{int(tw[m].sum()):<4d} {np.median(ath[m]):8.2f}'
          f' {c[0]:+12.5f} {c[1]:+10.5f} {c[2]:+9.5f}')
print('    a VEHICLE-FRAME DC bias gives intercepts of OPPOSITE sign on the two sides.')
print('    a POSITION-ODD term gives the SAME sign.')
print()
print('    joint fit with a free vehicle-frame constant:  U = a + d*sign(theta) + b|th| + F*sigma')
print('    (d is the vehicle-frame DC bias expressed in the outward-positive frame)')


def fitF1(ii):
    X = np.vstack([np.ones(len(ii)), sgn[ii], ath[ii], sig[ii]]).T
    c = np.linalg.lstsq(X, U[ii], rcond=None)[0]
    r = U[ii] - X @ c
    return np.array([c[0], c[1], c[2], c[3], float(np.sqrt(np.mean(r ** 2)))])


pt, lo, hi, bs = cluster_boot(lambda ii, rr: fitF1(ii), L, route[L], nb=2000, seed=41)
for i, n_ in enumerate(['a  position-odd', 'd  vehicle-frame DC', 'b  slope/deg', 'F', 'rms']):
    print(f'      {n_:20s} {pt[i]:+.5f}  CI [{lo[i]:+.5f}, {hi[i]:+.5f}]')
print(f'      P(a <= 0) = {np.mean(bs[:,0] <= 0):.3f}   P(|d| >= |a|) = {np.mean(np.abs(bs[:,1])>=np.abs(bs[:,0])):.3f}')
print(f"    left/right balance of the set: th>0 {int((sgn[L]>0).sum())} / th<0 {int((sgn[L]<0).sum())}")

print()
print('=' * 98)
print('F2  LEAVE-ONE-ROUTE-OUT')
print(f"    {'dropped':>24s} {'n':>4s} {'a':>9s} {'b':>9s} {'F':>9s}")
X = np.vstack([np.ones(len(L)), ath[L], sig[L]]).T
c0 = np.linalg.lstsq(X, U[L], rcond=None)[0]
print(f'    {"none (all 5)":>24s} {len(L):4d} {c0[0]:+9.5f} {c0[1]:+9.5f} {c0[2]:+9.5f}')
for r in sorted(set(route[L])):
    m = L[route[L] != r]
    X = np.vstack([np.ones(len(m)), ath[m], sig[m]]).T
    c = np.linalg.lstsq(X, U[m], rcond=None)[0]
    print(f'    {r:>24s} {len(m):4d} {c[0]:+9.5f} {c[1]:+9.5f} {c[2]:+9.5f}')

print()
print('=' * 98)
print('F3  ANGLE-CONTROLLED F at each sample instant (regression F, not the pooled median)')
print(f"    {'sample':>30s} {'a':>9s} {'b':>9s} {'F':>9s}")
for nm_, idx in [('dwell start (inside band)', d0), ('dwell mid', (d0 + d1) // 2),
                 ('dwell END = last stuck frame', d1), ('bk-23 (-200ms)', np.full(N, BK - 20)),
                 ('bk-13 (-100ms)', np.full(N, BK - 10)), ('bk-3 (the reported one)', np.full(N, BK)),
                 ('bk+0 (detection frame)', np.full(N, PRE))]:
    u = W['cmd'][ar, idx] * sgn
    X = np.vstack([np.ones(len(L)), ath[L], sig[L]]).T
    c = np.linalg.lstsq(X, u[L], rcond=None)[0]
    print(f'    {nm_:>30s} {c[0]:+9.5f} {c[1]:+9.5f} {c[2]:+9.5f}')
print('    NOTE the intercept a and slope b are STABLE from dwell start to breakaway while F')
print('    grows from ~0 to 0.033 -- exactly the band model: the command starts near the CENTRE')
print('    and travels to an EDGE.  The centre is NOT something the loop has to build during')
print('    the stick; it is already there when the stick begins.')

print()
print('=' * 98)
print('F4  what the intercept is worth, and what a MULTIPLICATIVE lever would have to do')
vmed = np.median(v[L])
sat = 19.3 + 546 * np.exp(-vmed / 3.01)
a, b = pt[0] + 0 * pt[1], None
X = np.vstack([np.ones(len(L)), ath[L], sig[L]]).T
cc = np.linalg.lstsq(X, U[L], rcond=None)[0]
a, b = cc[0], cc[1]
print(f'    at the median speed {vmed:.2f} m/s the fork hold map is k*sat*tanh(th/sat), sat={sat:.0f} deg')
print(f'    (tanh nonlinearity over 0-40 deg at this speed: '
      f'{100*(1-np.tanh(40/sat)/(40/sat)):.1f}% -- the map is LINEAR here, so a linear regressor')
print( '     is NOT mis-specified against it; possibility (3) as framed is quantitatively dead)')
print(f"    {'|th| deg':>9s} {'S = a+b|th|':>12s} {'intercept share':>16s} {'fork hold*1.15':>15s}"
      f" {'mult needed':>12s}")
for th in [0.5, 1, 2, 4, 8, 16, 32]:
    S = a + b * th
    h = float(hold_map(th, vmed, True))
    print(f'    {th:9.1f} {S:+12.4f} {100*a/S:15.0f}% {h:+15.4f} {S/h:11.2f}x')
print('    a k-schedule / HOLD_LEVEL / AccordEpsSpringScale is MULTIPLICATIVE in angle: one number')
print('    cannot serve a requirement whose multiplier runs 7x at 1 deg to 1.6x at 32 deg.')
print('    the hysteresis feedforward is in the MOTION frame and contributes ~0 to the centre')
print('    (measured z centre 0.000-0.004, z half-width 0.007-0.012 against a flown 0.015).')
