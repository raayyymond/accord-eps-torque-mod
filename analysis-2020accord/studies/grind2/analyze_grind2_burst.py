#!/usr/bin/env python3
"""Grind #2, the TAIL: a bursty limit cycle need not move a median.

Deliverable A's teeth. Three tail instruments, all matched-cell and all unit-bootstrapped:

  1. p90 (not median) of the per-window 30-49 Hz envelope p99, as the cell statistic.
  2. EXCEEDANCE RATE above a threshold set on the Kd=1 pool itself, swept over quantiles.
     If a phenomenon is new, it appears as a fat tail even when the body of the distribution
     is unchanged.
  3. SHAPE statistics that cancel any route-wide level offset: prominence, and the band's
     envelope ratio against 24-28 Hz (adjacent, pre-declared control) and against 1-4 Hz.
     🛑 Necessary because A finds a uniform ~0.85 level offset in EVERY band, 1-4 Hz included.

Also lists the worst 30-49 Hz windows per build, with wall clock where the cache carries it, so
the prior session's five route-37 instances can be placed against every other build.

Usage:  python studies/grind2/analyze_grind2_burst.py
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
import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G  # noqa: E402

PKL = HERE.parent / "_scratch/data/_cache_grind2_records.pkl"
OUTJSON = HERE / "_scratch/out/_grind2_burst.json"
RNG = np.random.default_rng(20260801)
NBOOT = 2000
R37_OFF = 1785517810.5370      # route-37 wall clock, fitted in studies/sessions/r37/r37_wallclock.py


def p90(v):
    return np.percentile(v, 90)


def derive(rs):
    """Shape keys that cancel a route-wide level offset."""
    for r in rs:
        r["s_hf_neg"] = r["e_30-49"] / max(r["e_24-28"], 1e-9)
        r["s_hf_drv"] = r["e_30-49"] / max(r["e_1-4"], 1e-9)
        r["s_g1_neg"] = r["e_18-22"] / max(r["e_24-28"], 1e-9)
    return rs


def exceed_ratio(kd2, kd1, key, thr, rng, nboot=NBOOT, min_ep=3, min_win=8):
    """Matched-cell ratio of the EXCEEDANCE FRACTION above `thr`, unit-bootstrapped.

    Cells where neither side exceeds contribute nothing; a +0.5/+0.5 continuity correction keeps
    a zero-count cell from sending the log-ratio to infinity.
    """
    def agg(v):
        return (np.sum(v > thr) + 0.5) / (len(v) + 1.0)
    return G.boot_cellwise(kd2, kd1, key, rng, nboot=nboot, min_ep=min_ep, min_win=min_win,
                           agg=agg)


def main():
    G.EPKEY = "blk"
    with open(PKL, "rb") as fh:
        store = pickle.load(fh)
    for b in store:
        derive(store[b])
    kd0 = [r for b in G.DOSE[0.0] for r in store.get(b, [])]
    kd1 = [r for b in G.DOSE[1.0] for r in store.get(b, [])]
    kd2 = [r for b in G.DOSE[2.0] for r in store.get(b, [])]
    out = {}

    # ================================================================ 1. p90 cell statistic ======
    G.hdr("1.  MATCHED-CELL RATIO with the cell statistic = p90 of the window envelope p99\n"
          "(the tail of the burst distribution, not its body). Kd=2 / Kd=1.")
    print(f"  {'band':14s} {'ratio(p90)':>10s} {'95% CI':>18s} | {'ratio(median)':>13s} "
          f"{'95% CI':>18s}")
    r1 = {}
    for b in G.BANDS:
        key = "e_" + b
        a = G.boot_cellwise(kd2, kd1, key, RNG, nboot=NBOOT, agg=p90)
        m = G.boot_cellwise(kd2, kd1, key, RNG, nboot=NBOOT)
        r1[b] = dict(p90=a[:3], med=m[:3], ncell=a[3])
        print(f"  {b:14s} {a[0]:10.3f} [{a[1]:7.3f},{a[2]:7.3f}] | {m[0]:13.3f} "
              f"[{m[1]:7.3f},{m[2]:7.3f}]")
    out["p90"] = {k: dict(p90=list(v["p90"]), med=list(v["med"])) for k, v in r1.items()}

    # split-half null for the p90 statistic -- a tail statistic has a wider null than a median
    print("\n  split-half null for the p90 statistic (same estimator, one pool halved):")
    for nm, rs in (("Kd=1", kd1), ("Kd=2", kd2)):
        for b in ("18-22", "24-28", "30-49"):
            m, lo, hi = G.split_half_null(rs, "e_" + b, RNG, nrep=300, agg=p90)
            print(f"    {nm}  {b:8s} median {m:6.3f}  null [{lo:6.3f}, {hi:6.3f}]  "
                  f"floor {max(hi, 1 / lo):.2f}x")

    # ================================================================ 2. exceedance ==============
    G.hdr("2.  EXCEEDANCE-RATE RATIO.  Threshold set on the Kd=1 pool inside the matched cells;\n"
          "a NEW phenomenon shows up as a fat tail even with the body unchanged.")
    r2 = {}
    for b in ("18-22", "24-28", "30-40", "40-49", "30-49"):
        key = "e_" + b
        v1 = G.col(kd1, key)
        v1 = v1[np.isfinite(v1)]
        print(f"\n  band {b} Hz   (Kd=1 pool: median {np.median(v1):.1f}, "
              f"p90 {np.percentile(v1, 90):.1f}, p99 {np.percentile(v1, 99):.1f} counts)")
        print(f"    {'thr q':>6s} {'thr':>8s} {'Kd1 frac':>9s} {'Kd2 frac':>9s} "
              f"{'rate ratio':>11s} {'95% CI':>18s}")
        for q in (50, 75, 90, 95, 99):
            thr = float(np.percentile(v1, q))
            f1 = float(np.mean(G.col(kd1, key) > thr))
            f2 = float(np.mean(G.col(kd2, key) > thr))
            a = exceed_ratio(kd2, kd1, key, thr, RNG)
            r2[f"{b}|q{q}"] = dict(thr=thr, f1=f1, f2=f2, ratio=a[0], lo=a[1], hi=a[2])
            print(f"    {q:6d} {thr:8.1f} {f1:9.3f} {f2:9.3f} {a[0]:11.3f} "
                  f"[{a[1]:7.3f},{a[2]:7.3f}]")
    out["exceed"] = r2

    # ================================================================ 3. shape ===================
    G.hdr("3.  SHAPE statistics -- immune to the uniform ~0.85 route-level offset that A found in\n"
          "every band including 1-4 Hz.")
    r3 = {}
    print(f"  {'statistic':22s} {'Kd2/Kd1':>8s} {'95% CI':>18s} | {'Kd0/Kd1':>8s} "
          f"{'95% CI':>18s}")
    for key, lbl in (("p_30-49", "prominence 30-49"), ("p_30-40", "prominence 30-40"),
                     ("p_40-49", "prominence 40-49"), ("p_18-22", "prominence 18-22"),
                     ("s_hf_neg", "E(30-49)/E(24-28)"), ("s_hf_drv", "E(30-49)/E(1-4)"),
                     ("s_g1_neg", "E(18-22)/E(24-28)")):
        a = G.boot_cellwise(kd2, kd1, key, RNG, nboot=NBOOT)
        c = G.boot_cellwise(kd0, kd1, key, RNG, nboot=NBOOT, min_ep=2, min_win=5)
        r3[key] = dict(kd2=a[:3], kd0=c[:3])
        print(f"  {lbl:22s} {a[0]:8.3f} [{a[1]:7.3f},{a[2]:7.3f}] | {c[0]:8.3f} "
              f"[{c[1]:7.3f},{c[2]:7.3f}]")
    print("\n  split-half null for the shape statistics:")
    for key in ("p_30-49", "s_hf_neg"):
        for nm, rs in (("Kd=1", kd1), ("Kd=2", kd2)):
            m, lo, hi = G.split_half_null(rs, key, RNG, nrep=300)
            print(f"    {key:10s} {nm}  median {m:6.3f}  null [{lo:6.3f}, {hi:6.3f}]")
    out["shape"] = {k: dict(kd2=list(v["kd2"]), kd0=list(v["kd0"])) for k, v in r3.items()}

    # ================================================================ 4. worst windows ===========
    G.hdr("4.  WORST 30-49 Hz WINDOWS PER BUILD  (rate per 1000 windows above fixed cuts, then the\n"
          "single worst windows).  A build-independent census: nothing here uses the operator's\n"
          "recollection of when the grinding happened.")
    cuts = (150.0, 250.0, 400.0, 700.0)
    print(f"  {'build':10s} {'kd':>3s} {'nwin':>6s} | " +
          " ".join(f"{'>' + str(int(c)):>12s}" for c in cuts) +
          f" | {'env p99':>7s} {'p99.9':>8s} {'max':>8s}")
    r4 = {}
    for b in G.ORDER:
        rs = store.get(b, [])
        if not rs:
            continue
        e = G.col(rs, "e_30-49")
        cells = " ".join(f"{1000 * np.mean(e > c):7.1f}/1e3" for c in cuts)
        r4[b] = dict(n=len(rs), rates=[float(np.mean(e > c)) for c in cuts],
                     p99=float(np.percentile(e, 99)), mx=float(e.max()))
        print(f"  {b:10s} {G.BUILDS[b]['kd']:3.0f} {len(rs):6d} | {cells} | "
              f"{np.percentile(e, 99):7.1f} {np.percentile(e, 99.9):8.1f} {e.max():8.1f}")
    out["census"] = r4

    print("\n  same census restricted to the HIGH-EFFORT arm (eff >= 800 counts), where the\n"
          "  operator places grind #2:")
    print(f"  {'build':10s} {'kd':>3s} {'nwin':>6s} | " +
          " ".join(f"{'>' + str(int(c)):>12s}" for c in cuts))
    for b in G.ORDER:
        rs = [r for r in store.get(b, []) if r["eff"] >= 800]
        if len(rs) < 5:
            print(f"  {b:10s} {G.BUILDS[b]['kd']:3.0f} {len(rs):6d} | (too few)")
            continue
        e = G.col(rs, "e_30-49")
        print(f"  {b:10s} {G.BUILDS[b]['kd']:3.0f} {len(rs):6d} | " +
              " ".join(f"{1000 * np.mean(e > c):7.1f}/1e3" for c in cuts))

    print("\n  TOP-25 windows by 30-49 Hz envelope p99 across ALL builds:")
    allr = [r for b in G.ORDER for r in store.get(b, [])]
    allr.sort(key=lambda r: -r["e_30-49"])
    print(f"  {'build':10s} {'seg':>3s} {'t0':>7s} {'wall':>9s} {'eng':>3s} {'env':>7s} "
          f"{'prom':>6s} {'f0':>6s} {'Q':>5s} {'v':>6s} {'eff':>6s} {'rate':>6s} {'E18-22':>7s}")
    for r in allr[:25]:
        w = (time.strftime("%H:%M:%S", time.localtime(R37_OFF + r["t0"] + 60.0 * r["seg"]))
             if r["build"] == "V62/r37" else "-")
        print(f"  {r['build']:10s} {r['seg']:3d} {r['t0']:7.2f} {w:>9s} {r['eng']:3d} "
              f"{r['e_30-49']:7.1f} {r['p_30-49']:6.2f} {r['f_30-49']:6.2f} {r['Qhf']:5.1f} "
              f"{r['v']:6.2f} {r['eff']:6.0f} {r['rate']:6.1f} {r['e_18-22']:7.1f}")

    OUTJSON.write_text(json.dumps(out, indent=1, default=float))
    print(f"\nwrote {OUTJSON}")


if __name__ == "__main__":
    main()
