"""A3: WHO supplies the +0.020 outward centre offset, and is it flat (an intercept) or angle/speed
dependent (a map error)?

(a) Channel decomposition.  cmd = P + I + hold_ff + move + z + rl + dob (identity checked).  The fit is
    linear, so running the SAME regression on each channel decomposes the centre and the half-width
    additively.  If the offset is carried by I or dob it is a LOOP state, not a plant property, and a
    static feedforward is the wrong remedy (and the observer will fight it -- the fork's own rev-6
    comment says a feedforward the observer's model does not know gets cancelled within its 0.6 Hz corner).
(b) Offset vs |aa| bin and v bin, model M (map residual, correct per-route level).
(c) HoldLevel ON (x1.15 map, 2 routes) vs OFF (3 routes): a map error should shrink under the level.
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
toward = (sj == -sgn).astype(float)
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
lev = np.array([PR[r].get('AccordHoldLevel', '0') == '1' for r in route])
d0 = np.maximum(c('w_d0'), 0)
IDX_BK = np.full(N, PRE - 3)
holdlev = np.array([hold_map(W['aa'][i], W['v'][i], bool(lev[i])) for i in range(N)])
out = {}

# ---- identity check
ch = ['P', 'I', 'hold_ff', 'move', 'z', 'rl', 'dob']
S = sum(W[k] for k in ch)
m28 = TQ & (v >= 2) & (v < 8)
r = (W['cmd'] - S)[np.where(m28)[0]][:, PRE - 3]
out['identity_cmd_minus_sum_rms'] = round(float(np.sqrt(np.mean(r ** 2))), 6)
out['identity_cmd_minus_sum_p95'] = round(float(np.percentile(np.abs(r), 95)), 6)
print('identity |cmd - sum(channels)| rms', out['identity_cmd_minus_sum_rms'], 'p95', out['identity_cmd_minus_sum_p95'])


def band_of(yfull, ii, idx, use_map_resid=False):
    aa = W['aa'][ar, idx]
    y = yfull[ar, idx] - (holdlev[ar, idx] if use_map_resid else 0.0)
    X = np.vstack([sj, sj * toward, np.ones(N)]).T if use_map_resid else np.vstack([aa, sj, sj * toward, np.ones(N)]).T
    co = np.linalg.lstsq(X[ii], y[ii], rcond=None)[0]
    Fa, d = (co[0], co[1]) if use_map_resid else (co[1], co[2])
    away, tw = Fa, -(Fa + d)
    return np.array([(away - tw) / 2.0, (away + tw) / 2.0])      # halfwidth, centre


print('\n=== (a) channel decomposition, torque 2-8, breakaway (halfwidth, centre) ===')
rows = {}
for nm, yy in [('cmd', W['cmd'])] + [(k, W[k]) for k in ch] + [('F(sum ff)', W['F'])]:
    est, lo, hi, _ = boot_routes(lambda ii: band_of(yy, ii, IDX_BK), route, m28, nb=800, seed=5)
    rows[nm] = dict(halfwidth=[round(float(est[0]), 5), [round(float(lo[0]), 5), round(float(hi[0]), 5)]],
                    centre=[round(float(est[1]), 5), [round(float(lo[1]), 5), round(float(hi[1]), 5)]])
    print(f'  {nm:10s} hw {est[0]:+.5f} [{lo[0]:+.5f},{hi[0]:+.5f}]   centre {est[1]:+.5f} [{lo[1]:+.5f},{hi[1]:+.5f}]')
out['channels_bk_2_8'] = rows
print('  --- same at dwell start ---')
rows2 = {}
for nm, yy in [('cmd', W['cmd'])] + [(k, W[k]) for k in ch]:
    est, lo, hi, _ = boot_routes(lambda ii: band_of(yy, ii, d0), route, m28, nb=800, seed=5)
    rows2[nm] = dict(halfwidth=[round(float(est[0]), 5), [round(float(lo[0]), 5), round(float(hi[0]), 5)]],
                     centre=[round(float(est[1]), 5), [round(float(lo[1]), 5), round(float(hi[1]), 5)]])
    print(f'  {nm:10s} hw {est[0]:+.5f} [{lo[0]:+.5f},{hi[0]:+.5f}]   centre {est[1]:+.5f} [{lo[1]:+.5f},{hi[1]:+.5f}]')
out['channels_ds_2_8'] = rows2

print('\n=== (b) model-M centre vs |aa| and v (flat = intercept, varying = map error) ===')
sub = {}
for lab, mm in (('|aa|<1', m28 & (np.abs(aa_bk) < 1)), ('1-3', m28 & (np.abs(aa_bk) >= 1) & (np.abs(aa_bk) < 3)),
                ('3-8', m28 & (np.abs(aa_bk) >= 3) & (np.abs(aa_bk) < 8)), ('>=8', m28 & (np.abs(aa_bk) >= 8)),
                ('v2-5', m28 & (v < 5)), ('v5-8', m28 & (v >= 5)),
                ('level ON', m28 & lev), ('level OFF', m28 & ~lev)):
    n = int(mm.sum())
    if n < 12:
        print(f'  {lab:10s} n={n} too few'); continue
    est, lo, hi, _ = boot_routes(lambda ii: band_of(W['cmd'], ii, IDX_BK, True), route, mm, nb=800, seed=5) \
        if len(np.unique(route[mm])) > 1 else (band_of(W['cmd'], np.where(mm)[0], IDX_BK, True), [np.nan] * 2, [np.nan] * 2, None)
    sub[lab] = dict(n=n, halfwidth=[round(float(est[0]), 5), [round(float(lo[0]), 5), round(float(hi[0]), 5)]],
                    centre=[round(float(est[1]), 5), [round(float(lo[1]), 5), round(float(hi[1]), 5)]],
                    n_routes=int(len(np.unique(route[mm]))))
    print(f'  {lab:10s} n={n:3d} r={len(np.unique(route[mm]))} hw {est[0]:+.5f} [{lo[0]:+.5f},{hi[0]:+.5f}]  centre {est[1]:+.5f} [{lo[1]:+.5f},{hi[1]:+.5f}]')
out['subsets_M_bk_2_8'] = sub

# (c) ratio test: a map error scales with the map value; an intercept does not.
# regress the model-M residual's outward component on hold_map itself.
print('\n=== (c) is the offset proportional to the map (slope error) or constant (intercept)? ===')
y = (W['cmd'][ar, IDX_BK] - holdlev[ar, IDX_BK]) * sgn          # outward-positive residual
hm = np.abs(holdlev[ar, IDX_BK])
dirn = np.where(toward > 0, -1.0, 1.0)


def two_term(ii):
    X = np.vstack([np.ones(N), hm, dirn, dirn * 0 + 0]).T[:, :3]
    co = np.linalg.lstsq(X[ii], y[ii], rcond=None)[0]
    return co       # const, per-unit-map, direction(half-width)


est, lo, hi, _ = boot_routes(two_term, route, m28, nb=800, seed=5)
lbl = ['const_outward', 'per_unit_holdmap', 'halfwidth']
out['prop_test_2_8'] = {a: [round(float(est[i]), 5), [round(float(lo[i]), 5), round(float(hi[i]), 5)]] for i, a in enumerate(lbl)}
for i, a in enumerate(lbl):
    print(f'  {a:18s} {est[i]:+.5f} [{lo[i]:+.5f},{hi[i]:+.5f}]')
print('  mean |hold_map| at breakaway, 2-8:', round(float(np.mean(hm[m28])), 4),
      ' p90', round(float(np.percentile(hm[m28], 90)), 4))
out['mean_absholdmap_2_8'] = round(float(np.mean(hm[m28])), 5)
json.dump(out, open('out/a3_decomp.json', 'w'), indent=1)
