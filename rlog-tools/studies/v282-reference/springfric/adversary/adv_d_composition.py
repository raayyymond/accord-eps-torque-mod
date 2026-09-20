"""ATTACK D -- composition, config, and winding.
D1  HISTORY-CLASS COMPOSITION.  The orchestrator's own crux (c) measured a 0.073 spread in the
    dwell-start command level across kind (cont +0.026 / rest -0.006 / rev -0.047) = 2.19x the
    half-width.  If the away and toward sets have different kind mixes, and the mix drifts with
    |angle|, that spread alone can manufacture the whole centre profile.  Census it, then
    recompute the profile WITHIN each kind and with the mix REWEIGHTED.
D2  the LINEAR/INTERCEPT split of the raw band centre S(theta), with clustered CI.  The fork's own
    HONDA_ACCORD_HOLD_STATIC_FRICTION = 0.020 is "the intercept the map was fitted WITHOUT".
D3  CONFIG: per-route profiles; the AccordHoldLevel natural experiment on the RAW centre;
    SteerFriction 0.212 vs 0.0 (two of the five torque routes silently ran stock 0.212).
D4  WINDING through the dwell, per term: does I or dob GROW during the stick (cause B) or is the
    centre already there at dwell start (no winding to blame)?
"""
import numpy as np
from adv_load import load, cols, PRE, BK, cluster_boot, hold_map
from adv_gate import fit4

EP, W, P = load()
C = cols(EP)
N = len(EP); ar = np.arange(N)
g, v, sj, route, kind = C['group'], C['v'], C['sjump'], C['route'], C['kind']
d0 = np.maximum(C['w_d0'].astype(int), 0); d1 = C['w_d1'].astype(int)
aa_pre = W['aa'][:, PRE]; sgn = np.sign(aa_pre); ath = np.abs(aa_pre)
tw = (sj == -sgn)
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
LOW = TQ & (v >= 2) & (v < 8)
L = np.where(LOW)[0]
Q = list(np.quantile(ath[LOW], [0, .2, .4, .6, .8, 1.0]))
U = W['cmd'][ar, BK] * sgn                      # raw outward-positive command at the edge
LEVEL = {r: (P[r].get('AccordHoldLevel', '0') == '1') for r in P}
SF = {r: float(P[r].get('SteerFriction', 'nan')) for r in P}


def binsets(ii, x=ath, ed=None):
    ed = Q if ed is None else ed
    return [ii[(x[ii] >= ed[i]) & ((x[ii] < ed[i + 1]) if i < len(ed) - 2 else (x[ii] <= ed[i + 1]))]
            for i in range(len(ed) - 1)]


def SF_(b, u=None):
    u = U if u is None else u
    a, t = u[b][~tw[b]], u[b][tw[b]]
    if len(a) < 2 or len(t) < 2:
        return np.nan, np.nan, len(a), len(t)
    return (np.median(a) + np.median(t)) / 2, (np.median(a) - np.median(t)) / 2, len(a), len(t)


print('=' * 98)
print('D1  HISTORY-CLASS COMPOSITION')
print('    (a) kind mix, AWAY vs TOWARD, per angle bin  (fractions cont/rest/rev)')
print(f"    {'bin med|th|':>12s} {'AWAY n':>7s} {'cont/rest/rev':>20s}   {'TOW n':>6s} {'cont/rest/rev':>20s}")
for b in binsets(L):
    a, t = b[~tw[b]], b[tw[b]]
    fa = [np.mean(kind[a] == k) for k in ['cont', 'rest', 'rev']]
    ft = [np.mean(kind[t] == k) for k in ['cont', 'rest', 'rev']]
    print(f'    {np.median(ath[b]):12.2f} {len(a):7d} {fa[0]:6.2f}/{fa[1]:5.2f}/{fa[2]:5.2f}      '
          f'{len(t):6d} {ft[0]:6.2f}/{ft[1]:5.2f}/{ft[2]:5.2f}')
print('    (b) the raw outward command U at the edge, by kind (pooled 2-8):')
for k in ['cont', 'rest', 'rev']:
    m = L[kind[L] == k]
    a, t = m[~tw[m]], m[tw[m]]
    print(f'        {k:5s} n {len(m):3d} (aw {len(a):2d}/tw {len(t):2d})  U_away {np.median(U[a]):+.4f}'
          f'  U_toward {np.median(U[t]):+.4f}   S {SF_(m)[0]:+.4f}  F {SF_(m)[1]:+.4f}'
          f'   med|th| aw {np.median(ath[a]):5.2f} tw {np.median(ath[t]):5.2f}')
print('    (c) the profile WITHIN each kind (3 angle terciles inside the kind):')
for k in ['cont', 'rest', 'rev']:
    m = L[kind[L] == k]
    ed = list(np.quantile(ath[m], [0, 1 / 3, 2 / 3, 1.0]))
    out = []
    for b in binsets(m, ed=ed):
        s, f, na, nt = SF_(b)
        out.append(f'{s:+.4f}@{np.median(ath[b]):.2f}(n{na}/{nt})')
    print(f'        {k:5s} S: ' + '  '.join(out))
print('    (d) MIX-REWEIGHTED profile: within each angle bin, compute S separately for each kind')
print('        present on BOTH sides and average with the POOLED kind weights (removes the mix drift)')
wk = {k: np.mean(kind[L] == k) for k in ['cont', 'rest', 'rev']}
print(f'        pooled kind weights {dict((k, round(x,3)) for k, x in wk.items())}')
for b in binsets(L):
    num, den, parts = 0.0, 0.0, []
    for k in ['cont', 'rest', 'rev']:
        bb = b[kind[b] == k]
        a, t = bb[~tw[bb]], bb[tw[bb]]
        if len(a) >= 1 and len(t) >= 1:
            s = (np.median(U[a]) + np.median(U[t])) / 2
            num += wk[k] * s; den += wk[k]; parts.append(f'{k[:2]}{s:+.3f}')
    print(f'        med|th| {np.median(ath[b]):6.2f}  S_raw {SF_(b)[0]:+.4f}   S_reweighted '
          f'{num/den if den else np.nan:+.4f}   [{" ".join(parts)}]  (weight covered {den:.2f})')

print()
print('=' * 98)
print('D2  INTERCEPT vs SLOPE of the raw band centre S(theta), clustered CI.')
print('    model  U = (a + b*|th|)  + F*sigma   fitted on the raw edges, sigma = +1 away / -1 toward')


def fit_ab(ii, rr=None):
    x = ath[ii]; s = 1.0 - 2 * tw[ii].astype(float)
    X = np.vstack([np.ones(len(ii)), x, s]).T
    c = np.linalg.lstsq(X, U[ii], rcond=None)[0]
    # and the same with a saturating spring instead of a linear one (fork sat at the median v)
    satv = 19.3 + 546 * np.exp(-np.median(v[ii]) / 3.01)
    X2 = np.vstack([np.ones(len(ii)), satv * np.tanh(x / satv), s]).T
    c2 = np.linalg.lstsq(X2, U[ii], rcond=None)[0]
    # and with NO intercept (pure spring through the origin)
    X3 = np.vstack([x, s]).T
    c3 = np.linalg.lstsq(X3, U[ii], rcond=None)[0]
    r1 = U[ii] - X @ c; r3 = U[ii] - X3 @ c3
    return np.array([c[0], c[1], c[2], c2[0], c2[1], c2[2], c3[0], c3[1],
                     float(np.sqrt(np.mean(r1 ** 2))), float(np.sqrt(np.mean(r3 ** 2)))])


pt, lo, hi, bs = cluster_boot(lambda ii, rr: fit_ab(ii), L, route[L], nb=2000, seed=21)
nm = ['intercept a', 'slope b /deg', 'F', 'sat: a', 'sat: k', 'sat: F',
      'no-intercept b', 'no-intercept F', 'rms with a', 'rms without a']
for i, n_ in enumerate(nm):
    print(f'    {n_:16s} {pt[i]:+.5f}  CI [{lo[i]:+.5f}, {hi[i]:+.5f}]')
print(f"    P(intercept <= 0) = {np.mean(bs[:,0] <= 0):.3f}      "
      f"fork HONDA_ACCORD_HOLD_STATIC_FRICTION = 0.020")
print('    => if the intercept is a real, nonzero, ANGLE-INDEPENDENT term, the remedy is NOT a k')
print('       schedule / HOLD_LEVEL / EpsSpringScale -- all three are MULTIPLICATIVE in angle and')
print('       cannot produce an intercept.')

print()
print('=' * 98)
print('D3  CONFIG.  per-route flown params and per-route raw band centre')
print(f"    {'route':>22s} {'grp':>5s} {'lvl':>4s} {'SteerFric':>10s} {'FricHyst':>9s} {'n aw/tw':>9s}"
      f" {'S_lo':>8s} {'S_hi':>8s} {'F':>8s} {'th_lo':>6s} {'th_hi':>6s}")
for r in sorted(set(route[L])):
    m = L[route[L] == r]
    med = np.median(ath[m])
    blo, bhi = m[ath[m] < med], m[ath[m] >= med]
    s1 = SF_(blo)[0]; s2 = SF_(bhi)[0]; f_ = SF_(m)[1]
    print(f'    {r:>22s} {g[m][0]:>5s} {str(int(LEVEL[r])):>4s} {SF[r]:10.4f}'
          f" {P[r].get('AccordFrictionHyst','--'):>9s} {int((~tw[m]).sum()):4d}/{int(tw[m].sum()):<4d}"
          f' {s1:+8.4f} {s2:+8.4f} {f_:+8.4f} {np.median(ath[blo]):6.2f} {np.median(ath[bhi]):6.2f}')
print('    (S_lo / S_hi = raw band centre below / above that route\'s own median |angle|)')
print()
print('    AccordHoldLevel NATURAL EXPERIMENT, restricted to the SAME fork rev (T64/T64B only):')
ON = L[np.isin(route[L], [r for r in set(route[L]) if LEVEL[r]]) & np.isin(g[L], ['T64', 'T64B'])]
OFF = L[(~np.isin(route[L], [r for r in set(route[L]) if LEVEL[r]])) & np.isin(g[L], ['T64', 'T64B'])]
for tag, ii in [('LEVEL ON  (6c,6d)', ON), ('LEVEL OFF (6e)', OFF)]:
    ed = list(np.quantile(ath[ii], [0, .5, 1.0]))
    out = []
    for b in binsets(ii, ed=ed):
        s, f_, na, nt = SF_(b)
        h = np.median(hold_map(ath[b], v[b], LEVEL[route[b][0]]))
        out.append(f'S {s:+.4f} hold {h:+.4f} S-hold {s-h:+.4f} @{np.median(ath[b]):.2f} (n{na}/{nt})')
    print(f'      {tag:18s} n={len(ii):3d}  ' + '   |   '.join(out))
print('      the 1.15x level removes ~13% of the hold map below 12.5 m/s.  Predicted move in')
print('      S-hold if cause (A): the DEFICIT should GROW by 0.15*hold when the level is off')
print('      (i.e. ~0.0006 at 1 deg, ~0.006 at 8 deg) -- a change far below the route scatter below.')
print()
print('    SteerFriction split (0.212 stock vs 0.0 declared):')
for tag, want in [('SteerFriction 0.212', 0.212), ('SteerFriction 0.0', 0.0)]:
    ii = L[np.array([abs(SF[r] - want) < 1e-3 for r in route[L]])]
    ed = list(np.quantile(ath[ii], [0, .5, 1.0]))
    out = []
    for b in binsets(ii, ed=ed):
        s, f_, na, nt = SF_(b)
        out.append(f'S {s:+.4f} F {f_:+.4f} @{np.median(ath[b]):.2f} (n{na}/{nt})')
    print(f'      {tag:20s} n={len(ii):3d}  ' + '   |   '.join(out))

print()
print('=' * 98)
print('D4  WINDING THROUGH THE DWELL, per term.  change = (X[bk-3] - X[dwell start]) * sign(theta),')
print('    averaged over away and toward the same way the centre is (so it is the centre\'s growth).')
chans = ['cmd', 'P', 'I', 'hold_ff', 'move', 'z', 'rl', 'dob']
print(f"    {'med|th|':>8s} {'dwell_s':>8s} " + ' '.join(f'{c:>8s}' for c in chans))
for b in binsets(L):
    outs = []
    for c in chans:
        d = (W[c][b, BK] - W[c][b, d0[b]]) * sgn[b]
        a, t = d[~tw[b]], d[tw[b]]
        outs.append((np.median(a) + np.median(t)) / 2)
    print(f'    {np.median(ath[b]):8.2f} {np.median(C["dwell_s"][b]):8.2f} '
          + ' '.join(f'{x:+8.4f}' for x in outs))
print('    and the LEVEL each term already had at dwell start (centre-aligned):')
for b in binsets(L):
    outs = []
    for c in chans:
        d = W[c][b, d0[b]] * sgn[b]
        a, t = d[~tw[b]], d[tw[b]]
        outs.append((np.median(a) + np.median(t)) / 2)
    print(f'    {np.median(ath[b]):8.2f} {"":8s} ' + ' '.join(f'{x:+8.4f}' for x in outs))
