"""Independent re-check of F5 (matched stick-slip 'no real size difference' claim) under the
CONFOUND lens: match on speed/angle/demand does not control for route/day; V282 side is
dominated by one route (0000006c--2bc842dbac, 230/309 = 74% of V282 episodes); T64B alone
carries 4x the demand of the other torque routes.

Re-derives from the SAME per-episode npz tables the original script wrote (out/*_ss.npz),
but:
  1. reports route composition per group (never taken on trust),
  2. reruns nearest-neighbour matching (v, |aa|, demand-rate) with a route-cluster bootstrap
     that resamples BOTH sides (the original 'matched' boot_ci only resampled the torque-side
     route, leaving the single-dominant-V282-route dependency invisible in its own CI),
  3. reruns with the dominant V282 route (0000006c--2bc842dbac) held out,
  4. reruns with T64B held out (its 4x-demand outlier),
  5. reruns leaving ONE V282 route in at a time (leave-two-out / single-route V282) to see
     how much the point estimate moves route to route -- if it moves more than the quoted CI,
     the CI is not a fair band and the "about equal" reading does not survive a real
     route-independence check.
"""
import sys, json
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip')
import numpy as np
from ss_load import load_all
from sslib import k_of_v

EP, W, EX, VAL = load_all()
N = len(EP)
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); sj = col('sjump'); route = col('route')
slip = col('slip'); j30 = col('j30'); aa_abs = col('abs_aa'); dr = col('dem_rate')
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
SB = [(2, 8), (8, 15)]

print('=== route composition per group ===')
for grp in sorted(set(g)):
    m = g == grp
    rks, cnts = np.unique(route[m], return_counts=True)
    frac = cnts / cnts.sum()
    print(f'{grp:8s} n={m.sum():4d}', {r: f'{c} ({f:.0%})' for r, c, f in zip(rks, cnts, frac)})

V282_DOM = '0000006c--2bc842dbac'


def match(tmask, rmask):
    ti = np.where(tmask)[0]; ri = np.where(rmask)[0]; pairs = []
    for i in ti:
        if len(ri) == 0:
            continue
        dv = np.abs(v[ri] - v[i]) / 2.0
        da = np.abs(np.log1p(aa_abs[ri]) - np.log1p(aa_abs[i])) / 0.5
        dd = np.abs(np.log(dr[ri]) - np.log(dr[i])) / 0.5
        dist = np.sqrt(dv ** 2 + da ** 2 + dd ** 2)
        j = np.argmin(dist)
        if dist[j] <= 1.5:
            pairs.append((i, ri[j]))
    return pairs


def two_sample_route_boot(ti, ri, nb=2000, seed=3):
    """Route-cluster bootstrap resampling BOTH the torque-side and the v282-side route sets
    independently (unlike the original ss_analyze.match's boot_ci, which only clustered on
    the torque route and left the v282 route fixed per torque episode)."""
    rt = route[ti]; rr = route[ri]
    ut = np.unique(rt); ur = np.unique(rr)
    rng = np.random.default_rng(seed)
    est = np.exp(np.mean(np.log((slip[ti] + 0.3) / (slip[ri] + 0.3))))
    bs = []
    # index pairs grouped by (torque route) since ri is a function of ti (nearest neighbour);
    # resample torque routes normally, and INDEPENDENTLY jitter which v282 route's episodes
    # are eligible by resampling v282 routes and re-matching only within the resampled pool.
    for _ in range(nb):
        pick_t = rng.choice(ut, len(ut))
        it = np.concatenate([np.where(rt == c)[0] for c in pick_t]) if len(ut) else np.array([], int)
        pick_r = rng.choice(ur, len(ur))
        ok_r = np.isin(rr[it], pick_r)
        it2 = it[ok_r]
        if len(it2) > 5:
            bs.append(np.exp(np.mean(np.log((slip[ti[it2]] + 0.3) / (slip[ri[it2]] + 0.3)))))
    return est, (np.percentile(bs, 2.5), np.percentile(bs, 97.5)) if bs else (np.nan, np.nan), len(bs)


def run(label, tmask, rmask):
    out = {}
    for lo, hi in SB:
        tm = tmask & (v >= lo) & (v < hi)
        rm = rmask & (v >= lo - 1) & (v < hi + 1)
        P_ = match(tm, rm)
        if len(P_) < 5:
            out[f'{lo}-{hi}'] = dict(n_pairs=len(P_), note='too few pairs')
            continue
        ti = np.array([p[0] for p in P_]); ri = np.array([p[1] for p in P_])
        est, ci, nb_used = two_sample_route_boot(ti, ri)
        v282_routes_used = sorted(set(route[ri]))
        out[f'{lo}-{hi}'] = dict(n_pairs=len(P_), slip_ratio_geo=float(est), ci95=[float(ci[0]), float(ci[1])],
                                  nb_used=nb_used, v282_routes_used=v282_routes_used,
                                  torque_routes_used=sorted(set(route[ti])),
                                  torque_slip_p50=float(np.median(slip[ti])), v282_slip_p50=float(np.median(slip[ri])))
    print(f'--- {label} ---')
    for k, x in out.items():
        print(' ', k, x)
    return out


R = {}
R['baseline_TORQUE_ALL_vs_V282'] = run('baseline: TORQUE_ALL vs V282 (two-sample route boot)', TQ, g == 'V282')
R['exclude_v282_dominant_route'] = run('exclude V282 dominant route 6c--2bc842dbac', TQ, (g == 'V282') & (route != V282_DOM))
R['only_v282_dominant_route'] = run('ONLY V282 dominant route 6c--2bc842dbac', TQ, (g == 'V282') & (route == V282_DOM))
R['exclude_T64B'] = run('exclude T64B (4x demand outlier)', TQ & (g != 'T64B'), g == 'V282')
R['exclude_both'] = run('exclude T64B AND V282 dominant route', TQ & (g != 'T64B'), (g == 'V282') & (route != V282_DOM))

print()
print('=== per-V282-route-only matches (leave-one-route-in), TORQUE_ALL vs each V282 route alone ===')
for rk in sorted(set(route[g == 'V282'])):
    R[f'v282_route_{rk}'] = run(f'TORQUE_ALL vs V282 route {rk} ONLY', TQ, (g == 'V282') & (route == rk))

json.dump(R, open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/verify/a_stickslip__F5__confound/results.json', 'w'), indent=1, default=float)
