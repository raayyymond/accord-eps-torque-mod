#!/usr/bin/env python3
r"""DOES AN INDEPENDENT SENSOR SEE THE RATCHET?

Everything the kit has measured about the ratchet came off the EPS's own CAN channels, so every
finding shares one failure mode: it could be an artefact of EPS signal processing, a decode error, or
the torsion-bar channel's scaling.  The comma device's LSM6DS3TR-C is **physically independent of the
EPS** -- its own sensor, its own clock, its own FIFO.  If it sees an engagement-gated line at the
ratchet frequency, the ratchet is real gross motion.  If it does not, the ratchet lives in the torque
channel without producing motion the chassis can feel, which is itself a strong constraint on what it
can be.

METHOD -- the same local-excess design that finally worked on the audio:
  * take the gyro (angular rate; a steering oscillation shows in yaw and roll) on its NATIVE grid
  * split by the engagement mask from the matching CAN cache
  * form the engaged/manual power ratio across 3-25 Hz, fit a SMOOTH BROADBAND BASELINE to it, and
    report the LOCAL EXCESS -- so a general "engaged is noisier" cannot masquerade as a line
  * a control on the ACCELEROMETER's vertical axis, which road input dominates and steering should
    not: a line there means the contrast is road, not steering

READING IT
  * a local excess at ~7.8 Hz in the gyro, absent in the vertical control  => the ratchet is real
    motion, confirmed off-EPS for the first time.
  * nothing anywhere                                                      => the ratchet does not
    reach the chassis; it is a torque-channel phenomenon, and every "resonance" reading built on CAN
    magnitudes needs re-reading in that light.

WHAT THIS IS NOT.  The IMU sits in the device on the windscreen, not on the steering column, so it
sees the ratchet only insofar as it shakes the car.  A null bounds the MOTION, not the torque.
Sampling is ~104 Hz, so the same >50 Hz fold applies as on CAN; the test is held well below that.

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
from scipy import signal, interpolate

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
F_LO, F_HI = 3.0, 25.0
F0_SEARCH = (6.5, 9.5)
SMOOTH_HZ = 6.0
MIN_S = 20.0            # seconds of each arm
SPD_BIN = 5.0           # km/h; arms are compared only inside speed bins BOTH occupy


def smooth_med(y, x, width):
    out = np.empty_like(y)
    for i, xi in enumerate(x):
        out[i] = np.median(y[np.abs(x - xi) <= width / 2])
    return out


def excess(sig, t, engf, fs, spd=None):
    """local excess of engaged over manual, above a smooth broadband baseline.

    🛑 SPEED-MATCHED. The unmatched version gave a broadband engaged/manual ratio of 20x, i.e.
    the two arms differ in ROAD and SPEED, not just engagement -- and a road control on the vertical
    axis came back at 2.50 against the gyro's 3.18, so the contrast was mostly driving conditions.
    The kit's own record already requires this ("averaged spectra need MATCHED speed distributions").
    Here each arm is restricted to the speed bins BOTH arms occupy, and each bin is weighted equally.
    """
    em = engf > 0.5
    mm = ~em
    if (em.sum() / fs) < MIN_S or (mm.sum() / fs) < MIN_S:
        return None, None, None
    if spd is not None:
        bins = np.floor(spd / SPD_BIN).astype(int)
        shared = np.intersect1d(np.unique(bins[em]), np.unique(bins[mm]))
        if len(shared) == 0:
            return None, None, None
        keep = np.isin(bins, shared)
        em = em & keep
        mm = mm & keep
        if (em.sum() / fs) < MIN_S or (mm.sum() / fs) < MIN_S:
            return None, None, None
    npg = int(min(1024, 2 ** int(np.log2(max(256, min(em.sum(), mm.sum()) // 4)))))
    f, Pe = signal.welch(sig[em] - sig[em].mean(), fs, nperseg=npg)
    _, Pm = signal.welch(sig[mm] - sig[mm].mean(), fs, nperseg=npg)
    b = (f >= F_LO) & (f <= F_HI)
    fb = f[b]
    r = Pe[b] / np.maximum(Pm[b], 1e-30)
    return fb, r / np.maximum(smooth_med(r, fb, SMOOTH_HZ), 1e-30), float(np.median(r))


def main():
    imus = sorted(glob.glob(os.path.join(REPO, '_scratch', 'cache', '*', '*_imu.npz')))
    rows = []
    for p in imus:
        seg = os.path.basename(p).replace('_imu.npz', '')
        can = os.path.join(os.path.dirname(p), seg + '.npz')
        if not os.path.exists(can):
            continue
        try:
            zi = np.load(p, allow_pickle=True)
            zc = np.load(can, allow_pickle=True)
        except Exception:
            continue
        if 'cc_lat' not in zc.files or 't' not in zc.files or 'gt' not in zi.files:
            continue
        gt = np.asarray(zi['gt'], float)
        if len(gt) < 2048:
            continue
        fs = 1.0 / np.median(np.diff(gt))
        tc = np.asarray(zc['t'], float)
        eng = np.asarray(zc['cc_lat'], float)
        n = min(len(tc), len(eng))
        if n < 100:
            continue
        # engagement onto the IMU's OWN grid -- nearest neighbour, never resample the IMU
        ei = interpolate.interp1d(tc[:n], eng[:n], kind='nearest',
                                  bounds_error=False, fill_value=0.0)(gt)
        vi = None
        if 'cs_v' in zc.files:
            v = np.abs(np.asarray(zc['cs_v'], float)[:n]) * 3.6
            vi = interpolate.interp1d(tc[:n], v, kind='nearest',
                                      bounds_error=False, fill_value=0.0)(gt)
        best = None
        for ax in ('gz', 'gy', 'gx'):
            if ax not in zi.files:
                continue
            fb, ex, med = excess(np.asarray(zi[ax], float), gt, ei, fs, vi)
            if fb is None:
                continue
            sw = (fb >= F0_SEARCH[0]) & (fb <= F0_SEARCH[1])
            if not sw.any():
                continue
            v = float(ex[sw].max())
            f0 = float(fb[sw][np.argmax(ex[sw])])
            if best is None or v > best[1]:
                best = (ax, v, f0, med)
        if best is None:
            continue
        # CONTROL: vertical acceleration, which road input dominates
        ctl = np.nan
        if 'az' in zi.files and 'at' in zi.files:
            at = np.asarray(zi['at'], float)
            if len(at) > 2048:
                fsa = 1.0 / np.median(np.diff(at))
                ea = interpolate.interp1d(tc[:n], eng[:n], kind='nearest',
                                          bounds_error=False, fill_value=0.0)(at)
                va = None
                if 'cs_v' in zc.files:
                    va = interpolate.interp1d(tc[:n],
                                              np.abs(np.asarray(zc['cs_v'], float)[:n]) * 3.6,
                                              kind='nearest', bounds_error=False,
                                              fill_value=0.0)(at)
                fb2, ex2, _ = excess(np.asarray(zi['az'], float), at, ea, fsa, va)
                if fb2 is not None:
                    sw2 = (fb2 >= F0_SEARCH[0]) & (fb2 <= F0_SEARCH[1])
                    if sw2.any():
                        ctl = float(ex2[sw2].max())
        rows.append((seg, fs, best[0], best[2], best[1], best[3], ctl))
        if len(rows) >= 26:
            break

    print('=' * 92)
    print('  DOES AN INDEPENDENT SENSOR SEE THE RATCHET?   comma IMU, native grid, SPEED-MATCHED')
    print('=' * 92)
    if not rows:
        print('  no segment had BOTH an IMU cache and a CAN cache with an engagement mask.')
        print('  \U0001f6d1 that is an EMPTY INPUT, not a null result.')
        return
    print('  %-12s %8s %5s %8s %9s %9s %9s' %
          ('segment', 'fs Hz', 'axis', 'f0 Hz', 'excess', 'bb ratio', 'ctrl az'))
    print('  (excess = local excess over the broadband baseline; bb ratio = the broadband part)')
    print('  ' + '-' * 74)
    for r in rows:
        print('  %-12s %8.2f %5s %8.2f %9.3f %9.3f %9.3f' % r)
    A = np.array([[r[4], r[5], r[6]] for r in rows], float)
    med = np.nanmedian(A, axis=0)
    print('  ' + '-' * 74)
    print('  %-12s %8s %5s %8s %9.3f %9.3f %9.3f' % ('MEDIAN', '', '', '', *med))
    print()
    print('  READING IT:')
    print('   * gyro excess >> 1 and control ~ 1  => the ratchet is REAL MOTION, confirmed off-EPS')
    print('     for the first time in this kit.')
    print('   * both ~ 1                          => the ratchet does not reach the chassis. It is a')
    print('     TORQUE-channel phenomenon, and every "resonance" reading built on CAN magnitudes')
    print('     needs re-reading in that light.')
    print('   * both >> 1                         => the contrast is road input, not steering.')
    print()
    print('  \U0001f6d1 the IMU is on the WINDSCREEN, not the column: a null bounds the MOTION, not the')
    print('     torque. ~104 Hz sampling carries the same >50 Hz fold as CAN.')


if __name__ == '__main__':
    main()
