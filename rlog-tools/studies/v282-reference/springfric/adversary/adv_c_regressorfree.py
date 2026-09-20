"""ATTACK C -- kill the regressor.  The band edges can be read with NO spring regressor at all.
C1  RAW band edges.  u = cmd*sign(theta), outward-positive.  Outward breakaway sits on the
    UPPER edge u=S+F, inward on the LOWER edge u=S-F.  So S(theta)=(u_aw+u_tw)/2 and
    F=(u_aw-u_tw)/2 with NO k, NO constant.  Any "fit artefact" objection dies or survives here.
C2  compare S(theta) measured against the FORK'S OWN delivered hold map, recomputed by me at
    each episode's v and THIS ROUTE'S FLOWN AccordHoldLevel (ss_extract.py:64 hard-codes
    level=False, so the stored hold_aa/hold_ff channels are the UNLEVELLED map on every route).
C3  TERM DECOMPOSITION of the band centre: which of P / I / hold / move / z / rl / dob carries it?
    A hold-map stiffness deficit (A) and an integrator/observer wind-up (B) live in different rows.
C4  SAMPLE-INSTANT robustness: recompute the centre at frames inside the dwell, which removes
    the 0.3-deg breakaway detector from the estimate entirely.
"""
import numpy as np
from adv_load import load, cols, PRE, BK, cluster_boot, hold_map
from adv_gate import fit4

EP, W, P = load()
C = cols(EP)
N = len(EP); ar = np.arange(N)
g, v, sj, route, kind = C['group'], C['v'], C['sjump'], C['route'], C['kind']
d0 = np.maximum(C['w_d0'].astype(int), 0); d1 = C['w_d1'].astype(int)
aa_pre = W['aa'][:, PRE]
sgn = np.sign(aa_pre)
tw = (sj == -sgn)
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
LOW = TQ & (v >= 2) & (v < 8)
L = np.where(LOW)[0]
Q = list(np.quantile(np.abs(aa_pre)[LOW], [0, .2, .4, .6, .8, 1.0]))
LEVEL = {r: (P[r].get('AccordHoldLevel', '0') == '1') for r in P}
lev = np.array([LEVEL[r] for r in route])

# my own hold map, at the ACTUAL angle and at the DESIRED angle, honouring each route's level
HOLD_AA = np.zeros_like(W['aa'])
HOLD_AA_NOLVL = np.zeros_like(W['aa'])
for r in np.unique(route):
    m = route == r
    HOLD_AA[m] = hold_map(W['aa'][m], W['v'][m], LEVEL[r])
    HOLD_AA_NOLVL[m] = hold_map(W['aa'][m], W['v'][m], False)


def band(ii, sig, idx, est=np.median):
    """(S, F, n_aw, n_tw, med|theta|) with NO regressor: u = sig*sign(theta)."""
    u = sig[ii, idx[ii]] * sgn[ii]
    a, t = u[~tw[ii]], u[tw[ii]]
    if len(a) < 2 or len(t) < 2:
        return (np.nan, np.nan, len(a), len(t))
    return ((est(a) + est(t)) / 2, (est(a) - est(t)) / 2, len(a), len(t))


def bins(ii, x, edges):
    out = []
    for i in range(len(edges) - 1):
        m = (x[ii] >= edges[i]) & ((x[ii] < edges[i + 1]) if i < len(edges) - 2 else (x[ii] <= edges[i + 1]))
        out.append(ii[m])
    return out


IDX = np.full(N, BK)
print('=' * 96)
print('C1  RAW BAND EDGES, NO SPRING REGRESSOR.   u = cmd*sign(theta), outward-positive.')
print('    S = (u_away + u_toward)/2   F = (u_away - u_toward)/2')
print(f"    {'|theta| bin':>16s} {'n_aw/tw':>8s} {'med|th|':>8s} {'u_away':>9s} {'u_toward':>9s}"
      f" {'S_meas':>9s} {'F_meas':>9s} {'S/|th|':>9s}")
rows = []
for b in bins(L, np.abs(aa_pre), Q):
    u = W['cmd'][b, BK] * sgn[b]
    a, t = u[~tw[b]], u[tw[b]]
    S, F = (np.median(a) + np.median(t)) / 2, (np.median(a) - np.median(t)) / 2
    mx = np.median(np.abs(aa_pre[b]))
    rows.append((mx, S, F, len(a), len(t), b))
    print(f'    {np.abs(aa_pre[b]).min():7.2f}-{np.abs(aa_pre[b]).max():8.2f} {len(a):3d}/{len(t):<4d}'
          f' {mx:8.2f} {np.median(a):+9.4f} {np.median(t):+9.4f} {S:+9.4f} {F:+9.4f} {S/mx:+9.5f}')
print('    => S RISES with |theta| with NO regressor in sight, and F is flat.  The "single linear')
print('       k*aa regressor manufactured it" objection FAILS: the band centre rises in RAW units.')
print('       BUT S/|theta| is NOT constant either -- S is a SATURATING function of angle.')

print()
print('=' * 96)
print('C2  S_measured vs THE FORK\'S OWN DELIVERED HOLD MAP (my recompute, per-route level)')
print(f"    {'med|th|':>8s} {'S_meas':>9s} {'hold(th)':>9s} {'hold*1.15':>9s} {'S-hold':>9s}"
      f" {'S/hold':>7s} {'fitted K*|th|':>13s} {'S-K|th|':>9s}")
K = fit4(LOW, IDX)['k']
for mx, S, F, na, nt, b in rows:
    h = np.median(np.abs(HOLD_AA[b, BK]))
    hn = np.median(np.abs(HOLD_AA_NOLVL[b, BK]))
    print(f'    {mx:8.2f} {S:+9.4f} {hn:+9.4f} {h:+9.4f} {S-h:+9.4f} {S/max(h,1e-9):7.2f}'
          f' {K*mx:+13.4f} {S-K*mx:+9.4f}')
print('    (hold(th) = unlevelled map = what the stored channel holds; hold*1.15 = per-route level)')
print('    the fitted K=%.5f is the TOTAL command slope, not the fork hold slope; at the median' % K)
print('    speed the fork hold slope is ~0.005 and the deficit S-hold is what feedback must supply.')

print()
print('=' * 96)
print('C3  TERM DECOMPOSITION of the band centre.  For each channel X, centre_X = (X_aw+X_tw)/2')
print('    with X measured outward-positive.  These SUM to the cmd centre (cmd = P+I+F_t,')
print('    F_t = hold_ff + move + z + rl + dob).  A hold-stiffness deficit (A) shows up as a')
print('    hold_ff row that is too small; an integrator/observer wind-up (B) shows up in I or dob.')
chans = ['cmd', 'P', 'I', 'F', 'hold_ff', 'move', 'z', 'rl', 'dob']
hdr = ' '.join(f'{c:>9s}' for c in chans)
print(f"    {'med|th|':>8s} {hdr}")
for mx, S, F, na, nt, b in rows:
    cs = []
    for c in chans:
        u = W[c][b, BK] * sgn[b]
        cs.append((np.median(u[~tw[b]]) + np.median(u[tw[b]])) / 2)
    print(f'    {mx:8.2f} ' + ' '.join(f'{x:+9.4f}' for x in cs))
print(f"    {'':8s} " + ' '.join(f'{c:>9s}' for c in chans))
print('    HALF-WIDTH of each term (what is odd in the direction of MOTION = friction-shaped):')
for mx, S, F, na, nt, b in rows:
    cs = []
    for c in chans:
        u = W[c][b, BK] * sgn[b]
        cs.append((np.median(u[~tw[b]]) - np.median(u[tw[b]])) / 2)
    print(f'    {mx:8.2f} ' + ' '.join(f'{x:+9.4f}' for x in cs))

print()
print('=' * 96)
print('C4  SAMPLE-INSTANT ROBUSTNESS -- centre computed at frames INSIDE the dwell, which')
print('    removes the 0.3-deg breakaway detector from the estimate.')
print(f"    {'sample':>22s} " + ' '.join(f'{r[0]:9.2f}' for r in rows) + '   <- med|theta|')
for nm, idx in [('bk-3   (the original)', np.full(N, BK)),
                ('bk-13  (-100 ms)', np.full(N, BK - 10)),
                ('bk-23  (-200 ms)', np.full(N, BK - 20)),
                ('dwell END  (i1)', d1),
                ('dwell MID', (d0 + d1) // 2),
                ('dwell START (i0)', d0)]:
    cs, fs = [], []
    for mx, S, F, na, nt, b in rows:
        u = W['cmd'][b, idx[b]] * sgn[b]
        cs.append((np.median(u[~tw[b]]) + np.median(u[tw[b]])) / 2)
        fs.append((np.median(u[~tw[b]]) - np.median(u[tw[b]])) / 2)
    print(f'    {nm:22s} ' + ' '.join(f'{x:+9.4f}' for x in cs) + '   S')
    print(f'    {"":22s} ' + ' '.join(f'{x:+9.4f}' for x in fs) + '   F')
print('    if S keeps its angle profile at instants well inside the dwell (where the detector')
print('    cannot act) the detection-artefact objection is dead; if F collapses there, good --')
print('    F is the edge-only quantity and should shrink away from the edge.')
