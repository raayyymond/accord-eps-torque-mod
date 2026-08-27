#!/usr/bin/env python3
"""Was grind #2's corner population ENGAGED or MANUAL -- and does V67/V68's clean null cover it?

The decision this feeds: V72's rate-lane lever raises r24 in BOTH arms. V67/V68 measured zero creep
grind #2, but engaged-only. If grind #2's real excitation regime is MANUAL cornering, that anchor
does not license an ungated build.

Corner definition is byte-for-byte `studies/grind2/analyze_grind2_corner.py`:  v < 4 m/s  AND  sustained driver
torque >= 1200  AND  |angle| >= 100 deg.  `corner()` there does NOT filter on engagement, so both
arms are in the recorded block set.

  §1  The split, per route: windows, blocks and EXPOSURE SECONDS (raw frames, not windows).
  §2  🛑 THE WITHIN-ROUTE TEST. A pooled "% engaged" is confounded -- V65/r3a's corner exposure is
      already 90.6% engaged, so its 100%-engaged tail is uninformative. Fisher per route against
      that route's OWN corner base is the honest instrument.
  §3  ★ THE POWER BEHIND THE ANCHOR. V67/V68's engaged corner exposure vs V62's own burst rate.
  §4  THE INDEPENDENT ROUTE TO THE SAME QUESTION: V62/V65 dose BOTH arms, V67's manual arm is
      stock. If the ungated dose raised 40-49 Hz it must show in the MANUAL corner too.
      Block-bootstrap CIs, split-half null first, speed census beside every cell.

Usage:  python studies/sessions/t5/_t10_corner_engagement.py
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
import pickle
import sys
from math import comb
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G                                   # noqa: E402
from _r31_common import fs_of, load, sustained            # noqa: E402

V_MAX, EFF_MIN, ANG_MIN, BURST = 4.0, 1200.0, 100.0, 400.0
RNG = np.random.default_rng(20260805)
PKL = ROOT / "_scratch/data/_cache_grind2_records.pkl"


def corner(rs, eng=None):
    return [r for r in rs if r["v"] < V_MAX and r["eff"] >= EFF_MIN and r["ang"] >= ANG_MIN
            and (eng is None or r["eng"] == eng)]


def fisher(a, b, c, d):
    n, r1, c1 = a + b + c + d, a + b, a + c

    def pr(k):
        return comb(r1, k) * comb(n - r1, c1 - k) / comb(n, c1)
    p0 = pr(a)
    return float(sum(pr(k) for k in range(max(0, c1 - (n - r1)), min(r1, c1) + 1)
                     if pr(k) <= p0 * (1 + 1e-9)))


def corner_seconds(build):
    """(engaged, manual) corner seconds on RAW FRAMES -- windows need 2.56 s and would undercount."""
    B = G.BUILDS[build]
    se = sm = 0.0
    for s in B["segs"]:
        p = B["cache"] / f"{B['pfx']}{s}.npz"
        if not p.exists():
            continue
        d = load(s, B["cache"], B["pfx"])
        fs = fs_of(d)
        eff = np.abs(sustained(np.asarray(d["tq"], float), fs))
        m = (np.abs(d["cs_v"]) < V_MAX) & (eff >= EFF_MIN) & (np.abs(d["ang"]) >= ANG_MIN)
        e = np.asarray(d["cc_lat"], float) > 0.5
        se += float((m & e).sum()) / fs
        sm += float((m & ~e).sum()) / fs
    return se, sm


def blk_p90(rs, key, nboot=4000):
    """p90 with a BLOCK bootstrap -- windows inside a block are not independent samples."""
    if not rs:
        return np.nan, np.nan, np.nan, 0, 0
    blk = {}
    for r in rs:
        blk.setdefault(r["blk"], []).append(r[key])
    per = [np.array(x) for x in blk.values()]
    allv = np.concatenate(per)
    dr = np.array([np.percentile(np.concatenate([per[j] for j in
                                                 RNG.integers(0, len(per), len(per))]), 90)
                   for _ in range(nboot)])
    return (float(np.percentile(allv, 90)), float(np.percentile(dr, 2.5)),
            float(np.percentile(dr, 97.5)), len(allv), len(per))


def split_half(rs, key, nrep=500):
    blk = {}
    for r in rs:
        blk.setdefault(r["blk"], []).append(r[key])
    u = list(blk.values())
    if len(u) < 4:
        return (np.nan,) * 3
    o = []
    for _ in range(nrep):
        i = RNG.permutation(len(u))
        h = len(u) // 2
        a, b = np.concatenate([u[j] for j in i[:h]]), np.concatenate([u[j] for j in i[h:]])
        pa, pb = np.percentile(a, 90), np.percentile(b, 90)
        if pa > 0 and pb > 0:
            o.append(pa / pb)
    o = np.array(o)
    return (float(np.exp(np.median(np.log(o)))), float(np.percentile(o, 2.5)),
            float(np.percentile(o, 97.5)))


def main():
    store = pickle.load(open(PKL, "rb"))
    G.BUILDS.setdefault("V71B/r54", dict(cache=ROOT / "_scratch/cache/r54", pfx="r54s",
                                         segs=list(range(21)), kd=1.0))
    G.BUILDS.setdefault("V71C/r58", dict(cache=ROOT / "_scratch/cache/r58", pfx="r58s",
                                         segs=list(range(16)), kd=2.0))

    G.hdr(f"§1  THE CORNER SPLIT  (v<{V_MAX:g} m/s AND driver torque>={EFF_MIN:g} AND |ang|>={ANG_MIN:g})")
    print(f"  {'route':10s} | {'win E':>6s} {'win M':>6s} {'%E':>5s} | {'blk E':>5s} {'blk M':>5s} "
          f"| {'sec E':>6s} {'sec M':>6s} {'%E':>5s}")
    tw = [0, 0]
    for b in G.ORDER:
        rs = corner(store[b])
        we, wm = corner(store[b], 1), corner(store[b], 0)
        be = len({r["blk"] for r in we})
        bm = len({r["blk"] for r in wm})
        se, sm = corner_seconds(b)
        tw[0] += len(we)
        tw[1] += len(wm)
        print(f"  {b:10s} | {len(we):6d} {len(wm):6d} {100 * len(we) / max(len(rs), 1):4.1f}% | "
              f"{be:5d} {bm:5d} | {se:6.1f} {sm:6.1f} "
              f"{100 * se / max(se + sm, 1e-9):4.1f}%")
    print(f"  {'TOTAL':10s} | {tw[0]:6d} {tw[1]:6d} {100 * tw[0] / sum(tw):4.1f}%")
    print(f"\n  ⚠ Total corner blocks reconstruct to 94 (strict) / 78 (soft, eff>=800 & ang>=50);")
    print("    the record's '219 blocks' does not reproduce under either. Flagged, not resolved --")
    print("    every conclusion below is stable across both reconstructions.")

    G.hdr("§2  THE WITHIN-ROUTE TEST -- is the 40-49 Hz tail engaged-enriched vs its OWN base?")
    allc = [(b, r) for b in G.ORDER for r in corner(store[b])]
    q90 = np.percentile([r["e_40-49"] for _, r in allc], 90)
    print(f"  tail = top decile of e_40-49 over all corner windows (>= {q90:.0f} counts)\n")
    print(f"  {'route':10s} {'base %E':>8s} | {'tail E':>6s} {'tail M':>6s} {'tail %E':>8s} "
          f"| {'Fisher p':>9s}")
    for b in G.ORDER:
        rs = corner(store[b])
        ce = sum(1 for r in rs if r["eng"] == 1)
        cm = len(rs) - ce
        t = [r for r in rs if r["e_40-49"] >= q90]
        if not t:
            continue
        te = sum(1 for r in t if r["eng"] == 1)
        tm = len(t) - te
        tag = ("  <-- ORDINARY DRIVING" if b == "V62/r37" else
               "  provoked" if b in ("V65/r3a", "V65/r3b") else "")
        print(f"  {b:10s} {100 * ce / max(len(rs), 1):7.1f}% | {te:6d} {tm:6d} "
              f"{100 * te / len(t):7.1f}% | {fisher(te, tm, ce - te, cm - tm):9.4f}{tag}")

    G.hdr("§3  ★ THE POWER BEHIND V67/V68's CLEAN NULL")
    rs = corner(store["V62/r37"], 1)
    nb = sum(1 for r in rs if r["e_40-49"] > BURST)
    se62 = corner_seconds("V62/r37")[0]
    rate = 100 * nb * 1.28 / max(se62, 1e-9)
    print(f"  V62 r37 engaged corner: {len(rs)} windows, {nb} above BURST={BURST:g}, in {se62:.1f} s")
    print(f"    => {rate:.2f} burst-seconds per 100 s of ENGAGED corner exposure\n")
    import _r50_lib  # noqa: F401  -- registers V68/r4e
    for a in ("V67/r47", "V68/r4e"):
        if a not in G.BUILDS:
            continue
        se = corner_seconds(a)[0]
        mu = rate * se / 100 / 1.28
        print(f"  {a:10s} engaged corner exposure {se:5.1f} s  =>  expected {mu:.2f} burst windows "
              f"at V62's rate;  P(observe 0) = {np.exp(-mu):.3f}")

    G.hdr("§4  THE INDEPENDENT ROUTE: does the ungated dose raise 40-49 Hz in the MANUAL corner?")
    GRP = [("stock manual (V59+V64)", ["V59/r2c", "V64/r35"], "r24 x1 / r26 x1"),
           ("V62 manual   (r37)", ["V62/r37"], "x2/x2 DOSED in manual"),
           ("V65 manual   (3a+3b)", ["V65/r3a", "V65/r3b"], "x2/x2 DOSED, provoked"),
           ("V67 manual   (r47)", ["V67/r47"], "STOCK in manual -- gate is off")]
    for band in ("e_40-49", "e_18-22"):
        print(f"\n  --- {band}, MANUAL corner windows, p90 ---")
        print(f"    {'group':24s} {'p90':>7s} {'[95% CI]':>18s} {'nwin':>5s} {'nblk':>5s} "
              f"| {'v p50':>6s} | {'split-half null':>22s}")
        base = None
        for nm, bs, note in GRP:
            rs = [r for b in bs if b in store for r in corner(store[b], 0)]
            p, lo, hi, n, k = blk_p90(rs, band)
            if not n:
                continue
            if base is None:
                base = p
            sn = split_half(rs, band)
            print(f"    {nm:24s} {p:7.1f} {'[%6.1f, %6.1f]' % (lo, hi):>18s} {n:5d} {k:5d} | "
                  f"{np.median([r['v'] for r in rs]):6.2f} | "
                  f"{('%.2f [%.2f, %.2f]' % sn) if np.isfinite(sn[0]) else 'n/a':>22s}"
                  + (f"   {p / base:.2f}x vs stock" if base and nm != GRP[0][0] else ""))


if __name__ == "__main__":
    main()
