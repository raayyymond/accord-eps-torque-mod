# -*- coding: utf-8 -*-
"""Slope-corrected band excess -- the validated resonance endpoint.

WHY THIS EXISTS.  Every prior 6-9 Hz endpoint in this kit was confounded by the spectral
TILT of the wheel-rate signal, which runs from 1/f^0.80 to 1/f^2.37 across routes.  On
coloured noise with NO resonance at all, the old measures return:

    1/f^1.5  ->  prominence 27.4, fitted Q 1.00, fit r2 0.585
    1/f^2.0  ->  prominence 64.9, fitted Q 1.00, fit r2 0.710

which is indistinguishable from what the real routes gave.  Prominence-against-a-fixed-
floor, fitted Lorentzian Q and half-power Q were all withdrawn on that basis.

WHAT SURVIVES.  Fit the route's OWN power law over 3-40 Hz using only bins outside the
bands under test, then measure the peak's excess over that background, and compare it to a
null generated at THAT ROUTE's measured slope.  Validated result:

    GRIND 15-25 Hz    excess 9.9-421.9 vs null p95 2.6-4.1   REAL on 9/9 routes
    RATCHET 5-12 Hz   excess 2.0-8.9   vs null p95 2.7-4.1   REAL on 6/9 routes

So the grind resonance is unambiguous and the ratchet is marginal in this channel -- which
is why 6-9 Hz endpoints have always underperformed: the feature is 10-50x weaker there, a
signal-strength problem rather than a noise problem.

WHY NOT HALF-POWER Q.  Its null sits ABOVE the data (real 13.7-34.7 vs null p95 58-78),
because on a noisy median periodogram the half-power crossing lands on an adjacent bin.
That makes Q NON-MONOTONE: adding damping broadens the peak and lowers Q, but once the
peak weakens toward the floor Q rises again toward the noise value.  A rise therefore
cannot distinguish "damping failed" from "damping worked".  Excess is monotone.

WINDOWS.  nperseg=512 (5.12 s) over CONTINUOUS engaged-creep runs.  The split-half floor is
driven by window count: 3/half -> 2.23x, 6/half -> 1.57x, extrapolating to ~1.2-1.3x at
12-16/half.  A 15 s continuous pass yields 4 windows, a 10 s pass yields 2.
"""
import os
import sys

import numpy as np
from scipy import signal

FS = 100.0
NPS = 512
FIT = (3.0, 40.0)
RATCHET = (5.0, 12.0)
GRIND = (15.0, 25.0)
BANDS = (RATCHET, GRIND)
CREEP_KMH = (1.0, 24.0)
CHANNEL = 'cs_tq'      # see creep_runs(): cs_rate is at chance for the ratchet
SUB_LO, SUB_HI = (15.0, 20.0), (20.0, 25.0)   # V158-damper vs V173-filter discriminator


def _cache(tag):
    for p in ('analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag),
              '_scratch/cache/%s/%s.npz' % (tag, tag)):
        if os.path.exists(p):
            return p
    return None


def creep_runs(tag, nps=NPS):
    """Maximal CONTINUOUS runs of engaged creep, each at least one window long."""
    p = _cache(tag)
    if p is None:
        return []
    z = np.load(p, allow_pickle=True)
    lat = np.asarray(z['cc_lat']).astype(float)
    v = np.asarray(z['cs_v']).astype(float)
    # CHANNEL: cs_tq, the torsion-bar torque.  NOT cs_rate -- that was the original
    # choice and it scores at CHANCE for the ratchet (margin 1.03 vs cs_tq's 7.42).
    # Every 6-9 Hz endpoint this kit used before 2026-08-29 read the wrong channel.
    r = np.asarray(z[CHANNEL]).astype(float)
    n = min(len(lat), len(v), len(r))
    lat, v, r = lat[:n], v[:n], r[:n]
    kmh = v * 3.6
    ok = (lat > 0.5) & (kmh >= CREEP_KMH[0]) & (kmh < CREEP_KMH[1]) & np.isfinite(r)
    d = np.diff(np.concatenate(([0], ok.view(np.int8), [0])))
    st, en = np.where(d == 1)[0], np.where(d == -1)[0]
    return [r[a:b] for a, b in zip(st, en) if (b - a) >= nps]


def pooled_psd(segs, nps=NPS):
    """Welch each continuous run separately, then median across runs."""
    acc, f = [], None
    for s in segs:
        f, P = signal.welch(s - s.mean(), FS, nperseg=nps, noverlap=nps // 2)
        acc.append(P)
    return f, np.median(np.asarray(acc), 0)


def background(f, M):
    """Power law over FIT, excluding every band under test so a band cannot set its own
    background. Returns (background array, slope)."""
    use = (f >= FIT[0]) & (f <= FIT[1]) & (M > 0)
    for lo, hi in BANDS:
        use &= ~((f >= lo) & (f <= hi))
    if use.sum() < 6:
        return None, np.nan
    c = np.polyfit(np.log(f[use]), np.log(M[use]), 1)
    return np.exp(np.polyval(c, np.log(np.maximum(f, 1e-9)))), float(c[0])


def band_excess(f, M, band):
    bg, slope = background(f, M)
    if bg is None:
        return np.nan, np.nan, np.nan
    w = (f >= band[0]) & (f <= band[1])
    k = int(np.argmax(M[w] / bg[w]))
    return float(np.max(M[w] / bg[w])), slope, float(f[w][k])


def _coloured(n, beta, rng):
    w = rng.standard_normal(n)
    F = np.fft.rfft(w)
    f = np.fft.rfftfreq(n, 1.0 / FS)
    g = np.ones_like(f)
    g[1:] = f[1:] ** (-beta / 2.0)
    g[0] = g[1]
    return np.fft.irfft(F * g, n)


def null_p95(slope, nseg, band, trials=300, seed=0, nps=NPS):
    """Excess reachable by coloured noise at this slope with this many windows.
    The control MUST be slope-matched -- a white-noise control passes anything."""
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(trials):
        f, M = pooled_psd([_coloured(nps, -slope, rng) for _ in range(nseg)], nps)
        e, _, _ = band_excess(f, M, band)
        if np.isfinite(e):
            out.append(e)
    return float(np.percentile(out, 95)) if out else np.nan


def split_half(segs, band, seed=0):
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(segs))
    h = len(segs) // 2
    if h < 2:
        return np.nan
    fa, Ma = pooled_psd([segs[i] for i in idx[:h]])
    fb, Mb = pooled_psd([segs[i] for i in idx[h:2 * h]])
    ea, _, _ = band_excess(fa, Ma, band)
    eb, _, _ = band_excess(fb, Mb, band)
    if not (np.isfinite(ea) and np.isfinite(eb)) or min(ea, eb) <= 0:
        return np.nan
    return float(max(ea, eb) / min(ea, eb))



def attribute_grind(segs):
    """15-20 vs 20-25 Hz. V173's filter attenuates the TOP of the band 2.2x more than the
    bottom; V158's damper is rate-proportional and dose-set, hence roughly flat. So the
    shape of a grind reduction says which lever produced it."""
    f, M = pooled_psd(segs)
    lo, _, _ = band_excess(f, M, SUB_LO)
    hi, _, _ = band_excess(f, M, SUB_HI)
    if not (np.isfinite(lo) and np.isfinite(hi)):
        return
    print('  GRIND SUB-BANDS   15-20 Hz excess %.1fx   20-25 Hz excess %.1fx   ratio %.2f'
          % (lo, hi, (hi / lo) if lo > 0 else float('nan')))
    print('       reference V122 (r24, cs_tq): 15-20 = 5.8x, 20-25 = 14.0x, ratio 2.39')
    print('       20-25 much LOWER than 15-20 => V173/V172 filter did it (sloped attenuation)')
    print('       both down about equally     => V158 damper did it (flat attenuation)')


def grind_by_command(tag):
    """The grind peaks at MID command (600-1500 ct) and DIES above it, while the ratchet
    grows monotonically. A pass spent at high command under-reads the grind, so take the
    grind verdict from the mid-command windows."""
    p = _cache(tag)
    if p is None:
        return
    z = np.load(p, allow_pickle=True)
    if 'sc_tq' not in z.files:
        print('  (no sc_tq in cache -- command stratification unavailable)')
        return
    lat = np.asarray(z['cc_lat']).astype(float)
    v = np.asarray(z['cs_v']).astype(float)
    a = np.asarray(z[CHANNEL]).astype(float)
    cmd = np.asarray(z['sc_tq']).astype(float)
    n = min(len(lat), len(v), len(a), len(cmd))
    lat, kmh, a, cmd = lat[:n], v[:n] * 3.6, a[:n], cmd[:n]
    ok = (lat > 0.5) & (kmh >= CREEP_KMH[0]) & (kmh < CREEP_KMH[1]) & np.isfinite(a)
    d = np.diff(np.concatenate(([0], ok.view(np.int8), [0])))
    st, en = np.where(d == 1)[0], np.where(d == -1)[0]
    strata = {'mid 600-1500': [], 'high 1500+': []}
    for i, j in zip(st, en):
        for k in range(i, j - NPS + 1, NPS // 2):
            w, c = a[k:k + NPS], np.abs(cmd[k:k + NPS]).mean()
            if np.std(w) == 0:
                continue
            if 600 <= c < 1500:
                strata['mid 600-1500'].append(w)
            elif c >= 1500:
                strata['high 1500+'].append(w)
    for nm, ws in strata.items():
        if len(ws) < 8:
            print('  command %-14s %2d windows -- TOO FEW to report (need 8; the'
                  ' background fit is unstable below that and the numbers are not'
                  ' credible)' % (nm, len(ws)))
            continue
        f, M = pooled_psd(ws)
        g, _, _ = band_excess(f, M, GRIND)
        r, _, _ = band_excess(f, M, RATCHET)
        print('  command %-14s %2d windows   grind %6.1fx   ratchet %6.1fx' % (nm, len(ws), g, r))
    print('       take the GRIND verdict from the MID row (it saturates above 1500 ct);')
    print('       take the RATCHET verdict from the HIGH row (it grows monotonically).')

def score(tag, label=''):
    segs = creep_runs(tag)
    print('%s %s -- %d continuous engaged-creep windows of %.2f s'
          % (tag, label, len(segs), NPS / FS))
    if len(segs) < 4:
        print('  NOT SCOREABLE: need at least 4 continuous runs; 12+ for a usable floor.')
        print('  A 15 s continuous pass yields ~4 windows, a 10 s pass ~2.')
        return
    f, M = pooled_psd(segs)
    for nm, band in (('GRIND  15-25', GRIND), ('RATCHET 5-12', RATCHET)):
        e, slope, pk = band_excess(f, M, band)
        p95 = null_p95(slope, len(segs), band)
        rep = split_half(segs, band)
        v = 'REAL PEAK' if e > p95 else 'TILT ONLY -- not a resonance'
        print('  %s Hz  peak %.2f Hz  excess %.1fx  (slope-matched null p95 %.1fx)  %s'
              % (nm, pk, e, p95, v))
        if np.isfinite(rep):
            print('       split-half %.2fx  -- an effect must exceed this to be readable'
                  % rep)
        if len(segs) < 12:
            print('       WARNING only %d windows; the floor is ~2.2x below 6/half.'
                  % len(segs))
    print('  spectral slope 1/f^%.2f  (routes span 0.80-2.37; the tilt is why raw'
          % -background(f, M)[1])
    print('  band power and fixed-floor prominence were withdrawn)')
    print()
    attribute_grind(segs)
    print()
    grind_by_command(tag)
    print()
    print('  REFERENCE, flying build V122 (route r24), same channel:')
    print('       ratchet 5-12 Hz  33.2x     grind 15-25 Hz  14.0x')
    print('       ratchet BELOW its null (~4) => gone;  UNCHANGED => falsifies the P.L')
    print('       assumption for BOTH lever classes at once.')


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        print('usage: score_band_excess.py <route-tag> [<route-tag> ...]')
        sys.exit(0)
    for t in args:
        score(t)
        print()
