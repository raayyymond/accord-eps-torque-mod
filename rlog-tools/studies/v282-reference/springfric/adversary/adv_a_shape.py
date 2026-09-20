"""ATTACK A -- is CENTRE ANGLE-PROPORTIONAL at all, and is the profile statistically real?
A1  implied slope CENTRE/|aa| per bin   (proportional => constant)
A2  route-cluster bootstrap CI on every bin's CENTRE and HW, and on the 454x ratio
A3  re-bin: fixed edges, log-spaced, 3 bins, terciles; drop the smallest-angle episodes
A4  estimators: median vs 20% trimmed mean vs mean vs Hodges-Lehmann
A5  model comparison on the signed residual: b*|th|  vs  const  vs  const*above-threshold
    vs  saturating tanh   (clustered bootstrap on the coefficients)
"""
import numpy as np
from adv_load import load, cols, PRE, BK, cluster_boot
from adv_gate import fit4

EP, W, P = load()
C = cols(EP)
N = len(EP); ar = np.arange(N)
g, v, sj, route, kind = C['group'], C['v'], C['sjump'], C['route'], C['kind']
aa_pre = W['aa'][:, PRE]
aabs = np.abs(aa_pre)
toward = (sj == -np.sign(aa_pre)).astype(float)
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
LOW = TQ & (v >= 2) & (v < 8)
f0 = fit4(LOW, np.full(N, BK))
K, Cc = f0['k'], f0['const']
y = (W['cmd'][ar, BK] - K * W['aa'][ar, BK] - Cc) * np.sign(aa_pre)   # = u - K|th| - c*sgn
L = np.where(LOW)[0]


def prof(ii, edges, est=np.median, xs=None):
    """CENTRE/HW per bin over index set ii."""
    x = aabs[ii]; yy = y[ii]; tw = toward[ii]
    out = []
    for i in range(len(edges) - 1):
        m = (x >= edges[i]) & (x < edges[i + 1] if i < len(edges) - 2 else x <= edges[i + 1])
        ma, mt = m & (tw == 0), m & (tw == 1)
        if ma.sum() < 2 or mt.sum() < 2:
            out.append((np.nan, np.nan, int(ma.sum()), int(mt.sum()), np.nan)); continue
        a_, t_ = est(yy[ma]), est(yy[mt])
        out.append(((a_ + t_) / 2, (a_ - t_) / 2, int(ma.sum()), int(mt.sum()), np.median(x[m])))
    return out


def trim(x, f=0.2):
    x = np.sort(np.asarray(x, float)); k = int(np.floor(len(x) * f))
    return float(np.mean(x[k:len(x) - k])) if len(x) - 2 * k >= 1 else float(np.mean(x))


def hl(x):
    x = np.asarray(x, float); s = x[:, None] + x[None, :]
    return float(np.median(s[np.triu_indices(len(x))] / 2.0))


Q = np.quantile(aabs[LOW], [0, .2, .4, .6, .8, 1.0])
print('=' * 84)
print('A1  IS IT PROPORTIONAL?  implied slope = CENTRE / med|aa| per bin')
print('    a truly angle-PROPORTIONAL centre has a CONSTANT slope here.')
rows = prof(L, Q)
print(f"    {'bin':>15s} {'med|aa|':>8s} {'CENTRE':>9s} {'slope/deg':>10s} {'HW':>9s}")
sl = []
for i, (ctr, hw, na, nt, mx) in enumerate(rows):
    print(f'    {Q[i]:6.2f}-{Q[i+1]:7.2f} {mx:8.2f} {ctr:+9.4f} {ctr/mx:+10.5f} {hw:+9.4f}')
    sl.append(ctr / mx)
sl = np.array(sl)
print(f'    slope spans {sl.min():+.5f} -> {sl.max():+.5f}   ratio {sl.max()/max(sl.min(),1e-9):.0f}x')
print(f'    slope over the FOUR bins above 0.63 deg: {np.array(sl[1:]).min():+.5f} ->'
      f' {np.array(sl[1:]).max():+.5f}  ratio {sl[1:].max()/sl[1:].min():.1f}x')
print('    VERDICT A1: if the slope is not constant, "angle-proportional" is the WRONG')
print('    functional form and every remedy sized from a proportional k is mis-sized.')

print()
print('=' * 84)
print('A2  ROUTE-CLUSTER BOOTSTRAP CI on each bin (2000 draws, indices concatenated)')


def f_prof(ii, rr):
    r = prof(ii, Q)
    return np.array([x[0] for x in r] + [x[1] for x in r])


pt, lo, hi, bs = cluster_boot(f_prof, L, route[L], nb=2000, seed=11)
print(f"    {'bin':>15s} {'CENTRE':>9s} {'95% CI':>22s}   {'HW':>9s} {'95% CI':>22s}")
for i in range(5):
    print(f'    {Q[i]:6.2f}-{Q[i+1]:7.2f} {pt[i]:+9.4f} [{lo[i]:+8.4f},{hi[i]:+8.4f}]'
          f'   {pt[5+i]:+9.4f} [{lo[5+i]:+8.4f},{hi[5+i]:+8.4f}]')
# does bin1 differ from bin3?  and is the ratio statistic bounded?
d13 = bs[:, 2] - bs[:, 0]
rat = bs[:, :5].max(1) / np.maximum(bs[:, :5].min(1), 1e-12)
print(f'\n    CENTRE(bin3) - CENTRE(bin1): point {pt[2]-pt[0]:+.4f}'
      f'  CI [{np.nanpercentile(d13,2.5):+.4f},{np.nanpercentile(d13,97.5):+.4f}]'
      f'   P(<=0)={np.mean(d13<=0):.3f}')
print(f'    the "454x" ratio, bootstrapped: median {np.nanmedian(rat):.0f}x'
      f'   CI [{np.nanpercentile(rat,2.5):.0f}x, {np.nanpercentile(rat,97.5):.0f}x]'
      f'   frac>1000x {np.mean(rat>1000):.2f}   frac NEGATIVE min {np.mean(bs[:,:5].min(1)<0):.2f}')
print('    VERDICT A2: a ratio whose denominator bootstraps through zero is not a statistic.')

print()
print('=' * 84)
print('A3  RE-BINNING -- does the profile survive different boundaries?')
for name, ed in [('fixed 0/.5/1/2/4/40', [0, .5, 1, 2, 4, 40]),
                 ('log  .1/.4/1/2.5/6/40', [0, .4, 1.0, 2.5, 6.0, 40]),
                 ('3 bins 0/1/3/40', [0, 1, 3, 40]),
                 ('terciles', list(np.quantile(aabs[L], [0, 1/3, 2/3, 1.0]))),
                 ('DROP |aa|<0.5 : 4 bins', None),
                 ('DROP |aa|<1.0 : 3 bins', None)]:
    if name.startswith('DROP'):
        thr = 0.5 if '0.5' in name else 1.0
        ii = L[aabs[L] >= thr]
        nb_ = 4 if thr == 0.5 else 3
        ed = list(np.quantile(aabs[ii], np.linspace(0, 1, nb_ + 1)))
        r = prof(ii, ed)
    else:
        ii = L; r = prof(ii, ed)
    s = ' '.join(f'{x[0]:+.4f}@{x[4]:.2f}(n{x[2]}/{x[3]})' for x in r)
    ctrs = np.array([x[0] for x in r])
    print(f'    {name:24s} n={len(ii):3d}  CENTRE: {s}')
    print(f'    {"":24s}    span {np.nanmin(ctrs):+.4f}..{np.nanmax(ctrs):+.4f}'
          f'   HW: ' + ' '.join(f'{x[1]:+.4f}' for x in r))

print()
print('=' * 84)
print('A4  ESTIMATORS (quintile bins, all 5)')
for nm, est in [('median', np.median), ('trim20', trim), ('mean', np.mean), ('HodgesLehm', hl)]:
    r = prof(L, Q, est)
    print(f'    {nm:11s} CENTRE ' + ' '.join(f'{x[0]:+.4f}' for x in r)
          + '    HW ' + ' '.join(f'{x[1]:+.4f}' for x in r))

print()
print('=' * 84)
print('A5  MODEL COMPARISON on the signed edge level, both directions jointly:')
print('    u_signed = y ;  model  u = f(|th|) + F*sigma ,  sigma=+1 away / -1 toward')
X = {}
th = aabs[L]; sg = 1.0 - 2 * toward[L]; yy = y[L]
X['prop      b*|th|'] = np.vstack([th, sg, np.ones(len(L))]).T
X['const     a*1[th>0]'] = np.vstack([np.ones(len(L)), sg, np.zeros(len(L))]).T
X['step      a*1[th>.6]'] = np.vstack([(th > 0.63).astype(float), sg, np.ones(len(L))]).T
X['tanh      a*tanh(th/1)'] = np.vstack([np.tanh(th / 1.0), sg, np.ones(len(L))]).T
X['tanh      a*tanh(th/3)'] = np.vstack([np.tanh(th / 3.0), sg, np.ones(len(L))]).T
X['log       a*log1p(th)'] = np.vstack([np.log1p(th), sg, np.ones(len(L))]).T
X['prop+const'] = np.vstack([th, np.ones(len(L)), sg, np.ones(len(L)) * 0]).T
for nm, Xm in X.items():
    c, res, rk, _ = np.linalg.lstsq(Xm, yy, rcond=None)
    pred = Xm @ c
    ss = float(np.sum((yy - pred) ** 2))
    print(f'    {nm:24s} rms {np.sqrt(ss/len(L)):.5f}  R2 {1-ss/np.sum((yy-yy.mean())**2):.4f}'
          f'  coef {np.round(c,5)}')
print('    (F = the sigma coefficient; the first coefficient is the angle term)')
