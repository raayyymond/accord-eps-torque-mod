"""Extend the nearest-neighbour match (v, log|aa|, log dem_rate) -- already in ss_analyze.py for
'slip' -- to ALL FOUR of F3's headline metrics (dwell, gap_model/lag-at-breakaway, catch30, peak_rate)
so the demand/angle confound this lens raises is controlled for on every number F3 quotes, not just
'slip'."""
import sys, os, json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'a_stickslip'))
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..', 'a_stickslip'))
from ss_load import load_all, PRE, boot_ci

EP, W, EX, VAL = load_all()
N = len(EP)
ar = np.arange(N)
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); sj = col('sjump'); route = col('route'); aa_abs = col('abs_aa'); dr = col('dem_rate'); dwell = col('dwell_s')
A = lambda k, i: W[k][ar, i] * sj
gap_model = A('ad', np.full(N, PRE)) - A('aa', np.full(N, PRE))
catch30 = A('aa', np.full(N, PRE + 30)) - A('aa', np.full(N, PRE))
pk = np.max(np.abs(W['sr'][:, PRE:PRE + 40]), 1)
METRICS = dict(dwell_s=dwell, gap_model_deg=gap_model, catch30_deg=catch30, peak_rate_dps=pk)

DOM = '0000006c--2bc842dbac'
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])


def match(tmask, rmask):
    ti = np.where(tmask)[0]; ri_pool = np.where(rmask)[0]; pairs = []
    for i in ti:
        dv = np.abs(v[ri_pool] - v[i]) / 2.0
        da = np.abs(np.log1p(aa_abs[ri_pool]) - np.log1p(aa_abs[i])) / 0.5
        dd = np.abs(np.log(dr[ri_pool]) - np.log(dr[i])) / 0.5
        dist = np.sqrt(dv ** 2 + da ** 2 + dd ** 2)
        j = np.argmin(dist)
        if dist[j] <= 1.5:
            pairs.append((i, ri_pool[j]))
    return pairs


def run(tg_mask, rmask_base, label, lo, hi):
    tm = tg_mask & (v >= lo) & (v < hi)
    rm = rmask_base & (v >= lo - 1) & (v < hi + 1)
    P_ = match(tm, rm)
    if len(P_) < 8:
        print(f'{label} v[{lo},{hi}): n_pairs={len(P_)} (insufficient)')
        return None
    ti = np.array([p[0] for p in P_]); ri = np.array([p[1] for p in P_])
    n_routes_r = len(set(route[ri].tolist())); n_routes_t = len(set(route[ti].tolist()))
    print(f'{label} v[{lo},{hi}): n_pairs={len(P_)}  (t_routes={n_routes_t} r_routes={n_routes_r})')
    out = {}
    for nm, x in METRICS.items():
        p50t, p50r = np.median(x[ti]), np.median(x[ri])
        ratio = p50t / p50r if p50r not in (0, np.nan) else None
        # geometric-mean-of-log-ratio bootstrap (robust to sign, matches ss_analyze.py's slip method)
        if nm == 'gap_model_deg':
            # can be negative -> use the same direct paired diff instead of log-ratio
            d = x[ti] - x[ri]
            if n_routes_r > 1 or n_routes_t > 1:
                md, ci = boot_ci(d, route[ti] if n_routes_t > 1 else route[ri], np.median)
            else:
                md, ci = float(np.median(d)), (float(np.median(d)), float(np.median(d)))
            print(f'  {nm:16s} torque_p50={p50t:.3f} v282_p50={p50r:.3f}  paired_diff_median={md:.3f} CI={tuple(round(c,3) for c in ci)}')
            out[nm] = dict(torque_p50=float(p50t), v282_p50=float(p50r), diff_median=md, diff_ci=list(ci))
        else:
            lr = np.log((x[ti] + 0.05) / (x[ri] + 0.05))
            clust = route[ti] if n_routes_t > 1 else route[ri]
            if n_routes_t > 1 or n_routes_r > 1:
                geo, ci = boot_ci(lr, clust, lambda y: float(np.exp(np.mean(y))))
            else:
                geo, ci = float(np.exp(np.mean(lr))), (float(np.exp(np.mean(lr))), float(np.exp(np.mean(lr))))
            print(f'  {nm:16s} torque_p50={p50t:.3f} v282_p50={p50r:.3f}  ratio={ratio:.2f}  geo_ratio={geo:.2f} CI={tuple(round(c,2) for c in ci)}')
            out[nm] = dict(torque_p50=float(p50t), v282_p50=float(p50r), ratio=ratio, geo_ratio=geo, geo_ci=list(ci))
    return out


results = {}
for lo, hi in [(2, 8), (8, 15)]:
    print(f'\n=== v[{lo},{hi}) ===')
    results[f'baseline_{lo}-{hi}'] = run(TQ, g == 'V282', 'baseline (TORQUE_ALL vs all-V282, matched)', lo, hi)
    print()
    results[f'exclDom_{lo}-{hi}'] = run(TQ, (g == 'V282') & (route != DOM), 'excl dominant V282 route, matched', lo, hi)
    print()
    results[f'T4_vs_6c_{lo}-{hi}'] = run(g == 'T4', route == DOM, 'T4 alone vs 6c alone, matched', lo, hi)

json.dump(results, open(os.path.join(os.path.dirname(__file__), 'out_f3_matched_all_metrics.json'), 'w'), indent=1)
