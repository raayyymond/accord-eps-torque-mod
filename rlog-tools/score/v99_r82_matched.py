#!/usr/bin/env python3
r"""🛑 THE RATE-MATCHED ENGAGED / MANUAL CONTRAST -- and a CORRECTION TO THE RECORD.

WHY THIS FILE EXISTS.  The orchestrator caught, before the contrasts were built, that the two arms
on route 82 are NOT rate-matched:

    ENGAGED (59.8 s) : micro 17.8 s · ratchet 26.6 s · macro  8.3 s   <- 14 % macro
    MANUAL  (60.2 s) : micro  4.7 s · ratchet 12.4 s · macro 30.2 s   <- 50 % macro

and `b6` is strongly rate-dependent.  A raw engaged-vs-manual `b6` duty contrast is therefore
confounded by wheel rate, **biased in the direction that manufactures a contrast**.  This script
rate-matches (and speed-matches) both arms before quoting any engaged/manual number, on BOTH
routes, so the same question can be asked of V98's headline 0.4235-vs-0.8041.

WHAT IT COMPUTES
  A  the exposure census that shows the confound, on both routes
  B  route 81's E1 bins RECOMPUTED from its own cache with THIS script's bin edges -- the V98
     numbers used in `score/v99_r82_score.py` were quoted from the brief, and a quoted number is not a
     measured one until it reproduces
  C  the RATE-MATCHED (and speed x rate matched) engaged/manual `b6` contrast, both routes, with
     the surviving matched exposure stated
  D  ⭐ the COMMON-STRATIFICATION E1 curve -- both routes on ONE set of edges, testing whether the
     whole curve shifted DOWN UNIFORMLY (the pre-registered artefact signature) or whether the
     shift is concentrated in the lever bins

🛑 `builds/v80_v107/build_v99_tva.py`: *"A change in ALL FOUR bins is an operating-point / route artefact, NOT the
   lever, and must be reported as such."*

Resampling unit is the 5.12 s contiguous block, as everywhere else in this scoring chain.
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1].parent
AN = ROOT / "analysis-2020accord"
OUT = AN / "sessions/v99"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from v97_r80_vs_v96 import episodes  # noqa: E402

KMH, FS, BLOCK_S = 3.6, 100.0, 5.12
RNG = np.random.default_rng(20260813)
M_B6 = 0x40

ROUTES = {"82": ("_scratch/cache/r82", "r82", "V99"), "81": ("_scratch/cache/r81", "r81", "V98")}
R_EDGES = [(0, 5, "0-5"), (5, 25, "5-25"), (25, 60, "25-60"), (60, 1e9, "60+")]
V_EDGES = [(0, 2), (2, 5), (5, 8), (8, 12), (12, 20), (20, 1e9)]
# the census regimes the kit already uses, for the confound table
REGIMES = [(1, 13, "micro"), (13, 50, "ratchet"), (50, 1e9, "macro")]
MIN_CELL = 30           # frames per arm per cell before a cell may carry weight


def load(r):
    cdir, stem, build = ROUTES[r]
    z = np.load(AN / cdir / f"{stem}.npz", allow_pickle=True)
    t = np.asarray(z["t"], float)
    idx = np.asarray(z["row2raw14"], int)
    b4 = (np.asarray(z["raw14_b4"], int) & 0xFF)[idx]
    assert np.all(b4 == (np.asarray(z["probe"], int) & 0xFF)), "raw14 map broken"
    ab_t, ab_mt = np.asarray(z["ab_t1ab"], float), np.asarray(z["ab_mt"], int)
    j = np.clip(np.searchsorted(ab_t, t, side="right") - 1, 0, len(ab_mt) - 1)
    d = dict(t=t, build=build, route=r, b6=(b4 & M_B6) != 0,
             eng=np.asarray(z["cc_lat"], float) > 0.5,
             v=np.asarray(z["cs_v"], float) * KMH,
             rate=np.abs(np.asarray(z["cs_rate"], float)),
             keep=ab_mt[j] != 1023)
    # 5.12 s contiguous blocks, tagged inside engaged AND inside manual runs separately
    blk = np.full(len(t), -1, int)
    bid = 0
    for sel in (d["eng"], ~d["eng"]):
        for a, b in episodes(sel, t, 1.0):
            per = int(round(BLOCK_S * FS))
            for s in range(a, b, per):
                blk[s:min(s + per, b)] = bid
                bid += 1
    d["blk"] = blk
    return d


def _cell(d, i):
    ri = max(k for k, (lo, hi, _n) in enumerate(R_EDGES) if d["rate"][i] >= lo)
    vi = max(k for k, (lo, hi) in enumerate(V_EDGES) if d["v"][i] >= lo)
    return ri, vi


def cell_ids(d):
    r = np.zeros(len(d["t"]), int)
    v = np.zeros(len(d["t"]), int)
    for k, (lo, hi, _n) in enumerate(R_EDGES):
        r[(d["rate"] >= lo) & (d["rate"] < hi)] = k
    for k, (lo, hi) in enumerate(V_EDGES):
        v[(d["v"] >= lo) & (d["v"] < hi)] = k
    return r * 100 + v


def matched_contrast(d, n_boot=2000):
    """Engaged/manual `b6` duty contrast, matched on (|rate| x speed) cells.
    Weight = min(n_eng, n_man) in the cell; cells below MIN_CELL in EITHER arm are DROPPED and the
    dropped exposure is reported.  A cell only one arm visited can never carry the contrast."""
    cid = cell_ids(d)
    E = d["eng"] & d["keep"]
    M = (~d["eng"]) & d["keep"]

    def _stat(maskE, maskM):
        num_e = num_m = den = 0.0
        for c in np.unique(cid):
            ie = maskE & (cid == c)
            im = maskM & (cid == c)
            ne, nm = int(ie.sum()), int(im.sum())
            if ne < MIN_CELL or nm < MIN_CELL:
                continue
            w = min(ne, nm)
            num_e += w * d["b6"][ie].mean()
            num_m += w * d["b6"][im].mean()
            den += w
        if den == 0:
            return np.nan, np.nan, 0.0
        return num_e / den, num_m / den, den

    pe, pm, den = _stat(E, M)
    # exposure accounting
    kept_e = kept_m = 0
    detail = {}
    for c in np.unique(cid):
        ne, nm = int((E & (cid == c)).sum()), int((M & (cid == c)).sum())
        ok = ne >= MIN_CELL and nm >= MIN_CELL
        if ok:
            kept_e += ne
            kept_m += nm
        if ne or nm:
            detail[int(c)] = dict(
                rate_bin=R_EDGES[c // 100][2], v_lo=V_EDGES[c % 100][0],
                n_eng=ne, n_man=nm, used=bool(ok),
                b6_eng=float(d["b6"][E & (cid == c)].mean()) if ne else None,
                b6_man=float(d["b6"][M & (cid == c)].mean()) if nm else None)
    # block bootstrap
    ub = np.unique(d["blk"][(E | M)])
    ub = ub[ub >= 0]
    boots = []
    for _ in range(n_boot):
        pick = RNG.choice(ub, len(ub), True)
        sel = np.zeros(len(d["t"]), bool)
        for b_ in pick:                       # union resample (blocks are disjoint by arm)
            sel |= (d["blk"] == b_)
        a, b, dn = _stat(E & sel, M & sel)
        if np.isfinite(a) and np.isfinite(b) and b > 0:
            boots.append(a - b)
    boots = np.array(boots)
    return dict(b6_eng_matched=pe, b6_man_matched=pm, diff=pe - pm,
                diff_ci=[float(np.percentile(boots, 2.5)),
                         float(np.percentile(boots, 97.5))] if len(boots) > 50 else [None, None],
                matched_weight=den, kept_eng_frames=kept_e, kept_man_frames=kept_m,
                total_eng_frames=int(E.sum()), total_man_frames=int(M.sum()),
                raw_b6_eng=float(d["b6"][E].mean()), raw_b6_man=float(d["b6"][M].mean()),
                cells=detail)


def main():
    res = {}
    D = {r: load(r) for r in ROUTES}
    print("=" * 98)
    print("  RATE-MATCHED ENGAGED / MANUAL CONTRAST -- and a CORRECTION TO THE RECORD")
    print("=" * 98)

    # ---------------- A  the confound, both routes ----------------
    print("\n=== A  THE CONFOUND.  Wheel-rate composition of the two arms, both routes. ===")
    res["A_census"] = {}
    for r, d in D.items():
        res["A_census"][r] = {}
        print(f"  r{r} ({d['build']}):")
        for nm, sel in (("ENGAGED", d["eng"]), ("MANUAL", ~d["eng"])):
            tot = int(sel.sum())
            row, reg = [], []
            for lo, hi, bn in R_EDGES:
                m = int((sel & (d["rate"] >= lo) & (d["rate"] < hi)).sum())
                row.append(f"{bn}:{100*m/tot:5.1f}%")
            for lo, hi, bn in REGIMES:
                m = int((sel & (d["rate"] >= lo) & (d["rate"] < hi)).sum())
                reg.append(f"{bn} {m/FS:5.1f}s")
            res["A_census"][r][nm] = dict(frames=tot, bins=row, regimes=reg)
            print(f"    {nm:8s} n={tot:6d}   " + "  ".join(row) + "   |  " + "  ".join(reg))
        e60 = float((d["rate"][d["eng"]] >= 60).mean())
        m60 = float((d["rate"][~d["eng"]] >= 60).mean())
        res["A_census"][r]["macro_skew"] = m60 / e60 if e60 else None
        print(f"    ⇒ MANUAL is {m60/e60:.2f}x more 60+ deg/s weighted than ENGAGED")

    # ---------------- B  does the quoted V98 reproduce? ----------------
    print("\n=== B  ROUTE 81's E1 BINS, RECOMPUTED FROM ITS OWN CACHE ON THESE EDGES ===")
    print("    (the V98 numbers used in score/v99_r82_score.py were QUOTED from the brief; a quoted")
    print("     number is not a measured one until it reproduces)")
    QUOTED = {"0-5": (894, 0.4911), "5-25": (2469, 0.3556),
              "25-60": (1781, 0.3268), "60+": (1447, 0.6164)}
    d81 = D["81"]
    sel81 = d81["eng"] & d81["keep"]
    res["B_recompute_r81"] = {}
    ok_all = True
    for lo, hi, bn in R_EDGES:
        m = sel81 & (d81["rate"] >= lo) & (d81["rate"] < hi)
        n, p = int(m.sum()), float(d81["b6"][m].mean())
        qn, qp = QUOTED[bn]
        ok = (n == qn) and abs(p - qp) < 5e-4
        ok_all &= ok
        res["B_recompute_r81"][bn] = dict(n=n, duty=p, quoted_n=qn, quoted_duty=qp,
                                          reproduces=bool(ok))
        print(f"    {bn:6s} n={n:5d} (quoted {qn:5d})   b6={p:.4f} (quoted {qp:.4f})   "
              f"{'✅ reproduces' if ok else '🛑 DOES NOT REPRODUCE'}")
    res["B_recompute_r81"]["all_reproduce"] = bool(ok_all)
    print(f"    ⇒ {'✅ the V98 reference numbers are MEASURED, not merely quoted'if ok_all else '🛑 the V98 reference does NOT reproduce -- do not use it'}")

    # ---------------- C  the matched contrast ----------------
    print("\n=== C  ⭐ THE RATE-MATCHED (|rate| x speed) ENGAGED / MANUAL b6 CONTRAST ===")
    print(f"    Cells: 4 |rate| bins x 6 speed bins.  A cell needs >= {MIN_CELL} frames in BOTH")
    print("    arms or it is DROPPED.  Weight = min(n_eng, n_man).  Block-bootstrap CI.")
    res["C_matched"] = {}
    for r, d in D.items():
        m = matched_contrast(d)
        res["C_matched"][r] = m
        used = [c for c in m["cells"].values() if c["used"]]
        print(f"\n    r{r} ({d['build']}):")
        print(f"      RAW      engaged {m['raw_b6_eng']:.4f}  manual {m['raw_b6_man']:.4f}   "
              f"diff {m['raw_b6_eng']-m['raw_b6_man']:+.4f}   <- CONFOUNDED")
        print(f"      MATCHED  engaged {m['b6_eng_matched']:.4f}  manual {m['b6_man_matched']:.4f}"
              f"   diff {m['diff']:+.4f}  95% CI "
              f"[{m['diff_ci'][0]:+.4f}, {m['diff_ci'][1]:+.4f}]"
              if m["diff_ci"][0] is not None else "")
        print(f"      matched exposure: {len(used)} cells used; "
              f"{m['kept_eng_frames']:,}/{m['total_eng_frames']:,} engaged frames "
              f"({100*m['kept_eng_frames']/m['total_eng_frames']:.1f} %) and "
              f"{m['kept_man_frames']:,}/{m['total_man_frames']:,} manual "
              f"({100*m['kept_man_frames']/m['total_man_frames']:.1f} %) survive matching")
        shrink = ((m["raw_b6_eng"] - m["raw_b6_man"]) - m["diff"])
        print(f"      ⇒ matching moved the contrast by {shrink:+.4f} "
              f"({100*abs(shrink)/abs(m['raw_b6_eng']-m['raw_b6_man']):.0f} % of the raw contrast)")
        print(f"      per-cell (rate x speed, cells actually used):")
        for c in sorted(used, key=lambda x: (x["rate_bin"], x["v_lo"])):
            print(f"        |rate| {c['rate_bin']:6s} v>={c['v_lo']:4.0f}  "
                  f"nE={c['n_eng']:5d} nM={c['n_man']:5d}  "
                  f"b6 eng {c['b6_eng']:.4f}  man {c['b6_man']:.4f}  "
                  f"diff {c['b6_eng']-c['b6_man']:+.4f}")

    # ---------------- D  the common-stratification E1 curve ----------------
    print("\n=== D  ⭐ COMMON STRATIFICATION -- both routes, ONE set of edges, ENGAGED only ===")
    print("    Testing the pre-registered artefact signature: did the WHOLE curve shift down")
    print("    uniformly, or is the shift concentrated in the LEVER bins?")
    print(f"\n    {'bin':8s} {'role':10s} {'V99 n':>7s} {'V99 b6':>8s} {'V98 n':>7s} "
          f"{'V98 b6':>8s} {'delta':>8s} {'ratio':>8s}")
    res["D_common"] = {}
    rows = []
    for lo, hi, bn in R_EDGES:
        e = {}
        for r, d in D.items():
            m = d["eng"] & d["keep"] & (d["rate"] >= lo) & (d["rate"] < hi)
            e[r] = (int(m.sum()), float(d["b6"][m].mean()))
        role = "LEVER" if lo < 25 else "CONTROL"
        delta = e["82"][1] - e["81"][1]
        ratio = e["82"][1] / e["81"][1]
        rows.append((bn, role, delta, ratio))
        res["D_common"][bn] = dict(role=role, v99_n=e["82"][0], v99_duty=e["82"][1],
                                   v98_n=e["81"][0], v98_duty=e["81"][1],
                                   delta=delta, ratio=ratio)
        print(f"    {bn:8s} {role:10s} {e['82'][0]:7d} {e['82'][1]:8.4f} {e['81'][0]:7d} "
              f"{e['81'][1]:8.4f} {delta:+8.4f} {ratio:8.4f}")

    lev = [x for x in rows if x[1] == "LEVER"]
    ctl = [x for x in rows if x[1] == "CONTROL"]
    lr = float(np.mean([x[3] for x in lev]))
    cr = float(np.mean([x[3] for x in ctl]))
    res["D_common"]["mean_ratio_lever"] = lr
    res["D_common"]["mean_ratio_control"] = cr
    res["D_common"]["all_same_sign"] = bool(len(set(np.sign([x[2] for x in rows]))) == 1)
    print(f"\n    mean V99/V98 duty RATIO:  LEVER bins {lr:.4f}   CONTROL bins {cr:.4f}")
    print(f"    all four deltas share a sign: {res['D_common']['all_same_sign']}")
    if res["D_common"]["all_same_sign"]:
        print("    🛑 ALL FOUR BINS MOVED IN THE SAME DIRECTION.  Per builds/v80_v107/build_v99_tva.py this is the")
        print("       OPERATING-POINT / ROUTE ARTEFACT signature and must be reported as such.")
        sep = abs(lr - cr)
        print(f"       Lever-vs-control separation in the ratio: {sep:.4f} "
              f"({100*sep/max(cr,1e-9):.1f} % of the control ratio)")

    (OUT / "v99_r82_matched.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"\nwrote {OUT/'v99_r82_matched.json'}")
    return res


if __name__ == "__main__":
    main()
