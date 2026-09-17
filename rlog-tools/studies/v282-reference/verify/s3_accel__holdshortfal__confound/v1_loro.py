"""ADVERSARIAL CONFOUND CHECK for s3_accel finding 'hold-shortfall-and-late-buildup-sag'.

Reuses turn_events.json (the raw per-event metric extraction -- deterministic from s3turns.find_turns +
s3turns.metrics, not a statistical conclusion) but reimplements the matched-contrast statistic INDEPENDENTLY
of s3_stats.py, and adds what the finding's own pipeline did not report:
  1. Leave-one-route-out: does the effect survive dropping 0000006c--2bc842dbac, which supplies 16/27 (59%)
     of the V282 group's turn events (a single 62-segment day)?
  2. Per-route medians (not just the pooled/stratified estimate) -- is the sign consistent V282-route by
     V282-route and TQ-route by TQ-route, or is the effect one route's arithmetic mean overwhelming the rest?
  3. Cross-check aa (wheel-angle-minus-offset) against ap (livePose-yaw-derived) independently, both directions.
  4. The matched-cell composition itself (which strata actually carry the weight).
"""
import json
import numpy as np

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel/out/'
D = json.load(open(OUT + 'turn_events.json'))
rows = D['rows']

GM = {"V282": "V282", "V282old": "V282old", "T64": "TQ", "T64B": "TQ", "T5": "TQ", "T4": "TQ"}
for r in rows:
    r['G'] = GM[r['group']]


def strata(r):
    vb = 0 if r['v'] < 5 else (1 if r['v'] < 8 else 2)
    pb = 0 if r['P'] < 60 else (1 if r['P'] < 150 else 2)
    return vb, pb


VB = ["2.5-5", "5-8", "8-15"]; PB = ["25-60", "60-150", "150+"]
rng = np.random.default_rng(7)
NB = 3000


def strat_diff(A, B, k, NB=NB):
    cells = {}
    for r in A:
        cells.setdefault(strata(r), [[], []])[0].append(r.get(k, np.nan))
    for r in B:
        cells.setdefault(strata(r), [[], []])[1].append(r.get(k, np.nan))
    use = {c: (np.array(a, float), np.array(b, float)) for c, (a, b) in cells.items()}
    use = {c: (a[np.isfinite(a)], b[np.isfinite(b)]) for c, (a, b) in use.items()}
    use = {c: ab for c, ab in use.items() if len(ab[0]) >= 2 and len(ab[1]) >= 2}
    if not use:
        return None
    w = {c: min(len(a), len(b)) for c, (a, b) in use.items()}; W = sum(w.values())

    def est(sampler):
        return sum(w[c] * (np.mean(sampler(b)) - np.mean(sampler(a))) for c, (a, b) in use.items()) / W
    e0 = est(lambda x: x)
    bs = [est(lambda x: x[rng.integers(0, len(x), len(x))]) for _ in range(NB)]
    return dict(diff=float(e0), ci=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                cells={f"{VB[c[0]]}|{PB[c[1]]}": [len(a), len(b)] for c, (a, b) in use.items()}, n_matched=int(W))


def by_route_median(sub, k):
    routes = sorted(set(r['rk'] for r in sub))
    out = {}
    for rk in routes:
        x = np.array([r.get(k, np.nan) for r in sub if r['rk'] == rk], float)
        x = x[np.isfinite(x)]
        out[rk] = (float(np.median(x)), len(x))
    return out


print("=== per-route event counts by group ===")
from collections import Counter
print(Counter((r['G'], r['rk']) for r in rows if True))
cnt = Counter(r['rk'] for r in rows if r['G'] == 'V282')
print("V282 route event counts:", dict(cnt), " -> 2bc842dbac fraction of V282 events:",
      cnt.get('0000006c--2bc842dbac', 0) / sum(cnt.values()))

full_V282 = [r for r in rows if r['G'] == 'V282']
loro_V282 = [r for r in rows if r['G'] == 'V282' and r['rk'] != '0000006c--2bc842dbac']
TQall = [r for r in rows if r['G'] == 'TQ']
T64 = [r for r in rows if r['group'] in ('T64', 'T64B')]

print(f"\nV282 n={len(full_V282)}  V282-minus-2bc842dbac n={len(loro_V282)}  TQall n={len(TQall)}  T64 n={len(T64)}")

print("\n=== per-route MEDIAN hold error (aa, ap), + n events -- is the sign route-consistent? ===")
for k in ('aa_hold_err', 'ap_hold_err'):
    print(f" -- {k} --")
    for r in full_V282 + TQall:
        pass
    byr = by_route_median(full_V282, k)
    for rk, (m, n) in sorted(byr.items()):
        print(f"   V282   {rk:24s} median={m:+.4f} n={n}")
    byr = by_route_median(TQall, k)
    for rk, (m, n) in sorted(byr.items()):
        print(f"   TQ     {rk:24s} median={m:+.4f} n={n}")

print("\n=== FULL (as-reported) matched stratified diff, TQall - V282 ===")
for k in ('aa_hold_err', 'ap_hold_err'):
    c = strat_diff(full_V282, TQall, k)
    print(f"  {k:14s} diff={c['diff']:+.4f} ci={c['ci']} matched={c['n_matched']} cells={c['cells']}")

print("\n=== LORO: matched stratified diff, TQall - (V282 minus 2bc842dbac) ===")
for k in ('aa_hold_err', 'ap_hold_err'):
    c = strat_diff(loro_V282, TQall, k)
    if c is None:
        print(f"  {k:14s} NO MATCHED CELLS SURVIVE dropping 2bc842dbac")
        continue
    print(f"  {k:14s} diff={c['diff']:+.4f} ci={c['ci']} matched={c['n_matched']} cells={c['cells']}")

print("\n=== LORO restricted to T64/T64B only (as-shipped rev 6.4, drop T5/T4 dev builds) ===")
for k in ('aa_hold_err', 'ap_hold_err'):
    c = strat_diff(loro_V282, T64, k)
    if c is None:
        print(f"  {k:14s} NO MATCHED CELLS SURVIVE")
        continue
    print(f"  {k:14s} diff={c['diff']:+.4f} ci={c['ci']} matched={c['n_matched']} cells={c['cells']}")

print("\n=== unmatched (pooled, NOT stratified) group means -- sanity ===")
for G, sub in [('V282', full_V282), ('V282(-2bc)', loro_V282), ('TQall', TQall), ('T64', T64)]:
    for k in ('aa_hold_err', 'ap_hold_err'):
        x = np.array([r.get(k, np.nan) for r in sub], float); x = x[np.isfinite(x)]
        print(f"  {G:12s} {k:14s} mean={np.mean(x):+.4f} median={np.median(x):+.4f} n={len(x)}")

json.dump(dict(note="see stdout"), open('v1_loro_marker.json', 'w'))
