# -*- coding: utf-8 -*-
"""Harmonics: the decisive control, and a ROUTE-level bootstrap.

First pass gave 2f0 = 1.491x and 3f0 = 1.472x over off-multiple controls, but those
controls sat at ~2.0 themselves, so the statistic has a floor. Two things needed:

  1. THE REAL CONTROL -- run the identical test on NON-oscillating windows. If they show
     the same harmonic ratio, the effect is an artifact of the statistic, not of the car.
  2. A ROUTE-level bootstrap, per feedback-one-route-per-build-cannot-resolve-band-ratios:
     windows within a drive are not independent, so resample DRIVES.

Also report where 2f0 and 3f0 actually LAND, since the kit's grind bands are 18-22 and
26-31 and the fundamental is ~7.8 Hz.
"""
import numpy as np, glob, os
from scipy import signal

FS, NW = 100.0, 512
ROUTES = ['21', '22', '23', '77', '78', '79', '7e', '7f', '85', '95', '96', '97', '9e', 'a4', 'a5', 'a6', '1e']


def spectra(r):
    p = 'analysis-2020accord/_scratch/cache/r%s/r%s.npz' % (r, r)
    if not os.path.exists(p):
        return []
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('cs_rate', 'cc_lat', 'cs_v')):
        return []
    rate, lat, v = [np.asarray(z[k]).astype(float) for k in ('cs_rate', 'cc_lat', 'cs_v')]
    m = (lat > 0.5) & (v > 1.0)
    out = []
    for a in range(0, len(rate) - NW, NW // 2):
        sl = slice(a, a + NW)
        if m[sl].mean() < 0.99:
            continue
        x = rate[sl] - np.mean(rate[sl])
        fr, P = signal.welch(x, FS, nperseg=NW, noverlap=NW // 2)
        out.append(P)
    return out


PER = {r: spectra(r) for r in ROUTES}
PER = {r: v for r, v in PER.items() if len(v) > 30}
f = signal.welch(np.zeros(NW), FS, nperseg=NW)[0]
b69 = (f >= 6) & (f <= 9)


def prom(P, ft, hw=1.0, gap=0.4):
    pk = (f >= ft - gap) & (f <= ft + gap)
    sh = (((f >= ft - hw - gap) & (f < ft - gap)) | ((f > ft + gap) & (f <= ft + hw + gap)))
    if pk.sum() == 0 or sh.sum() == 0:
        return np.nan
    return P[pk].max() / max(np.median(P[sh]), 1e-30)


def stat(route_subset):
    """harmonic ratio for OSC and for NON-OSC windows, pooled over the given routes"""
    out = {}
    for tag in ('OSC', 'NONOSC'):
        h, c, f0s = [], [], []
        for r in route_subset:
            Ps = PER[r]
            E = np.array([P[b69].sum() for P in Ps])
            k = max(int(0.05 * len(E)), 5)
            idx = np.argsort(E)[-k:] if tag == 'OSC' else np.argsort(E)[:k]
            for i in idx:
                P = Ps[i]
                f0 = f[b69][np.argmax(P[b69])]
                f0s.append(f0)
                for m in (2.0, 3.0):
                    if f0 * m < f[-1] - 2:
                        h.append(prom(P, f0 * m))
                for m in (2.37, 2.63):
                    if f0 * m < f[-1] - 2:
                        c.append(prom(P, f0 * m))
        h = np.array([x for x in h if np.isfinite(x)])
        c = np.array([x for x in c if np.isfinite(x)])
        out[tag] = (np.median(h) / np.median(c), np.median(f0s))
    return out


rs = list(PER)
base = stat(rs)
print("%d routes.\n" % len(rs))
print("  HARMONIC RATIO = median prominence at {2f0,3f0} / median at {2.37,2.63}f0")
print("     window class      ratio     median f0")
for tag in ('OSC', 'NONOSC'):
    print("     %-16s  %6.3f     %5.2f Hz" % (tag, base[tag][0], base[tag][1]))
print("\n  ⇒ THE REAL CONTROL: OSC ratio / NON-OSC ratio = %.3f" % (base['OSC'][0] / base['NONOSC'][0]))

rng = np.random.default_rng(0)
bs = []
for _ in range(400):
    samp = list(rng.choice(rs, len(rs)))
    try:
        s = stat(samp)
        bs.append(s['OSC'][0] / s['NONOSC'][0])
    except Exception:
        pass
bs = np.array(bs)
print("     ROUTE-level bootstrap 95%% CI: [%.3f, %.3f]   (1.0 = no excess harmonic structure)"
      % (np.percentile(bs, 2.5), np.percentile(bs, 97.5)))

f0 = base['OSC'][1]
print("\n  WHERE THE HARMONICS LAND:  f0 = %.2f Hz  ->  2f0 = %.2f Hz,  3f0 = %.2f Hz"
      % (f0, 2 * f0, 3 * f0))
print("  the kit's grind bands are 18-22 Hz and 26-31 Hz")
print("     2f0 in 18-22? %s      3f0 in 18-22? %s      3f0 in 26-31? %s"
      % (18 <= 2 * f0 <= 22, 18 <= 3 * f0 <= 22, 26 <= 3 * f0 <= 31))
