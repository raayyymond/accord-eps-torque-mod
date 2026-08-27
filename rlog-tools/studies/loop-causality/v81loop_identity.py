#!/usr/bin/env python3
"""S0.1b -- nail the channel identities before any phase number is quoted.

The survey threw two numbers that must not be accepted at face value:
    corr(tq, cs_tq)            = +0.60   (should be ~1: both are meant to be the torsion bar)
    corr(rate_f, d(ang)/dt)    = -0.38   (should be ~+0.9: rate_f is meant to be the fine rate copy)

Either the columns are mislabelled, or the discrepancy is a RESAMPLING artefact of the 27 Hz line
that only exists in segment 8.  Those two have opposite consequences for T1, so this file separates
them by repeating the same comparisons on a QUIET segment.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from v81loop_lib import band_env, fs_run, load_seg  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def report(s):
    d = load_seg(s)
    t = d["t"]
    fs = fs_run(t)
    ang, rc, rf, tq = d["ang"], d["rate_c"], d["rate_f"], d["tq"]
    dang = np.gradient(ang, t)
    hf = band_env(np.asarray(tq, float)[:4096], fs, 24, 32)
    print(f"\n--- seg {s}   fs {fs:.3f}   v {d['cs_v'].mean():.1f} m/s   "
          f"bar 24-32 Hz envelope {hf:.0f} counts ---")
    print(f"  corr(rate_c, rate_f)      = {np.corrcoef(rc, rf)[0, 1]:+.4f}")
    print(f"  corr(rate_c, d(ang)/dt)   = {np.corrcoef(rc, dang)[0, 1]:+.4f}")
    print(f"  corr(rate_f, d(ang)/dt)   = {np.corrcoef(rf, dang)[0, 1]:+.4f}")
    print(f"  corr(tq, cs_tq)           = {np.corrcoef(tq, d['cs_tq'])[0, 1]:+.4f}")
    print(f"  corr(ang, cs_ang)         = {np.corrcoef(ang, d['cs_ang'])[0, 1]:+.4f}")
    print(f"  LS  rate_c = a*rate_f     a = {np.dot(rc, rf) / np.dot(rf, rf):+.5f}"
          f"   (1/a = {np.dot(rf, rf) / np.dot(rc, rf):+.4f})")
    print(f"  LS  tq     = a*cs_tq      a = {np.dot(tq, d['cs_tq']) / np.dot(d['cs_tq'], d['cs_tq']):+.5f}")
    # low-pass both rate copies to 5 Hz: if the disagreement is HF resampling, LF must agree
    for fc in (2.0, 5.0, 10.0):
        def lp(x):
            X = np.fft.rfft(np.asarray(x, float) - np.mean(x))
            f = np.fft.rfftfreq(len(x), 1 / fs)
            X[f > fc] = 0
            return np.fft.irfft(X, n=len(x))
        a, b, c = lp(rc), lp(rf), lp(tq)
        print(f"  <{fc:4.1f} Hz: corr(rate_c,rate_f) {np.corrcoef(a, b)[0, 1]:+.4f}"
              f"   ratio rate_f/rate_c {np.dot(b, a) / np.dot(a, a):+.4f}"
              f"   corr(tq,cs_tq) {np.corrcoef(c, lp(d['cs_tq']))[0, 1]:+.4f}")
    # raw-integer view: what is the RAW 0x18F rate field vs the RAW 0x14A rate field?
    print(f"  raw 0x14A b2:3 (=rate_c/-1.0) ptp {np.ptp(rc / -1.0):8.0f}"
          f"   raw 0x18F b2:3 (=rate_f/-0.1) ptp {np.ptp(rf / -0.1):8.0f}"
          f"   raw ratio {np.ptp(rf / -0.1) / max(np.ptp(rc / -1.0), 1):.4f}")


def main():
    print("=" * 92)
    print("CHANNEL IDENTITY -- quiet segments first, then the segment that carries the 27 Hz line")
    print("=" * 92)
    for s in (2, 7, 11, 5, 8):
        report(s)

    print()
    print("=" * 92)
    print("SHORT TIME SLICE, seg 8 inside the event (t = 46.0 .. 46.5 s)")
    print("=" * 92)
    d = load_seg(8)
    t = d["t"]
    m = (t >= 46.0) & (t <= 46.5)
    print(f"  {'t':>7} {'ang':>8} {'rate_c':>8} {'rate_f':>9} {'tq':>8} {'cs_tq':>9} "
          f"{'sc_tq':>9} {'e4tq':>8}")
    for i in np.flatnonzero(m)[:50]:
        print(f"  {t[i]:>7.3f} {d['ang'][i]:>8.2f} {d['rate_c'][i]:>8.1f} {d['rate_f'][i]:>9.2f} "
              f"{d['tq'][i]:>8.0f} {d['cs_tq'][i]:>9.1f} {d['sc_tq'][i]:>9.1f} "
              f"{d['e4tq'][i]:>8.0f}")


if __name__ == "__main__":
    main()
