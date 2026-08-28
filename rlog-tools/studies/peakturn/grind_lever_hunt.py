# -*- coding: utf-8 -*-
"""Hunt a NEW grind-#1 lever with the now-VALIDATED pipeline.

The pipeline recovered Lever B's known 2.5x effect at 2.32x [1.62, 2.94] from a different
dataset and a different statistic, so it is sensitive enough to trust. Now use it as the
outcome in the same natural-experiment design that proved the deletion-set hypothesis.

Restrict to the 13 Lever-B-ON routes so that lever -- by far the largest known effect -- is
held constant, then regress the exposure-controlled grind ratio against every cal that
actually varies across those builds.
"""
import numpy as np, glob, os
from scipy import signal
from scipy.stats import spearmanr

FS, NW = 100.0, 256
FR = os.environ['ACCORD_FIRMWARE_ROOT'] + '/analysis-2020accord'
ON = {'21': ('V111', '_v111_'), '22': ('V112', '_v112_'), '23': ('V112', '_v112_'),
      '77': ('V90', '_v90_'), '78': ('V91', '_v91_'), '79': ('V92', '_v92_'),
      '7e': ('V96', '_v96_'), '7f': ('V96', '_v96_'), '85': ('V100', '_v100_'),
      'a4': ('V104', '_v104_'), 'a5': ('V105', '_v105_'), 'a6': ('V106', '_v106_'),
      '1e': ('V107', '_v107_')}
CAL = {'knee_C40BC': 0xC40BC, 'K1_C40D2': 0xC40D2, 'a2_C40DC': 0xC40DC,
       'gain_C6CD0': 0xC6CD0, 'pole_C40D0': 0xC40D0, 'resid_C7468': 0xC7468,
       'biq_C649B': 0xC649B, 'kd_C6AE6': 0xC6AE6, 'kp_C6B26': 0xC6B26, 'ki_C6B12': 0xC6B12}


def cals(tag):
    g = [x for x in glob.glob(os.path.join(FR, tag + '*plain_image.bin')) if 'SUPERSEDED' not in x]
    if not g:
        return None
    d = open(g[0], 'rb').read()
    return {n: (d[a] if n == 'biq_C649B' else int.from_bytes(d[a:a + 2], 'little')) for n, a in CAL.items()}


def stat(r):
    p = 'analysis-2020accord/_scratch/cache/r%s/r%s.npz' % (r, r)
    if not os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('cs_rate', 'cc_lat', 'cs_v')):
        return None
    rate, lat, v = [np.asarray(z[k]).astype(float) for k in ('cs_rate', 'cc_lat', 'cs_v')]
    m = (lat > 0.5) & (v > 1.0)
    hi, lo = [], []
    for a in range(0, len(rate) - NW, NW // 2):
        sl = slice(a, a + NW)
        if m[sl].mean() < 0.99:
            continue
        f, P = signal.welch(rate[sl] - np.mean(rate[sl]), FS, nperseg=NW, noverlap=NW // 2)
        g = np.sqrt(np.sum(P[(f >= 18) & (f <= 22)]) * (f[1] - f[0]))
        (hi if np.percentile(np.abs(rate[sl]), 95) >= 20 else lo).append(g)
    if len(hi) < 15 or len(lo) < 15:
        return None
    return np.percentile(hi, 90) / np.percentile(lo, 90)


rows = []
for r in sorted(ON):
    y = stat(r)
    c = cals(ON[r][1])
    if y and c:
        rows.append((r, ON[r][0], y, c))
print("  %d Lever-B-ON routes.  Outcome = exposure-controlled 18-22 Hz ratio (LOWER is better).\n" % len(rows))
print("  route build   grind ratio")
for r, b, y, c in sorted(rows, key=lambda x: x[2]):
    print("   r%-4s %-6s   %6.2f" % (r, b, y))

y = np.array([x[2] for x in rows])
print("\n  predictor        levels   values                       Spearman rho     p")
for n in CAL:
    v = np.array([float(x[3][n]) for x in rows])
    u = sorted(set(v))
    if len(u) < 2:
        print("   %-16s %5d   %-28s  CONSTANT -- untestable" % (n, 1, '%g' % u[0]))
        continue
    rho, p = spearmanr(v, y)
    flag = '  <== ' if p < 0.10 else ''
    print("   %-16s %5d   %-28s  %+7.3f   %6.3f%s"
          % (n, len(u), ','.join('%g' % x for x in u[:5]), rho, p, flag))
print("\n  (a lever that REDUCES grind #1 shows a rho whose sign means 'more cal -> lower ratio')")
