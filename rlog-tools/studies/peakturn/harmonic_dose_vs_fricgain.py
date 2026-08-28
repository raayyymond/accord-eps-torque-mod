# -*- coding: utf-8 -*-
"""DOSE-RESPONSE: does harmonic strength track the Coulomb relay's gain across builds?

If the relay is the nonlinear excitation path for the 7-9 Hz mode, then the harmonic
structure it radiates should scale with its own small-signal gain,
    fric_gain = (K1/1024) * (12/knee)
which the build history varies 4x:

    0.00199  stock              (K1 102, knee 600)     1 route
    0.00398  V90/91/92/96/111/112 (K1 204 knee 600; K1 612 knee 1800)   8 routes
    0.00797  V100..V107         (K1 204, knee 300)     8 routes

The 0.00398-vs-0.00797 contrast is 8 routes against 8 -- it does NOT depend on the
single stock route, so it is the arm that can actually carry a conclusion.

PREDICTION (pre-registered): harmonic ratio rises with fric_gain.
FALSIFIER: flat or falling => the relay is not the excitation path, and V120's new
mechanism argument is withdrawn.
"""
import numpy as np, os
from scipy import signal
from scipy.stats import spearmanr

FS, NW = 100.0, 512
# route -> (build, fric_gain = (K1/1024)*(12/knee))
R = {'97': ('STOCK', 102 / 1024 * 12 / 600),
     '77': ('V90', 204 / 1024 * 12 / 600), '78': ('V91', 204 / 1024 * 12 / 600),
     '79': ('V92', 204 / 1024 * 12 / 600), '7e': ('V96', 204 / 1024 * 12 / 600),
     '7f': ('V96', 204 / 1024 * 12 / 600), '21': ('V111', 204 / 1024 * 12 / 600),
     '22': ('V112', 612 / 1024 * 12 / 1800), '23': ('V112', 612 / 1024 * 12 / 1800),
     '85': ('V100', 204 / 1024 * 12 / 300), '95': ('V101', 204 / 1024 * 12 / 300),
     '96': ('V102', 204 / 1024 * 12 / 300), '9e': ('V103', 204 / 1024 * 12 / 300),
     'a4': ('V104', 204 / 1024 * 12 / 300), 'a5': ('V105', 204 / 1024 * 12 / 300),
     'a6': ('V106', 204 / 1024 * 12 / 300), '1e': ('V107', 204 / 1024 * 12 / 300)}

f = signal.welch(np.zeros(NW), FS, nperseg=NW)[0]
b69 = (f >= 6) & (f <= 9)


def prom(P, ft, hw=1.0, gap=0.4):
    pk = (f >= ft - gap) & (f <= ft + gap)
    sh = (((f >= ft - hw - gap) & (f < ft - gap)) | ((f > ft + gap) & (f <= ft + hw + gap)))
    if pk.sum() == 0 or sh.sum() == 0:
        return np.nan
    return P[pk].max() / max(np.median(P[sh]), 1e-30)


def harmonic_ratio(r):
    p = 'analysis-2020accord/_scratch/cache/r%s/r%s.npz' % (r, r)
    if not os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('cs_rate', 'cc_lat', 'cs_v')):
        return None
    rate, lat, v = [np.asarray(z[k]).astype(float) for k in ('cs_rate', 'cc_lat', 'cs_v')]
    m = (lat > 0.5) & (v > 1.0)
    Ps = []
    for a in range(0, len(rate) - NW, NW // 2):
        sl = slice(a, a + NW)
        if m[sl].mean() < 0.99:
            continue
        x = rate[sl] - np.mean(rate[sl])
        Ps.append(signal.welch(x, FS, nperseg=NW, noverlap=NW // 2)[1])
    if len(Ps) < 40:
        return None
    E = np.array([P[b69].sum() for P in Ps])
    idx = np.argsort(E)[-max(int(0.05 * len(E)), 5):]
    h, c = [], []
    for i in idx:
        P = Ps[i]
        f0 = f[b69][np.argmax(P[b69])]
        for mlt in (2.0, 3.0):
            if f0 * mlt < f[-1] - 2:
                h.append(prom(P, f0 * mlt))
        for mlt in (2.37, 2.63):
            if f0 * mlt < f[-1] - 2:
                c.append(prom(P, f0 * mlt))
    h = np.array([x for x in h if np.isfinite(x)])
    c = np.array([x for x in c if np.isfinite(x)])
    return np.median(h) / np.median(c), len(idx)


rows = []
for r in sorted(R):
    hr = harmonic_ratio(r)
    if hr:
        rows.append((r, R[r][0], R[r][1], hr[0], hr[1]))

print("  route build   fric_gain   harmonic ratio   n_osc")
for r, b, g, hr, n in sorted(rows, key=lambda x: x[2]):
    print("   r%-4s %-6s  %.5f       %6.3f       %4d" % (r, b, g, hr, n))

g = np.array([x[2] for x in rows])
y = np.array([x[3] for x in rows])
rho, p = spearmanr(g, y)
print("\n  ALL %d routes:   Spearman rho = %+.3f   p = %.3f" % (len(rows), rho, p))

lo = y[np.isclose(g, 0.00398, atol=1e-4)]
hi = y[np.isclose(g, 0.00797, atol=1e-4)]
print("\n  THE ARM THAT DOES NOT DEPEND ON THE SINGLE STOCK ROUTE:")
print("     fric_gain 0.00398  (n=%d routes)  median harmonic ratio %.3f" % (len(lo), np.median(lo)))
print("     fric_gain 0.00797  (n=%d routes)  median harmonic ratio %.3f" % (len(hi), np.median(hi)))
print("     2x the relay gain =>  %+.1f %% change" % ((np.median(hi) / np.median(lo) - 1) * 100))
rng = np.random.default_rng(0)
bs = [np.median(rng.choice(hi, len(hi))) / np.median(rng.choice(lo, len(lo))) for _ in range(4000)]
print("     ROUTE-level bootstrap 95%% CI on that ratio: [%.3f, %.3f]   (1.0 = no dose response)"
      % (np.percentile(bs, 2.5), np.percentile(bs, 97.5)))
print("\n  ⇒ %s" % ("DOSE RESPONSE CONFIRMED - the relay drives the harmonics"
                    if np.percentile(bs, 2.5) > 1.0 else
                    "NO DOSE RESPONSE - doubling the relay gain does not raise the harmonics"))
