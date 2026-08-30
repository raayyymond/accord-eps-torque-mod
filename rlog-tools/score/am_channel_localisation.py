# -*- coding: utf-8 -*-
"""PASS B, POWERED -- amplitude modulation of broadband carriers, speed AND gear matched.

The previous attempt retained ONE route and could not be read. The cause was the segmentation, not the
data: it demanded a single contiguous 4 s run inside each (1 m/s speed, gear) cell at 500 Hz. Engagement,
speed and gear all change on a shorter timescale than that, so almost every cell was discarded.

Fixes, all of which cost resolution rather than validity:
  * Welch segments of 1.024 s (512 samples at 500 Hz) -> ~1 Hz bins, ample for 6-99 Hz bands
  * accumulate periodograms across EVERY contiguous piece >= 1 segment, instead of needing one long run
  * speed bins widened 1 -> 2 m/s
  * all SIX carrier bands scored, not just the top one -- grinding may modulate one carrier only

Why this channel matters more than the direct one: extract_audio_grind.py argues the audible signature
of a rough mechanism is broadband noise AMPLITUDE-MODULATED at the mode rate, because a steering rack
is a hopeless radiator below 100 Hz. The direct-acoustic result is on the channel that docstring calls
LESS likely.
"""
import glob, os, sys
import numpy as np
from scipy.signal import welch
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RNG = np.random.default_rng(20260830)
VB = np.arange(0, 36, 2.0)
NPERSEG = 512
BANDS = [(6,9),(9,12),(15,22),(22,30),(30,40),(40,50),(50,60),(60,72),(72,85),(85,99)]


def cells(env_col, t, c, fs):
    """-> {(vbin, gear): {'A': (power, f, n), 'B': ...}} using every contiguous piece."""
    tc = np.asarray(c['t']).astype(float)
    eng = np.interp(t, tc, (np.asarray(c['cc_lat']).astype(float) > 0.5).astype(float))
    v = np.interp(t, tc, np.abs(np.asarray(c['cs_v']).astype(float)))
    gr = np.round(np.interp(t, tc, np.asarray(c['cs_gear']).astype(float)))
    out = {}
    for lo in VB:
        for g in np.unique(gr[np.isfinite(gr)]):
            for arm, sel in (('A', eng > 0.95), ('B', eng < 0.05)):
                m = sel & (v >= lo) & (v < lo + 2) & (gr == g)
                if m.sum() < NPERSEG:
                    continue
                idx = np.flatnonzero(m)
                acc, n = [], 0
                for p in np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1):
                    if len(p) < NPERSEG:
                        continue
                    x = env_col[p]
                    ff, pp = welch(x - x.mean(), fs=fs, nperseg=NPERSEG)
                    acc.append(pp * len(p)); n += len(p)
                if acc:
                    out.setdefault((lo, g), {})[arm] = (np.sum(acc, axis=0) / n, ff, n)
    return out


rows_by_carrier = {}
fmod = None
edges = None
for ap in sorted(glob.glob('analysis-2020accord/_scratch/cache/*/*_grind.npz')):
    tag = os.path.basename(ap).split('_grind')[0]
    cp = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
    if not os.path.exists(cp):
        continue
    g = np.load(ap, allow_pickle=True); c = np.load(cp, allow_pickle=True)
    if not {'cc_lat', 'cs_v', 'cs_gear', 't'} <= set(c.files):
        continue
    env = np.asarray(g['env']).astype(float)
    te = np.asarray(g['t_env']).astype(float)
    edges = np.asarray(g['env_f'])
    spl = np.asarray(g['splice']).astype(bool) if 'splice' in set(g.files) else np.zeros(len(te), bool)
    fs = 1.0 / np.median(np.diff(te))
    keep = ~spl
    for ci in range(env.shape[1]):
        col = env[:, ci].copy()
        col[~keep] = np.nan
        col = np.where(np.isfinite(col), col, np.nanmedian(col))
        cc = cells(col, te, c, fs)
        num = None; w = 0.0
        for k, d in cc.items():
            if 'A' in d and 'B' in d:
                pa, ff, na = d['A']; pb, _, nb = d['B']
                if num is None:
                    num = np.zeros(len(ff)); fmod = ff
                ww = float(min(na, nb))
                num += ww * np.log10(np.maximum(pa, 1e-30) / np.maximum(pb, 1e-30))
                w += ww
        if w >= 2 * NPERSEG:
            rows_by_carrier.setdefault(ci, []).append((tag, num / w))

print('=' * 100)
print('  PASS B -- AM of broadband carriers, speed AND gear matched, route-level bootstrap')
print('=' * 100)
if fmod is None:
    print('\n  still no matched cells -- the AM channel cannot be assessed from these caches.')
    raise SystemExit
for ci in sorted(rows_by_carrier):
    rows = rows_by_carrier[ci]
    lo_c, hi_c = (edges[ci] if edges is not None and ci < len(edges) else (0, 0))
    print()
    print('  CARRIER %d  (%.0f-%.0f Hz)   routes retained: %d  [%s]'
          % (ci, lo_c, hi_c, len(rows), ', '.join(t for t, _ in rows)))
    if len(rows) < 3:
        print('    UNDER-POWERED, no verdict.')
        continue
    M = np.vstack([r for _, r in rows])
    print('    %-14s %9s %20s  %s' % ('mod band (Hz)', 'ratio', '95% CI', 'licensed?'))
    for lo, hi in BANDS:
        b = (fmod >= lo) & (fmod < hi)
        if not b.any():
            continue
        per = M[:, b].mean(axis=1)
        pt = 10 ** np.median(per)
        bs = np.array([10 ** np.median(RNG.choice(per, len(per), True)) for _ in range(4000)])
        l, h = np.percentile(bs, [2.5, 97.5])
        lic = 'YES' if l > 1.0 else ('yes (CUT)' if h < 1.0 else 'no')
        print('    %-14s %9.2fx  [%5.2f, %5.2f]   %s' % ('%d-%d' % (lo, hi), pt, l, h, lic))

# ---- PAIRED within route, per carrier: is 50-72 Hz modulation stronger than 15-22 Hz? ----------
print()
print('=' * 100)
print('  PAIRED within route: (50-72 Hz modulation excess) / (15-22 Hz modulation excess)')
print('=' * 100)
b1 = (fmod >= 15) & (fmod < 22)
b2 = (fmod >= 50) & (fmod < 72)
for ci in sorted(rows_by_carrier):
    rows = rows_by_carrier[ci]
    if len(rows) < 3:
        continue
    lo_c, hi_c = (edges[ci] if edges is not None and ci < len(edges) else (0, 0))
    M = np.vstack([r for _, r in rows])
    d = M[:, b2].mean(axis=1) - M[:, b1].mean(axis=1)
    pt = 10 ** np.median(d)
    bs = np.array([10 ** np.median(RNG.choice(d, len(d), True)) for _ in range(5000)])
    l, h = np.percentile(bs, [2.5, 97.5])
    print('  carrier %d (%.0f-%.0f Hz)  %5.2fx  [%5.2f, %5.2f]  %-28s  %d/%d routes'
          % (ci, lo_c, hi_c, pt, l, h,
             'LICENSED' if l > 1.0 else 'not licensed (spans 1.0)',
             int((d > 0).sum()), len(d)))
