#!/usr/bin/env python3
r"""🛑 SUPERSEDED -- THIS FILE PRICES THE DAMPER BY MAGNITUDE, WHICH IS THE WRONG QUANTITY.

The 89.5 % / "Re(Z) -> -6.8" figures below are WRONG BY ~20x.  For a small oscillation riding on a
larger steady rate, the damping coefficient is the curve's SLOPE, not its value:
    T = -sign(rate)*M(|rate|),  rate = R0 + d*sin,  R0 >> d   =>   oscillating part = -M'(R0)*d
and the regime IS the slope regime -- measured, the rate sign reverses in only 9.4 % of engaged
windows (6-9 Hz amplitude p50 0.72 deg/s against a slow rate of 1.65).

CORRECT figures, counts per deg/s against a requirement of 65:
    V122 0.813 = 1.3 %   V249 2.742 = 4.2 %   V250 5.485 = 8.4 %   lane ceiling 18.866 = 29.0 %
THE DAMPER CANNOT CANCEL THE RATCHET.  Corrected prediction: Re(Z) -64.8 -> about -62.
See [[accord-damper-sizing-was-magnitude-not-slope]].  Original text follows, kept for the method.

ORIGINAL: what should V249 do to Re(Z)? A pre-registered prediction.

WHY THIS EXISTS.  The kit's design law: "before cutting, write the sentence a null will license."
V249 is about to be flown against a symptom that sixty builds have failed to move, so the value of the
drive depends entirely on having said in advance what counts as success and what counts as failure.
Without that, a null becomes "uninterpretable" -- which the record calls a DESIGN FAILURE on our side,
not a verdict.

THE PREDICTION.  V249 adds damper torque `T_d = -sign(rate) * M(|rate|)`, where M is computed by the
decompiled mirror from the build's own tables.  Damping torque OPPOSES rate, so it adds a NEGATIVE
real part to the driver-side impedance seen at the column... but with the OPPOSITE sign convention to
Re(Z) as measured here, because Re(Z) = Re(tq/rate) is measured on the DRIVER's torque, and the motor's
damping torque reduces the motion the driver has to fight.

So: more damper => the 6-9 Hz motion is more opposed => Re(Z) moves TOWARD ZERO (less negative).

    Re(Z)_predicted = Re(Z)_measured * (1 - T_d / T_total)

where T_d is the damper's contribution at the ratchet operating point and T_total is the torque scale
the impedance is normalised against.  This is a first-order estimate and is stated as such.

WHAT THE DRIVE SETTLES
  * Re(Z) moves toward zero by roughly the predicted amount  =>  the mechanism is right and the dose
    is calibrated. V250 becomes the margin step if more is wanted.
  * Re(Z) unchanged                                          =>  the damper does not reach the loop
    the ratchet lives in. That RULES OUT the damper lane by experiment -- which sixty builds of
    inference never managed -- and the next candidate is the aggregator hop that is still [OPEN].
  * Re(Z) more negative                                      =>  the sign argument is inverted
    somewhere, and V249 must be reverted immediately.

\U0001f6d1 THIS IS A FIRST-ORDER PREDICTION, NOT A SIMULATION.  It assumes the damper's torque enters
the same summing junction the impedance is measured across, and that the plant is linear over the
increment.  Both are the standard small-signal assumptions used throughout this arc.  The magnitude
should be read as an order, and the SIGN and the ROUGH SIZE are what the drive tests.

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
from scipy import signal

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, 'analysis-2020accord', 'model'))
from damper_fun34350_mirror import damper, MODE_ENGAGED   # noqa: E402

FW = os.environ.get('ACCORD_FIRMWARE_ROOT', r'C:\Users\dudei\Desktop\Projects\accord-firmwares')
IMGDIR = os.path.join(FW, 'analysis-2020accord')
BAND = (6.0, 9.5)
MIN_COH = 0.60
WIN_S = 2.0
CAR_REZ = -64.77          # corpus median, coherence-gated


def image(tag):
    p = [q for q in glob.glob(os.path.join(IMGDIR, '_%s_*_plain_image.bin' % tag))
         if 'DO-NOT-FLASH' not in os.path.basename(q)]
    return open(p[0], 'rb').read() if p else None


def route_stats(path):
    """Per-window (band torque amplitude, band rate amplitude, speed, motor-rate proxy)."""
    z = np.load(path, allow_pickle=True)
    if not {'t', 'tq', 'cs_rate', 'cc_lat', 'cs_v'} <= set(z.files):
        return []
    t = np.asarray(z['t'], float)
    n = len(t)
    q = np.asarray(z['tq'], float)[:n]
    r = np.asarray(z['cs_rate'], float)[:n]
    e = (np.asarray(z['cc_lat'], float) > 0.5)[:n]
    v = np.abs(np.asarray(z['cs_v'], float))[:n] * 3.6
    if len(q) < n or len(r) < n or len(v) < n:
        return []
    fs = 1.0 / np.median(np.diff(t))
    lo, hi = BAND[0] / (fs / 2), BAND[1] / (fs / 2)
    if hi >= 1.0:
        return []
    b, a = signal.butter(3, [lo, hi], btype='band')
    qa = np.abs(signal.hilbert(signal.filtfilt(b, a, q - q.mean())))
    ra = np.abs(signal.hilbert(signal.filtfilt(b, a, r - r.mean())))
    w = int(WIN_S * fs)
    out = []
    for i in range(0, n - w, w):
        sl = slice(i, i + w)
        if e[sl].mean() < 0.98:
            continue
        out.append((float(np.mean(qa[sl])), float(np.mean(ra[sl])), float(np.median(v[sl]))))
    return out


def main():
    print('=' * 86)
    print('  PRE-REGISTERED PREDICTION FOR V249  -- written BEFORE the drive, to make a null readable')
    print('=' * 86)
    car, v249 = image('v122'), image('v249')
    if car is None or v249 is None:
        print('  images missing.')
        return

    rows = []
    seen = set()
    for p in (sorted(glob.glob(os.path.join(REPO, '_scratch', 'cache', '*', '*.npz'))) +
              sorted(glob.glob(os.path.join(REPO, 'analysis-2020accord', '_scratch', 'cache',
                                            '*', '*.npz')))):
        r = os.path.basename(p)[:-4]
        if r in seen or 's' in r[1:]:
            continue
        seen.add(r)
        try:
            rows += route_stats(p)
        except Exception:
            continue
    if len(rows) < 200:
        print('  too few windows.')
        return
    tq_amp = float(np.median([x[0] for x in rows]))
    speeds = np.array([x[2] for x in rows])
    print('\n  measured, %d engaged windows:' % len(rows))
    print('     6-9.5 Hz torque amplitude   p50 %.0f counts' % tq_amp)
    print('     speed distribution          %.0f %% below the FactorC knee (35 km/h)'
          % (100 * (speeds < 35).mean()))

    # damper delivered at the ratchet operating point, weighted by the real speed distribution
    print('\n  damper at the ratchet operating point (rate 99), weighted by that speed mix:')
    tot = {}
    for tag, img in (('V122 (car)', car), ('V249', v249)):
        vals = [damper(img, MODE_ENGAGED, int(max(s, 1) * 64), 99)[0] for s in speeds]
        tot[tag] = float(np.mean(vals))
        print('     %-11s mean %6.1f counts   (median %5.1f)' % (tag, tot[tag], float(np.median(vals))))
    delta = tot['V249'] - tot['V122 (car)']
    frac = delta / max(tq_amp, 1e-9)
    print('\n  V249 adds %.1f counts of damping against a %.0f-count band torque = %.1f %%'
          % (delta, tq_amp, 100 * frac))

    pred = CAR_REZ * (1 - frac)
    print('\n  ' + '=' * 76)
    print('  THE PREDICTION, ON THE RECORD BEFORE THE DRIVE:')
    print('     Re(Z) at 6-9 Hz should move from  %.1f  toward zero, to roughly  %.1f'
          % (CAR_REZ, pred))
    print('     i.e. an improvement of about %.0f %%.' % (100 * frac))
    print('  ' + '=' * 76)
    print('\n  WHAT EACH OUTCOME LICENSES')
    print('     moves toward zero by roughly this  => mechanism right, dose calibrated.')
    print('                                           V250 is the margin step if more is wanted.')
    print('     unchanged                          => the damper does NOT reach the loop the ratchet')
    print('                                           lives in. RULES OUT the damper lane by')
    print('                                           experiment, which inference never could.')
    print('     more negative                      => the sign argument is inverted somewhere.')
    print('                                           REVERT V249 immediately.')
    print('\n  \U0001f6d1 FIRST-ORDER, not a simulation: it assumes the damper torque enters the same')
    print('     summing junction the impedance is measured across and that the plant is linear over')
    print('     the increment. Read the SIGN and the ORDER, not the decimal.')


if __name__ == '__main__':
    main()
