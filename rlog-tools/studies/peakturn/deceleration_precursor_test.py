# -*- coding: utf-8 -*-
"""IS THE OSCILLATION TRIGGERED BY DECELERATING INTO A TURN?

The case-control on the operator's own labelled event (r23, t=445.6-448.2) put two channels
at the extremes of six matched controls: speed at the 100th percentile (43.6 vs 25.4 km/h)
and d(speed)/dt at the 0th (-1.159 vs +0.619 m/s^2). Those are one physical fact --
BRAKING INTO A CORNER AT SPEED -- and it matches the operator's own words, "a fixed
oscillation during the peak of a hard curve".

n=6 gives p about 0.14, so it is a hypothesis, not a finding. Test it across the whole
corpus with real n: are oscillating windows preceded by deceleration more often than
matched non-oscillating windows?

Design: within each route, take the top 5 % of engaged windows by 6-9 Hz content as CASES
and the rest as the pool. For every case, draw CONTROLS from the SAME route matched on
speed and |angle|, then compare the mean longitudinal acceleration over the preceding 2 s.
Matching within route means route-level variance cannot drive it, and the unit for the
bootstrap is the ROUTE.
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
    W = []
    for a in range(0, len(rate) - NW, NW // 2):
        b = a + NW
        if m[a:b].mean() < 0.99:
            continue
        f, P = signal.welch(rate[a:b] - np.mean(rate[a:b]), FS, nperseg=NW, noverlap=NW // 2)
        osc = np.sqrt(np.sum(P[(f >= 6) & (f <= 9)]) * (f[1] - f[0]))
        lead0 = max(0, a - int(2.0 * FS))
        if a - lead0 < 50:
            continue
        W.append(dict(osc=osc, v=np.mean(v[a:b]) * 3.6, ang=np.mean(np.abs(ang[a:b])),
                      dv=np.mean(np.diff(v[lead0:a])) * FS))
    return W if len(W) >= 40 else None


rows = []
for r in ROUTES:
    W = route(r)
    if not W:
        continue
    o = np.array([w['osc'] for w in W])
    thr = np.percentile(o, 95)
    cases = [w for w in W if w['osc'] >= thr]
    pool = [w for w in W if w['osc'] < np.percentile(o, 60)]
    if len(cases) < 3 or len(pool) < 10:
        continue
    cd, td = [], []
    for c in cases:
        mt = [w for w in pool if abs(w['v'] - c['v']) < 15 and abs(w['ang'] - c['ang']) < 20]
        if len(mt) < 3:
            continue
        cd.append(c['dv'])
        td.append(np.median([w['dv'] for w in mt]))
    if len(cd) < 3:
        continue
    rows.append((r, len(cd), np.median(cd), np.median(td), np.median(cd) - np.median(td)))

print("  preceding-2 s mean longitudinal acceleration (m/s^2), CASES vs MATCHED CONTROLS\n")
print("  route  n_cases   case dv/dt   control dv/dt    difference")
for r, n, c, t, d in rows:
    print("   r%-4s   %4d     %+8.3f      %+8.3f      %+8.3f%s"
          % (r, n, c, t, d, '   <-- decelerating more' if d < 0 else ''))
d = np.array([x[4] for x in rows])
print("\n  %d routes.  routes where cases decelerate MORE than matched controls: %d of %d"
      % (len(rows), (d < 0).sum(), len(d)))
rng = np.random.default_rng(0)
bs = [np.median(rng.choice(d, len(d))) for _ in range(4000)]
print("  median difference = %+.4f m/s^2   ROUTE-level bootstrap 95%% CI [%+.4f, %+.4f]"
      % (np.median(d), np.percentile(bs, 2.5), np.percentile(bs, 97.5)))
from scipy.stats import wilcoxon
try:
    st, p = wilcoxon(d, alternative='less')
    print("  Wilcoxon signed-rank (cases decelerate more): p = %.4f" % p)
except Exception as e:
    print("  wilcoxon: %s" % e)
print("\n  ⇒ %s" % ("DECELERATION IS A REAL PRECURSOR" if np.percentile(bs, 97.5) < 0 else
                    "NOT SUPPORTED corpus-wide -- the event's deceleration does not generalise"))
