#!/usr/bin/env python3
"""Route 67 / V81 as the FIFTH RUNG of the damper-dose grind ladder.

    build   route                                      k (loop gain)   what changed
    V74     ..._0000005d  (cache only)                  0.5799
    V76     ..._00000065--ae43aa0f27                    1.3866
    V75     ..._0000005e--857d0bd164  (pre-fault)       1.5798        faulted at t=284.805 s
    V81     ..._00000067--9b3ebbe218                    1.5798        = V75 image, 0xC407E 850->511
                                                                      + friction reverted to stock
    V80     ..._00000066--276b942769                    4.1597

🛑 V81 AND V75 SHARE k EXACTLY. V81 is the flown V75 image with a 126-byte cal revert that touches
the hard-fault interlock and the friction table -- NOT FactorC/FactorE. So the V81/V75 contrast is
the only pair in this ladder that holds the damper dose fixed, and any difference between them is
attributable to the clamp + friction (or to route/exposure, which is what the split-half null is
for).

Every number comes from `compare_v75_v76_v80_grind`'s instrument -- the same `_grind2_lib` window
cut (NFFT 256 / hop 128), the same p99 analytic band envelope, the same ~10.2 s blocks nested in
engagement runs, the same episode-level bootstrap and split-half null. This file only registers a
fifth build and re-runs the sections over five rungs instead of four.

Usage:
    python studies/grind/compare_r67_v81_grind.py records   # build/refresh the 5-build window records
    python studies/grind/compare_r67_v81_grind.py analyze   # S0-S6 over five rungs
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

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import compare_v75_v76_v80_grind as M  # noqa: E402  -- THE instrument; do not reimplement
import _grind2_lib as G  # noqa: E402

CACHE67 = ROOT / "_scratch/cache/r67x"
PFX67 = "r67xs"
SEGS67 = list(range(14))

# 🛑 k IS V75's, UNCHANGED. `0xC407E` is the hard-fault interlock and the friction table is a
# separate lane; neither appears in k = (C_Y0 * FactorE_Y[1] >> 10) / (X[1] - X[0]).
K5 = dict(M.K)
K5["V81/r67"] = 1.5798
LADDER5 = ["V74/r5d", "V76/r65", "V75/r5e", "V81/r67", "V80/r66"]
PARKED5 = dict(M.PARKED)
PARKED5["V81/r67"] = [13]           # 7.7 s tail segment, 0.0% engaged

MYPKL = CACHE67 / "records_5build_extbands.pkl"
RNG = np.random.default_rng(81_67)
OUT = {}


def register5():
    M.register()                                   # V80 + lattice fs for every build
    G.BUILDS["V81/r67"] = dict(cache=CACHE67, pfx=PFX67, segs=SEGS67, kd=K5["V81/r67"])


def build_records5(rebuild=False):
    register5()
    if MYPKL.exists() and not rebuild:
        with open(MYPKL, "rb") as fh:
            st = pickle.load(fh)
        if st.get("__bands__") == sorted(M.BANDS_EXT) and all(b in st for b in LADDER5):
            return {k: v for k, v in st.items() if not k.startswith("__")}
    # The four prior rungs come out of the instrument's OWN pickle -- read-only, never rewritten.
    base = M.build_records()
    st = {"__bands__": sorted(M.BANDS_EXT)}
    st.update(base)
    print("  wrecs V81/r67 ...", flush=True)
    rs = M.R47.augment(G.wrecs("V81/r67"))
    rs = M.augment2(rs)
    for r in rs:
        r["k"] = K5["V81/r67"]
    st["V81/r67"] = rs
    print(f"    {len(rs)} windows", flush=True)
    CACHE67.mkdir(exist_ok=True)
    with open(MYPKL, "wb") as fh:
        pickle.dump(st, fh)
    return {k: v for k, v in st.items() if not k.startswith("__")}


def eng(rs, build, lo=None, hi=None):
    out = [r for r in rs if r["eng"] == 1 and r["seg"] not in PARKED5.get(build, [])]
    if lo is not None:
        out = [r for r in out if lo <= r["v"] < hi]
    return out


def analyze():
    G.EPKEY = "blk"
    R = build_records5()
    STRATA, BAND4, hdr, nunits = M.STRATA, M.BAND4, M.hdr, M.nunits
    BANDS = [bd for _, bd in BAND4] + [M.NEGCTRL]

    # ---------------------------------------------------------------- S0 EXPOSURE ---------------
    hdr("S0  EXPOSURE CENSUS -- engaged only, parked segments dropped.  ALSO the T7 coverage table.")
    print(f"{'build':10s} {'k':>7s}  {'wins':>5s} {'sec':>7s} {'blk':>4s} {'run':>4s} | "
          + " ".join(f"{nm:>13s}" for nm, _, _ in STRATA))
    OUT["exposure"] = {}
    for b in LADDER5:
        e = eng(R[b], b)
        row = [f"{b:10s} {K5[b]:7.4f}  {len(e):5d} {len(e) * 1.28:7.1f} "
               f"{nunits(e,'blk'):4d} {nunits(e,'ep'):4d} |"]
        st = {}
        for nm, lo, hi in STRATA:
            s = eng(R[b], b, lo, hi)
            row.append(f"  {len(s):4d}w/{nunits(s,'blk'):2d}b ")
            st[nm] = dict(n=len(s), blk=nunits(s, "blk"), ep=nunits(s, "ep"),
                          sec=len(s) * 1.28,
                          v_med=float(np.median(G.col(s, "v"))) if s else float("nan"),
                          eff_med=float(np.median(G.col(s, "eff"))) if s else float("nan"),
                          rate_med=float(np.median(G.col(s, "rate"))) if s else float("nan"))
        print("".join(row))
        OUT["exposure"][b] = dict(k=K5[b], n=len(e), sec=len(e) * 1.28, strata=st)
    print("\n  per-stratum MEDIAN SPEED v (m/s) / sustained EFFORT e (counts) / |angle rate| r:")
    for nm, _, _ in STRATA:
        print(f"  {nm:14s} " + "  ".join(
            "%s: v=%5.2f e=%6.0f r=%5.1f" % (
                b.split('/')[0], OUT['exposure'][b]['strata'][nm]['v_med'],
                OUT['exposure'][b]['strata'][nm]['eff_med'],
                OUT['exposure'][b]['strata'][nm]['rate_med']) for b in LADDER5))

    # ---------------------------------------------------------------- S1 BAND TABLE -------------
    hdr("S1  SPEED-STRATIFIED BAND TABLE -- engaged only.  median [2.5%, 97.5%] block-bootstrap.\n"
        "    e_band = p99 analytic band-envelope AMPLITUDE of the torsion bar, counts (pp = 2x).")
    OUT["bands"] = {}
    for label, bd in BAND4 + [("NEGATIVE CONTROL", M.NEGCTRL)]:
        print(f"\n---- {label}   [{bd} Hz] ----")
        print(f"{'stratum':14s} {'build':10s} {'n':>4s} {'blk':>4s} | {'prominence p':>26s} | "
              f"{'envelope e (counts)':>28s}")
        for nm, lo, hi in STRATA:
            for b in LADDER5:
                s = eng(R[b], b, lo, hi)
                if len(s) < 5:
                    print(f"{nm:14s} {b:10s} {len(s):4d} {nunits(s,'blk'):4d} |"
                          f"{'-- no sample --':>26s} |")
                    continue
                pp = G.boot_median_ci(s, "p_" + bd, RNG, nboot=1500)
                ee = G.boot_median_ci(s, "e_" + bd, RNG, nboot=1500)
                print(f"{nm:14s} {b:10s} {len(s):4d} {nunits(s,'blk'):4d} |"
                      f"{pp[0]:8.2f} [{pp[1]:6.2f},{pp[2]:6.2f}] |"
                      f"{ee[0]:9.1f} [{ee[1]:7.1f},{ee[2]:7.1f}]")
                OUT["bands"].setdefault(bd, {}).setdefault(nm, {})[b] = dict(
                    n=len(s), blk=nunits(s, "blk"), p=list(pp), e=list(ee))

    # ---------------------------------------------------------------- S2 SPLIT-HALF NULL --------
    hdr("S2  SPLIT-HALF NULL -- each route halved against ITSELF, IDENTICAL estimator.\n"
        "    🛑 A ratio inside its own null interval is NOT a result.  300 halvings.")
    OUT["null"] = {}
    print(f"{'band':8s} {'build':10s} {'key':3s} {'null median':>12s} {'null 95% interval':>26s}")
    for bd in BANDS:
        for b in LADDER5:
            e = eng(R[b], b)
            for key, tag in (("e_" + bd, "e"), ("p_" + bd, "p")):
                n = G.split_half_null(e, key, RNG, nrep=300, min_ep=2, min_win=4)
                print(f"{bd:8s} {b:10s} {tag:3s} {n[0]:12.3f} [{n[1]:10.3f}, {n[2]:10.3f}]")
                OUT["null"].setdefault(bd, {}).setdefault(b, {})[tag] = list(n)
        print()

    # ---------------------------------------------------------------- S3 RATIOS -----------------
    hdr("S3  RATIOS TO V76 (the clean reference) and the V81/V75 SAME-k PAIR.\n"
        "    Cell-stratified on speed x effort x |rate| cells occupied by BOTH routes.")
    OUT["ratios"] = {}
    PAIRS = [("V81/r67", "V76/r65"), ("V81/r67", "V75/r5e"), ("V81/r67", "V80/r66"),
             ("V80/r66", "V76/r65"), ("V75/r5e", "V76/r65"), ("V81/r67", "V74/r5d")]
    for bd in BANDS:
        print(f"\n---- {bd} Hz ----")
        print(f"{'pair':16s} {'key':4s} {'ratio':>8s} {'95% CI':>20s} {'cells':>6s} "
              f"{'nA':>4s} {'nB':>4s}   verdict-vs-null")
        for A, B in PAIRS:
            for key, tag in (("e_" + bd, "e"), ("p_" + bd, "p")):
                res = G.boot_cellwise(eng(R[A], A), eng(R[B], B), key, RNG, nboot=1500,
                                      min_ep=2, min_win=4)
                nl, nlB = OUT["null"][bd][A][tag], OUT["null"][bd][B][tag]
                lo, hi = min(nl[1], nlB[1]), max(nl[2], nlB[2])
                out = "OUTSIDE null" if (res[0] < lo or res[0] > hi) else "inside null "
                ci = "CI excl 1" if (np.isfinite(res[1]) and (res[1] > 1 or res[2] < 1)) \
                    else "CI incl 1"
                print(f"{A.split('/')[0]+'/'+B.split('/')[0]:16s} {tag:4s} {res[0]:8.3f} "
                      f"[{res[1]:8.3f},{res[2]:8.3f}] {res[3]:6d} {res[4]:4d} {res[5]:4d}   "
                      f"{out}; {ci}")
                OUT["ratios"].setdefault(bd, {})[f"{A}|{B}|{tag}"] = dict(
                    ratio=res[0], lo=res[1], hi=res[2], cells=res[3], null=[lo, hi],
                    outside=bool(res[0] < lo or res[0] > hi))

    hdr("S3b  PER-STRATUM ratios of V81 to V76 and to V75 (key = e).  🛑 This is where the\n"
        "     operator's two scenarios live: creep (turn+brake) and >80 kph (lane change).")
    for bd in BANDS:
        print(f"\n---- {bd} Hz ----")
        for nm, lo_, hi_ in STRATA:
            for B in ("V76/r65", "V75/r5e", "V80/r66"):
                a = eng(R["V81/r67"], "V81/r67", lo_, hi_)
                b_ = eng(R[B], B, lo_, hi_)
                if len(a) < 8 or len(b_) < 8:
                    print(f"  {nm:14s} V81/{B.split('/')[0]:4s}  -- insufficient "
                          f"(nA={len(a)}, nB={len(b_)})")
                    continue
                res = G.boot_cellwise(a, b_, "e_" + bd, RNG, nboot=1200, min_ep=1, min_win=3)
                print(f"  {nm:14s} V81/{B.split('/')[0]:4s}  {res[0]:7.3f} "
                      f"[{res[1]:7.3f},{res[2]:7.3f}]  cells={res[3]}  nblk {res[4]}/{res[5]}")
                OUT.setdefault("strat_ratio", {}).setdefault(bd, {})[f"{nm}|{B}"] = dict(
                    ratio=res[0], lo=res[1], hi=res[2], cells=res[3])

    # ---------------------------------------------------------------- S4 DOSE RESPONSE ----------
    hdr("S4  DOSE-RESPONSE vs the damper loop gain k, five rungs, all against V76.\n"
        "    ⚠ V75 and V81 SHARE k = 1.5798, so they are a REPLICATE pair on this axis, not two\n"
        "      doses -- their spread is a direct read of the ladder's between-route noise.")
    OUT["dose"] = {}
    REF = "V76/r65"
    for bd in BANDS:
        print(f"\n---- {bd} Hz ----")
        pts = []
        for b in LADDER5:
            if b == REF:
                pts.append((K5[b], 1.0, 1.0, 1.0, b))
                print(f"  k={K5[b]:6.4f}  {b:10s}   1.000 (reference)")
                continue
            res = G.boot_cellwise(eng(R[b], b), eng(R[REF], REF), "e_" + bd, RNG,
                                  nboot=1200, min_ep=2, min_win=4)
            pts.append((K5[b], res[0], res[1], res[2], b))
            print(f"  k={K5[b]:6.4f}  {b:10s}   {res[0]:6.3f} [{res[1]:6.3f}, {res[2]:6.3f}]"
                  f"   cells={res[3]}")
        OUT["dose"][bd] = [[p[0], p[1], p[2], p[3], p[4]] for p in pts]

    # ---------------------------------------------------------------- S5 IDENTITY ---------------
    hdr("S5  LINE IDENTITY.  f0 by a FREE 12-30 Hz prominence argmax; crest; speed/amplitude slope.")
    OUT["identity"] = {}
    print(f"{'build':10s} {'n':>4s} | {'f0 12-30 Hz med [CI]':>26s} | {'sd':>5s} | "
          f"{'crest 17-23':>22s} | {'crest 40-49':>22s} | {'CV e18':>6s}")
    for b in LADDER5:
        e = [r for r in eng(R[b], b) if np.isfinite(r["f_12-30"])]
        f0 = G.boot_median_ci(e, "f_12-30", RNG, nboot=1500)
        c1 = G.boot_median_ci(e, "crest18", RNG, nboot=1200)
        c4 = G.boot_median_ci(e, "crest40", RNG, nboot=1200)
        vv = G.col(e, "e_18-22")
        vv = vv[np.isfinite(vv)]
        cv = float(np.std(vv) / np.mean(vv))
        print(f"{b:10s} {len(e):4d} | {f0[0]:7.3f} [{f0[1]:6.3f},{f0[2]:6.3f}] | "
              f"{float(np.std(G.col(e, 'f_12-30'))):5.2f} | "
              f"{c1[0]:6.3f} [{c1[1]:6.3f},{c1[2]:6.3f}] | "
              f"{c4[0]:6.3f} [{c4[1]:6.3f},{c4[2]:6.3f}] | {cv:6.3f}")
        OUT["identity"][b] = dict(f0=list(f0), crest18=list(c1), crest40=list(c4), cv18=cv,
                                  n=len(e))

    print("\n  f0 vs SPEED (Theil-Sen, Hz per m/s) -- wheel order 1 predicts +0.481, order 2 +0.961")
    for b in LADDER5:
        e = [r for r in eng(R[b], b) if np.isfinite(r["f_12-30"])]
        sv = M.theil_sen_boot(e, "v", "f_12-30", RNG, nboot=800)
        for r in e:
            r["_amp100"] = r["e_18-22"] / 100.0
        sa = M.theil_sen_boot(e, "_amp100", "f_12-30", RNG, nboot=800)
        print(f"  {b:10s} d f0/d v = {sv[0]:+7.4f} [{sv[1]:+7.4f},{sv[2]:+7.4f}] Hz/(m/s)   "
              f"d f0/d amp = {sa[0]:+7.4f} [{sa[1]:+7.4f},{sa[2]:+7.4f}] Hz/100ct")
        OUT["identity"][b]["slope_v"] = list(sv)
        OUT["identity"][b]["slope_amp"] = list(sa)

    KEYS = ("6-9", "18-22", "26-31", "32-38", "35-39", "40-49")
    print("\n  MEDIAN PROMINENCE (engaged):")
    print(f"{'build':10s} " + " ".join(f"{k:>10s}" for k in KEYS))
    for b in LADDER5:
        e = eng(R[b], b)
        print(f"{b:10s} " + " ".join(f"{np.nanmedian(G.col(e, 'p_' + k)):10.2f}" for k in KEYS))
    print("\n  MEDIAN ENVELOPE amplitude (counts):")
    print(f"{'build':10s} " + " ".join(f"{k:>10s}" for k in KEYS))
    for b in LADDER5:
        e = eng(R[b], b)
        print(f"{b:10s} " + " ".join(f"{np.nanmedian(G.col(e, 'e_' + k)):10.1f}" for k in KEYS))
        OUT.setdefault("medians", {})[b] = {k: float(np.nanmedian(G.col(e, "e_" + k)))
                                            for k in KEYS}

    # ---------------------------------------------------------------- S6 DUTY ------------------
    hdr("S6  GRIND DUTY -- fraction of ENGAGED windows above a stated 18-22 Hz amplitude.")
    OUT["duty"] = {}
    for thr in (200.0, 400.0, 600.0, 1000.0):
        print(f"\n  e_18-22 > {thr:.0f} counts (pp >= {2 * thr:.0f})")
        for b in LADDER5:
            f = M.frac_ci(eng(R[b], b), "e_18-22", thr, RNG, nboot=2000)
            print(f"    {b:10s} {100 * f[0]:6.1f}% [{100 * f[1]:5.1f}, {100 * f[2]:5.1f}]  "
                  f"of {f[3]} windows ({f[3] * 1.28:.0f} s)")
            OUT["duty"].setdefault(f"{thr:.0f}", {})[b] = list(f)
    print("\n  Per-stratum duty at pp>=1200 ct (e_18-22 > 600):")
    for nm, lo_, hi_ in STRATA:
        row = []
        for b in LADDER5:
            s = eng(R[b], b, lo_, hi_)
            if len(s) < 5:
                row.append(f"{b.split('/')[0]}:  n/a")
                continue
            f = M.frac_ci(s, "e_18-22", 600.0, RNG, nboot=1200)
            row.append(f"{b.split('/')[0]}:{100 * f[0]:5.1f}%")
        print(f"  {nm:14s} " + "   ".join(row))
        OUT.setdefault("duty_strat", {})[nm] = row

    # ---------------------------------------------------------------- S7 VALIDITY ---------------
    hdr("S7  VALIDITY -- 1-4 Hz driver-input matching check, and the 'ep' EPKEY sensitivity.")
    for A, B in [("V81/r67", "V76/r65"), ("V81/r67", "V75/r5e"), ("V81/r67", "V80/r66")]:
        res = G.boot_cellwise(eng(R[A], A), eng(R[B], B), "e_1-4", RNG, nboot=1200,
                              min_ep=2, min_win=4)
        print(f"  1-4 Hz  {A.split('/')[0]}/{B.split('/')[0]:6s}  {res[0]:6.3f} "
              f"[{res[1]:6.3f}, {res[2]:6.3f}]  cells={res[3]}")
        OUT.setdefault("validity", {})[f"1-4|{A}|{B}"] = [res[0], res[1], res[2], res[3]]
    G.EPKEY = "ep"
    for bd in ("18-22", "40-49", "26-31"):
        for A, B in [("V81/r67", "V76/r65"), ("V81/r67", "V75/r5e")]:
            res = G.boot_cellwise(eng(R[A], A), eng(R[B], B), "e_" + bd, RNG, nboot=1000,
                                  min_ep=2, min_win=4)
            print(f"  ep-key {bd:6s} {A.split('/')[0]}/{B.split('/')[0]:6s}  {res[0]:6.3f} "
                  f"[{res[1]:6.3f}, {res[2]:6.3f}]  cells={res[3]}  runs {res[4]}/{res[5]}")
            OUT.setdefault("validity", {})[f"ep|{bd}|{A}|{B}"] = [res[0], res[1], res[2], res[3]]
    G.EPKEY = "blk"

    def _san(o):
        try:
            return None if not np.isfinite(o) else float(o)
        except Exception:
            return str(o)
    (CACHE67 / "compare_5build.json").write_text(json.dumps(OUT, indent=1, default=_san))
    print(f"\nwrote {CACHE67 / 'compare_5build.json'}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "analyze"
    if cmd == "records":
        r = build_records5(rebuild="--rebuild" in sys.argv)
        for b in LADDER5:
            print(f"  {b:10s} {len(r[b]):6d} windows, engaged {len(eng(r[b], b)):6d}")
    else:
        analyze()
