#!/usr/bin/env python3
r"""DOES THE TORQUE CHANNEL NAME THE SAME BAND AS THE CHASSIS?

V241's notch geometry was optimised against the IMU's engagement-excess profile.  That profile is
CHASSIS MOTION, and the notch filters a TORQUE lane -- the one assumption in the chain that has not
been checked.  If the torque channel's own engagement excess peaks somewhere else, the geometry is
aimed by the wrong spectrum.

METHOD -- the same local-excess design, on `tq` from CAN instead of the gyro:
  * per route, engaged vs manual power, SPEED-MATCHED
  * divided by a smooth broadband baseline, so "engaged is noisier" cannot masquerade as a band
  * compared against the IMU profile computed identically

WHY NOT JUST USE TORQUE FOR THE OBJECTIVE.  Because `tq` rides the ~101 Hz CAN frame, so 22-30 Hz is
contaminated by anything real at 71-79 Hz.  The audio bound says real 20-32 Hz energy beats its fold
source ~2.3x, so the band is genuinely there -- but roughly 30 % of the CAN band power is folded.  The
IMU carries the same fold; the AUDIO does not, which is why it was used to settle that question.  This
test therefore asks for AGREEMENT ON SHAPE, not for a better objective.

READING IT
  * both peak in 22-30 Hz            => the notch is aimed by a spectrum that matches the lane it
    filters, and the last gap in V241's chain is closed.
  * torque peaks elsewhere           => the geometry is aimed by chassis motion that the torque lane
    does not share, and the objective needs rebuilding on `tq`.

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

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import notch_vs_imu_profile as N                                      # noqa: E402

F_LO, F_HI = 3.0, 45.0
SPD_BIN = 5.0
MIN_S = 30.0
NPERSEG = 512
SMOOTH_HZ = 6.0
BANDS = [('ratchet', 6.0, 10.0), ('mid', 10.0, 15.0), ('grind', 15.0, 22.0),
         ('V241 band', 22.0, 30.0), ('upper', 30.0, 45.0)]


def smooth_med(y, x, width):
    return np.array([np.median(y[np.abs(x - xi) <= width / 2]) for xi in x])


def torque_curves():
    out = []
    for c in sorted(glob.glob(os.path.join(REPO, '_scratch', 'cache', '*', '*.npz'))):
        b = os.path.basename(c)
        if b.endswith('_imu.npz') or '_' in b.replace('.npz', ''):
            continue
        try:
            z = np.load(c, allow_pickle=True)
        except Exception:
            continue
        if not {'tq', 'cc_lat', 'cs_v', 't'} <= set(z.files):
            continue
        t = np.asarray(z['t'], float)
        eg = np.asarray(z['cc_lat'], float) > 0.5
        tq = np.asarray(z['tq'], float)
        vv = np.abs(np.asarray(z['cs_v'], float)) * 3.6
        n = min(len(t), len(eg), len(tq), len(vv))
        if n < 4 * NPERSEG:
            continue
        t, eg, tq, vv = t[:n], eg[:n], tq[:n], vv[:n]
        fs = 1.0 / np.median(np.diff(t))
        bins = np.floor(vv / SPD_BIN).astype(int)
        shared = np.intersect1d(np.unique(bins[eg]), np.unique(bins[~eg]))
        if len(shared) == 0:
            continue
        keep = np.isin(bins, shared)
        em, mm = eg & keep, (~eg) & keep
        if em.sum() / fs < MIN_S or mm.sum() / fs < MIN_S:
            continue
        f, Pe = signal.welch(tq[em] - tq[em].mean(), fs, nperseg=NPERSEG)
        _, Pm = signal.welch(tq[mm] - tq[mm].mean(), fs, nperseg=NPERSEG)
        m = (f >= F_LO) & (f <= F_HI)
        r = Pe[m] / np.maximum(Pm[m], 1e-30)
        out.append((f[m], r / np.maximum(smooth_med(r, f[m], SMOOTH_HZ), 1e-30)))
        if len(out) >= 24:
            break
    return out


def main():
    wf = np.arange(F_LO, F_HI, 0.25)
    tq = torque_curves()
    im = N.SP_curves()
    print('=' * 92)
    print('  DOES TORQUE NAME THE SAME BAND AS THE CHASSIS?   %d torque routes, %d IMU routes'
          % (len(tq), len(im)))
    print('=' * 92)
    if not tq or not im:
        print('  \U0001f6d1 EMPTY INPUT on one side, not a null result.')
        return
    T = np.vstack([np.interp(wf, f, c) for f, c in tq])
    I = np.vstack([np.interp(wf, f, c) for f, c in im])
    tm, imd = np.median(T, axis=0), np.median(I, axis=0)

    print('  %-12s %8s %11s %11s' % ('band', 'Hz', 'TORQUE', 'IMU'))
    print('  ' + '-' * 46)
    for name, lo, hi in BANDS:
        m = (wf >= lo) & (wf < hi)
        print('  %-12s %4.0f-%-3.0f %11.3f %11.3f'
              % (name, lo, hi, np.median(T[:, m].mean(axis=1)), np.median(I[:, m].mean(axis=1))))
    print('  ' + '-' * 46)

    bt = BANDS[int(np.argmax([np.median(T[:, (wf >= lo) & (wf < hi)].mean(axis=1))
                              for _, lo, hi in BANDS]))]
    bi = BANDS[int(np.argmax([np.median(I[:, (wf >= lo) & (wf < hi)].mean(axis=1))
                              for _, lo, hi in BANDS]))]
    print('  TORQUE peaks in: %-12s   IMU peaks in: %s' % (bt[0], bi[0]))
    rho = stats.spearmanr(tm, imd)
    print('  profile agreement across 3-45 Hz: spearman rho=%+.3f p=%.4g' % (rho[0], rho[1]))
    print()
    if bt[0] == bi[0]:
        print('  ✅ SAME BAND. The notch is aimed by a spectrum that matches the lane it filters,')
        print('     and the last untested link in V241\'s chain is closed.')
    else:
        print('  \U0001f6d1 DIFFERENT BANDS. The geometry is aimed by chassis motion the torque lane does')
        print('     not share -- the objective needs rebuilding on tq.')
    print()
    print('  \U0001f6d1 `tq` rides the ~101 Hz CAN frame, so its 22-30 Hz carries ~30 %% folded from')
    print('     71-79 Hz (the audio bound says real energy beats the fold ~2.3x). This asks for')
    print('     AGREEMENT ON SHAPE; it is not a better objective than the IMU.')


if __name__ == '__main__':
    main()
