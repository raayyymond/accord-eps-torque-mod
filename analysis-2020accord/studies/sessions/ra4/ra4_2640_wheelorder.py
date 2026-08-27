"""IS ROUTE a4's HUGE 26-40 Hz FEATURE A BUILD EFFECT OR A WHEEL ORDER?

a4 shows 26-40 Hz at 5.16 deg/s (40-80 km/h) and 17.13 (80-130) vs STOCK's 0.54 / 0.30.
That is the PLACEBO band, where c4's model says ~0.99.  Before it is reported as anything,
the kit's own recurring trap must be excluded: `accord-869hz-line-is-wheel-order-not-v56`
and `accord-averaged-spectrum-needs-matched-speed-distributions`.

A wheel order tracks SPEED: f = n * v / C, C = 2.073-2.080 m.  At 100 km/h order 2 = 26.7 Hz
and order 3 = 40.1 Hz -- so 26-40 Hz at highway is EXACTLY where orders 2-3 live.
TEST: peak frequency inside 26-40 Hz vs speed.  A wheel order gives f/v = n/C = constant.
      A firmware mode does not move with speed.
CONTROLS: the manual arm (a wheel order is there too; a loop mode is not), and the same test
          on STOCK and V103.
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
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import _gate2_boost_lib as L

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

KPH = 3.6
NPER = int(round(8 * L.FS))                # 8 s -> 0.125 Hz bins, enough to resolve an order
f = np.fft.rfftfreq(NPER, 1 / L.FS)
WIN = np.hanning(NPER + 1)[:NPER]
U = (WIN ** 2).sum()
C_LO, C_HI = 2.073, 2.080                  # tyre circumference, m (accord-v57-confirms-wheel-order)


def windows(tag, engaged, vlo, vhi):
    d = L.load(tag)
    e = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    m = (e if engaged else ~e) & (v >= vlo) & (v < vhi)
    rate = d['rate_f'].astype(float)
    idx = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(m)]))
    tt = np.arange(NPER); M = np.vstack([tt, np.ones(NPER)]).T
    out = []
    for i in range(len(b) - 1):
        a0, b0 = b[i], b[i + 1]
        if (b0 - a0) < NPER or not m[a0]:
            continue
        for s in range(a0, b0 - NPER + 1, NPER // 2):
            if not m[s:s + NPER].all():
                continue
            xs = rate[s:s + NPER]
            if not np.all(np.isfinite(xs)):
                continue
            xs = xs - M @ np.linalg.lstsq(M, xs, rcond=None)[0]
            X = np.fft.rfft(xs * WIN)
            out.append(((X.conj() * X).real / (L.FS * U), float(np.mean(v[s:s + NPER]))))
    return out


print("=" * 108)
print("PEAK FREQUENCY INSIDE 26-40 Hz vs SPEED -- a wheel order gives f/v = n/C = CONSTANT")
print("=" * 108)
sel = (f >= 26) & (f < 40)
print("%8s %8s %6s %9s %9s %11s %11s %11s" %
      ('route', 'arm', 'nw', 'v mean', 'f peak', 'implied C', 'order @C=2.08', 'band RMS'))
for tag in ('ra4', 'r9e', 'r96', 'r97'):
    for arm, eng in (('ENG', True), ('MAN', False)):
        for vlo, vhi in ((40, 80), (80, 130)):
            W = windows(tag, eng, vlo, vhi)
            if len(W) < 3:
                continue
            vs = np.array([w[1] for w in W])
            S = sum(w[0] for w in W) / len(W)
            fp = f[sel][np.argmax(S[sel])]
            vm = vs.mean() / KPH                      # m/s
            order = fp * 2.08 / vm if vm > 1 else np.nan
            impC = round(order) * vm / fp if (vm > 1 and round(order) > 0) else np.nan
            rms = float(np.sqrt(S[sel].sum() * (f[1] - f[0])))
            print("%8s %8s %6d %9.1f %9.2f %11.3f %11.2f %11.4f"
                  % (tag, arm, len(W), vs.mean(), fp, impC, order, rms))
print()
print("  'order' = f_peak * 2.08 / v(m/s).  An INTEGER (2 or 3) with a consistent implied")
print("  circumference near 2.073-2.080 m across speed bands => WHEEL ORDER, i.e. TYRES.")
print()
print("=" * 108)
print("PER-WINDOW REGRESSION of f_peak on speed -- the decisive form")
print("=" * 108)
for tag in ('ra4', 'r97'):
    W = windows(tag, True, 30, 130)
    if len(W) < 8:
        continue
    fp = np.array([f[sel][np.argmax(w[0][sel])] for w in W])
    vs = np.array([w[1] / KPH for w in W])
    ok = vs > 8
    if ok.sum() < 8:
        continue
    A = np.vstack([vs[ok], np.ones(ok.sum())]).T
    sl, ic = np.linalg.lstsq(A, fp[ok], rcond=None)[0]
    pred = A @ np.array([sl, ic])
    r2 = 1 - ((fp[ok] - pred) ** 2).sum() / ((fp[ok] - fp[ok].mean()) ** 2).sum()
    print("  %s: f_peak = %.4f*v + %.2f   R2 = %.3f   n = %d windows" % (tag, sl, ic, r2, ok.sum()))
    print("       slope implies order/C = %.4f  =>  at C = 2.08 m that is order %.2f"
          % (sl, sl * 2.08))
print("  A wheel order predicts slope = n/C (0.962 for n=2, 1.442 for n=3) and intercept ~0.")
