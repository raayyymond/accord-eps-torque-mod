#!/usr/bin/env python3
"""V62 route `37` -- the V62 row produced by the PUBLISHED code path, plus a non-FFT check.

Nothing in this file is new method. `analyze_r31_manual_vs_engaged` is imported UNMODIFIED and is
the same code that produced the published V59 (n=9, 21.18 Hz, 227x, 5.26e8) and V61 (n=3, 18.25 Hz,
486x, 4.15e9) rows; if those two do not come back out, the comparison is void and it says FAIL.
Method A is a 4.0 s Welch with a GLOBAL 8-40 Hz median floor -- different window length, different
floor, different detrend from the 2.56 s local-floor periodograms used everywhere else.

METHOD C is time-domain and shares no code with any periodogram: band-pass, then estimate frequency
from upward zero-crossing spacing and from the first autocorrelation maximum. Run in BOTH bands,
because the finding this session is that route 37's 12-30 Hz energy is harmonic distortion of the
6-9 Hz ratchet rather than an independent 21 Hz mode -- a claim that should not rest on rfft bins.

🛑 route 37's glob is `r37s[1-9]*.npz`: seg 0 is a stale 07:05 boot and must not enter any pool.
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

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import analyze_r31_manual_vs_engaged as A  # noqa: E402  -- Method A, verbatim
from _r31_common import runs_of, stat  # noqa: E402
from analyze_r35_v64_verify import bandpass, f_autocorr, f_zerocross  # noqa: E402

PUB = {"V59 r2c": dict(n=9, peak=21.18, prom=227.0, power=5.26e8),
       "V61 r31": dict(n=3, peak=18.25, prom=486.0, power=4.15e9),
       "V64 r35": dict(n=2, peak=21.30, prom=149.0, power=4.31e8)}
POOLS = {"V59 r2c": str(ROOT / "_scratch/cache/r2c" / "r2cs*.npz"),
         "V64 r35": str(ROOT / "_scratch/cache/r35" / "r35s*.npz"),
         "V61 r31": str(ROOT / "_scratch/cache/r31" / "r31s*.npz"),
         "V62 r37": str(ROOT / "_scratch/cache/r37" / "r37s*.npz")}   # seg 0 INCLUDED -- it is real driving
CAP = 5.35
creepA = lambda lat, gear, v: lat & (v > 0.3) & (v <= CAP)          # noqa: E731

R37 = ROOT / "_scratch/cache/r37"
SDPOOLS = {k: sorted(Path(v).parent.glob(Path(v).name)) for k, v in POOLS.items()}
SDPOOLS["V62 road"] = [R37 / f"r37s{s}.npz" for s in range(0, 13)]     # the commute (seg 0 in)
SDPOOLS["V62 lot"] = [R37 / f"r37s{s}.npz" for s in (13, 14)]         # the parking-lot test


def main():
    print("=" * 100)
    print("M-A.  METHOD A (published code path, 4.0 s Welch, global 8-40 Hz floor), engaged creep")
    print("=" * 100)
    got = {}
    for label, pat in POOLS.items():
        arrs, fs = A._pool(pat, creepA)
        got[label] = A._report(label, arrs, fs)
    print()
    for k, p in PUB.items():
        g = got[k]
        ok = (abs(g["peak"] - p["peak"]) < 0.06 and abs(g["prom"] / p["prom"] - 1) < 0.03
              and abs(g["power"] / p["power"] - 1) < 0.03 and g["n"] == p["n"])
        print(f"   {'PASS' if ok else 'FAIL'}  {k}: published n={p['n']} {p['peak']} Hz {p['prom']}x "
              f"{p['power']:.3g}  vs  reproduced n={g['n']} {g['peak']:.2f} Hz {g['prom']:.1f}x "
              f"{g['power']:.3g}")
    v59, v62 = got["V59 r2c"], got["V62 r37"]
    print(f"\n   V62 vs V59 (Method A): freq {v59['peak']:.2f} -> {v62['peak']:.2f} Hz "
          f"({v62['peak'] - v59['peak']:+.2f})  power {v62['power'] / v59['power']:.3f}x  "
          f"prominence {v62['prom'] / v59['prom']:.3f}x")
    print("   ⚠ Method A locates a single argmax over 12-30 Hz on the POOLED spectrum. On route 37")
    print("   that argmax is the ratchet's 3rd harmonic (see studies/sessions/r37/analyze_r37_v62_harmonic.py), so the")
    print("   FREQUENCY it reports for V62 is not a mode frequency. The POWER and PROMINENCE ratios")
    print("   are still meaningful -- they are integrated over the same band on both builds.")

    print()
    print("=" * 100)
    print("M-C.  METHOD C -- TIME DOMAIN, no rfft bin index. Engaged creep, both bands.")
    print("=" * 100)
    NW = 256
    for lo, hi, bname in ((12.0, 30.0, "GRINDING 12-30 Hz"), (6.0, 9.0, "RATCHET 6-9 Hz")):
        print(f"\n  --- {bname} ---")
        for label, pat in POOLS.items():
            zc, ac, w, act = [], [], 0, 0
            for f in sorted(Path(pat).parent.glob(Path(pat).name)):
                d = {k: v for k, v in np.load(f).items()}
                fs = 1.0 / np.median(np.diff(d["t"]))
                m = (d["cc_lat"] > 0.5) & (d["cs_v"] > 0.3) & (d["cs_v"] <= CAP)
                for a, b in runs_of(m, d["t"], NW):
                    y = bandpass(d["tq"][a:b], fs, lo, hi)
                    for i in range(0, len(y) - NW + 1, NW):
                        seg = y[i:i + NW]
                        w += 1
                        if np.std(seg) < 20:      # a quiet window has no period to estimate
                            continue
                        act += 1
                        z, c = f_zerocross(seg, fs), f_autocorr(seg, fs, lo, hi)
                        if np.isfinite(z):
                            zc.append(z)
                        if np.isfinite(c):
                            ac.append(c)
            print(f"    {label:10s} {act}/{w} windows active (band sd >= 20 counts)")
            print(f"       zero-crossing  {stat(zc, '')}")
            print(f"       autocorrelation{stat(ac, '')}")
            if zc and ac:
                print(f"       => zc {np.median(zc):5.2f} Hz | ac {np.median(ac):5.2f} Hz")

    print()
    print("=" * 100)
    print("M-D.  BAND ACTIVITY DUTY CYCLE -- what fraction of engaged-creep time each band is live")
    print("=" * 100)
    print("   Per-window band-limited sd, in raw torsion-bar counts. No peak-finding at all, so it")
    print("   cannot be fooled by a wandering argmax, and it is directly comparable across builds.")
    print("   Duty cycle at several thresholds beside it.\n")
    CUTS = (50, 100, 200, 400, 800)
    for lo, hi in ((6, 9), (12, 30), (18, 26)):
        print(f"   --- {lo}-{hi} Hz ---")
        print(f"   {'build':10s} {'win':>4s} {'sd p50':>8s} {'p90':>8s} {'p99':>8s} {'max':>8s}  "
              + "".join(f"{'>=' + str(c):>8s}" for c in CUTS))
        for label, files in SDPOOLS.items():
            sds = []
            for f in files:
                d = {k: v for k, v in np.load(f).items()}
                fs = 1.0 / np.median(np.diff(d["t"]))
                m = (d["cc_lat"] > 0.5) & (d["cs_v"] > 0.3) & (d["cs_v"] <= CAP)
                for a, b in runs_of(m, d["t"], NW):
                    y = bandpass(d["tq"][a:b], fs, lo, hi)
                    for i in range(0, len(y) - NW + 1, NW):
                        sds.append(float(np.std(y[i:i + NW])))
            s = np.array(sds)
            print(f"   {label:10s} {len(s):4d} {np.percentile(s, 50):8.1f} "
                  f"{np.percentile(s, 90):8.1f} {np.percentile(s, 99):8.1f} {s.max():8.1f}  "
                  + "".join(f"{100 * np.mean(s >= c):7.0f}%" for c in CUTS))
        print()


def rail_controlled():
    """The one confound that could fake a fix: 'the vibration dies at the rail' (141x, measured).

    Route 37's engaged creep sits at a HIGHER LKAS command than route 2c's (|0x0E4| p50 2867 vs
    2035) and spends more time on the +/-4096 rail (41.3% vs 26.9%). More command drive should make
    the mode WORSE, but more rail time could suppress it -- so the comparison is repeated on
    windows selected to be OFF the rail on every build.
    """
    print()
    print("=" * 100)
    print("M-E.  RAIL-CONTROLLED -- windows with <10% of frames on the +/-4096 LKAS command rail")
    print("=" * 100)
    NW = 256
    print(f"   {'build':10s} {'win':>4s} {'railfrac':>9s} {'|e4| p50':>9s} | "
          f"{'18-26 sd p50':>13s} {'p90':>7s} {'max':>7s} | {'6-9 sd p50':>11s} {'p90':>7s}")
    for label, files in SDPOOLS.items():
        rows = []
        for f in files:
            d = {k: v for k, v in np.load(f).items()}
            fs = 1.0 / np.median(np.diff(d["t"]))
            m = (d["cc_lat"] > 0.5) & (d["cs_v"] > 0.3) & (d["cs_v"] <= CAP)
            for a, b in runs_of(m, d["t"], NW):
                y26 = bandpass(d["tq"][a:b], fs, 18.0, 26.0)
                y69 = bandpass(d["tq"][a:b], fs, 6.0, 9.0)
                e4 = np.abs(d["e4tq"][a:b])
                for i in range(0, len(y26) - NW + 1, NW):
                    rows.append((float(np.mean(e4[i:i + NW] >= 4096)),
                                 float(np.median(e4[i:i + NW])),
                                 float(np.std(y26[i:i + NW])), float(np.std(y69[i:i + NW]))))
        r = np.array(rows)
        sel = r[:, 0] < 0.10
        if sel.sum() < 2:
            print(f"   {label:10s} {int(sel.sum()):4d}  -- too few off-rail windows")
            continue
        s = r[sel]
        print(f"   {label:10s} {len(s):4d} {np.median(s[:, 0]):8.2f}% {np.median(s[:, 1]):9.0f} | "
              f"{np.percentile(s[:, 2], 50):13.1f} {np.percentile(s[:, 2], 90):7.1f} "
              f"{s[:, 2].max():7.1f} | {np.percentile(s[:, 3], 50):11.1f} "
              f"{np.percentile(s[:, 3], 90):7.1f}")
    print("\n   (if V62's 18-26 Hz collapse survives an off-rail selection, saturation is not the")
    print("    explanation for it)")


if __name__ == "__main__":
    main()
    rail_controlled()
