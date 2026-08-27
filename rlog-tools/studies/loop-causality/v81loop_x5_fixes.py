#!/usr/bin/env python3
"""X5 -- two corrections to X4/X2 that change what the numbers mean.

  X5a  BANDWIDTH-MATCHED rate comparison.  X4 low-passed the DEMAND at 3 Hz (a raw derivative of
       a 27 Hz-noisy curvature is all noise) but left the ACHIEVED rate broadband.  At highway the
       achieved p95 is then dominated by the 27.5 Hz buzz itself -- +-87 deg/s of oscillation
       counted as if it were manoeuvre rate.  That is why '>24 m/s' came out at ach/dem = 1.23
       while every other regime sat at 0.06-0.28.  Both sides are filtered to 3 Hz here.

  X5b  THE ORDER VETO WITH A REAL SPEED LEVER ARM.  Inside the event, speed spans 2.2 m/s and is
       98.4% correlated with time, so df/dv there is nearly unidentifiable.  Across builds and
       speed cells the lever arm is 14.8 -> 28.4 m/s, nearly a doubling, and the line's frequency
       is located in a FREE band (5-45 Hz) so it is not pinned inside 22-34 by construction.
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
from v81loop_lib import (CACHE, FS_NOM, band_env, fs_run, locate,  # noqa: E402
                         prom_spectrum)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2].parent
NF, HOP = 256, 128
RATE_FIX = 1.25
BUILDS = [("V81/r67", ROOT / "_scratch/cache/r67x", "r67xs", list(range(14))),
          ("V80/r66", ROOT / "_scratch/cache/r66x", "r66xs", list(range(15))),
          ("V76/r65", ROOT / "_scratch/cache/r65", "r65s", list(range(14)))]


def lp(x, fs, fc):
    x = np.asarray(x, float)
    X = np.fft.rfft(x - x.mean())
    f = np.fft.rfftfreq(len(x), 1 / fs)
    X[f > fc] = 0
    return np.fft.irfft(X, n=len(x)) + x.mean()


def main():
    print("=" * 100)
    print("X5a  DEMANDED vs ACHIEVED COLUMN RATE, both band-limited to 3 Hz")
    print("=" * 100)
    print(f"  {'regime':>14} {'sec':>7} {'p50 dem':>9} {'p95 dem':>9} {'p50 ach':>9} "
          f"{'p95 ach':>9} {'p95 ach/dem':>12} {'p95 ach RAW':>12}")
    SR, WB = 16.0, 2.83
    for nm, lo, hi in [("creep <4", 0, 4), ("4-11", 4, 11), ("11-20", 11, 20),
                       ("20-24", 20, 24), (">24 highway", 24, 99), ("EVENT", -1, -1)]:
        D, A, Ar = [], [], []
        for s in range(14):
            p = CACHE / f"r67xs{s}.npz"
            if not p.exists():
                continue
            d = dict(np.load(p, allow_pickle=True))
            t = np.asarray(d["t"], float)
            keep = np.ones(len(t), bool)
            keep[1:] = np.diff(t) > 0
            m = keep & (d["cc_lat"] > 0.5)
            if nm == "EVENT":
                m &= (s == 8) & (t >= 38.0) & (t <= 52.0)
            else:
                m &= (d["cs_v"] >= lo) & (d["cs_v"] < hi)
            if m.sum() < 50:
                continue
            fs = fs_run(t[keep])
            tk = t[keep]
            dcv = np.nan_to_num(np.asarray(d["ct_dcurv"], float))[keep]
            dem = np.gradient(lp(dcv, fs, 3.0), tk) * d["cs_v"][keep] * SR * WB * 180 / np.pi
            ach_raw = np.asarray(d["rate_f"], float)[keep] * RATE_FIX
            ach = lp(ach_raw, fs, 3.0)          # 🛑 the fix: SAME bandwidth on both sides
            sel = m[keep]
            D.append(np.abs(dem[sel])); A.append(np.abs(ach[sel])); Ar.append(np.abs(ach_raw[sel]))
        if not D:
            continue
        D, A, Ar = np.concatenate(D), np.concatenate(A), np.concatenate(Ar)
        print(f"  {nm:>14} {len(D) / 100:>7.1f} {np.percentile(D, 50):>9.2f} "
              f"{np.percentile(D, 95):>9.2f} {np.percentile(A, 50):>9.2f} "
              f"{np.percentile(A, 95):>9.2f} "
              f"{np.percentile(A, 95) / max(np.percentile(D, 95), 1e-9):>12.2f} "
              f"{np.percentile(Ar, 95):>12.2f}")
    print("  The last column is the UNFILTERED achieved p95 -- the gap between it and the filtered")
    print("  one at highway IS the 27.5 Hz oscillation being counted as manoeuvre rate.")

    print()
    print("=" * 100)
    print("X5b  ORDER VETO with a 14.8 -> 28.4 m/s lever arm, line located in a FREE 5-45 Hz band")
    print("=" * 100)
    cells = [(6, 11), (11, 16), (16, 20), (20, 24), (24, 99)]
    print(f"  {'build':>9} {'v cell':>10} {'nwin':>5} {'mean v':>7} {'med f0 FREE':>12} "
          f"{'med f0 22-34':>13} {'ord1':>6} {'ord2':>6} {'ord3':>6} {'med e2432':>10}")
    pts = []
    for nm, cache, pfx, segs in BUILDS:
        for lo, hi in cells:
            F, G, V, E = [], [], [], []
            for s in segs:
                p = cache / f"{pfx}{s}.npz"
                if not p.exists():
                    continue
                d = dict(np.load(p, allow_pickle=True))
                if "cc_lat" not in d:
                    continue
                t = np.asarray(d["t"], float)
                fs = fs_run(t)
                eng = d["cc_lat"] > 0.5
                x = np.asarray(d["tq"], float)
                for i in range(0, len(t) - NF + 1, HOP):
                    sl = slice(i, i + NF)
                    if eng[sl].mean() < 0.95:
                        continue
                    vm = float(np.mean(d["cs_v"][sl]))
                    if not (lo <= vm < hi):
                        continue
                    xw = x[sl]
                    P = np.abs(np.fft.rfft((xw - xw.mean()) * np.hanning(NF))) ** 2
                    f = np.fft.rfftfreq(NF, 1 / fs)
                    R = prom_spectrum(f, P)
                    e = band_env(xw, fs, 24, 32)
                    if e < 300:            # only windows that actually HAVE the mode
                        continue
                    F.append(locate(f, P, 5.0, 45.0, R=R)[0])
                    G.append(locate(f, P, 22.0, 34.0, R=R)[0])
                    V.append(vm); E.append(e)
            if len(F) < 4:
                continue
            mv = float(np.mean(V))
            print(f"  {nm:>9} {f'{lo}-{hi}':>10} {len(F):>5} {mv:>7.1f} "
                  f"{np.median(F):>12.2f} {np.median(G):>13.2f} "
                  f"{mv / 2.073:>6.2f} {2 * mv / 2.073:>6.2f} {3 * mv / 2.073:>6.2f} "
                  f"{np.median(E):>10.1f}")
            pts.append((mv, float(np.median(G)), len(F)))
    if len(pts) >= 3:
        V = np.array([p[0] for p in pts]); F = np.array([p[1] for p in pts])
        W = np.array([p[2] for p in pts], float)
        sl_, ic = np.polyfit(V, F, 1, w=np.sqrt(W))
        print(f"\n  pooled across builds and cells ({len(pts)} cells, "
              f"v {V.min():.1f}-{V.max():.1f} m/s):")
        print(f"    df/dv = {sl_:+.4f} Hz per m/s   intercept {ic:+.2f} Hz")
        print(f"    wheel order 1 predicts {1 / 2.073:+.4f}, order 2 {2 / 2.073:+.4f}, "
              f"order 3 {3 / 2.073:+.4f} Hz per m/s")
        print(f"    over the {np.ptp(V):.1f} m/s span, order 2 would move the line "
              f"{2 * np.ptp(V) / 2.073:+.1f} Hz; observed {sl_ * np.ptp(V):+.1f} Hz")
    print("  🛑 windows are filtered to those with a 24-32 Hz bar envelope > 300 counts, i.e. the")
    print("     mode is actually present. Without that filter the 'line' in a quiet window is")
    print("     whatever noise peak the locator finds, and the regression measures nothing.")


if __name__ == "__main__":
    main()
