#!/usr/bin/env python3
r"""IS THE 6-9 Hz ANTI-DAMPING A LOOP DELAY, OR A GAIN?

The record's stock baseline says Re(Z) at 6-9 Hz is NEGATIVE at every speed -- the anti-damping is
Honda's, and we only multiply it.  Nothing in the arc has ever located what CREATES it, and every
calibration lever is now measured and closed.  This test discriminates the two mechanisms that could
produce it, using only data already on disk.

    Z(f) = steeringTorque(f) / steeringRateDeg(f)     both from the same 0x18F frame, so staleness
                                                      cancels -- the record's own estimator convention

  * A PURE DELAY of tau seconds contributes  arg(Z) = -2*pi*f*tau,  i.e. phase FALLS LINEARLY with
    frequency and Re(Z) goes negative above the quarter-wave frequency  f = 1/(4*tau).
  * A GAIN (or a minimum-phase filter well away from its corner) contributes a phase that is FLAT, or
    that saturates -- it does not keep rotating.

So: fit arg(Z) against f over the band where coherence supports it.  A good linear fit with a
consistent tau across routes and speeds says DELAY, and the fix is to find and shorten the delay.  A
flat or incoherent phase says the anti-damping is not a delay artifact and the search has to go
somewhere else.

WHY IT MATTERS.  If it is a delay, tau is the single number that sets the anti-damping frequency, and
it is made of enumerable parts: the 1 kHz task period, the sensor filtering, the EMA lag (which alone
is -77 deg at 7.79 Hz on the car), the biquad, and the motor.  That would be the first mechanism this
arc has found that is not a calibration.

WHAT THIS IS NOT.  Z here is the CAR's driver-side impedance as seen on CAN at ~101 Hz, so anything
above ~50 Hz is aliased and the fit is restricted to well below that.  It also cannot separate the
firmware's delay from the mechanical plant's own phase -- it measures the total.

PATH BOOTSTRAP -- see the note in the sibling scripts.
"""
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_sys.path[:0] = [_r] + ([_repo] if _repo else [])
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_v"):
    globals().pop(_v, None)

import glob
import os
import sys

import numpy as np
from scipy import signal

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# score/ -> rlog-tools/ -> repo root: THREE dirnames, not two (the two-level form silently
# globbed an empty tree and printed a clean-looking table of zero routes).
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIT_LO, FIT_HI = 3.0, 20.0      # well inside Nyquist (~50 Hz); spans the ratchet at 7.79
COH_MIN = 0.30
MIN_ENG = 3000


def analyse(path):
    z = np.load(path, allow_pickle=True)
    if not {'tq', 'rate_f', 'cc_lat', 't'} <= set(z.files):
        return None
    eng = np.asarray(z['cc_lat'], float) > 0.5
    tq = np.asarray(z['tq'], float)
    rt = np.asarray(z['rate_f'], float)
    n = min(len(eng), len(tq), len(rt))
    eng, tq, rt = eng[:n], tq[:n], rt[:n]
    if eng.sum() < MIN_ENG:
        return None
    t = np.asarray(z['t'], float)[:n]
    fs = 1.0 / np.median(np.diff(t))
    x, y = tq[eng], rt[eng]
    if len(x) < 4096:
        return None
    npg = 1024
    f, Pxy = signal.csd(y, x, fs, nperseg=npg)      # Z = torque / rate  => csd(rate, torque)
    _, Pxx = signal.welch(y, fs, nperseg=npg)
    _, Pyy = signal.welch(x, fs, nperseg=npg)
    coh = np.abs(Pxy) ** 2 / np.maximum(Pxx * Pyy, 1e-30)
    m = (f >= FIT_LO) & (f <= FIT_HI) & (coh >= COH_MIN)
    if m.sum() < 8:
        return None
    ph = np.unwrap(np.angle(Pxy[m]))
    ff = f[m]
    A = np.vstack([ff, np.ones_like(ff)]).T
    sol, res, _, _ = np.linalg.lstsq(A, ph, rcond=None)
    slope, icept = sol
    pred = A @ sol
    ss_res = float(((ph - pred) ** 2).sum())
    ss_tot = float(((ph - ph.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float('nan')
    tau_ms = -slope / (2 * np.pi) * 1000.0
    # Re(Z) in the ratchet band, the record's own quantity
    rb = (f >= 6) & (f <= 9)
    reZ = float(np.real(Pxy[rb]).sum())
    return dict(route=os.path.basename(path), n=int(eng.sum()), fs=fs, tau_ms=tau_ms,
                r2=r2, npts=int(m.sum()), reZ=reZ, cohmed=float(np.median(coh[m])))


def main():
    caches = sorted(glob.glob(os.path.join(REPO, '_scratch', 'cache', '*', '*.npz')))
    if len(sys.argv) > 1:
        caches = [c for c in caches if any(a in c for a in sys.argv[1:])]
    rows = []
    for c in caches:
        try:
            r = analyse(c)
        except Exception:
            continue
        if r:
            rows.append(r)
        if len(rows) >= 24:
            break

    print('=' * 92)
    print('  IS THE 6-9 Hz ANTI-DAMPING A LOOP DELAY?   arg(Z) fitted against f over %.0f-%.0f Hz'
          % (FIT_LO, FIT_HI))
    print('=' * 92)
    print('  %-14s %8s %7s %9s %8s %7s %12s' %
          ('route', 'eng.f', 'fs Hz', 'tau ms', 'R^2', 'coh', 'Re(Z) 6-9'))
    print('  ' + '-' * 78)
    for r in rows:
        print('  %-14s %8d %7.2f %9.2f %8.3f %7.2f %12.4g'
              % (r['route'], r['n'], r['fs'], r['tau_ms'], r['r2'], r['cohmed'], r['reZ']))

    if rows:
        tau = np.array([r['tau_ms'] for r in rows])
        r2 = np.array([r['r2'] for r in rows])
        neg = sum(1 for r in rows if r['reZ'] < 0)
        print('  ' + '-' * 78)
        print('  %d routes.  tau median %.2f ms  [p10 %.2f, p90 %.2f]   R^2 median %.3f'
              % (len(rows), np.median(tau), np.percentile(tau, 10), np.percentile(tau, 90),
                 np.median(r2)))
        print('  Re(Z) at 6-9 Hz is NEGATIVE on %d of %d routes' % (neg, len(rows)))
        q = 1000.0 / (4 * np.median(tau)) if np.median(tau) > 0 else float('nan')
        print()
        print('  READING IT:')
        print('   * a high R^2 with a consistent tau => the phase is a DELAY, and the quarter-wave')
        print('     frequency 1/(4*tau) = %.2f Hz is where Re(Z) must cross into anti-damping.' % q)
        print('   * the ratchet sits at 7.79 Hz.  If those two agree, the anti-damping is a DELAY')
        print('     artifact and tau is the thing to shorten -- the first non-calibration mechanism')
        print('     this arc has found.')
        print('   * a low R^2, or tau scattered across routes, means it is NOT a simple delay and')
        print('     this line of attack is closed too.')
        print()
        print('  \U0001f6d1 Z is measured on CAN at ~101 Hz, so the fit is held well below Nyquist, and')
        print('     it cannot separate the firmware delay from the plant\'s own phase.')


if __name__ == '__main__':
    main()
