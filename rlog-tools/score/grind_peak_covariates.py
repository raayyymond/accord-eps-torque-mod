# -*- coding: utf-8 -*-
"""
WHAT DOES THE GRIND PEAK FREQUENCY TRACK?

The re-centred notch gives 9.5x at the median episode but only 2.0x at the p10, where episodes peak
near 16.4 Hz.  One biquad cannot cover the 6.7 Hz spread -- the minimax settled that.  So the useful
question is whether the low-peak episodes are an identifiable DRIVING REGIME rather than noise.

The record already established that the ratchet's AMPLITUDE axis is wheel rate, not speed
([[accord-ratchet-axis-is-wheel-rate]]), and separately that the mode is "speed-invariant" in
FREQUENCY.  Those were measured on different quantities and never cross-checked per episode.

Per engaged episode: the 15-25 Hz peak on cs_rate, against that episode's own median speed, median
|steering rate|, median |driver torque| and median |LKAS command|.  Spearman, because none of these
is expected linear -- and a per-episode n, so the correlation is over EPISODES, not frames.
"""
import glob
import os

import numpy as np
from scipy import signal, stats

C = 'analysis-2020accord/_scratch/cache'
FS = 100.0


def episodes(mask, minlen=256):
    out, i, n = [], 0, len(mask)
    while i < n:
        if not mask[i]:
            i += 1
            continue
        j = i
        while j < n and mask[j]:
            j += 1
        if j - i >= minlen:
            out.append((i, j))
        i = j
    return out


rows = []
for d in sorted(glob.glob(C + '/r*')):
    tag = os.path.basename(d)
    f = glob.glob(os.path.join(d, tag + '.npz'))
    if not f:
        continue
    try:
        z = np.load(f[0], allow_pickle=True)
    except Exception:
        continue
    have = set(z.files)
    if not {'cc_lat', 'cs_rate'} <= have:
        continue
    lat = np.asarray(z['cc_lat']).astype(float) > 0.5
    rate = np.asarray(z['cs_rate']).astype(float)
    n = min(len(lat), len(rate))
    lat, rate = lat[:n], rate[:n]
    get = lambda k: (np.asarray(z[k]).astype(float)[:n] if k in have else None)
    v, tq, cmd = get('cs_v'), get('cs_tq'), get('e4tq')
    for a, b in episodes(lat):
        seg = rate[a:b]
        fr, P = signal.welch(seg - seg.mean(), FS, nperseg=min(256, len(seg)))
        bd = (fr >= 15) & (fr <= 25)
        if not bd.any():
            continue
        rows.append(dict(
            tag=tag, pk=float(fr[bd][int(np.argmax(P[bd]))]), n=b - a,
            v=float(np.median(v[a:b])) if v is not None else np.nan,
            rate=float(np.median(np.abs(seg))),
            tq=float(np.median(np.abs(tq[a:b]))) if tq is not None else np.nan,
            cmd=float(np.median(np.abs(cmd[a:b]))) if cmd is not None else np.nan))

pk = np.array([r['pk'] for r in rows])
print('=' * 92)
print('  GRIND PEAK vs EPISODE COVARIATES   (%d engaged episodes, %d routes)'
      % (len(rows), len({r['tag'] for r in rows})))
print('=' * 92)
print('  peak Hz: median %.2f  p10 %.2f  p90 %.2f  min %.2f  max %.2f'
      % (np.median(pk), np.percentile(pk, 10), np.percentile(pk, 90), pk.min(), pk.max()))
print()
print('  covariate            median      Spearman rho vs peak     p')
for key, nm in (('v', 'speed m/s'), ('rate', '|steering rate|'),
                ('tq', '|driver torque|'), ('cmd', '|LKAS command|')):
    x = np.array([r[key] for r in rows])
    ok = np.isfinite(x) & np.isfinite(pk)
    if ok.sum() < 20:
        print('  %-20s (insufficient)' % nm)
        continue
    rho, p = stats.spearmanr(x[ok], pk[ok])
    star = ' **' if p < 0.01 else (' *' if p < 0.05 else '')
    print('  %-20s %8.2f      %+8.3f            %7.4f%s'
          % (nm, np.median(x[ok]), rho, p, star))

print()
print('  LOW-PEAK vs HIGH-PEAK episodes (split at the median peak)')
lo = pk <= np.median(pk)
for key, nm in (('v', 'speed m/s'), ('rate', '|steering rate|'),
                ('tq', '|driver torque|'), ('cmd', '|LKAS command|')):
    x = np.array([r[key] for r in rows])
    ok = np.isfinite(x)
    if ok.sum() < 20:
        continue
    a, b = x[ok & lo], x[ok & ~lo]
    print('  %-20s low-peak %8.2f   high-peak %8.2f   ratio %.2f'
          % (nm, np.median(a), np.median(b), (np.median(b) / np.median(a)) if np.median(a) else np.nan))

print()
print('  BY ROUTE -- is the peak a property of the DRIVE rather than the episode?')
byr = {}
for r in rows:
    byr.setdefault(r['tag'], []).append(r['pk'])
w = np.array([np.var(v) for v in byr.values() if len(v) > 2])
allv = np.var(pk)
print('  mean WITHIN-route variance %.3f  vs  TOTAL variance %.3f  ->  within/total %.2f'
      % (w.mean(), allv, w.mean() / allv))
print('  (near 1 = the peak varies episode to episode within a drive;')
print('   near 0 = the peak is fixed per drive and differs BETWEEN drives)')
