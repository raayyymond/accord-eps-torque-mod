# -*- coding: utf-8 -*-
"""Peak command oscillation: is there a real resonance IN THE COMMAND?

The ratchet and grind both live in cs_tq.  The command channels scored 0.56-0.67 in the
ratchet band, i.e. below their own nulls -- but that was one band.  This sweeps the whole
usable spectrum of the COMMAND channels with the same validated estimator: excess over the
channel's OWN fitted power law, nulled at that channel's OWN measured slope.

If the command carries no excess anywhere, "peak command oscillation" is not a resonance to
damp and no firmware lever can reduce it -- it would be openpilot's controller output doing
what it was asked, and the kit's standing instruction forbids openpilot-side changes.
If it DOES carry excess in some band, that band names the mechanism.
"""
import os, sys
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

FS, NPS = 100.0, 512
RNG = np.random.default_rng(41)
BANDS = [('0.5-3', 0.5, 3.0), ('3-5', 3.0, 5.0), ('5-12', 5.0, 12.0),
         ('12-15', 12.0, 15.0), ('15-25', 15.0, 25.0), ('25-35', 25.0, 35.0),
         ('35-49', 35.0, 49.0)]
CHANS = ['cc_req', 'co_tqcan', 'sc_tq', 'cs_tq']
ROUTES = [('r78', 'V91'), ('r7e', 'V96'), ('r96', 'V102'), ('ra6', 'V106'),
          ('r1e', 'V107'), ('r22', 'V112'), ('r24', 'V122')]


def pooled(segs):
    acc, f = [], None
    for s in segs:
        f, P = signal.welch(s - s.mean(), FS, nperseg=NPS, noverlap=NPS // 2)
        acc.append(P)
    return f, np.median(np.asarray(acc), 0)


def bg_and_excess(f, M, band, all_bands):
    """Background fitted OUTSIDE every band under test, so no band sets its own floor."""
    # Exclude ONLY the band under test.  Excluding every band left no bins to fit -- the
    # band list tiles the whole spectrum -- and the whole sweep silently returned NaN.
    use = (f >= 0.5) & (f <= 49.0) & (M > 0)
    use &= ~((f >= band[1]) & (f <= band[2]))
    if use.sum() < 8 or not np.all(np.isfinite(M[use])):
        return np.nan, np.nan
    c = np.polyfit(np.log(f[use]), np.log(M[use]), 1)
    bgv = np.exp(np.polyval(c, np.log(np.maximum(f, 1e-9))))
    w = (f >= band[1]) & (f <= band[2])
    return float(np.max(M[w] / bgv[w])), float(c[0])


def coloured(n, beta):
    w = RNG.standard_normal(n)
    F = np.fft.rfft(w)
    fr = np.fft.rfftfreq(n, 1.0 / FS)
    g = np.ones_like(fr)
    g[1:] = fr[1:] ** (-beta / 2.0)
    g[0] = g[1]
    return np.fft.irfft(F * g, n)


def null95(slope, nseg, band, trials=150):
    out = []
    for _ in range(trials):
        f, M = pooled([coloured(NPS, -slope) for _ in range(nseg)])
        e, _ = bg_and_excess(f, M, band, BANDS)
        if np.isfinite(e):
            out.append(e)
    return float(np.percentile(out, 95)) if out else np.nan


def segs_for(tag, ch):
    p = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
    if not os.path.exists(p):
        return []
    z = np.load(p, allow_pickle=True)
    if ch not in z.files:
        return []
    lat = np.asarray(z['cc_lat']).astype(float)
    v = np.asarray(z['cs_v']).astype(float)
    a = np.asarray(z[ch]).astype(float)
    n = min(len(lat), len(v), len(a))
    lat, kmh, a = lat[:n], v[:n] * 3.6, a[:n]
    ok = (lat > 0.5) & (kmh >= 1.0) & (kmh < 24.0) & np.isfinite(a)
    d = np.diff(np.concatenate(([0], ok.view(np.int8), [0])))
    st, en = np.where(d == 1)[0], np.where(d == -1)[0]
    return [a[i:j] for i, j in zip(st, en) if (j - i) >= NPS and np.std(a[i:j]) > 0]


for ch in CHANS:
    print('=' * 92)
    print('CHANNEL %-10s  excess / slope-matched null p95, by band  (>1.0 = a real peak)' % ch)
    hdr = '%-6s %-6s %-5s %-7s' % ('route', 'build', 'nseg', 'slope')
    print(hdr + ' '.join('%-9s' % b[0] for b in BANDS))
    agg = {b[0]: [] for b in BANDS}
    for tag, bld in ROUTES:
        s = segs_for(tag, ch)
        if len(s) < 4:
            continue
        f, M = pooled(s)
        cells, slope = [], np.nan
        for b in BANDS:
            e, sl = bg_and_excess(f, M, b, BANDS)
            slope = sl
            p95 = null95(sl, len(s), b)
            r = e / p95 if (np.isfinite(e) and p95 > 0) else np.nan
            cells.append('%-9s' % ('%.2f' % r if np.isfinite(r) else '-'))
            if np.isfinite(r):
                agg[b[0]].append(r)
        print('%-6s %-6s %-5d %-7.2f %s' % (tag, bld, len(s), slope, ' '.join(cells)))
    print('%-27s %s' % ('MEDIAN across routes:',
                        ' '.join('%-9.2f' % np.median(agg[b[0]]) if agg[b[0]] else '%-9s' % '-'
                                 for b in BANDS)))
