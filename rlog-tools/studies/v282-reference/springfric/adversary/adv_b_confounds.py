"""ATTACK B -- the mechanisms that can MANUFACTURE the profile.
B1  SIGN DEGENERACY.  `toward` and the y sign both come from sign(aa[PRE]), a 0.1-deg-LSB
    signal whose median |value| in bin 1 is 3 LSB.  Algebra: a fraction p of mislabelled
    episodes gives CENTRE_obs = CENTRE_true*(1-2p) and leaves HALF-WIDTH EXACTLY UNCHANGED.
    That is the observed pattern.  Test with signs taken from cleaner estimators.
B2  SPEED CONFOUND.  one K over 2-8 m/s while the fork's own k(v) spans 0.0021->0.0052
    (x2.5) and the plant spring is itself speed-dependent.  Bin by SPEED; bin by angle
    WITHIN a speed band; check corr(|aa|,v).
B3  DETECTION ASYMMETRY per angle bin: frames from dwell end to the 0.3-deg breakaway,
    away vs toward.  If outward detection lags more at large angle, the command has more
    time to grow and the profile is a detector artefact.
B4  ANGLE-SENSOR / OFFSET floor: how many episodes sit inside a plausible offset error.
"""
import numpy as np
from adv_load import load, cols, PRE, BK, cluster_boot
from adv_gate import fit4

EP, W, P = load()
C = cols(EP)
N = len(EP); ar = np.arange(N)
g, v, sj, route, kind = C['group'], C['v'], C['sjump'], C['route'], C['kind']
d0 = np.maximum(C['w_d0'].astype(int), 0); d1 = C['w_d1'].astype(int)
aa_pre = W['aa'][:, PRE]
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
LOW = TQ & (v >= 2) & (v < 8)
f0 = fit4(LOW, np.full(N, BK)); K, Cc = f0['k'], f0['const']
L = np.where(LOW)[0]
R = W['cmd'][ar, BK] - K * W['aa'][ar, BK] - Cc


def dwell_mean_aa(i):
    return float(np.mean(W['aa'][i, d0[i]:d1[i] + 1]))


aa_dw = np.array([dwell_mean_aa(i) for i in range(N)])
aa_des = W['angdes'][ar, PRE]
aa_dwdes = np.array([float(np.mean(W['angdes'][i, d0[i]:d1[i] + 1])) for i in range(N)])


def profile(ii, sgn, xabs, edges, est=np.median):
    """CENTRE/HW using an arbitrary outward-sign definition sgn (global array)."""
    yy = R[ii] * sgn[ii]
    tw = (sj[ii] == -sgn[ii])
    x = xabs[ii]
    out = []
    for i in range(len(edges) - 1):
        m = (x >= edges[i]) & ((x < edges[i + 1]) if i < len(edges) - 2 else (x <= edges[i + 1]))
        ma, mt = m & ~tw, m & tw
        if ma.sum() < 2 or mt.sum() < 2:
            out.append((np.nan, np.nan, int(ma.sum()), int(mt.sum()), np.nan)); continue
        a_, t_ = est(yy[ma]), est(yy[mt])
        out.append(((a_ + t_) / 2, (a_ - t_) / 2, int(ma.sum()), int(mt.sum()), float(np.median(x[m]))))
    return out


def show(tag, rows):
    print(f'    {tag:34s} CENTRE ' + ' '.join(f'{r[0]:+.4f}' for r in rows)
          + '  | HW ' + ' '.join(f'{r[1]:+.4f}' for r in rows))
    print(f'    {"":34s} med|x| ' + ' '.join(f'{r[4]:7.2f}' for r in rows)
          + '  | n ' + ' '.join(f'{r[2]}/{r[3]}' for r in rows))


Q = list(np.quantile(np.abs(aa_pre)[LOW], [0, .2, .4, .6, .8, 1.0]))
print('=' * 92)
print('B1  SIGN DEGENERACY  --  the same sign(aa[PRE]) defines BOTH the y sign and toward/away.')
print('    algebra: mislabel fraction p  =>  CENTRE_obs = CENTRE_true*(1-2p),  HW unchanged.')
print('    bin1 shows CENTRE ~0 with HW FULLY PRESERVED (+0.0336) -- the contamination signature.')
print()
print('    (a) how noisy is the sign?  |aa[PRE]| in LSB (0.1 deg) for the 2-8 torque set:')
apre = np.abs(aa_pre[L])
for thr in [0.05, 0.1, 0.2, 0.3, 0.5, 0.63]:
    print(f'        |aa| <= {thr:4.2f} deg ({thr/0.1:3.1f} LSB): {int((apre<=thr).sum()):3d} of {len(L)}'
          f'  ({100*(apre<=thr).mean():4.1f}%)')
print(f'        disagreement sign(aa[PRE]) vs sign(dwell-mean aa): '
      f'{int((np.sign(aa_pre[L])!=np.sign(aa_dw[L])).sum())} of {len(L)}')
print(f'        disagreement sign(aa[PRE]) vs sign(angdes[PRE]):   '
      f'{int((np.sign(aa_pre[L])!=np.sign(aa_des[L])).sum())} of {len(L)}')
print()
print('    (b) the profile under different outward-sign definitions, SAME quintile edges:')
show('sign(aa[PRE])  [the original]', profile(L, np.sign(aa_pre), np.abs(aa_pre), Q))
show('sign(dwell-mean aa)', profile(L, np.sign(aa_dw), np.abs(aa_pre), Q))
show('sign(angdes[PRE])', profile(L, np.sign(aa_des), np.abs(aa_pre), Q))
show('sign(dwell-mean angdes)', profile(L, np.sign(aa_dwdes), np.abs(aa_pre), Q))
print()
print('    (c) restrict to episodes where the sign is UNAMBIGUOUS, then re-bin inside them:')
for thr in [0.3, 0.5, 1.0, 2.0]:
    ii = L[np.abs(aa_pre[L]) >= thr]
    ed = list(np.quantile(np.abs(aa_pre[ii]), [0, 1 / 3, 2 / 3, 1.0]))
    rows = profile(ii, np.sign(aa_pre), np.abs(aa_pre), ed)
    ctr = np.array([r[0] for r in rows]); xs = np.array([r[4] for r in rows])
    print(f'        |aa|>={thr:4.1f}  n={len(ii):3d}  CENTRE ' + ' '.join(f'{c:+.4f}' for c in ctr)
          + '  at |aa| ' + ' '.join(f'{x:.2f}' for x in xs)
          + f'   slope/deg ' + ' '.join(f'{c/x:+.4f}' for c, x in zip(ctr, xs)))
print('    if the slope/deg still falls by >2x across the retained range, the centre is NOT')
print('    proportional to angle even with the sign degeneracy removed.')

print()
print('=' * 92)
print('B2  SPEED CONFOUND')
print(f'    corr(|aa[PRE]|, v) over the 2-8 torque set: '
      f'{np.corrcoef(np.abs(aa_pre[L]), v[L])[0,1]:+.3f}'
      f'   corr(log|aa|, v) {np.corrcoef(np.log(np.abs(aa_pre[L])+0.05), v[L])[0,1]:+.3f}')
print('    median v per ANGLE quintile: ' + ' '.join(
    f'{np.median(v[L][(np.abs(aa_pre[L])>=Q[i]) & (np.abs(aa_pre[L])<=Q[i+1])]):.2f}' for i in range(5)))
print('    median |aa| per SPEED tercile, and the profile binned BY SPEED:')
Vs = list(np.quantile(v[L], [0, 1 / 3, 2 / 3, 1.0]))


def profile_x(ii, xabs, edges):
    return profile(ii, np.sign(aa_pre), xabs, edges)


rows = profile_x(L, v, Vs)
print(f'        speed bins {[round(x,2) for x in Vs]}')
show('BINNED BY SPEED (not angle)', rows)
print('    fork k(v)*level vs the single fitted K=%.5f:' % K)
for vv in [2, 3, 4, 5, 6, 7, 8]:
    kf = np.interp(vv, [2., 4., 6., 8., 10., 12.5, 15., 17.5, 20., 23., 28.],
                   [.0021, .0028, .0044, .0052, .0074, .0092, .0095, .0103, .0116, .0133, .0160])
    print(f'        v={vv:2d}  k_fork={kf:.5f}  k*1.15={kf*1.15:.5f}   K-k*1.15 = {K-kf*1.15:+.5f}'
          f'   x {K/(kf*1.15):.2f}')
print('    => a single K mis-specifies the angle slope by -0.0032 at 2 m/s and +0.0004 at 8 m/s;')
print('       any |aa|-v correlation turns that into a spurious angle profile.')
print()
print('    angle profile WITHIN each speed tercile (3 angle bins each):')
for i in range(3):
    ii = L[(v[L] >= Vs[i]) & (v[L] <= Vs[i + 1])]
    ed = list(np.quantile(np.abs(aa_pre[ii]), [0, 1 / 3, 2 / 3, 1.0]))
    rows = profile_x(ii, np.abs(aa_pre), ed)
    print(f'        v {Vs[i]:.2f}-{Vs[i+1]:.2f}  n={len(ii):3d}  CENTRE '
          + ' '.join(f'{r[0]:+.4f}@{r[4]:.2f}(n{r[2]}/{r[3]})' for r in rows))

print()
print('=' * 92)
print('B3  DETECTION ASYMMETRY per angle bin  (frames from dwell end i1 to breakaway bk)')
lag = C['bk'].astype(float) - C['i1'].astype(float)
tw = (sj == -np.sign(aa_pre))
print(f'    pooled: away {np.median(lag[L][~tw[L]]):.1f}  toward {np.median(lag[L][tw[L]]):.1f} frames')
print(f"    {'bin':>15s} {'lag_away':>9s} {'lag_tow':>9s} {'diff':>7s} {'pkrate_aw':>10s} {'pkrate_tw':>10s}")
pk = C['pk_rate']
for i in range(5):
    m = (np.abs(aa_pre) >= Q[i]) & ((np.abs(aa_pre) <= Q[i + 1]) if i == 4 else (np.abs(aa_pre) < Q[i + 1])) & LOW
    ma, mt = m & ~tw, m & tw
    print(f'    {Q[i]:6.2f}-{Q[i+1]:7.2f} {np.median(lag[ma]):9.1f} {np.median(lag[mt]):9.1f}'
          f' {np.median(lag[ma])-np.median(lag[mt]):+7.1f} {np.median(pk[ma]):10.2f} {np.median(pk[mt]):10.2f}')
print('    and the command growth rate over the 30 ms before bk, to price the lag:')
gro = (W['cmd'][ar, BK] - W['cmd'][ar, BK - 10]) * sj
print(f'    median |dcmd| per 10 frames, sign-aligned: away {np.median(gro[L][~tw[L]]):+.4f}'
      f'  toward {np.median(gro[L][tw[L]]):+.4f}')

print()
print('=' * 92)
print('B4  the offset floor:  aa = sa - aoff (learned).  A 0.1-0.3 deg offset error flips the')
print('    sign of any episode inside it, and bin 1 is |aa| <= 0.63 deg = 6 LSB.')
print(f'    bin-1 episodes with |aa| <= 0.3 deg: '
      f'{int(((np.abs(aa_pre[L])<=0.3)).sum())} of {int(((np.abs(aa_pre[L])<Q[1])).sum())} in bin 1')
print('    implied CENTRE_true from bin1 if p is the mislabel fraction:  CENTRE_true = 0.0001/(1-2p)')
for p in [0.1, 0.2, 0.3, 0.4, 0.45]:
    print(f'        p={p:.2f} -> CENTRE_true = {0.0001/(1-2*p):+.4f}   (needs p ~ 0.5 to reach 0.03)')
