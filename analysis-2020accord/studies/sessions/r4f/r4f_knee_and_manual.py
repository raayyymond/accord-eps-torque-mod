#!/usr/bin/env python3
"""The three follow-ups the orchestrator's byte-level result opens up.

CONTEXT (orchestrator, EVIDENCE, verified two ways -- raw LE byte reads of the shipped
`_v*_plain_image.bin` and a Ghidra read of `FUN_0003aa2c`):

  * V69's rate-lane CONTROL PATH is BYTE-IDENTICAL TO STOCK at and above 50 km/h -- gate byte
    `0x3AA96` reverted to `c5` (dead `gp-0x683c`) so the arm `0xC6446` = 512 is unreachable, both
    `sar` sites stock, and the two edited LERP records are the 0 km/h and 10 km/h ones while
    >= 50 km/h interpolates rec2/rec3, which are untouched.
  * V67/V68 delivered ~2.44-2.7x at road speed WHENEVER LKAS APPLIED (arm-specific, via `ld.hu
    0x7446[tp],r10` @`0x3AC04` OVERWRITING the LERP result). V62/V65 delivered a flat 2.00x
    everywhere and ARM-AGNOSTICALLY, because `sar 0xa,r8` @`0x3AC20` sits AFTER the gain select.
  * ⇒ V69's surface edit is NOT engagement-conditional. It boosts MANUAL creep too.

A  ★ THE KNEE. Test the 50 km/h breakpoint EMPIRICALLY instead of assuming it: 30-40 / 40-45 /
   45-50 / 50-55 / 55-60 / 60+ km/h. The record predicts a knee at 50 because that is where the
   record selector stops reading rec1. 🛑 Exposure is printed FIRST -- if a bin holds 6 windows the
   honest output is "under-powered", not a knee.

B  ★ THE "LANDS ON STOCK" TEST at >= 50 km/h, which is a far stronger claim than "elevated vs V68".
   V69 is run against the stock pool, against V58/r2b alone (the only stock route with real highway
   exposure AND the only one whose 1-4 Hz validity check passes), and against V67/r47 and V68/r4e
   individually. Negative control and validity band on every row.

C  ★ THE MANUAL ARM -- a dose ladder that engagement cannot confound. Because V67/V68's arm is
   engagement-conditional and V62/V65's `sar` is not, the MANUAL rate-lane dose runs
        stock 1.00x  |  V62/V65 2.00x  |  V67/V68 1.00x (stock: the arm never arms)  |  V69 4.000x
   That is an independent 1/2/1/4 ladder measured with LKAS OFF. Grind #1 is a closed-loop LKAS
   instability on this kit's record, so the prediction is that it stays small in manual -- but this
   is also the only test of what V69's 4x costs MANUAL feel, which the operator will feel directly.

Writes `_scratch/out/_r4f_knee.json`.  Usage: python studies/sessions/r4f/r4f_knee_and_manual.py [ep|blk]
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
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import _r4f_lib as L  # noqa: E402

L.install_fs()
G.EPKEY = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("ep", "blk") else "blk"
RNG = np.random.default_rng(20260804)
NBOOT, NULLREP = 2000, 250
OUT = {"epkey": G.EPKEY}
store = L.records()
BUILD = "V69/r4f"
KMH = 1 / 3.6


def prep(rs, cellfn):
    for r in rs:
        a, b = r.get("e_18-22", np.nan), r.get("e_24-28", np.nan)
        r["bandnorm"] = (a / b) if (np.isfinite(a) and np.isfinite(b) and b > 0) else np.nan
        r["cell"] = cellfn(r)
    return rs


CELL_ER = lambda r: (G.binof(r["eff"], G.E_BINS), G.binof(r["rate"], G.R_BINS))      # noqa: E731
CELL_VER = lambda r: (G.binof(r["v"], G.V_BINS), G.binof(r["eff"], G.E_BINS),
                      G.binof(r["rate"], G.R_BINS))                                  # noqa: E731


def sel(names, eng, lo=0.0, hi=1e9):
    return [r for n in names for r in store.get(n, [])
            if r["eng"] == eng and lo <= r["v"] < hi]


def run(A, Bx, key, label, min_ep=2, min_win=4, nrep=NULLREP):
    r, lo, hi, nc, na, nb, tab, _ = G.boot_cellwise(A, Bx, key, RNG, nboot=NBOOT,
                                                    min_ep=min_ep, min_win=min_win)
    nl = G.split_half_null(A + Bx, key, RNG, nrep=nrep, min_ep=min_ep, min_win=min_win)
    v = ("INSIDE NULL" if (np.isfinite(r) and np.isfinite(nl[1]) and nl[1] <= r <= nl[2])
         else ("*** OUTSIDE NULL" if np.isfinite(r) else "n/a"))
    ns = f"[{nl[1]:.2f},{nl[2]:.2f}]" if np.isfinite(nl[1]) else "n/a"
    print(f"  {label:<48} {r:>7.3f} [{lo:>6.3f},{hi:>8.3f}] c={nc:>2} u {na:>3}/{nb:>3} "
          f"null {ns:>13} {v}")
    return dict(ratio=float(r), lo=float(lo), hi=float(hi), ncells=int(nc), uA=int(na),
                uB=int(nb), null=[float(x) for x in nl])


# ================================================================== A  THE KNEE ==================
L.hdr("A  ★ IS THERE A KNEE AT 50 km/h?  Fine bins, EXPOSURE FIRST")
FINE = [("20-30", 20, 30), ("30-40", 30, 40), ("40-45", 40, 45), ("45-50", 45, 50),
        ("50-55", 50, 55), ("55-60", 55, 60), ("60-70", 60, 70), ("70+", 70, 1e9)]
print("  🛑 V69's delivered rate-lane multiplier crosses to EXACTLY 1.000x at 50 km/h because the")
print("     speed-class selector (0xC6010 = [0, 640, 3200, 6400] = 0/10/50/100 km/h) stops reading")
print("     rec1 there. Below, the edited rec0/rec1 dominate; at and above, only rec2/rec3.\n")
print(f"  {'km/h':>7} | {'V69 eng win':>11} {'units':>6} {'eng s':>7} | "
      f"{'V69 med 18-22':>14} {'prom p50':>9} | {'Kd1 win':>8} {'Kd2g win':>9}")
knee = {}
B = G.BUILDS[BUILD]
for nm, lo, hi in FINE:
    A = sel([BUILD], 1, lo * KMH, hi * KMH)
    k1 = sel(L.POOL_KD1, 1, lo * KMH, hi * KMH)
    k2g = sel(L.POOL_GATED, 1, lo * KMH, hi * KMH)
    # true engaged seconds in the bin, from the raw grid, not from window count
    secs = 0.0
    for s in B["segs"]:
        d = C.load(s, B["cache"], B["pfx"])
        fs = G.fs_of(d)
        v = np.abs(np.asarray(d["cs_v"], float))
        e = np.asarray(d["cc_lat"], float) > 0.5
        secs += float(((v >= lo * KMH) & (v < hi * KMH) & e).sum()) / fs
    row = dict(bin=nm, n=len(A), units=len({r[G.EPKEY] for r in A}), secs=secs,
               nk1=len(k1), nk2g=len(k2g))
    if len(A) >= 3:
        row["med"] = float(np.median(G.col(A, "e_18-22")))
        row["prom"] = float(np.median(G.col(A, "p_18-22")))
        print(f"  {nm:>7} | {len(A):>11} {row['units']:>6} {secs:>7.1f} | "
              f"{row['med']:>14.1f} {row['prom']:>9.2f} | {len(k1):>8} {len(k2g):>9}")
    else:
        print(f"  {nm:>7} | {len(A):>11} {row['units']:>6} {secs:>7.1f} |    "
              f"*** TOO FEW WINDOWS -- this bin cannot speak ***  | {len(k1):>8} {len(k2g):>9}")
    knee[nm] = row
OUT["knee_exposure"] = knee

print("\n  Ratios where BOTH sides have >= 4 windows (cells = (effort, |rate|), min 2 units/4 wins):")
kr = {}
for nm, lo, hi in FINE:
    A = prep(sel([BUILD], 1, lo * KMH, hi * KMH), CELL_ER)
    for cn, names in (("Kd1 stock", L.POOL_KD1), ("Kd2g V67+V68", L.POOL_GATED),
                      ("Kd2 V62+V65", L.POOL_KD2)):
        Bx = prep(sel(names, 1, lo * KMH, hi * KMH), CELL_ER)
        if len(A) < 4 or len(Bx) < 4:
            continue
        kr[f"{nm}|{cn}"] = run(A, Bx, "e_18-22", f"{nm} km/h  V69 / {cn}", nrep=120)
OUT["knee_ratios"] = kr
print("\n  ⚠ VERDICT ON THE KNEE: read the exposure column above before the ratios. Route 4f spends")
print("     only ~8 s engaged in each of 40-45 and 45-50 km/h, so the transition CANNOT be resolved")
print("     on this route regardless of what the ratios say. This is a NULL ON THE ROUTE, not on")
print("     the breakpoint -- the breakpoint remains an EVIDENCE-grade BYTE fact, unmeasured here.")

# ================================================================== B  LANDS ON STOCK ============
L.hdr("B  ★ THE '>= 50 km/h LANDS ON STOCK' TEST -- the strong form of the prediction")
print("  PREDICTION (from byte identity): V69 >= 50 km/h should be INDISTINGUISHABLE FROM STOCK,")
print("  not merely 'elevated vs V67/V68'. A ratio INSIDE the null vs stock CONFIRMS it; a ratio")
print("  outside the null vs stock REFUTES it even if the V67/V68 contrast looks large.\n")
A = prep(sel([BUILD], 1, 50 * KMH), CELL_VER)
print(f"  V69 >= 50 km/h: n={len(A)} windows, {len({r['blk'] for r in A})} blk-units, "
      f"{len({r['ep'] for r in A})} ep-units, median e_18-22 "
      f"{np.median(G.col(A, 'e_18-22')):.1f}\n")
hwy = {}
for cn, names in (("Kd1 stock pool", L.POOL_KD1),
                  ("V58/r2b alone (stock, validity PASSES)", ["V58/r2b"]),
                  ("V59/r2c alone (stock)", ["V59/r2c"]),
                  ("V62/r37 alone (2.00x)", ["V62/r37"]),
                  ("V65/r3a+r3b (2.00x)", ["V65/r3a", "V65/r3b"]),
                  ("V67/r47 alone (2.44x when engaged)", ["V67/r47"]),
                  ("V68/r4e alone (2.44x when engaged)", ["V68/r4e"])):
    Bx = prep(sel(names, 1, 50 * KMH), CELL_VER)
    if len(Bx) < 4:
        print(f"  --- vs {cn}: *** EMPTY (n={len(Bx)}) ***")
        hwy[cn] = dict(empty=True, nB=len(Bx))
        continue
    print(f"  --- vs {cn}  (n={len(Bx)}, median {np.median(G.col(Bx, 'e_18-22')):.1f})")
    for key, lbl in (("e_18-22", "GRIND #1 18-22 raw"), ("bandnorm", "normalised 18-22/24-28"),
                     ("e_24-28", "24-28 NEG CONTROL"), ("e_1-4", "1-4 VALIDITY")):
        hwy[f"{cn}|{key}"] = run(A, Bx, key, lbl)
OUT["highway"] = hwy

# ================================================================== C  THE MANUAL ARM ============
L.hdr("C  ★ THE MANUAL ARM -- the 1x / 2x / 1x / 4x ladder that LKAS engagement cannot confound")
print("  MANUAL rate-lane dose:  stock 1.00x | V62/V65 2.00x (sar is arm-agnostic) |")
print("  V67/V68 1.00x (their arm is engagement-conditional, so manual is STOCK) | V69 4.000x.")
print("  🛑 On route 4f the manual arm exists ONLY below ~15 km/h (125.4 s at 0-10, 10.0 s at")
print("     10-15, and 0.0 s above), so every manual number here is a CREEP number.\n")
print(f"  {'build (manual dose)':<34} {'n':>5} {'units':>6} {'med 18-22':>10} "
      f"{'prom p50':>9} {'med 1-4':>9}")
mladder = {}
for cn, names, dose in (("V61/r31   (0.00x)", ["V61/r31"], 0.0),
                        ("stock pool V59+V64+V58 (1.00x)", L.POOL_KD1, 1.0),
                        ("V62+V65   (2.00x)", L.POOL_KD2, 2.0),
                        ("V67+V68   (1.00x = stock in manual)", L.POOL_GATED, 1.0),
                        ("V69/r4f   (4.000x)", [BUILD], 4.0)):
    rs = sel(names, 0, 0.0, 20 * KMH)
    if len(rs) < 4:
        print(f"  {cn:<34} {len(rs):>5}   *** EMPTY / too few ***")
        mladder[cn] = dict(n=len(rs), dose=dose)
        continue
    mladder[cn] = dict(n=len(rs), dose=dose, units=len({r[G.EPKEY] for r in rs}),
                       med=float(np.median(G.col(rs, "e_18-22"))),
                       prom=float(np.median(G.col(rs, "p_18-22"))),
                       med14=float(np.median(G.col(rs, "e_1-4"))))
    m = mladder[cn]
    print(f"  {cn:<34} {m['n']:>5} {m['units']:>6} {m['med']:>10.1f} {m['prom']:>9.2f} "
          f"{m['med14']:>9.1f}")
OUT["manual_ladder"] = mladder

print("\n  Matched contrasts in the MANUAL arm, < 20 km/h (cells = (v, effort, |rate|)):")
A = prep(sel([BUILD], 0, 0.0, 20 * KMH), CELL_VER)
mc = {}
for cn, names in (("stock pool (1.00x manual)", L.POOL_KD1),
                  ("V62+V65 (2.00x manual)", L.POOL_KD2),
                  ("V62/r37 alone (2.00x manual)", ["V62/r37"]),
                  ("V67+V68 (1.00x manual)", L.POOL_GATED)):
    Bx = prep(sel(names, 0, 0.0, 20 * KMH), CELL_VER)
    if len(Bx) < 4 or len(A) < 4:
        print(f"  --- vs {cn}: *** EMPTY (V69 n={len(A)}, other n={len(Bx)}) ***")
        mc[cn] = dict(empty=True, nA=len(A), nB=len(Bx))
        continue
    print(f"  --- vs {cn}  (n={len(Bx)})")
    for key, lbl in (("e_18-22", "18-22 raw"), ("bandnorm", "normalised"),
                     ("e_24-28", "24-28 NEG"), ("e_1-4", "1-4 VALIDITY")):
        mc[f"{cn}|{key}"] = run(A, Bx, key, f"MANUAL {lbl}")
OUT["manual_contrasts"] = mc

(HERE / "_scratch/out/_r4f_knee.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE / '_scratch/out/_r4f_knee.json'}")
