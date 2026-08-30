#!/usr/bin/env python3
r"""DOES AN INDEPENDENT SENSOR SEE THE RATCHET?  Pooled across a route's segments, speed-matched.

The per-segment version was underpowered: speed matching left n=3 with ~30 s per arm, and a gyro
excess of 3.18 against a road control of 2.37 decides nothing.  The speed-matched exposure exists --
r66 alone carries 300 s engaged and 492 s manual -- it is just spread across a route's SEGMENTS while
the CAN cache is route-level.  This pools it.

WHAT IS FIXED HERE
  * PAIRING: per-segment IMU (`r66s0_imu.npz`) now falls back to the ROUTE-level CAN cache
    (`r66.npz`) when no per-segment one exists.  Both carry `t` on the same t0, which is the whole
    point of the extractor's time base.
  * POOLING: PSDs are averaged ACROSS segments per arm rather than each segment being scored alone,
    so a route's whole speed-matched exposure counts once.
  * The speed matching and the road control (vertical acceleration) are unchanged -- they are what
    showed the unmatched contrast was 20x broadband road difference.

READING IT
  * gyro excess >> 1 with the road control ~ 1  => the ratchet is REAL MOTION, confirmed off-EPS.
  * both ~ 1                                    => it does not reach the chassis; it is a
    torque-channel phenomenon and the "resonance" readings built on CAN magnitudes need re-reading.
  * both >> 1                                   => still road, and speed matching did not clear it.

WHAT THIS IS NOT.  The IMU sits on the windscreen, not the column, so a null bounds the MOTION, not
the torque.  ~101 Hz sampling carries the same >50 Hz fold as CAN; the test is held well below it.

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

import collections
import glob
import os
import re
import sys

import numpy as np
from scipy import signal, interpolate

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
F_LO, F_HI = 3.0, 25.0
F0_SEARCH = (6.5, 9.5)
SMOOTH_HZ = 6.0
SPD_BIN = 5.0
MIN_S = 30.0
NPERSEG = 512


def smooth_med(y, x, width):
    return np.array([np.median(y[np.abs(x - xi) <= width / 2]) for xi in x])


def can_for(imu_path):
    """per-segment CAN cache if it exists, else the ROUTE-level one (same t0)"""
    d = os.path.dirname(imu_path)
    seg = os.path.basename(imu_path).replace('_imu.npz', '')
    p = os.path.join(d, seg + '.npz')
    if os.path.exists(p):
        return p, seg
    m = re.match(r'^(r[0-9a-fx]+?)s?\d*$', seg)
    if m:
        p = os.path.join(d, m.group(1) + '.npz')
        if os.path.exists(p):
            return p, m.group(1)
    return None, seg


def arms(sig, t, engf, spd, fs):
    """return (engaged PSD list, manual PSD list, freqs) for the SPEED-MATCHED part"""
    em = engf > 0.5
    mm = ~em
    bins = np.floor(spd / SPD_BIN).astype(int)
    shared = np.intersect1d(np.unique(bins[em]), np.unique(bins[mm]))
    if len(shared) == 0:
        return None, None, None, 0.0, 0.0
    keep = np.isin(bins, shared)
    em, mm = em & keep, mm & keep
    out = []
    for m in (em, mm):
        if m.sum() < NPERSEG:
            out.append(None)
            continue
        f, P = signal.welch(sig[m] - sig[m].mean(), fs, nperseg=NPERSEG)
        out.append((f, P))
    if out[0] is None or out[1] is None:
        return None, None, None, 0.0, 0.0
    return out[0], out[1], out[0][0], em.sum() / fs, mm.sum() / fs


def main():
    imus = sorted(glob.glob(os.path.join(REPO, '_scratch', 'cache', '*', '*_imu.npz')))
    byroute = collections.defaultdict(list)
    for p in imus:
        m = re.match(r'^(r[0-9a-fx]+?)s?\d*$', os.path.basename(p).replace('_imu.npz', ''))
        if m:
            byroute[m.group(1)].append(p)

    print('=' * 96)
    print('  RATCHET IN THE IMU -- POOLED per route, SPEED-MATCHED, with a road control')
    print('=' * 96)
    print('  %-8s %5s %8s %8s %8s %9s %9s %9s' %
          ('route', 'segs', 'eng s', 'man s', 'f0 Hz', 'gyro exc', 'road ctl', 'ratio'))
    print('  ' + '-' * 76)

    rows = []
    for route, paths in sorted(byroute.items()):
        acc = {'g': [[], []], 'a': [[], []]}
        fg = fa = None
        te = tm = 0.0
        for p in paths:
            can, _ = can_for(p)
            if not can:
                continue
            try:
                zi = np.load(p, allow_pickle=True)
                zc = np.load(can, allow_pickle=True)
            except Exception:
                continue
            if not {'cc_lat', 'cs_v', 't'} <= set(zc.files):
                continue
            tc = np.asarray(zc['t'], float)
            eg = np.asarray(zc['cc_lat'], float)
            vv = np.abs(np.asarray(zc['cs_v'], float)) * 3.6
            n = min(len(tc), len(eg), len(vv))
            if n < 200:
                continue
            tc, eg, vv = tc[:n], eg[:n], vv[:n]
            for kind, tk, axes in (('g', 'gt', ('gz', 'gy')), ('a', 'at', ('az',))):
                if tk not in zi.files:
                    continue
                tt = np.asarray(zi[tk], float)
                if len(tt) < 4 * NPERSEG:
                    continue
                fs = 1.0 / np.median(np.diff(tt))
                ei = interpolate.interp1d(tc, eg, kind='nearest', bounds_error=False,
                                          fill_value=0.0)(tt)
                vi = interpolate.interp1d(tc, vv, kind='nearest', bounds_error=False,
                                          fill_value=0.0)(tt)
                ax = next((a for a in axes if a in zi.files), None)
                if ax is None:
                    continue
                e_, m_, f_, se, sm = arms(np.asarray(zi[ax], float), tt, ei, vi, fs)
                if e_ is None:
                    continue
                acc[kind][0].append(e_[1])
                acc[kind][1].append(m_[1])
                if kind == 'g':
                    fg = f_
                    te += se
                    tm += sm
                else:
                    fa = f_
        if not acc['g'][0] or not acc['g'][1] or fg is None:
            continue
        if te < MIN_S or tm < MIN_S:
            continue

        def local_excess(f, Pe, Pm):
            b = (f >= F_LO) & (f <= F_HI)
            fb = f[b]
            r = np.mean(Pe, axis=0)[b] / np.maximum(np.mean(Pm, axis=0)[b], 1e-30)
            ex = r / np.maximum(smooth_med(r, fb, SMOOTH_HZ), 1e-30)
            sw = (fb >= F0_SEARCH[0]) & (fb <= F0_SEARCH[1])
            return float(ex[sw].max()), float(fb[sw][np.argmax(ex[sw])])

        gexc, f0 = local_excess(fg, acc['g'][0], acc['g'][1])
        rctl = np.nan
        if acc['a'][0] and acc['a'][1] and fa is not None:
            rctl, _ = local_excess(fa, acc['a'][0], acc['a'][1])
        rows.append((route, len(paths), te, tm, f0, gexc, rctl,
                     gexc / rctl if rctl and np.isfinite(rctl) else np.nan))

    if not rows:
        print('  no route pooled enough speed-matched exposure.')
        print('  \U0001f6d1 EMPTY INPUT, not a null result.')
        return
    for r in sorted(rows, key=lambda x: -(x[2] + x[3])):
        print('  %-8s %5d %8.1f %8.1f %8.2f %9.3f %9.3f %9.3f' % r)
    A = np.array([[r[5], r[6], r[7]] for r in rows], float)
    med = np.nanmedian(A, axis=0)
    print('  ' + '-' * 76)
    print('  %-8s %5s %8s %8s %8s %9.3f %9.3f %9.3f' % ('MEDIAN', '', '', '', '', *med))
    print()
    print('  READING IT:')
    print('   * gyro excess clearly above the road control => the ratchet is REAL MOTION,')
    print('     confirmed off-EPS for the first time in this kit.')
    print('   * gyro ~ road control                        => the contrast is still conditions.')
    print('   * both ~ 1                                   => it does not reach the chassis at all.')
    print()
    print('  \U0001f6d1 the IMU is on the WINDSCREEN, not the column: a null bounds the MOTION, not the')
    print('     torque. Sampling ~101 Hz carries the same >50 Hz fold as CAN.')


if __name__ == '__main__':
    main()
