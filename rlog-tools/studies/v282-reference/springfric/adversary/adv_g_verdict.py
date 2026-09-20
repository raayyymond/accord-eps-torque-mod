"""ATTACK G -- the verdict numbers.  Two things this pass established that change the finding:
G1  the INTERCEPT/SLOPE SPLIT IS NOT IDENTIFIED.  The "+0.019 intercept" is what a straight line
    does when it is fitted over a 130x angle range to a shape that is not a straight line.  Over
    the window where 2/3 of the episodes live (|aa| < 3 deg) the intercept is ZERO and the slope
    TRIPLES.  Report the non-parametric shape instead.
G2  the non-parametric requirement S(theta) against the fork's own delivered hold map: the
    SHORTFALL RATIO FALLS from ~6x at 1 deg to ~1.9x at 9 deg, i.e. the deficit is worst, in
    relative terms, at SMALL angle.  A multiplicative lever cannot serve that.
G3  who carries the standing deficit, per route: on the one route with no observer the
    INTEGRATOR carries it; on the observer routes the OBSERVER does and I stays small.
"""
import numpy as np
from adv_load import load, cols, PRE, BK, cluster_boot, hold_map

EP, W, P = load()
C = cols(EP); N = len(EP); ar = np.arange(N)
g, v, sj, route = C['group'], C['v'], C['sjump'], C['route']
aap = W['aa'][:, PRE]; sgn = np.sign(aap); ath = np.abs(aap)
tw = (sj == -sgn); sig = 1.0 - 2 * tw.astype(float)
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4']); LOW = TQ & (v >= 2) & (v < 8)
U = W['cmd'][ar, BK] * sgn


def ab(ii):
    X = np.vstack([np.ones(len(ii)), ath[ii], sig[ii]]).T
    return np.linalg.lstsq(X, U[ii], rcond=None)[0]


print('=' * 100)
print('G1  THE INTERCEPT/SLOPE SPLIT IS NOT IDENTIFIED -- it is entirely a function of the')
print('    angle window the line is fitted over.')
print(f"    {'window (deg)':>14s} {'n':>4s} {'intercept a':>26s} {'P(a<=0)':>8s} {'slope b /deg':>24s} {'F':>9s}")
for lo_, hi_ in [(0.0, 40.), (0.3, 40.), (0.3, 6.), (0.3, 4.), (0.3, 3.), (0.0, 3.), (0.0, 2.)]:
    m = np.where(LOW & (ath >= lo_) & (ath < hi_))[0]
    pt, l, h, bs = cluster_boot(lambda ii, rr: ab(ii), m, route[m], nb=1500, seed=77)
    print(f'    {lo_:5.1f}-{hi_:6.1f} {len(m):5d} {pt[0]:+9.5f} [{l[0]:+8.5f},{h[0]:+8.5f}]'
          f' {np.mean(bs[:,0]<=0):8.3f} {pt[1]:+9.5f} [{l[1]:+8.5f},{h[1]:+8.5f}] {pt[2]:+9.5f}')
print('    => the +0.019 intercept and the +0.0055/deg slope are ONE parameterisation of the same')
print('       curve; over |aa|<3 deg (95 of 145 episodes) the intercept is 0.000 and the slope is')
print('       0.0168/deg.  Neither number is a property of the car on its own.')

print()
print('=' * 100)
print('G2  NON-PARAMETRIC requirement S(theta) vs the fork\'s delivered hold map (no functional form)')
print(f"    {'window':>12s} {'n aw/tw':>9s} {'med|th|':>8s} {'S (CI)':>30s} {'fork hold':>10s}"
      f" {'S-hold':>8s} {'S/hold':>7s}")


def Sof(ii, rr=None):
    a, t = U[ii][~tw[ii]], U[ii][tw[ii]]
    return np.nan if (len(a) < 2 or len(t) < 2) else (np.median(a) + np.median(t)) / 2


for lo_, hi_ in [(0.0, 0.6), (0.6, 1.5), (1.5, 3.0), (3.0, 6.0), (6.0, 40.0)]:
    m = np.where(LOW & (ath >= lo_) & (ath < hi_))[0]
    pt, l, h, bs = cluster_boot(Sof, m, route[m], nb=1500, seed=88)
    hm = float(np.median(hold_map(ath[m], v[m], True)))
    print(f'    {lo_:4.1f}-{hi_:5.1f} {int((~tw[m]).sum()):4d}/{int(tw[m].sum()):<4d} {np.median(ath[m]):8.2f}'
          f' {pt[0]:+9.4f} [{l[0]:+8.4f},{h[0]:+8.4f}] {hm:+10.4f} {pt[0]-hm:+8.4f}'
          f' {pt[0]/max(hm,1e-9):6.2f}x')
print('    the SHORTFALL RATIO falls 6.0x -> 1.9x as angle grows, and the ABSOLUTE shortfall runs')
print('    -0.001 / +0.022 / +0.032 / +0.032 / +0.042.  A lever that is multiplicative in angle,')
print('    sized on the 9-deg shortfall, delivers 0.005 at 1 deg where 0.022 is needed (4.6x short);')
print('    sized on the 1-deg shortfall it delivers 0.19 at 9 deg where 0.042 is needed (4.6x over).')

print()
print('=' * 100
      )
print('G3  WHO CARRIES THE STANDING DEFICIT, per route (centre-aligned level at bk-3)')
print(f"    {'route':>22s} {'DobHz':>6s} {'Ki':>5s} {'n':>4s} {'S':>8s} {'hold_ff':>8s} {'dob':>8s}"
      f" {'I':>8s} {'P':>8s} {'ff share':>9s} {'slow-int share':>15s}")
L = np.where(LOW)[0]
for r in sorted(set(route[L])):
    m = L[route[L] == r]
    cs = {}
    for ch in ['cmd', 'hold_ff', 'dob', 'P', 'I']:
        u = W[ch][m, BK] * sgn[m]
        cs[ch] = (np.median(u[~tw[m]]) + np.median(u[tw[m]])) / 2
    S = cs['cmd']
    print(f"    {r:>22s} {P[r].get('AccordDobHz','--'):>6s} {P[r].get('AccordTorqueKi','0.30'):>5s}"
          f" {len(m):4d} {S:+8.4f} {cs['hold_ff']:+8.4f} {cs['dob']:+8.4f} {cs['I']:+8.4f}"
          f" {cs['P']:+8.4f} {100*cs['hold_ff']/S:8.0f}% {100*(cs['dob']+cs['I'])/S:14.0f}%")
print('    route 75 is the ONE route with no AccordDobHz: its I is 0.0178, 5-10x the I on every')
print('    observer route (0.0015-0.0038), and its dob is exactly 0.  The deficit is carried by')
print('    whichever slow integrating element is enabled -- that is a measured substitution.')
print()
print('    and NOTHING winds during the stick: through a 0.4-0.5 s dwell the centre-aligned change')
print('    is I +0.0002..+0.0014 and dob +0.0000..+0.0031, against a centre of 0.018-0.089.')
print('    The intercept and slope of the band centre are STABLE from dwell start to breakaway')
print('    (a 0.0237 -> 0.0190, b 0.00568 -> 0.00546) while F grows -0.0006 -> +0.0332.')
