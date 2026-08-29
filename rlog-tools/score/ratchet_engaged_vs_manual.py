# -*- coding: utf-8 -*-
"""Engaged vs manual ratchet, on a per-route SPEED-MATCHED band.

First pass showed engaged excess 9.8-67.8 and manual 1.3-3.1 -- the manual arm sitting at
or BELOW its own null, i.e. no ratchet peak at all.  But every route failed the speed guard
(engaged 11.5-14.1 km/h, manual 5.0-9.7), so the contrast was confounded with speed.

Fix: per route, find the speed band both arms actually occupy, restrict BOTH to it, and
require the residual gap to be small.  Report the null for each arm so "absent" can be
distinguished from "smaller".
"""
import os, sys
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

FS = 100.0
NPS = 512
RATCHET = (5.0, 12.0)
GRIND = (15.0, 25.0)
BANDS = (RATCHET, GRIND)
RNG = np.random.default_rng(21)
ROUTES = [('r78', 'V91'), ('r7e', 'V96'), ('r7f', 'V96'), ('r96', 'V102'),
          ('ra6', 'V106'), ('r1e', 'V107'), ('r24', 'V122')]
CH = 'cs_tq'


def pooled(segs):
    acc, f = [], None
    for s in segs:
        f, P = signal.welch(s - s.mean(), FS, nperseg=NPS, noverlap=NPS // 2)
        acc.append(P)
    return f, np.median(np.asarray(acc), 0)


def exc(f, M, band):
    use = (f >= 3.0) & (f <= 40.0) & (M > 0)
    for lo, hi in BANDS:
        use &= ~((f >= lo) & (f <= hi))
    if use.sum() < 6 or not np.all(np.isfinite(M[use])):
        return np.nan, np.nan
    c = np.polyfit(np.log(f[use]), np.log(M[use]), 1)
    bg = np.exp(np.polyval(c, np.log(np.maximum(f, 1e-9))))
    w = (f >= band[0]) & (f <= band[1])
    return float(np.max(M[w] / bg[w])), float(c[0])


def coloured(n, beta):
    w = RNG.standard_normal(n)
    F = np.fft.rfft(w)
    fr = np.fft.rfftfreq(n, 1.0 / FS)
    g = np.ones_like(fr)
    g[1:] = fr[1:] ** (-beta / 2.0)
    g[0] = g[1]
    return np.fft.irfft(F * g, n)


def null95(slope, nseg, band, trials=200):
    out = []
    for _ in range(trials):
        f, M = pooled([coloured(NPS, -slope) for _ in range(nseg)])
        e, _ = exc(f, M, band)
        if np.isfinite(e):
            out.append(e)
    return float(np.percentile(out, 95)) if out else np.nan


def segs_in(tag, eng, lo, hi):
    p = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
    z = np.load(p, allow_pickle=True)
    lat = np.asarray(z['cc_lat']).astype(float)
    v = np.asarray(z['cs_v']).astype(float)
    a = np.asarray(z[CH]).astype(float)
    n = min(len(lat), len(v), len(a))
    lat, kmh, a = lat[:n], v[:n] * 3.6, a[:n]
    ok = (kmh >= lo) & (kmh < hi) & np.isfinite(a) & ((lat > 0.5) if eng else (lat <= 0.5))
    d = np.diff(np.concatenate(([0], ok.view(np.int8), [0])))
    st, en = np.where(d == 1)[0], np.where(d == -1)[0]
    segs, sp = [], []
    for i, j in zip(st, en):
        if (j - i) >= NPS and np.std(a[i:j]) > 0:
            segs.append(a[i:j])
            sp.append(kmh[i:j].mean())
    return segs, (np.mean(sp) if sp else np.nan)


def overlap_band(tag):
    """Speed range both arms occupy, as p10..p90 of the narrower arm."""
    p = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
    z = np.load(p, allow_pickle=True)
    lat = np.asarray(z['cc_lat']).astype(float)
    v = np.asarray(z['cs_v']).astype(float)
    n = min(len(lat), len(v))
    kmh = v[:n] * 3.6
    creep = (kmh >= 1.0) & (kmh < 24.0)
    e = kmh[creep & (lat[:n] > 0.5)]
    m = kmh[creep & (lat[:n] <= 0.5)]
    if len(e) < 100 or len(m) < 100:
        return None
    lo = max(np.percentile(e, 5), np.percentile(m, 5))
    hi = min(np.percentile(e, 95), np.percentile(m, 95))
    return (lo, hi) if hi - lo > 1.5 else None


print('%s -- SPEED-MATCHED engaged vs manual, ratchet 5-12 Hz\n' % CH)
print('%-6s %-6s %-12s %-13s %-13s %-8s %s'
      % ('route', 'build', 'band km/h', 'eng exc/null', 'man exc/null', 'ratio', 'gap'))
rr = []
for tag, bld in ROUTES:
    ob = overlap_band(tag)
    if ob is None:
        print('%-6s %-6s  -- no usable speed overlap between the arms' % (tag, bld))
        continue
    lo, hi = ob
    es, se = segs_in(tag, True, lo, hi)
    ms, sm = segs_in(tag, False, lo, hi)
    if len(es) < 3 or len(ms) < 3:
        print('%-6s %-6s %-12s  -- too few windows in band (eng %d, man %d)'
              % (tag, bld, '%.1f-%.1f' % (lo, hi), len(es), len(ms)))
        continue
    fe, Me = pooled(es)
    fm, Mm = pooled(ms)
    ee, sle = exc(fe, Me, RATCHET)
    em, slm = exc(fm, Mm, RATCHET)
    ne = null95(sle, len(es), RATCHET)
    nm = null95(slm, len(ms), RATCHET)
    gap = abs(se - sm)
    r = ee / em if em > 0 else np.nan
    print('%-6s %-6s %-12s %-13s %-13s %-8.2f %.1f%s'
          % (tag, bld, '%.1f-%.1f' % (lo, hi),
             '%.1f / %.1f' % (ee, ne), '%.1f / %.1f' % (em, nm), r, gap,
             '' if gap <= 2.0 else '  UNMATCHED'))
    if gap <= 2.0 and np.isfinite(r):
        rr.append((r, ee > ne, em > nm))

if rr:
    v = np.asarray([x[0] for x in rr])
    print('\nspeed-matched routes (n=%d):' % len(v))
    print('  ratchet engaged/manual  median %.2f  range %.2f-%.2f' % (np.median(v), v.min(), v.max()))
    b = [np.median(np.random.default_rng(s).choice(v, len(v))) for s in range(4000)]
    print('  95%% CI [%.2f, %.2f]' % (np.percentile(b, 2.5), np.percentile(b, 97.5)))
    print('  engaged arm beats its null on %d/%d routes; manual arm on %d/%d'
          % (sum(x[1] for x in rr), len(rr), sum(x[2] for x in rr), len(rr)))
    print('  memory records engaging amplifies 6-9 Hz by 2.8x -- compare')
