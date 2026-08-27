#!/usr/bin/env python3
"""The four checks the route-4f verdict rests on, isolated so each can be audited on its own.

A  ★ THE CREEP CONTRAST UNDER BOTH RESAMPLING UNITS, and against V62/r37 ALONE. The operator's
   felt reference is "V62 fixed it and now it is back", so V62's own route is the comparator that
   matters; the V62+V65 pool is a convenience. Run at 0-10 km/h (V69 = 4.000x) and <20 km/h.

B  IS THE CREEP EFFECT ONE SEGMENT? The per-segment averaged-periodogram prominences at creep were
   29.97 / 20.60 / 1.47 / 29.15 / 18.13 for segs 0-4, and a single bad segment could carry the
   whole result. Leave-one-segment-out on the headline contrast.

C  THE Kd=1 POOL WITH AND WITHOUT V64/r35. The record is explicit: "V64 CANNOT serve as a control
   for stratified work -- 3 episodes, CIs [0.14, 61], and it drove a very different profile
   (|rate| p50 17.8 vs 2.9)." It is in the stock pool here because it is one of only three stock
   routes; the contrast is re-run without it.

D  THE COHERENCE BIAS FLOOR. Welch coherence over K averaged windows has expectation ~1/K under
   ZERO true coherence. Every coherence in this session is reprinted beside its own 1/K floor, so a
   cell with K = 2 cannot be read as a detection.

Writes `_scratch/out/_r4f_final.json`.  Usage: python studies/sessions/r4f/r4f_final_checks.py
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

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _r4f_lib as L  # noqa: E402

L.install_fs()
RNG = np.random.default_rng(20260803)
NBOOT, NULLREP = 2000, 250
OUT = {}
store = L.records()
BUILD = "V69/r4f"


def prep(rs, cellfn):
    for r in rs:
        a, b = r.get("e_18-22", np.nan), r.get("e_24-28", np.nan)
        r["bandnorm"] = (a / b) if (np.isfinite(a) and np.isfinite(b) and b > 0) else np.nan
        r["cell"] = cellfn(r)
    return rs


CELL_ER = lambda r: (G.binof(r["eff"], G.E_BINS), G.binof(r["rate"], G.R_BINS))     # noqa: E731
CELL_STD = lambda r: (r["eng"], G.binof(r["v"], G.V_BINS), G.binof(r["eff"], G.E_BINS),
                      G.binof(r["rate"], G.R_BINS))                                 # noqa: E731


def eng(names, lo=0.0, hi=1e9):
    return [r for n in names for r in store.get(n, [])
            if r["eng"] == 1 and lo <= r["v"] < hi]


def run(A, Bx, key, label, min_ep=2, min_win=4, nrep=NULLREP):
    r, lo, hi, nc, na, nb, tab, _ = G.boot_cellwise(A, Bx, key, RNG, nboot=NBOOT,
                                                    min_ep=min_ep, min_win=min_win)
    nl = G.split_half_null(A + Bx, key, RNG, nrep=nrep, min_ep=min_ep, min_win=min_win)
    v = ("INSIDE NULL" if (np.isfinite(r) and np.isfinite(nl[1]) and nl[1] <= r <= nl[2])
         else ("*** OUTSIDE NULL" if np.isfinite(r) else ""))
    ns = f"[{nl[1]:.2f},{nl[2]:.2f}]" if np.isfinite(nl[1]) else "n/a"
    print(f"  {label:<46} {r:>7.3f} [{lo:>6.3f},{hi:>8.3f}] c={nc:>2} u {na:>3}/{nb:>3} "
          f"null {ns:>13} {v}")
    return dict(ratio=float(r), lo=float(lo), hi=float(hi), ncells=int(nc), uA=int(na),
                uB=int(nb), null=[float(x) for x in nl])


# ================================================================== A ============================
L.hdr("A  ★ THE CREEP CONTRAST -- both resampling units, and V62/r37 on its own")
A_out = {}
CMP = {"V62/r37 alone": ["V62/r37"], "V65/r3a+r3b": ["V65/r3a", "V65/r3b"],
       "Kd2 pool V62+V65": L.POOL_KD2, "Kd1 stock pool": L.POOL_KD1,
       "V59/r2c alone": ["V59/r2c"]}
for band_lbl, (vlo, vhi) in (("0-10 km/h  (V69 = 4.000x)", (0.0, 10 / 3.6)),
                             ("<20 km/h   (V69 = 3.3-4.0x)", (0.0, 20 / 3.6)),
                             (">=50 km/h  (V69 = 1.000x = STOCK)", (50 / 3.6, 1e9))):
    print(f"\n  ===== {band_lbl}")
    A = prep(eng([BUILD], vlo, vhi), CELL_ER)
    print(f"        V69 n={len(A)}  blk-units={len({r['blk'] for r in A})}  "
          f"ep-units={len({r['ep'] for r in A})}  median e_18-22="
          f"{np.median(G.col(A, 'e_18-22')):.1f}")
    for cname, names in CMP.items():
        Bx = prep(eng(names, vlo, vhi), CELL_ER)
        if len(Bx) < 4 or len(A) < 4:
            print(f"    {cname:<20} *** EMPTY: V69 n={len(A)}, {cname} n={len(Bx)} -- "
                  f"this comparison cannot be made")
            A_out[f"{band_lbl}|{cname}"] = dict(empty=True, nA=len(A), nB=len(Bx))
            continue
        print(f"    --- vs {cname}  (n={len(Bx)}, median {np.median(G.col(Bx, 'e_18-22')):.1f})")
        for unit in ("blk", "ep"):
            G.EPKEY = unit
            A_out[f"{band_lbl}|{cname}|{unit}|raw"] = run(
                A, Bx, "e_18-22", f"unit={unit}  18-22 Hz raw")
            A_out[f"{band_lbl}|{cname}|{unit}|norm"] = run(
                A, Bx, "bandnorm", f"unit={unit}  18-22/24-28 normalised")
OUT["A_creep"] = A_out

# ================================================================== B ============================
L.hdr("B  LEAVE-ONE-SEGMENT-OUT on the headline (V69 engaged, all speeds, vs the Kd=2 pool)")
G.EPKEY = "blk"
Bpool = prep(eng(L.POOL_KD2), CELL_STD)
allA = prep(eng([BUILD]), CELL_STD)
full = run(allA, Bpool, "e_18-22", "ALL 8 SEGMENTS", min_ep=3, min_win=8)
B_out = {"all": full}
print()
for s in G.BUILDS[BUILD]["segs"]:
    A = [r for r in allA if r["seg"] != s]
    B_out[f"drop_s{s}"] = run(A, Bpool, "e_18-22", f"drop seg {s}  (n={len(A)})",
                              min_ep=3, min_win=8, nrep=120)
vals = [v["ratio"] for k, v in B_out.items() if k != "all" and np.isfinite(v["ratio"])]
print(f"\n  leave-one-out range {min(vals):.3f} - {max(vals):.3f} about the full-data "
      f"{full['ratio']:.3f}  ⇒ "
      f"{'NOT driven by one segment' if max(vals) / min(vals) < 1.6 else '⚠ segment-sensitive'}")
OUT["B_loso"] = B_out

# ================================================================== C ============================
L.hdr("C  THE Kd=1 STOCK POOL WITH AND WITHOUT V64/r35")
C_out = {}
for cname, names in (("V59+V64+V58 (as used)", L.POOL_KD1),
                     ("V59+V58 only (V64 dropped)", ["V59/r2c", "V58/r2b"]),
                     ("V58/r2b alone (the only stock highway route)", ["V58/r2b"])):
    Bx = prep(eng(names), CELL_STD)
    print(f"  --- {cname}: n={len(Bx)} units={len({r[G.EPKEY] for r in Bx})}")
    for key in ("e_18-22", "e_1-4"):
        C_out[f"{cname}|{key}"] = run(allA, Bx, key, f"V69 / {key}", min_ep=3, min_win=8)
OUT["C_kd1"] = C_out

# ================================================================== D ============================
L.hdr("D  THE COHERENCE BIAS FLOOR -- E[C] ~ 1/K under ZERO true coherence")
try:
    coh = json.loads((HERE / "_scratch/out/_r4f_sat_coh.json").read_text())["coherence"]
except Exception:
    coh = {}
print(f"  {'cell':<28} {'K':>5} {'1/K floor':>10} {'C max 18-22':>12} {'f':>7} "
      f"{'C/floor':>8}  verdict")
D_out = {}
for k, v in coh.items():
    if not v:
        print(f"  {k:<28} EMPTY")
        continue
    fl = 1.0 / max(v["K"], 1)
    ratio = v["c1822_max"] / fl
    D_out[k] = dict(K=v["K"], floor=fl, c=v["c1822_max"], f=v["f_at_max"], ratio=ratio)
    print(f"  {k:<28} {v['K']:>5} {fl:>10.3f} {v['c1822_max']:>12.3f} {v['f_at_max']:>7.2f} "
          f"{ratio:>8.1f}x  "
          + ("*** UNINTERPRETABLE (K too small)" if v["K"] < 8
             else ("DETECTION" if ratio > 5 else "at/near the floor")))
OUT["D_coherence_floor"] = D_out

(HERE / "_scratch/out/_r4f_final.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE / '_scratch/out/_r4f_final.json'}")
