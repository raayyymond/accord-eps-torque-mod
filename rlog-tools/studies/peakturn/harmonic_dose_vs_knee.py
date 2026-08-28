# -*- coding: utf-8 -*-
"""Re-test the dose-response on the variable that actually controls RELAY SHAPE.

The relay is   fVar13 = clamp(POL * gp-0x6abc * 12 / knee, +-1)
and then       friction = EMA(|model| * K1/1024 * fVar13)

So K1 multiplies AFTER the relay -- pure gain, no shape change -- while KNEE sets
where the clamp bites, which IS the shape. A signum's harmonic content relative to
its fundamental is scale-invariant, so K1 cannot move a harmonic RATIO by construction.
My earlier test used fric_gain = (K1/1024)(12/knee), which conflates the two; that is
why it was flat. The shape variable is KNEE alone.

PREDICTION (pre-registered): SMALLER knee = harder signum = MORE harmonic content.
   knee 300  (V100..V107)          8 routes   -- hardest relay
   knee 600  (stock, V90..V96, V111) 7 routes
   knee 1800 (V112)                2 routes   -- softest / most linear relay
FALSIFIER: flat or rising with knee.
"""
import numpy as np, os
from scipy import signal
from scipy.stats import spearmanr

FS, NW = 100.0, 512
KNEE = {'97': ('STOCK', 600), '77': ('V90', 600), '78': ('V91', 600), '79': ('V92', 600),
        '7e': ('V96', 600), '7f': ('V96', 600), '21': ('V111', 600),
        '22': ('V112', 1800), '23': ('V112', 1800),
        '85': ('V100', 300), '95': ('V101', 300), '96': ('V102', 300), '9e': ('V103', 300),
        'a4': ('V104', 300), 'a5': ('V105', 300), 'a6': ('V106', 300), '1e': ('V107', 300)}

f = signal.welch(np.zeros(NW), FS, nperseg=NW)[0]
b69 = (f >= 6) & (f <= 9)


def prom(P, ft, hw=1.0, gap=0.4):
    pk = (f >= ft - gap) & (f <= ft + gap)
    sh = (((f >= ft - hw - gap) & (f < ft - gap)) | ((f > ft + gap) & (f <= ft + hw + gap)))
    if pk.sum() == 0 or sh.sum() == 0:
        return np.nan
    return P[pk].max() / max(np.median(P[sh]), 1e-30)


def hr(r):
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
        Ps.append(signal.welch(rate[sl] - np.mean(rate[sl]), FS, nperseg=NW, noverlap=NW // 2)[1])
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
    return np.median(h) / np.median(c)


rows = [(r, KNEE[r][0], KNEE[r][1], hr(r)) for r in sorted(KNEE)]
rows = [x for x in rows if x[3] is not None]
print("  KNEE = the relay's SATURATION THRESHOLD = its SHAPE\n")
print("  route build   knee   harmonic ratio")
for r, b, k, y in sorted(rows, key=lambda x: x[2]):
    print("   r%-4s %-6s %5d      %6.3f" % (r, b, k, y))

k = np.array([x[2] for x in rows], float)
y = np.array([x[3] for x in rows])
rho, p = spearmanr(k, y)
print("\n  Spearman(knee, harmonic ratio) = %+.3f   p = %.3f   [prediction: NEGATIVE]" % (rho, p))

rng = np.random.default_rng(0)
print("\n  knee   n_routes   median harmonic ratio")
grp = {}
for kk in (300, 600, 1800):
    v = y[np.isclose(k, kk)]
    grp[kk] = v
    print("  %5d      %2d          %6.3f" % (kk, len(v), np.median(v)))

a, b = grp[300], grp[1800]
bs = [np.median(rng.choice(a, len(a))) / np.median(rng.choice(b, len(b))) for _ in range(4000)]
print("\n  hardest relay (knee 300) / softest (knee 1800) = %.3f   CI [%.3f, %.3f]"
      % (np.median(a) / np.median(b), np.percentile(bs, 2.5), np.percentile(bs, 97.5)))
a6, b6 = grp[300], grp[600]
bs6 = [np.median(rng.choice(a6, len(a6))) / np.median(rng.choice(b6, len(b6))) for _ in range(4000)]
print("  knee 300 / knee 600 (8 vs 7 routes)          = %.3f   CI [%.3f, %.3f]"
      % (np.median(a6) / np.median(b6), np.percentile(bs6, 2.5), np.percentile(bs6, 97.5)))
print("\n  ⇒ %s" % ("MONOTONE IN THE PREDICTED DIRECTION" if rho < 0 else "NOT in the predicted direction"))
