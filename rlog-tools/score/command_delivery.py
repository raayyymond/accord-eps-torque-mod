# -*- coding: utf-8 -*-
"""Does the LKAS command turn into WHEEL MOTION?

The previous cut correlated the command against cs_tq, which is the DRIVER torque at the
torsion bar -- with hands off there is no reason for it to track the command, so a low
correlation there proves nothing.  The kit has no delivered-motor-torque channel either
(memory: steeringTorqueEps and raw 427 MOTOR_TORQUE are both ~0 and are not delivery
anchors).

The channel that DOES answer it is the steering ANGLE RATE: a torque command that is being
delivered must move the wheel.  Cross-correlate command against cs_rate over a lag sweep,
engaged frames only, with a phase-shuffled surrogate control so "the plant responds" can be
distinguished from "two smooth signals correlate".

Also stratify by command magnitude: delivery may be fine for large commands and fail for
small ones, which is what a friction/stiction-limited plant looks like and is exactly the
regime the operator describes.
"""
import os, sys
import numpy as np
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

FS = 100.0
ROUTES = [('r78', 'V91'), ('r7e', 'V96'), ('r96', 'V102'), ('ra6', 'V106'),
          ('r1e', 'V107'), ('r22', 'V112'), ('r24', 'V122')]
RNG = np.random.default_rng(51)


def arrs(tag):
    p = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
    if not os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    need = ('cc_lat', 'sc_tq', 'cs_rate', 'cs_v')
    if any(k not in z.files for k in need):
        return None
    lat = np.asarray(z['cc_lat']).astype(float)
    cmd = np.asarray(z['sc_tq']).astype(float)
    rate = np.asarray(z['cs_rate']).astype(float)
    v = np.asarray(z['cs_v']).astype(float)
    n = min(len(lat), len(cmd), len(rate), len(v))
    m = (lat[:n] > 0.5) & np.isfinite(cmd[:n]) & np.isfinite(rate[:n])
    return cmd[:n][m], rate[:n][m], v[:n][m] * 3.6


def best_lag(x, y, maxlag=40):
    """Correlation of x with y over lags 0..maxlag samples; returns (lag, r)."""
    x = x - x.mean()
    y = y - y.mean()
    best = (0, 0.0)
    for L in range(maxlag + 1):
        a, b = x[:len(x) - L], y[L:]
        if len(a) < 500 or np.std(a) == 0 or np.std(b) == 0:
            continue
        r = float(np.corrcoef(a, b)[0, 1])
        if abs(r) > abs(best[1]):
            best = (L, r)
    return best


def shuffle(a):
    F = np.fft.rfft(a - a.mean())
    ph = RNG.uniform(0, 2 * np.pi, len(F))
    ph[0] = 0
    return np.fft.irfft(np.abs(F) * np.exp(1j * ph), len(a))


print('COMMAND -> STEERING RATE, engaged frames, best lag in 0-400 ms\n')
print('%-6s %-6s %-8s %-10s %-9s %-11s %s'
      % ('route', 'build', 'n', 'best lag', 'corr', 'shuf p95', 'verdict'))
for tag, bld in ROUTES:
    a = arrs(tag)
    if a is None:
        continue
    cmd, rate, kmh = a
    if cmd.size < 2000:
        continue
    L, r = best_lag(cmd, rate)
    null = [abs(best_lag(shuffle(cmd), rate)[1]) for _ in range(20)]
    p95 = float(np.percentile(null, 95))
    print('%-6s %-6s %-8d %-10s %-9.3f %-11.3f %s'
          % (tag, bld, cmd.size, '%d ms' % int(L * 1000 / FS), r, p95,
             'DELIVERED' if abs(r) > p95 else 'not above chance'))

print('\nSTRATIFIED BY COMMAND MAGNITUDE -- does delivery fail for SMALL commands?')
print('%-6s %-6s %-14s %-14s %-14s %s'
      % ('route', 'build', '|cmd| 0-200', '200-800', '800-2000', '2000+'))
for tag, bld in ROUTES:
    a = arrs(tag)
    if a is None:
        continue
    cmd, rate, kmh = a
    cells = []
    for lo, hi in ((0, 200), (200, 800), (800, 2000), (2000, 1e9)):
        m = (np.abs(cmd) >= lo) & (np.abs(cmd) < hi)
        if m.sum() < 800:
            cells.append('%-14s' % '-')
            continue
        # mean |rate| achieved per 1000 counts of command, in that stratum
        g = np.abs(rate[m]).mean() / max(np.abs(cmd[m]).mean(), 1e-9) * 1000.0
        cells.append('%-14.2f' % g)
    print('%-6s %-6s %s' % (tag, bld, ' '.join(cells)))
print('\n  units: mean |deg/s| of wheel motion per 1000 counts of command, within the stratum.')
print('  A plant limited by friction/stiction delivers LESS per count at SMALL commands.')
