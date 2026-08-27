"""THE ONE HYPOTHESIS THE RESULTANT R IS BLIND TO -- a PARAMETRIC subharmonic.

R = |mean exp(i.phi)| tests HARMONIC GENERATION (a nonlinearity making 2f from f), where phi is
single-valued.  A PARAMETRIC pump at 2f driving a subharmonic at f locks the subharmonic phase
only MODULO pi -- two stable states 180 deg apart -- and those CANCEL in R.  The standard fix is
the doubled-angle resultant

        R2 = |mean_w exp(2 i phi_w)|,      phi = arg(X(f)^2 . conj(X(2f)))

which is invariant to a pi flip.  Also reported: the pi-folded histogram concentration.

⚠ THIS MATTERS BECAUSE THE DOSE-SCALING ARGUMENT DOES NOT REFUTE THE PARAMETRIC DIRECTION.
  A harmonic must grow at least as fast as its fundamental (it does not: 1.93x vs 13.3x).
  But a parametric resonance is THRESHOLD-driven -- a 1.93x pump increase past threshold CAN
  produce a 13.3x subharmonic.  So the parametric reading survives D3b and needs its own test.
  Prior in the record: `memory/accord/builds/accord-v59-parametric-pump-marginal.md`, eps 0.013-0.169 vs a
  threshold of 0.147 -- MARGINAL, never resolved.
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
NPER = int(round(4 * L.FS))
f = np.fft.rfftfreq(NPER, 1 / L.FS)
WIN = np.hanning(NPER + 1)[:NPER]
SEL = np.flatnonzero((f >= 20.0) & (f < 25.0))
J2 = [int(np.argmin(np.abs(f - 2.0 * f[i]))) for i in SEL]


def wins(tag, sig, mask):
    d = L.load(tag); x = d[sig].astype(float)
    idx = np.flatnonzero(np.diff(mask.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(mask)]))
    tt = np.arange(NPER); A = np.vstack([tt, np.ones(NPER)]).T
    out = []
    for i in range(len(b) - 1):
        a0, b0 = b[i], b[i + 1]
        if not mask[a0] or (b0 - a0) < NPER:
            continue
        for s in range(a0, b0 - NPER + 1, NPER // 2):
            xs = x[s:s + NPER]
            if not np.all(np.isfinite(xs)):
                continue
            xs = xs - A @ np.linalg.lstsq(A, xs, rcond=None)[0]
            out.append(np.fft.rfft(xs * WIN))
    return np.array(out) if out else np.zeros((0, len(f)), complex)


def stats(X):
    phs = []
    for k, i in enumerate(SEL):
        tri = X[:, i] ** 2 * np.conj(X[:, J2[k]])
        phs.append(tri / (np.abs(tri) + 1e-30))
    p = np.concatenate(phs)
    return float(np.abs(p.mean())), float(np.abs((p ** 2).mean()))


print("=" * 112)
print("R  = single-angle resultant (harmonic generation).  R2 = doubled-angle (pi-ambiguous,")
print("     catches a PARAMETRIC subharmonic).  Null = 400 cross-window shuffles, per arm.")
print("=" * 112)
print("%26s %6s %9s %9s %11s %11s %9s %9s" %
      ('arm', 'nw', 'R', 'R2', 'null R p95', 'null R2 p95', 'p(R)', 'p(R2)'))
rng = np.random.default_rng(77)
for nm, tag, hi in (('STOCK 1x  ENG', 'r97', False), ('STOCK 1x  ENG>=60', 'r97', True),
                    ('V102 6x   ENG', 'r96', False), ('V102 6x   ENG>=60', 'r96', True),
                    ('V103 6x   ENG', 'r9e', False), ('V103 6x   ENG>=60', 'r9e', True),
                    ('V103 6x   MANUAL', 'r9e', None)):
    d = L.load(tag); e = d['cc_lat'] > 0.5; v = d['v_rear'].astype(float) * KPH
    m = (~e) if hi is None else (e & (v >= 60) if hi else e)
    X = wins(tag, 'rate_f', m)
    if X.shape[0] < 10:
        print("%26s %6d  (too few windows)" % (nm, X.shape[0])); continue
    R, R2 = stats(X)
    nR, nR2 = [], []
    for _ in range(400):
        Y = X.copy(); perm = rng.permutation(X.shape[0])
        for k in range(len(SEL)):
            Y[:, J2[k]] = X[perm, J2[k]]
        a, b = stats(Y); nR.append(a); nR2.append(b)
    nR, nR2 = np.array(nR), np.array(nR2)
    print("%26s %6d %9.4f %9.4f %11.4f %11.4f %9.4f %9.4f"
          % (nm, X.shape[0], R, R2, np.percentile(nR, 95), np.percentile(nR2, 95),
             (nR >= R).mean(), (nR2 >= R2).mean()))
print()
print("  A parametric subharmonic would show R ~ null but R2 CLEARLY ABOVE its null.")
