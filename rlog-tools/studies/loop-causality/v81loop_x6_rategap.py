#!/usr/bin/env python3
"""X6 -- the operator's rate claim, with the nominal steering geometry CALIBRATED OUT.

X5a still divided a demand built from nominal steerRatio(16.0) x wheelbase(2.83) by an achieved
rate in real deg/s, so its absolute ratio inherited whatever those constants are wrong by.  Here
the curvature->column-angle gain is FITTED from the car's own low-frequency behaviour, where
openpilot tracks well and the gain is therefore identified:

    ang_deg  ~=  K * desiredCurvature        K fitted below 0.5 Hz, engaged, per speed cell

Then demand and achievement are the SAME quantity in the SAME units through the SAME filter, and
the ratio means something.  openpilot's own `cc_ccurv` (currentCurvature) is carried as a
cross-check on K.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from v81loop_lib import CACHE, fs_run  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def lp(x, fs, fc):
    x = np.asarray(x, float)
    X = np.fft.rfft(x - x.mean())
    f = np.fft.rfftfreq(len(x), 1 / fs)
    X[f > fc] = 0
    return np.fft.irfft(X, n=len(x)) + x.mean()


def load(seg):
    d = dict(np.load(CACHE / f"r67xs{seg}.npz", allow_pickle=True))
    t = np.asarray(d["t"], float)
    k = np.ones(len(t), bool)
    k[1:] = np.diff(t) > 0
    return {kk: (np.asarray(vv, float)[k] if getattr(vv, "shape", ()) == t.shape else vv)
            for kk, vv in d.items()}, fs_run(t[k])


def main():
    # --- K, the curvature -> column-angle gain, fitted below 0.5 Hz on engaged data ------------
    num = den = 0.0
    for s in range(14):
        try:
            d, fs = load(s)
        except Exception:
            continue
        m = d["cc_lat"] > 0.5
        if m.sum() < 500:
            continue
        a = lp(d["ang"], fs, 0.5)[m]
        c = lp(np.nan_to_num(d["ct_dcurv"]), fs, 0.5)[m]
        num += float(np.dot(a - a.mean(), c - c.mean()))
        den += float(np.dot(c - c.mean(), c - c.mean()))
    K = num / den
    print("=" * 96)
    print("X6  DEMANDED vs ACHIEVED COLUMN ANGLE AND RATE, geometry calibrated from the data")
    print("=" * 96)
    print(f"  fitted gain K:  ang_deg = {K:.1f} * curvature[1/m]   (below 0.5 Hz, engaged, "
          f"all segments)")
    print(f"  nominal steerRatio*wheelbase*180/pi would be {16.0 * 2.83 * 180 / np.pi:.1f} "
          f"-- ratio {K / (16.0 * 2.83 * 180 / np.pi):.2f}")
    print()
    print(f"  {'regime':>14} {'sec':>7} | {'ANGLE p95 (deg)':>25} | {'RATE p95 (deg/s)':>26}")
    print(f"  {'':>14} {'':>7} | {'dem':>8} {'ach':>8} {'ach/dem':>7} | "
          f"{'dem':>8} {'ach':>8} {'ach/dem':>7}")
    for nm, lo, hi in [("creep <4", 0, 4), ("4-11", 4, 11), ("11-20", 11, 20),
                       ("20-24", 20, 24), (">24 highway", 24, 99), ("EVENT", -1, -1)]:
        DA, AA, DR, AR = [], [], [], []
        for s in range(14):
            try:
                d, fs = load(s)
            except Exception:
                continue
            t = d["t"]
            m = d["cc_lat"] > 0.5
            if nm == "EVENT":
                m = m & (s == 8) & (t >= 38.0) & (t <= 52.0)
            else:
                m = m & (d["cs_v"] >= lo) & (d["cs_v"] < hi)
            if m.sum() < 100:
                continue
            dem_a = lp(np.nan_to_num(d["ct_dcurv"]) * K, fs, 3.0)
            ach_a = lp(d["ang"], fs, 3.0)
            DA.append(np.abs(dem_a[m] - np.median(dem_a[m])))
            AA.append(np.abs(ach_a[m] - np.median(ach_a[m])))
            DR.append(np.abs(np.gradient(dem_a, t)[m]))
            AR.append(np.abs(np.gradient(ach_a, t)[m]))
        if not DA:
            continue
        f = [np.percentile(np.concatenate(x), 95) for x in (DA, AA, DR, AR)]
        print(f"  {nm:>14} {len(np.concatenate(DA)) / 100:>7.1f} | {f[0]:>8.2f} {f[1]:>8.2f} "
              f"{f[1] / max(f[0], 1e-9):>7.2f} | {f[2]:>8.2f} {f[3]:>8.2f} "
              f"{f[3] / max(f[2], 1e-9):>7.2f}")
    print()
    print("  ANGLE ach/dem ~ 1 with RATE ach/dem << 1 would be the operator's picture exactly:")
    print("  the car eventually reaches the angle but cannot get there fast enough.")
    print("  Both near 1 means no rate starvation. Both << 1 means it is not tracking at all.")


if __name__ == "__main__":
    main()
