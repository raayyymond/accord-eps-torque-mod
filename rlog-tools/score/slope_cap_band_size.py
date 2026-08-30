#!/usr/bin/env python3
r"""How big is `0xC6384` really, at the ratchet?  The same treatment that sized the pole at 3.8 %.

V239's big lever is the assist-map slope cap `0xC6384`, 2048 -> 1536 (s 2.000 -> 1.500).  Its only
number, "3.4x more damped", comes from a loop model the record itself later corrected -- the census
priced this lane as MEMORYLESS when it has a lagged branch.  So the direction is well-founded and the
SIZE has never been measured.  This measures it.

Method, identical to `clip_duty_and_v238_dose.py` so the two numbers are comparable:

  * rebuild the map through the integer-exact firmware mirror with CAL_7384 = 2048 and again = 1536
  * run the real per-frame torque/speed/angle from the route caches through `lane()`
  * form the lane output   out(f) = b82 + H_k(f)*b84   and take Welch band power over 6-9 Hz

Reported at the car's pole (k=20), which ISOLATES the cap, and at V239's pole (k=8), which is the
build.  A ratio below 1 is less lane gain at the ratchet, i.e. less positive feedback.

WHAT THIS IS NOT.  It is not a claim about how the car will feel.  It measures the LANE's contribution
at the ratchet band, which is the quantity the loop census makes a denominator term.  The step from
there to felt ratcheting is the loop model, and that model is the part the record calls incomplete.

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
from scipy import signal

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import assist_map_mirror as AM
from assist_map_mirror import stage_382d8, stage_389ec, build_map, lane

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clip_duty_and_v238_dose import g69a0_of, H, REQUIRED, REPO   # noqa: E402

CAP_STOCK, CAP_V236 = 2048, 1536
BAND = (6.0, 9.0)
MIN_ENG = 1500


def lane_series(z, cap, mode=24, max_frames=40000):
    """Per-frame b82/b84 with the slope cap forced to `cap`.  Nothing cached across caps."""
    AM.CAL_7384 = cap
    tq = np.asarray(z['tq'], float)
    kmh = np.abs(np.asarray(z['cs_v'], float)) * 3.6
    ang = np.abs(np.asarray(z['cs_ang'], float))
    eng = np.asarray(z['cc_lat'], float) > 0.5
    n = min(len(tq), len(kmh), len(ang), len(eng), max_frames)
    tq, kmh, ang, eng = tq[:n], kmh[:n], ang[:n], eng[:n]
    Tsens = np.rint(tq * 1.024).astype(int)
    b82 = np.zeros(n)
    b84 = np.zeros(n)
    mc = {}
    for i in range(n):
        key = (int(kmh[i] * 64.0) // 16, int(ang[i] * 10.0) // 10)
        m = mc.get(key)
        if m is None:
            sc, ag = key[0] * 16, key[1] * 10
            A, B = stage_382d8(mode, sc)
            Xs, Ys = stage_389ec(A, B, sc, ag)
            m = build_map(Xs, Ys, g69a0_of(sc))
            mc[key] = m
        r = lane(int(Tsens[i]), *m)
        b82[i] = r['b82']
        b84[i] = r['b84']
    return b82, b84, eng


def band_power(b82, b84, fs, k):
    """Welch band power of  out = b82 + H_k*b84,  evaluated per frequency bin."""
    npg = min(1024, (len(b82) // 4) * 2)
    if npg < 256:
        return np.nan
    f, P82 = signal.welch(b82 - b82.mean(), fs, nperseg=npg)
    _, P84 = signal.welch(b84 - b84.mean(), fs, nperseg=npg)
    _, Px = signal.csd(b82 - b82.mean(), b84 - b84.mean(), fs, nperseg=npg)
    m = (f >= BAND[0]) & (f <= BAND[1])
    Hk = np.array([H(k, ff, 1000.0) for ff in f])
    return float((P82[m] + Hk[m] ** 2 * P84[m] + 2 * Hk[m] * np.real(Px[m])).sum())


def main():
    caches = sorted(glob.glob(os.path.join(REPO, '_scratch', 'cache', '*', '*.npz')))
    if len(sys.argv) > 1:
        caches = [c for c in caches if any(a in c for a in sys.argv[1:])]

    print('=' * 100)
    print('  HOW BIG IS 0xC6384 AT THE RATCHET?   6-9 Hz band power, slope cap 2048 -> 1536')
    print('=' * 100)
    print('  %-16s %7s %11s %11s %11s' %
          ('route', 'eng.f', 'cap@k=20', 'cap@k=8', 'V239 total'))
    print('  (cap@k    = band power with the cap lowered, over the car, at that pole)')
    print('  (V239 total = cap lowered AND pole 20->8, over the car at 2048/k=20)')
    print('  ' + '-' * 76)

    rows = []
    for c in caches:
        try:
            z = np.load(c, allow_pickle=True)
        except Exception:
            continue
        if not all(k in z.files for k in REQUIRED) or 't' not in z.files:
            continue
        eng0 = np.asarray(z['cc_lat'], float) > 0.5
        if eng0.sum() < MIN_ENG:
            continue
        t = np.asarray(z['t'], float)
        fs = 1.0 / np.median(np.diff(t))
        try:
            a82, a84, e = lane_series(z, CAP_STOCK)
            c82, c84, _ = lane_series(z, CAP_V236)
        except Exception:
            continue
        finally:
            AM.CAL_7384 = CAP_STOCK
        if e.sum() < MIN_ENG:
            continue
        base20 = band_power(a82[e], a84[e], fs, 20)
        if not np.isfinite(base20) or base20 <= 0:
            continue
        cap20 = band_power(c82[e], c84[e], fs, 20) / base20
        cap8 = band_power(c82[e], c84[e], fs, 8) / base20
        rows.append((os.path.basename(c), int(e.sum()), cap20, cap8, cap8))
        if len(rows) >= 22:
            break

    for r in sorted(rows, key=lambda x: x[2]):
        print('  %-16s %7d %11.4f %11.4f %11.4f' % r)

    if rows:
        c20 = np.array([r[2] for r in rows])
        c8 = np.array([r[3] for r in rows])
        print('  ' + '-' * 76)
        print('  %d routes' % len(rows))
        print('    0xC6384 ALONE (k=20)   median %.4f  (%+.1f %%)   range %.3f .. %.3f'
              % (np.median(c20), 100 * (np.median(c20) - 1), c20.min(), c20.max()))
        print('    V239 = cap + pole      median %.4f  (%+.1f %%)   range %.3f .. %.3f'
              % (np.median(c8), 100 * (np.median(c8) - 1), c8.min(), c8.max()))
        print()
        print('  FOR COMPARISON, measured the same way last tick:')
        print('    0xC6906 alone, k 20->8      0.9731   (-2.7 %)')
        print('    0xC6906 alone, k 20->2      0.9622   (-3.8 %)  <- the cell\'s WHOLE range')
        print()
        print('  \U0001f6d1 A ratio below 1 is less LANE GAIN at the ratchet band. The step from there to')
        print('     felt ratcheting is the loop model, and that model is the part the record calls')
        print('     incomplete. This sizes the lever, not the symptom.')


if __name__ == '__main__':
    main()
