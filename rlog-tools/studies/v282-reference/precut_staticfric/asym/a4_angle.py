"""A4: is the +0.020 outward offset FLAT in angle (a Coulomb intercept) or PROPORTIONAL to angle
(a hold-map slope deficit)?  Robust, regression-free where possible, plus route leave-one-out
and the influence diagnostics.

y_out = (cmd - hold_map(aa, v, level_of_route)) * sign(aa)   [outward-positive, +left frame]
  away release  -> y_out = centre + halfwidth
  toward release -> y_out = centre - halfwidth
so  centre(|aa| bin) = (median_away + median_toward)/2   -- no regression, no shared slope.
"""
import json
import numpy as np
from alib import *

EP, W, PR = load()
c = cols(EP)
g, v, sj, route = c('group'), c('v'), c('sjump'), c('route')
N = len(EP); ar = np.arange(N)
aa_bk = W['aa'][:, PRE]
sgn = np.sign(aa_bk)
toward = (sj == -sgn)
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
lev = np.array([PR[r].get('AccordHoldLevel', '0') == '1' for r in route])
IDX = PRE - 3
holdlev = np.array([hold_map(W['aa'][i], W['v'][i], bool(lev[i])) for i in range(N)])
y_out = (W['cmd'][ar, IDX] - holdlev[ar, IDX]) * sgn
absaa = np.abs(W['aa'][ar, IDX])
m28 = TQ & (v >= 2) & (v < 8)
m815 = TQ & (v >= 8) & (v < 15)
out = {}

print('=== frame checks (EVIDENCE, method: sign of correlations on the episode set) ===')
print('  corr(cmd, aa) at breakaway, torque 2-8 :', round(float(np.corrcoef(W['cmd'][m28, IDX], W['aa'][m28, IDX])[0, 1]), 3))
print('  corr(hold_ff, angdes)                  :', round(float(np.corrcoef(W['hold_ff'][m28, IDX], W['angdes'][m28, IDX])[0, 1]), 3))
print('  corr(hold_map(aa), cmd)                :', round(float(np.corrcoef(holdlev[m28, IDX], W['cmd'][m28, IDX])[0, 1]), 3))
print('  frac away episodes with sign(angdes)==sign(aa):',
      round(float(np.mean(np.sign(W['angdes'][ar, IDX])[m28 & ~toward] == sgn[m28 & ~toward])), 3))
out['frame'] = dict(corr_cmd_aa=round(float(np.corrcoef(W['cmd'][m28, IDX], W['aa'][m28, IDX])[0, 1]), 3),
                    corr_holdff_angdes=round(float(np.corrcoef(W['hold_ff'][m28, IDX], W['angdes'][m28, IDX])[0, 1]), 3))


def med_centre(ii):
    a = ii[~toward[ii]]; t = ii[toward[ii]]
    if len(a) < 3 or len(t) < 3:
        return np.array([np.nan, np.nan])
    ma, mt = np.median(y_out[a]), np.median(y_out[t])
    return np.array([(ma + mt) / 2.0, (ma - mt) / 2.0])


print('\n=== (1) robust centre per |aa| bin (median-based, no shared slope), torque 2-8 ===')
BINS = [(0, 1), (1, 2), (2, 4), (4, 8), (8, 1e9)]
rows = {}
for a0, a1 in BINS:
    mm = m28 & (absaa >= a0) & (absaa < a1)
    n = int(mm.sum()); na = int((mm & ~toward).sum()); nt = int((mm & toward).sum())
    if na < 3 or nt < 3:
        print(f'  |aa| {a0}-{a1}: n={n} away={na} toward={nt} -- too few'); continue
    est, lo, hi, _ = boot_routes(med_centre, route, mm, nb=800, seed=3)
    rows[f'{a0}-{a1}'] = dict(n=n, n_away=na, n_toward=nt,
                              centre=[round(float(est[0]), 5), [round(float(lo[0]), 5), round(float(hi[0]), 5)]],
                              halfwidth=[round(float(est[1]), 5), [round(float(lo[1]), 5), round(float(hi[1]), 5)]],
                              med_absaa=round(float(np.median(absaa[mm])), 2),
                              med_holdmap=round(float(np.median(np.abs(holdlev[mm, IDX]))), 4))
    print(f'  |aa| {a0:>2}-{a1:<4} n={n:3d} (a{na:2d}/t{nt:2d}) med|aa|={np.median(absaa[mm]):5.2f}  '
          f'centre {est[0]:+.5f} [{lo[0]:+.5f},{hi[0]:+.5f}]  hw {est[1]:+.5f} [{lo[1]:+.5f},{hi[1]:+.5f}]')
out['centre_by_absaa_2_8'] = rows

print('\n  same, torque 8-15 (independent speed bin):')
rows = {}
for a0, a1 in BINS:
    mm = m815 & (absaa >= a0) & (absaa < a1)
    na = int((mm & ~toward).sum()); nt = int((mm & toward).sum())
    if na < 3 or nt < 3:
        continue
    est, lo, hi, _ = boot_routes(med_centre, route, mm, nb=800, seed=3)
    rows[f'{a0}-{a1}'] = dict(n=int(mm.sum()), centre=[round(float(est[0]), 5), [round(float(lo[0]), 5), round(float(hi[0]), 5)]],
                              halfwidth=[round(float(est[1]), 5), [round(float(lo[1]), 5), round(float(hi[1]), 5)]])
    print(f'  |aa| {a0:>2}-{a1:<4} n={int(mm.sum()):3d} centre {est[0]:+.5f} [{lo[0]:+.5f},{hi[0]:+.5f}]  hw {est[1]:+.5f}')
out['centre_by_absaa_8_15'] = rows

print('\n=== (2) intercept vs slope-deficit fit: y_out = a + b*|aa| + hw*dir (per speed bin) ===')


def two(ii, mask_len=None):
    X = np.vstack([np.ones(N), absaa, np.where(toward, -1.0, 1.0)]).T
    return np.linalg.lstsq(X[ii], y_out[ii], rcond=None)[0]


for lab, mm in (('2-8', m28), ('2-5', m28 & (v < 5)), ('5-8', m28 & (v >= 5)), ('8-15', m815)):
    est, lo, hi, _ = boot_routes(two, route, mm, nb=800, seed=3)
    kmap = float(np.median(np.interp(v[mm], HOLD_V_BP, HOLD_K_V) * np.where(lev[mm], 1.15, 1.0)))
    out[f'intercept_slope_{lab}'] = dict(
        intercept=[round(float(est[0]), 5), [round(float(lo[0]), 5), round(float(hi[0]), 5)]],
        slope_per_deg=[round(float(est[1]), 5), [round(float(lo[1]), 5), round(float(hi[1]), 5)]],
        halfwidth=[round(float(est[2]), 5), [round(float(lo[2]), 5), round(float(hi[2]), 5)]],
        map_slope_k_median=round(kmap, 5), slope_as_frac_of_map=round(float(est[1]) / kmap, 3))
    print(f'  {lab:5s} intercept {est[0]:+.5f} [{lo[0]:+.5f},{hi[0]:+.5f}]  slope {est[1]:+.5f} '
          f'[{lo[1]:+.5f},{hi[1]:+.5f}] torque/deg  (map k={kmap:.5f}, i.e. {est[1] / kmap:+.2f} x the map slope)'
          f'  hw {est[2]:+.5f}')

print('\n=== (3) route leave-one-out, torque 2-8 (model-M centre, OLS with the study spec) ===')


def centre_ols(ii):
    X = np.vstack([np.ones(N), np.where(toward, -1.0, 1.0)]).T
    co = np.linalg.lstsq(X[ii], y_out[ii], rcond=None)[0]
    return np.array([co[0], co[1]])


u = np.unique(route[m28])
loo = {}
full = centre_ols(np.where(m28)[0])
print(f'  ALL           centre {full[0]:+.5f}  hw {full[1]:+.5f}')
for r in u:
    mm = m28 & (route != r)
    e = centre_ols(np.where(mm)[0])
    loo[str(r)] = dict(centre=round(float(e[0]), 5), halfwidth=round(float(e[1]), 5), n_dropped=int((m28 & (route == r)).sum()))
    print(f'  drop {r}  n-{int((m28 & (route == r)).sum()):3d}  centre {e[0]:+.5f}  hw {e[1]:+.5f}')
out['loo_2_8'] = loo
out['all_2_8'] = dict(centre=round(float(full[0]), 5), halfwidth=round(float(full[1]), 5))

print('\n=== (4) per-route centre, torque 2-8 ===')
pr = {}
for r in u:
    mm = m28 & (route == r)
    e = centre_ols(np.where(mm)[0])
    a, t = int((mm & ~toward).sum()), int((mm & toward).sum())
    pr[str(r)] = dict(n=int(mm.sum()), n_away=a, n_toward=t, centre=round(float(e[0]), 5), halfwidth=round(float(e[1]), 5),
                      holdlevel=bool(lev[np.where(mm)[0][0]]))
    print(f'  {r} n={int(mm.sum()):3d} (a{a}/t{t}) level={bool(lev[np.where(mm)[0][0]])}  centre {e[0]:+.5f}  hw {e[1]:+.5f}')
out['per_route_2_8'] = pr

print('\n=== (5) influence: single-episode dfbeta on the centre, torque 2-8 ===')
ii = np.where(m28)[0]
base = centre_ols(ii)[0]
df = np.array([centre_ols(np.delete(ii, q))[0] - base for q in range(len(ii))])
o = np.argsort(-np.abs(df))[:6]
out['dfbeta_max'] = round(float(np.max(np.abs(df))), 5)
out['dfbeta_top'] = [dict(route=str(route[ii[q]]), absaa=round(float(absaa[ii[q]]), 2), v=round(float(v[ii[q]]), 2),
                          toward=bool(toward[ii[q]]), y_out=round(float(y_out[ii[q]]), 4), dfbeta=round(float(df[q]), 5))
                     for q in o]
print('  max |dfbeta| =', round(float(np.max(np.abs(df))), 5), ' (centre =', round(float(base), 5), ')')
for q in o:
    print(f'   {route[ii[q]]} |aa|={absaa[ii[q]]:6.2f} v={v[ii[q]]:5.2f} toward={bool(toward[ii[q]])!s:5s} '
          f'y_out={y_out[ii[q]]:+.4f} dfbeta={df[q]:+.5f}')
# heteroscedasticity: spread of y_out by |aa| bin
print('\n  y_out spread by |aa| bin (heteroscedasticity):')
het = {}
for a0, a1 in BINS:
    mm = m28 & (absaa >= a0) & (absaa < a1)
    if mm.sum() < 5:
        continue
    het[f'{a0}-{a1}'] = dict(n=int(mm.sum()), iqr=round(float(np.subtract(*np.percentile(y_out[mm], [75, 25]))), 4),
                             sd=round(float(np.std(y_out[mm])), 4))
    print(f'   |aa| {a0}-{a1}: n={int(mm.sum()):3d} sd={np.std(y_out[mm]):.4f} IQR={np.subtract(*np.percentile(y_out[mm], [75, 25])):.4f}')
out['heterosced_2_8'] = het
json.dump(out, open('out/a4_angle.json', 'w'), indent=1)
