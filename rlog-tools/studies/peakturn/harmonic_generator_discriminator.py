# -*- coding: utf-8 -*-
"""WHICH nonlinearity manufactures the 7-9 Hz energy? A within-route discriminator.

The energy is generated inside the loop (26.5x more relative 6-9 Hz content in the
response than the command). Two hard nonlinearities sit in that loop and they are
distinguishable because they saturate on DIFFERENT axes:

  A) the COULOMB RELAY   clamp(POL * gp-0x6abc * 12 / knee, +-1)
     saturates on |motor RATE| >= knee/(12*4.7121)  -- V112: 31.8 deg/s
     => harmonics should track |RATE|, and be largely SPEED-INDEPENDENT

  B) the DAMPER's +-511 CLAMP on gp-0x6b26 (cal 0xC407E)
     build_v108_tva.py E2 measured its rail duty as strongly SPEED-dependent:
        10-25 km/h <=15.46 %   24-40 <=10.45 %   40-64 <=3.43 %   65-90 <=0.23 %   90+ <=0.03 %
     => harmonics should be strong at 10-40 km/h and essentially VANISH above 65 km/h

Both are signums, so both would produce the harmonics already measured. The axes separate
them. Route-level bootstrap throughout.
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
    if any(k not in z.files for k in ('cs_rate', 'cc_lat', 'cs_v')):
        return []
    rate, lat, v = [np.asarray(z[k]).astype(float) for k in ('cs_rate', 'cc_lat', 'cs_v')]
    m = (lat > 0.5) & (v > 1.0)
    out = []
    for a in range(0, len(rate) - NW, NW // 2):
        b = a + NW
        if m[a:b].mean() < 0.99:
            continue
        _, P = signal.welch(rate[a:b] - rate[a:b].mean(), FS, nperseg=NW, noverlap=NW // 2)
        out.append((P, np.mean(v[a:b]) * 3.6, np.percentile(np.abs(rate[a:b]), 95)))
    return out


def hratio(ws):
    h, c = [], []
    for P, _, _ in ws:
        f0 = f[b69][np.argmax(P[b69])]
        for mlt in (2.0, 3.0):
            if f0 * mlt < f[-1] - 2:
                h.append(prom(P, f0 * mlt))
        for mlt in (2.37, 2.63):
            if f0 * mlt < f[-1] - 2:
                c.append(prom(P, f0 * mlt))
    h = np.array([x for x in h if np.isfinite(x)])
    c = np.array([x for x in c if np.isfinite(x)])
    if len(h) < 6 or len(c) < 6:
        return None
    return np.median(h) / np.median(c)


W = {r: windows(r) for r in ROUTES}
W = {r: w for r, w in W.items() if len(w) >= 60}
rng = np.random.default_rng(0)
print("  %d routes.\n" % len(W))


def report(name, bins, key):
    print("  harmonic ratio by %s  (route-level bootstrap; 1.0 = no harmonic structure)" % name)
    print("     bin              n_routes    ratio      95%% CI")
    for lo, hi in bins:
        per = []
        for r, ws in W.items():
            s = [x for x in ws if lo <= x[key] < hi]
            if len(s) >= 12:
                v = hratio(s)
                if v:
                    per.append(v)
        if len(per) < 5:
            print("     [%5.0f,%5.0f)      %3d      too few routes" % (lo, hi, len(per)))
            continue
        per = np.array(per)
        bs = [np.median(rng.choice(per, len(per))) for _ in range(4000)]
        print("     [%5.0f,%5.0f)      %3d      %6.3f    [%.3f, %.3f]"
              % (lo, hi, len(per), np.median(per), np.percentile(bs, 2.5), np.percentile(bs, 97.5)))
    print("")


report("SPEED km/h  [clamp hypothesis: high 10-40, ~gone above 65]",
       [(0, 10), (10, 25), (25, 40), (40, 65), (65, 200)], 1)
report("|RATE| p95 deg/s  [relay hypothesis: rises past ~32 deg/s]",
       [(0, 15), (15, 32), (32, 60), (60, 120), (120, 500)], 2)
