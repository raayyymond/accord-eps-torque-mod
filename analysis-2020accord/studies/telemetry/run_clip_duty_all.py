#!/usr/bin/env python3
r"""All-routes reconstruction: |gp-0x6b82|, gp-0x6b7e, the critical k, and the 6-9 Hz split.

Mode is per-frame: ENGAGED -> 26, MANUAL -> 24 (HANDOFF-2026-08-05, V73's probe: the mode byte
gp+0x63fd toggles with engagement, manual=24 / engaged=26).
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
from scipy.signal import butter, sosfiltfilt

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
import run_clip_duty as RC
from assist_map_mirror import lane, biquad_response, CAL_7178

KS = [1.10, 1.20, 1.25, 1.35, 1.50, 1.70, 1.85, 2.00, 2.33, 3.00, 5.00, 10.0]
FS = 100.0


def run(route, comp=0.0):
    path, build = RC.ROUTES[route]
    p = HERE / path
    if not p.exists():
        return None
    z = np.load(p, allow_pickle=True)
    t = np.asarray(z['t'], float)
    eng = np.asarray(z['cc_lat'], float) > 0.5
    tq = np.asarray(z['tq'], float)
    kmh = np.abs(np.asarray(z['v_rear'], float)) * 3.6
    ang = np.abs(np.asarray(z['cs_ang'], float))
    rate = np.abs(np.asarray(z['rate_f'], float))
    n = len(t)
    Ts = np.rint(tq * 1.024).astype(int)
    KEYS = {'b7a': 'b7a', 'b82': 'b82', 'b84': 'b84', 'aq': 'a_q10', 'aTc': 'aTc'}
    out = {k: np.zeros(n, int) for k in KEYS}
    step = np.zeros(n, bool)
    for i in range(n):
        mode = 26 if eng[i] else 24
        X, Y, Z, S = RC.map_for(mode, kmh[i] * 64.0, ang[i] * 10.0, True)
        r = lane(int(Ts[i]) + int(comp), X, Y, Z, S)
        for k, src in KEYS.items():
            out[k][i] = r[src]
        step[i] = r['step_on']
    acc = 0
    b7e = np.zeros(n, int)
    for i in range(n):
        acc = acc + (((out['b84'][i] * 128) - acc) * 20 >> 11)
        v = acc - 0x80 if acc > 0x80 else (acc + 0x80 if acc < -0x80 else 0)
        b7e[i] = v >> 7
    out.update(dict(t=t, eng=eng, kmh=kmh, rate=rate, b7e=b7e, step=step, build=build))
    return out


def apply_biquad(u, fs=FS, k=1.0):
    """The exact difference equation from 0x35a28, without the +-12.0 clamp (so we can SEE overflow)."""
    from assist_map_mirror import BQ_A1, BQ_A2, BQ_B1, BQ_C4
    c4 = BQ_C4 * k
    w1 = w2 = 0.0
    y = np.zeros(len(u))
    for i, x in enumerate(u):
        w = c4 * (x / 1024.0) - BQ_A1 * w1 - BQ_A2 * w2
        y[i] = (w + BQ_B1 * w1 + w2) * 1024.0
        w2, w1 = w1, w
    return y


def band_rms(x, lo, hi, fs=FS):
    sos = butter(4, [lo / (fs / 2), hi / (fs / 2)], btype='band', output='sos')
    return float(np.sqrt(np.mean(sosfiltfilt(sos, x) ** 2)))


def main():
    rows = []
    for rt in ('9e', '96', '95', '85', '97'):
        R = run(rt)
        if R is None:
            print('route %s: cache missing' % rt)
            continue
        eng = R['eng']
        a82 = np.abs(R['b82']).astype(float)
        a7e = np.abs(R['b7e']).astype(float)
        e = a82[eng]
        dt = float(np.median(np.diff(R['t'])))
        print('\n' + '=' * 96)
        print('ROUTE %s (%s)  n=%d  engaged=%d (%.1f s)  mode 26 engaged / 24 manual'
              % (rt, R['build'], len(R['t']), eng.sum(), eng.sum() * dt))
        print('=' * 96)
        print(' |6b82| ENG p50=%.0f p95=%.0f p99=%.0f p99.9=%.0f max=%.0f   |  MAN p50=%.0f p95=%.0f max=%.0f'
              % (np.percentile(e, 50), np.percentile(e, 95), np.percentile(e, 99),
                 np.percentile(e, 99.9), e.max(),
                 np.percentile(a82[~eng], 50), np.percentile(a82[~eng], 95), a82[~eng].max()))
        print(' |6b7e| ENG p50=%.0f p95=%.0f max=%.0f    step_on duty ENG=%.6f MAN=%.6f'
              % (np.percentile(a7e[eng], 50), np.percentile(a7e[eng], 95), a7e[eng].max(),
                 R['step'][eng].mean(), R['step'][~eng].mean()))
        print(' a=gp-0x69a4/1024 ENG p50=%.4f p95=%.4f p99=%.4f max=%.4f  | P(a>=0.5)=%.6f P(a>=1.0)=%.6f'
              % (np.percentile(R['aq'][eng], 50) / 1024, np.percentile(R['aq'][eng], 95) / 1024,
                 np.percentile(R['aq'][eng], 99) / 1024, R['aq'][eng].max() / 1024,
                 (R['aq'][eng] >= 512).mean(), (R['aq'][eng] >= 1024).mean()))
        print(' a ALL FRAMES P(a>=512)=%.6f  P(a>=1024)=%.6f     [V72 bit6/bit5 prediction, route 59 shape]'
              % ((R['aq'] >= 512).mean(), (R['aq'] >= 1024).mean()))
        # --- critical k, frame-exact:  |k*H(z)*b82 + b7e| > 12288 ---
        yh = apply_biquad(R['b82'].astype(float), FS, 1.0)   # H at k=1 (linear -> scales with k)
        crit = (12288.0 - a7e) / np.maximum(np.abs(yh), 1e-9)
        ce = crit[eng]
        print(' CRITICAL k (frame-exact, |k*H*6b82| + |6b7e| = 12288): min over ENGAGED = %.2f'
              ' (p1=%.2f p5=%.2f)' % (ce.min(), np.percentile(ce, 1), np.percentile(ce, 5)))
        print('   -> engaged clip duty is EXACTLY ZERO for every k < %.2f' % ce.min())
        hdr = '   %-6s %-11s %-11s' % ('k', 'duty ENG', 'duty ALL')
        print(hdr)
        for k in KS:
            d_e = (np.abs(yh[eng]) * k + a7e[eng] > 12288).mean()
            d_a = (np.abs(yh) * k + a7e > 12288).mean()
            print('   %-6.2f %-11.6f %-11.6f' % (k, d_e, d_a))
        # --- 6-9 Hz split: what fraction of the lane's band content is NOT scaled by c4 ---
        for lo, hi, nm in ((6, 9, '6-9'), (15, 22, '15-22'), (20, 28, '20-28')):
            try:
                r82 = band_rms(yh[eng], lo, hi)
                r7e = band_rms(a7e[eng] * np.sign(R['b7e'][eng] + 1e-9), lo, hi)
                tot = band_rms(yh[eng] + R['b7e'][eng], lo, hi)
                print('   %s Hz engaged RMS: H*6b82=%.3f  6b7e=%.3f  total=%.3f'
                      '   a_filt/a = %.4f   pedestal share = %.4f'
                      % (nm, r82, r7e, tot, r82 / tot if tot else np.nan,
                         r7e / tot if tot else np.nan))
            except Exception as ex:
                print('   %s Hz: %s' % (nm, ex))
        rows.append(dict(route=rt, build=R['build'], p50=float(np.percentile(e, 50)),
                         p95=float(np.percentile(e, 95)), p99=float(np.percentile(e, 99)),
                         mx=float(e.max()), crit_k=float(ce.min()),
                         a_p50=float(np.percentile(R['aq'][eng], 50) / 1024),
                         step_duty=float(R['step'][eng].mean())))
    print('\n' + '=' * 96)
    print('CROSS-ROUTE SUMMARY')
    print('%-6s %-7s %8s %8s %8s %8s %10s %8s %10s' % ('route', 'build', 'p50', 'p95', 'p99',
                                                       'max', 'crit k', 'a p50', 'step duty'))
    for r in rows:
        print('%-6s %-7s %8.0f %8.0f %8.0f %8.0f %10.2f %8.4f %10.6f'
              % (r['route'], r['build'], r['p50'], r['p95'], r['p99'], r['mx'],
                 r['crit_k'], r['a_p50'], r['step_duty']))
    json.dump(rows, open(HERE / '_scratch/out/_clip_duty_summary.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
