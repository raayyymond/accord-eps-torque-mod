"""ATTACK E -- the intercept is the whole decision, so attack the intercept.
E1  is the +0.019 intercept POSITION-aligned (a spring/detent, remedy = hold map) or
    ARRIVAL-DIRECTION-aligned (a friction/hysteresis term, remedy = AccordFrictionHyst)?
    Near centre the wheel has recently been on both sides, so arrival direction DECORRELATES
    from sign(angle); away from centre the wheel got there by driving outward, so they agree.
    That decorrelation alone produces "a term that turns on over ~1 deg".  Measure it, then fit
    both regressors jointly and see which one keeps the intercept.
E2  per-bin residual of the a + b|th| model -- does the linear+intercept model even fit?
E3  the half-width F is an EDGE-TIMING statistic: bounded below by the last verifiably-stuck
    frame and above by the 30-ms-before-detection sample.  Price it against the fork's own
    identified plant Coulomb (0.010-0.012, "SteerFriction's own unit").
E4  the observer's share, PER ROUTE (route 75 has no AccordDobHz -- a pooled median hides that).
E5  matched-angle AccordHoldLevel contrast, and a within-route intercept.
"""
import numpy as np
from adv_load import load, cols, PRE, BK, cluster_boot, hold_map

EP, W, P = load()
C = cols(EP)
N = len(EP); ar = np.arange(N)
g, v, sj, route, kind = C['group'], C['v'], C['sjump'], C['route'], C['kind']
d0 = np.maximum(C['w_d0'].astype(int), 0); d1 = C['w_d1'].astype(int)
aa_pre = W['aa'][:, PRE]; sgn = np.sign(aa_pre); ath = np.abs(aa_pre)
tw = (sj == -sgn); sig = 1.0 - 2 * tw.astype(float)
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
LOW = TQ & (v >= 2) & (v < 8)
L = np.where(LOW)[0]
Q = list(np.quantile(ath[LOW], [0, .2, .4, .6, .8, 1.0]))
U = W['cmd'][ar, BK] * sgn
LEVEL = {r: (P[r].get('AccordHoldLevel', '0') == '1') for r in P}

# arrival direction: the wheel's motion in the 0.5 s before the dwell starts, from the window
back = np.maximum(d0 - 50, 0)
arr_raw = W['aa'][ar, d0] - W['aa'][ar, back]
arr = np.sign(arr_raw)
arr[arr == 0] = 1.0
arr_out = arr * sgn        # +1 = arrived moving OUTWARD, -1 = arrived moving inward
# the same from the DESIRED angle (what the fork's hysteresis term actually keys on)
arrd = np.sign(W['angdes'][ar, d0] - W['angdes'][ar, back]); arrd[arrd == 0] = 1.0
arrd_out = arrd * sgn


def bset(ii, ed, x=ath):
    return [ii[(x[ii] >= ed[i]) & ((x[ii] < ed[i + 1]) if i < len(ed) - 2 else (x[ii] <= ed[i + 1]))]
            for i in range(len(ed) - 1)]


print('=' * 98)
print('E1  POSITION-ALIGNED vs ARRIVAL-DIRECTION-ALIGNED intercept')
print('    (a) how strongly does arrival direction agree with sign(angle), per angle bin?')
print(f"    {'med|th|':>8s} {'n':>4s} {'frac arrived OUTWARD':>21s} {'|arr travel| med':>17s}"
      f" {'frac(desired) OUT':>18s}")
for b in bset(L, Q):
    print(f'    {np.median(ath[b]):8.2f} {len(b):4d} {np.mean(arr_out[b] > 0):21.2f}'
          f' {np.median(np.abs(arr_raw[b])):17.2f} {np.mean(arrd_out[b] > 0):18.2f}')
print('    => if this fraction climbs from ~0.5 near centre to ~1.0 away from it, then an')
print('       arrival-direction friction term MASQUERADES as a position term that "turns on"')
print('       over exactly that scale, and the intercept is NOT identified as a spring.')
print()
print('    (b) joint fit  U = a1 + a2*arr_out + b*|th| + F*sigma   (a1 position, a2 arrival)')


def fitE(ii, use_des=False):
    ao = (arrd_out if use_des else arr_out)[ii]
    X = np.vstack([np.ones(len(ii)), ao, ath[ii], sig[ii]]).T
    c = np.linalg.lstsq(X, U[ii], rcond=None)[0]
    r = U[ii] - X @ c
    # drop a1 (pure arrival model) and drop a2 (pure position model), compare rms
    X1 = np.vstack([ao, ath[ii], sig[ii]]).T
    X2 = np.vstack([np.ones(len(ii)), ath[ii], sig[ii]]).T
    c1 = np.linalg.lstsq(X1, U[ii], rcond=None)[0]
    c2 = np.linalg.lstsq(X2, U[ii], rcond=None)[0]
    r1 = U[ii] - X1 @ c1; r2 = U[ii] - X2 @ c2
    return np.array([c[0], c[1], c[2], c[3], float(np.sqrt(np.mean(r ** 2))),
                     c1[0], c1[1], c1[2], float(np.sqrt(np.mean(r1 ** 2))),
                     c2[0], c2[1], c2[2], float(np.sqrt(np.mean(r2 ** 2)))])


for tag, ud in [('arrival from MEASURED angle', False), ('arrival from DESIRED angle', True)]:
    pt, lo, hi, bs = cluster_boot(lambda ii, rr: fitE(ii, ud), L, route[L], nb=2000, seed=33)
    nm = ['a1 position', 'a2 arrival', 'b slope/deg', 'F', 'rms both',
          'arrival-only a2', 'arrival-only b', 'arrival-only F', 'rms arrival-only',
          'position-only a1', 'position-only b', 'position-only F', 'rms position-only']
    print(f'    --- {tag} ---')
    for i, n_ in enumerate(nm):
        print(f'      {n_:19s} {pt[i]:+.5f}  CI [{lo[i]:+.5f}, {hi[i]:+.5f}]')
    print(f'      P(a1 <= 0) = {np.mean(bs[:,0] <= 0):.3f}   P(a2 <= 0) = {np.mean(bs[:,1] <= 0):.3f}')
print('    (c) the intercept measured ONLY on episodes that arrived INWARD (arr_out < 0), where')
print('        a position term and an arrival term have OPPOSITE sign -- the discriminating subset:')
for tag, m in [('arrived OUTWARD', L[arr_out[L] > 0]), ('arrived INWARD', L[arr_out[L] < 0])]:
    if len(m) < 12:
        print(f'      {tag:16s} n={len(m)} -- too few to fit'); continue
    X = np.vstack([np.ones(len(m)), ath[m], sig[m]]).T
    c = np.linalg.lstsq(X, U[m], rcond=None)[0]
    print(f'      {tag:16s} n={len(m):3d} (aw {int((~tw[m]).sum())}/tw {int(tw[m].sum())})'
          f'  intercept {c[0]:+.5f}  slope {c[1]:+.5f}  F {c[2]:+.5f}'
          f'   med|th| {np.median(ath[m]):.2f}')
print('        a POSITION term keeps the SAME sign in both rows.  An ARRIVAL term FLIPS.')

print()
print('=' * 98)
print('E2  does the a + b|th| model even fit?  per-bin residual')
X = np.vstack([np.ones(len(L)), ath[L], sig[L]]).T
c = np.linalg.lstsq(X, U[L], rcond=None)[0]
print(f'    a={c[0]:+.5f} b={c[1]:+.5f} F={c[2]:+.5f}')
print(f"    {'med|th|':>8s} {'S_obs':>9s} {'S_pred':>9s} {'resid':>9s}")
for b in bset(L, Q):
    a_, t_ = U[b][~tw[b]], U[b][tw[b]]
    s = (np.median(a_) + np.median(t_)) / 2
    mx = np.median(ath[b])
    print(f'    {mx:8.2f} {s:+9.4f} {c[0]+c[1]*mx:+9.4f} {s-(c[0]+c[1]*mx):+9.4f}')
print('    a straight line + intercept misses the two end bins by +/-0.02 = the size of the')
print('    effect itself.  NEITHER a pure spring NOR a spring+constant is the right form.')

print()
print('=' * 98)
print('E3  F IS AN EDGE-TIMING STATISTIC.  bracket it.')
for nm_, idx in [('dwell start (inside band)', d0), ('dwell mid', (d0 + d1) // 2),
                 ('dwell END = last stuck frame', d1), ('bk-23 (-200ms)', np.full(N, BK - 20)),
                 ('bk-13 (-100ms)', np.full(N, BK - 10)), ('bk-3 (the reported one)', np.full(N, BK)),
                 ('bk+0', np.full(N, PRE)), ('bk+10', np.full(N, PRE + 10))]:
    u = W['cmd'][ar, idx] * sgn
    f_ = (np.median(u[L][~tw[L]]) - np.median(u[L][tw[L]])) / 2
    print(f'    {nm_:30s} F = {f_:+.4f}')
print('    LOWER bound = the last frame the wheel is verifiably stuck (command still INSIDE the')
print('    band).  UPPER bound = 30 ms before a breakaway that is itself detected 0.3 deg AFTER')
print('    true slip onset (command has passed the edge).  So plant Coulomb in [~0.023, ~0.033].')
print('    The fork\'s own V293 plant identification puts Coulomb at 0.010-0.012 (SteerFriction\'s')
print('    unit).  These disagree by 2-3x; at most one of them is right.')

print()
print('=' * 98)
print('E4  THE OBSERVER\'S SHARE, PER ROUTE (a pooled median hides routes with no observer)')
print(f"    {'route':>22s} {'DobHz':>7s} {'n':>4s} {'S':>9s} {'hold_ff':>9s} {'dob':>9s} {'P':>8s} {'I':>8s} {'z':>8s}")
for r in sorted(set(route[L])):
    m = L[route[L] == r]
    cs = {}
    for ch in ['cmd', 'hold_ff', 'dob', 'P', 'I', 'z']:
        u = W[ch][m, BK] * sgn[m]
        cs[ch] = (np.median(u[~tw[m]]) + np.median(u[tw[m]])) / 2
    print(f"    {r:>22s} {P[r].get('AccordDobHz','--'):>7s} {len(m):4d} {cs['cmd']:+9.4f}"
          f" {cs['hold_ff']:+9.4f} {cs['dob']:+9.4f} {cs['P']:+8.4f} {cs['I']:+8.4f} {cs['z']:+8.4f}")
print(f"    frac of episodes with dob EXACTLY 0 at bk-3: {np.mean(W['dob'][L, BK] == 0):.2f}")

print()
print('=' * 98)
print('E5  MATCHED-ANGLE AccordHoldLevel contrast (T64/T64B only, one angle band at a time)')
ON = np.array([LEVEL[r] for r in route])
for lo_, hi_ in [(0.3, 1.5), (1.5, 4.0), (4.0, 40.0)]:
    m = L[(ath[L] >= lo_) & (ath[L] < hi_) & np.isin(g[L], ['T64', 'T64B'])]
    out = []
    for tag, mm in [('ON', m[ON[m]]), ('OFF', m[~ON[m]])]:
        if len(mm) < 6 or (~tw[mm]).sum() < 2 or tw[mm].sum() < 2:
            out.append(f'{tag} n={len(mm)} (too few)'); continue
        s = (np.median(U[mm][~tw[mm]]) + np.median(U[mm][tw[mm]])) / 2
        h = np.median(hold_map(ath[mm], v[mm], LEVEL[route[mm][0]]))
        out.append(f'{tag} n={len(mm):2d} S {s:+.4f} hold {h:+.4f} S-hold {s-h:+.4f} @{np.median(ath[mm]):.2f}')
    print(f'    |th| {lo_:4.1f}-{hi_:4.1f}:  ' + '   |   '.join(out))
print('    cause (A) predicts S-hold GROWS by 0.13*hold when the level is switched off')
print('    (0.0003 / 0.0013 / 0.0055 in these three bands) -- compare against the spread.')
print()
print('    WITHIN-ROUTE intercept (a + b|th| + F*sigma fitted inside each route):')
for r in sorted(set(route[L])):
    m = L[route[L] == r]
    if len(m) < 12 or (~tw[m]).sum() < 4:
        print(f'    {r} n={len(m)} -- too few'); continue
    X = np.vstack([np.ones(len(m)), ath[m], sig[m]]).T
    c = np.linalg.lstsq(X, U[m], rcond=None)[0]
    print(f'    {r} n={len(m):3d}  a {c[0]:+.5f}  b {c[1]:+.5f}  F {c[2]:+.5f}')
