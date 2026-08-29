# -*- coding: utf-8 -*-
"""RING-DOWN: a time-domain estimator, immune to the spectral tilt that killed the others.

Everything this session rests on a frequency-domain excess measure, and the P.L assumption
behind the levers is said to be testable only by driving.  But the kit's own record notes
that a RING-DOWN estimate of the ratchet's Q "passed its control" where four spectral
measures failed -- and I have not used it this session.

A ring-down needs an abrupt end to the excitation followed by free decay.  The ratchet's
amplitude is MONOTONE in command, so a sharp command drop should leave the mode ringing
down at its own rate.  Decay rate gives zeta directly, and zeta is what 1-P.L sets:

    zeta_eff = zeta_passive * |1 - P.L|

so if |L| differs across builds, the measured DECAY RATE must differ too -- testable from
data already in hand, with no new drive.

Method: find engaged frames where |command| falls by a large factor within ~100 ms and
stays low; band-pass cs_tq around 8.64 Hz; fit an exponential to the envelope of the
following 0.5 s; report the implied zeta and Q.  Controls: the same fit on time-reversed
segments (a real decay is NOT symmetric) and on random engaged frames with no command drop.
"""
import os, sys
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

FS = 100.0
F0 = 8.64
ROUTES = [('r78', 'V91'), ('r7e', 'V96'), ('r7f', 'V96'), ('r96', 'V102'), ('ra4', 'V104'),
          ('ra6', 'V106'), ('r1e', 'V107'), ('r22', 'V112'), ('r24', 'V122')]
DECAY_N = 50            # 0.5 s of free decay
PRE_N = 10


def load(tag):
    p = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
    if not os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    need = ('cc_lat', 'cs_v', 'cs_tq', 'sc_tq')
    if any(k not in z.files for k in need):
        return None
    lat = np.asarray(z['cc_lat']).astype(float)
    v = np.asarray(z['cs_v']).astype(float)
    a = np.asarray(z['cs_tq']).astype(float)
    c = np.asarray(z['sc_tq']).astype(float)
    n = min(len(lat), len(v), len(a), len(c))
    return lat[:n], v[:n] * 3.6, a[:n], c[:n]


def envelope(x):
    """Analytic envelope of the band-passed signal around F0."""
    b, a_ = signal.butter(2, [(F0 - 2.5) / (FS / 2), (F0 + 2.5) / (FS / 2)], btype='band')
    y = signal.filtfilt(b, a_, x)
    return np.abs(signal.hilbert(y))


def fit_decay(env):
    """Exponential fit to the envelope: env ~ A exp(-alpha t). Returns (alpha, r2)."""
    t = np.arange(len(env)) / FS
    e = np.maximum(env, 1e-9)
    y = np.log(e)
    A = np.vstack([t, np.ones_like(t)]).T
    coef, res, *_ = np.linalg.lstsq(A, y, rcond=None)
    pred = A @ coef
    ss = 1 - np.sum((y - pred) ** 2) / max(np.sum((y - y.mean()) ** 2), 1e-30)
    return -coef[0], ss


def events(tag):
    d = load(tag)
    if d is None:
        return []
    lat, kmh, a, c = d
    out = []
    ac = np.abs(c)
    for i in range(PRE_N + 5, len(a) - DECAY_N - 5):
        if not (lat[i] > 0.5 and 1.0 <= kmh[i] < 24.0):
            continue
        pre = ac[i - PRE_N:i].mean()
        post = ac[i:i + DECAY_N].mean()
        if pre < 400:
            continue
        if post > 0.25 * pre:                     # command must actually collapse
            continue
        if not np.all(lat[i:i + DECAY_N] > 0.5):  # stay engaged through the decay
            continue
        seg = a[i - 5:i + DECAY_N]
        if not np.all(np.isfinite(seg)) or np.std(seg) == 0:
            continue
        out.append(seg)
    return out


print('RING-DOWN after abrupt command collapse (engaged creep)\n')
print('%-6s %-6s %-8s %-11s %-11s %-11s %-8s %s'
      % ('route', 'build', 'events', 'alpha 1/s', 'zeta', 'Q', 'CONTROL', 'verdict'))
rows = []
for tag, bld in ROUTES:
    ev = events(tag)
    if len(ev) < 4:
        print('%-6s %-6s %-8d  -- too few events' % (tag, bld, len(ev)))
        continue
    # PROPER CONTROL: the same fit on engaged segments with NO command collapse.
    # (The previous control -- fitting the time-REVERSED envelope -- was vacuous: reversing
    #  a linear fit's x-ordering flips the slope but leaves the residuals identical, so r2
    #  is invariant BY CONSTRUCTION and it could never discriminate.  It returned
    #  0.64/0.64, 0.61/0.61 ... on every route, which was the tell.)
    d = load(tag)
    lat, kmh, aa, cc = d
    rng = np.random.default_rng(0)
    ctrl = []
    idx = np.where((lat > 0.5) & (kmh >= 1.0) & (kmh < 24.0))[0]
    idx = idx[(idx > 20) & (idx < len(aa) - DECAY_N - 5)]
    for i in rng.choice(idx, size=min(300, len(idx)), replace=False):
        ac_ = np.abs(cc)
        if ac_[i:i + DECAY_N].mean() < 0.25 * max(ac_[i - PRE_N:i].mean(), 1e-9):
            continue                     # skip anything that IS a collapse
        seg = aa[i - 5:i + DECAY_N]
        if np.all(np.isfinite(seg)) and np.std(seg) > 0:
            a2, s2 = fit_decay(envelope(seg)[5:])
            if np.isfinite(a2) and s2 > 0.3:
                ctrl.append(a2)
    al, r2f = [], []
    for seg in ev:
        env = envelope(seg)[5:]
        a1, s1 = fit_decay(env)
        if np.isfinite(a1) and s1 > 0.3:
            al.append(a1)
            r2f.append(s1)
    if len(al) < 4:
        print('%-6s %-6s %-8d  -- too few usable fits' % (tag, bld, len(ev)))
        continue
    a_med = float(np.median(al))
    zeta = a_med / (2 * np.pi * F0)
    cmed = float(np.median(ctrl)) if len(ctrl) > 10 else float('nan')
    print('%-6s %-6s %-8d %-11.2f %-11.4f %-11.1f %-8s %s'
          % (tag, bld, len(al), a_med, zeta, 1 / (2 * zeta) if zeta > 0 else np.inf,
             '%.2f' % cmed if np.isfinite(cmed) else '-',
             'DECAY' if np.isfinite(cmed) and a_med > 1.5 * cmed else 'no better than control'))
    rows.append((bld, a_med, zeta))

print("""
CONTROL READING
  CONTROL is the same exponential fit on engaged segments with NO command collapse.
  If alpha after a collapse is not clearly LARGER than the control, the "ring-down" is
  just the generic envelope behaviour of a noisy band-passed signal and carries no
  damping information at all.""")
if len(rows) >= 4:
    z = np.array([r[2] for r in rows])
    print('\n  zeta across builds: %.4f - %.4f  (memory records 0.017-0.036 from ring-down)'
          % (z.min(), z.max()))
    print('  implied Q: %.1f - %.1f' % (1 / (2 * z.max()), 1 / (2 * z.min())))
