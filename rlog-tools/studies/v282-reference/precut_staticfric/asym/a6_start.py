"""A6: is "the command starts at the band centre" an artefact of how the dwell START is defined?

Three attacks:
(1) INDEX SWEEP.  Move the start index over the dwell and before it (and drop the 8/145 episodes whose
    window does not reach the dwell start, where ss_centring_fit clips w_d0 to 0 = 1.5 s before breakaway).
(2) CAUSALITY / TAUTOLOGY.  At dwell start the break DIRECTION is a future event, so a direction-dependent
    coefficient there can only be nonzero if the pre-break command predicts the future.  Null: shuffle the
    direction labels and see how big |halfwidth_ds| gets by chance.  If the observed 0.0004 is inside the
    shuffled spread it carries no information.
(3) PRIOR-MOTION SPLIT.  ss_extract records kind = rest / cont / rev (prior wheel motion vs the jump).
    If the dwell start is where the command just released the wheel the OTHER way ('rev'), the start level
    is that release level by construction.  Does the result hold inside kind == 'rest'?
"""
import json
import numpy as np
from alib import *

EP, W, PR = load()
c = cols(EP)
g, v, sj, route = c('group'), c('v'), c('sjump'), c('route')
N = len(EP); ar = np.arange(N)
aa_bk = W['aa'][:, PRE]; sgn = np.sign(aa_bk)
toward = (sj == -sgn); dirn = np.where(toward, -1.0, 1.0)
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
lev = np.array([PR[r].get('AccordHoldLevel', '0') == '1' for r in route])
holdlev = np.array([hold_map(W['aa'][i], W['v'][i], bool(lev[i])) for i in range(N)])
kind = c('kind'); w_d0 = c('w_d0'); w_d1 = c('w_d1')
m28 = TQ & (v >= 2) & (v < 8)
IDX_BK = np.full(N, PRE - 3)
out = {}


def band_at(ii, idx, resid=True):
    y = (W['cmd'][ar, idx] - (holdlev[ar, idx] if resid else 0.0)) * sgn
    X = np.vstack([np.ones(N), dirn, np.abs(W['aa'][ar, idx])]).T
    co = np.linalg.lstsq(X[ii], y[ii], rcond=None)[0]
    return np.array([co[0], co[1]])       # centre, halfwidth


ctr_bk = band_at(np.where(m28)[0], IDX_BK)[0]
print('reference: centre at breakaway (model M, outward frame) =', round(float(ctr_bk), 5))

print('\n=== (1) start-index sweep, torque 2-8 ===')
d0c = np.maximum(w_d0, 0)
d1c = np.clip(w_d1, 0, 2 * PRE - 1)
variants = {
    'w_d0 (the study, clipped)': d0c,
    'w_d0 UNclipped subset': d0c,                       # masked below
    'dwell start + 0.10 s': np.clip(d0c + 10, 0, PRE - 4),
    'dwell start + 0.20 s': np.clip(d0c + 20, 0, PRE - 4),
    'dwell midpoint': ((d0c + d1c) // 2).astype(int),
    'dwell END (g1)': d1c,
    '0.10 s BEFORE dwell start': np.clip(d0c - 10, 0, PRE - 4),
    '0.30 s BEFORE dwell start': np.clip(d0c - 30, 0, PRE - 4),
    'fixed 1.0 s before breakaway': np.full(N, PRE - 100),
    'fixed 0.5 s before breakaway': np.full(N, PRE - 50),
}
rows = {}
for lab, idx in variants.items():
    mm = m28 & (w_d0 >= 0) if 'UNclipped' in lab else m28
    est, lo, hi, bs = boot_routes(lambda ii: np.concatenate([band_at(ii, idx),
                                                             [band_at(ii, idx)[0] - band_at(ii, IDX_BK)[0]]]),
                                  route, mm, nb=600, seed=9)
    rows[lab] = dict(n=int(mm.sum()),
                     centre=[round(float(est[0]), 5), [round(float(lo[0]), 5), round(float(hi[0]), 5)]],
                     halfwidth=[round(float(est[1]), 5), [round(float(lo[1]), 5), round(float(hi[1]), 5)]],
                     centre_minus_bk=[round(float(est[2]), 5), [round(float(lo[2]), 5), round(float(hi[2]), 5)]])
    print(f'  {lab:30s} n={int(mm.sum()):3d}  centre {est[0]:+.5f} [{lo[0]:+.5f},{hi[0]:+.5f}]  '
          f'hw {est[1]:+.5f} [{lo[1]:+.5f},{hi[1]:+.5f}]  centre-centre_bk {est[2]:+.5f} [{lo[2]:+.5f},{hi[2]:+.5f}]')
out['index_sweep_2_8'] = rows

print('\n=== (2) shuffle null for halfwidth at dwell start ===')
rng = np.random.default_rng(23)
ii28 = np.where(m28)[0]
obs_ds = band_at(ii28, d0c)[1]
obs_bk = band_at(ii28, IDX_BK)[1]
sh_ds, sh_bk = [], []
for _ in range(2000):
    perm = rng.permutation(len(ii28))
    dsave = dirn.copy()
    dirn[ii28] = dirn[ii28][perm]
    sh_ds.append(band_at(ii28, d0c)[1]); sh_bk.append(band_at(ii28, IDX_BK)[1])
    dirn[:] = dsave
sh_ds = np.array(sh_ds); sh_bk = np.array(sh_bk)
print(f'  halfwidth at DWELL START  observed {obs_ds:+.5f}   shuffled |q95| {np.percentile(np.abs(sh_ds), 95):.5f} '
      f'  p(|shuffled| >= |obs|) = {np.mean(np.abs(sh_ds) >= abs(obs_ds)):.3f}')
print(f'  halfwidth at BREAKAWAY    observed {obs_bk:+.5f}   shuffled |q95| {np.percentile(np.abs(sh_bk), 95):.5f} '
      f'  p(|shuffled| >= |obs|) = {np.mean(np.abs(sh_bk) >= abs(obs_bk)):.3f}')
out['shuffle'] = dict(hw_ds=round(float(obs_ds), 5), hw_ds_shuf_q95=round(float(np.percentile(np.abs(sh_ds), 95)), 5),
                      p_ds=round(float(np.mean(np.abs(sh_ds) >= abs(obs_ds))), 4),
                      hw_bk=round(float(obs_bk), 5), hw_bk_shuf_q95=round(float(np.percentile(np.abs(sh_bk), 95)), 5),
                      p_bk=round(float(np.mean(np.abs(sh_bk) >= abs(obs_bk))), 4))

print('\n=== (3) prior-motion split (kind), torque 2-8 ===')
rows = {}
for k in ('rest', 'cont', 'rev'):
    mm = m28 & (kind == k)
    na, nt = int((mm & ~toward).sum()), int((mm & toward).sum())
    if na < 4 or nt < 4:
        print(f'  kind={k}: n={int(mm.sum())} (a{na}/t{nt}) -- too few in one direction'); continue
    est, lo, hi, bs = boot_routes(lambda ii: np.concatenate([band_at(ii, IDX_BK), band_at(ii, d0c),
                                                             [band_at(ii, d0c)[0] - band_at(ii, IDX_BK)[0]]]),
                                  route, mm, nb=600, seed=9)
    rows[k] = dict(n=int(mm.sum()), n_away=na, n_toward=nt,
                   centre_bk=[round(float(est[0]), 5), [round(float(lo[0]), 5), round(float(hi[0]), 5)]],
                   hw_bk=[round(float(est[1]), 5), [round(float(lo[1]), 5), round(float(hi[1]), 5)]],
                   centre_ds=[round(float(est[2]), 5), [round(float(lo[2]), 5), round(float(hi[2]), 5)]],
                   hw_ds=[round(float(est[3]), 5), [round(float(lo[3]), 5), round(float(hi[3]), 5)]],
                   ds_minus_bk=[round(float(est[4]), 5), [round(float(lo[4]), 5), round(float(hi[4]), 5)]])
    print(f'  kind={k:5s} n={int(mm.sum()):3d} (a{na:2d}/t{nt:2d})  centre_bk {est[0]:+.5f} [{lo[0]:+.5f},{hi[0]:+.5f}]  '
          f'hw_bk {est[1]:+.5f}  centre_ds {est[2]:+.5f}  hw_ds {est[3]:+.5f} [{lo[3]:+.5f},{hi[3]:+.5f}]  '
          f'ds-bk {est[4]:+.5f} [{lo[4]:+.5f},{hi[4]:+.5f}]')
out['kind_split_2_8'] = rows
json.dump(out, open('out/a6_start.json', 'w'), indent=1)
