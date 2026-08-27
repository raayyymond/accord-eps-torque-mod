#!/usr/bin/env python3
r"""TWO CORRECTIONS TO `v89_e8`, both found by its own output.

FIX 1 -- MY PLACEBO WAS TOO TIGHT, AND ITS OWN CLEANEST CASE SAYS SO.
   `v89_e8` built placebo pairs by randomly partitioning the 26 usable V89 segments, and got
   contrast sd(log) = 0.164.  But the ONE genuine cross-drive same-build pair it also computed --
   whole r75 vs whole r76 -- landed at 0.807, i.e. log −0.214 = **1.3 sigma of that same placebo**.
   A placebo that puts its own cleanest realisation at the 10th percentile is not calibrated.
   THE REASON: a random segment partition puts segments from BOTH drives in BOTH halves, which
   averages away exactly the drive-level heterogeneity (route, traffic, manoeuvre mix, tyre temp)
   that a cross-build comparison actually carries.
   ⇒ This file rebuilds the placebo from **CONTIGUOUS segment CHUNKS that never straddle a route**,
   which is the closest thing to "two different drives" the data can make, and reports both.

FIX 2 -- v >= 18.8 m/s IS NOT ORDER-CLEAN, AND THE VETO SAID SO.
   `v89_e8` claimed 18.8 m/s (67.7 km/h) is intrinsically clean because order 1 sits at 9.03 Hz.
   Its own veto then flagged 3/66, 3/175 and **26/102** windows.  The 0.8 Hz guard plus the
   2.073-2.088 m circumference sweep means order 1 must clear 9.0 + 0.8 = 9.8 Hz, i.e.
   **v >= 20.4 m/s**, and the stratum must be defined by its SLOWEST window, not its median.
   ⇒ The clean cut used here is **v >= 22.2 m/s (80 km/h)**, where order 1 is at 10.68 Hz --
   1.68 Hz of margin -- and the claim "0 windows vetoed" is CHECKED rather than asserted.
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
import pickle
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "rlog-tools"))
sys.path.insert(0, str(HERE))

import _grind2_lib as G          # noqa: E402
import compare_v75_v76_v80_grind as M   # noqa: E402
from v89_e2_h2h3 import ARMS, eng, order_hit, nblk       # noqa: E402
from v89_e3_contrast import strat_multi                  # noqa: E402
from v89_e8_placebo_and_dose import measured, pct_of, SUBJ, CTRL   # noqa: E402

RNG = np.random.default_rng(89_9999)
PKL = ROOT / "_scratch/cache/r75" / "records_v89_score.pkl"
OUTJ = ROOT / "_scratch/cache/r75" / "v89_e9_placebo_fix.json"
V_CLEAN = 22.2      # m/s == 80 km/h; order 1 = 10.68 Hz, 1.68 Hz clear of the 9 Hz band top
LEAKDOSE_SD = 1.025  # the corpus-wide cross-build placebo sd, 213 constant-alpha pairs
OUT = {}


def hdr(s):
    print("\n" + "=" * 112 + f"\n{s}\n" + "=" * 112, flush=True)


def sub(s):
    print(f"\n--- {s}", flush=True)


def chunk_placebo(pool, nrep=400, nchunk=3, tag=""):
    """Placebo pairs from CONTIGUOUS segment chunks that never straddle a route.

    Each draw: cut every route into `nchunk` contiguous blocks of segments, then randomly assign
    whole blocks to two arms.  A block is a stretch of one continuous drive, so the pair carries
    real drive-level heterogeneity instead of averaging it away.
    """
    by = {}
    for r in pool:
        by.setdefault((r["build"], r["seg"]), []).append(r)
    routes = {}
    for (b, s) in by:
        routes.setdefault(b, []).append(s)
    blocks = []
    for b, segs in routes.items():
        segs = sorted(segs)
        for part in np.array_split(np.array(segs), min(nchunk, len(segs))):
            if len(part):
                blocks.append([r for s in part for r in by[(b, s)]])
    con, rat = [], []
    for _ in range(nrep):
        p = RNG.permutation(len(blocks))
        h = len(blocks) // 2
        A = [r for i in p[:h] for r in blocks[i]]
        B = [r for i in p[h:] for r in blocks[i]]
        v, nc = strat_multi(G.episodes(A), G.episodes(B), [SUBJ, CTRL])
        if nc and np.isfinite(v[SUBJ]) and np.isfinite(v[CTRL]):
            con.append(v[SUBJ] - v[CTRL])
            rat.append(v[SUBJ])
    con, rat = np.array(con), np.array(rat)
    if not len(con):
        print(f"    {tag}: no usable partition")
        return None
    print(f"    {tag}: {len(con)}/{nrep} usable, {len(blocks)} contiguous chunks")
    print(f"      CONTRAST sd(log) {con.std():.3f}   95 % "
          f"[{np.exp(np.percentile(con,2.5)):.3f}, {np.exp(np.percentile(con,97.5)):.3f}]")
    return dict(contrast=con, sd=float(con.std()),
                lo=float(np.exp(np.percentile(con, 2.5))),
                hi=float(np.exp(np.percentile(con, 97.5))))


def verdict(m, floors):
    """One measured log-contrast against every floor we have, from tightest to most conservative."""
    if not m:
        return
    x = m["log_contrast"]
    print(f"\n    MEASURED log-contrast {x:+.3f}  (ratio {m['contrast']:.3f})")
    print(f"    {'floor':44s} {'sd(log)':>8s} {'sigma':>7s} {'95 % band':>22s}  resolvable?")
    for nm, sd, band in floors:
        s = abs(x) / sd if sd else np.nan
        ok = (band is not None) and not (band[0] <= m["contrast"] <= band[1])
        bt = f"[{band[0]:.3f}, {band[1]:.3f}]" if band else "—"
        print(f"    {nm:44s} {sd:8.3f} {s:7.2f} {bt:>22s}  "
              f"{'YES' if (ok if band else s > 1.96) else 'NO'}")
        OUT.setdefault("verdict", {})[nm] = dict(sd=float(sd), sigma=float(s),
                                                 resolvable=bool(ok if band else s > 1.96))


# =================================================================================================
if __name__ == "__main__":
    R = {k: v for k, v in pickle.load(open(PKL, "rb")).items() if not k.startswith("__")}
    E = {b: eng(R[b], b) for b in ARMS}
    POOL = E["V89/r75"] + E["V89/r76"]

    hdr("FIX 1  A PLACEBO THAT RESPECTS DRIVE STRUCTURE -- contiguous chunks, never straddling a route")
    f2 = chunk_placebo(POOL, nchunk=2, tag="V89 pool, 2 chunks/route (4 chunks)")
    f3 = chunk_placebo(POOL, nchunk=3, tag="V89 pool, 3 chunks/route (6 chunks)")
    f4 = chunk_placebo(POOL, nchunk=4, tag="V89 pool, 4 chunks/route (8 chunks)")
    sub("★ and the single genuine cross-drive same-build pair, for calibration")
    pp = measured(E["V89/r75"], E["V89/r76"], "r75 / r76 -- SAME BUILD, different drives")
    OUT["r75_vs_r76"] = pp
    for k, f in (("chunk2", f2), ("chunk3", f3), ("chunk4", f4)):
        if f:
            OUT[k] = {x: f[x] for x in ("sd", "lo", "hi")}
            if pp:
                print(f"      r75-vs-r76 sits at {abs(np.log(pp['contrast']))/f['sd']:.2f} sigma "
                      f"of the {k} floor")

    hdr("THE MEASUREMENT, ALL ENGAGED, AGAINST EVERY FLOOR WE HAVE")
    m = measured(POOL, E["V88/r73"], "V89 pooled / V88 r73")
    floors = [("v89_e8 random segment partition (TOO TIGHT)", 0.164, (0.735, 1.362))]
    if f3:
        floors.append(("contiguous 3-chunk partition, same build", f3["sd"], (f3["lo"], f3["hi"])))
    if f2:
        floors.append(("contiguous 2-chunk partition, same build", f2["sd"], (f2["lo"], f2["hi"])))
    if pp:
        floors.append(("r75-vs-r76, the one real same-build pair", abs(np.log(pp["contrast"])),
                       None))
    floors.append((f"LeakDose corpus placebo, 213 pairs", LEAKDOSE_SD, None))
    verdict(m, floors)
    OUT["measured_all"] = m

    hdr(f"FIX 2  THE STRATUM THAT IS ACTUALLY ORDER-CLEAN -- v >= {V_CLEAN} m/s "
        f"({V_CLEAN*3.6:.0f} km/h)\n"
        "   order 1 = v/2.0805 = 10.68 Hz there, 1.68 Hz clear of the 9 Hz band top with the\n"
        "   0.8 Hz guard and the 2.073-2.088 m circumference sweep.  CHECKED, not asserted.")
    H = {b: [r for r in E[b] if r["v"] >= V_CLEAN] for b in ARMS}
    for b in ARMS:
        n = len(H[b])
        hit = sum(order_hit(r["f_6-9"], r["v"]) for r in H[b])
        vs = [r["v"] for r in H[b]]
        print(f"    {b:10s} n={n:4d} blk={nblk(H[b]):3d}  v min {min(vs) if n else float('nan'):5.1f} "
              f"med {np.median(vs) if n else float('nan'):5.1f} m/s   "
              f"veto would drop {hit}/{n}  ⇒ {'✅ CLEAN' if hit == 0 else '🛑 NOT clean'}")
        OUT.setdefault("clean_census", {})[b] = dict(n=n, hits=hit, blk=nblk(H[b]))
    sub("placebo floor on this stratum (contiguous chunks, same build)")
    fh = chunk_placebo(H["V89/r75"] + H["V89/r76"], nrep=300, nchunk=3, tag="V89 highway")
    sub("the measurement on the order-clean stratum")
    mh = measured(H["V89/r75"] + H["V89/r76"], H["V88/r73"], f"V89 pooled / V88, v>={V_CLEAN}")
    OUT["clean_measured"] = mh
    if mh:
        fl = []
        if fh:
            fl.append(("contiguous 3-chunk, highway only", fh["sd"], (fh["lo"], fh["hi"])))
        fl.append(("LeakDose corpus placebo", LEAKDOSE_SD, None))
        verdict(mh, fl)

    json.dump(OUT, open(OUTJ, "w"), indent=1, default=float)
    print(f"\n  wrote {OUTJ}")
