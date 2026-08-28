# -*- coding: utf-8 -*-
"""Is deceleration a THRESHOLD trigger rather than a linear precursor?

The corpus-wide mean comparison gave 12/17 routes in the right direction but a CI spanning
zero (median -0.172 m/s^2, Wilcoxon p 0.189). The operator's own labelled event sits at
-1.159 m/s^2, 6.7x that. A threshold model -- "hard braking triggers it, gentle braking does
not" -- is invisible to a mean comparison, and it is the pre-registered next test.

Design: pool engaged windows across routes. A window is a CASE if its 6-9 Hz content is in
the top 5 % OF ITS OWN ROUTE (so route level cancels). Then measure the case rate as a
function of the preceding-2 s longitudinal acceleration. Under a threshold model the case
rate should be flat until some decel and then rise sharply.

Bootstrap unit is the ROUTE, per feedback-one-route-per-build-cannot-resolve-band-ratios.
"""
import numpy as np, os
from scipy import signal

FS, NW = 100.0, 256
ROUTES = ['21', '22', '23', '77', '78', '79', '7e', '7f', '85', '95', '96', '97', '9e',
          'a4', 'a5', 'a6', '1e']


def route(r):
    p = 'analysis-2020accord/_scratch/cache/r%s/r%s.npz' % (r, r)
    if not os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('cs_rate', 'cc_lat', 'cs_v', 'ang')):
        return None
    rate, lat, v, ang = [np.asarray(z[k]).astype(float) for k in ('cs_rate', 'cc_lat', 'cs_v', 'ang')]
    m = (lat > 0.5) & (v > 1.0)
    O, D, V, A = [], [], [], []
    for a in range(0, len(rate) - NW, NW // 2):
        b = a + NW
        if m[a:b].mean() < 0.99:
            continue
        lead0 = max(0, a - int(2.0 * FS))
        if a - lead0 < 50:
            continue
        f, P = signal.welch(rate[a:b] - np.mean(rate[a:b]), FS, nperseg=NW, noverlap=NW // 2)
        O.append(np.sqrt(np.sum(P[(f >= 6) & (f <= 9)]) * (f[1] - f[0])))
        D.append(np.mean(np.diff(v[lead0:a])) * FS)
        V.append(np.mean(v[a:b]) * 3.6)
        A.append(np.mean(np.abs(ang[a:b])))
    if len(O) < 40:
        return None
    O = np.array(O)
    return dict(route=r, case=O >= np.percentile(O, 95), dv=np.array(D),
                v=np.array(V), ang=np.array(A))


R = [x for x in (route(r) for r in ROUTES) if x]
print("  %d routes, %d engaged windows total.\n" % (len(R), sum(len(x['dv']) for x in R)))

BINS = [(-99, -1.0), (-1.0, -0.5), (-0.5, -0.2), (-0.2, 0.2), (0.2, 0.5), (0.5, 99)]
print("  case rate (top 5 %% of 6-9 Hz within each route) by PRECEDING-2 s acceleration")
print("     dv/dt bin (m/s^2)      n_win   case rate   vs overall 5.0 %   route-bootstrap CI")
rng = np.random.default_rng(0)
for lo, hi in BINS:
    per = []
    n = 0
    for x in R:
        s = (x['dv'] >= lo) & (x['dv'] < hi)
        n += s.sum()
        if s.sum() >= 8:
            per.append(x['case'][s].mean())
    if len(per) < 5:
        print("     [%5.1f, %5.1f)  %8d   too few routes with >=8 windows" % (lo, hi, n))
        continue
    per = np.array(per)
    bs = [np.mean(rng.choice(per, len(per))) for _ in range(4000)]
    print("     [%5.1f, %5.1f)  %8d   %6.2f %%     %5.2fx        [%4.2f %%, %4.2f %%]  (%d routes)"
          % (lo, hi, n, np.mean(per) * 100, np.mean(per) / 0.05,
             np.percentile(bs, 2.5) * 100, np.percentile(bs, 97.5) * 100, len(per)))

print("\n  THRESHOLD TEST: case rate for dv/dt below T vs at-or-above T, paired WITHIN route")
print("     T        n routes   below T   at/above T   ratio    route-bootstrap CI")
for T in (-1.0, -0.8, -0.6, -0.4, -0.2):
    lo_, hi_ = [], []
    for x in R:
        a = x['dv'] < T
        b = x['dv'] >= T
        if a.sum() >= 8 and b.sum() >= 8:
            lo_.append(x['case'][a].mean())
            hi_.append(x['case'][b].mean())
    if len(lo_) < 5:
        print("     %5.1f      too few routes" % T)
        continue
    lo_, hi_ = np.array(lo_), np.array(hi_)
    bs = [(lambda k: np.mean(lo_[k]) / max(np.mean(hi_[k]), 1e-9))(rng.integers(0, len(lo_), len(lo_)))
          for _ in range(4000)]
    print("     %5.1f      %4d      %6.2f %%   %6.2f %%    %5.2fx   [%4.2f, %4.2f]"
          % (T, len(lo_), np.mean(lo_) * 100, np.mean(hi_) * 100,
             np.mean(lo_) / max(np.mean(hi_), 1e-9), np.percentile(bs, 2.5), np.percentile(bs, 97.5)))
