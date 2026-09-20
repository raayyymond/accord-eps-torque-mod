"""Independent re-derivation of F5 ('matched slip is about equal, torque/V282 ~1').
Fresh script: reads only the per-route episode tables (out/*_ss.npz, produced by ss_extract.py -- the
raw episode extraction, not the ss_analyze.py matching/statistics code under test). Re-implements the
nearest-neighbour match and the bootstrap independently, does not import ss_analyze.py or call match()/
boot_ci() from it.
"""
import sys, glob, json
import numpy as np

BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference'
OUTDIR = BASE + '/lowspeed/a_stickslip/out'

CH = ('cmd', 'P', 'I', 'F', 'hold_ff', 'move', 'z', 'rl', 'dob', 'hold_aa', 'aa', 'ad', 'angdes', 'sr', 'v')


def load(outdir):
    EP = []
    for f in sorted(glob.glob(outdir + '/*_ss.npz')):
        D = np.load(f, allow_pickle=True)
        EP += list(D['EP'])
    return EP


EP = load(OUTDIR)
N = len(EP)
print('N episodes', N)

col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); slip = col('slip'); j30 = col('j30')
aa_abs = col('abs_aa'); dr = col('dem_rate'); route = col('route')

TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
V282 = g == 'V282'
print('n torque (<15 m/s)', TQ.sum(), 'n V282', V282.sum())
print('counts by group', {gg: int((g == gg).sum()) for gg in np.unique(g)})

# sanity: dwell-based fields present and finite
for k in ('v', 'slip', 'j30', 'abs_aa', 'dem_rate'):
    x = col(k)
    assert np.all(np.isfinite(x)), f'{k} has non-finite values'
print('all key fields finite: OK')

# sanity: slip and j30 non-negative (they are defined as abs travel)
assert (slip >= 0).all() and (j30 >= 0).all()
print('slip, j30 >= 0: OK')


def independent_match(tmask, rmask, dv_scale=2.0, da_scale=0.5, dd_scale=0.5, max_dist=1.5, seed=0):
    """Independent re-implementation: for every torque episode, nearest V282 episode by
    (speed, log1p|angle|, log demand-rate) with WITH-REPLACEMENT nearest neighbour (same as original),
    but written from scratch and vectorised differently (broadcasting, not per-i loop distance calc
    reused from ss_analyze) to catch a copy/paste bug."""
    ti = np.where(tmask)[0]; ri = np.where(rmask)[0]
    if len(ti) == 0 or len(ri) == 0:
        return []
    Vr = v[ri]; Ar = np.log1p(aa_abs[ri]); Dr = np.log(dr[ri])
    pairs = []
    for i in ti:
        dv = (Vr - v[i]) / dv_scale
        da = (Ar - np.log1p(aa_abs[i])) / da_scale
        dd = (Dr - np.log(dr[i])) / dd_scale
        dist = np.sqrt(dv * dv + da * da + dd * dd)
        j = np.argmin(dist)
        if dist[j] <= max_dist:
            pairs.append((i, ri[j]))
    return pairs


def route_boot_geo_ratio(ti, ri_matched, route_of_t, nb=4000, seed=0):
    """Bootstrap CI of the geometric-mean ratio slip_torque/slip_v282 over MATCHED PAIRS, resampling by the
    torque episode's route (cluster bootstrap), independent RNG/implementation from ss_analyze.boot_ci."""
    lr = np.log((slip[ti] + 0.3) / (slip[ri_matched] + 0.3))
    clusters = route_of_t
    u = np.unique(clusters)
    rng = np.random.default_rng(seed)
    idx = {c: np.where(clusters == c)[0] for c in u}
    est = float(np.exp(np.mean(lr)))
    bs = []
    for _ in range(nb):
        pick = rng.choice(u, len(u))
        ii = np.concatenate([idx[c] for c in pick])
        bs.append(float(np.exp(np.mean(lr[ii]))))
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return est, (float(lo), float(hi))


results = {}
for lo, hi, label in [(2, 8, '<8'), (8, 15, '8-15')]:
    tm = TQ & (v >= lo) & (v < hi)
    rm = V282 & (v >= lo - 1) & (v < hi + 1)
    pairs = independent_match(tm, rm)
    ti = np.array([p[0] for p in pairs]); ri = np.array([p[1] for p in pairs])
    est, ci = route_boot_geo_ratio(ti, ri, route[ti])
    j30_t_p90 = float(np.percentile(j30[ti], 90))
    j30_r_p90 = float(np.percentile(j30[ri], 90))
    results[label] = dict(n_pairs=len(pairs), n_torque_stratum=int(tm.sum()), n_v282_pool=int(rm.sum()),
                           slip_ratio_geo=est, slip_ratio_ci=ci,
                           torque_slip_p50=float(np.median(slip[ti])), v282_slip_p50=float(np.median(slip[ri])),
                           torque_slip_p90=float(np.percentile(slip[ti], 90)), v282_slip_p90=float(np.percentile(slip[ri], 90)),
                           j30_torque_p90=j30_t_p90, j30_v282_p90=j30_r_p90)
    print(label, json.dumps(results[label], indent=1))

# cross-check against the checked-in ss_analyze.json TORQUE_ALL rows (same numbers should come back close,
# since this is the SAME underlying episode table with an independently-written matcher/bootstrap)
R = json.load(open(BASE + '/lowspeed/a_stickslip/out/ss_analyze.json'))
print()
print('=== reported (ss_analyze.json TORQUE_ALL) for comparison ===')
for lo, hi, label in [(2, 8, '2-8'), (8, 15, '8-15')]:
    row = R['matched'][f'TORQUE_ALL|{lo}-{hi}']
    print(label, dict(n_pairs=row['n_pairs'], slip_ratio_geo=row['slip_ratio_geo'],
                       torque_j30_p90=row['torque_j30_p90'], v282_j30_p90=row['v282_j30_p90']))

json.dump(results, open(BASE + '/lowspeed/verify/a_stickslip__F5__method/verify_f5_out.json', 'w'), indent=1)
