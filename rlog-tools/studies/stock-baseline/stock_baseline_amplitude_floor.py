#!/usr/bin/env python3
"""THE AMPLITUDE REPRODUCIBILITY FLOOR for the ~7.79 Hz ratchet line.

The kit quotes a779 = 145.2 / 549.2 / 275.1 / 597.6 counts for V81 / V83a / V84 / V85 and reads a
~3-4x rise off it.  Those four numbers come from four routes on four different days.  The
BUILD-TO-BUILD reproducibility floor in FREQUENCY is on record (1.7%); the floor in AMPLITUDE has
never been measured, and a bisection would rest entirely on it.  This file measures what CAN be
measured without new flights:

  A  BLOCK split-half within a route          -> pure sampling noise at half the exposure
  B  contiguous SEGMENT split within a route  -> road / regime drift inside one drive
  C  per-segment median spread                -> road variability, minute to minute
  D  a779 vs SPEED within route               -> how much an unmatched speed census can manufacture
  E  speed-matched cross-build ratios          -> the cross-build signal, against A/B/C

🛑 THE INSTRUMENT IS THE CORPUS'S.  Windows, spectra and a779 are `ratchet_line_ladder_v87.load`,
imported verbatim -- the same code that printed the four numbers above.  Nothing is redefined.

Resampling unit is `blk` (~10.13 s contiguous block) everywhere, per the standing instruction.
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
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod")
sys.path.insert(0, str(ROOT / "rlog-tools"))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import ratchet_line_ladder_v87 as L  # noqa: E402
import relay_fingerprint_r6e as RF   # noqa: E402

RNG = np.random.default_rng(87_0808)
NBOOT = 4000
OUT = {}


def hdr(s):
    print("\n" + "=" * 104 + f"\n{s}\n" + "=" * 104, flush=True)


def med_by_blk(recs):
    """Median a779 over windows (windows inside a blk are ~50% overlapped, so blk is the unit)."""
    return float(np.median([r["a779"] for r in recs])) if recs else np.nan


def split_half_blocks(recs, nboot=NBOOT):
    """A: randomly halve the route's BLOCKS, ratio the two half-medians.  log2 |ratio|."""
    blks = sorted({r["blk"] for r in recs})
    by = {b: [r for r in recs if r["blk"] == b] for b in blks}
    if len(blks) < 8:
        return None
    lr = []
    for _ in range(nboot):
        perm = RNG.permutation(len(blks))
        h = len(blks) // 2
        A = [r for i in perm[:h] for r in by[blks[i]]]
        B = [r for i in perm[h:] for r in by[blks[i]]]
        a, b = med_by_blk(A), med_by_blk(B)
        if np.isfinite(a) and np.isfinite(b) and a > 0 and b > 0:
            lr.append(abs(np.log(a / b)))
    lr = np.asarray(lr)
    return dict(n_blk=len(blks), med=float(np.exp(np.median(lr))),
                p95=float(np.exp(np.percentile(lr, 95))),
                p99=float(np.exp(np.percentile(lr, 99))))


def segment_split(recs):
    """B: contiguous first-half vs second-half of the route's SEGMENTS."""
    segs = sorted({r["seg"] for r in recs})
    if len(segs) < 4:
        return None
    h = len(segs) // 2
    A = [r for r in recs if r["seg"] in segs[:h]]
    B = [r for r in recs if r["seg"] in segs[h:]]
    a, b = med_by_blk(A), med_by_blk(B)
    return dict(n_seg=len(segs), a=a, b=b, ratio=float(max(a, b) / min(a, b)),
                nA=len(A), nB=len(B))


def per_segment(recs):
    """C: median a779 per segment; report the spread."""
    segs = sorted({r["seg"] for r in recs})
    med = {s: med_by_blk([r for r in recs if r["seg"] == s]) for s in segs}
    v = np.array([m for m in med.values() if np.isfinite(m) and m > 0])
    if len(v) < 3:
        return None
    return dict(per_seg={int(k): float(x) for k, x in med.items()},
                n_seg=len(v), lo=float(v.min()), hi=float(v.max()),
                span=float(v.max() / v.min()),
                iqr_ratio=float(np.percentile(v, 75) / np.percentile(v, 25)))


def speed_law(recs):
    """D: OLS of log(a779) on speed, block-bootstrapped.  Units: log-counts per m/s."""
    v = np.array([r["v"] for r in recs], float)
    a = np.array([r["a779"] for r in recs], float)
    ok = np.isfinite(v) & np.isfinite(a) & (a > 0)
    v, a, u = v[ok], np.log(a[ok]), np.array([r["blk"] for r in recs])[ok]
    if len(v) < 8 or len(set(np.round(v, 2))) < 4:
        return None
    groups = {}
    for i, k in enumerate(u):
        groups.setdefault(k, []).append(i)
    keys = list(groups)
    full = np.polyfit(v, a, 1)[0]
    draws = []
    for _ in range(2000):
        idx = np.concatenate([groups[keys[i]] for i in RNG.integers(0, len(keys), len(keys))])
        if len(set(np.round(v[idx], 2))) < 4:
            continue
        draws.append(np.polyfit(v[idx], a[idx], 1)[0])
    if len(draws) < 50:
        return dict(slope=float(full), lo=np.nan, hi=np.nan)
    return dict(slope=float(full), lo=float(np.percentile(draws, 2.5)),
                hi=float(np.percentile(draws, 97.5)),
                v_med=float(np.median(v)), v_p10=float(np.percentile(v, 10)),
                v_p90=float(np.percentile(v, 90)))


def ratio_ci(A, B, nboot=NBOOT):
    """Block-bootstrap CI on median(A)/median(B)."""
    def g(recs):
        d = {}
        for r in recs:
            d.setdefault(r["blk"], []).append(r["a779"])
        return d
    ga, gb = g(A), g(B)
    ka, kb = list(ga), list(gb)
    if len(ka) < 3 or len(kb) < 3:
        return (np.nan, np.nan, np.nan)
    pt = np.median([x for k in ka for x in ga[k]]) / np.median([x for k in kb for x in gb[k]])
    d = []
    for _ in range(nboot):
        a = np.concatenate([ga[ka[i]] for i in RNG.integers(0, len(ka), len(ka))])
        b = np.concatenate([gb[kb[i]] for i in RNG.integers(0, len(kb), len(kb))])
        d.append(np.median(a) / np.median(b))
    return (float(pt), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)))


def main():
    hdr("LOAD -- the corpus instrument, engaged arm, four builds")
    per = {}
    for route, cache, pfx, segs in L.ROUTES:
        e = L.load(route, cache, pfx, segs, True)
        per[route] = e
        v = np.array([r["v"] for r in e])
        print(f"  {route:10s} {len(e):4d} windows / {len({r['blk'] for r in e}):3d} blk / "
              f"{len({r['seg'] for r in e}):2d} seg   speed p10-p90 "
              f"{np.percentile(v, 10):5.2f}-{np.percentile(v, 90):5.2f} m/s  med {np.median(v):5.2f}",
              flush=True)
        OUT.setdefault(route, {})["speed"] = dict(
            p10=float(np.percentile(v, 10)), p50=float(np.median(v)),
            p90=float(np.percentile(v, 90)), lo=float(v.min()), hi=float(v.max()))

    hdr("A  BLOCK SPLIT-HALF WITHIN A ROUTE -- the pure sampling floor at half exposure\n"
        "   ratio of the two half-medians; 1.00 would be perfect reproducibility")
    print(f"{'build':10s} {'blk':>4s} | {'median |ratio|':>15s} {'p95':>8s} {'p99':>8s}")
    for route, _, _, _ in L.ROUTES:
        r = split_half_blocks(per[route])
        OUT[route]["split_half_blk"] = r
        if r:
            print(f"{route:10s} {r['n_blk']:4d} | {r['med']:15.3f} {r['p95']:8.3f} {r['p99']:8.3f}")

    hdr("B  CONTIGUOUS SEGMENT SPLIT -- first half of the drive vs second half\n"
        "   this one carries ROAD and REGIME drift, not just sampling noise")
    print(f"{'build':10s} {'seg':>4s} | {'first half':>11s} {'second half':>12s} {'ratio':>8s}")
    for route, _, _, _ in L.ROUTES:
        r = segment_split(per[route])
        OUT[route]["segment_split"] = r
        if r:
            print(f"{route:10s} {r['n_seg']:4d} | {r['a']:11.1f} {r['b']:12.1f} {r['ratio']:8.2f}")

    hdr("C  PER-SEGMENT MEDIAN a779 -- minute-to-minute road variability inside ONE build")
    print(f"{'build':10s} {'seg':>4s} | {'min':>8s} {'max':>8s} {'max/min':>9s} {'IQR ratio':>10s}")
    for route, _, _, _ in L.ROUTES:
        r = per_segment(per[route])
        OUT[route]["per_segment"] = r
        if r:
            print(f"{route:10s} {r['n_seg']:4d} | {r['lo']:8.1f} {r['hi']:8.1f} "
                  f"{r['span']:9.2f} {r['iqr_ratio']:10.2f}")
            print("           " + "  ".join(f"s{k}:{v:.0f}" for k, v in sorted(r["per_seg"].items())
                                             if np.isfinite(v)))

    hdr("D  a779 vs SPEED within a route -- d log(a779) / d v, and what a census mismatch buys")
    print(f"{'build':10s} | {'slope /(m/s), 95% CI':>28s} | {'x per +1 m/s':>13s}")
    for route, _, _, _ in L.ROUTES:
        r = speed_law(per[route])
        OUT[route]["speed_law"] = r
        if r:
            print(f"{route:10s} | {r['slope']:+9.3f} [{r['lo']:+8.3f},{r['hi']:+8.3f}] | "
                  f"{np.exp(r['slope']):13.2f}")

    hdr("E  CROSS-BUILD RATIOS, all-speed and speed-matched, vs the floors above")
    bands = [(0.5, 1.5), (1.5, 2.78), (2.78, 5.0), (5.0, 10.0), (10.0, 20.0), (20.0, 40.0)]
    ref = "V81/r67"
    print(f"{'build':10s} | {'a779 ratio vs V81, all speeds':>34s} | per-band point estimates")
    for route, _, _, _ in L.ROUTES:
        if route == ref:
            continue
        pt = ratio_ci(per[route], per[ref])
        pb = []
        for lo, hi in bands:
            A = [r for r in per[route] if lo <= r["v"] < hi]
            B = [r for r in per[ref] if lo <= r["v"] < hi]
            if len(A) >= 4 and len(B) >= 4:
                pb.append(f"{lo:g}-{hi:g}:{med_by_blk(A)/med_by_blk(B):.2f}(n{len(A)}/{len(B)})")
        OUT.setdefault("cross", {})[route] = dict(vs_V81=list(pt), per_band=pb)
        print(f"{route:10s} | {pt[0]:10.2f} [{pt[1]:9.2f},{pt[2]:9.2f}] | " + "  ".join(pb))

    hdr("F  SPEED CENSUS OVERLAP -- how comparable are these four routes at all?")
    print(f"{'band m/s':>12s} | " + " ".join(f"{r:>10s}" for r, _, _, _ in L.ROUTES))
    for lo, hi in bands:
        row = []
        for route, _, _, _ in L.ROUTES:
            n = sum(1 for r in per[route] if lo <= r["v"] < hi)
            row.append(f"{n:10d}")
        print(f"{lo:5g}-{hi:<5g} | " + " ".join(row))
        OUT.setdefault("census", {})[f"{lo}-{hi}"] = {
            route: sum(1 for r in per[route] if lo <= r["v"] < hi) for route, _, _, _ in L.ROUTES}

    dst = ROOT / "_scratch/cache/r6f" / "stock_baseline_search.json"
    dst.parent.mkdir(exist_ok=True)
    prev = json.loads(dst.read_text()) if dst.exists() else {}
    prev["amplitude_floor"] = OUT
    dst.write_text(json.dumps(prev, indent=1, default=float))
    print(f"\nwrote {dst}")


if __name__ == "__main__":
    main()
