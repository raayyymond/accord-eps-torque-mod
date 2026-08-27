#!/usr/bin/env python3
"""POWER: what size change in Q could these three routes actually have detected?

A falsifier only counts if it could have fired.  Two beds, two signal families, one answer.

BED       real MANUAL windows from each route -- the only stretches with no line in them
          (prominence 8-13x vs 34-72x engaged), so injecting into them is injecting into the
          route's OWN noise, not into white noise.
FAMILIES  (a) noise-driven 2nd-order resonance, Q = 1/(2.zeta)      -- a damped MODE
          (b) coherent tone with Wiener phase diffusion, FWHM = f0/Q -- a LIMIT CYCLE
          They are the two physical readings of the line and they do NOT have the same
          detectability, so both are swept.
SCALING   the injected component is scaled so the recovered PROMINENCE matches the median
          prominence actually measured in that arm's engaged windows.

Output: the transfer curve Q_true -> Q_app (where it saturates), and the minimum detectable
        Q ratio at the block counts these routes really have.

Usage:  python studies/damping-q/qd_power.py
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
HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import qd_lib as Q                                                       # noqa: E402
import qd_win as S                                                       # noqa: E402

RNG = np.random.default_rng(4030)
F0 = 7.79
QGRID = [5, 10, 20, 30, 50, 75, 100, 150, 250, 500, 1000, np.inf]
NREP = 60
OUT = {}


def hdr(s):
    print("\n" + "=" * 112 + "\n" + s + "\n" + "=" * 112, flush=True)


# ============================================================================================
hdr("P1  TRANSFER CURVE  Q_true -> Q_app   (real manual bed, prominence matched to engaged)")
beds, proms = {}, {}
for b in S.ROUTES:
    man = S.order_clean(S.score(S.windows(b, 1024, engaged=False)))
    eng = S.order_clean(S.score(S.windows(b, 1024)))
    beds[b] = man
    proms[b] = float(np.median([r["prom"] for r in eng])) if eng else 70.0
    print(f"  {b:5s} manual bed windows n={len(man):3d}   target prominence "
          f"{proms[b]:6.1f}x (median of that arm's engaged windows)")

curves = {}
for nw, tlab in [(1024, "10.1 s"), (2048, "20.3 s")]:
    qfloor = F0 * nw / (Q.HANN_FWHM * 101.1)
    print(f"\n  --- T = {tlab}   window-limited Q floor = {qfloor:.1f}")
    for fam in ("mode", "cycle"):
        bed_pool = []
        for b in S.ROUTES:
            for r in S.windows(b, nw, engaged=False):
                bed_pool.append(r)
        if not bed_pool:
            print("      no manual bed at this length")
            continue
        pt = float(np.median(list(proms.values())))
        row = []
        print(f"      family = {fam:6s}  (bed n={len(bed_pool)}, prominence target {pt:.0f}x)")
        for qt in QGRID:
            got = []
            for k in range(NREP):
                bed = bed_pool[RNG.integers(0, len(bed_pool))]
                y, _ = Q.inject(np.asarray(bed["x"], float), bed["fs"], F0, qt, pt, fam, RNG)
                L = Q.linewidth(y, bed["fs"])
                if np.isfinite(L["q_app"]):
                    got.append(L["q_app"])
            g = np.array(got)
            row.append(dict(q_true=float(qt), q_app_med=float(np.median(g)),
                            q_app_p16=float(np.percentile(g, 16)),
                            q_app_p84=float(np.percentile(g, 84)), n=len(g)))
            print(f"        Q_true {str(qt):>6s}  ->  Q_app {np.median(g):7.1f}  "
                  f"[p16 {np.percentile(g,16):6.1f}, p84 {np.percentile(g,84):6.1f}]  "
                  f"(= {np.median(g)/qfloor:.2f} of the floor)")
        curves[f"{tlab}/{fam}"] = dict(qfloor=float(qfloor), rows=row)
OUT["transfer"] = curves

# ============================================================================================
hdr("P2  MINIMUM DETECTABLE Q RATIO at the block counts these routes actually have")
NBLK = {"10.1 s": dict(V86=13, V86B=6, V85=11), "20.3 s": dict(V86=11, V86B=5, V85=7)}
WPB = {"10.1 s": 23 / 13, "20.3 s": 11 / 11}          # windows per blk, V86 arm
mdd = {}
for tlab in ("10.1 s", "20.3 s"):
    for fam in ("mode", "cycle"):
        key = f"{tlab}/{fam}"
        if key not in curves:
            continue
        rows = curves[key]["rows"]
        qt = np.array([r["q_true"] for r in rows])
        qa = np.array([r["q_app_med"] for r in rows])
        sd = np.array([(r["q_app_p84"] - r["q_app_p16"]) / 2 for r in rows])
        # per-window sd -> sd of the median over nA/nB blocks (median is ~1.25x noisier than mean)
        nA, nB = NBLK[tlab]["V86"], NBLK[tlab]["V86B"]
        print(f"\n  {tlab}  family={fam}   blocks V86 {nA} / V86B {nB}")
        print(f"    Q_true   Q_app   per-window sd   sd(median,V86)   sd(median,V86B)   "
              f"95% detectable Q_app shift")
        for i, q in enumerate(qt):
            sA = 1.25 * sd[i] / np.sqrt(nA)
            sB = 1.25 * sd[i] / np.sqrt(nB)
            se = np.hypot(sA, sB)
            print(f"    {str(q):>6s}  {qa[i]:6.1f}      {sd[i]:6.1f}        {sA:6.2f}"
                  f"           {sB:6.2f}            +-{1.96*se:6.2f} "
                  f"(= {1.96*se/qa[i]*100:5.1f}% of Q_app)")
        # map a detectable Q_app shift back onto Q_true via the transfer curve
        det = {}
        for i, q in enumerate(qt[:-1]):
            if not np.isfinite(q):
                continue
            sA = 1.25 * sd[i] / np.sqrt(nA)
            sB = 1.25 * sd[i] / np.sqrt(nB)
            thr = 1.96 * np.hypot(sA, sB)
            # smallest factor k such that |Q_app(k.q) - Q_app(q)| > thr
            k = np.nan
            for j in range(len(qt)):
                if np.isfinite(qt[j]) and abs(qa[j] - qa[i]) > thr:
                    r = qt[j] / q
                    if not np.isfinite(k) or abs(np.log(r)) < abs(np.log(k)):
                        k = r
            det[float(q)] = float(k)
        mdd[key] = det
        print("    => minimum detectable Q_true FACTOR, by where the truth sits: " +
              ", ".join(f"Q={int(k)}:{v:.2f}x" if np.isfinite(v) else f"Q={int(k)}:NONE"
                        for k, v in det.items()))
OUT["mdd"] = mdd

json.dump(OUT, open(ROOT / "_scratch/cache/r6f" / "qd_power.json", "w"), indent=1, default=float)
print("\nwrote _scratch/cache/r6f/qd_power.json")
