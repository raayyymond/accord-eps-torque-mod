#!/usr/bin/env python3
r"""DOES THE ENGAGEMENT BAND MOVE WITH THE LKAS GAIN?

V241's notch was optimised against the IMU engagement-excess profile -- and **every route in that
profile is a 4x build** (r5e V75 through r73 V88, all pre-V100).  The operator's recommended build,
V242, runs at **8x**.

That gap matters because the record already measured the band MOVING with gain: V101 (8x) put the peak
at **23.0 Hz** against **20.3 Hz** on three separate 4x routes -- "a POLE MOVED" -- with a
de-confounded gain of 2.7-3.9x at 22-26 Hz.  If the engagement band sits higher at 8x, a notch aimed on
4x data is aimed low.

METHOD -- the same speed-matched, road-controlled local-excess profile as
`imu_engagement_spectrum.py`, but grouped by the GAIN the build was running:

    4x   r5e r61 r65 r66 r67 r68 r6d r6e r6f r70 r71 r73 r75 r76   (V74-V89)
    6x   r96 r9e ra4 ra5 ra6                                        (V102-V106)
    8x   r95                                                        (V101)

READING IT
  * the 6x/8x peak sits where the 4x peak does  => V241's geometry transfers, and V242 is aimed right.
  * the peak moves UP with gain                 => the notch is aimed low for 8x, and either the
    geometry should be re-cut for the gain it will run at, or V241 (6x) is the better first drive.

WHAT THIS IS NOT.  One route at 8x, so the 8x arm is a single point and build/route are confounded.
This can show a shift worth acting on; it cannot attribute it to the gain alone.

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
from scipy import interpolate

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imu_engagement_spectrum as SP                                  # noqa: E402

GAIN = {}
for r in ('r5e', 'r61', 'r65', 'r66', 'r66x', 'r67', 'r67x', 'r68', 'r68x', 'r6d', 'r6e',
          'r6f', 'r70', 'r71', 'r73', 'r75', 'r76', 'r31', 'r37', 'r3a', 'r3b', 'r5d'):
    GAIN[r] = 4
for r in ('r96', 'r9e', 'ra4', 'ra5', 'ra6'):
    GAIN[r] = 6
GAIN['r95'] = 8
BANDS = [('ratchet', 6, 10), ('mid', 10, 15), ('grind', 15, 22),
         ('V241 notch', 22, 30), ('upper', 30, 45)]
WF = np.arange(3.0, 45.0, 0.25)


def curves_by_route():
    # caches live under BOTH kit roots -- the 6x/8x routes are under analysis-2020accord/
    imus = sorted(glob.glob(os.path.join(SP.REPO, '_scratch', 'cache', '*', '*_imu.npz')) +
                  glob.glob(os.path.join(SP.REPO, 'analysis-2020accord', '_scratch', 'cache',
                                         '*', '*_imu.npz')))
    byroute = collections.defaultdict(list)
    for p in imus:
        m = re.match(r'^(r[0-9a-fx]+?)s?\d*$', os.path.basename(p).replace('_imu.npz', ''))
        if m:
            byroute[m.group(1)].append(p)
    out = {}
    for route, paths in sorted(byroute.items()):
        acc = {'g': [[], []], 'a': [[], []]}
        te = tm = 0.0
        fg = fa = None
        for p in paths:
            can, _ = SP.can_for(p) if hasattr(SP, 'can_for') else (None, None)
            if not can:
                from ratchet_in_the_imu_pooled import can_for
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
                if len(tt) < 4 * SP.NPERSEG:
                    continue
                fs = 1.0 / np.median(np.diff(tt))
                ei = interpolate.interp1d(tc, eg, kind='nearest', bounds_error=False,
                                          fill_value=0.0)(tt)
                vi = interpolate.interp1d(tc, vv, kind='nearest', bounds_error=False,
                                          fill_value=0.0)(tt)
                ax = next((a for a in axes if a in zi.files), None)
                if ax is None:
                    continue
                r = SP.arms_psd(np.asarray(zi[ax], float), ei, vi, fs)
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
        if te < SP.MIN_S or tm < SP.MIN_S:
            continue
        b = (fg >= 3.0) & (fg <= 45.0)
        gy = np.mean(acc['g'][0], axis=0)[b] / np.maximum(np.mean(acc['g'][1], axis=0)[b], 1e-30)
        rd = np.mean(acc['a'][0], axis=0)[b] / np.maximum(np.mean(acc['a'][1], axis=0)[b], 1e-30)
        out[route] = np.interp(WF, fg[b], gy / np.maximum(rd, 1e-30))
    return out


def main():
    cur = curves_by_route()
    groups = collections.defaultdict(list)
    unknown = []
    for route, c in cur.items():
        g = GAIN.get(route)
        (groups[g] if g else unknown).append((route, c))
    print('=' * 92)
    print('  DOES THE ENGAGEMENT BAND MOVE WITH THE LKAS GAIN?')
    print('=' * 92)
    if unknown:
        print('  routes with no gain mapping (excluded): %s' % ', '.join(r for r, _ in unknown))
    print()
    print('  %-6s %-6s %s' % ('gain', 'routes', '  '.join('%-11s' % b[0] for b in BANDS)))
    print('  ' + '-' * 78)
    peaks = {}
    for g in sorted(groups):
        A = np.vstack([c for _, c in groups[g]])
        med = np.median(A, axis=0)
        row = []
        for _, lo, hi in BANDS:
            m = (WF >= lo) & (WF < hi)
            row.append(float(np.median(A[:, m].mean(axis=1))))
        # peak of the profile in 15-40 Hz, where the notch lives
        pm = (WF >= 15) & (WF <= 40)
        pk = float(WF[pm][np.argmax(med[pm])])
        peaks[g] = pk
        print('  %-6s %-6d %s' % ('%dx' % g, len(groups[g]),
                                  '  '.join('%-11.3f' % v for v in row)))
    print('  ' + '-' * 78)
    print()
    print('  PEAK of the profile over 15-40 Hz (where the notch lives):')
    for g in sorted(peaks):
        print('    %2dx : %.2f Hz   (%d route%s)' % (g, peaks[g], len(groups[g]),
                                                     '' if len(groups[g]) == 1 else 's'))
    print()
    print('  V241/V242 carry a notch with zero 29.75 Hz, pole 22.50 Hz, r 0.940.')
    if len(peaks) > 1:
        lo_g, hi_g = min(peaks), max(peaks)
        print('  shift from %dx to %dx: %+.2f Hz' % (lo_g, hi_g, peaks[hi_g] - peaks[lo_g]))
    print()
    print('  \U0001f6d1 the 8x arm is ONE route (r95/V101), so build and route are confounded there.')
    print('     This can show a shift worth acting on; it cannot attribute it to the gain alone.')


if __name__ == '__main__':
    main()
