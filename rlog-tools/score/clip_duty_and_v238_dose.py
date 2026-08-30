#!/usr/bin/env python3
r"""How hard does the slew limiter actually bite -- and therefore what is V238 worth?

V238 lowers the engaged lag pole `0xC6906` 20 -> 8.  The lane is a BLEND

    out(f) = table2 + H_k(f) * (table1 - table2)      table2 = the gp-0x69a0 slew-limited map
                                                      table1 = the 0xC6384-capped map

so the SIZE of the change is set entirely by how big `table1 - table2` is in real driving -- the CUT
the slew limiter makes -- and by how often the gate `step_on` is even closed.  Neither has ever been
measured on a route.  That is the one open question on V238's card, and this answers it.

Per frame, from the integer-exact firmware mirror (`assist_map_mirror`):

    b82  = iVar34, the DIRECT path (the limited value when the gate is on)
    b84  = iVar33, EXACTLY what the slew limiter cut
    step = bVar3,  the gate

    lane output at f   =  b82 + H_k(f) * b84
    V238's delta at f  =  (H_20(f) - H_8(f)) * b84
    relative change    =  that, over |b82| + H_20 * |b84|

NOTHING here is a model of the car: b82/b84/step come from the ROM record plus the exact integer
transform.  What IS assumed is that the cached torque/speed/angle are the firmware's own inputs.

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

import cmath
import glob
import os
import sys

import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from assist_map_mirror import stage_382d8, stage_389ec, build_map, lane, _lerp_u16, u16, TP

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
F_RATCHET = 7.79
FS = 1000.0
K_CAR, K_V238, K_FLOOR = 20, 8, 2

G69A0_B_X = [u16(TP + 0x7912 + 2 * i) for i in range(4)]
G69A0_B_Y = [u16(TP + 0x791A + 2 * i) for i in range(4)]


def g69a0_of(speed_cnt):
    return min(4096, _lerp_u16(int(speed_cnt), G69A0_B_X, G69A0_B_Y))


def H(k, f=F_RATCHET, fs=FS):
    """|H| of the EMA  y += (x-y)*k>>11, i.e. a = k/2048, at frequency f."""
    a = k / 2048.0
    z = cmath.exp(-2j * cmath.pi * f / fs)
    return abs(a / (1 - (1 - a) * z))


_MAPCACHE = {}


def map_for(mode, speed_cnt, angle_10deg):
    key = (mode, int(speed_cnt) // 16, int(angle_10deg) // 10)
    m = _MAPCACHE.get(key)
    if m is None:
        sc = (int(speed_cnt) // 16) * 16
        ag = (int(angle_10deg) // 10) * 10
        A, B = stage_382d8(mode, sc)
        Xs, Ys = stage_389ec(A, B, sc, ag)
        m = build_map(Xs, Ys, g69a0_of(sc))
        _MAPCACHE[key] = m
    return m


# 🛑 NO FALLBACK KEY CHAIN.  A first pass used ('tq','sc_t','cs_t') and the loopop caches -- which
# carry no 'tq' -- silently fell through to `sc_t`, which is NOT the torque sensor (p50 129.9, max
# 159.9, near-constant, against tq's p50 111 / max 4076).  That manufactured a 0.0 % gate duty on 40
# routes and would have retired a live lever.  Require the exact keys or skip the cache.
REQUIRED = ('tq', 'cs_v', 'cs_ang', 'cc_lat')     # counts · m/s · deg · bool


def run_cache(path, mode=24, max_frames=40000):
    z = np.load(path, allow_pickle=True)
    if not all(k in z.files for k in REQUIRED):
        return None
    tq = np.asarray(z['tq'], float)
    kmh = np.abs(np.asarray(z['cs_v'], float)) * 3.6
    ang = np.abs(np.asarray(z['cs_ang'], float))
    eng = np.asarray(z['cc_lat'], float) > 0.5
    n = min(len(tq), len(kmh), len(ang), len(eng))
    if n < 500 or eng[:n].sum() < 200:
        return None
    sl = slice(0, min(n, max_frames))
    tq, kmh, ang, eng = tq[sl], kmh[sl], ang[sl], eng[sl]
    Tsens = np.rint(tq * 1.024).astype(int)
    m = len(Tsens)
    b82 = np.zeros(m, int)
    b84 = np.zeros(m, int)
    step = np.zeros(m, bool)
    for i in range(m):
        X, Y, Z, S = map_for(mode, kmh[i] * 64.0, ang[i] * 10.0)
        r = lane(int(Tsens[i]), X, Y, Z, S)
        b82[i] = r['b82']
        b84[i] = r['b84']
        step[i] = r['step_on']
    return dict(b82=b82, b84=b84, step=step, eng=eng, route=os.path.basename(path))


def main():
    caches = sorted(glob.glob(os.path.join(REPO, '_scratch', 'cache', '*', '*.npz')))
    if len(sys.argv) > 1:
        caches = [c for c in caches if any(a in c for a in sys.argv[1:])]
    h20, h8, h2 = H(K_CAR), H(K_V238), H(K_FLOOR)

    print('=' * 100)
    print('  CLIP DUTY AND V238 DOSE   --   how hard does the slew limiter bite?')
    print('=' * 100)
    print('  |H| at %.2f Hz:   k=20 (car) %.4f   k=8 (V238) %.4f   k=2 (floor) %.4f'
          % (F_RATCHET, h20, h8, h2))
    print('  the lane runs at 1 kHz; these caches are ~101 Hz, so b84 is a PER-FRAME amplitude,')
    print('  not a spectrum -- what is measured here is the SIZE of the cut, not its frequency content.')
    print()
    print('  %-20s %6s %7s %10s %10s %9s %9s %9s' %
          ('route', 'eng.f', 'gate%', 'p50|b84|*', 'p90|b84|*', 'cut/out*', 'dv p50*', 'dv p90*'))
    print('  (* = CONDITIONAL ON THE GATE BEING ON. The unconditional median is 0 by construction')
    print('     wherever the gate duty is under 50 %, which is most routes -- that is not a null.)')
    print('  ' + '-' * 96)

    rows = []
    for c in caches:
        try:
            R = run_cache(c)
        except Exception:
            continue
        if R is None:
            continue
        e = R['eng']
        if e.sum() < 200:
            continue
        on = e & R['step']
        gate = 100.0 * R['step'][e].mean()
        if on.sum() < 50:
            rows.append((R['route'], int(e.sum()), gate, 0.0, 0.0, 0.0, 0.0, 0.0))
            continue
        a84 = np.abs(R['b84'][on]).astype(float)
        a82 = np.abs(R['b82'][on]).astype(float)
        denom = np.maximum(a82 + h20 * a84, 1.0)
        dv = 100.0 * (h20 - h8) * a84 / denom
        rows.append((R['route'], int(e.sum()), gate,
                     np.percentile(a84, 50), np.percentile(a84, 90),
                     100.0 * np.median(h20 * a84 / denom),
                     np.percentile(dv, 50), np.percentile(dv, 90)))
        if len(rows) >= 60:
            break

    for r in sorted(rows, key=lambda x: -x[2])[:28]:
        print('  %-20s %6d %6.1f%% %10.1f %10.1f %8.1f%% %8.2f%% %8.2f%%' % r)

    if rows:
        live = [r for r in rows if r[2] >= 1.0]
        g = np.array([r[2] for r in rows])
        print('  ' + '-' * 96)
        print('  %d routes, %d with the gate live (>=1%%). MEDIAN gate duty %.1f%%, '
              'median dv(p50) %.2f%%, median dv(p90) %.2f%%'
              % (len(rows), len(live), np.median(g),
                 np.median([r[6] for r in live]) if live else 0.0,
                 np.median([r[7] for r in live]) if live else 0.0))
        print()
        print('  READING IT:')
        print('   * gate%%    = engaged frames where the slew limiter is actually biting. If this were')
        print('               near zero everywhere the cell would be INERT and V238 could do nothing.')
        print("   * cut/out  = how much of the lane output IS the restored cut, at the car's k=20.")
        print('   * dv       = the reduction in lane output at %.2f Hz from k 20 -> 8, in per cent.' % F_RATCHET)
        print('               This is the honest size of V238, which the card has called UNMEASURED.')
        print()
        print('  🛑 WHAT THIS IS NOT: the caches run at ~101 Hz, so this measures the SIZE of the')
        print('     cut per frame, NOT how much of it sits at 7.79 Hz. A large cut that is all')
        print('     low-frequency would be restored at any k and would move nothing.')


if __name__ == '__main__':
    main()
