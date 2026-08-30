# -*- coding: utf-8 -*-
"""RATE-MATCHED BAND RATIOS: classify WHOLE WINDOWS by their own median rate.

    python rlog-tools/score/rate_matched_band_ratio.py

Reusable instrument. Gating individual SAMPLES on instantaneous rate fragments the signal below a
spectral window and yields nothing; classifying whole windows keeps contiguity and still gives every
window an honest rate label, enforced by a within-window spread cap.

Gating individual samples on instantaneous rate fragments the signal below a spectral window -- that
killed 3 of 4 rate bands last attempt. Classifying contiguous windows by their own median rate keeps
contiguity AND gives every window a rate label. A within-window spread cap keeps the label honest.
"""
import sys

import numpy as np
from scipy.signal import welch

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

LADDER = [('r21', 'V111', 50), ('r22', 'V112', 150), ('r24', 'V122', 250)]
BANDS = {'ratchet 6-9': (6, 9), 'mid 9-12': (9, 12), 'grind 15-22': (15, 22), 'ctl 30-40': (30, 40)}
RATE_BINS = [(0, 3), (3, 8), (8, 20), (20, 50), (50, 1e9)]
SPREAD_MAX = 3.0          # p90/p50 within a window; above this the label is not meaningful


def load(t):
    return np.load('analysis-2020accord/_scratch/cache/%s/%s.npz' % (t, t), allow_pickle=True)


def wins(d, engaged):
    fs = 1.0 / np.median(np.diff(d['t']))
    n = int(round(2.0 * fs))
    lat = d['cc_lat'] > 0.5
    m = lat if engaged else ~lat
    m = m & (np.abs(d['cs_v'].astype(float)) > 0.3)
    i = np.flatnonzero(m)
    if not len(i):
        return fs, n, []
    out = []
    for e in np.split(i, np.flatnonzero(np.diff(i) > 1) + 1):
        for k in range(0, len(e) - n + 1, n):
            w = e[k:k + n]
            r = np.abs(d['cs_rate'].astype(float))[w]
            p50, p90 = np.percentile(r, 50), np.percentile(r, 90)
            if p50 <= 0 or p90 / max(p50, 1e-9) > SPREAD_MAX:
                continue                       # the window is not in ONE rate regime
            out.append((w, float(p50)))
    return fs, n, out


def bandpow(d, ws, fs, n):
    acc = None
    for w, _ in ws:
        s = d['cs_rate'].astype(float)[w]
        if np.allclose(s, s[0]):
            continue
        f, p = welch(s - s.mean(), fs=fs, nperseg=n, detrend='linear')
        acc = p if acc is None else acc + p
    if acc is None:
        return None
    acc /= len(ws)
    return {nm: float(acc[(f >= lo) & (f <= hi)].mean()) for nm, (lo, hi) in BANDS.items()}


BOOT = 4000


def ratio_ci(d, ws, fs, n, band, ctl='ctl 30-40'):
    """Per-window band ratio to the control band, with a bootstrap CI OVER WINDOWS."""
    vals = []
    for w, _ in ws:
        s_ = d['cs_rate'].astype(float)[w]
        if np.allclose(s_, s_[0]):
            continue
        f, p = welch(s_ - s_.mean(), fs=fs, nperseg=n, detrend='linear')
        num = p[(f >= BANDS[band][0]) & (f <= BANDS[band][1])].mean()
        den = p[(f >= BANDS[ctl][0]) & (f <= BANDS[ctl][1])].mean()
        if den > 0:
            vals.append(np.log2(num / den))
    if len(vals) < 6:
        return None
    v = np.array(vals)
    rng = np.random.default_rng(0)
    bs = [v[rng.integers(0, len(v), len(v))].mean() for _ in range(BOOT)]
    return float(v.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), len(v)


print('=' * 98)
print('  WITHIN-WINDOW BAND RATIO vs the 30-40 Hz control band -- engaged only, no manual needed')
print('  (that control band is itself alias-contaminated from 52-71 Hz, but IDENTICALLY so on every')
print('   route, so as a NORMALISER across routes it is still usable. It is not a clean band.)')
print('=' * 98)
for lo, hi in RATE_BINS:
    lab = '%g-%g' % (lo, hi) if hi < 1e9 else '>%g' % lo
    got = []
    for tag, bld, onset in LADDER:
        d = load(tag)
        fs, n, we = wins(d, True)
        we = [w for w in we if lo <= w[1] < hi]
        r = {b: ratio_ci(d, we, fs, n, b) for b in ('ratchet 6-9', 'mid 9-12', 'grind 15-22')}
        got.append((tag, bld, onset, len(we), r))
    if sum(1 for g in got if g[4]['ratchet 6-9']) < 3:
        continue
    print()
    print('  |rate| %-6s   log2(band / ctl 30-40), mean [95%% CI over windows]' % lab)
    print('    %-5s %-5s %6s %6s   %-24s %-24s %-24s'
          % ('route', 'bld', 'onset', 'winN', 'ratchet 6-9', 'mid 9-12', 'grind 15-22'))
    for tag, bld, onset, nw, r in got:
        cells = []
        for b in ('ratchet 6-9', 'mid 9-12', 'grind 15-22'):
            v = r[b]
            cells.append('%7.3f [%6.3f,%6.3f]' % (v[0], v[1], v[2]) if v else '        --        ')
        print('    %-5s %-5s %6d %6d   %s' % (tag, bld, onset, nw, ' '.join(cells)))
