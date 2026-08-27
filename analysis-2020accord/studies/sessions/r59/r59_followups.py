#!/usr/bin/env python3
"""ROUTE 59 (V72) FOLLOW-UPS -- the checks the headline in `studies/sessions/r59/r59_grind1.py` demands.

`studies/sessions/r59/r59_grind1.py` put V72 at median `e_18-22` = 614 engaged creep, i.e. in the STOCK region and not
at V67/V68's 70-111. That is the pre-registered "major finding" branch, so it has to survive:

  A  THE EXACT-DOSE-MATCH STRATUM. V72 == V67/V68 byte-for-byte in BOTH lanes only below 10 km/h.
     Contrast them THERE, on several strata, with each arm's own split-half null beside it.
  B  BIN-BY-BIN. A pooled creep median mixes speeds at which V72's dose differs by 2x on r26.
     Simpson's paradox produced a fake f0 shift in this kit; stratify before pooling.
  C  THE 35 km/h STEP. FactorC's first breakpoint is 35.0 km/h. Test whether V72's collapse is
     sharp THERE and whether it is sharper than the other arms' -- a collapse every build shows is
     a plant property, not V72's.
  D  THE MANUAL ARM AT MATCHED SPEED. V72's manual creep windows are 83% standstill, so the raw
     eng/man ratio is confounded with the car being stopped. Redo it inside 5-10 km/h.
  E  EMPTY IS NOT NULL. P(observe 0) under a stated alternative for every empty cell.
  F  LEVER B. The 1-4 Hz band, stratified, engaged and manual.
  G  SENSITIVITY. The headline under both resampling units and both cell definitions.

Writes `_scratch/out/_r59_followups.json`.  Usage: python studies/sessions/r59/r59_followups.py
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
import _r59_lib as L  # noqa: E402

L.install_fs()
RNG = np.random.default_rng(20260805)
NBOOT, NULLREP = 2000, 300
CREEP, SUB10 = 20 / 3.6, 10 / 3.6
OUT = {}

store = L.records()
ARMS = {"V72/r59": ["V72/r59"], "V67+V68": L.POOL_GATED, "V71C/r58": ["V71C/r58"],
        "V71B/r54": ["V71B/r54"], "stock pool": L.POOL_KD1, "V62+V65": L.POOL_KD2,
        "V69/r4f": ["V69/r4f"], "V70/r50": ["V70/r50"]}


def arm(k, eng=1, lo=0.0, hi=1e9):
    return [r for n in ARMS[k] for r in L.driving(store.get(n, []), n)
            if r["eng"] == eng and lo <= r["v"] < hi]


CELLFN = {"4d (eng,v,eff,rate)": lambda r: r["cell"],
          "3d (v,eff,rate)": lambda r: r["cell"][1:],
          "2d (v,eff)": lambda r: (r["cell"][1], r["cell"][2]),
          "2d (v,rate)": lambda r: (r["cell"][1], r["cell"][3]),
          "1d (v)": lambda r: (r["cell"][1],)}


def recell(rs, fn):
    out = []
    for r in rs:
        q = dict(r)
        q["cell"] = fn(r)
        out.append(q)
    return out


def contrast(A, B, key, min_ep=2, min_win=4):
    r, lo, hi, nc, na, nb, tab, _ = G.boot_cellwise(A, B, key, RNG, nboot=NBOOT,
                                                    min_ep=min_ep, min_win=min_win)
    return dict(ratio=float(r), lo=float(lo), hi=float(hi), ncells=int(nc))


# ================================================================== A =============================
L.hdr("§A  ★★ THE EXACT-DOSE-MATCH STRATUM: V72 vs V67+V68 BELOW 10 km/h")
print("  Below 10 km/h V72's delivered surface is IDENTICAL to V67/V68's in BOTH lanes at every")
print("  rate index (r24 1.862/2.271, r26 0.169/0.208 at rateKey 400/1400 -- swept from the shipped")
print("  images). If the rate lane were the whole story these two must agree HERE.\n")
for k in ("V72/r59", "V67+V68", "V71C/r58", "stock pool", "V62+V65"):
    for nm, (lo, hi) in (("<10 km/h", (0.0, SUB10)), ("5-10 km/h", (5 / 3.6, SUB10))):
        rs = arm(k, 1, lo, hi)
        if len(rs) < 3:
            print(f"  {k:<12} {nm:<10} *** n={len(rs)} TOO FEW")
            continue
        m, a, b = G.boot_median_ci(rs, "e_18-22", RNG, nboot=NBOOT)
        print(f"  {k:<12} {nm:<10} n={len(rs):>4} u={len({r['blk'] for r in rs}):>3} "
              f"v p50={np.median(G.col(rs, 'v')):>5.2f}  eff p50={np.median(G.col(rs, 'eff')):>6.0f} "
              f"rate p50={np.median(G.col(rs, 'rate')):>6.1f} | e18-22 {m:>7.1f} [{a:>7.1f},{b:>8.1f}]")
print()
Asub = {}
for nm, (lo, hi) in (("<10 km/h", (0.0, SUB10)), ("5-10 km/h", (5 / 3.6, SUB10))):
    A = arm("V72/r59", 1, lo, hi)
    print(f"  --- V72 vs each arm, ENGAGED, {nm}   (ratio > 1 = MORE grind #1 on V72)")
    print(f"      {'vs':<12} {'strata':<20} {'18-22':>8} {'[95% CI]':>19} {'24-28':>8} "
          f"{'1-4':>7} {'excess':>7} {'cells':>6}")
    for other in ("V67+V68", "V71C/r58", "stock pool", "V62+V65"):
        B = arm(other, 1, lo, hi)
        if len(B) < 6:
            print(f"      {other:<12} *** n={len(B)} TOO FEW")
            continue
        for sname, fn in CELLFN.items():
            if sname.startswith("4d"):
                continue
            rw = {bd: contrast(recell(A, fn), recell(B, fn), "e_" + bd)
                  for bd in ("18-22", "24-28", "1-4")}
            exc = (rw["18-22"]["ratio"] / rw["24-28"]["ratio"]
                   if np.isfinite(rw["24-28"]["ratio"]) and rw["24-28"]["ratio"] > 0 else np.nan)
            Asub[f"{nm}|{other}|{sname}"] = dict(rw, excess=float(exc))
            print(f"      {other:<12} {sname:<20} {rw['18-22']['ratio']:>8.3f} "
                  f"[{rw['18-22']['lo']:>7.3f},{rw['18-22']['hi']:>9.3f}] "
                  f"{rw['24-28']['ratio']:>8.3f} {rw['1-4']['ratio']:>7.3f} {exc:>7.3f} "
                  f"{rw['18-22']['ncells']:>6}")
    print()
OUT["dose_match"] = Asub

print("  THE NULL FOR THIS STRATUM -- split-half inside each arm, same estimator, 2d (v,eff):")
for k in ("V72/r59", "V67+V68", "stock pool"):
    rs = recell(arm(k, 1, 0.0, SUB10), CELLFN["2d (v,eff)"])
    m, a, b = G.split_half_null(rs, "e_18-22", RNG, nrep=NULLREP, min_ep=2, min_win=4)
    print(f"      {k:<12} null median {m:>6.3f}  [{a:>6.3f},{b:>6.3f}]")
    OUT[f"null_sub10|{k}"] = [float(m), float(a), float(b)]

print("\n  MATCHED-EXPOSURE SUBSAMPLING inside <10 km/h (V72's own block count drawn from each arm):")
A = arm("V72/r59", 1, 0.0, SUB10)
nb, obs = len({r["blk"] for r in A}), float(np.median(G.col(A, "e_18-22")))
print(f"      V72 observed {obs:.1f} over {nb} blocks / {len(A)} windows")
for other in ("V67+V68", "V71C/r58", "stock pool", "V62+V65", "V62/r37", "V71B/r54"):
    rs = (arm(other, 1, 0.0, SUB10) if other in ARMS
          else [r for r in L.driving(store[other], other)
                if r["eng"] == 1 and r["v"] < SUB10])
    blk = {}
    for r in rs:
        blk.setdefault(r["blk"], []).append(r)
    per = [G.col(v, "e_18-22") for v in blk.values()]
    if len(per) < 2:
        print(f"      {other:<12} *** {len(per)} blocks -- cannot subsample")
        continue
    d = np.array([np.median(np.concatenate([per[j] for j in RNG.integers(0, len(per), nb)]))
                  for _ in range(20000)])
    pge, ple = float((d >= obs).mean()), float((d <= obs).mean())
    p = min(1.0, 2 * min(pge, ple))
    OUT[f"memb_sub10|{other}"] = dict(p=p, p50=float(np.percentile(d, 50)),
                                      p025=float(np.percentile(d, 2.5)),
                                      p975=float(np.percentile(d, 97.5)), nblk=len(per))
    print(f"      {other:<12} blocks={len(per):>3} sim [{np.percentile(d, 2.5):>7.1f},"
          f"{np.percentile(d, 97.5):>8.1f}] p50={np.percentile(d, 50):>7.1f} | P={p:.4f}  "
          f"{'CONSISTENT' if p > 0.05 else ('EXCLUDED (V72 HIGHER)' if pge < ple else 'EXCLUDED (V72 LOWER)')}")

# ================================================================== B =============================
L.hdr("§B  BIN-BY-BIN -- V72 against each arm inside each speed bin, stratified on (eff, rate)")
print("  Stratify BEFORE pooling. The pooled creep median mixes speeds at which V72's own r26 dose")
print("  differs by 2x, and the arms' speed distributions differ.\n")
BINS = [("0-5", 0.0, 5 / 3.6), ("5-10", 5 / 3.6, SUB10), ("10-15", SUB10, 15 / 3.6),
        ("15-20", 15 / 3.6, CREEP), ("20-30", CREEP, 30 / 3.6), ("30-40", 30 / 3.6, 40 / 3.6),
        ("40-50", 40 / 3.6, 50 / 3.6), ("50+", 50 / 3.6, 1e9)]
EFFRATE = lambda r: (r["cell"][2], r["cell"][3])  # noqa: E731 -- speed is already the outer bin
bb = {}
for other in ("V67+V68", "stock pool", "V71C/r58", "V62+V65"):
    print(f"  --- V72 vs {other}   [ratio > 1 = MORE grind #1 on V72; strata = (eff, |rate|)]")
    print(f"      {'km/h':<7} {'nA':>4} {'nB':>4} {'V72 p50':>9} {'other p50':>10} | "
          f"{'18-22 ratio':>12} {'[95% CI]':>19} {'24-28':>7} {'cells':>6}")
    for nm, lo, hi in BINS:
        A = [r for r in arm("V72/r59", 1, lo, hi)]
        B = [r for r in arm(other, 1, lo, hi)]
        if len(A) < 4 or len(B) < 4:
            print(f"      {nm:<7} {len(A):>4} {len(B):>4}   *** too few")
            bb[f"{other}|{nm}"] = dict(nA=len(A), nB=len(B))
            continue
        rw = {bd: contrast(recell(A, EFFRATE), recell(B, EFFRATE), "e_" + bd)
              for bd in ("18-22", "24-28")}
        bb[f"{other}|{nm}"] = dict(rw, nA=len(A), nB=len(B),
                                   medA=float(np.median(G.col(A, "e_18-22"))),
                                   medB=float(np.median(G.col(B, "e_18-22"))))
        print(f"      {nm:<7} {len(A):>4} {len(B):>4} {np.median(G.col(A, 'e_18-22')):>9.1f} "
              f"{np.median(G.col(B, 'e_18-22')):>10.1f} | {rw['18-22']['ratio']:>12.3f} "
              f"[{rw['18-22']['lo']:>7.3f},{rw['18-22']['hi']:>9.3f}] "
              f"{rw['24-28']['ratio']:>7.3f} {rw['18-22']['ncells']:>6}")
    print()
OUT["binwise"] = bb

# ================================================================== C =============================
L.hdr("§C  ★ THE 35 km/h STEP -- FactorC's first breakpoint, where stock's base damping starts")
print("  `excess` = median e_18-22 / median e_24-28 in the SAME windows, so a broadband rise in")
print("  driver effort cannot make it move. Reported for every arm at the SAME bins, and the")
print("  30-35 -> 35-40 STEP is bootstrapped over blocks.\n")
STEPB = [("25-30", 25 / 3.6, 30 / 3.6), ("30-35", 30 / 3.6, 35 / 3.6),
         ("35-40", 35 / 3.6, 40 / 3.6), ("40-50", 40 / 3.6, 50 / 3.6)]


def boot_excess(rs, nboot=NBOOT):
    """median(e_18-22)/median(e_24-28) with a block bootstrap. Both from the SAME windows."""
    blk = {}
    for r in rs:
        blk.setdefault(r["blk"], []).append(r)
    per = list(blk.values())
    if len(per) < 2:
        return np.nan, np.nan, np.nan
    pt = float(np.median(G.col(rs, "e_18-22")) / np.median(G.col(rs, "e_24-28")))
    d = np.empty(nboot)
    for i in range(nboot):
        s = [r for j in RNG.integers(0, len(per), len(per)) for r in per[j]]
        d[i] = np.median(G.col(s, "e_18-22")) / np.median(G.col(s, "e_24-28"))
    return pt, float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


st = {}
print(f"  {'arm':<12} " + " ".join(f"{n:>22}" for n, _, _ in STEPB) + f" {'30-35/35-40 step':>22}")
for k in ("V72/r59", "V67+V68", "V71C/r58", "stock pool", "V62+V65"):
    cells, keep = [], {}
    for nm, lo, hi in STEPB:
        rs = arm(k, 1, lo, hi)
        if len(rs) < 4:
            cells.append(f"{'n=' + str(len(rs)):>22}")
            keep[nm] = dict(n=len(rs))
            continue
        pt, a, b = boot_excess(rs)
        keep[nm] = dict(n=len(rs), pt=pt, lo=a, hi=b)
        cells.append(f"{pt:>8.2f}[{a:>5.2f},{b:>5.2f}]")
    # the step itself, bootstrapped jointly over the two bins' blocks
    lo_rs, hi_rs = arm(k, 1, 30 / 3.6, 35 / 3.6), arm(k, 1, 35 / 3.6, 40 / 3.6)
    if len(lo_rs) >= 4 and len(hi_rs) >= 4:
        bl, bh = {}, {}
        for r in lo_rs:
            bl.setdefault(r["blk"], []).append(r)
        for r in hi_rs:
            bh.setdefault(r["blk"], []).append(r)
        pl, ph = list(bl.values()), list(bh.values())
        d = np.empty(NBOOT)
        for i in range(NBOOT):
            sa = [r for j in RNG.integers(0, len(pl), len(pl)) for r in pl[j]]
            sb = [r for j in RNG.integers(0, len(ph), len(ph)) for r in ph[j]]
            d[i] = ((np.median(G.col(sa, "e_18-22")) / np.median(G.col(sa, "e_24-28"))) /
                    (np.median(G.col(sb, "e_18-22")) / np.median(G.col(sb, "e_24-28"))))
        pt = ((np.median(G.col(lo_rs, "e_18-22")) / np.median(G.col(lo_rs, "e_24-28"))) /
              (np.median(G.col(hi_rs, "e_18-22")) / np.median(G.col(hi_rs, "e_24-28"))))
        step = f"{pt:>8.2f}[{np.percentile(d, 2.5):>5.2f},{np.percentile(d, 97.5):>5.2f}]"
        keep["step"] = dict(pt=float(pt), lo=float(np.percentile(d, 2.5)),
                            hi=float(np.percentile(d, 97.5)))
    else:
        step = f"{'too few':>22}"
    st[k] = keep
    print(f"  {k:<12} " + " ".join(cells) + f" {step:>22}")
OUT["step35"] = st

# ================================================================== D =============================
L.hdr("§D  THE MANUAL ARM AT MATCHED SPEED -- the raw eng/man ratio is 83% standstill")
r59 = L.driving(store["V72/r59"], "V72/r59")
print(f"  {'km/h':<8} {'eng n':>6} {'eng u':>6} {'man n':>6} {'man u':>6} | {'eng p50':>9} "
      f"{'man p50':>9} {'eng/man':>9} {'[95% CI]':>19} {'24-28 ratio':>12}")
mm = {}
for nm, lo, hi in BINS:
    A = [r for r in r59 if r["eng"] == 1 and lo <= r["v"] < hi]
    B = [r for r in r59 if r["eng"] == 0 and lo <= r["v"] < hi]
    if len(A) < 4 or len(B) < 4:
        print(f"  {nm:<8} {len(A):>6} {'':>6} {len(B):>6}   *** one arm too few")
        mm[nm] = dict(nA=len(A), nB=len(B))
        continue
    rw = {bd: contrast(recell(A, EFFRATE), recell(B, EFFRATE), "e_" + bd)
          for bd in ("18-22", "24-28")}
    mm[nm] = dict(rw, nA=len(A), nB=len(B), medA=float(np.median(G.col(A, "e_18-22"))),
                  medB=float(np.median(G.col(B, "e_18-22"))))
    print(f"  {nm:<8} {len(A):>6} {len({r['blk'] for r in A}):>6} {len(B):>6} "
          f"{len({r['blk'] for r in B}):>6} | {np.median(G.col(A, 'e_18-22')):>9.1f} "
          f"{np.median(G.col(B, 'e_18-22')):>9.1f} {rw['18-22']['ratio']:>9.3f} "
          f"[{rw['18-22']['lo']:>7.3f},{rw['18-22']['hi']:>9.3f}] {rw['24-28']['ratio']:>12.3f}")
OUT["eng_man_binwise"] = mm

print("\n  ★ UNSTRATIFIED medians in the one bin with real manual exposure at speed (5-10 km/h):")
for e, nm in ((1, "engaged"), (0, "manual")):
    sel = [r for r in r59 if r["eng"] == e and 5 / 3.6 <= r["v"] < SUB10]
    if len(sel) < 2:
        continue
    m, a, b = G.boot_median_ci(sel, "e_18-22", RNG, nboot=NBOOT)
    print(f"      {nm:<8} n={len(sel):>3} u={len({r['blk'] for r in sel}):>2} "
          f"v p50={np.median(G.col(sel, 'v')):>5.2f} eff p50={np.median(G.col(sel, 'eff')):>6.0f} "
          f"| e18-22 {m:>7.1f} [{a:>6.1f},{b:>7.1f}]  e24-28 "
          f"{np.median(G.col(sel, 'e_24-28')):>6.1f}")

# ================================================================== E =============================
L.hdr("§E  EMPTY IS NOT NULL -- P(observe 0 windows) for every empty cell that matters")
print("  Route 59's manual arm has ZERO windows above 40 km/h and zero in 10-25 km/h. Those are")
print("  EXPOSURE facts about the drive, not measurements. Stated as a probability under the")
print("  alternative 'the manual arm is sampled at the same speed distribution as the engaged one'.\n")
eng_all = [r for r in r59 if r["eng"] == 1]
man_all = [r for r in r59 if r["eng"] == 0]
emp = {}
for nm, lo, hi in BINS + [("40+", 40 / 3.6, 1e9)]:
    ne = sum(1 for r in eng_all if lo <= r["v"] < hi)
    nm_ = sum(1 for r in man_all if lo <= r["v"] < hi)
    p_bin = ne / max(len(eng_all), 1)
    p0 = (1 - p_bin) ** len(man_all)
    emp[nm] = dict(eng=ne, man=nm_, p_bin=float(p_bin), p_zero=float(p0))
    flag = ""
    if nm_ == 0:
        flag = ("  <- P(0) = %.2g under the matched-distribution alternative => %s"
                % (p0, "the emptiness IS informative" if p0 < 0.05 else "UNINFORMATIVE, not a null"))
    print(f"  {nm:<8} engaged n={ne:>4} ({100 * p_bin:>5.1f}% of engaged)   manual n={nm_:>4}{flag}")
OUT["empty"] = emp

# ================================================================== F =============================
L.hdr("§F  LEVER B -- the 1-4 Hz driver/control band, where a base-damping change should show")
print("  🛑 V72 changes THREE things at once (rate lane, FactorC/E damping, 0xC63A0). Nothing here")
print("  can attribute a 1-4 Hz move to Lever B specifically. This is a description, not a test.\n")
print(f"  {'arm':<12} {'speed':<10} {'n':>5} {'e_1-4 p50':>10} {'[95% CI]':>19} | "
       f"{'vs V72 (strat 2d v,eff)':>24}")
lb = {}
for nm, lo, hi in (("creep<20", 0.0, CREEP), ("20-40", CREEP, 40 / 3.6), ("40+", 40 / 3.6, 1e9)):
    A = arm("V72/r59", 1, lo, hi)
    for k in ("V72/r59", "V67+V68", "V71C/r58", "stock pool", "V62+V65"):
        rs = arm(k, 1, lo, hi)
        if len(rs) < 4:
            print(f"  {k:<12} {nm:<10} {len(rs):>5}  *** too few")
            continue
        m, a, b = G.boot_median_ci(rs, "e_1-4", RNG, nboot=NBOOT)
        tail = ""
        if k != "V72/r59" and len(A) >= 4:
            rw = contrast(recell(A, CELLFN["2d (v,eff)"]), recell(rs, CELLFN["2d (v,eff)"]), "e_1-4")
            tail = f"{rw['ratio']:>7.3f} [{rw['lo']:>6.3f},{rw['hi']:>7.3f}]"
            lb[f"{nm}|{k}"] = rw
        print(f"  {k:<12} {nm:<10} {len(rs):>5} {m:>10.1f} [{a:>7.1f},{b:>9.1f}] | {tail:>24}")
    print()
OUT["lever_b"] = lb

# ================================================================== G =============================
L.hdr("§G  SENSITIVITY -- the headline under both resampling units")
sens = {}
for epkey in ("blk", "ep"):
    G.EPKEY = epkey
    A = [r for r in L.driving(store["V72/r59"], "V72/r59") if r["eng"] == 1 and r["v"] < CREEP]
    m, a, b = G.boot_median_ci(A, "e_18-22", RNG, nboot=NBOOT)
    row = dict(med=float(m), lo=float(a), hi=float(b), units=len({r[epkey] for r in A}))
    for other in ("stock pool", "V67+V68"):
        B = arm(other, 1, 0.0, CREEP)
        row[other] = contrast(A, B, "e_18-22")
    sens[epkey] = row
    print(f"  EPKEY={epkey:<4} units={row['units']:>3}  median {m:>7.1f} [{a:>7.1f},{b:>8.1f}]  "
          f"| vs stock {row['stock pool']['ratio']:>6.3f} "
          f"[{row['stock pool']['lo']:>5.3f},{row['stock pool']['hi']:>6.3f}] "
          f"({row['stock pool']['ncells']} cells)  | vs V67+V68 {row['V67+V68']['ratio']:>6.3f} "
          f"({row['V67+V68']['ncells']} cells)")
G.EPKEY = "blk"
OUT["sensitivity"] = sens

(HERE.parent / "_scratch/out/_r59_followups.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE.parent / '_scratch/out/_r59_followups.json'}")
