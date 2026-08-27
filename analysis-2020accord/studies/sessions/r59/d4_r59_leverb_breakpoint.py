#!/usr/bin/env python3
"""D4 -> D3: the two things D3-microratchet asked for.

Q1  IS V72's LOW-RATE EFFORT RISE AN OFFSET OR A SLOPE?
    Offset (flat in |rate|)  => friction / stiction / breakaway  -> FEELS like notchiness.
    Slope  (grows with |rate|) => viscous damping                -> feels like heaviness.
    Test: the EXCESS median |bar torque| of V72 over a reference, per |rate| bin, fitted as
    excess = a + b*rate. `b` is the viscous term. Segment bootstrap on both builds.

Q2  THE LEVER-B BREAKPOINT. Lever B (FactorC/FactorE) is a BASE-ASSIST damper and stock is exactly
    ZERO below 35 km/h = 9.7222 m/s, so V72 -- and ONLY V72 -- should show a step in the low-rate
    torque statistic at that speed.
    🛑 THE PREDICTION MUST BE TESTED AS A DIFFERENCE-IN-DIFFERENCES, not as a step. Every build has
    a step at 9.72 m/s, because steering effort falls with speed for ordinary reasons (that is what
    the speed-scheduled assist surface is FOR). Only a step that V72 has and the others do not is
    evidence about Lever B. So the statistic is
        DiD = [lo/hi ratio on V72] / [lo/hi ratio on the reference]
    ⚠ Lever B is NOT LKAS-gated, so both arms are informative, but they measure different things:
    the manual arm is the driver's own hand, the engaged arm is mostly hands-off. Both are reported
    and never pooled.

Writes `_scratch/out/_d4_r59_leverb.json`.
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

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _r31_common as C  # noqa: E402

VB = 35.0 / 3.6                       # 9.7222 m/s -- Lever B's own onset speed
LOWRATE = 20.0                        # deg/s -- the bin where the V72 rise lives
RBINS = [(0, 20), (20, 50), (50, 100), (100, 200), (200, 400)]
RCTR = np.array([10.0, 35.0, 75.0, 150.0, 300.0])
ROUTES = {
    "V59 r2c":  ("_scratch/cache/r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12], []),
    "V62 r37":  ("_scratch/cache/r37", "r37s", list(range(15)), []),
    "V67 r47":  ("_scratch/cache/r47", "r47s", list(range(26)), []),
    "V69 r4f":  ("_scratch/cache/r4f", "r4fs", list(range(8)), []),
    "V70 r50":  ("_scratch/cache/r50", "r50s", [0, 1, 2], [0]),
    "V71B r54": ("_scratch/cache/r54", "r54s", list(range(21)), [10, 11]),
    "V71C r58": ("_scratch/cache/r58", "r58s", list(range(16)), [12, 13, 14, 15]),
    "V72 r59":  ("_scratch/cache/r59", "r59s", list(range(15)), [12, 13, 14]),
}
NEW = "V72 r59"
OUT = {}
RNG = np.random.default_rng(20260805)


def hdr(s):
    print("\n" + "=" * 126 + f"\n{s}\n" + "=" * 126)


def load_all():
    """Per-build frame arrays: |tq|, |rate|, |v|, engaged, segment id."""
    store = {}
    for tag, (cache, pfx, segs, skip) in ROUTES.items():
        TQ, RT, V, EN, SG = [], [], [], [], []
        for s in segs:
            if s in skip:
                continue
            p = ROOT / cache / f"{pfx}{s}.npz"
            if not p.exists():
                continue
            d = C.load(s, ROOT / cache, pfx)
            n = len(d["t"])
            TQ.append(np.abs(np.asarray(d["tq"], float)))
            RT.append(np.abs(np.asarray(d["rate_c"], float)))
            V.append(np.abs(np.asarray(d["cs_v"], float)))
            EN.append(np.asarray(d["cc_lat"], float) > 0.5)
            SG.append(np.full(n, s, float))
        store[tag] = tuple(np.concatenate(x) for x in (TQ, RT, V, EN, SG))
    return store


S = load_all()


def med_boot(tq, seg, nb=1500):
    u = np.unique(seg)
    if len(u) < 2 or len(tq) < 40:
        return (float(np.median(tq)) if len(tq) else np.nan), np.nan, np.nan
    per = [tq[seg == s] for s in u]
    dr = np.empty(nb)
    for i in range(nb):
        dr[i] = np.median(np.concatenate([per[k] for k in RNG.integers(0, len(per), len(per))]))
    return float(np.median(tq)), float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5))


# ================================================================ Q1  offset or slope =============
hdr("Q1  OFFSET OR SLOPE? Excess median |bar torque| of V72 over each reference, per |rate| bin,\n"
    "    MANUAL creep (0.3-4 m/s). Fit excess = a + b*rate: `b` is the viscous (damping) term.")
print(f"   {'reference':10s} | " + " ".join(f"{f'{lo}-{hi}':>12s}" for lo, hi in RBINS) +
      f" | {'a (offset)':>11s} {'b (viscous)':>12s} {'95% CI on b':>21s}")
q1 = {}
tq0, rt0, v0, en0, sg0 = S[NEW]
m0 = (v0 >= 0.3) & (v0 < 4.0) & ~en0
for ref in ("V71C r58", "V71B r54", "V62 r37", "V59 r2c", "V69 r4f", "V67 r47"):
    tq1, rt1, v1, en1, sg1 = S[ref]
    m1 = (v1 >= 0.3) & (v1 < 4.0) & ~en1
    exc, ok = [], []
    for lo, hi in RBINS:
        a = tq0[m0 & (rt0 >= lo) & (rt0 < hi)]
        b = tq1[m1 & (rt1 >= lo) & (rt1 < hi)]
        if len(a) < 60 or len(b) < 60:
            exc.append(np.nan)
            ok.append(False)
            continue
        exc.append(float(np.median(a) - np.median(b)))
        ok.append(True)
    ok = np.array(ok)
    if ok.sum() < 3:
        continue
    x, y = RCTR[ok], np.array(exc)[ok]
    coef = np.polyfit(x, y, 1)
    # segment bootstrap of the whole fit
    draws = np.empty(800)
    sA = [sg0[m0], tq0[m0], rt0[m0]]
    sB = [sg1[m1], tq1[m1], rt1[m1]]
    uA, uB = np.unique(sA[0]), np.unique(sB[0])
    for k in range(800):
        ia = np.isin(sA[0], RNG.choice(uA, len(uA)))
        ib = np.isin(sB[0], RNG.choice(uB, len(uB)))
        e = []
        for lo, hi in RBINS:
            a = sA[1][ia & (sA[2] >= lo) & (sA[2] < hi)]
            b = sB[1][ib & (sB[2] >= lo) & (sB[2] < hi)]
            e.append(np.median(a) - np.median(b) if (len(a) > 20 and len(b) > 20) else np.nan)
        e = np.array(e)
        g = np.isfinite(e)
        draws[k] = np.polyfit(RCTR[g], e[g], 1)[0] if g.sum() >= 3 else np.nan
    lo_b, hi_b = np.nanpercentile(draws, 2.5), np.nanpercentile(draws, 97.5)
    q1[ref] = dict(excess=exc, a=float(coef[1]), b=float(coef[0]), b_lo=float(lo_b),
                   b_hi=float(hi_b))
    print(f"   {ref:10s} | " + " ".join(f"{e:>12.0f}" if np.isfinite(e) else f"{'--':>12s}"
                                        for e in exc) +
          f" | {coef[1]:>11.0f} {coef[0]:>12.3f} [{lo_b:>8.3f},{hi_b:>9.3f}]")
print("\n   READ: `b` is counts of extra bar torque per deg/s of column rate. A viscous damper is")
print("   b > 0 with the CI clear of 0. An offset-only rise is b ~ 0 with a > 0.")
OUT["q1_offset_vs_slope"] = q1

# ================================================================ Q2  the breakpoint ==============
hdr(f"Q2  THE LEVER-B BREAKPOINT at {VB:.4f} m/s (35 km/h). Median |bar torque| in the LOW-RATE\n"
    f"    bin (|rate| < {LOWRATE:.0f} deg/s), by speed. 🛑 Read the DiD column, not the step.")
SPD = [(0.3, 4.0), (4.0, 8.0), (8.0, VB), (VB, 12.0), (12.0, 16.0), (16.0, 22.0), (22.0, 40.0)]
SNAM = ["0.3-4", "4-8", f"8-{VB:.2f}", f"{VB:.2f}-12", "12-16", "16-22", "22+"]
for arm, want in (("MANUAL", False), ("ENGAGED", True)):
    print(f"\n   --- {arm} arm, |rate| < {LOWRATE:.0f} deg/s")
    print(f"   {'route':10s} | " + " ".join(f"{n:>14s}" for n in SNAM))
    tab = {}
    for tag in ROUTES:
        tq, rt, v, en, sg = S[tag]
        base = (rt < LOWRATE) & (en if want else ~en)
        row = []
        for lo, hi in SPD:
            m = base & (v >= lo) & (v < hi)
            row.append((float(np.median(tq[m])), int(m.sum())) if m.sum() >= 60 else (np.nan, 0))
        tab[tag] = row
        print(f"   {tag:10s} | " + " ".join(f"{a:>7.0f}[{n:>5d}]" if np.isfinite(a)
                                            else f"{'--':>14s}" for a, n in row))
    # the DiD: below-vs-above the 9.72 m/s onset, V72 relative to each reference
    print(f"\n   ★ DIFFERENCE-IN-DIFFERENCES across the {VB:.2f} m/s onset "
          f"(lo = 8-{VB:.2f}, hi = {VB:.2f}-12 m/s -- adjacent bins, so speed is nearly matched):")
    print(f"   {'reference':10s} | {'V72 lo/hi':>10s} {'ref lo/hi':>10s} {'DiD':>8s}   verdict")
    did = {}
    for ref in ROUTES:
        if ref == NEW:
            continue
        a_lo, a_hi = tab[NEW][2][0], tab[NEW][3][0]
        b_lo, b_hi = tab[ref][2][0], tab[ref][3][0]
        if not all(np.isfinite(x) and x > 0 for x in (a_lo, a_hi, b_lo, b_hi)):
            print(f"   {ref:10s} |  *** a bin is empty -- no test")
            continue
        r72, rr = a_lo / a_hi, b_lo / b_hi
        did[ref] = dict(v72=r72, ref=rr, did=r72 / rr)
        print(f"   {ref:10s} | {r72:>10.3f} {rr:>10.3f} {r72 / rr:>8.3f}   "
              f"{'V72 step LARGER' if r72 / rr > 1.15 else 'V72 step SMALLER' if r72 / rr < 0.87 else 'no differential step'}")
    OUT[f"q2_{arm}"] = dict(table={k: [list(x) for x in v] for k, v in tab.items()}, did=did)

(ROOT / "_scratch/out/_d4_r59_leverb.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {ROOT / '_scratch/out/_d4_r59_leverb.json'}")
