#!/usr/bin/env python3
"""V62 route-37: presence-test the three lines that the free locator actually found, and ask
whether each is NEW relative to every earlier cached build.

The free-locator pass (studies/sessions/r37/analyze_r37_newgrind.py) found three things and nothing else:

    RATCHET   ~7.3 Hz   enormous at v<2.5 m/s with the LKAS command railed
    MODE      ~20.9 Hz  the known grinding mode
    HARM      ~41.9 Hz  = 2.00 x MODE, only during one violent burst

Now that the frequencies are KNOWN, a tracking band is the right instrument (a strict band
presence-TESTS a known f0; it cannot locate one -- which is why it was not used first).

Also computes partial Spearman correlations, because |e4tq| and vEgo are themselves strongly
coupled on this route (tight low-speed turns produce big commands), so the raw rho of +0.750 for
env_mode vs |e4tq| cannot by itself say which variable the symptom keys on.
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
import sys
from pathlib import Path

import numpy as np
from scipy.stats import rankdata, spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import _r31_common as C  # noqa: E402

NF = 256
RATCHET = (6.3, 8.3)
MODE = (19.4, 22.4)
HARM = (39.9, 43.9)

ROUTES = [
    ("2b", C.ROOT / "_scratch/cache/r2b", "r2bs", [0, 1, 2, 11, 12, 13]),
    ("2c", C.ROOT / "_scratch/cache/r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12]),
    ("31 (V61)", C.ROOT / "_scratch/cache/r31", "r31s", [0, 1, 2, 3]),
    ("35 (V64=V59)", C.ROOT / "_scratch/cache/r35", "r35s", [0, 1, 2]),
    ("37 (V62)", C.ROOT / "_scratch/cache/r37", "r37s", list(range(1, 15))),
]


def recs(cache, pfx, segs):
    out = []
    for s in segs:
        p = cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, cache, pfx)
        fs = C.fs_of(d)
        x = d["tq"]
        if len(x) < NF:
            continue
        env = {k: C.band_envelope(x, fs, *b)
               for k, b in (("rat", RATCHET), ("mode", MODE), ("harm", HARM))}
        f = np.fft.rfftfreq(NF, 1 / fs)
        for i in range(0, len(x) - NF + 1, 64):
            P = C.periodogram(x[i:i + NF], fs, NF)
            if P is None:
                continue
            sl = slice(i, i + NF)
            r = dict(seg=s, t0=float(d["t"][i]),
                     v=float(np.mean(d["cs_v"][sl])),
                     ang=float(np.mean(np.abs(d["ang"][sl]))),
                     eff=float(np.mean(np.abs(C.sustained(d["tq"][sl], fs)))),
                     e4=float(np.mean(np.abs(d["e4tq"][sl]))),
                     lat=float(np.mean(d["cc_lat"][sl] > 0.5)))
            for k, b in (("rat", RATCHET), ("mode", MODE), ("harm", HARM)):
                r["e_" + k] = float(np.percentile(env[k][sl], 99))
                r["f_" + k], r["p_" + k] = C.peak_prom(f, P, *b)
            out.append(r)
    return out


def cell(rs, **kw):
    o = rs
    for k, (lo, hi) in kw.items():
        o = [r for r in o if lo <= r[k] < hi]
    return o


def summ(rs, k):
    v = np.array([r[k] for r in rs], float)
    v = v[np.isfinite(v)]
    if not len(v):
        return "n=0"
    return f"{np.median(v):8.1f} p90={np.percentile(v,90):8.1f} max={v.max():8.1f}"


def partial(x, y, z):
    """Spearman partial correlation of x,y controlling for the columns of z (rank-linear)."""
    X, Y = rankdata(x), rankdata(y)
    Z = np.column_stack([rankdata(c) for c in z] + [np.ones(len(x))])
    bx = np.linalg.lstsq(Z, X, rcond=None)[0]
    by = np.linalg.lstsq(Z, Y, rcond=None)[0]
    rx, ry = X - Z @ bx, Y - Z @ by
    n, k = len(x), Z.shape[1]
    r = float(np.corrcoef(rx, ry)[0, 1])
    dfree = max(n - k - 1, 1)
    t = r * np.sqrt(dfree / max(1 - r * r, 1e-12))
    return r, dfree, t


def main():
    store = {name: recs(c, p, s) for name, c, p, s in ROUTES}

    print("TRACKING-BAND ENVELOPE p99 (counts) at MATCHED conditions, all cached builds.")
    print("Bands: ratchet 6.3-8.3 Hz | mode 19.4-22.4 Hz | harmonic 39.9-43.9 Hz\n")
    for lbl, kw in (
            ("engaged, v 0-2.5 m/s  (creep / parking)", dict(v=(0.0, 2.5), lat=(0.5, 1.1))),
            ("engaged, v 2.5-4 m/s", dict(v=(2.5, 4.0), lat=(0.5, 1.1))),
            ("engaged, v 4-10 m/s   (the NEW symptom's speed)", dict(v=(4.0, 10.0),
                                                                    lat=(0.5, 1.1))),
            ("engaged, v >14 m/s", dict(v=(14.0, 99.0), lat=(0.5, 1.1))),
            ("engaged, v 4-10, eff>=800 (NEW-SYMPTOM cell)", dict(v=(4.0, 10.0), lat=(0.5, 1.1),
                                                                 eff=(800, 1e9))),
    ):
        print(f"  --- {lbl} ---")
        print(f"      {'route':14s} {'n':>4s} | {'ratchet med/p90/max':>34s} | "
              f"{'mode med/p90/max':>34s} | {'harmonic med/p90/max':>34s}")
        for name in store:
            rs = cell(store[name], **kw)
            if not rs:
                print(f"      {name:14s} {0:4d} | (no windows)")
                continue
            print(f"      {name:14s} {len(rs):4d} | {summ(rs,'e_rat')} | {summ(rs,'e_mode')} | "
                  f"{summ(rs,'e_harm')}")
        print()

    # ---- frequency of each line on route 37, with scatter ------------------------------------
    r37 = store["37 (V62)"]
    print("Route 37 line frequencies (windows where that band's prominence >= 10):")
    for k, b in (("rat", RATCHET), ("mode", MODE), ("harm", HARM)):
        sel = [r for r in r37 if np.isfinite(r["p_" + k]) and r["p_" + k] >= 10]
        if not sel:
            print(f"  {k:5s} band {b}: n=0")
            continue
        fv = np.array([r["f_" + k] for r in sel])
        print(f"  {k:5s} band {b[0]}-{b[1]} Hz: n={len(sel):4d}  f0 median {np.median(fv):6.2f} "
              f"sd {fv.std(ddof=1):5.2f}  IQR {np.percentile(fv,25):.2f}-"
              f"{np.percentile(fv,75):.2f}  median prom {np.median([r['p_'+k] for r in sel]):.1f}")

    # ---- partial correlations ----------------------------------------------------------------
    eng = [r for r in r37 if r["lat"] > 0.5]
    print(f"\nPARTIAL SPEARMAN, engaged windows on route 37 (n={len(eng)}).")
    print("  Raw rho, then rho controlling for the other three predictors.")
    print(f"  {'response':10s} {'predictor':10s} {'raw rho':>9s} {'partial':>9s} {'df':>5s} "
          f"{'t':>8s}")
    preds = ("v", "ang", "eff", "e4")
    for resp in ("e_mode", "e_rat", "e_harm"):
        y = np.array([r[resp] for r in eng])
        for k in preds:
            x = np.array([r[k] for r in eng])
            others = [np.array([r[o] for r in eng]) for o in preds if o != k]
            raw = spearmanr(x, y).statistic
            pr, dfree, t = partial(x, y, others)
            print(f"  {resp:10s} {k:10s} {raw:+9.3f} {pr:+9.3f} {dfree:5d} {t:+8.2f}")
    print("  |t| > 3.3 corresponds to p < 0.001 at these df.")


if __name__ == "__main__":
    main()
