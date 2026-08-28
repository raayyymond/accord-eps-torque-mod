# -*- coding: utf-8 -*-
"""Head-to-head: does ANGLE separate the oscillation from normal driving better than RATE did?

Rate scored AUC 0.630 and was parked. The symptom is angle-gated, so angle is the
natural axis -- and table (b) at 0xC6B80 has 8 flat knots sitting in that region.
Same window set, same OSC definition, same comparison, so the two AUCs are comparable.
"""
import numpy as np, glob, os
from scipy import signal
from scipy.stats import mannwhitneyu

FS, NW = 100.0, 256
ROUTES = ['21', '22', '23', '77', '78', '79', '7e', '7f', '85', '95', '96', '97', '9e', 'a4', 'a5', 'a6', '1e']


def wins(r):
    p = 'analysis-2020accord/_scratch/cache/r%s/r%s.npz' % (r, r)
    if not os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('cs_rate', 'cc_lat', 'cs_v', 'ang')):
        return None
    rate, lat, v, ang = [np.asarray(z[k]).astype(float) for k in ('cs_rate', 'cc_lat', 'cs_v', 'ang')]
    m = (lat > 0.5) & (v > 1.0)
    o = []
    for a in range(0, len(rate) - NW, NW // 2):
        sl = slice(a, a + NW)
        if m[sl].mean() < 0.99:
            continue
        x = rate[sl] - np.mean(rate[sl])
        f, P = signal.welch(x, FS, nperseg=NW, noverlap=NW // 2)
        b = (f >= 6) & (f <= 9)
        o.append((np.sqrt(np.sum(P[b]) * (f[1] - f[0])),
                  np.percentile(np.abs(ang[sl]), 95),
                  np.percentile(np.abs(rate[sl]), 95)))
    return np.array(o) if o else None


A = np.vstack([w for w in (wins(r) for r in ROUTES) if w is not None])
osc, a95, r95 = A[:, 0], A[:, 1], A[:, 2]
OSC = osc >= np.percentile(osc, 95)
NORM = osc < np.percentile(osc, 60)          # ordinary driving, NOT restricted to hard curves
print("%d engaged windows;  OSCILLATING n = %d;  NORMAL n = %d\n" % (len(A), OSC.sum(), NORM.sum()))

for name, sig in (('ANGLE  p95|ang|  (deg)', a95), ('RATE   p95|rate| (deg/s)', r95)):
    u, p = mannwhitneyu(sig[OSC], sig[NORM], alternative='greater')
    auc = u / (OSC.sum() * NORM.sum())
    print("  %-26s AUC = %.3f   median osc %7.2f  vs normal %7.2f   ratio %.2fx"
          % (name, auc, np.median(sig[OSC]), np.median(sig[NORM]),
             np.median(sig[OSC]) / max(np.median(sig[NORM]), 1e-9)))

print("\n  ⇒ THE ROC ON ANGLE -- a knot placed at T degrees catches ...")
print("     T (deg)   %% OSCILLATING    %% NORMAL    ratio    (table-b knot)")
KN = {0.85: 'k1', 1.6: 'k2', 2.12: 'k3', 2.5: 'k4', 3.0: 'k5', 3.5: 'k6',
      3.94: 'k7', 4.34: 'k8', 4.79: 'k9', 5.21: 'k10', 5.7: 'k11', 11.94: 'k12'}
for T in [2.5, 3.0, 3.5, 3.94, 4.34, 4.79, 5.21, 5.7, 8.0, 11.94, 20.0]:
    a = (a95[OSC] >= T).mean() * 100
    b = (a95[NORM] >= T).mean() * 100
    print("     %6.2f      %6.1f %%      %6.1f %%    %5s     %s"
          % (T, a, b, ('%.2fx' % (a / b)) if b > 0.5 else 'inf', KN.get(T, '')))
