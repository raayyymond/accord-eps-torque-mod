#!/usr/bin/env python3
"""ROUTE 59 (V72) -- GRIND #1 LADDER PLACEMENT, on the corpus's own instrument.

PRE-REGISTERED (by the orchestrator, before this ran): V72 carries V67/V68's creep multipliers, so
it should land at ~70-111 on the median-`e_18-22` engaged-creep ladder. The fork:
    ~70-111   => the rate lane is at its floor after eight builds; V73 must go OUTSIDE it.
    ~500-900  => V72 did NOT reproduce V67/V68 despite the multipliers => something else confounds
                 the whole ladder.

METRIC + ESTIMATOR are `_grind2_lib` unchanged: `e_18-22` = p99 of the analytic 18-22 Hz envelope of
one 2.56 s window on the torsion bar; medians over ENGAGED windows below 20 km/h; CIs resample
EPISODES (`blk` = ~10.2 s blocks by default, `ep` = whole engagement runs); every ratio is quoted
against a split-half null computed FIRST with the same estimator.

🛑 MEMBERSHIP IS TESTED BY SUBSAMPLING AT MATCHED EXPOSURE, NOT BY CI OVERLAP -- identical to
`studies/sessions/r58/r58_grind1.py` §2, so the verdicts are directly comparable.

⊕ EXCESS OVER CONTROL: every contrast is also reported as (18-22 ratio) / (24-28 ratio), a
difference-in-differences against the pre-declared negative control. 1-4 Hz is the
exposure-matching validity check.

🛑 TWO ROUTE-59-SPECIFIC FACTS THAT CHANGE HOW THIS IS READ, both from the shipped image:
  * V72 IS UNGATED (0x3AA96 = 0xC5) => the MANUAL arm is dosed too. It is NOT a stock control.
  * V72 reproduces V67/V68 EXACTLY only BELOW 10 km/h. Between 10 and 50 km/h the speed LERP walks
    both lanes back toward stock, so within the < 20 km/h creep band V72's r26 dose runs 0.167x
    (<10) to 0.354x (20) where V67/V68 held 0.167-0.172x throughout. The creep median speed is
    printed beside every contrast for exactly this reason.

Writes `_scratch/out/_r59_grind1.json`.  Usage: python studies/sessions/r59/r59_grind1.py [ep|blk]
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
import _r59_lib as L  # noqa: E402

L.install_fs()
G.EPKEY = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("ep", "blk") else "blk"
RNG = np.random.default_rng(20260804)
NBOOT, NULLREP = 2000, 300
CREEP = 20 / 3.6                       # 5.556 m/s -- the ladder's own creep cut
HWY = 40 / 3.6                         # 11.11 m/s -- the operator's "gone above 25 mph"
OUT = {"epkey": G.EPKEY, "creep_ms": CREEP}

store = L.records()
NEW = ["V72/r59"]

LADDER = ["V61/r31", "V59/r2c", "V64/r35", "V58/r2b", "V69/r4f", "V70/r50", "V62/r37", "V65/r3a",
          "V65/r3b", "V67/r47", "V68/r4e", "V71B/r54", "V71C/r58", "V72/r59"]
RECORDED = {"V61/r31": 2501, "V69/r4f": 746, "V70/r50": 729, "V62/r37": 268, "V71B/r54": 545,
            "V71C/r58": 223, "V65/r3a": 94, "V67/r47": 111, "V68/r4e": 70}
# (r24, r26) DELIVERED creep multipliers, swept from the shipped images (`v72_lane_model.effective`
# at 5 km/h / rateKey 400). The historical rows keep the peak-velocity price already on record so
# the table matches the kit's ladder; V72's own row is swept fresh and both are labelled below.
PRICE = {"V61/r31": (0.000, 1.000), "V59/r2c": (1.000, 1.000), "V64/r35": (1.000, 1.000),
         "V58/r2b": (1.000, 1.000), "V69/r4f": (1.000, 1.000), "V70/r50": (1.000, 1.000),
         "V62/r37": (2.000, 2.000), "V65/r3a": (2.000, 2.000), "V65/r3b": (2.000, 2.000),
         "V67/r47": (2.452, 0.167), "V68/r4e": (2.452, 0.167),
         "V71B/r54": (1.000, 2.000), "V71C/r58": (0.931, 1.000), "V72/r59": (1.862, 0.169)}

ENG_CREEP = {b: [r for r in L.driving(store.get(b, []), b) if r["eng"] == 1 and r["v"] < CREEP]
             for b in LADDER}

# ------------------------------------------------------------------ §0 census --------------------
L.hdr("§0  ROUTE 59 EXPOSURE CENSUS -- per-arm, per-speed-bin, before any statistic")
rs59 = L.driving(store["V72/r59"], "V72/r59")
allr59 = store["V72/r59"]
print(f"  windows total {len(allr59)}, driving (segs 0-11) {len(rs59)}, "
      f"parked (segs 12-14) {len(allr59) - len(rs59)}")
print(f"  {'arm':<8} {'band':<10} {'n win':>6} {'blocks':>7} {'eps':>5} {'v p50':>6} {'v p10':>6} "
      f"{'v p90':>6} {'eff p50':>8} {'rate p50':>9}")
cen = {}
for arm, e in (("engaged", 1), ("manual", 0)):
    for bn, (lo, hi) in (("creep<20", (0.0, CREEP)), ("20-40kmh", (CREEP, HWY)),
                         ("40+kmh", (HWY, 1e9)), ("all", (0.0, 1e9))):
        sel = [r for r in rs59 if r["eng"] == e and lo <= r["v"] < hi]
        if not sel:
            print(f"  {arm:<8} {bn:<10} {'0':>6}   *** EMPTY")
            cen[f"{arm}|{bn}"] = dict(n=0)
            continue
        v = G.col(sel, "v")
        cen[f"{arm}|{bn}"] = dict(n=len(sel), nblk=len({r["blk"] for r in sel}),
                                  nep=len({r["ep"] for r in sel}), v50=float(np.median(v)),
                                  v10=float(np.percentile(v, 10)), v90=float(np.percentile(v, 90)),
                                  eff50=float(np.median(G.col(sel, "eff"))),
                                  rate50=float(np.median(G.col(sel, "rate"))))
        c = cen[f"{arm}|{bn}"]
        print(f"  {arm:<8} {bn:<10} {c['n']:>6} {c['nblk']:>7} {c['nep']:>5} {c['v50']:>6.2f} "
              f"{c['v10']:>6.2f} {c['v90']:>6.2f} {c['eff50']:>8.0f} {c['rate50']:>9.1f}")
OUT["census"] = cen

print("\n  ★ WHERE THE CREEP WINDOWS ACTUALLY SIT -- V72's dose is NOT flat across this band.")
print(f"  {'arm':<8} {'<10 km/h':>10} {'10-20 km/h':>12} | delivered r24x / r26x at each")
for arm, e in (("engaged", 1), ("manual", 0)):
    sel = [r for r in rs59 if r["eng"] == e and r["v"] < CREEP]
    lo10 = sum(1 for r in sel if r["v"] < 10 / 3.6)
    print(f"  {arm:<8} {lo10:>10} {len(sel) - lo10:>12} | 1.86/0.17  and  1.99-1.87/0.22-0.31")
OUT["creep_split"] = {a: sum(1 for r in rs59 if r["eng"] == e and r["v"] < 10 / 3.6)
                      for a, e in (("engaged", 1), ("manual", 0))}

# ------------------------------------------------------------------ §1 the ladder ----------------
L.hdr("§1  ★★ THE LADDER -- median e_18-22, ENGAGED, CREEP (< 20 km/h). Identical instrument.")
print("  `r24x`/`r26x` are the DELIVERED creep multipliers on the two rate-lane paths. The V67/V68")
print("  rows carry the PEAK-VELOCITY price already on record (2.452); V72's row is the 5 km/h /")
print("  rateKey-400 sweep (1.862) -- at rateKey 1400 V72 and V67/V68 are BOTH 2.271 below 10 km/h.\n")
print(f"  {'build':<10} {'r24x':>6} {'r26x':>6} | {'n':>5} {'units':>6} {'v p50':>6} {'eff p50':>8} "
      f"{'rate p50':>8} | {'e18-22 p50':>11} {'[95% CI]':>19} {'p90':>7} {'on record':>10}")
meds = {}
for b in LADDER:
    rs = ENG_CREEP[b]
    if len(rs) < 4:
        print(f"  {b:<10} {'':>6} {'':>6} |  *** n={len(rs)} TOO FEW ***")
        meds[b] = dict(n=len(rs))
        continue
    m, lo, hi = G.boot_median_ci(rs, "e_18-22", RNG, nboot=NBOOT)
    v = G.col(rs, "e_18-22")
    meds[b] = dict(n=len(rs), units=len({r[G.EPKEY] for r in rs}), r24=PRICE[b][0],
                   r26=PRICE[b][1], med=float(m), lo=float(lo), hi=float(hi),
                   p90=float(np.percentile(v, 90)), v50=float(np.median(G.col(rs, "v"))),
                   eff50=float(np.median(G.col(rs, "eff"))),
                   rate50=float(np.median(G.col(rs, "rate"))))
    mk = " ★★" if b in NEW else ""
    rec = RECORDED.get(b, "")
    print(f"  {b:<10} {PRICE[b][0]:>6.3f} {PRICE[b][1]:>6.3f} | {len(rs):>5} "
          f"{meds[b]['units']:>6} {meds[b]['v50']:>6.2f} {meds[b]['eff50']:>8.0f} "
          f"{meds[b]['rate50']:>8.1f} | {m:>11.1f} [{lo:>7.1f},{hi:>9.1f}] "
          f"{meds[b]['p90']:>7.0f} {str(rec):>10}{mk}")
OUT["ladder"] = meds

# ------------------------------------------------------------------ §1b sub-10 km/h ladder -------
L.hdr("§1b ★ THE SAME LADDER RESTRICTED TO < 10 km/h -- where V72 IS byte-equivalent to V67/V68")
print("  The whole point: above 10 km/h V72's speed LERP walks both lanes back toward stock, so the")
print("  < 20 km/h headline mixes two different doses. This rung does not.\n")
sub = {}
print(f"  {'build':<10} {'n':>5} {'units':>6} {'v p50':>6} | {'e18-22 p50':>11} {'[95% CI]':>19}")
for b in LADDER:
    rs = [r for r in ENG_CREEP[b] if r["v"] < 10 / 3.6]
    if len(rs) < 4:
        print(f"  {b:<10} *** n={len(rs)} TOO FEW")
        sub[b] = dict(n=len(rs))
        continue
    m, lo, hi = G.boot_median_ci(rs, "e_18-22", RNG, nboot=NBOOT)
    sub[b] = dict(n=len(rs), units=len({r[G.EPKEY] for r in rs}), med=float(m), lo=float(lo),
                  hi=float(hi), v50=float(np.median(G.col(rs, "v"))))
    print(f"  {b:<10} {len(rs):>5} {sub[b]['units']:>6} {sub[b]['v50']:>6.2f} | {m:>11.1f} "
          f"[{lo:>7.1f},{hi:>9.1f}]{'  ★★' if b in NEW else ''}")
OUT["ladder_sub10"] = sub

# ------------------------------------------------------------------ §2 membership ----------------
L.hdr("§2  ★★ MEMBERSHIP BY SUBSAMPLING AT MATCHED EXPOSURE -- not by CI overlap")
print("  For each arm, draw V72's own block count from that arm's engaged-creep windows, with")
print("  replacement, and read the median. P is two-sided: 2*min(P(sim>=obs), P(sim<=obs)).\n")


def subsample_median(rs, nblk, ndraw=20000, key="e_18-22"):
    blk = {}
    for r in rs:
        blk.setdefault(r[G.EPKEY], []).append(r)
    per = [G.col(v, key) for v in blk.values()]
    per = [p[np.isfinite(p)] for p in per]
    per = [p for p in per if len(p)]
    if len(per) < 2:
        return None
    out = np.empty(ndraw)
    for i in range(ndraw):
        j = RNG.integers(0, len(per), nblk)
        out[i] = np.median(np.concatenate([per[k] for k in j]))
    return out


memb = {}
for new in NEW:
    rsN = ENG_CREEP[new]
    nb = len({r[G.EPKEY] for r in rsN})
    obs = float(np.median(G.col(rsN, "e_18-22")))
    print(f"  --- {new}:  observed median e_18-22 = {obs:.1f}  over {nb} blocks / {len(rsN)} windows")
    print(f"      {'arm':<11} {'blocks':>7} {'wins':>6} | {'sim p2.5':>9} {'sim p50':>9} "
          f"{'sim p97.5':>10} | {'P two-sided':>12}  verdict")
    for b in LADDER:
        if b == new:
            continue
        d = subsample_median(ENG_CREEP[b], nb)
        if d is None:
            print(f"      {b:<11} {'--':>7} {len(ENG_CREEP[b]):>6} |  *** too few blocks")
            continue
        pge, ple = float((d >= obs).mean()), float((d <= obs).mean())
        p = min(1.0, 2 * min(pge, ple))
        vd = ("CONSISTENT" if p > 0.05 else
              (f"EXCLUDED ({new.split('/')[0]} HIGHER)" if pge < ple
               else f"EXCLUDED ({new.split('/')[0]} LOWER)"))
        memb[f"{new}|{b}"] = dict(nblk=len({r[G.EPKEY] for r in ENG_CREEP[b]}),
                                  nwin=len(ENG_CREEP[b]), p025=float(np.percentile(d, 2.5)),
                                  p50=float(np.percentile(d, 50)),
                                  p975=float(np.percentile(d, 97.5)), p=p, obs=obs)
        print(f"      {b:<11} {memb[f'{new}|{b}']['nblk']:>7} {len(ENG_CREEP[b]):>6} | "
              f"{np.percentile(d, 2.5):>9.1f} {np.percentile(d, 50):>9.1f} "
              f"{np.percentile(d, 97.5):>10.1f} | {p:>12.4f}  {vd}")
    print()
OUT["membership"] = memb

# ------------------------------------------------------------------ §3 nulls ---------------------
L.hdr("§3  THE NOISE FLOOR FIRST -- split-half null inside each arm, identical estimator")
ARMS = {"V72/r59": ["V72/r59"], "V71C/r58": ["V71C/r58"], "V71B/r54": ["V71B/r54"],
        "stock pool": L.POOL_KD1, "V62+V65": L.POOL_KD2, "V67+V68": L.POOL_GATED,
        "V69/r4f": ["V69/r4f"], "V70/r50": ["V70/r50"]}
ENG = {k: [r for n in v for r in L.driving(store.get(n, []), n) if r["eng"] == 1]
       for k, v in ARMS.items()}
MAN = {k: [r for n in v for r in L.driving(store.get(n, []), n) if r["eng"] == 0]
       for k, v in ARMS.items()}
nulls = {}
print(f"  {'band':<8} {'arm':<14} {'median':>8} {'2.5%':>8} {'97.5%':>8}")
for band in ("1-4", "18-22", "24-28", "40-49"):
    for k, rs in ENG.items():
        m, lo, hi = G.split_half_null(rs, "e_" + band, RNG, nrep=NULLREP)
        nulls[(band, k)] = (m, lo, hi)
        print(f"  {band:<8} {k:<14} {m:>8.3f} {lo:>8.3f} {hi:>8.3f}")
    print()
OUT["nulls"] = {f"{b}|{k}": [float(x) for x in v] for (b, k), v in nulls.items()}


def contrast(A, B, key, min_ep=3, min_win=8):
    r, lo, hi, nc, na, nb, tab, _ = G.boot_cellwise(A, B, key, RNG, nboot=NBOOT,
                                                    min_ep=min_ep, min_win=min_win)
    return dict(ratio=float(r), lo=float(lo), hi=float(hi), ncells=int(nc),
                unitsA=int(na), unitsB=int(nb))


# 🛑 `_grind2_lib`'s `cell` is (eng, v, eff, rate) -- ENGAGEMENT IS ITS FIRST COMPONENT, so an
# engaged and a manual window can never share a cell. `recell` restratifies on the covariates only.
CELLFN = {"4d (eng,v,eff,rate)": lambda r: r["cell"],
          "3d (v,eff,rate) -- eng dropped": lambda r: r["cell"][1:],
          "2d (v,rate)": lambda r: (r["cell"][1], r["cell"][3]),
          "1d (v)": lambda r: (r["cell"][1],)}


def recell(rs, fn):
    out = []
    for r in rs:
        q = dict(r)
        q["cell"] = fn(r)
        out.append(q)
    return out


# ------------------------------------------------------------------ §4 matched contrasts ---------
L.hdr("§4  ★★ MATCHED CROSS-BUILD CONTRASTS, ENGAGED CREEP -- ratio > 1 = MORE grind #1 on V72")
print("  `excess` = (18-22 ratio) / (24-28 ratio): the subject band's move net of the control's.\n")
cc = {}
for new in NEW:
    A = ENG_CREEP[new]
    print(f"  --- {new}")
    print(f"      {'vs':<14} {'18-22':>8} {'[CI]':>19} {'24-28':>8} {'1-4':>8} {'excess':>8} "
          f"{'cells':>6} {'null(18-22)':>20}")
    for other in ("stock pool", "V62+V65", "V67+V68", "V71C/r58", "V71B/r54", "V69/r4f", "V70/r50"):
        Bm = [r for r in ENG[other] if r["v"] < CREEP]
        if len(Bm) < 8:
            print(f"      {other:<14}  *** n={len(Bm)} TOO FEW")
            continue
        row = {}
        for band in ("18-22", "24-28", "1-4"):
            row[band] = contrast(A, Bm, "e_" + band, min_ep=2, min_win=4)
        exc = (row["18-22"]["ratio"] / row["24-28"]["ratio"]
               if np.isfinite(row["24-28"]["ratio"]) and row["24-28"]["ratio"] > 0 else np.nan)
        nl = nulls.get(("18-22", other), (np.nan,) * 3)
        tag = ""
        if np.isfinite(nl[1]):
            inside = np.isfinite(row["18-22"]["ratio"]) and nl[1] <= row["18-22"]["ratio"] <= nl[2]
            tag = f"[{nl[1]:.2f},{nl[2]:.2f}] {'INSIDE' if inside else '*OUT*'}"
        cc[f"{new}|{other}"] = dict(row, excess=float(exc))
        print(f"      {other:<14} {row['18-22']['ratio']:>8.3f} "
              f"[{row['18-22']['lo']:>7.3f},{row['18-22']['hi']:>9.3f}] "
              f"{row['24-28']['ratio']:>8.3f} {row['1-4']['ratio']:>8.3f} {exc:>8.3f} "
              f"{row['18-22']['ncells']:>6} {tag:>20}")
    print()
OUT["contrasts"] = cc

# ------------------------------------------------------------------ §4b coarse ladder ------------
L.hdr("§4b  COARSE-STRATA LADDER -- the 4-d cell is unaffordable against the small arms")
print("  🛑 A ratio from a coarser rung is NOT comparable to the record's 4-dim ratios. Labelled.\n")
lad = {}
for lname, fn in list(CELLFN.items())[:1] + list(CELLFN.items())[2:]:
    print(f"  --- strata: {lname}")
    for new in NEW:
        A = recell(ENG_CREEP[new], fn)
        for other in ("stock pool", "V62+V65", "V67+V68", "V71C/r58", "V71B/r54", "V69/r4f",
                      "V70/r50"):
            Bm = recell([r for r in ENG[other] if r["v"] < CREEP], fn)
            if len(Bm) < 8:
                continue
            row = {bd: contrast(A, Bm, "e_" + bd, min_ep=2, min_win=4)
                   for bd in ("18-22", "24-28")}
            exc = (row["18-22"]["ratio"] / row["24-28"]["ratio"]
                   if np.isfinite(row["24-28"]["ratio"]) and row["24-28"]["ratio"] > 0 else np.nan)
            lad[f"{lname}|{new}|{other}"] = dict(row, excess=float(exc))
            print(f"      {new:<10} vs {other:<12} 18-22 {row['18-22']['ratio']:>7.3f} "
                  f"[{row['18-22']['lo']:>6.3f},{row['18-22']['hi']:>8.3f}]  "
                  f"24-28 {row['24-28']['ratio']:>6.3f}  excess {exc:>6.3f}  "
                  f"cells={row['18-22']['ncells']}")
    print()
OUT["coarse_ladder"] = lad

# ------------------------------------------------------------------ §5 engaged vs manual ---------
L.hdr("§5  WITHIN-ROUTE ENGAGED vs MANUAL")
print("  🛑 ON ROUTE 59 THE MANUAL ARM IS DOSED (V72 is UNGATED, 0x3AA96 = 0xC5), so this is an")
print("  ENGAGEMENT test, not a dose test. On route 58 the manual arm IS byte-stock; on 54 it is")
print("  dosed like 59's. Strata are (v, eff, |rate|) -- `eng` is dropped, or no cell is shared.\n")
vet = {}
for b in NEW + ["V71C/r58", "V71B/r54", "V69/r4f", "V70/r50", "V62/r37", "V67/r47"]:
    rs = recell(L.driving(store.get(b, []), b), CELLFN["3d (v,eff,rate) -- eng dropped"])
    for rn, (lo, hi) in [("creep", (0.0, CREEP)), ("20-40kmh", (CREEP, HWY)),
                         ("all speeds", (0.0, 1e9))]:
        A = [r for r in rs if r["eng"] == 1 and lo <= r["v"] < hi]
        Bm = [r for r in rs if r["eng"] == 0 and lo <= r["v"] < hi]
        if len(A) < 8 or len(Bm) < 8:
            print(f"  {b:<10} {rn:<11} *** eng n={len(A)}, man n={len(Bm)} TOO FEW")
            continue
        row = {bd: contrast(A, Bm, "e_" + bd, min_ep=2, min_win=4)
               for bd in ("18-22", "24-28", "1-4")}
        exc = (row["18-22"]["ratio"] / row["24-28"]["ratio"]
               if row["24-28"]["ratio"] > 0 else np.nan)
        vet[f"{b}|{rn}"] = dict(row, excess=float(exc), nA=len(A), nB=len(Bm),
                                medA=float(np.median(G.col(A, "e_18-22"))),
                                medB=float(np.median(G.col(Bm, "e_18-22"))))
        print(f"  {b:<10} {rn:<11} eng/man 18-22 = {row['18-22']['ratio']:>7.3f} "
              f"[{row['18-22']['lo']:>6.3f},{row['18-22']['hi']:>8.3f}]  "
              f"24-28 {row['24-28']['ratio']:>6.3f}  1-4 {row['1-4']['ratio']:>6.3f}  "
              f"excess {exc:>6.3f}  | medians eng {np.median(G.col(A, 'e_18-22')):>7.1f} "
              f"man {np.median(G.col(Bm, 'e_18-22')):>7.1f}  cells={row['18-22']['ncells']}")
OUT["eng_vs_man"] = vet

# ------------------------------------------------------------------ §6 the band table ------------
L.hdr("§6  ★ THE FULL BAND TABLE ON ROUTE 59 -- engaged/manual x creep/highway, median [95% CI]")
print("  Bands: 1-4 (driver/control -- where LEVER B's damping change would show), 18-22 (grind #1),")
print("  24-28 (negative control), 40-49 (grind #2 candidate). CIs resample "
      f"{'~10 s blocks' if G.EPKEY == 'blk' else 'whole engagement runs'}.\n")
BANDS4 = ("1-4", "18-22", "24-28", "40-49")
bt = {}
print(f"  {'arm':<8} {'speed':<11} {'n':>5} {'u':>4} " +
      " ".join(f"{'e_' + b:>22}" for b in BANDS4))
for arm, e in (("engaged", 1), ("manual", 0)):
    for rn, (lo, hi) in (("creep<20", (0.0, CREEP)), ("20-40kmh", (CREEP, HWY)),
                         ("40+kmh", (HWY, 1e9))):
        sel = [r for r in rs59 if r["eng"] == e and lo <= r["v"] < hi]
        if len(sel) < 4:
            print(f"  {arm:<8} {rn:<11} {len(sel):>5}  *** TOO FEW")
            bt[f"{arm}|{rn}"] = dict(n=len(sel))
            continue
        cells, rec = [], dict(n=len(sel), u=len({r[G.EPKEY] for r in sel}))
        for bd in BANDS4:
            m, blo, bhi = G.boot_median_ci(sel, "e_" + bd, RNG, nboot=NBOOT)
            rec[bd] = [float(m), float(blo), float(bhi)]
            cells.append(f"{m:>8.1f}[{blo:>5.0f},{bhi:>5.0f}]")
        bt[f"{arm}|{rn}"] = rec
        print(f"  {arm:<8} {rn:<11} {len(sel):>5} {rec['u']:>4} " + " ".join(cells))
OUT["bandtable"] = bt

print("\n  ★ THE SAME TABLE FOR THE COMPARISON ARMS at creep, so route 59's 1-4 Hz band has a "
      "reference.")
print(f"  {'arm':<14} {'n':>5} " + " ".join(f"{'e_' + b:>22}" for b in BANDS4))
btr = {}
for k in ("V72/r59", "V67+V68", "V71C/r58", "stock pool", "V62+V65"):
    sel = [r for r in ENG[k] if r["v"] < CREEP]
    if len(sel) < 4:
        continue
    cells, rec = [], dict(n=len(sel))
    for bd in BANDS4:
        m, blo, bhi = G.boot_median_ci(sel, "e_" + bd, RNG, nboot=NBOOT)
        rec[bd] = [float(m), float(blo), float(bhi)]
        cells.append(f"{m:>8.1f}[{blo:>5.0f},{bhi:>5.0f}]")
    btr[k] = rec
    print(f"  {k:<14} {len(sel):>5} " + " ".join(cells))
OUT["bandtable_arms"] = btr

# ------------------------------------------------------------------ §7 speed profile -------------
L.hdr("§7  ★★ THE SPEED PROFILE OF e_18-22 -- where does grind #1 collapse, and how sharply?")
print("  The operator reports grind #1 GONE above ~25 mph (40 km/h). FactorC's first breakpoint is")
print("  35.0 km/h, where stock's base damping switches on from zero -- V72 is the FIRST build to")
print("  open damping BELOW it. If the ceiling MOVED on V72 relative to the prior builds, that is")
print("  direct evidence damping controls grind #1. 🛑 The comparison arms' own profiles are")
print("  printed beside V72's, because a collapse every build shows is a PLANT property, not V72's.")
SPEED_EDGES = [(0.0, 5 / 3.6), (5 / 3.6, 10 / 3.6), (10 / 3.6, 15 / 3.6), (15 / 3.6, 20 / 3.6),
               (20 / 3.6, 25 / 3.6), (25 / 3.6, 30 / 3.6), (30 / 3.6, 35 / 3.6),
               (35 / 3.6, 40 / 3.6), (40 / 3.6, 50 / 3.6), (50 / 3.6, 70 / 3.6),
               (70 / 3.6, 1e9)]
SPEED_NAMES = ["0-5", "5-10", "10-15", "15-20", "20-25", "25-30", "30-35", "35-40", "40-50",
               "50-70", "70+"]
sp = {}
for k in ("V72/r59", "V67+V68", "V71C/r58", "stock pool", "V62+V65"):
    print(f"\n  --- {k}  (ENGAGED)")
    print(f"      {'km/h':<8} {'n':>5} {'u':>4} {'e18-22 p50':>11} {'[95% CI]':>19} "
          f"{'e24-28 p50':>11} {'ratio':>7}")
    for nm, (lo, hi) in zip(SPEED_NAMES, SPEED_EDGES):
        sel = [r for r in ENG[k] if lo <= r["v"] < hi]
        if len(sel) < 4:
            print(f"      {nm:<8} {len(sel):>5}   *** too few")
            sp[f"{k}|{nm}"] = dict(n=len(sel))
            continue
        m, blo, bhi = G.boot_median_ci(sel, "e_18-22", RNG, nboot=NBOOT)
        c = float(np.median(G.col(sel, "e_24-28")))
        sp[f"{k}|{nm}"] = dict(n=len(sel), u=len({r[G.EPKEY] for r in sel}), med=float(m),
                               lo=float(blo), hi=float(bhi), ctrl=c)
        print(f"      {nm:<8} {len(sel):>5} {len({r[G.EPKEY] for r in sel}):>4} {m:>11.1f} "
              f"[{blo:>7.1f},{bhi:>9.1f}] {c:>11.1f} {m / c if c else np.nan:>7.2f}")
OUT["speed_profile"] = sp

print("\n  ★ V72 MANUAL arm, same bins -- the operator reports grind #1 ABSENT in manual.")
print(f"      {'km/h':<8} {'n':>5} {'u':>4} {'e18-22 p50':>11} {'[95% CI]':>19} {'e24-28 p50':>11}")
spm = {}
for nm, (lo, hi) in zip(SPEED_NAMES, SPEED_EDGES):
    sel = [r for r in rs59 if r["eng"] == 0 and lo <= r["v"] < hi]
    if len(sel) < 4:
        print(f"      {nm:<8} {len(sel):>5}   *** too few")
        spm[nm] = dict(n=len(sel))
        continue
    m, blo, bhi = G.boot_median_ci(sel, "e_18-22", RNG, nboot=NBOOT)
    c = float(np.median(G.col(sel, "e_24-28")))
    spm[nm] = dict(n=len(sel), u=len({r[G.EPKEY] for r in sel}), med=float(m), lo=float(blo),
                   hi=float(bhi), ctrl=c)
    print(f"      {nm:<8} {len(sel):>5} {len({r[G.EPKEY] for r in sel}):>4} {m:>11.1f} "
          f"[{blo:>7.1f},{bhi:>9.1f}] {c:>11.1f}")
OUT["speed_profile_manual"] = spm

# ------------------------------------------------------------------ §8 the line ------------------
L.hdr("§8  IS THERE A LINE? averaged periodogram, engaged creep, located FREE in 12-30 Hz")
print("  ★ AVERAGE FIRST, PEAK-FIND AFTER, with the per-window speed census beside it.\n")
print(f"  {'arm':<12} {'K':>5} {'v mean':>7} {'v sd':>6} | {'f0(12-30)':>10} {'prom':>7} "
      f"{'wheel-1':>8} | {'18-22 sum':>11} {'24-28 sum':>11} {'ratio':>7}")
lines = {}
for k, names in ARMS.items():
    accs, Ks, vs, fref = [], 0, [], None
    for n in names:
        f, P, K, stack, meta = L.avg_periodogram(n, mask_fn=L.eng_mask, vlo=0.0, vhi=CREEP,
                                                 segs=[s for s in G.BUILDS[n]["segs"]
                                                       if s not in L.PARKED.get(n, [])])
        if P is None:
            continue
        fref, Ks = f, Ks + K
        accs.append(P * K)
        vs += [m["v"] for m in meta]
    if not accs or Ks == 0:
        print(f"  {k:<12} {'--':>5}  (no windows)")
        continue
    P, f = np.sum(accs, axis=0) / Ks, fref
    f0, pr = G.locate(f, P, 12.0, 30.0)
    b1 = float(P[(f >= 18) & (f <= 22)].sum())
    b2 = float(P[(f >= 24) & (f <= 28)].sum())
    vm = float(np.mean(vs))
    lines[k] = dict(K=Ks, v=vm, vsd=float(np.std(vs)), f0=float(f0), prom=float(pr),
                    w1=float(L.wheel_order(vm)), b1822=b1, b2428=b2)
    print(f"  {k:<12} {Ks:>5} {vm:>7.2f} {np.std(vs):>6.2f} | {f0:>10.2f} {pr:>7.2f} "
          f"{L.wheel_order(vm):>8.2f} | {b1:>11.4g} {b2:>11.4g} {b1 / b2 if b2 else np.nan:>7.2f}")
OUT["lines"] = lines

(HERE.parent / "_scratch/out/_r59_grind1.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE.parent / '_scratch/out/_r59_grind1.json'}")
