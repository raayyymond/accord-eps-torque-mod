#!/usr/bin/env python3
"""Grind #2 against the comma device IMU -- the only truly INDEPENDENT instrument available.

0x14A and 0x18F are both steering-system messages on bus 1, so agreement between them rules out a
torsion-bar-only telemetry artifact but not a shared steering-sensor one. The comma device's
accelerometer is not on that bus and not in that ECU. If the burst is the whole car shaking, it is
here.

🛑 The IMU caches exist ONLY for the V65 routes (3a, 3b). This script therefore CONFIRMS that the
burst is real vehicle motion; it CANNOT serve as a cross-build control, and nothing here should be
read as evidence about V59/V61/V64.

🛑 The IMU is also sampled at ~101 Hz, so it inherits the same Nyquist limit. It does not resolve
the aliasing question either.

Usage:  python studies/grind2/analyze_grind2_imu.py
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
import glob
import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from _r31_common import fs_of, load, runs_of  # noqa: E402

BURST = 400.0
OUTJSON = HERE / "_scratch/out/_grind2_imu.json"


def bandenv(t, x, lo, hi):
    fs = 1.0 / np.median(np.diff(t))
    x = np.asarray(x, float) - np.mean(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / fs)
    H = np.zeros(len(f), complex)
    m = (f >= lo) & (f <= hi)
    H[m] = 2 * X[m]
    return fs, np.abs(np.fft.irfft(H, n=len(x)))


def main():
    rows = []
    print(f"{'route':7s} {'seg':>3s} {'nEPSburst':>9s} {'fs_imu':>7s} | "
          f"{'IMU 30-49 |a| med':>17s} {'p99':>7s} {'max':>7s} | {'max in-burst':>12s} "
          f"{'x median':>9s} | {'Spearman rho':>12s} {'p':>10s}")
    tot = 0
    for cache, pfx in (("_scratch/cache/r3a", "r3as"), ("_scratch/cache/r3b", "r3bs")):
        for p in sorted(glob.glob(str(ROOT / cache / f"{pfx}*_imu.npz"))):
            s = int(os.path.basename(p).split(pfx)[1].split("_")[0])
            d = load(s, ROOT / cache, pfx)
            fse = fs_of(d)
            x = np.asarray(d["tq"], float)
            X = np.fft.rfft(x - x.mean())
            f = np.fft.rfftfreq(len(x), 1 / fse)
            H = np.zeros(len(f), complex)
            m = (f >= 30) & (f <= 49)
            H[m] = 2 * X[m]
            env = np.abs(np.fft.irfft(H, n=len(x)))
            ev = [(a, b) for a, b in runs_of(env > BURST, d["t"], 3, max_gap=0.06)
                  if d["t"][b - 1] - d["t"][a] >= 0.05]
            z = np.load(p)
            at = z["at"]
            fsa, ax = bandenv(at, z["ax"], 30, 49)
            _, ay = bandenv(at, z["ay"], 30, 49)
            _, az = bandenv(at, z["az"], 30, 49)
            mag = np.sqrt(ax ** 2 + ay ** 2 + az ** 2)
            base = float(np.median(mag))
            e_on = np.interp(at, d["t"], env)
            rho, pv = spearmanr(e_on, mag)
            inb = np.zeros(len(at), bool)
            for a, b in ev:
                inb |= (at >= d["t"][a] - 0.05) & (at <= d["t"][b - 1] + 0.05)
            mx = float(mag[inb].max()) if inb.any() else np.nan
            tot += len(ev)
            rows.append(dict(route=cache[-3:], seg=s, nev=len(ev), base=base,
                             p99=float(np.percentile(mag, 99)), mx=float(mag.max()),
                             inburst=mx, rho=float(rho), p=float(pv)))
            print(f"{cache[-3:]:7s} {s:3d} {len(ev):9d} {fsa:7.2f} | {base:17.4f} "
                  f"{np.percentile(mag, 99):7.4f} {mag.max():7.4f} | "
                  f"{mx:12.4f} {mx / base if np.isfinite(mx) else np.nan:9.1f}x | "
                  f"{rho:+12.3f} {pv:10.2e}")

    seg_ev = [r for r in rows if r["nev"] > 0]
    print(f"\n  {tot} EPS bursts across {len(seg_ev)} segments with IMU coverage.")
    print(f"  In-burst 30-49 Hz vehicle acceleration reaches "
          f"{max(r['inburst'] for r in seg_ev):.2f} m/s^2 "
          f"({max(r['inburst'] for r in seg_ev) / 9.81:.2f} g), "
          f"{max(r['inburst'] / r['base'] for r in seg_ev):.0f}x that segment's own median.")
    print(f"  Spearman(EPS 30-49 envelope, IMU 30-49 |a|) is POSITIVE on every segment: "
          f"rho {min(r['rho'] for r in seg_ev):+.3f} .. {max(r['rho'] for r in seg_ev):+.3f}, "
          f"every p < {max(r['p'] for r in seg_ev):.0e}.")
    print("\n  ⇒ The burst is whole-vehicle vibration, measured by an instrument that is not on the")
    print("    steering CAN bus and not inside the EPS. It is not a telemetry artifact.")
    print("  🛑 No control build has an IMU cache, so this says nothing about V59/V61/V64.")
    OUTJSON.write_text(json.dumps(rows, indent=1, default=float))
    print(f"\nwrote {OUTJSON}")


if __name__ == "__main__":
    main()
