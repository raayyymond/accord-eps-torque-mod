#!/usr/bin/env python3
r"""Frame-by-frame reconstruction of gp-0x6b82 / gp-0x6b7a / gp-0x6b7e over the route caches,
and the +-0x3000 clip duty as a function of the c4 boost k.

Uses `assist_map_mirror` (the integer-exact firmware mirror).  Nothing here is a model:
every number comes from the ROM record plus the exact integer transform.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
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
# --- end path bootstrap ---------------------------------------------------
import sys, json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
from assist_map_mirror import (stage_382d8, stage_389ec, build_map, lane, _lerp_u16,
                               biquad_response, u16, TP, CAL_7178, CAL_7200)

ROUTES = {                      # route -> (cache dir, build)
    '9e': ('_scratch/cache/r9e/r9e.npz', 'V103'),
    '96': ('_scratch/cache/r96/r96.npz', 'V102'),
    '95': ('_scratch/cache/r95/r95.npz', 'V101'),
    '85': ('_scratch/cache/r85/r85.npz', 'V100'),
    '97': ('_scratch/cache/r97/r97.npz', 'STOCK'),
}
SPEED_BANDS = [(0, 10), (10, 20), (20, 40), (40, 70), (70, 999)]
RATE_BANDS = [(0, 5), (5, 20), (20, 60), (60, 999)]
KS = [1.10, 1.20, 1.25, 1.35, 1.50, 1.70, 1.85, 2.00, 2.33, 2.50, 3.00]

# gp-0x69a0: min( LERP_A(gp-0x69a8)=4096 , LERP_B_or_C(speed) ) -- FUN_00035b20
G69A0_B_X = [u16(TP + 0x7912 + 2 * i) for i in range(4)]
G69A0_B_Y = [u16(TP + 0x791A + 2 * i) for i in range(4)]
G69A0_C_X = [u16(TP + 0x7936 + 2 * i) for i in range(4)]
G69A0_C_Y = [u16(TP + 0x793E + 2 * i) for i in range(4)]


def g69a0_of(speed_cnt, armed=True):
    X, Y = (G69A0_B_X, G69A0_B_Y) if armed else (G69A0_C_X, G69A0_C_Y)
    return min(4096, _lerp_u16(int(speed_cnt), X, Y))


_MAPCACHE = {}


def map_for(mode, speed_cnt, angle_10deg, armed=True):
    key = (mode, int(speed_cnt) // 16, int(angle_10deg) // 10, armed)
    m = _MAPCACHE.get(key)
    if m is None:
        sc = (int(speed_cnt) // 16) * 16
        ag = (int(angle_10deg) // 10) * 10
        A, B = stage_382d8(mode, sc)
        Xs, Ys = stage_389ec(A, B, sc, ag)
        m = build_map(Xs, Ys, g69a0_of(sc, armed))
        _MAPCACHE[key] = m
    return m


def run_route(route, mode=24, comp=0.0, armed=True):
    path, build = ROUTES[route]
    z = np.load(HERE / path, allow_pickle=True)
    t = np.asarray(z['t'], float)
    eng = np.asarray(z['cc_lat'], float) > 0.5
    tq = np.asarray(z['tq'], float)
    v_ms = np.abs(np.asarray(z['v_rear'], float))
    ang = np.abs(np.asarray(z['cs_ang'], float))
    rate = np.abs(np.asarray(z['rate_f'], float))
    kmh = v_ms * 3.6
    n = len(t)
    Tsens = np.rint(tq * 1.024).astype(int)
    b7a = np.zeros(n, int); b82 = np.zeros(n, int); b84 = np.zeros(n, int)
    aq = np.zeros(n, int); step = np.zeros(n, bool); aTc = np.zeros(n, int)
    for i in range(n):
        X, Y, Z, S = map_for(mode, kmh[i] * 64.0, ang[i] * 10.0, armed)
        r = lane(int(Tsens[i]) + int(comp), X, Y, Z, S)
        b7a[i] = r['b7a']; b82[i] = r['b82']; b84[i] = r['b84']
        aq[i] = r['a_q10']; step[i] = r['step_on']; aTc[i] = r['aTc']
    # gp-0x6b7e : 32-bit EMA of 128*gp-0x6b84 with alpha = 20/2048, +-0x80 deadband (0x359d8)
    acc = 0
    b7e = np.zeros(n, int)
    for i in range(n):
        acc = acc + (((b84[i] * 128) - acc) * 20 >> 11)
        v = acc - 0x80 if acc > 0x80 else (acc + 0x80 if acc < -0x80 else 0)
        b7e[i] = v >> 7
    return dict(t=t, eng=eng, kmh=kmh, rate=rate, Tsens=Tsens, aTc=aTc,
                b7a=b7a, b82=b82, b84=b84, b7e=b7e, aq=aq, step=step, build=build)


def episodes_of(mask, t, min_s=1.0):
    out, i, n = [], 0, len(mask)
    dt = float(np.median(np.diff(t)))
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if (j - i) * dt >= min_s:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


def boot_pct(vals, eps, q, nboot=2000, seed=0):
    """Episode block bootstrap of a percentile."""
    rng = np.random.default_rng(seed)
    blocks = [vals[a:b] for a, b in eps if b > a]
    if not blocks:
        return (np.nan, np.nan)
    out = []
    for _ in range(nboot):
        idx = rng.integers(0, len(blocks), len(blocks))
        out.append(np.percentile(np.concatenate([blocks[i] for i in idx]), q))
    return (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)))


def report(route, mode=24, comp=0.0, armed=True, do_boot=True):
    R = run_route(route, mode, comp, armed)
    eng, t = R['eng'], R['t']
    a82 = np.abs(R['b82']).astype(float)
    print('\n' + '=' * 92)
    print('ROUTE %s (%s)  mode=%d  comp(gp-0x6b4a)=%+.0f  armed=%s   n=%d  engaged=%d frames (%.1f s)'
          % (route, R['build'], mode, comp, armed, len(t), eng.sum(),
             eng.sum() * float(np.median(np.diff(t)))))
    print('=' * 92)
    e = a82[eng]
    print('|gp-0x6b82| ENGAGED : p50=%.1f p90=%.1f p95=%.1f p99=%.1f p99.9=%.1f max=%.1f   (clamp=12288)'
          % (np.percentile(e, 50), np.percentile(e, 90), np.percentile(e, 95),
             np.percentile(e, 99), np.percentile(e, 99.9), e.max()))
    m = a82[~eng]
    print('|gp-0x6b82| MANUAL  : p50=%.1f p95=%.1f p99=%.1f max=%.1f' %
          (np.percentile(m, 50), np.percentile(m, 95), np.percentile(m, 99), m.max()))
    print('|gp-0x6b7a| ENGAGED : p50=%.1f p95=%.1f max=%.1f    identical to 6b82 on %.4f%% of engaged frames'
          % (np.percentile(np.abs(R['b7a'])[eng], 50), np.percentile(np.abs(R['b7a'])[eng], 95),
             np.abs(R['b7a'])[eng].max(),
             100.0 * (R['b82'][eng] == R['b7a'][eng]).mean()))
    print('gp-0x6b7e  ENGAGED : p50=%.2f p95=%.2f max|.|=%.2f    step_on duty=%.6f'
          % (np.percentile(np.abs(R['b7e'])[eng], 50), np.percentile(np.abs(R['b7e'])[eng], 95),
             np.abs(R['b7e'])[eng].max(), R['step'][eng].mean()))
    print('a = gp-0x69a4/1024 ENGAGED : p5=%.4f p50=%.4f p95=%.4f'
          % (np.percentile(R['aq'][eng], 5) / 1024, np.percentile(R['aq'][eng], 50) / 1024,
             np.percentile(R['aq'][eng], 95) / 1024))
    print('|Tc| ENGAGED : p50=%.0f p95=%.0f p99=%.0f max=%.0f  (map saturates at |Tc|>=8192)'
          % (np.percentile(R['aTc'][eng], 50), np.percentile(R['aTc'][eng], 95),
             np.percentile(R['aTc'][eng], 99), R['aTc'][eng].max()))
    if do_boot:
        eps = episodes_of(eng, t)
        for q in (50, 95, 99):
            lo, hi = boot_pct(a82, eps, q)
            print('   episode-bootstrap 95%% CI on engaged p%-2d of |6b82|: [%.1f, %.1f]  (%d episodes)'
                  % (q, lo, hi, len(eps)))
    print('\n  CLIP DUTY  P(|6b82| > 12288/k)  engaged     |  per speed band (km/h)')
    hdr = '   %-6s %-10s %-12s |' % ('k', 'thresh', 'overall')
    for lo, hi in SPEED_BANDS:
        hdr += ' %8s' % ('%d-%d' % (lo, hi) if hi < 999 else '>%d' % lo)
    print(hdr)
    for k in KS:
        th = 12288.0 / k
        d = (e > th).mean()
        row = '   %-6.2f %-10.1f %-12.6f |' % (k, th, d)
        for lo, hi in SPEED_BANDS:
            sel = eng & (R['kmh'] >= lo) & (R['kmh'] < hi)
            row += ' %8.6f' % ((a82[sel] > th).mean() if sel.sum() else np.nan)
        print(row)
    print('\n  |gp-0x6b82| engaged by SPEED band                    |  by |wheel rate| band (deg/s)')
    for lo, hi in SPEED_BANDS:
        sel = eng & (R['kmh'] >= lo) & (R['kmh'] < hi)
        if sel.sum() == 0:
            continue
        s = a82[sel]
        print('   %-8s n=%6d  p50=%7.1f p95=%7.1f p99=%7.1f max=%7.1f'
              % ('%d-%d' % (lo, hi) if hi < 999 else '>%d' % lo, sel.sum(),
                 np.percentile(s, 50), np.percentile(s, 95), np.percentile(s, 99), s.max()))
    for lo, hi in RATE_BANDS:
        sel = eng & (R['rate'] >= lo) & (R['rate'] < hi)
        if sel.sum() == 0:
            continue
        s = a82[sel]
        print('   rate %-6s n=%6d  p50=%7.1f p95=%7.1f p99=%7.1f max=%7.1f'
              % ('%d-%d' % (lo, hi) if hi < 999 else '>%d' % lo, sel.sum(),
                 np.percentile(s, 50), np.percentile(s, 95), np.percentile(s, 99), s.max()))
    return R


if __name__ == '__main__':
    args = sys.argv[1:]
    rt = args[0] if args else '9e'
    md = int(args[1]) if len(args) > 1 else 24
    cp = float(args[2]) if len(args) > 2 else 0.0
    report(rt, md, cp)
