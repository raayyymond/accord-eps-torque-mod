#!/usr/bin/env python3
"""THE ORDER TEST, settled: does the highway 30-49 Hz line track 3*v/2.08, or does it sit still?

The operator's single most decision-bearing statement is that the pitch STAYS ABOUT THE SAME as
speed changes. If the line is wheel order 3 it must run 31.7 Hz at 22 m/s to 48.2 Hz at 33.4 --
a 52% pitch change no driver would call "about the same" -- and it is a tyre, not firmware.

Two earlier passes disagreed and both were under-specified:
  * `studies/highway/highway_fast_lane.py` §2 reported implied order p50 = 3.00 AND a Theil-Sen slope of -0.20
    that EXCLUDES 1.442. Those cannot both be a description of the same line.
    🛑 The resolution is that "implied order p50 = 3.00" is NOT a test. order = f0*2.08/v, so a
    line PINNED at the middle of a 30-49.5 Hz band, observed at a median 28 m/s, reads
    40*2.08/28 = 2.97 whatever it is doing. Only the SLOPE, or a binned f0-vs-v table, tests it.
  * `studies/highway/highway_event_hunt.py` §4's per-band "MODE" verdicts are band-censored (a 9 Hz band cannot
    show a 26 Hz sweep) and are withdrawn.

This file replaces both with the assumption-free version: median f0 in 2 m/s speed bins, and a
head-to-head of two models fitted to the same windows --
    MODEL A  f0 = const                    (a mode)
    MODEL B  f0 = 3*v/CIRC                 (wheel order 3, zero free parameters)
    MODEL C  f0 = n*v/CIRC, n free         (best-fit order)
compared by residual sd and by BIC on the same data.

The 8-30 Hz line is carried alongside as the POSITIVE CONTROL: the kit already knows it is wheel
order 1, so any instrument that cannot recover order 1 here is not to be believed on 30-49.

Usage:  python studies/highway/highway_order_test.py
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

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G          # noqa: E402
import _r47_imu_lib as I         # noqa: E402
import highway_event_hunt as H   # noqa: E402

RNG = np.random.default_rng(20260803)
OUT = HERE / "_scratch/out/_hwy_order_test.json"
NFFT = 256
CIRC = H.CIRC
VB = [(22, 24), (24, 26), (26, 28), (28, 30), (30, 32), (32, 35)]


def blockboot_median(vals, blocks, rng, nboot=2000):
    grp = {}
    for v, b in zip(vals, blocks):
        grp.setdefault(b, []).append(v)
    per = [np.array(x, float) for x in grp.values()]
    if not per:
        return np.nan, np.nan, np.nan
    allv = np.concatenate(per)
    dr = np.empty(nboot)
    for k in range(nboot):
        dr[k] = np.median(np.concatenate([per[i] for i in
                                          rng.integers(0, len(per), len(per))]))
    return (float(np.median(allv)), float(np.percentile(dr, 2.5)),
            float(np.percentile(dr, 97.5)))


def model_compare(v, f0, label):
    """MODEL A (constant) vs B (order 3, no free parameter) vs C (free order)."""
    n = len(v)
    a = float(np.median(f0))
    rA = f0 - a
    rB = f0 - 3.0 * v / CIRC
    nfit = float(np.sum(f0 * v) / np.sum(v * v) * CIRC)     # least-squares order through origin
    rC = f0 - nfit * v / CIRC
    def bic(r, k):
        s2 = float(np.mean(r ** 2))
        return n * np.log(max(s2, 1e-12)) + k * np.log(n)
    bA, bB, bC = bic(rA, 1), bic(rB, 0), bic(rC, 1)
    print(f"    {label}")
    print(f"      MODEL A  f0 = {a:.2f} Hz constant      resid sd {np.std(rA):6.2f} Hz   "
          f"BIC {bA:9.1f}")
    print(f"      MODEL B  f0 = 3*v/2.08 (order 3)      resid sd {np.std(rB):6.2f} Hz   "
          f"BIC {bB:9.1f}")
    print(f"      MODEL C  f0 = {nfit:.2f}*v/2.08 (free order) resid sd {np.std(rC):6.2f} Hz   "
          f"BIC {bC:9.1f}")
    best = min((bA, "A: a MODE at a fixed frequency"), (bB, "B: WHEEL ORDER 3"),
               (bC, f"C: wheel order {nfit:.2f}"))[1]
    print(f"      => lowest BIC: {best}   (dBIC A-B = {bA - bB:+.1f}, A-C = {bA - bC:+.1f})")
    return dict(a=a, sdA=float(np.std(rA)), sdB=float(np.std(rB)), sdC=float(np.std(rC)),
                nfit=nfit, bicA=bA, bicB=bB, bicC=bC, best=best)


def main():
    store = {}
    runs = H.collect_envelopes("tq")

    # ---------------------------------------------------------------- CAN windows ---------------
    W = []
    for ri, r in enumerate(runs):
        fs, n = r["fs"], len(r["tq"])
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        for i in range(0, n - NFFT + 1, NFFT // 2):
            vv = float(np.mean(r["v"][i:i + NFFT]))
            if vv < 22.0:
                continue
            P = G.periodogram(r["tq"][i:i + NFFT], fs, NFFT, True)
            if P is None:
                continue
            R = G.prom_spectrum(f, P)
            hi, ph = G.locate(f, P, 30.0, 49.5, R=R)
            lo, pl = G.locate(f, P, 8.0, 30.0, R=R)
            W.append(dict(v=vv, f_hi=hi, p_hi=ph, f_lo=lo, p_lo=pl, kd=r["kd"],
                          route=r["route"], blk=(ri, i // int(10 * fs))))
    print(f"[{len(W)} torsion-bar windows above 22 m/s]")

    G.hdr("1.  BINNED f0 vs SPEED -- the assumption-free test. Torsion bar, 0x18F.\n"
          "    If the 30-49.5 Hz line is WHEEL ORDER 3 its median must follow the 'order3'\n"
          "    column. If it is a MODE it must stay put while that column climbs 15 Hz.")
    print(f"    {'speed bin':>11}{'n':>6}{'f0(30-49.5)':>14}{'   [95% CI]':>20}"
          f"{'order3':>9}{'order2':>9}{'order4':>9}{'  implied order':>16}")
    rows = []
    for a, b in VB:
        s = [w for w in W if a <= w["v"] < b and np.isfinite(w["f_hi"])]
        if len(s) < 10:
            print(f"    {f'{a}-{b}':>11}{len(s):>6}   (thin)")
            continue
        m, lo, hi = blockboot_median([w["f_hi"] for w in s], [w["blk"] for w in s], RNG)
        vm = float(np.median([w["v"] for w in s]))
        print(f"    {f'{a}-{b}':>11}{len(s):>6}{m:>14.2f}   [{lo:6.2f},{hi:6.2f}]"
              f"{3 * vm / CIRC:>9.2f}{2 * vm / CIRC:>9.2f}{4 * vm / CIRC:>9.2f}"
              f"{m * CIRC / vm:>16.2f}")
        rows.append(dict(bin=[a, b], n=len(s), f0=m, lo=lo, hi=hi, v=vm,
                         order=m * CIRC / vm))
    store["binned_hi"] = rows

    print(f"\n    POSITIVE CONTROL -- the 8-30 Hz line, which the kit already knows is order 1:")
    print(f"    {'speed bin':>11}{'n':>6}{'f0(8-30)':>14}{'   [95% CI]':>20}{'order1':>9}"
          f"{'  implied order':>16}")
    rows = []
    for a, b in VB:
        s = [w for w in W if a <= w["v"] < b and np.isfinite(w["f_lo"])]
        if len(s) < 10:
            continue
        m, lo, hi = blockboot_median([w["f_lo"] for w in s], [w["blk"] for w in s], RNG)
        vm = float(np.median([w["v"] for w in s]))
        print(f"    {f'{a}-{b}':>11}{len(s):>6}{m:>14.2f}   [{lo:6.2f},{hi:6.2f}]"
              f"{vm / CIRC:>9.2f}{m * CIRC / vm:>16.2f}")
        rows.append(dict(bin=[a, b], n=len(s), f0=m, lo=lo, hi=hi, v=vm, order=m * CIRC / vm))
    store["binned_lo"] = rows

    G.hdr("2.  MODEL COMPARISON on the same windows")
    v = np.array([w["v"] for w in W if np.isfinite(w["f_hi"])])
    f0 = np.array([w["f_hi"] for w in W if np.isfinite(w["f_hi"])])
    store["model_hi"] = model_compare(v, f0, "30-49.5 Hz line, all windows > 22 m/s "
                                             f"(n={len(v)})")
    m = v >= 28
    store["model_hi_fast"] = model_compare(v[m], f0[m], "\n    30-49.5 Hz line, > 28 m/s only "
                                                        f"(n={int(m.sum())})")
    vl = np.array([w["v"] for w in W if np.isfinite(w["f_lo"])])
    fl = np.array([w["f_lo"] for w in W if np.isfinite(w["f_lo"])])
    print()
    store["model_lo"] = model_compare(vl, fl, "POSITIVE CONTROL: 8-30 Hz line "
                                              f"(n={len(vl)})  -- MODEL B here is order 3, so\n"
                                              "      the informative line is MODEL C's free order,"
                                              " which must come out near 1.00")

    # ---------------------------------------------------------------- IMU ------------------------
    G.hdr("3.  THE SAME TEST ON THE COMMA IMU (independent hardware, no EPS signal path)")
    irecs = H.collect_imu()
    IW = {}
    for r in irecs:
        for ax in ("ay", "gz", "gx", "az"):
            g = ax[0]
            cd = dict((x[0], x[1]) for x in H.ROUTES)[r["route"]]
            pf = dict((x[0], x[2]) for x in H.ROUTES)[r["route"]]
            p = ROOT / cd / f"{pf}{r['seg']}_imu.npz"
            di = dict(np.load(p))
            u, odr, _, tu = I.uniform(di["at"] if g == "a" else di["gt"], di[ax])
            vv = r[g + "_v"]
            lat = r[g + "_lat"]
            n = min(len(u), len(vv))
            f = np.fft.rfftfreq(NFFT, 1 / odr)
            for i in range(0, n - NFFT + 1, NFFT // 2):
                sp = float(np.mean(vv[i:i + NFFT]))
                if sp < 22.0 or np.mean(lat[i:i + NFFT]) < 0.9:
                    continue
                P = I.periodogram(u[i:i + NFFT], odr, NFFT, True)
                if P is None:
                    continue
                R = I.prom_spectrum(f, P)
                hi, ph = I.locate(f, P, 30.0, 49.5, R=R)
                IW.setdefault(ax, []).append(dict(v=sp, f0=hi, prom=ph, kd=r["kd"],
                                                  blk=(r["route"], r["seg"], i // 1000)))
    for ax in ("ay", "gz", "gx", "az"):
        s = IW.get(ax, [])
        if len(s) < 40:
            continue
        v = np.array([w["v"] for w in s])
        f0 = np.array([w["f0"] for w in s])
        print(f"\n  --- {ax} ---  n={len(s)} windows > 22 m/s")
        print(f"    {'speed bin':>11}{'n':>6}{'f0':>10}{'   [95% CI]':>20}{'order3':>9}"
              f"{'  implied order':>16}")
        for a, b in VB:
            k = [w for w in s if a <= w["v"] < b]
            if len(k) < 10:
                continue
            m, lo, hi = blockboot_median([w["f0"] for w in k], [w["blk"] for w in k], RNG, 800)
            vm = float(np.median([w["v"] for w in k]))
            print(f"    {f'{a}-{b}':>11}{len(k):>6}{m:>10.2f}   [{lo:6.2f},{hi:6.2f}]"
                  f"{3 * vm / CIRC:>9.2f}{m * CIRC / vm:>16.2f}")
        store[f"model_imu_{ax}"] = model_compare(v, f0, f"    {ax}, all windows > 22 m/s")

    OUT.write_text(json.dumps(store, indent=1, default=float))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
