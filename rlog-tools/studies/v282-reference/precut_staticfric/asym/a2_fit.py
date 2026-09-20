"""A2: re-derive the band from scratch, then attack it.

Design models (all in the +left torque frame, y = cmd):
  L  (the study's):   y = k*aa + Fa*sj + d*sj*toward + c          <- free LINEAR spring, one slope per speed bin
  M  (map residual):  y - hold_map(aa, v, level_of_route) = Fa*sj + d*sj*toward + c
  MG (map + gain):    y = gmap*hold_map(...) + Fa*sj + d*sj*toward + c
In sign(aa) units the two release levels are  away = Fa,  toward = -(Fa+d);
  halfwidth = (away - toward)/2 = Fa + d/2 ;  centre = (away + toward)/2 = -d/2.
CRUX: the design needs  centre(breakaway) == level(dwell_start),  because only then does each
direction need the same halfwidth of travel.  Fitted separately those are two numbers from two
regressions; here they are computed in ONE resample so their difference gets a CI.
"""
import json
import numpy as np
from alib import *

EP, W, PR = load()
c = cols(EP)
g, v, sj, route = c('group'), c('v'), c('sjump'), c('route')
N = len(EP)
ar = np.arange(N)
aa_bk = W['aa'][:, PRE]
sgn = np.sign(aa_bk)
toward = (sj == -sgn).astype(float)
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
lev = np.array([PR[r].get('AccordHoldLevel', '0') == '1' for r in route])
d0 = np.maximum(c('w_d0'), 0)          # the study's dwell-start index (clipped)
d0raw = c('w_d0')
IDX_BK = np.full(N, PRE - 3)           # 30 ms before breakaway, as the study
hold_at_aa_lev = np.array([hold_map(W['aa'][i], W['v'][i], bool(lev[i])) for i in range(N)])


def design(idx, kind='L'):
    aa = W['aa'][ar, idx]
    vv = W['v'][ar, idx]
    one = np.ones(N)
    if kind == 'L':
        return np.vstack([aa, sj, sj * toward, one]).T, W['cmd'][ar, idx], ('k', 'Fa', 'd', 'c')
    if kind == 'M':
        h = hold_at_aa_lev[ar, idx]
        return np.vstack([sj, sj * toward, one]).T, W['cmd'][ar, idx] - h, ('Fa', 'd', 'c')
    if kind == 'MG':
        h = hold_at_aa_lev[ar, idx]
        return np.vstack([h, sj, sj * toward, one]).T, W['cmd'][ar, idx], ('gmap', 'Fa', 'd', 'c')
    raise ValueError(kind)


def band(ii, idx, kind='L'):
    X, y, nm = design(idx, kind)
    co = np.linalg.lstsq(X[ii], y[ii], rcond=None)[0]
    Fa = co[nm.index('Fa')]; d = co[nm.index('d')]
    away, tw = Fa, -(Fa + d)
    return np.array([away, tw, (away - tw) / 2.0, (away + tw) / 2.0] + list(co))


def crux(ii, kind='L'):
    """One resample -> breakaway band AND dwell-start level AND the travel each direction needs."""
    b = band(ii, IDX_BK, kind)
    s = band(ii, d0, kind)
    away_bk, tw_bk, hw_bk, ctr_bk = b[:4]
    away_ds, tw_ds, hw_ds, ctr_ds = s[:4]
    start = ctr_ds                                  # the common start level, if hw_ds ~ 0
    return np.array([away_bk, tw_bk, hw_bk, ctr_bk, away_ds, tw_ds, hw_ds, ctr_ds,
                     ctr_ds - ctr_bk,                # the claim needs this ~ 0
                     away_bk - away_ds,              # travel needed outward
                     away_ds - tw_bk,                # travel needed inward  (start - inward threshold)
                     (away_ds - tw_bk) - (away_bk - away_ds)])   # inward minus outward travel
NMS = ['away_bk', 'toward_bk', 'halfwidth_bk', 'centre_bk', 'away_ds', 'toward_ds', 'halfwidth_ds',
       'centre_ds', 'centre_ds_minus_centre_bk', 'travel_out', 'travel_in', 'travel_in_minus_out']

res = {}
for gname, gm in (('torque', TQ), ('V282', g == 'V282')):
    for lo, hi in ((2, 8), (8, 15)):
        m = gm & (v >= lo) & (v < hi)
        if m.sum() < 30:
            continue
        for kind in ('L', 'M', 'MG'):
            est, clo, chi, bs = boot_routes(lambda ii: crux(ii, kind), route, m, nb=1500, seed=11)
            key = f'{gname}|{lo}-{hi}|{kind}'
            res[key] = {nm: [round(float(est[q]), 5), [round(float(clo[q]), 5), round(float(chi[q]), 5)]]
                        for q, nm in enumerate(NMS)}
            res[key]['n'] = int(m.sum()); res[key]['n_routes'] = int(len(np.unique(route[m])))
            # extra coefficients
            X, y, nm = design(IDX_BK, kind)
            co = np.linalg.lstsq(X[np.where(m)[0]], y[np.where(m)[0]], rcond=None)[0]
            res[key]['coef_bk'] = {a: round(float(b), 5) for a, b in zip(nm, co)}
            r = y[m] - X[m] @ co
            res[key]['resid_rms_bk'] = round(float(np.sqrt(np.mean(r ** 2))), 5)
            print(key, 'n', int(m.sum()))
            for q, nm2 in enumerate(NMS):
                print(f'   {nm2:26s} {est[q]:+.5f}  [{clo[q]:+.5f},{chi[q]:+.5f}]')
            print('   coef', res[key]['coef_bk'], 'resid_rms', res[key]['resid_rms_bk'])
json.dump(res, open('out/a2_fit.json', 'w'), indent=1)
