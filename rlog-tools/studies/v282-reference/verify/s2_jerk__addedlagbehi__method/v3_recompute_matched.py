"""Independent re-derivation of the matched-pair act.slag diff for T64 vs V282, hi>=15 m/s stratum, and v8-15.
Own match() and own bootstrap, not importing s2_common."""
import sys, json, glob
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import numpy as np
import v282cmp as V

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s2_jerk/_out'
VBINS = [(3, 8), (8, 15), (15, 22), (22, 40)]
def vbin(v):
    for i, (a, b) in enumerate(VBINS):
        if a <= v < b:
            return i
    return -1

rows = []
for f in sorted(glob.glob(f'{OUT}/events_*.npz')):
    D = np.load(f, allow_pickle=True)
    r = json.loads(str(D['rows']))
    for x in r:
        x['vb'] = vbin(x['v'])
    rows += r

REF = [r for r in rows if r['group'] == 'V282']
TQ  = [r for r in rows if r['group'] == 'T64']
print("n V282 events:", len(REF), "n T64 events:", len(TQ))
print("V282 routes:", sorted(set(r['route'] for r in REF)))
print("T64 routes:", sorted(set(r['route'] for r in TQ)))
print("V282 type counts:", {t: sum(r['type']==t for r in REF) for t in set(r['type'] for r in REF)})
print("T64 type counts:", {t: sum(r['type']==t for r in TQ) for t in set(r['type'] for r in TQ)})

def match(ref, tq, cal_j=0.35, cal_s=0.35, cal_v=0.25):
    used = set(); pairs = []
    for i, t in sorted(enumerate(tq), key=lambda it: -it[1]['jerk']):
        best, bd, best_i = None, 1e9, None
        for j, r in enumerate(ref):
            if j in used or r['type'] != t['type'] or r['vb'] != t['vb']:
                continue
            dj = abs(np.log(r['jerk'] / t['jerk'])); ds = abs(np.log(max(r['step'], .05) / max(t['step'], .05)))
            dv = abs(np.log(r['v'] / t['v']))
            if dj > cal_j or ds > cal_s or dv > cal_v:
                continue
            d = dj**2 + ds**2 + dv**2
            if d < bd:
                bd, best, best_i = d, r, j
        if best is not None:
            used.add(best_i); pairs.append((best, t))
    return pairs

pairs_all = match(REF, TQ)
print("n matched pairs (all strata):", len(pairs_all))

def boot_diff(pairs, key, n=4000, seed=123, stat=np.median):
    rng = np.random.default_rng(seed)
    d = np.array([p[1].get(key, np.nan) - p[0].get(key, np.nan) for p in pairs], float)
    ok = np.isfinite(d)
    d = d[ok]; rts = np.array([p[1]['route'] for p, o in zip(pairs, ok) if o])
    if len(d) < 3:
        return dict(n=len(d), med=np.nan, ci_ev=(np.nan, np.nan), ci_rt=(np.nan, np.nan))
    be = [stat(d[rng.integers(0, len(d), len(d))]) for _ in range(n)]
    ur = np.unique(rts); br = []
    for _ in range(n):
        pick = rng.choice(ur, len(ur))
        dd = np.concatenate([d[rts == u] for u in pick])
        dd = dd[rng.integers(0, len(dd), len(dd))]
        br.append(stat(dd))
    return dict(n=int(len(d)), med=float(stat(d)), ci_ev=tuple(np.percentile(be, [2.5, 97.5])),
                ci_rt=tuple(np.percentile(br, [2.5, 97.5])))

for sn, vbs in (('hi>=15', [2,3]), ('v8-15', [1])):
    P = [p for p in pairs_all if p[1]['vb'] in vbs]
    b = boot_diff(P, 'act.slag')
    ref_med = np.median([p[0]['act.slag'] for p in P])
    tq_med = np.median([p[1]['act.slag'] for p in P])
    print(f"{sn}: n_pairs={len(P)} ref_med={ref_med:.3f} tq_med={tq_med:.3f} diff={b['med']:+.3f} ci_ev=({b['ci_ev'][0]:+.3f},{b['ci_ev'][1]:+.3f}) ci_rt=({b['ci_rt'][0]:+.3f},{b['ci_rt'][1]:+.3f}) n={b['n']}")
    b2 = boot_diff(P, 'pose.slag')
    print(f"   pose.slag: diff={b2['med']:+.3f} ci_ev=({b2['ci_ev'][0]:+.3f},{b2['ci_ev'][1]:+.3f}) n={b2['n']}")
