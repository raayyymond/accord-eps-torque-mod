# -*- coding: utf-8 -*-
"""WHERE IS THE LKAS-CAUSED NOISE? Two channels, speed AND gear matched.

Speed matching alone does not control ENGINE ORDER: at one road speed, engaged and not-engaged driving
can sit in different gears and so different RPM. A 4-cylinder fires twice per revolution, so 60-72 Hz
is 1800-2160 rpm -- squarely in the range this car cruises at. Matching (speed bin, gear) pins RPM.

  PASS A  direct sub-100 Hz acoustic content        (`sp`)
  PASS B  amplitude MODULATION of broadband carriers (`env`) -- the extractor's own docstring calls
          this "the more likely physical signature", because a steering rack is a hopeless radiator
          below ~100 Hz. A rough mechanism MODULATES broadband noise at the mode rate.

Route-level bootstrap throughout (the route is the unit).
"""
import glob, os, sys
import numpy as np
from scipy.signal import welch
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
RNG = np.random.default_rng(20260830)
VB = np.arange(0, 36, 1.0)
BANDS = [(6,9),(9,12),(15,22),(22,30),(30,40),(40,50),(50,60),(60,72),(72,85),(85,99)]


def load(tag):
    ap = 'analysis-2020accord/_scratch/cache/%s/%s_grind.npz' % (tag, tag)
    cp = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
    if not (os.path.exists(ap) and os.path.exists(cp)):
        return None
    g = np.load(ap, allow_pickle=True); c = np.load(cp, allow_pickle=True)
    ks = set(c.files)
    if not {'cc_lat', 'cs_v', 'cs_gear', 't'} <= ks:
        return None
    return g, c


def masks(c, t):
    tc = np.asarray(c['t']).astype(float)
    eng = np.interp(t, tc, (np.asarray(c['cc_lat']).astype(float) > 0.5).astype(float))
    v = np.interp(t, tc, np.abs(np.asarray(c['cs_v']).astype(float)))
    gr = np.interp(t, tc, np.asarray(c['cs_gear']).astype(float))
    return eng, v, np.round(gr)


def matched_logratio(P, t, c, nb):
    """Weighted mean log10 ratio over (speed bin, gear) cells where both arms are populated."""
    eng, v, gr = masks(c, t)
    A = (eng > 0.95) & (v > 0.3); B = (eng < 0.05) & (v > 0.3)
    num = np.zeros(nb); w = 0.0
    for lo in VB:
        for g in np.unique(gr[np.isfinite(gr)]):
            a = A & (v >= lo) & (v < lo+1) & (gr == g)
            b = B & (v >= lo) & (v < lo+1) & (gr == g)
            if a.sum() < 10 or b.sum() < 10:
                continue
            ww = float(min(a.sum(), b.sum()))
            num += ww * np.log10(np.maximum(P[a].mean(axis=0), 1e-30)
                                 / np.maximum(P[b].mean(axis=0), 1e-30))
            w += ww
    return (num / w, w) if w >= 30 else (None, w)


def report(title, rows, f):
    print()
    print('  ' + title)
    if len(rows) < 3:
        print('    UNDER-POWERED: only %d routes retain matched cells. NOT licensed.' % len(rows))
        return
    M = np.vstack(rows)
    print('    %d routes.  %-11s %9s %20s  %s' % (len(M), 'band (Hz)', 'ratio', '95% CI', 'licensed?'))
    for lo, hi in BANDS:
        b = (f >= lo) & (f < hi)
        if not b.any():
            continue
        per = M[:, b].mean(axis=1)
        pt = 10 ** np.median(per)
        bs = np.array([10 ** np.median(RNG.choice(per, len(per), True)) for _ in range(4000)])
        l, h = np.percentile(bs, [2.5, 97.5])
        lic = 'YES' if l > 1.0 else ('yes (CUT)' if h < 1.0 else 'no')
        print('    %-15s %9.2fx  [%5.2f, %5.2f]   %s' % ('%d-%d' % (lo, hi), pt, l, h, lic))


tags = sorted({os.path.basename(p).split('_grind')[0]
               for p in glob.glob('analysis-2020accord/_scratch/cache/*/*_grind.npz')})
A_rows, B_rows, fA = [], [], None
FMOD = None
for tag in tags:
    d = load(tag)
    if d is None:
        continue
    g, c = d
    fA = np.asarray(g['sp_f']).astype(float)
    r, w = matched_logratio(np.asarray(g['sp']).astype(float),
                            np.asarray(g['t_sp']).astype(float), c, len(fA))
    if r is not None:
        A_rows.append(r)
    # ---- PASS B: spectrum of the broadband envelope ----
    env = np.asarray(g['env']).astype(float)
    te = np.asarray(g['t_env']).astype(float)
    sp = np.asarray(g['splice']).astype(bool) if 'splice' in set(g.files) else np.zeros(len(te), bool)
    fs = 1.0 / np.median(np.diff(te))
    eng, v, gr = masks(c, te)
    keep = (~sp) & (v > 0.3)
    nseg = int(round(4.0 * fs))
    rowsB, fmod = [], None
    car_ix = env.shape[1] - 1                       # highest carrier band: most broadband content
    x = env[:, car_ix]
    segs = {}
    for lo in VB:
        for gg in np.unique(gr[np.isfinite(gr)]):
            for arm, sel in (('A', eng > 0.95), ('B', eng < 0.05)):
                m = keep & sel & (v >= lo) & (v < lo+1) & (gr == gg)
                if m.sum() < nseg:
                    continue
                idx = np.flatnonzero(m)
                pieces = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
                acc = []
                for p in pieces:
                    if len(p) < nseg:
                        continue
                    ff, pp = welch(x[p] - x[p].mean(), fs=fs, nperseg=nseg)
                    acc.append(pp)
                if acc:
                    segs.setdefault((lo, gg), {})[arm] = (np.mean(acc, axis=0), ff)
    num = np.zeros(0); wsum = 0.0
    for k, dd in segs.items():
        if 'A' in dd and 'B' in dd:
            pa, ff = dd['A']; pb, _ = dd['B']
            if num.size == 0:
                num = np.zeros(len(ff)); fmod = ff
            num += np.log10(np.maximum(pa, 1e-30) / np.maximum(pb, 1e-30))
            wsum += 1
    if wsum >= 3:
        B_rows.append(num / wsum)
        FMOD = fmod

print('=' * 96)
print('  LKAS-CAUSED NOISE, speed AND gear matched (gear pins engine order)')
print('=' * 96)
report('PASS A -- DIRECT sub-100 Hz acoustic content', A_rows, fA)
if FMOD is not None:
    report('PASS B -- AMPLITUDE MODULATION of the broadband carrier (the likelier signature)',
           B_rows, FMOD)
else:
    print('\n  PASS B -- no route retained matched (speed, gear) cells with enough contiguous samples.')

# ---- PAIRED test: within each route, is 50-72 Hz more LKAS-affected than 15-22 Hz? -------------
if len(A_rows) >= 3:
    M = np.vstack(A_rows)
    b1 = (fA >= 15) & (fA < 22)
    b2 = (fA >= 50) & (fA < 72)
    d = M[:, b2].mean(axis=1) - M[:, b1].mean(axis=1)      # log10 difference, per route
    pt = 10 ** np.median(d)
    bs = np.array([10 ** np.median(RNG.choice(d, len(d), True)) for _ in range(5000)])
    l, h = np.percentile(bs, [2.5, 97.5])
    print()
    print('  PAIRED, within route: (50-72 Hz excess) / (15-22 Hz excess)')
    print('    per-route ratios: %s' % ', '.join('%.2f' % x for x in 10 ** d))
    print('    median %.2fx   95%% CI [%.2f, %.2f]   %s'
          % (pt, l, h, 'LICENSED' if l > 1.0 else 'NOT licensed -- CI spans 1.0'))
    print('    %d of %d routes have MORE excess at 50-72 than at 15-22.' % (int((d > 0).sum()), len(d)))
