# -*- coding: utf-8 -*-
"""Can the ratchet be scored from ONE short engaged episode?

The skill's design law: every build must be interpretable from ~15-30 s of engaged
symptomatic frames, because the operator stops the drive the moment the symptom persists.
Last tick I specified 8 passes of 15 s to resolve a 1.68-2.74x RATIO between builds.  That
spec is unbuildable by that law.

But the engaged-vs-manual result was PRESENCE/ABSENCE, not a ratio: the peak clears its
null on 7/7 engaged arms and 0/7 manual arms.  A build that kills the ratchet moves the
excess from ~33 to below its null ~4 -- an 8x change, not a 1.7x one.

Test: draw N consecutive windows from a real engaged route (as one episode would give),
and ask how often the peak still clears its own slope-matched null.  That is the detection
rate for "the ratchet is still there", and 1 - it is the false-negative rate for "fixed".
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
RNG = np.random.default_rng(31)
CH = 'cs_tq'
ROUTES = [('r78', 'V91'), ('r7e', 'V96'), ('r7f', 'V96'), ('r96', 'V102'),
          ('ra4', 'V104'), ('ra6', 'V106'), ('r1e', 'V107'), ('r22', 'V112'), ('r24', 'V122')]


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
    b = np.exp(np.polyval(c, np.log(np.maximum(f, 1e-9))))
    w = (f >= band[0]) & (f <= band[1])
    return float(np.max(M[w] / b[w])), float(c[0])


def coloured(n, beta):
    w = RNG.standard_normal(n)
    F = np.fft.rfft(w)
    fr = np.fft.rfftfreq(n, 1.0 / FS)
    g = np.ones_like(fr)
    g[1:] = fr[1:] ** (-beta / 2.0)
    g[0] = g[1]
    return np.fft.irfft(F * g, n)


def null95(slope, nseg, trials=200):
    out = []
    for _ in range(trials):
        f, M = pooled([coloured(NPS, -slope) for _ in range(nseg)])
        e, _ = exc(f, M, RATCHET)
        if np.isfinite(e):
            out.append(e)
    return float(np.percentile(out, 95)) if out else np.nan


def raw(tag):
    p = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
    z = np.load(p, allow_pickle=True)
    lat = np.asarray(z['cc_lat']).astype(float)
    v = np.asarray(z['cs_v']).astype(float)
    a = np.asarray(z[CH]).astype(float)
    n = min(len(lat), len(v), len(a))
    return lat[:n], v[:n] * 3.6, a[:n]


def episodes(tag, secs):
    """Contiguous engaged-creep stretches of at least `secs`, as one episode each."""
    lat, kmh, a = raw(tag)
    ok = (lat > 0.5) & (kmh >= 1.0) & (kmh < 24.0) & np.isfinite(a)
    d = np.diff(np.concatenate(([0], ok.view(np.int8), [0])))
    st, en = np.where(d == 1)[0], np.where(d == -1)[0]
    need = int(secs * FS)
    return [a[i:j] for i, j in zip(st, en) if (j - i) >= need and np.std(a[i:j]) > 0]


def windows_of(ep):
    """Split one continuous episode into 50%-overlapped analysis windows."""
    step = NPS // 2
    return [ep[i:i + NPS] for i in range(0, len(ep) - NPS + 1, step)]


for secs in (15, 20, 30):
    nw = (int(secs * FS) - NPS) // (NPS // 2) + 1
    print('=' * 74)
    print('ONE EPISODE OF %d s  ->  %d analysis windows' % (secs, nw))
    print('%-6s %-6s %-7s %-9s %-9s %s' % ('route', 'build', 'episodes', 'detect', 'excess med', 'null p95'))
    tot_hit = tot = 0
    for tag, bld in ROUTES:
        eps = episodes(tag, secs)
        if not eps:
            print('%-6s %-6s %-7d  -- no episode this long' % (tag, bld, 0))
            continue
        hits, es = 0, []
        for ep in eps:
            w = windows_of(ep)
            if len(w) < 2:
                continue
            f, M = pooled(w)
            e, sl = exc(f, M, RATCHET)
            if not np.isfinite(e):
                continue
            p95 = null95(sl, len(w), trials=120)
            es.append(e)
            hits += (e > p95)
            tot += 1
            tot_hit += (e > p95)
        if es:
            print('%-6s %-6s %-7d %-9s %-9.1f %.1f'
                  % (tag, bld, len(eps), '%d/%d' % (hits, len(es)), np.median(es), p95))
    if tot:
        print('  OVERALL: the ratchet is detected in %d of %d single episodes = %.0f %%'
              % (tot_hit, tot, 100.0 * tot_hit / tot))
