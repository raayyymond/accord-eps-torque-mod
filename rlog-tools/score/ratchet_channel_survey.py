# -*- coding: utf-8 -*-
"""Which CHANNEL shows the ratchet?

The ratchet is real but only 1.1-2.3x above its slope-matched null in wheel rate (6/9
routes), while the grind is 3-100x above in the same channel.  That is a signal-strength
fact about the CHANNEL, so test the others: driver torque, EPS torque, angle, yaw, wheel
speeds, and the command.

Same validated machinery throughout: pooled PSD over continuous engaged-creep runs, a
power-law background fitted outside the test bands, and a null generated at each channel's
OWN measured slope.  A channel only wins if its ratchet excess clears its own null by more
than wheel rate's 1.1-2.3x.
"""
import os, sys
import numpy as np
from scipy import signal
sys.path.insert(0, 'rlog-tools/score')
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
RNG = np.random.default_rng(7)
CHANS = ['cs_rate', 'cs_tq', 'tq', 'sc_tq', 'co_tqcan', 'cs_ang', 'ang', 'wang',
         'cs_yaw', 'ws_fl', 'ws_fr', 'cc_req']
ROUTES = [('r24', 'V122'), ('r1e', 'V107'), ('r7e', 'V96'), ('ra4', 'V104')]


def pooled(segs):
    acc, f = [], None
    for s in segs:
        f, P = signal.welch(s - s.mean(), FS, nperseg=NPS, noverlap=NPS // 2)
        acc.append(P)
    return f, np.median(np.asarray(acc), 0)


def bg(f, M):
    use = (f >= 3.0) & (f <= 40.0) & (M > 0)
    for lo, hi in BANDS:
        use &= ~((f >= lo) & (f <= hi))
    if use.sum() < 6 or not np.all(np.isfinite(M[use])):
        return None, np.nan
    c = np.polyfit(np.log(f[use]), np.log(M[use]), 1)
    return np.exp(np.polyval(c, np.log(np.maximum(f, 1e-9)))), float(c[0])


def exc(f, M, band):
    b, sl = bg(f, M)
    if b is None:
        return np.nan, np.nan, np.nan
    w = (f >= band[0]) & (f <= band[1])
    r = M[w] / b[w]
    return float(np.max(r)), sl, float(f[w][int(np.argmax(r))])


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
        e, _, _ = exc(f, M, band)
        if np.isfinite(e):
            out.append(e)
    return float(np.percentile(out, 95)) if out else np.nan


def mask_runs(tag):
    p = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
    if not os.path.exists(p):
        return None, []
    z = np.load(p, allow_pickle=True)
    lat = np.asarray(z['cc_lat']).astype(float)
    v = np.asarray(z['cs_v']).astype(float)
    n = min(len(lat), len(v))
    kmh = v[:n] * 3.6
    ok = (lat[:n] > 0.5) & (kmh >= 1.0) & (kmh < 24.0)
    d = np.diff(np.concatenate(([0], ok.view(np.int8), [0])))
    st, en = np.where(d == 1)[0], np.where(d == -1)[0]
    return z, [(a, b) for a, b in zip(st, en) if (b - a) >= NPS]


print('RATCHET 5-12 Hz by channel  (excess / slope-matched null p95 = margin)\n')
print('%-10s %-26s %-26s' % ('channel', 'margin per route', 'mean margin'))
agg = {}
for ch in CHANS:
    cells, marg = [], []
    for tag, bld in ROUTES:
        z, iv = mask_runs(tag)
        if z is None or ch not in z.files or len(iv) < 4:
            cells.append('%s -' % tag)
            continue
        a = np.asarray(z[ch]).astype(float)
        segs = [a[i:j] for i, j in iv if j <= len(a) and np.all(np.isfinite(a[i:j]))
                and np.std(a[i:j]) > 0]
        if len(segs) < 4:
            cells.append('%s -' % tag)
            continue
        f, M = pooled(segs)
        e, sl, pk = exc(f, M, RATCHET)
        if not np.isfinite(e):
            cells.append('%s -' % tag)
            continue
        p95 = null95(sl, len(segs), RATCHET)
        m = e / p95 if p95 > 0 else np.nan
        cells.append('%s %.1f' % (tag, m))
        if np.isfinite(m):
            marg.append(m)
    mm = np.mean(marg) if marg else np.nan
    agg[ch] = mm
    print('%-10s %-52s %.2f' % (ch, '  '.join(cells), mm))

print('\nranked (wheel rate cs_rate is the incumbent at ~1.1-2.3x):')
for ch, m in sorted(agg.items(), key=lambda kv: -(kv[1] if np.isfinite(kv[1]) else -1)):
    if np.isfinite(m):
        print('  %-10s %.2f' % (ch, m))
