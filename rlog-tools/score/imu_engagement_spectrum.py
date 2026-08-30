#!/usr/bin/env python3
r"""WHERE DOES ENGAGEMENT ACTUALLY ADD MOTION?  The full band profile, off-EPS.

The kit has scored three named bands for a long time -- ratchet, grind, pumping -- all chosen from CAN
measurements of the EPS's own channels.  The IMU is independent of the EPS and has now been validated
as a scorer: it ranked V88, the kit's one measured grinding fix, near-best for grinding and near-worst
for ratchet, which was the pre-registered prediction.

So ask it the open question rather than the named one: **at which frequencies does engagement raise
chassis motion above what the road explains?**  That tests V235's notch placement (25.0 Hz) directly,
and it can find bands nobody has named.

METHOD
  * per route, pool the segments' gyro PSDs into engaged and manual arms, SPEED-MATCHED
  * divide, and divide again by the same quantity computed on VERTICAL ACCELERATION -- the road
    control -- so a route driven on rougher tarmac cannot read as engagement
  * report the median across routes at every frequency, and where it exceeds 1

READING IT
  * a peak at 6.5-9.5 Hz          => the ratchet, already confirmed.
  * excess at 22-30 Hz            => V235's notch is aimed at real engagement-created motion.
  * no excess at 22-30 Hz         => the notch is aimed at a band the chassis does not show, and the
    CAN evidence placing it there needs re-reading.
  * an unnamed band above 1       => a target nobody has looked at.

WHAT THIS IS NOT.  The IMU is on the windscreen, not the column: it bounds MOTION, not torque, and the
lane the notch actually filters is a torque lane.  A band that is quiet here may still matter in
torque.  ~101 Hz sampling folds anything above ~50 Hz, so nothing above 45 Hz is reported.

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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ratchet_in_the_imu_pooled import can_for, SPD_BIN, NPERSEG      # noqa: E402

F_LO, F_HI = 3.0, 45.0          # 45 keeps clear of the ~50 Hz fold
MIN_S = 30.0
NAMED = [('ratchet', 6.5, 9.5), ('mid', 9.5, 15.0), ('grind', 15.0, 22.0),
         ('V235 notch', 22.0, 30.0), ('upper', 30.0, 45.0)]


def arms_psd(sig, engf, spd, fs):
    em, mm = engf > 0.5, engf <= 0.5
    bins = np.floor(spd / SPD_BIN).astype(int)
    shared = np.intersect1d(np.unique(bins[em]), np.unique(bins[mm]))
    if len(shared) == 0:
        return None
    keep = np.isin(bins, shared)
    em, mm = em & keep, mm & keep
    if em.sum() < NPERSEG or mm.sum() < NPERSEG:
        return None
    f, Pe = signal.welch(sig[em] - sig[em].mean(), fs, nperseg=NPERSEG)
    _, Pm = signal.welch(sig[mm] - sig[mm].mean(), fs, nperseg=NPERSEG)
    return f, Pe, Pm, em.sum() / fs, mm.sum() / fs


def main():
    imus = sorted(glob.glob(os.path.join(REPO, '_scratch', 'cache', '*', '*_imu.npz')))
    byroute = collections.defaultdict(list)
    for p in imus:
        m = re.match(r'^(r[0-9a-fx]+?)s?\d*$', os.path.basename(p).replace('_imu.npz', ''))
        if m:
            byroute[m.group(1)].append(p)

    curves = []
    for route, paths in sorted(byroute.items()):
        acc = {'g': [[], []], 'a': [[], []]}
        te = tm = 0.0
        fg = fa = None
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
                r = arms_psd(np.asarray(zi[ax], float), ei, vi, fs)
                if r is None:
                    continue
                f, Pe, Pm, se, sm = r
                acc[kind][0].append(Pe)
                acc[kind][1].append(Pm)
                if kind == 'g':
                    fg = f
                    te += se
                    tm += sm
                else:
                    fa = f
        if not acc['g'][0] or not acc['a'][0] or fg is None or fa is None:
            continue
        if te < MIN_S or tm < MIN_S:
            continue
        b = (fg >= F_LO) & (fg <= F_HI)
        gy = np.mean(acc['g'][0], axis=0)[b] / np.maximum(np.mean(acc['g'][1], axis=0)[b], 1e-30)
        rd = np.mean(acc['a'][0], axis=0)[b] / np.maximum(np.mean(acc['a'][1], axis=0)[b], 1e-30)
        # 🛑 routes differ slightly in IMU sample rate, so their Welch grids differ by a bin.
        # Interpolate every curve onto ONE grid rather than assuming they align.
        curves.append((fg[b], gy / np.maximum(rd, 1e-30)))

    print('=' * 92)
    print('  WHERE DOES ENGAGEMENT ADD MOTION?   IMU gyro / road control, speed-matched, %d routes'
          % len(curves))
    print('=' * 92)
    if not curves:
        print('  no route pooled enough speed-matched exposure.')
        print('  \U0001f6d1 EMPTY INPUT, not a null result.')
        return
    fref = np.arange(F_LO, F_HI, 0.25)
    A = np.vstack([np.interp(fref, f, c) for f, c in curves])
    med = np.median(A, axis=0)
    frac = (A > 1.0).mean(axis=0)

    print('  %-12s %8s %9s %9s %10s' % ('band', 'Hz', 'median', 'p25..p75', 'routes>1'))
    print('  ' + '-' * 60)
    for name, lo, hi in NAMED:
        m = (fref >= lo) & (fref < hi)
        if not m.any():
            continue
        q = np.percentile(A[:, m].mean(axis=1), [25, 75])
        print('  %-12s %5.0f-%-3.0f %9.3f  %4.2f..%-4.2f %9.0f %%'
              % (name, lo, hi, np.median(A[:, m].mean(axis=1)), q[0], q[1],
                 100 * frac[m].mean()))
    print('  ' + '-' * 60)
    print()
    print('  per-bin profile (median across routes), 3-45 Hz:')
    step = max(1, len(fref) // 40)
    for i in range(0, len(fref), step):
        j = min(i + step, len(fref))
        v = float(np.median(med[i:j]))
        bar = '#' * min(44, int(round(v * 14)))
        print('   %5.1f Hz %6.3f %s' % (fref[i], v, bar))
    print('   %s' % ('(a bar of 14 blocks is a ratio of 1.0)'))
    print()
    print('  \U0001f6d1 the IMU bounds MOTION, not torque, and the notch filters a TORQUE lane.')
    print('     A band quiet here may still matter in torque. Nothing above 45 Hz is reported')
    print('     because ~101 Hz sampling folds it.')


if __name__ == '__main__':
    main()
