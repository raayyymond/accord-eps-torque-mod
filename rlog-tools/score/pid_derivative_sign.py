#!/usr/bin/env python3
r"""DOES THE RESONANCE PID'S D TERM DAMP OR PUMP AT THE RATCHET?  The sign, from measured phase.

THE QUESTION THIS SETTLES.  FUN_0003a382 runs a D gain of 2048 (Q10 2.0) against a P gain of 256 --
eight times larger -- through a derivative pole (0xC644A) that reads 1024 on all 18 flown builds, i.e.
a PASSTHROUGH.  So the lane injects a genuinely raw derivative whose gain rises with frequency.  That
is sizeable.  What was missing is its SIGN: reducing D could damp the loop or destabilise it, and
without the sign a build is a coin flip.

THE SIGN IS COMPUTABLE, NOT UNKNOWABLE.  The PID's error is torque-derived -- `gp-0x4f60` minus a
clamped feedback term -- and its output joins the motor torque.  So the D term injects a torque
proportional to `d(tq)/dt`, which LEADS `tq` by exactly 90 degrees.  Damping requires torque in
antiphase with RATE (180 degrees); pumping is torque in phase with rate (0 degrees).  Therefore:

    phase of the D contribution relative to rate  =  arg(Z) + 90 degrees,     Z = tq / rate

    arg(Z) ~ +90  =>  D lands near 180  =>  the D term DAMPS, and cutting it would HURT
    arg(Z) ~ -90  =>  D lands near   0  =>  the D term PUMPS, and cutting it would HELP

`arg(Z)` is measurable on `tq` and `cs_rate`, both NON-RECTIFIED, with the same coherence gate used
throughout.  The record's own delay fit (tau 28 ms, R^2 0.82) predicts arg(Z) ~ -86 degrees at 8.5 Hz,
which would put the D term at +4 degrees -- almost pure pumping -- but that fit is not the same thing
as a direct measurement, so this measures it.

\U0001f6d1 WHAT THIS DOES AND DOES NOT ESTABLISH.  It gives the sign of the D term's CONTRIBUTION under
the assumption that the plant seen by the injected torque is the same plant `Z` describes.  That is the
standard small-signal argument and it is how the damper's own sign was settled, but it is a model step,
not a measurement of the D term itself.  Marked BELIEF accordingly.

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
import math
import os
import sys

import numpy as np
from scipy import signal

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BAND = (6.0, 9.5)
GRIND = (22.0, 30.0)
MIN_COH = 0.60
WIN_S = 2.0


def phases(path, band):
    """Complex Z = tq/rate per engaged window, coherence-gated."""
    z = np.load(path, allow_pickle=True)
    if not {'t', 'tq', 'cs_rate', 'cc_lat'} <= set(z.files):
        return []
    t = np.asarray(z['t'], float)
    n = len(t)
    q = np.asarray(z['tq'], float)[:n]
    r = np.asarray(z['cs_rate'], float)[:n]
    e = (np.asarray(z['cc_lat'], float) > 0.5)[:n]
    if len(q) < n or len(r) < n:
        return []
    fs = 1.0 / np.median(np.diff(t))
    lo, hi = band[0] / (fs / 2), band[1] / (fs / 2)
    if hi >= 1.0:
        return []
    b, a = signal.butter(3, [lo, hi], btype='band')
    qa = signal.hilbert(signal.filtfilt(b, a, q - q.mean()))
    ra = signal.hilbert(signal.filtfilt(b, a, r - r.mean()))
    w = int(WIN_S * fs)
    out = []
    for i in range(0, n - w, w):
        sl = slice(i, i + w)
        if e[sl].mean() < 0.98:
            continue
        rr, qq = ra[sl], qa[sl]
        den = float(np.mean(np.abs(rr) ** 2))
        if den < 1e-6:
            continue
        cxy = np.mean(qq * np.conj(rr))
        coh = float(abs(cxy) ** 2 / max(den * float(np.mean(np.abs(qq) ** 2)), 1e-30))
        if coh >= MIN_COH:
            out.append(cxy / den)
    return out


def circ_median_deg(zs):
    """Median phase, via the circular mean direction (phases wrap)."""
    v = np.array([complex(x) for x in zs])
    ang = np.angle(v)
    m = np.angle(np.mean(np.exp(1j * ang)))
    return math.degrees(m)


def main():
    print('=' * 88)
    print('  DOES THE PID D TERM DAMP OR PUMP?   arg(Z) + 90 deg, on non-rectified instruments')
    print('=' * 88)
    print()
    print('  the D term injects torque proportional to d(tq)/dt, which LEADS tq by 90 deg.')
    print('  damping = torque antiphase with rate (180 deg).  pumping = in phase (0 deg).\n')
    for label, band in (('ratchet 6-9.5 Hz', BAND), ('grinding 22-30 Hz', GRIND)):
        allz = []
        seen = set()
        for p in (sorted(glob.glob('_scratch/cache/*/*.npz')) +
                  sorted(glob.glob('analysis-2020accord/_scratch/cache/*/*.npz'))):
            r = os.path.basename(p)[:-4]
            if r in seen or 's' in r[1:]:
                continue
            seen.add(r)
            try:
                allz += phases(p, band)
            except Exception:
                continue
        if len(allz) < 200:
            print('  %-20s too few windows (%d)' % (label, len(allz)))
            continue
        argz = circ_median_deg(allz)
        d_phase = argz + 90.0
        while d_phase > 180:
            d_phase -= 360
        while d_phase < -180:
            d_phase += 360
        # cos of the angle to 180 deg: +1 = pure damping, -1 = pure pumping
        damp = -math.cos(math.radians(d_phase))
        print('  %-20s %d windows' % (label, len(allz)))
        print('     arg(Z)                  %+8.1f deg' % argz)
        print('     D contribution          %+8.1f deg  (arg(Z) + 90)' % d_phase)
        print('     damping fraction        %+8.3f     (+1 = pure damp, -1 = pure pump)' % damp)
        if damp < -0.5:
            print('     => the D term PUMPS here. Cutting it should HELP.')
        elif damp > 0.5:
            print('     => the D term DAMPS here. Cutting it would HURT.')
        else:
            print('     => near quadrature: the D term is mostly a SPRING here, neither damping')
            print('        nor pumping, so cutting it changes stiffness more than stability.')
        print()
    print('  \U0001f6d1 [BELIEF] this gives the sign of the D term\'s CONTRIBUTION assuming the plant')
    print('     seen by the injected torque is the plant Z describes. That is the standard')
    print('     small-signal argument -- the same one that settled the damper\'s sign -- but it is a')
    print('     model step, not a direct measurement of the D term.')


if __name__ == '__main__':
    main()
