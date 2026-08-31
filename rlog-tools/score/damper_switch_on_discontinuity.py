#!/usr/bin/env python3
r"""DOES THE DAMPER HELP OR HURT?  A regression discontinuity at its own switch-on speed.

THE PROBLEM THIS SOLVES.  V249 opens the damper's speed dead zone and raises the GRINDING band 4.1x as
a side effect.  That direction is a hypothesis, not a finding -- V62's lesson on a different lane was
"2x is the OPTIMUM, not a point on a ramp", so more damping is not monotonically better.  Before flying
it, the flown corpus should be asked whether damping has ever made grinding worse.

WHY A DISCONTINUITY AND NOT A CORRELATION.  The damper is byte-stock in every flown build, so its
output varies only through the OPERATING POINT -- and higher motor rate means more damper AND more of
every symptom, which makes a plain correlation useless.  But `FactorC` has a hard dead zone:

    FactorC X[0] = 2240 counts = 35.0 km/h, Y[0] = 0     =>  damper is EXACTLY ZERO below 35 km/h
                                                             and live above it

That is a sharp, cal-driven switch at a fixed speed, and **nothing else in the firmware changes at
35 km/h**.  So a STEP in band energy at exactly that speed is attributable to the damper switching on,
while a smooth speed trend is not.  This is the one falsification test available without a drive.

READING IT
  * grinding STEPS DOWN at 35 km/h  =>  the damper helps grinding; V249's side effect is a benefit.
  * grinding STEPS UP at 35 km/h    =>  damping this lane makes grinding WORSE, and V249 carries a
                                        real cost that V241/V247 do not.
  * no step, only a smooth trend    =>  the corpus cannot answer it; V249's grinding effect stays an
                                        open question the drive settles.

\U0001f6d1 CONFOUNDS THAT SURVIVE.  Speed changes road input, tyre excitation and aero regardless of the
damper, so the SMOOTH component of any trend means nothing here -- only the discontinuity at the knee
does.  The estimator therefore fits a local linear trend on each side and reports the JUMP at the
boundary, not the level difference.

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

KNEE_KMH = 2240 / 64.0          # FactorC X[0]
HALFWIDTH = 12.0                # fit window on each side of the knee
BANDS = {'ratchet 6-9.5': (6.0, 9.5), 'grinding 22-30': (22.0, 30.0),
         'control 12-18': (12.0, 18.0)}
WIN_S = 2.0


def band_windows(path, band):
    z = np.load(path, allow_pickle=True)
    if not {'t', 'tq', 'cc_lat', 'cs_v'} <= set(z.files):
        return []
    t = np.asarray(z['t'], float)
    n = len(t)
    q = np.asarray(z['tq'], float)[:n]
    e = (np.asarray(z['cc_lat'], float) > 0.5)[:n]
    v = np.abs(np.asarray(z['cs_v'], float))[:n] * 3.6
    if len(q) < n or len(v) < n:
        return []
    fs = 1.0 / np.median(np.diff(t))
    lo, hi = band[0] / (fs / 2), band[1] / (fs / 2)
    if hi >= 1.0:
        return []
    b, a = signal.butter(3, [lo, hi], btype='band')
    env = np.abs(signal.hilbert(signal.filtfilt(b, a, q - q.mean())))
    tot = np.abs(signal.hilbert(q - q.mean())) + 1e-9
    w = int(WIN_S * fs)
    out = []
    for i in range(0, n - w, w):
        sl = slice(i, i + w)
        if e[sl].mean() < 0.98:
            continue
        sp = float(np.median(v[sl]))
        if not (KNEE_KMH - HALFWIDTH <= sp <= KNEE_KMH + HALFWIDTH):
            continue
        # band energy as a FRACTION of total, so route loudness divides out
        out.append((sp, float(np.mean(env[sl]) / np.mean(tot[sl]))))
    return out


def rd(rows):
    """Local linear fit each side; report the jump at the knee."""
    if len(rows) < 60:
        return None
    S = np.array([r[0] for r in rows])
    Y = np.array([r[1] for r in rows])
    lo, hi = S < KNEE_KMH, S >= KNEE_KMH
    if lo.sum() < 25 or hi.sum() < 25:
        return None
    fl = stats.linregress(S[lo], Y[lo])
    fh = stats.linregress(S[hi], Y[hi])
    left = fl.intercept + fl.slope * KNEE_KMH
    right = fh.intercept + fh.slope * KNEE_KMH
    # jump SE from the two fits' prediction SEs at the boundary
    def se(f, x):
        n = len(x)
        return f.stderr * np.sqrt(np.mean((x - x.mean()) ** 2) + (KNEE_KMH - x.mean()) ** 2) \
            if f.stderr > 0 else np.nan
    j = right - left
    s = np.sqrt(se(fl, S[lo]) ** 2 + se(fh, S[hi]) ** 2)
    z = j / s if s and np.isfinite(s) and s > 0 else np.nan
    return j, s, z, lo.sum(), hi.sum(), left, right


def main():
    print('=' * 88)
    print('  REGRESSION DISCONTINUITY AT THE DAMPER SWITCH-ON SPEED (%.0f km/h)' % KNEE_KMH)
    print('=' * 88)
    print('\n  the damper is EXACTLY ZERO below %.0f km/h and live above it, and nothing else in the'
          % KNEE_KMH)
    print('  firmware changes there. A STEP at the knee is the damper; a smooth trend is not.\n')
    files = []
    seen = set()
    for p in (sorted(glob.glob('_scratch/cache/*/*.npz')) +
              sorted(glob.glob('analysis-2020accord/_scratch/cache/*/*.npz'))):
        r = os.path.basename(p)[:-4]
        if r in seen or 's' in r[1:]:
            continue
        seen.add(r)
        files.append(p)
    print('  %-16s %8s %8s %10s %9s %9s %8s'
          % ('band', 'n below', 'n above', 'jump', 'SE', 'z', 'verdict'))
    print('  ' + '-' * 74)
    for name, band in BANDS.items():
        rows = []
        for p in files:
            try:
                rows += band_windows(p, band)
            except Exception:
                continue
        got = rd(rows)
        if got is None:
            print('  %-16s %8s %8s %10s' % (name, '--', '--', 'too few'))
            continue
        j, s, z, nl, nh, left, right = got
        if not np.isfinite(z):
            verdict = 'n/a'
        elif abs(z) < 2:
            verdict = 'no step'
        elif j < 0:
            verdict = 'DROPS'
        else:
            verdict = 'RISES'
        print('  %-16s %8d %8d %+10.5f %9.5f %9.2f %8s' % (name, nl, nh, j, s, z, verdict))
    print('  ' + '-' * 74)
    print('\n  READING')
    print('  grinding DROPS at the knee  => the damper HELPS grinding; V249 side effect is a benefit.')
    print('  grinding RISES at the knee  => damping this lane makes grinding WORSE; V249 carries a')
    print('                                 real cost that V241/V247 do not.')
    print('  no step                     => the corpus cannot answer it; the drive settles it.')
    print('\n  \U0001f6d1 the 12-18 Hz CONTROL band should show NO step. If it does, the estimator is')
    print('     picking up something about speed itself and none of the rows can be trusted.')


if __name__ == '__main__':
    main()
