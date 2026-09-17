"""s2_jerk shared loaders: event tables, speed bins, matching, cluster bootstrap."""
import json, glob, os
import numpy as np

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s2_jerk/_out'
VBINS = [(3, 8), (8, 15), (15, 22), (22, 40)]


def vbin(v):
    for i, (a, b) in enumerate(VBINS):
        if a <= v < b:
            return i
    return -1


def load_all():
    rows, traces = [], {}
    for f in sorted(glob.glob(f'{OUT}/events_*.npz')):
        D = np.load(f)
        r = json.loads(str(D['rows']))
        base = len(rows)
        for q, x in enumerate(r):
            x['uid'] = base + q; x['vb'] = vbin(x['v'])
        rows += r
        for k in D.files:
            if k == 'rows':
                continue
            if len(r):
                traces.setdefault(k, []).append(D[k])
    traces = {k: np.concatenate(v, 0) for k, v in traces.items()}
    return rows, traces


def match(ref, tq, cal_j=0.35, cal_s=0.35, cal_v=0.25):
    """Greedy 1:1 nearest-neighbour: exact type + speed bin; distance on log jerk, log step, log speed; calipers in log units.
    Returns list of (ref_row, tq_row). Torque events processed in descending jerk so the rare large ones match first."""
    used = set(); pairs = []
    for t in sorted(tq, key=lambda x: -x['jerk']):
        best, bd = None, 1e9
        for r in ref:
            if r['uid'] in used or r['type'] != t['type'] or r['vb'] != t['vb']:
                continue
            dj = abs(np.log(r['jerk'] / t['jerk'])); ds = abs(np.log(max(r['step'], .05) / max(t['step'], .05)))
            dv = abs(np.log(r['v'] / t['v']))
            if dj > cal_j or ds > cal_s or dv > cal_v:
                continue
            d = dj ** 2 + ds ** 2 + dv ** 2
            if d < bd:
                bd, best = d, r
        if best is not None:
            used.add(best['uid']); pairs.append((best, t))
    return pairs


def boot_diff(pairs, key, n=4000, seed=0, stat=np.median):
    """paired difference tq - ref; CI by (a) event bootstrap, (b) route-cluster bootstrap (resample torque routes)."""
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


def boot_group(rows, key, n=3000, seed=1, stat=np.median):
    """group-level stat with route-cluster + event bootstrap CI."""
    rng = np.random.default_rng(seed)
    x = np.array([r.get(key, np.nan) for r in rows], float); rt = np.array([r['route'] for r in rows])
    ok = np.isfinite(x); x, rt = x[ok], rt[ok]
    if len(x) < 3:
        return dict(n=len(x), med=np.nan, ci=(np.nan, np.nan))
    ur = np.unique(rt); b = []
    for _ in range(n):
        pick = rng.choice(ur, len(ur))
        xx = np.concatenate([x[rt == u] for u in pick]); b.append(stat(xx[rng.integers(0, len(xx), len(xx))]))
    return dict(n=int(len(x)), med=float(stat(x)), ci=tuple(np.percentile(b, [2.5, 97.5])))
