"""Confound check on F3 using the SAME nearest-neighbour match (v, log|aa|, log dem_rate) that
ss_analyze.py already uses to control for the demand-rate/angle confound this lens raises, then
re-runs it with the dominant V282 route and the 4x-demand T64B route excluded."""
import sys, os, json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'a_stickslip'))
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..', 'a_stickslip'))
from ss_load import load_all, PRE, boot_ci

EP, W, EX, VAL = load_all()
N = len(EP)
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); route = col('route'); aa_abs = col('abs_aa'); dr = col('dem_rate')
slip = col('slip'); j30 = col('j30'); dwell = col('dwell_s')

DOM = '0000006c--2bc842dbac'
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])


def match(tmask, rmask):
    ti = np.where(tmask)[0]; ri = np.where(rmask)[0]; pairs = []
    for i in ti:
        dv = np.abs(v[ri] - v[i]) / 2.0
        da = np.abs(np.log1p(aa_abs[ri]) - np.log1p(aa_abs[i])) / 0.5
        dd = np.abs(np.log(dr[ri]) - np.log(dr[i])) / 0.5
        dist = np.sqrt(dv ** 2 + da ** 2 + dd ** 2)
        j = np.argmin(dist)
        if dist[j] <= 1.5:
            pairs.append((i, ri[j]))
    return pairs


def run(tg_mask, rmask_base, label, lo, hi):
    tm = tg_mask & (v >= lo) & (v < hi)
    rm = rmask_base & (v >= lo - 1) & (v < hi + 1)
    P_ = match(tm, rm)
    if len(P_) < 5:
        print(f'{label} v[{lo},{hi}): n_pairs={len(P_)} (insufficient)')
        return None
    ti = np.array([p[0] for p in P_]); ri = np.array([p[1] for p in P_])
    lr = np.log((slip[ti] + 0.3) / (slip[ri] + 0.3))
    geo, ci = boot_ci(lr, route[ti], lambda x: float(np.exp(np.mean(x))))
    n_v282_used = len(set(ri.tolist()))
    r_routes_used = sorted(set(route[ri].tolist()))
    out = dict(n_pairs=len(P_), n_torque_pool=int(tm.sum()), n_v282_pool=int(rm.sum()),
               torque_slip_p50=float(np.median(slip[ti])), v282_slip_p50=float(np.median(slip[ri])),
               torque_j30_p90=float(np.percentile(j30[ti], 90)), v282_j30_p90=float(np.percentile(j30[ri], 90)),
               slip_ratio_geo=geo, slip_ratio_ci=ci, v282_routes_matched_to=r_routes_used,
               dwell_torque_p50=float(np.median(dwell[ti])), dwell_v282_p50=float(np.median(dwell[ri])))
    print(f'{label} v[{lo},{hi}): n_pairs={len(P_)}  slip_ratio_geo={geo:.2f} CI={tuple(round(x,2) for x in ci)}  '
          f'v282 routes used: {r_routes_used}')
    return out


out = {}
for lo, hi in [(2, 8), (8, 15)]:
    print(f'\n=== v[{lo},{hi}) ===')
    out[f'baseline_{lo}-{hi}'] = run(TQ, g == 'V282', 'baseline(TORQUE_ALL vs all-V282)', lo, hi)
    out[f'exclDom_{lo}-{hi}'] = run(TQ, (g == 'V282') & (route != DOM), 'excl dominant V282 route', lo, hi)
    out[f'exclT64B_{lo}-{hi}'] = run(np.isin(g, ['T64', 'T5', 'T4']), g == 'V282', 'excl T64B', lo, hi)
    out[f'exclBoth_{lo}-{hi}'] = run(np.isin(g, ['T64', 'T5', 'T4']), (g == 'V282') & (route != DOM), 'excl both', lo, hi)
    out[f'T4_vs_exclDom_{lo}-{hi}'] = run(g == 'T4', (g == 'V282') & (route != DOM), 'T4 alone vs V282 excl-dom', lo, hi)
    out[f'T4_vs_6c_{lo}-{hi}'] = run(g == 'T4', route == DOM, 'T4 alone vs 6c alone', lo, hi)

json.dump(out, open(os.path.join(os.path.dirname(__file__), 'out_f3_matched_confound.json'), 'w'), indent=1)
