#!/usr/bin/env python3
r"""IS V235's NOTCH OPTIMAL FOR THE BAND, OR MERELY INSIDE IT?

The IMU -- independent of the EPS, and no part of the geometry's derivation -- names 22-30 Hz as the
largest engagement-created motion band, peaking at 25-26 Hz.  V235's notch sits at zero 25.00 Hz,
pole 23.50 Hz, r 0.96.  That is the right band.  This asks whether it is the right SHAPE, by scoring
candidate geometries against the MEASURED profile instead of the CAN objective they were fitted to.

THE OBJECTIVE, and every constraint is one the record already imposes:
  * MINIMISE  sum over f of  excess(f) * |H(f)|^2   -- cut where engagement actually adds motion,
    weighted by how much it adds, rather than at a hand-picked centre frequency
  * SUBJECT TO  max|H| <= 1.0000 over 0-50 Hz.  The lineage bar: V194/V195/V196/V198 were PULLED for
    max|H| 1.3533-1.7177, and a later candidate peaking at 1.0020 was DELETED rather than granted a
    third exception.
  * SUBJECT TO  |H| >= KEEP_LOW over 6-15 Hz.  The lane is measured DAMPING there (cos -0.918/-0.989/
    -0.629, 3/3 routes) and the record's instruction is verbatim: "never notch 6-15 Hz on this lane".
    Cutting there removes damping -- it is what condemned V238/V240.

So the search is: among notches that obey the kit's own two hard rules, which cuts the most of what
the independent instrument says engagement creates?

READING IT
  * V235 at or near the top  => the geometry is already right and no rebuild is warranted.
  * a clearly better shape   => a free improvement, in the same 12 bytes, on a better-founded
    objective than the one it was fitted to.

WHAT THIS IS NOT.  The weight is CHASSIS MOTION; the notch filters a TORQUE lane.  Optimising against
motion is better founded than optimising against nothing, but it is not the lane's own spectrum.

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
import struct
import sys

import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import imu_engagement_spectrum as SP                                  # noqa: E402

FS = 1000.0
# 🛑 THE BAR IS THE CAR, NOT A GUESS. A first pass used an arbitrary 0.97 floor, which is
# STRICTER than Honda's own filter meets (stock dips to 0.9344 at 15 Hz) -- so stock itself came
# back 'VIOLATES'. The record has been bitten by exactly this before, when an arbitrary 1.5x
# threshold carried from V232 had to be corrected to 'the bar is Honda'. The floor is now what
# STOCK achieves: a candidate must cut no MORE of the damping band than Honda already does.
KEEP_LOW = 0.9344        # stock's own min |H| over 6-15 Hz, measured from the image
LOW_LO, LOW_HI = 6.0, 15.0
MAXH = 1.0000            # the lineage bar
GRID = np.arange(0.5, 50.0, 0.25)


def resp(zf, pf, r, f):
    """direct-form biquad with zeros ON the unit circle at zf and poles at radius r, angle pf"""
    wz, wp = 2 * np.pi * zf / FS, 2 * np.pi * pf / FS
    b1 = -2 * np.cos(wz)
    a1, a2 = -2 * r * np.cos(wp), r * r
    z = np.exp(-2j * np.pi * f / FS)
    num = 1 + b1 * z + z * z
    den = 1 + a1 * z + a2 * z * z
    c4 = abs((1 + a1 + a2) / (1 + b1 + 1))          # unit DC gain
    return np.abs(c4 * num / den)


def score(zf, pf, r, w, wf):
    H = resp(zf, pf, r, GRID)
    mx = H.max()
    if mx > MAXH + 1e-9:
        return None, mx, None
    lowm = (GRID >= LOW_LO) & (GRID <= LOW_HI)
    lo = H[lowm].min()
    if lo < KEEP_LOW - 1e-4:          # tolerance: stock must pass its OWN measured bar
        return None, mx, lo
    Hb = resp(zf, pf, r, wf)
    return float((w * Hb ** 2).sum() / w.sum()), mx, lo


def main():
    # the measured weight: engagement excess above 1, over the band the IMU says is real
    curves = []
    for f, c in SP_curves():
        curves.append(np.interp(np.arange(3.0, 45.0, 0.25), f, c))
    wf = np.arange(3.0, 45.0, 0.25)
    med = np.median(np.vstack(curves), axis=0)
    w = np.clip(med - 1.0, 0, None)                 # only the EXCESS counts
    print('=' * 92)
    print('  IS V235 OPTIMAL FOR THE MEASURED BAND?   weight = IMU engagement excess, %d routes'
          % len(curves))
    print('=' * 92)
    print('  constraints: max|H| <= %.4f over 0-50 Hz   AND   |H| >= %.2f over %.0f-%.0f Hz'
          % (MAXH, KEEP_LOW, LOW_LO, LOW_HI))
    print('  (the second is the record\'s "never notch 6-15 Hz on this lane" -- it damps there)')
    print()

    # what the images actually carry
    FW = os.environ.get('ACCORD_FIRMWARE_ROOT', '')
    cur = None
    for tag, pat in (('V235', '_v235_*plain_image.bin'), ('stock', 'stock_fw_dump/code.bin')):
        g = glob.glob(os.path.join(FW, 'analysis-2020accord', pat))
        if not g:
            continue
        a1, a2, b1, c4 = struct.unpack_from('<ffff', open(g[0], 'rb').read(), 0xC60A8)
        zf = np.arccos(np.clip(-b1 / 2, -1, 1)) * FS / (2 * np.pi)
        rr = np.sqrt(abs(a2))
        pf = np.arccos(np.clip(-a1 / (2 * rr), -1, 1)) * FS / (2 * np.pi)
        s, mx, lo = score(zf, pf, rr, w, wf)
        Hb = resp(zf, pf, rr, wf)
        raw = float((w * Hb ** 2).sum() / w.sum())      # cost regardless of feasibility
        print('  ON DISK  %-6s zero %6.2f Hz  pole %6.2f Hz  r %.4f   cost %.5f  max|H| %.4f  '
              'min|H| 6-15 %.4f%s'
              % (tag, zf, pf, rr, raw, mx, lo if lo is not None else float('nan'),
                 '' if s is not None else '   <- BELOW the stock floor'))
        s = raw
        if tag == 'V235':
            cur = (zf, pf, rr, s)
    print()

    best = []
    for zf in np.arange(20.0, 34.01, 0.25):
        for pf in np.arange(18.0, 34.01, 0.25):
            for r in (0.90, 0.92, 0.94, 0.95, 0.96, 0.97, 0.975, 0.98):
                s, mx, lo = score(zf, pf, r, w, wf)
                if s is not None:
                    best.append((s, zf, pf, r, mx))
    best.sort()
    print('  BEST FEASIBLE GEOMETRIES (lower cost = more of the measured excess removed):')
    print('  %8s %9s %9s %7s %9s' % ('cost', 'zero Hz', 'pole Hz', 'r', 'max|H|'))
    for s, zf, pf, r, mx in best[:10]:
        print('  %8.5f %9.2f %9.2f %7.3f %9.4f' % (s, zf, pf, r, mx))
    if cur and cur[3] is not None:
        rank = sum(1 for b in best if b[0] < cur[3])
        print()
        print('  V235 cost %.5f  -> rank %d of %d feasible geometries (%.1f%% are better)'
              % (cur[3], rank + 1, len(best), 100.0 * rank / max(len(best), 1)))
        if best:
            gain = 100.0 * (1 - best[0][0] / cur[3])
            print('  best feasible removes %.1f%% more of the measured excess than V235' % gain)
    print()
    print('  \U0001f6d1 the weight is CHASSIS MOTION; the notch filters a TORQUE lane. Better founded')
    print('     than the objective it was fitted to, but not the lane\'s own spectrum.')


def SP_curves():
    """reuse the spectrum module's per-route curves without duplicating the pipeline"""
    import collections
    import re
    from scipy import interpolate
    imus = sorted(glob.glob(os.path.join(SP.REPO, '_scratch', 'cache', '*', '*_imu.npz')))
    byroute = collections.defaultdict(list)
    for p in imus:
        m = re.match(r'^(r[0-9a-fx]+?)s?\d*$', os.path.basename(p).replace('_imu.npz', ''))
        if m:
            byroute[m.group(1)].append(p)
    out = []
    for route, paths in sorted(byroute.items()):
        acc = {'g': [[], []], 'a': [[], []]}
        te = tm = 0.0
        fg = fa = None
        for p in paths:
            can, _ = SP.can_for(p)
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
        out.append((fg[b], gy / np.maximum(rd, 1e-30)))
    return out


if __name__ == '__main__':
    main()
