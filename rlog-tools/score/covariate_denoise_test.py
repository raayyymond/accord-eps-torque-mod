# -*- coding: utf-8 -*-
"""Can COVARIATE ADJUSTMENT make the ratchet endpoint answerable from ONE 15 s pass?

The ratchet band scores with log10 sd 0.332 across 15 s engaged windows, which is why one pass
cannot resolve V175's predicted 0.260x.  But the record already says the ratchet's axis is WHEEL
RATE (1.16x at 2 deg/s -> 3.94x at 100 deg/s), so much of that spread should be operating point,
not noise.  Regress it out and see what the residual is.

This is the right way to buy power: it costs the operator NOTHING, versus asking for more passes.
Controls, so this is not just overfitting:
  * leave-one-out residual sd (not in-sample), since with n=27 an in-sample R^2 flatters badly;
  * a PERMUTATION control -- shuffle the covariate and confirm the gain disappears.
"""
import os, sys
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS, WIN, NPS = 100.0, int(15 * 100), 512
CTRL = (30.0, 40.0)
ROUTES = ['r77', 'r21', 'ra6', 'r1e', 'ra4', 'r7e', 'r7f', 'r95', 'r81', 'r82',
          'r78', 'r79', 'r85', 'r96', 'r9e', 'ra5', 'r22', 'r24', 'r97']


def windows():
    out = []
    for tag in ROUTES:
        p = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
        if not os.path.exists(p):
            continue
        z = np.load(p, allow_pickle=True)
        need = ('cc_lat', 'cs_v', 'cs_tq', 'cs_rate')
        if any(k not in z.files for k in need):
            continue
        lat = np.asarray(z['cc_lat']).astype(float)
        v = np.asarray(z['cs_v']).astype(float)
        a = np.asarray(z['cs_tq']).astype(float)
        r = np.asarray(z['cs_rate']).astype(float)
        cmd = np.asarray(z['cc_req']).astype(float) if 'cc_req' in z.files else np.zeros_like(a)
        n = min(len(lat), len(v), len(a), len(r), len(cmd))
        lat, kmh, a, r, cmd = lat[:n], v[:n] * 3.6, a[:n], r[:n], cmd[:n]
        ok = (lat > 0.5) & (kmh >= 1.0) & (kmh < 24.0) & np.isfinite(a) & np.isfinite(r)
        d = np.diff(np.concatenate(([0], ok.view(np.int8), [0])))
        for i, j in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
            if (j - i) >= WIN and np.std(a[i:i + WIN]) > 0:
                out.append((a[i:i + WIN], r[i:i + WIN], kmh[i:i + WIN], cmd[i:i + WIN], tag))
    return out


def bp(x, lo, hi):
    f, P = signal.welch(x - x.mean(), FS, nperseg=NPS, noverlap=NPS // 2)
    m = (f >= lo) & (f <= hi)
    tr = np.trapezoid if hasattr(np, 'trapezoid') else np.trapz
    return float(tr(P[m], f[m]))


W = windows()
print('engaged 15 s windows with rate available: %d' % len(W))
y, X, tags = [], [], []
for a, r, kmh, cmd, tag in W:
    s = bp(a, 6.5, 11.0) / max(bp(a, *CTRL), 1e-30)
    if not np.isfinite(s) or s <= 0:
        continue
    y.append(np.log10(s))
    X.append([np.log10(np.mean(np.abs(r)) + 1e-3),
              np.log10(np.mean(kmh) + 1e-3),
              np.log10(np.mean(np.abs(cmd)) + 1e-3)])
    tags.append(tag)
y = np.asarray(y)
X = np.asarray(X)
print('usable: %d' % len(y))
print('\nraw log10 sd                       %.4f   -> detect@1 pass %.2fx'
      % (y.std(ddof=1), 10 ** (1.96 * y.std(ddof=1))))

NAMES = ['log|wheel rate|', 'log speed', 'log|command|']


def loo_sd(cols):
    """leave-one-out residual sd -- honest, not in-sample."""
    A = np.column_stack([np.ones(len(y))] + [X[:, c] for c in cols])
    res = []
    for k in range(len(y)):
        m = np.ones(len(y), bool)
        m[k] = False
        try:
            beta, *_ = np.linalg.lstsq(A[m], y[m], rcond=None)
        except np.linalg.LinAlgError:
            return np.nan
        res.append(y[k] - A[k] @ beta)
    return float(np.std(res, ddof=1))


print('\nLEAVE-ONE-OUT residual sd after adjusting for:')
best = (y.std(ddof=1), None)
for cols in ([0], [1], [2], [0, 1], [0, 2], [0, 1, 2]):
    sd = loo_sd(cols)
    det = 10 ** (1.96 * sd)
    mark = ''
    if sd < best[0]:
        best = (sd, cols)
    print('   %-34s sd %.4f   detect@1 %.2fx%s'
          % (' + '.join(NAMES[c] for c in cols), sd, det, mark))

print('\nPERMUTATION CONTROL -- shuffle the covariates, the gain must VANISH')
rng = np.random.default_rng(9)
perm = []
for _ in range(200):
    Xs = X[rng.permutation(len(y))]
    A = np.column_stack([np.ones(len(y)), Xs[:, 0]])
    r_ = []
    for k in range(len(y)):
        m = np.ones(len(y), bool)
        m[k] = False
        beta, *_ = np.linalg.lstsq(A[m], y[m], rcond=None)
        r_.append(y[k] - A[k] @ beta)
    perm.append(np.std(r_, ddof=1))
perm = np.asarray(perm)
real = loo_sd([0])
print('   real (wheel rate)     sd %.4f' % real)
print('   shuffled              sd %.4f  [p5 %.4f, p95 %.4f]'
      % (perm.mean(), np.percentile(perm, 5), np.percentile(perm, 95)))
print('   -> %s' % ('REAL: the adjustment beats its own permutation null'
                    if real < np.percentile(perm, 5) else
                    'NOT REAL: the shuffled covariate does just as well -- adjustment is NOISE'))

print('\nVERDICT for the V175 card')
sd = best[0]
det = 10 ** (1.96 * sd)
print('   best honest sd %.4f -> one pass detects %.2fx' % (sd, det))
print('   V175 predicts the ratchet band at 0.260x (a 3.85x cut)')
print('   => %s' % ('ANSWERABLE FROM ONE PASS after adjustment'
                    if det <= 1 / 0.260 else
                    'STILL NOT answerable from one pass -- keep the 2-pass ask'))
