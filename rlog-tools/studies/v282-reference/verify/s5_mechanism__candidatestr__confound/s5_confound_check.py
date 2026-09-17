"""
Adversarial CONFOUND check on s5_mechanism finding 'candidate-structures-ranked'.

The finding's magnitude table's only empirical (non-simulated) number is the "measured matched V282 lag"
figure (0.23s @8-15 m/s, 0.14s @15-99 m/s) used as the scale/reference against which every candidate's
simulated lag reduction is judged.  That number comes from s5_07_matched.py, whose V282 reference pool
is NOT leave-one-route-out tested and is NOT actually route-block bootstrapped despite the docstring's
claim (the code resamples matched PAIRS, not ROUTES).

This script:
  (a) reproduces s5_07's matching for T64 (both speed bins) with the FULL V282 pool (sanity reproduction),
  (b) redoes it EXCLUDING route 0000006c--2bc842dbac, which supplies 159/190 (84%) of all V282 events in
      the s5_04 event table -- does the ang_lag number survive?
  (c) computes a genuine ROUTE-BLOCK bootstrap CI (resample V282 ROUTES, not pairs) for ang_lag, to
      check whether the docstring's claimed method would actually still support the same conclusion,
  (d) checks whether the matched-pair speed/demand calipers actually land close (already partly reported
      in s5_07's output, re-verified here),
  (e) reports the la_pose_lag figure (the fully independent achieved-position proxy; la_yaw already
      established unusable on this car) alongside ang_lag for the same matched pairs.
"""
import json
import numpy as np

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism/'
VOUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s5_mechanism__candidatestr__confound/'
rows = json.load(open(OUT + 's5_04_events_rows.json'))
DOM_ROUTE = '0000006c--2bc842dbac'
METRICS = ['ang_lag', 'ang_gain', 'hf', 'la_pose_lag']
rng = np.random.default_rng(0)


def match(grp, vb, ref_pool):
    pairs = []
    for r in rows:
        if r['g'] != grp or not (vb[0] <= r['v'] < vb[1]):
            continue
        best, bd = None, 1e9
        for q in ref_pool:
            if abs(q['v'] - r['v']) > 3 or not (0.67 <= r['ad_rate_pk'] / max(q['ad_rate_pk'], 1e-6) <= 1.5):
                continue
            dist = abs(np.log(r['ad_rate_pk'] / q['ad_rate_pk'])) + abs(q['v'] - r['v']) / 10
            if dist < bd:
                best, bd = q, dist
        if best is not None:
            pairs.append((r, best))
    return pairs


def summarize(pairs, tag):
    if len(pairs) < 5:
        return dict(n=len(pairs), note='too few pairs')
    out = dict(n=len(pairs), distinct_ref=len(set(id(q) for _, q in pairs)),
               ref_routes=sorted(set(q['rk'] for _, q in pairs)),
               v_torque=round(float(np.median([r['v'] for r, _ in pairs])), 2),
               v_ref=round(float(np.median([q['v'] for _, q in pairs])), 2),
               adr_torque=round(float(np.median([r['ad_rate_pk'] for r, _ in pairs])), 2),
               adr_ref=round(float(np.median([q['ad_rate_pk'] for _, q in pairs])), 2))
    for m in METRICS:
        pr = [(r[m], q[m]) for r, q in pairs if m in r and m in q and np.isfinite(r[m]) and np.isfinite(q[m])]
        if len(pr) < 5:
            continue
        t = np.array([a for a, _ in pr]); f = np.array([b for _, b in pr])
        d = t - f
        # pair-level bootstrap (matches s5_07's method)
        bs_pair = [np.median(rng.choice(d, len(d))) for _ in range(1000)]
        # route-block bootstrap: resample V282 REFERENCE ROUTES with replacement (what the s5_07
        # docstring claims to do but the code does not)
        ref_routes = sorted(set(q['rk'] for _, q in pairs))
        bs_route = []
        if len(ref_routes) >= 2:
            for _ in range(1000):
                sampled = rng.choice(ref_routes, len(ref_routes), replace=True)
                idx = [i for i, (r, q) in enumerate(pairs) if q['rk'] in sampled]
                if len(idx) < 3:
                    continue
                dd = d[idx] if hasattr(d, '__getitem__') else None
                sub = np.array([d[i] for i in idx])
                bs_route.append(np.median(sub))
        out[m] = dict(torque=round(float(np.median(t)), 3), v282=round(float(np.median(f)), 3),
                      diff=round(float(np.median(d)), 3),
                      ci_pair=[round(float(np.percentile(bs_pair, 2.5)), 3), round(float(np.percentile(bs_pair, 97.5)), 3)],
                      ci_route_block=([round(float(np.percentile(bs_route, 2.5)), 3), round(float(np.percentile(bs_route, 97.5)), 3)]
                                       if bs_route else None),
                      n_ref_routes=len(ref_routes))
    print(f'--- {tag}: n={out["n"]} distinct_ref={out["distinct_ref"]} ref_routes={out["ref_routes"]} '
          f'v(t/r)={out["v_torque"]}/{out["v_ref"]} adr(t/r)={out["adr_torque"]}/{out["adr_ref"]}')
    for m in METRICS:
        if m in out:
            x = out[m]
            print(f'    {m:12s} torque={x["torque"]:+.3f} v282={x["v282"]:+.3f} diff={x["diff"]:+.3f} '
                  f'CI_pair={x["ci_pair"]} CI_route_block={x["ci_route_block"]} (n_ref_routes={x["n_ref_routes"]})')
    return out


ALL_V282 = [r for r in rows if r['g'] == 'V282']
NODOM_V282 = [r for r in ALL_V282 if r['rk'] != DOM_ROUTE]
print(f'V282 pool: {len(ALL_V282)} events total, {len(NODOM_V282)} excluding {DOM_ROUTE} '
      f'(dominant route supplies {len(ALL_V282) - len(NODOM_V282)}/{len(ALL_V282)} = '
      f'{100 * (len(ALL_V282) - len(NODOM_V282)) / len(ALL_V282):.0f}%)')

results = {}
print('\n=== PART A: full V282 pool (reproduction of s5_07) ===')
for vb in ((8, 15), (15, 99)):
    pairs = match('T64', vb, ALL_V282)
    results[f'A_full|T64|v{vb[0]}-{vb[1]}'] = summarize(pairs, f'A full V282, T64 v{vb[0]}-{vb[1]}')

print('\n=== PART B: V282 pool EXCLUDING dominant route 2bc842dbac ===')
for vb in ((8, 15), (15, 99)):
    pairs = match('T64', vb, NODOM_V282)
    results[f'B_nodom|T64|v{vb[0]}-{vb[1]}'] = summarize(pairs, f'B V282-nodom, T64 v{vb[0]}-{vb[1]}')

print('\n=== PART C: same for T64B, T5, T4 (full pool only, for breadth) ===')
for grp in ('T64B', 'T5', 'T4'):
    for vb in ((8, 15), (15, 99)):
        pairs = match(grp, vb, ALL_V282)
        results[f'C_full|{grp}|v{vb[0]}-{vb[1]}'] = summarize(pairs, f'C full V282, {grp} v{vb[0]}-{vb[1]}')
        pairs2 = match(grp, vb, NODOM_V282)
        results[f'C_nodom|{grp}|v{vb[0]}-{vb[1]}'] = summarize(pairs2, f'C nodom V282, {grp} v{vb[0]}-{vb[1]}')

json.dump(results, open(VOUT + 'verify_results.json', 'w'), indent=1, default=str)
print('\nWrote', VOUT + 'verify_results.json')
