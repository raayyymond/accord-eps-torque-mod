"""Re-derive s5_07's matched-event comparison with explicit controls for the CONFOUND lens:
  1. leave-one-route-out on the V282 reference (drop the dominant 2bc842dbac, 84% of V282 primary events)
  2. per-route breakdown of the torque-mode side (T64 has only 2 routes, 28+18 events)
  3. route-block bootstrap CI (resample ROUTES, not events) in addition to the event-level CI
  4. explicit speed/adr match-quality check (are matches close, or is this extrapolating?)
Uses the SAME event rows s5_04 already computed (s5_04_events_rows.json) -- no new data pulled, no v282cmp edits.
"""
import json
import numpy as np

SRC = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism/s5_04_events_rows.json'
rows = json.load(open(SRC))
METRICS = ['ang_lag', 'ang_gain', 'ang_err_deg', 'rate_gain', 'hf', 'la_pose_gain', 'la_pose_lag', 'la_act_rough']
rng = np.random.default_rng(1)

def match(ref_rows, grp, vb):
    pairs = []
    for r in rows:
        if r['g'] != grp or not (vb[0] <= r['v'] < vb[1]):
            continue
        best, bd = None, 1e9
        for q in ref_rows:
            if abs(q['v'] - r['v']) > 3 or not (0.67 <= r['ad_rate_pk'] / max(q['ad_rate_pk'], 1e-6) <= 1.5):
                continue
            dist = abs(np.log(r['ad_rate_pk'] / q['ad_rate_pk'])) + abs(q['v'] - r['v']) / 10
            if dist < bd:
                best, bd = q, dist
        if best is not None:
            pairs.append((r, best, bd))
    return pairs

def summarize(pairs, label):
    if len(pairs) < 5:
        print(f'  {label}: only {len(pairs)} pairs, SKIP')
        return None
    out = dict(n=len(pairs))
    out['v_t'] = float(np.median([r['v'] for r, _, _ in pairs]))
    out['v_ref'] = float(np.median([q['v'] for _, q, _ in pairs]))
    out['adr_t'] = float(np.median([r['ad_rate_pk'] for r, _, _ in pairs]))
    out['adr_ref'] = float(np.median([q['ad_rate_pk'] for _, q, _ in pairs]))
    out['match_dist_med'] = float(np.median([d for _, _, d in pairs]))
    t_routes = sorted(set(r['rk'] for r, _, _ in pairs))
    ref_routes = sorted(set(q['rk'] for _, q, _ in pairs))
    out['t_routes'] = t_routes
    out['ref_routes'] = ref_routes
    for m in METRICS:
        pr = [(r[m], q[m]) for r, q, _ in pairs if m in r and m in q and np.isfinite(r[m]) and np.isfinite(q[m])]
        if len(pr) < 5:
            continue
        t = np.array([a for a, _ in pr]); f = np.array([b for _, b in pr]); d = t - f
        # event-level bootstrap
        bs = [np.median(rng.choice(d, len(d))) for _ in range(1000)]
        # route-block bootstrap: resample the SET OF TORQUE ROUTES WITH REPLACEMENT (conservative)
        pairs_by_troute = {}
        for (r, q, _) in pairs:
            pairs_by_troute.setdefault(r['rk'], []).append(r[m] - q[m])
        troutes = list(pairs_by_troute.keys())
        rb = []
        if len(troutes) >= 2:
            for _ in range(1000):
                chosen = rng.choice(troutes, len(troutes))
                pooled = np.concatenate([pairs_by_troute[c] for c in chosen])
                rb.append(np.median(pooled))
        out[m] = dict(t=round(float(np.median(t)), 3), ref=round(float(np.median(f)), 3), diff=round(float(np.median(d)), 3),
                      ci_event=[round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)],
                      ci_routeblock=([round(float(np.percentile(rb, 2.5)), 3), round(float(np.percentile(rb, 97.5)), 3)] if rb else None),
                      n_t_routes=len(troutes))
    print(f'  {label}: n={out["n"]} v_t={out["v_t"]:.1f} v_ref={out["v_ref"]:.1f} adr_t={out["adr_t"]:.1f} adr_ref={out["adr_ref"]:.1f}')
    print(f'    t_routes={out["t_routes"]}')
    print(f'    ref_routes={out["ref_routes"]}')
    for m in METRICS:
        if m in out:
            v = out[m]
            print(f'    {m:14s} diff={v["diff"]:+.3f}  event_CI={v["ci_event"]}  routeblockCI={v["ci_routeblock"]}  (n_troutes={v["n_t_routes"]})')
    return out

V282_ALL = [r for r in rows if r['g'] == 'V282']
V282_NO_6c = [r for r in rows if r['g'] == 'V282' and r['rk'] != '0000006c--2bc842dbac']
print('V282 route event counts:', {rk: sum(1 for r in V282_ALL if r['rk']==rk) for rk in set(r['rk'] for r in V282_ALL)})
print('V282 WITHOUT dominant route event counts:', {rk: sum(1 for r in V282_NO_6c if r['rk']==rk) for rk in set(r['rk'] for r in V282_NO_6c)})

results = {}
for grp in ('T64', 'T64B', 'T5', 'T4'):
    for vb in ((8, 15), (15, 99)):
        print(f'\n=== {grp} v{vb[0]}-{vb[1]} ===')
        print(' -- FULL V282 reference --')
        p_full = match(V282_ALL, grp, vb)
        r_full = summarize(p_full, 'full-ref')
        print(' -- V282 WITHOUT 2bc842dbac (leave-one-route-out) --')
        p_loo = match(V282_NO_6c, grp, vb)
        r_loo = summarize(p_loo, 'loo-ref')
        results[f'{grp}|v{vb[0]}-{vb[1]}'] = dict(full=r_full, loo=r_loo)

json.dump(results, open('redo_matched_results.json', 'w'), indent=1, default=str)
