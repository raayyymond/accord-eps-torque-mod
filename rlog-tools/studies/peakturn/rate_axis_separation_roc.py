# -*- coding: utf-8 -*-
"""Can a RATE-scheduled gain separate the 7-9 Hz oscillation from a normal hard curve?

gp-0x6ac0 (the PID LERP axis) is the FOC electrical rate. We do not have it on the
wire, so use |cs_rate| (steering-wheel rate) as a monotone proxy: motor rate is the
wheel rate times a fixed gear/pole ratio, so any separation in one appears in the other.

The question is an ROC question, not a means question: set a knot threshold high enough
to catch oscillating windows, and ask how many NORMAL windows it also catches.
"""
import numpy as np, glob, os
from scipy import signal

FS, NW = 100.0, 256
BUILD = {'21': 'V111', '22': 'V112', '23': 'V112', '77': 'V90', '78': 'V91', '79': 'V92',
         '7e': 'V96', '7f': 'V96', '85': 'V100', '95': 'V101', '96': 'V102', '97': 'STOCK',
         '9e': 'V103', 'a4': 'V104', 'a5': 'V105', 'a6': 'V106', '1e': 'V107'}


def windows(r):
    p = 'analysis-2020accord/_scratch/cache/r%s/r%s.npz' % (r, r)
    if not os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('cs_rate', 'cc_lat', 'cs_v', 'ang')):
        return None
    rate, lat, v, ang = [np.asarray(z[k]).astype(float) for k in ('cs_rate', 'cc_lat', 'cs_v', 'ang')]
    m = (lat > 0.5) & (v > 1.0)
    out = []
    for a in range(0, len(rate) - NW, NW // 2):
        sl = slice(a, a + NW)
        if m[sl].mean() < 0.99:
            continue
        x = rate[sl] - np.mean(rate[sl])
        f, P = signal.welch(x, FS, nperseg=NW, noverlap=NW // 2)
        b = (f >= 6) & (f <= 9)
        osc = np.sqrt(np.sum(P[b]) * (f[1] - f[0]))          # 6-9 Hz content
        pk = np.percentile(np.abs(rate[sl]), 95)             # proxy for peak gp-0x6ac0
        out.append((osc, pk, np.mean(np.abs(ang[sl]))))
    return np.array(out) if out else None


A = []
for r in sorted(BUILD):
    w = windows(r)
    if w is not None:
        A.append(np.column_stack([w, np.full(len(w), BUILD[r] != 'STOCK')]))
A = np.vstack(A)
osc, pk, ang, ismod = A[:, 0], A[:, 1], A[:, 2], A[:, 3].astype(bool)

print("%d engaged windows across %d routes.\n" % (len(A), len(BUILD)))
hi = np.percentile(osc, 95)
OSC = osc >= hi                    # the oscillating windows we want to catch
NORM = (osc < np.percentile(osc, 60)) & (ang >= 20)   # normal HARD-CURVE windows we must not touch
print("  OSCILLATING  windows (6-9 Hz p95+):        n = %4d   median |rate| p95 = %6.2f deg/s"
      % (OSC.sum(), np.median(pk[OSC])))
print("  NORMAL HARD-CURVE windows (ang>=20, low 6-9 Hz): n = %4d   median |rate| p95 = %6.2f deg/s"
      % (NORM.sum(), np.median(pk[NORM])))

print("\n  ⇒ THE ROC: a knot placed at threshold T catches ...")
print("     T (deg/s)   %% of OSCILLATING caught   %% of NORMAL-CURVE caught   ratio")
for T in [10, 20, 30, 40, 60, 80, 100, 140, 200]:
    a = (pk[OSC] >= T).mean() * 100
    b = (pk[NORM] >= T).mean() * 100
    print("      %6d          %6.1f %%                 %6.1f %%           %s"
          % (T, a, b, ('%.2fx' % (a / b)) if b > 0.5 else '  inf'))

from scipy.stats import mannwhitneyu
u, p = mannwhitneyu(pk[OSC], pk[NORM], alternative='greater')
auc = u / (OSC.sum() * NORM.sum())
print("\n  AUC(oscillating > normal hard curve) on |rate| p95 = %.3f   (0.5 = no separation)  p = %.2e"
      % (auc, p))
print("  ⇒ %s" % ("SEPARABLE - a rate knot can act on the oscillation and largely spare normal curves"
                      if auc > 0.75 else
                      "WEAK/NO SEPARATION - a rate-scheduled knot would hit normal hard curves too"))
