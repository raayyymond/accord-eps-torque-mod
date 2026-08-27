#!/usr/bin/env python3
r"""studies/v102-crossbuild/v102_endpoint_reconcile.py -- WHY DO TWO AGENTS GET 2.982 AND 1.003 FOR THE SAME ENDPOINT?

`route-stock` and I measured the same pre-registered quantity -- within-route `tq`
band-RMS(21.5-25.5) / band-RMS(2.5-4.5), median over engaged windows -- and agree within 10-20 %
on STOCK, V100 and V101 but disagree **3x on V102**, the arm that carries the verdict.  That is a
specific reason to think one of us is wrong, so it gets re-derived.

THE TWO ESTIMATORS ARE GENUINELY DIFFERENT:

  MINE   `score/r95_v102_prereg.py` lineage (the one that produced the record's 5.07 / 0.62)
         * NATIVE event-driven `t` grid, no resampling
         * brick-wall FFT band-pass applied to the WHOLE engaged run, then 1 s RMS sub-windows
         * no speed-spread filter, no per-window purity filter

  THEIRS `v102_xb_lib.windows()` lineage (the one `score/score_v102.py` uses)
         * UNIFORM 100 Hz resampled grid, gap-split at 50 ms
         * 2.56 s Hann window, Parseval-normalised band-RMS, per window
         * `vspread_kmh = 8.0` -- REJECTS any window whose speed range exceeds 8 km/h
         * `purity >= 0.98`

Both are defensible.  This file turns the knobs ONE AT A TIME so the fork is located rather than
argued about.
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

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import v102_xb_lib as L      # noqa: E402
import score_v102_full as F  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

for _r, _lab in (("96", "V102"), ("97", "V9b-STOCK")):
    if _r not in L.ROUTES:
        L.ROUTES[_r] = L._mk(_r, _lab, gain=0, clamp=0, leverB=False, idcode=0, bits="x")

ARMS = [("97", "STOCK 1x"), ("85", "V100 4x"), ("96", "V102 6x"), ("95", "V101 8x")]
TGT, CTL = (21.5, 25.5), (2.5, 4.5)


def uniform_estimator(route, nfft, vspread, purity=0.98, ch="tq"):
    """THEIR path: uniform grid, Hann, Parseval band-RMS.  vspread=None disables the filter."""
    win = np.hanning(nfft)
    vals, vs = [], []
    for blk in L.all_blocks(route):
        eng = blk["cc_lat"] > 0.5
        idx = np.nonzero(np.diff(eng.astype(int)) != 0)[0] + 1
        bounds = [0] + list(idx) + [len(eng)]
        for a, b in zip(bounds[:-1], bounds[1:]):
            if not eng[a] or (b - a) < nfft:
                continue
            for s in range(a, b - nfft + 1, nfft // 2):
                sl = slice(s, s + nfft)
                if eng[sl].mean() < purity:
                    continue
                v = blk["v_rear"][sl] * 3.6
                if vspread is not None and (v.max() - v.min()) > vspread:
                    continue
                num = L.bandrms(blk[ch][sl], L.FS, TGT[0], TGT[1], win)
                den = L.bandrms(blk[ch][sl], L.FS, CTL[0], CTL[1], win)
                if den > 0:
                    vals.append(num / den)
                    vs.append(float(np.median(v)))
    return np.array(vals), np.array(vs)


def native_estimator(route, wl_s, ch="tq"):
    """MY path: native grid, band-pass the whole run, then wl_s-second RMS sub-windows."""
    z = dict(np.load(ROOT / "analysis-2020accord" / F.NPZ[route], allow_pickle=True))
    t = np.asarray(z["t"], float)
    FS = 1.0 / np.median(np.diff(t))
    lat = np.asarray(z["cc_lat"], float) > 0.5
    vk = np.abs(np.asarray(z["cs_v"], float)) * 3.6
    WL = int(round(wl_s * FS))
    vals, vs = [], []
    for a, b in F.runs_break(lat, t, WL):
        n_ = F.bp(np.asarray(z[ch], float), a, b, FS, *TGT)
        d_ = F.bp(np.asarray(z[ch], float), a, b, FS, *CTL)
        for i in range(0, (b - a) - WL + 1, WL):
            sl = slice(i, i + WL)
            den = np.sqrt(np.mean(d_[sl] ** 2))
            if den > 0:
                vals.append(np.sqrt(np.mean(n_[sl] ** 2)) / den)
                vs.append(float(np.median(vk[a:b][sl])))
    return np.array(vals), np.array(vs)


if __name__ == "__main__":
    print("=" * 104)
    print("MEDIAN of within-route tq shape (21.5-25.5 / 2.5-4.5), engaged.  n in brackets.")
    print("=" * 104)
    rows = [
        ("MINE   native band-pass, 1.00 s", lambda r: native_estimator(r, 1.00)),
        ("MINE   native band-pass, 2.56 s", lambda r: native_estimator(r, 2.56)),
        ("THEIRS uniform Hann 2.56 s, vspread 8", lambda r: uniform_estimator(r, 256, 8.0)),
        ("THEIRS uniform Hann 2.56 s, NO vspread", lambda r: uniform_estimator(r, 256, None)),
        ("THEIRS uniform Hann 1.00 s, vspread 8", lambda r: uniform_estimator(r, 100, 8.0)),
        ("THEIRS uniform Hann 1.00 s, NO vspread", lambda r: uniform_estimator(r, 100, None)),
    ]
    print("    %-40s %s" % ("estimator", "".join("%18s" % lab for _, lab in ARMS)))
    RES = {}
    for name, fn in rows:
        line = "    %-40s" % name
        for r, lab in ARMS:
            v, vs = fn(r)
            RES[(name, r)] = (v, vs)
            line += "%18s" % ("%.3f [%d]" % (np.median(v), len(v)) if len(v) else "--")
        print(line)

    print("\n" + "=" * 104)
    print("WHERE DOES V102 LOSE ITS SIGNAL?  Speed census of the windows each estimator KEEPS.")
    print("(V102's shape rises steeply with speed, so any filter that drops highway windows")
    print(" lowers its median -- and V102 is the only arm with a lot of highway.)")
    print("=" * 104)
    EDG = [0, 20, 40, 70, 95, 200]
    for name, _ in rows:
        print("\n  %s" % name)
        for r, lab in ARMS:
            v, vs = RES[(name, r)]
            if not len(v):
                continue
            cens = "  ".join("%d-%d:%d(m=%.2f)" % (
                EDG[i], EDG[i + 1], int(((vs >= EDG[i]) & (vs < EDG[i + 1])).sum()),
                np.median(v[(vs >= EDG[i]) & (vs < EDG[i + 1])])
                if ((vs >= EDG[i]) & (vs < EDG[i + 1])).sum() else np.nan)
                for i in range(len(EDG) - 1))
            print("    %-10s n=%-5d  %s" % (lab, len(v), cens))

    print("\n" + "=" * 104)
    print("THE RATIO THAT ACTUALLY DECIDES: V102 / V101, under every estimator.")
    print("(A within-route statistic self-normalises for level, so the RATIO is what survives")
    print(" a change of estimator -- if the verdict is robust, this column barely moves.)")
    print("=" * 104)
    for name, _ in rows:
        a = RES[(name, "95")][0]
        b = RES[(name, "96")][0]
        c = RES[(name, "85")][0]
        d = RES[(name, "97")][0]
        if not (len(a) and len(b)):
            continue
        print("    %-40s  V102/V101 = %5.3f   V100/V101 = %5.3f   STOCK/V101 = %5.3f"
              % (name, np.median(b) / np.median(a), np.median(c) / np.median(a),
                 np.median(d) / np.median(a)))
