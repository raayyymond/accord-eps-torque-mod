#!/usr/bin/env python3
r"""HOW FAR CAN LEVER B USEFULLY GO?  The describing function priced against MEASURED amplitudes.

Lever B is the one cell that moves the ratchet without spending forward authority (within gain 6x,
5244 is +5.81 less anti-damped than 512, p 0.0556).  V246 takes it 5244 -> 7866.  The question this
answers is whether MORE would deliver more, and it needs no drive -- the lane is a plain saturation and
its arithmetic is known:

    scaled = (clamp(gp-0x4f62, +-5120) * k) >> 10      0x3AC18 / 0x3AC20
    shaped = deadzone(scaled, +-3)                     0x3AC24, cal 0xC61F6
    out    = clamp(polarity * shaped, +-8192)          0x3AC42 / 0x3AC46

So the lane is LINEAR in k while  k*A/1024 <= 8192,  i.e. while  A <= 8388608/k,  and saturates above
it.  For a sinusoid of amplitude A the sinusoidal-input describing function gives the damping the loop
actually sees:

    N(A)/k = 1                                                for rho <= 1
    N(A)/k = (2/pi)[asin(1/rho) + (1/rho)sqrt(1-1/rho^2)]     rho = k*A/(8192*1024)
    as k -> inf,  N(A) -> 4*8192*1024/(pi*A)   -- a CONSTANT independent of k

\U0001f6d1 THE POINT.  If the measured torque-rate amplitudes sit BELOW the knee, then N(A) = k exactly
and raising the dose buys damping PROPORTIONALLY -- there is no diminishing return to discover.  If they
sit above it, extra dose is wasted.  This script reads the amplitudes off the flown routes rather than
assuming them, and reports the effective damping at each candidate dose.

The doses that matter: 5244 (V88's bracketed optimum, on V241 and the car), 7866 (V246, 1.5x), and
13107 (V222/V231-V233's 2.5x, which the record flagged as over-dosing V88's GRINDING optimum).

\U0001f6d1 WHAT THIS DOES NOT SETTLE.  5244 was bracketed for GRINDING, not for the ratchet.  A dose
that is better at 6-9 Hz can still be worse at 22-30 Hz, and this computation says nothing about that.
It prices the RATCHET side only.

PATH BOOTSTRAP -- see the note in the sibling scripts.
"""
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_sys.path[:0] = [_r]
for _v in ("_os", "_sys", "_r", "_n", "_v"):
    globals().pop(_v, None)

import math
import os
import sys

import numpy as np
from scipy import signal

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAIL = 8192.0          # output clamp, immediates at 0x3AC42/0x3AC46
Q = 1024.0             # >> 10
IN_CLAMP = 5120.0      # input clamp on gp-0x4f62
DOSES = [(5244, 'V241 / the car -- V88 bracketed'), (7866, 'V246, 1.5x'),
         (13107, 'V222 & V231-V233, 2.5x')]
ROUTES = ('r24', 'ra6', 'r1e', 'r96')


def N_over_k(k, A):
    """Sinusoidal-input describing function of the saturation, normalised to k."""
    rho = k * A / (RAIL * Q)
    if rho <= 1.0:
        return 1.0
    r = 1.0 / rho
    return (2.0 / math.pi) * (math.asin(r) + r * math.sqrt(max(0.0, 1.0 - r * r)))


def rate_amplitudes(route):
    """6-9.5 Hz envelope of the torque RATE, engaged frames, in the lane's own counts."""
    p = None
    for c in (os.path.join(REPO, '_scratch', 'cache', route, route + '.npz'),
              os.path.join(REPO, 'analysis-2020accord', '_scratch', 'cache', route, route + '.npz')):
        if os.path.exists(c):
            p = c
            break
    if not p:
        return None
    z = np.load(p, allow_pickle=True)
    if not {'t', 'tq', 'cc_lat'} <= set(z.files):
        return None
    t = np.asarray(z['t'], float)
    n = len(t)
    q = np.asarray(z['tq'], float)[:n]
    e = (np.asarray(z['cc_lat'], float) > 0.5)[:n]
    if e.sum() < 5000:
        return None
    fs = 1.0 / np.median(np.diff(t))
    # 🛑 NOT np.gradient(q, t): the caches carry DUPLICATE timestamps, which divides by
    # zero and NaNs the whole envelope silently. Use the uniform sample rate.
    rate = np.gradient(q) * fs                     # gp-0x4f62 is the torque rate
    rate = np.clip(rate, -IN_CLAMP, IN_CLAMP)
    lo, hi = 6.0 / (fs / 2), 9.5 / (fs / 2)
    if hi >= 1.0:
        return None
    b, a = signal.butter(3, [lo, hi], btype='band')
    env = np.abs(signal.hilbert(signal.filtfilt(b, a, rate - rate.mean())))[e]
    return env[np.isfinite(env)]


def main():
    print('=' * 88)
    print('  HOW FAR CAN LEVER B USEFULLY GO?  describing function vs MEASURED torque-rate amplitude')
    print('=' * 88)
    print('\n  the lane is LINEAR in k while A <= %.0f/k. Knees at the candidate doses:' % (RAIL * Q))
    for k, lab in DOSES:
        print('     k = %-6d  linear up to A = %8.1f   (%s)' % (k, RAIL * Q / k, lab))

    pool = []
    print('\n  %-7s %10s %10s %10s %10s' % ('route', 'A p50', 'A p90', 'A p99', 'A max'))
    print('  ' + '-' * 52)
    for r in ROUTES:
        env = rate_amplitudes(r)
        if env is None or len(env) < 1000:
            continue
        pool.append(env)
        print('  %-7s %10.1f %10.1f %10.1f %10.1f'
              % (r, *[np.percentile(env, p) for p in (50, 90, 99)], env.max()))
    print('  ' + '-' * 52)
    if not pool:
        print('\n  no route measurable.')
        return
    allenv = np.concatenate(pool)

    print('\n  EFFECTIVE DAMPING N(A) THE LOOP ACTUALLY SEES, at each dose:')
    print('  %-8s %12s %12s %12s %14s' % ('A', 'k=5244', 'k=7866', 'k=13107', 'saturating?'))
    print('  ' + '-' * 62)
    for lab, A in (('p50', np.percentile(allenv, 50)), ('p90', np.percentile(allenv, 90)),
                   ('p99', np.percentile(allenv, 99)), ('max', allenv.max())):
        vals = [k * N_over_k(k, A) for k, _ in DOSES]
        sat = [k * A / (RAIL * Q) > 1.0 for k, _ in DOSES]
        print('  %-8s %12.0f %12.0f %12.0f   %s'
              % ('%s %.0f' % (lab, A), *vals,
                 'none' if not any(sat) else ', '.join(str(DOSES[i][0]) for i, x in enumerate(sat) if x)))
    print('  ' + '-' * 62)

    # amplitude-weighted: what fraction of engaged frames is each dose still linear on?
    print('\n  fraction of engaged frames on which the dose is still LINEAR (no dose wasted):')
    for k, lab in DOSES:
        frac = float((allenv <= RAIL * Q / k).mean())
        print('     k = %-6d  %6.2f %%   (%s)' % (k, 100 * frac, lab))

    print('\n  READING')
    lin13 = float((allenv <= RAIL * Q / 13107).mean())
    if lin13 > 0.97:
        print('  => even 2.5x is LINEAR on %.1f %% of engaged frames, so within this range MORE DOSE'
              % (100 * lin13))
        print('     BUYS PROPORTIONALLY MORE DAMPING at the ratchet -- there is no diminishing return')
        print('     to find, and V246 at 1.5x is a CONSERVATIVE step rather than an optimum.')
    else:
        print('  => 2.5x saturates on %.1f %% of frames, so the returns do flatten inside this range.'
              % (100 * (1 - lin13)))
    print('\n  \U0001f6d1 THIS PRICES THE RATCHET SIDE ONLY. 5244 is V88\'s bracketed optimum for')
    print('     GRINDING, and nothing here says a larger dose is safe at 22-30 Hz.')


if __name__ == '__main__':
    main()
