# -*- coding: utf-8 -*-
"""Re-run the grind-#1 lever hunt on the CORRECTED band, and test whether the FREQUENCY moves.

Two questions, both now askable because the band error is fixed:

  A) AMPLITUDE: does the 21-26 Hz engaged excess track any cal?  (the lever hunt, redone)
  B) FREQUENCY: does the PEAK LOCATION track any cal?

(B) is the more valuable question. A mode whose frequency MOVES with a calibration is a
CLOSED-LOOP POLE and can be relocated in firmware -- unlike the 7.8 Hz oscillation, whose
f0 was invariant to a 2x gain change and is therefore mechanical. The operator's own report
is that grind #1 moved, so something is moving it.

Lever B is held constant by restricting to routes that carry it, so the largest known effect
does not swamp the rest.  Route-level bootstrap throughout.
"""
import numpy as np, glob, os
from scipy import signal
from scipy.stats import spearmanr

FS, NW = 100.0, 512
FR = os.environ['ACCORD_FIRMWARE_ROOT'] + '/analysis-2020accord'
ON = {'21': ('V111', '_v111_'), '22': ('V112', '_v112_'), '23': ('V112', '_v112_'),
      '77': ('V90', '_v90_'), '78': ('V91', '_v91_'), '79': ('V92', '_v92_'),
      '7e': ('V96', '_v96_'), '7f': ('V96', '_v96_'), '85': ('V100', '_v100_'),
      'a4': ('V104', '_v104_'), 'a5': ('V105', '_v105_'), 'a6': ('V106', '_v106_'),
      '1e': ('V107', '_v107_')}
CAL = {'knee_C40BC': (0xC40BC, 2), 'K1_C40D2': (0xC40D2, 2), 'a2_C40DC': (0xC40DC, 2),
       'gain_C6CD0': (0xC6CD0, 2), 'biq_C649B': (0xC649B, 1),
       'fricY0_D7A5C': (0xD7A5C, 2), 'fricY2_D7A6C': (0xD7A6C, 2),
       'pole1_C50D4': (0xC50D4, 2), 'kd_C6AE6': (0xC6AE6, 2)}


def cals(tag):
    g = [x for x in glob.glob(os.path.join(FR, tag + '*plain_image.bin')) if 'SUPERSEDED' not in x]
    if not g:
        return None
    d = open(g[0], 'rb').read()
    return {n: (d[a] if w == 1 else int.from_bytes(d[a:a + w], 'little')) for n, (a, w) in CAL.items()}


def stat(r):
    p = 'analysis-2020accord/_scratch/cache/r%s/r%s.npz' % (r, r)
    if not os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('cs_rate', 'cc_lat', 'cs_v')):
        return None
    x, lat, v = [np.asarray(z[k]).astype(float) for k in ('cs_rate', 'cc_lat', 'cs_v')]
    m = (lat > 0.5) & (v > 1.0)
    sh, pk = [], []
    for a in range(0, len(x) - NW, NW // 2):
        b = a + NW
        if m[a:b].mean() < 0.99:
            continue
        f, P = signal.welch(x[a:b] - x[a:b].mean(), FS, nperseg=NW, noverlap=NW // 2)
        tot = P[(f >= 1) & (f <= 45)].sum()
        if tot <= 0:
            continue
        w = (f >= 15) & (f <= 40)
        sh.append(P[(f >= 21) & (f <= 26)].sum() / tot)
        pk.append(f[w][int(np.argmax(P[w]))])
    if len(sh) < 40:
        return None
    hi = np.array(sh) >= np.percentile(sh, 75)
    return np.percentile(sh, 90), float(np.median(np.array(pk)[hi]))


rows = []
for r in sorted(ON):
    s = stat(r)
    c = cals(ON[r][1])
    if s and c:
        rows.append((r, ON[r][0], s[0], s[1], c))
print("  %d Lever-B-ON routes.\n" % len(rows))
print("  route build   21-26 share   peak freq (15-40 Hz, top-quartile windows)")
for r, b, sh, pk, c in sorted(rows, key=lambda x: x[3]):
    print("   r%-4s %-6s     %.5f        %5.2f Hz" % (r, b, sh, pk))

y_amp = np.array([x[2] for x in rows])
y_frq = np.array([x[3] for x in rows])
rng = np.random.default_rng(0)
for title, y in (("A) AMPLITUDE  (21-26 Hz share)", y_amp), ("B) FREQUENCY  (peak location)", y_frq)):
    print("\n  %s" % title)
    print("     predictor        levels  values                 rho      p      hi/lo      CI")
    for n in CAL:
        v = np.array([float(x[4][n]) for x in rows])
        u = sorted(set(v))
        if len(u) < 2:
            print("      %-16s %4d   %-22s CONSTANT" % (n, 1, '%g' % u[0]))
            continue
        rho, p = spearmanr(v, y)
        lo, hi = y[v <= u[0]], y[v >= u[-1]]
        if len(lo) < 3 or len(hi) < 2:
            print("      %-16s %4d   %-22s %+.3f  %.3f   arms %d/%d too small"
                  % (n, len(u), ','.join('%g' % x for x in u[:4]), rho, p, len(lo), len(hi)))
            continue
        bs = [np.median(rng.choice(hi, len(hi))) / np.median(rng.choice(lo, len(lo))) for _ in range(4000)]
        l, h = np.percentile(bs, 2.5), np.percentile(bs, 97.5)
        print("      %-16s %4d   %-22s %+.3f  %.3f   %6.3f   [%.2f, %.2f]%s"
              % (n, len(u), ','.join('%g' % x for x in u[:4]), rho, p,
                 np.median(hi) / np.median(lo), l, h, '  <== HIT' if (l > 1 or h < 1) else ''))
