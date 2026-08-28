# -*- coding: utf-8 -*-
"""Does grind #1's band track the relay KNEE across builds, as the operator's report says?

The operator's qualitative dose-response is the strongest on-car evidence the kit has for
any grind #1 lever: it went from a constant feature to "rare... a few moments in each drive"
exactly when the knee went 600 -> 1800. Test it quantitatively.

Knee is the relay's saturation threshold, so a larger knee means less relay chattering --
a DIFFERENT mechanism from the harmonic one that bears on the 7-9 Hz oscillation. The
harmonic test already showed the two symptoms are separate (2f0=15.62, 3f0=23.44 land in
neither grind band), so this is an independent prediction, not a restatement.

PREDICTION: 18-22 Hz and 26-31 Hz band energy FALL as knee rises.
NORMALISATION: each band is expressed as a SHARE of that window's own 1-40 Hz power, so a
drive that is simply busier does not read as more grind (the route-offset problem).
"""
import numpy as np, os
from scipy import signal
from scipy.stats import spearmanr

FS, NW = 100.0, 256
KNEE = {'97': ('STOCK', 600), '77': ('V90', 600), '78': ('V91', 600), '79': ('V92', 600),
        '7e': ('V96', 600), '7f': ('V96', 600), '21': ('V111', 600),
        '22': ('V112', 1800), '23': ('V112', 1800),
        '85': ('V100', 300), '95': ('V101', 300), '96': ('V102', 300), '9e': ('V103', 300),
        'a4': ('V104', 300), 'a5': ('V105', 300), 'a6': ('V106', 300), '1e': ('V107', 300)}
BANDS = {'18-22': (18, 22), '26-31': (26, 31), '6-9 (ref)': (6, 9)}


def shares(r):
    p = 'analysis-2020accord/_scratch/cache/r%s/r%s.npz' % (r, r)
    if not os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('cs_rate', 'cc_lat', 'cs_v')):
        return None
    rate, lat, v = [np.asarray(z[k]).astype(float) for k in ('cs_rate', 'cc_lat', 'cs_v')]
    m = (lat > 0.5) & (v > 1.0)
    acc = {k: [] for k in BANDS}
    for a in range(0, len(rate) - NW, NW // 2):
        sl = slice(a, a + NW)
        if m[sl].mean() < 0.99:
            continue
        f, P = signal.welch(rate[sl] - np.mean(rate[sl]), FS, nperseg=NW, noverlap=NW // 2)
        tot = P[(f >= 1) & (f <= 40)].sum()
        if tot <= 0:
            continue
        for k, (lo, hi) in BANDS.items():
            acc[k].append(P[(f >= lo) & (f <= hi)].sum() / tot)
    if len(acc['18-22']) < 40:
        return None
    return {k: float(np.median(v)) for k, v in acc.items()}, len(acc['18-22'])


rows = []
for r in sorted(KNEE):
    s = shares(r)
    if s:
        rows.append((r, KNEE[r][0], KNEE[r][1], s[0], s[1]))

print("  band power as a SHARE of each window's own 1-40 Hz power (median over windows)\n")
print("  route build   knee   18-22 Hz   26-31 Hz   6-9 Hz    n_win")
for r, b, k, s, n in sorted(rows, key=lambda x: x[2]):
    print("   r%-4s %-6s %5d   %7.4f    %7.4f   %7.4f   %4d"
          % (r, b, k, s['18-22'], s['26-31'], s['6-9 (ref)'], n))

kn = np.array([x[2] for x in rows], float)
print("\n  knee   n_routes   18-22 Hz    26-31 Hz    6-9 Hz")
grp = {}
for kk in (300, 600, 1800):
    sel = [x for x in rows if x[2] == kk]
    grp[kk] = sel
    print("  %5d      %2d      %8.4f    %8.4f   %8.4f"
          % (kk, len(sel), np.median([x[3]['18-22'] for x in sel]),
             np.median([x[3]['26-31'] for x in sel]),
             np.median([x[3]['6-9 (ref)'] for x in sel])))

print("\n  Spearman(knee, band share) across %d routes   [prediction: NEGATIVE for the grind bands]" % len(rows))
rng = np.random.default_rng(0)
for k in BANDS:
    y = np.array([x[3][k] for x in rows])
    rho, p = spearmanr(kn, y)
    a = np.array([x[3][k] for x in grp[300]])
    b = np.array([x[3][k] for x in grp[1800]])
    bs = [np.median(rng.choice(a, len(a))) / np.median(rng.choice(b, len(b))) for _ in range(4000)]
    print("    %-10s rho %+.3f  p %.3f    knee300/knee1800 = %.2fx  CI [%.2f, %.2f]"
          % (k, rho, p, np.median(a) / np.median(b), np.percentile(bs, 2.5), np.percentile(bs, 97.5)))
