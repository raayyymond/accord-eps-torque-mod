#!/usr/bin/env python3
r"""IS THE 6-9 Hz ANTI-DAMPING A COULOMB RELAY?  Its describing function is the fingerprint.

THE QUESTION.  The system is anti-damped at 6-9 Hz (Re(Z) < 0 on 31/31 routes, measured on
non-rectified instruments -- see `rez_nonrectified_replication.py`), yet EVERY individually tapped lane
measures as DAMPING there.  No set of damping LINEAR lanes can produce an anti-damped system, so the
source must be NONLINEAR.  The record's standing candidate is a command-proportional COULOMB RELAY.

THE TEST, and it needs no probe, no build and no drive.  A relay (signum nonlinearity) has an
AMPLITUDE-DEPENDENT describing function:

    N(A) = 4F / (pi * A)          =>   effective gain proportional to 1/A

so its contribution to Re(Z) must FALL as the oscillation amplitude rises.  A linear element's does
not.  Fit log|Re(Z)| against log A across windows:

    slope ~ -1   COULOMB RELAY        (the standing hypothesis, confirmed)
    slope ~  0   LINEAR               (relay exonerated; the nonlinear search reopens)
    slope >  0   growing with drive   (saturation/parametric, NOT a relay)

METHOD.  Band-pass `tq` and `cs_rate` to 6-9.5 Hz, take analytic signals, and per 2 s window compute
    A      = rms|rate_a|                          the band oscillation amplitude
    Re(Z)  = Re(<tq_a conj(rate_a)>/<|rate_a|^2>) the in-phase (damping) part
Windows are pooled across routes; the regression is over windows, and a per-ROUTE median slope is
reported alongside so one long route cannot carry the fit.

BOTH INSTRUMENTS ARE NON-RECTIFIED -- neither passes through FUN_00055d80, so unlike every 427-derived
phase this sign and its amplitude dependence are actually measured.

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

import glob
import os
import sys

import numpy as np
from scipy import signal, stats

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BAND = (6.0, 9.5)
CTL = (22.0, 30.0)          # control band: engagement DAMPS here, so the relay should not show
WIN_S = 2.0
MIN_WIN = 40
MIN_A = 1e-6


def windows(t, q, r, eng, fs, band):
    """Per-window (A, Re(Z)) inside `band`, engaged frames only."""
    lo, hi = band[0] / (fs / 2), band[1] / (fs / 2)
    if hi >= 1.0:
        return None
    b, a = signal.butter(3, [lo, hi], btype='band')
    qa = signal.hilbert(signal.filtfilt(b, a, q - q.mean()))
    ra = signal.hilbert(signal.filtfilt(b, a, r - r.mean()))
    n = int(WIN_S * fs)
    out = []
    for i in range(0, len(t) - n, n):
        sl = slice(i, i + n)
        if eng[sl].mean() < 0.98:
            continue
        rr, qq = ra[sl], qa[sl]
        den = float(np.mean(np.abs(rr) ** 2))
        if den < MIN_A:
            continue
        A = float(np.sqrt(den))
        Z = np.mean(qq * np.conj(rr)) / den
        out.append((A, float(Z.real)))
    return out


def slope(rows):
    """log-log slope of |Re(Z)| against A, over the ANTI-DAMPED windows."""
    neg = [(A, -z) for A, z in rows if z < 0 and A > MIN_A]
    if len(neg) < MIN_WIN:
        return None
    x = np.log(np.array([A for A, _ in neg]))
    y = np.log(np.array([m for _, m in neg]))
    lr = stats.linregress(x, y)
    return lr.slope, lr.rvalue ** 2, len(neg), lr.pvalue


def main():
    print('=' * 92)
    print('  IS THE 6-9 Hz ANTI-DAMPING A COULOMB RELAY?   describing function N(A) = 4F/(pi A)')
    print('=' * 92)
    print('\n  a relay\'s effective gain goes as 1/A, so log|Re(Z)| vs log A must have slope ~ -1.')
    print('  a linear element gives slope ~ 0. Both instruments are NON-RECTIFIED.\n')
    print('  %-7s %7s %9s %7s %9s %9s' %
          ('route', 'wins', 'slope', 'R2', 'ctl slope', 'ctl R2'))
    print('  ' + '-' * 54)
    allrows, allctl, per, perctl = [], [], [], []
    seen = set()
    for p in (sorted(glob.glob('_scratch/cache/*/*.npz')) +
              sorted(glob.glob('analysis-2020accord/_scratch/cache/*/*.npz'))):
        r = os.path.basename(p)[:-4]
        if r in seen or 's' in r[1:]:
            continue
        try:
            z = np.load(p, allow_pickle=True)
        except Exception:
            continue
        if not {'t', 'tq', 'cs_rate', 'cc_lat'} <= set(z.files):
            continue
        seen.add(r)
        t = np.asarray(z['t'], float)
        n = len(t)
        q = np.asarray(z['tq'], float)[:n]
        ra = np.asarray(z['cs_rate'], float)[:n]
        e = (np.asarray(z['cc_lat'], float) > 0.5)[:n]
        if len(q) < n or len(ra) < n:
            continue
        fs = 1.0 / np.median(np.diff(t))
        w = windows(t, q, ra, e, fs, BAND)
        c = windows(t, q, ra, e, fs, CTL)
        if not w:
            continue
        allrows += w
        allctl += (c or [])
        sw, sc = slope(w), slope(c or [])
        if sw:
            per.append(sw[0])
        if sc:
            perctl.append(sc[0])
        print('  %-7s %7d %9s %7s %9s %9s' %
              (r, len(w),
               ('%.3f' % sw[0]) if sw else '--', ('%.2f' % sw[1]) if sw else '--',
               ('%.3f' % sc[0]) if sc else '--', ('%.2f' % sc[1]) if sc else '--'))
    print('  ' + '-' * 54)
    g, gc = slope(allrows), slope(allctl)
    if not g:
        print('\n  too few anti-damped windows to fit.')
        return
    print('\n  POOLED 6-9.5 Hz : slope %+.3f   R2 %.3f   over %d windows   p %.2e'
          % (g[0], g[1], g[2], g[3]))
    if gc:
        print('  POOLED %4.0f-%2.0f Hz : slope %+.3f   R2 %.3f   over %d windows   p %.2e'
              % (CTL[0], CTL[1], gc[0], gc[1], gc[2], gc[3]))
    if per:
        print('  PER-ROUTE slope : median %+.3f over %d routes  (so no single route carries the fit)'
              % (float(np.median(per)), len(per)))
    if perctl:
        print('  PER-ROUTE ctl   : median %+.3f over %d routes' % (float(np.median(perctl)), len(perctl)))
    print()
    s = g[0]
    if s < -0.75:
        print('  => SLOPE NEAR -1: the COULOMB RELAY signature. The standing hypothesis is CONFIRMED,')
        print('     and the lever is the relay, not any linear lane.')
    elif s > -0.25:
        print('  => SLOPE NEAR 0: AMPLITUDE-INDEPENDENT, which is NOT a relay. The command-proportional')
        print('     Coulomb relay is EXONERATED as the 6-9 Hz source and the nonlinear search reopens.')
    else:
        print('  => SLOPE INTERMEDIATE (%.2f): neither signature cleanly. Do not call it either way.' % s)
    print('\n  \U0001f6d1 A(t) and Re(Z) are not independent of SPEED or of driver input; this fit is a')
    print('     SCREEN on the amplitude dependence, not a controlled experiment.')


if __name__ == '__main__':
    main()
