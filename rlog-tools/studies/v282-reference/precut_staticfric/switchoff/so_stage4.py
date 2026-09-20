"""Stage 4: (a) the TIME fraction of a return episode on which the term is actually non-zero (the most
direct test of "its value is zero on returns"); (b) the realistic one-new-drive detection threshold for
FAIL clause 1, which must carry BOTH the within-route sampling noise and the route-to-route spread.
-> out/so_timefrac.json
"""
import sys, glob, json
import numpy as np
from solib import route_signals, episodes, OUT, LEVEL, g_of_v

TORQUE = ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd',
          '00000075--6c8687d5bd', '00000076--d0b7ea7e4d']
R = {}
rows = []
for rk in TORQUE:
    S = route_signals(rk)
    zo, aa = S['z_out'], S['aa']
    n = len(zo)
    for e in episodes(rk):
        i0, bk = e['i0'], e['bk']
        s = float(np.sign(aa[bk])) or 1.0
        end = min(n - 1, bk + int(round(e['slip_s'] * 100)))
        zs = zo[i0:end + 1] * s
        if not len(zs):
            continue
        rows.append(dict(route=rk, group=S['group'], v=e['v'], ret=bool(e['sjump'] == -s),
                         f_out=float(np.mean(zs >= 0.25 * LEVEL)), f_in=float(np.mean(zs <= -0.25 * LEVEL)),
                         f_zero=float(np.mean(np.abs(zs) < 0.25 * LEVEL)),
                         f_out50=float(np.mean(zs >= 0.5 * LEVEL)), f_in50=float(np.mean(zs <= -0.5 * LEVEL)),
                         mean_abs=float(np.mean(np.abs(zs))), frames=len(zs)))
    del S
col = lambda k: np.array([r[k] for r in rows], dtype=float if not isinstance(rows[0][k], str) else object)
v = col('v').astype(float); ret = col('ret').astype(bool); route = np.array([r['route'] for r in rows])
P = lambda x, q: float(np.percentile(x, q))
R['time_fraction'] = {}
for nm, lo, hi in (('2-8', 2, 8), ('8-12', 8, 12), ('2-12', 2, 12)):
    for lbl, m0 in (('return', ret), ('depart', ~ret)):
        m = m0 & (v >= lo) & (v < hi)
        if m.sum() < 5:
            continue
        # frame-weighted, so it is a true time fraction over the episode population
        wgt = col('frames').astype(float)[m]
        tw = lambda k: float(np.sum(col(k).astype(float)[m] * wgt) / np.sum(wgt))
        R['time_fraction'][f'{nm}|{lbl}'] = dict(n=int(m.sum()), frames=int(wgt.sum()),
            time_frac_outward_ge25=tw('f_out'), time_frac_inward_ge25=tw('f_in'), time_frac_near_zero=tw('f_zero'),
            time_frac_outward_ge50=tw('f_out50'), time_frac_inward_ge50=tw('f_in50'),
            mean_abs_z_out=tw('mean_abs'),
            frac_episodes_any_inward_ge25=float(np.mean(col('f_in').astype(float)[m] > 0)),
            frac_episodes_inward_ge25_over_10pct_of_time=float(np.mean(col('f_in').astype(float)[m] > 0.10)),
            frac_episodes_untouched=float(np.mean((col('f_out').astype(float)[m] == 0) & (col('f_in').astype(float)[m] == 0))))

# ---------- (b) one-new-drive detection threshold ----------
POW = json.load(open(OUT + '/so_power.json'))
R['one_drive_threshold'] = {}
for nm in ('2-8', '2-12'):
    d = POW['clause1_power'][nm]
    brs = d.get('between_route_spread')
    out = {}
    for stat, key in (('return_dwell_p50', 'dwell_p50'), ('return_os30_p90', 'os30_p90')):
        sd_between = brs[f'{key}_sd'] if brs else None
        for nsub in (11, 20, 29):
            k = f'{key}|n={nsub}'
            if k not in d:
                continue
            sd_within = d[k]['sd_of_stat']
            tot = float(np.hypot(sd_within, sd_between))
            out[f'{stat}|n={nsub}'] = dict(base=d[k]['base'], sd_within=sd_within, sd_between=sd_between,
                                           sd_total=tot, detect_thr_95=1.96 * tot, mde_80pct=2.80 * tot)
    R['one_drive_threshold'][nm] = out

# what the term is MEANT to remove, in the same units: the outward requirement it cancels, converted to
# dwell seconds at the measured through-dwell command build rate (EVIDENCE: ss_analyze net_swing / dwell)
BUILD = 0.0313 / 0.48        # torque/s, torque routes 2-8 m/s, median over 145 dwells
R['effect_scale'] = dict(build_rate_torque_per_s=BUILD,
                         z_hold_p50_2_8=0.0194, hw_2_8=0.0333,
                         seconds_of_dwell_removed=0.0194 / BUILD,
                         note='the dwell shortening a full-dose one-sided term would produce on the side it acts on; '
                              'a wrong-sign or symmetric implementation would produce a shift of this order on RETURNS')
json.dump(R, open(OUT + '/so_timefrac.json', 'w'), indent=1, default=float)
r3 = lambda x: round(x, 3)
for k, x in R['time_fraction'].items():
    print(k, {a: (r3(b) if isinstance(b, float) else b) for a, b in x.items()})
print()
for nm, o in R['one_drive_threshold'].items():
    for k, x in o.items():
        print(nm, k, {a: (r3(b) if isinstance(b, float) else b) for a, b in x.items()})
print()
print('effect_scale', {a: (r3(b) if isinstance(b, float) else b) for a, b in R['effect_scale'].items()})
