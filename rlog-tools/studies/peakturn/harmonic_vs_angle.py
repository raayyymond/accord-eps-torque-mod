# -*- coding: utf-8 -*-
"""DO THE HARMONICS TRACK ANGLE?  The test I never ran.

The harmonics were shown to track NEITHER firmware saturation axis: flat in SPEED
(refuting the damper's +-511 clamp, whose duty falls 67x over that range) and flat in
|RATE| (failing to support the Coulomb relay's own saturation point).

But the surviving hypothesis is different: the generator is the SIGNUM, and its AMPLITUDE
is |model| * K1/1024. |model| was measured to rise 7-9x with steering angle, which is why
the oscillation is angle-gated. A signum's harmonic RATIO is scale-invariant, but the
harmonics it radiates are not -- they scale with its amplitude.

So: if the generator is the |model|-scaled signum, the harmonic content should rise with
ANGLE while its ratio stays flat in speed and rate. That is a specific, falsifiable pattern
and it was never tested.

Two outcomes:
  harmonics rise with angle  -> the |model|-scaled signum is confirmed as the generator,
                                and K1 / table (b) become the levers
  harmonics flat in angle    -> that hypothesis dies too, and the generator is something
                                whose amplitude is angle-independent
"""
import numpy as np, os
from scipy import signal

FS, NW = 100.0, 512
ROUTES = ['21', '22', '23', '77', '78', '79', '7e', '7f', '85', '95', '96', '97', '9e',
          'a4', 'a5', 'a6', '1e']
f = signal.welch(np.zeros(NW), FS, nperseg=NW)[0]
b69 = (f >= 6) & (f <= 9)


def prom(P, ft, hw=1.0, gap=0.4):
    pk = (f >= ft - gap) & (f <= ft + gap)
    sh = (((f >= ft - hw - gap) & (f < ft - gap)) | ((f > ft + gap) & (f <= ft + hw + gap)))
    if pk.sum() == 0 or sh.sum() == 0:
        return np.nan
    return P[pk].max() / max(np.median(P[sh]), 1e-30)


def windows(r):
    p = 'analysis-2020accord/_scratch/cache/r%s/r%s.npz' % (r, r)
    if not os.path.exists(p):
        return []
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('cs_rate', 'cc_lat', 'cs_v', 'ang')):
        return []
    x, lat, v, ang = [np.asarray(z[k]).astype(float) for k in ('cs_rate', 'cc_lat', 'cs_v', 'ang')]
    m = (lat > 0.5) & (v > 1.0)
    out = []
    for a in range(0, len(x) - NW, NW // 2):
        b = a + NW
        if m[a:b].mean() < 0.99:
            continue
        _, P = signal.welch(x[a:b] - x[a:b].mean(), FS, nperseg=NW, noverlap=NW // 2)
        out.append((P, np.mean(np.abs(ang[a:b]))))
    return out


def hratio(ws):
    h, c = [], []
    for P, _ in ws:
        f0 = f[b69][np.argmax(P[b69])]
        for m_ in (2.0, 3.0):
            if f0 * m_ < f[-1] - 2:
                h.append(prom(P, f0 * m_))
        for m_ in (2.37, 2.63):
            if f0 * m_ < f[-1] - 2:
                c.append(prom(P, f0 * m_))
    h = np.array([x for x in h if np.isfinite(x)])
    c = np.array([x for x in c if np.isfinite(x)])
    if len(h) < 6 or len(c) < 6:
        return None
    return np.median(h) / np.median(c)


W = {r: windows(r) for r in ROUTES}
W = {r: w for r, w in W.items() if len(w) >= 60}
rng = np.random.default_rng(0)
print("  %d routes.\n" % len(W))
print("  HARMONIC RATIO by |ANGLE|  (route-level bootstrap; 1.0 = no harmonic structure)")
print("     |ang| bin        n_routes   ratio      95%% CI")
res = {}
for lo, hi in ((0, 5), (5, 10), (10, 20), (20, 40), (40, 400)):
    per = []
    for r, ws in W.items():
        s = [x for x in ws if lo <= x[1] < hi]
        if len(s) >= 12:
            v = hratio(s)
            if v:
                per.append(v)
    if len(per) < 5:
        print("     [%3d,%4d)          %3d      too few routes" % (lo, hi, len(per)))
        continue
    per = np.array(per)
    res[(lo, hi)] = per
    bs = [np.median(rng.choice(per, len(per))) for _ in range(4000)]
    print("     [%3d,%4d)          %3d      %6.3f    [%.3f, %.3f]"
          % (lo, hi, len(per), np.median(per), np.percentile(bs, 2.5), np.percentile(bs, 97.5)))

ks = sorted(res)
if len(ks) >= 2:
    lo_k, hi_k = ks[0], ks[-1]
    a, b = res[hi_k], res[lo_k]
    bs = [np.median(rng.choice(a, len(a))) / np.median(rng.choice(b, len(b))) for _ in range(4000)]
    print("\n  high-angle %s / low-angle %s = %.3f   CI [%.3f, %.3f]"
          % (hi_k, lo_k, np.median(a) / np.median(b), np.percentile(bs, 2.5), np.percentile(bs, 97.5)))
    print("\n  => %s" % ("HARMONICS RISE WITH ANGLE -- the |model|-scaled signum is the generator"
                         if np.percentile(bs, 2.5) > 1.0 else
                         "NOT resolved / flat in angle -- the |model|-scaled signum hypothesis is NOT supported"))
