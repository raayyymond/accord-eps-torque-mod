#!/usr/bin/env python3
r"""A LEVER CENSUS BY MEASUREMENT, not by loop model.

Every cal the assist-map path reads is perturbed one at a time, and the 6-9 Hz band power of the lane
output is measured through the integer-exact firmware mirror driven by real route data.  The effort cost
is measured alongside it, so a lever that buys damping by taking assist away is not mistaken for a free
one.

WHY THIS EXISTS.  The loop census ranked these lanes analytically and has now been wrong twice in one
session: it priced `0xC6384` as "3.4x more damped" when the cell is INERT (it only reaches above 2844
torque counts, 1.65 % of frames), and it priced the lane as memoryless when it is a blend.  Direct
measurement caught both, and then found `0xC693E` -- byte-stock on all 161 images -- at -6.0 %.

METHOD
  * for each cal, rebuild the map through the mirror with the cal scaled up and down
  * run real per-frame torque/speed/angle from the route caches through `lane()`
  * Welch band power over 6-9 Hz on  out = b82 + H_k*b84,  at the car's pole (k=20)
  * report band ratio vs the car AND the delivered-assist ratio (p50 and p95)

READING IT.  band < 1 is less lane gain at the ratchet.  assist < 1 is less delivered assist, i.e. more
steering effort -- the operator's standing constraint is that damping must not be bought with effort.

WHAT THIS IS NOT.  It measures the LANE's contribution at the band.  The step from there to felt
ratcheting is the loop model, which is the part the record calls incomplete.  A lever measuring 0.0 %
here is genuinely unreachable; a lever measuring -6 % here is a candidate, not a promise.

PATH BOOTSTRAP -- see the note in the sibling scripts.
"""
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)

import glob
import os
import sys

import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import assist_map_mirror as AM
from assist_map_mirror import u16, TP, _lerp_u16

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clip_duty_and_v238_dose as C          # noqa: E402
import slope_cap_band_size as S              # noqa: E402

REPO = C.REPO
MIN_ENG = 1500
N_ROUTES = 10

# The NORMAL gp-0x69a0 curve is the live one; the readers default to the OSCILLATING branch, which
# cost two ticks of measurement before it was caught.  Pin it explicitly here.
NX = [u16(TP + 0x7936 + 2 * i) for i in range(4)]
NY = [u16(TP + 0x793E + 2 * i) for i in range(4)]


def slew_fn(Y):
    return lambda sc: min(4096, _lerp_u16(int(sc), NX, Y))


# name, address, kind, how to apply a scale
SCALARS = [
    ('CAL_7384  slope cap',      0xC6384, 'CAL_7384'),
    ('CAL_7178  slot ceiling',   0xC6178, 'CAL_7178'),
    ('CAL_713A',                 0xC613A, 'CAL_713A'),
    ('CAL_713C  X-ish[9]',       0xC613C, 'CAL_713C'),
    ('CAL_7200  torque clamp',   0xC6200, 'CAL_7200'),
    ('CAL_7468',                 0xC6468, 'CAL_7468'),
]
TABLES = [
    ('SPD_CAP_Y  torque cap',    0xC66A8, 'SPD_CAP_Y'),
    ('BOOST_Y    angle boost',   0xC6B80, 'BOOST_Y'),
]
SCALES = [0.6, 1.4]


def measure(caches, apply_fn, base):
    b, a50, a95 = [], [], []
    for c in caches:
        z = np.load(c, allow_pickle=True)
        t = np.asarray(z['t'], float)
        fs = 1.0 / np.median(np.diff(t))
        apply_fn()
        try:
            b82, b84, e = S.lane_series(z, AM.CAL_7384)
        except Exception:
            return None
        b0, m50, m95 = base[c]
        bp = S.band_power(b82[e], b84[e], fs, 20)
        if b0 > 0 and np.isfinite(bp):
            b.append(bp / b0)
        if m50 > 0:
            a50.append(np.percentile(np.abs(b82[e]), 50) / m50)
        if m95 > 0:
            a95.append(np.percentile(np.abs(b82[e]), 95) / m95)
    if not b:
        return None
    return np.median(b), np.median(a50), np.median(a95)


def main():
    caches = []
    for c in sorted(glob.glob(os.path.join(REPO, '_scratch', 'cache', '*', '*.npz'))):
        try:
            z = np.load(c, allow_pickle=True)
        except Exception:
            continue
        if not all(k in z.files for k in C.REQUIRED) or 't' not in z.files:
            continue
        if (np.asarray(z['cc_lat'], float) > 0.5).sum() < MIN_ENG:
            continue
        caches.append(c)
        if len(caches) >= N_ROUTES:
            break

    stock = {k: getattr(AM, k) for _, _, k in SCALARS + TABLES}
    C.g69a0_of = slew_fn(NY)
    S.g69a0_of = C.g69a0_of

    base = {}
    for c in caches:
        z = np.load(c, allow_pickle=True)
        t = np.asarray(z['t'], float)
        fs = 1.0 / np.median(np.diff(t))
        b82, b84, e = S.lane_series(z, stock['CAL_7384'])
        base[c] = (S.band_power(b82[e], b84[e], fs, 20),
                   np.percentile(np.abs(b82[e]), 50), np.percentile(np.abs(b82[e]), 95))

    print('=' * 100)
    print('  CAL CENSUS BY MEASUREMENT -- %d routes, 6-9 Hz band power, gp-0x69a0 on the NORMAL curve'
          % len(caches))
    print('=' * 100)
    print('  %-26s %7s %10s %10s %10s' % ('cal', 'scale', 'band 6-9', 'assist p50', 'assist p95'))
    print('  ' + '-' * 70)

    rows = []
    for name, addr, key in SCALARS + TABLES:
        istable = any(key == k for _, _, k in TABLES)
        for sc in SCALES:
            def apply(key=key, sc=sc, istable=istable):
                for k, v in stock.items():
                    setattr(AM, k, v)
                v = stock[key]
                setattr(AM, key, [max(0, int(round(x * sc))) for x in v] if istable
                        else max(0, int(round(v * sc))))
            r = measure(caches, apply, base)
            for k, v in stock.items():
                setattr(AM, k, v)
            if r is None:
                print('  %-26s %7.2f %10s' % (name, sc, 'n/a'))
                continue
            print('  %-26s %7.2f %10.4f %10.4f %10.4f' % (name, sc, r[0], r[1], r[2]))
            rows.append((name, sc, r[0], r[1], r[2]))

    # the two curve/table levers already characterised, for comparison on the same axis
    print('  ' + '-' * 70)
    for tag, Y in (('gp-0x69a0 NORMAL x0.6', [round(y * 0.6) for y in NY]),
                   ('gp-0x69a0 NORMAL x1.4', [round(y * 1.4) for y in NY])):
        def apply(Y=Y):
            for k, v in stock.items():
                setattr(AM, k, v)
            C.g69a0_of = slew_fn(Y)
            S.g69a0_of = C.g69a0_of
        r = measure(caches, apply, base)
        C.g69a0_of = slew_fn(NY)
        S.g69a0_of = C.g69a0_of
        if r:
            print('  %-26s %7s %10.4f %10.4f %10.4f' % (tag, '', r[0], r[1], r[2]))
            rows.append((tag, 0.6 if 'x0.6' in tag else 1.4, r[0], r[1], r[2]))

    print()
    print('  RANKED by band reduction, among levers that do NOT cost median assist:')
    free = [r for r in rows if r[3] >= 0.999 and r[2] < 1.0]
    for r in sorted(free, key=lambda x: x[2])[:10]:
        print('    %-26s scale %.2f   band %.4f (%+.1f %%)   assist p95 %.4f'
              % (r[0], r[1], r[2], 100 * (r[2] - 1), r[4]))
    if not free:
        print('    (none)')
    print()
    print('  \U0001f6d1 band < 1 = less lane gain at the ratchet. assist < 1 = MORE STEERING EFFORT.')
    print('     A lever is only interesting if it moves band without moving assist p50.')


if __name__ == '__main__':
    main()
