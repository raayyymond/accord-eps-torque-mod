"""s5_07: speed- and demand-matched V282 vs torque-mode event comparison (from s5_04_events_rows.json).

For every torque-mode event at v >= 8 m/s, the V282 (primary group) event with |dv| <= 3 m/s and desired-angle-rate peak within
x0.67-1.5 that is closest in log(adr) + |dv|/10 is its match (V282 events may be reused; the count of distinct V282 events is
reported).  Paired differences (torque - V282) per metric; median with a bootstrap CI over pairs, and a route-block bootstrap
(resample torque routes) as the conservative CI.
"""
import json
import numpy as np

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism/'
rows = json.load(open(OUT + 's5_04_events_rows.json'))
ref = [r for r in rows if r['g'] == 'V282']
METRICS = ['ang_lag', 'ang_gain', 'ang_err', 'ang_err_deg', 'rate_lag', 'rate_gain', 'hf', 'la_pose_gain', 'la_pose_lag', 'la_act_rough']
rng = np.random.default_rng(0)
res = {}
for grp in ('T64', 'T64B', 'T5', 'T4', 'V282old'):
    for vb in ((8, 15), (15, 99)):
        pairs = []
        for r in rows:
            if r['g'] != grp or not (vb[0] <= r['v'] < vb[1]):
                continue
            best, bd = None, 1e9
            for q in ref:
                if abs(q['v'] - r['v']) > 3 or not (0.67 <= r['ad_rate_pk'] / max(q['ad_rate_pk'], 1e-6) <= 1.5):
                    continue
                dist = abs(np.log(r['ad_rate_pk'] / q['ad_rate_pk'])) + abs(q['v'] - r['v']) / 10
                if dist < bd:
                    best, bd = q, dist
            if best is not None:
                pairs.append((r, best))
        if len(pairs) < 5:
            res[f'{grp}|v{vb[0]}-{vb[1]}'] = dict(n=len(pairs))
            continue
        out = dict(n=len(pairs), distinct_ref=len(set(id(q) for _, q in pairs)),
                   v_torque=float(np.median([r['v'] for r, _ in pairs])), v_ref=float(np.median([q['v'] for _, q in pairs])),
                   adr_torque=float(np.median([r['ad_rate_pk'] for r, _ in pairs])), adr_ref=float(np.median([q['ad_rate_pk'] for _, q in pairs])))
        routes = sorted(set(r['rk'] for r, _ in pairs))
        for m in METRICS:
            pr = [(r[m], q[m]) for r, q in pairs if m in r and m in q and np.isfinite(r[m]) and np.isfinite(q[m])]
            if len(pr) < 5:
                continue
            t = np.array([a for a, _ in pr]); f = np.array([b for _, b in pr]); d = t - f
            bs = [np.median(rng.choice(d, len(d))) for _ in range(1000)]
            out[m] = dict(torque=round(float(np.median(t)), 3), v282=round(float(np.median(f)), 3), diff=round(float(np.median(d)), 3),
                          ci=[round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)],
                          ratio=round(float(np.median(t)) / max(float(np.median(f)), 1e-9), 2))
        res[f'{grp}|v{vb[0]}-{vb[1]}'] = out
        print(grp, vb, json.dumps(out))
json.dump(res, open(OUT + 's5_07_matched.json', 'w'), indent=1)
