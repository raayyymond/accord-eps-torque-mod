# -*- coding: utf-8 -*-
"""Is the EXISTING 193-count damper step at 35 km/h measurable on the car?

If it is not, deepening it to 467 (to buy ~2x creep damping) is low risk and the damper
raise can be built on evidence rather than a guess.  If it IS measurable, the trade is real
and must wait for a drive.

FactorC X[0] = 2240 cal units; 2240/64 = 35.0 km/h exactly, which confirms the scale.
Method: find every crossing of 35 km/h, measure short-window torque activity centred on the
crossing, and compare against the SAME statistic at control speeds where no knot exists.
The controls are the whole point -- speed crossings are correlated with driving activity, so
a bare "torque is elevated at 35 km/h" result would prove nothing.
"""
import os, sys
import numpy as np
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS = 100.0
HALF = int(0.60 * FS)              # +-0.6 s around a crossing
ROUTES = ['r77', 'r21', 'ra6', 'r1e', 'ra4', 'r7e', 'r7f', 'r95', 'r81', 'r82',
          'r78', 'r79', 'r85', 'r96', 'r9e', 'ra5', 'r22', 'r24', 'r97', 'r1b', 'r23',
          'r7d', 'r80']


def load(tag):
    p = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
    if not os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('cs_v', 'cs_tq')):
        return None
    v = np.asarray(z['cs_v']).astype(float) * 3.6
    a = np.asarray(z['cs_tq']).astype(float)
    n = min(len(v), len(a))
    return v[:n], a[:n]


def crossings(v, thr):
    s = np.sign(v - thr)
    idx = np.where(np.diff(s) != 0)[0]
    # keep only clean, well-separated crossings with real speed change through the level
    out = []
    for i in idx:
        if i < HALF or i + HALF >= len(v):
            continue
        w = v[i - HALF:i + HALF]
        if np.ptp(w) < 3.0 or np.ptp(w) > 25.0:
            continue
        if out and i - out[-1] < 2 * HALF:
            continue
        out.append(i)
    return out


def activity(a, i):
    """short-window torque activity, detrended -- the thing a step would perturb"""
    w = a[i - HALF:i + HALF].astype(float)
    if not np.all(np.isfinite(w)):
        return np.nan
    w = w - np.polyval(np.polyfit(np.arange(len(w)), w, 1), np.arange(len(w)))
    return float(np.std(w))


LEVELS = [(35.0, 'THE KNOT (35 km/h)'), (25.0, 'control 25'), (45.0, 'control 45'),
          (30.0, 'control 30'), (40.0, 'control 40')]
res = {}
for thr, nm in LEVELS:
    vals = []
    for tag in ROUTES:
        d = load(tag)
        if d is None:
            continue
        v, a = d
        for i in crossings(v, thr):
            x = activity(a, i)
            if np.isfinite(x):
                vals.append(x)
    res[nm] = np.asarray(vals)

print('torque activity in a +-0.6 s window centred on each speed crossing')
print('%-22s %6s %10s %10s %10s' % ('level', 'n', 'p50', 'p90', 'mean'))
for thr, nm in LEVELS:
    v = res[nm]
    if len(v) == 0:
        print('%-22s %6d   (none)' % (nm, 0))
        continue
    print('%-22s %6d %10.2f %10.2f %10.2f'
          % (nm, len(v), np.median(v), np.percentile(v, 90), v.mean()))

k = res['THE KNOT (35 km/h)']
ctrl = np.concatenate([res[nm] for _, nm in LEVELS[1:] if len(res[nm])])
print('')
if len(k) < 8 or len(ctrl) < 8:
    print('TOO FEW CROSSINGS to decide (knot n=%d, control n=%d).' % (len(k), len(ctrl)))
    print('=> the question stays OPEN and the damper raise still needs a drive.')
else:
    rng = np.random.default_rng(5)
    obs = np.median(k) / np.median(ctrl)
    pool = np.concatenate([k, ctrl])
    lab = np.array([1] * len(k) + [0] * len(ctrl))
    null = []
    for _ in range(5000):
        p = rng.permutation(lab)
        null.append(np.median(pool[p == 1]) / np.median(pool[p == 0]))
    null = np.asarray(null)
    lo, hi = np.percentile(null, [2.5, 97.5])
    print('knot / control median ratio = %.3f' % obs)
    print('permutation null 95%% band  = [%.3f, %.3f]  (n=%d vs %d)'
          % (lo, hi, len(k), len(ctrl)))
    if lo <= obs <= hi:
        print('')
        print('=> NO measurable artifact at the existing 193-count step.')
        print('   The step is not detectable against speed-matched controls, so DEEPENING it')
        print('   to 467 to buy ~2x creep damping is a LOW-RISK trade, not a blind one.')
    else:
        print('')
        print('=> THE STEP IS MEASURABLE. Deepening it is a real cost; wait for the drive.')
