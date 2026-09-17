"""ADVERSARIAL CONFOUND CHECK, part 2: the 'late build-up sag' (error 2-3.5 s into build-up, from ensemble.pkl).
Reimplements s3_pass3.py's err_late computation independently (per-event, per-route), then:
  1. per-route medians -- sign-consistent or route-driven?
  2. LORO: drop 0000006c--2bc842dbac from V282
  3. route-cluster bootstrap contrast V282 vs TQ, with and without that route
"""
import pickle
import numpy as np

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel/out/'
E = pickle.load(open(OUT + 'ensemble.pkl', 'rb'))
g = E['grid']
GM = {"V282": "V282", "V282old": "V282old", "T64": "TQ", "T64B": "TQ", "T5": "TQ", "T4": "TQ"}

rows = []
for e in E['ens']:
    tr = e['tr']['i']
    m2 = (g >= 2.0) & (g < 3.5)
    err_late = float(np.nanmean((tr['aa'] - tr['ad'])[m2]))
    m1 = (g >= 0) & (g < 1.0)
    err_early = float(np.nanmean((tr['aa'] - tr['ad'])[m1]))
    rows.append(dict(rk=e['rk'], group=e['group'], G=GM[e['group']], v=e['v'], P=e['P'],
                      err_late=err_late, err_early=err_early))

print("=== per-route median err_late (aa, 2-3.5s into build-up) ===")
from collections import defaultdict
byr = defaultdict(list)
for r in rows:
    byr[(r['G'], r['rk'])].append(r['err_late'])
for (G, rk), x in sorted(byr.items()):
    x = np.array(x); x = x[np.isfinite(x)]
    print(f"  {G:8s} {rk:24s} median={np.median(x):+.4f} mean={np.mean(x):+.4f} n={len(x)}")

rng = np.random.default_rng(11)
NB = 3000


def route_boot(sub, k='err_late', stat=np.nanmedian):
    routes = sorted(set(r['rk'] for r in sub))
    byrx = {rk: np.array([r[k] for r in sub if r['rk'] == rk], float) for rk in routes}
    x = np.array([r[k] for r in sub], float)
    est = float(stat(x[np.isfinite(x)]))
    bs = []
    for _ in range(NB):
        pick = rng.choice(routes, len(routes))
        z = np.concatenate([byrx[p][rng.integers(0, len(byrx[p]), len(byrx[p]))] for p in pick])
        bs.append(stat(z[np.isfinite(z)]))
    return est, float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5)), len(x), len(routes)


print("\n=== FULL group route-cluster bootstrap (median err_late) ===")
V282full = [r for r in rows if r['G'] == 'V282']
TQ = [r for r in rows if r['G'] == 'TQ']
T64 = [r for r in rows if r['group'] in ('T64', 'T64B')]
V282loro = [r for r in rows if r['G'] == 'V282' and r['rk'] != '0000006c--2bc842dbac']
for name, sub in [('V282', V282full), ('V282(-2bc)', V282loro), ('TQall', TQ), ('T64only', T64)]:
    e = route_boot(sub)
    print(f"  {name:12s} median={e[0]:+.4f} ci=[{e[1]:+.4f},{e[2]:+.4f}] n={e[3]} routes={e[4]}")

print("\n=== difference-of-medians bootstrap (paired route resample, TQ - V282), with/without 2bc842dbac ===")


def diff_boot(A, B, k='err_late', stat=np.nanmedian):
    ra = sorted(set(r['rk'] for r in A)); rb = sorted(set(r['rk'] for r in B))
    bya = {rk: np.array([r[k] for r in A if r['rk'] == rk], float) for rk in ra}
    byb = {rk: np.array([r[k] for r in B if r['rk'] == rk], float) for rk in rb}
    xa = np.array([r[k] for r in A], float); xb = np.array([r[k] for r in B], float)
    e0 = float(stat(xb[np.isfinite(xb)]) - stat(xa[np.isfinite(xa)]))
    bs = []
    for _ in range(NB):
        pa = rng.choice(ra, len(ra)); pb = rng.choice(rb, len(rb))
        za = np.concatenate([bya[p][rng.integers(0, len(bya[p]), len(bya[p]))] for p in pa])
        zb = np.concatenate([byb[p][rng.integers(0, len(byb[p]), len(byb[p]))] for p in pb])
        bs.append(stat(zb[np.isfinite(zb)]) - stat(za[np.isfinite(za)]))
    return e0, float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


for name, A, B in [("TQall-V282(full)", V282full, TQ), ("TQall-V282(LORO)", V282loro, TQ),
                    ("T64only-V282(full)", V282full, T64), ("T64only-V282(LORO)", V282loro, T64)]:
    e = diff_boot(A, B)
    print(f"  {name:24s} diff={e[0]:+.4f} ci=[{e[1]:+.4f},{e[2]:+.4f}]")

print("\n=== speed/peak composition check: median v and P per group (is TQ systematically different demand?) ===")
for name, sub in [('V282', V282full), ('V282(-2bc)', V282loro), ('TQall', TQ), ('T64only', T64)]:
    v = np.array([r['v'] for r in sub]); P = np.array([r['P'] for r in sub])
    print(f"  {name:12s} v median={np.median(v):.1f} [{np.percentile(v,25):.1f},{np.percentile(v,75):.1f}]  "
          f"P median={np.median(P):.0f} [{np.percentile(P,25):.0f},{np.percentile(P,75):.0f}]  n={len(sub)}")
