"""Adversarial re-test of s5_07_matched's hf ratio (torque vs V282, speed+demand matched):
1. Leave-one-route-out on the V282 REFERENCE side (159/190=84% of V282 events are route 2bc842dbac -- drop it).
2. A REAL route-block bootstrap (resample distinct routes, not pairs) on both sides, since s5_07's own bootstrap
   resamples PAIRS despite its docstring promising a route-block bootstrap (the `routes` variable it computes is
   dead code -- never used).
3. Per-individual-route hf medians (no matching) as a sanity check that low n / route dominance is not silently
   producing the ratio.
Uses the already-extracted s5_04_events_rows.json -- no route reload needed (rows already carry g/rk/v/ad_rate_pk/hf).
"""
import json
import numpy as np

BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism/'
rows = json.load(open(BASE + 's5_04_events_rows.json'))
rng = np.random.default_rng(0)

DOMINANT_V282 = '0000006c--2bc842dbac'


def match(torque_rows, ref_rows, vb):
    pairs = []
    for r in torque_rows:
        if not (vb[0] <= r['v'] < vb[1]):
            continue
        best, bd = None, 1e9
        for q in ref_rows:
            if abs(q['v'] - r['v']) > 3 or not (0.67 <= r['ad_rate_pk'] / max(q['ad_rate_pk'], 1e-6) <= 1.5):
                continue
            dist = abs(np.log(r['ad_rate_pk'] / q['ad_rate_pk'])) + abs(q['v'] - r['v']) / 10
            if dist < bd:
                best, bd = q, dist
        if best is not None:
            pairs.append((r, best))
    return pairs


def route_block_bootstrap(pairs, metric, n_boot=2000):
    """Resample by DISTINCT ROUTE PAIR-OF-ROUTES block: group pairs by (torque_route, ref_route), resample blocks."""
    from collections import defaultdict
    blocks = defaultdict(list)
    for r, q in pairs:
        blocks[(r['rk'], q['rk'])].append(r[metric] - q[metric])
    keys = list(blocks.keys())
    if len(keys) < 2:
        return None  # cannot block-bootstrap with <2 blocks
    meds = []
    for _ in range(n_boot):
        chosen = rng.choice(len(keys), len(keys), replace=True)
        d = np.concatenate([blocks[keys[i]] for i in chosen])
        meds.append(np.median(d))
    return float(np.median([blocks[k][j] for k in keys for j in range(len(blocks[k]))])), float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5)), len(keys)


print("=== per-route raw hf medians (no matching, sanity) ===")
for g in ('V282', 'T64', 'T64B', 'T5', 'T4'):
    for vb in ((8, 15), (15, 99)):
        by_route = {}
        for r in rows:
            if r['g'] == g and vb[0] <= r['v'] < vb[1] and np.isfinite(r.get('hf', np.nan)):
                by_route.setdefault(r['rk'], []).append(r['hf'])
        for rk, vals in by_route.items():
            print(f"  {g:6s} v{vb} {rk:26s} n={len(vals):3d} hf_med={np.median(vals):.3f}")

print("\n=== V282 reference: full vs LOO (drop dominant route) ===")
ref_full = [r for r in rows if r['g'] == 'V282']
ref_loo = [r for r in rows if r['g'] == 'V282' and r['rk'] != DOMINANT_V282]
print(f"ref_full n={len(ref_full)}  ref_loo(drop {DOMINANT_V282}) n={len(ref_loo)}")

results = {}
for grp in ('T64', 'T64B', 'T5', 'T4'):
    torque_rows = [r for r in rows if r['g'] == grp]
    for vb in ((8, 15), (15, 99)):
        row_out = {}
        for label, ref in (('full', ref_full), ('LOO_drop_6c', ref_loo)):
            pairs = match(torque_rows, ref, vb)
            if len(pairs) < 5:
                row_out[label] = dict(n=len(pairs), note='too few pairs')
                continue
            t = np.array([p[0]['hf'] for p in pairs]); f = np.array([p[1]['hf'] for p in pairs])
            diff = t - f
            # pair-resample CI (s5_07's own method, for comparison)
            bs_pair = [np.median(rng.choice(diff, len(diff))) for _ in range(1000)]
            rb = route_block_bootstrap(pairs, 'hf')
            distinct_ref_routes = sorted(set(p[1]['rk'] for p in pairs))
            row_out[label] = dict(
                n=len(pairs), distinct_ref_events=len(set(id(p[1]) for p in pairs)),
                distinct_ref_routes=distinct_ref_routes,
                torque_med=round(float(np.median(t)), 3), ref_med=round(float(np.median(f)), 3),
                ratio=round(float(np.median(t)) / max(float(np.median(f)), 1e-9), 2),
                pair_ci=[round(float(np.percentile(bs_pair, 2.5)), 3), round(float(np.percentile(bs_pair, 97.5)), 3)],
                route_block_ci=([round(rb[1], 3), round(rb[2], 3)], rb[3]) if rb else 'N/A (<2 route-blocks)')
        results[f'{grp}|v{vb[0]}-{vb[1]}'] = row_out
        print(f"\n{grp} v{vb}:")
        for label, d in row_out.items():
            print(f"  {label}: {json.dumps(d, default=str)}")

json.dump(results, open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s5_mechanism__feedbackceil__confound/v1_matched_loo.json', 'w'), indent=1)
