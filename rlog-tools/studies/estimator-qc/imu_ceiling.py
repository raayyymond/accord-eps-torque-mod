#!/usr/bin/env python3
"""WHERE DOES THE IMU STOP BEING REAL?  Establish the usable ceiling BEFORE measuring anything.

`imu_vert`/`imu_lat` in every cache are `np.interp(t_can, t_accel, a)` -- LINEAR INTERPOLATION
from the accelerometer's own hardware timestamps onto the ~101 Hz CAN grid.  Linear interpolation
does NOT create information: above the accelerometer's own Nyquist the gridded signal carries
IMAGES of content from below it, not real content.  Three independent ways to find that fold:

  C1  SPECTRAL DIP.  Real content rolls off toward f_N; the image rises above it.  The minimum
      of the averaged spectrum locates f_N.
  C2  MIRROR TEST.  If it is an image, P(f) above the fold should track P(2*f_N - f) below it,
      window by window.  A real independent band would not.
  C3  COHERENCE WITH THE BAR.  Genuine mechanical transmission keeps bar-IMU coherence; an
      interpolation image has no physical partner and coherence collapses.
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
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import coherence, welch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
import v86_freq_test as V           # noqa: E402
import _r31_common as C31           # noqa: E402

ROOT = V.ROOT
O = {}
ROUTES = ("V86/r6f", "V85/r6e", "V86B/r70")


def segs_of(nm):
    cache, pfx, segs = V.ROUTES[nm]
    for s in segs:
        p = ROOT / cache / ("%s%d.npz" % (pfx, s))
        if p.exists():
            yield C31.load(s, ROOT / cache, pfx)


def main():
    V.hdr("C1  SPECTRAL DIP -- averaged engaged spectrum of the gridded IMU, 15-45 Hz.\n"
          "    Real content falls toward the accelerometer's Nyquist; the interpolation image\n"
          "    rises above it.  The MINIMUM locates the fold.")
    O["c1"] = {}
    for nm in ROUTES:
        acc = {}
        for d in segs_of(nm):
            t = np.asarray(d["t"], float)
            fs = C31.fs_of(d)
            lat = np.asarray(d["cc_lat"], float) > 0.5
            for a, b in C31.runs_of(lat, t, 2048):
                for key in ("imu_vert", "imu_lat"):
                    x = np.asarray(d[key], float)[a:b]
                    if not np.all(np.isfinite(x)):
                        continue
                    f, P = welch(x - x.mean(), fs=fs, nperseg=1024, noverlap=512)
                    acc.setdefault(key, []).append((f, P))
        for key, lst in acc.items():
            f = lst[0][0]
            P = np.mean([p for _, p in lst], axis=0)
            m = (f >= 18.0) & (f <= 34.0)
            j = int(np.argmin(np.where(m, P, np.inf)))
            O["c1"].setdefault(nm, {})[key] = dict(fold=float(f[j]), n=len(lst))
            print("    %-10s %-9s  n=%2d  spectral minimum at %6.2f Hz  =>  implied native "
                  "rate %6.2f Hz" % (nm, key, len(lst), f[j], 2 * f[j]))
            if key == "imu_vert":
                sel = [(lo, hi) for lo, hi in ((15, 18), (18, 21), (21, 24), (24, 27),
                                               (27, 30), (30, 33), (33, 36), (36, 40))]
                print("        band power: " + "  ".join(
                    "%d-%d:%.2e" % (lo, hi, P[(f >= lo) & (f < hi)].mean()) for lo, hi in sel))

    V.hdr("C2  MIRROR TEST.  If the >fold content is an interpolation IMAGE, then window by\n"
          "    window P(f) should track P(2*f_fold - f).  Spearman rho across windows, per\n"
          "    frequency pair.  A real independent band would show no such pairing.")
    O["c2"] = {}
    from scipy.stats import spearmanr
    for nm in ("V86/r6f",):
        rows = []
        for d in segs_of(nm):
            t = np.asarray(d["t"], float)
            fs = C31.fs_of(d)
            lat = np.asarray(d["cc_lat"], float) > 0.5
            for a, b in C31.runs_of(lat, t, 1024):
                for j0 in range(0, (b - a) - 1024 + 1, 512):
                    x = np.asarray(d["imu_vert"], float)[a:b][j0:j0 + 1024]
                    if not np.all(np.isfinite(x)):
                        continue
                    f, P = welch(x - x.mean(), fs=fs, nperseg=512, noverlap=256)
                    rows.append(P)
        if len(rows) < 8:
            print("    too few windows"); continue
        M = np.array(rows)
        fold = O["c1"][nm]["imu_vert"]["fold"]
        print("    fold = %.2f Hz, n = %d windows" % (fold, len(M)))
        print("    %10s %10s %10s %8s" % ("f above", "f mirror", "rho", "p"))
        for fa in (27.0, 29.0, 31.0, 33.0, 35.0):
            fm = 2 * fold - fa
            if fm < 3:
                continue
            ja = int(np.argmin(np.abs(f - fa))); jm = int(np.argmin(np.abs(f - fm)))
            rho, pv = spearmanr(M[:, ja], M[:, jm])
            print("    %10.2f %10.2f %10.3f %8.4f" % (f[ja], f[jm], rho, pv))
            O["c2"].setdefault(nm, []).append([float(f[ja]), float(f[jm]), float(rho), float(pv)])

    V.hdr("C3  COHERENCE bar -> IMU across frequency.  Genuine mechanical transmission keeps\n"
          "    coherence; an interpolation image has no physical partner.  This also tells us\n"
          "    where the transmissibility estimate is trustworthy AT ALL.")
    O["c3"] = {}
    for nm in ROUTES:
        acc = []
        for d in segs_of(nm):
            t = np.asarray(d["t"], float)
            fs = C31.fs_of(d)
            lat = np.asarray(d["cc_lat"], float) > 0.5
            for a, b in C31.runs_of(lat, t, 2048):
                x = np.asarray(d["tq"], float)[a:b]
                y = np.asarray(d["imu_vert"], float)[a:b]
                if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
                    continue
                f, Cxy = coherence(x - x.mean(), y - y.mean(), fs=fs, nperseg=512, noverlap=384)
                acc.append(Cxy)
        if not acc:
            continue
        Cm = np.mean(acc, axis=0)
        nseg = len(acc) * 7
        floor = 1.0 - 0.05 ** (1.0 / max(nseg - 1, 1))
        print("    %-10s n=%2d runs, coherence 95%% chance floor ~ %.3f" % (nm, len(acc), floor))
        cells = []
        for lo, hi in ((5, 8), (8, 11), (11, 14), (14, 17), (17, 20), (20, 23),
                       (23, 26), (26, 29), (29, 33), (33, 38), (38, 45)):
            m = (f >= lo) & (f < hi)
            cells.append("%d-%d:%.3f" % (lo, hi, Cm[m].mean()))
        print("        " + "  ".join(cells))
        O["c3"][nm] = dict(floor=float(floor), n=len(acc),
                           f=[float(x) for x in f], coh=[float(x) for x in Cm])

    (ROOT / "_scratch/cache/r6f" / "imu_ceiling.json").write_text(json.dumps(O, indent=1, default=float))
    print("\nwrote %s" % (ROOT / "_scratch/cache/r6f" / "imu_ceiling.json"))


if __name__ == "__main__":
    main()
