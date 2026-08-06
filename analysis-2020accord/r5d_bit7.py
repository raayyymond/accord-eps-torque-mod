#!/usr/bin/env python3
"""Route `5d` -- the `bit7` (damper-output) within-route contrast, de-confounded properly.

`r5d_duty.py`'s first pass matched on a (rate x speed) grid and only ONE cell survived with >= 6
windows per side (n = 7 vs 70). That is not a de-confounding, it is a coincidence. This file does
the job three ways and reports how much overlap each one actually buys:

  A  OVERLAP CENSUS. Cross-tab of `damp` duty against (rate_lp, v). If bit7 is a deterministic
     function of the covariates there is NO contrast to be had, and that must be shown, not assumed.
  B  BAND-RELATIVE OUTCOME. `e_6-9 / e_24-28` and `e_18-22 / e_24-28` instead of the raw envelope.
     A window that is simply noisier moves all three bands together; the ratio does not. This is the
     kit's own excess-over-control statistic.
  C  PROPENSITY-STYLE STRATIFICATION on a single covariate at a time, with the strata chosen from
     the data (quintiles of `rate_lp` inside a fixed speed band), so strata are guaranteed occupied.

🛑 What NONE of these can do: `bit7` is `(gp-0x6bd0 != 0)`, a DUTY, so the contrast is
damper-ACTIVE vs damper-IDLE. It cannot measure a dose-response slope, and a null here does not
bound the effect of a LARGER dose.

Usage:  python r5d_bit7.py   ->  writes _r5d_bit7.json
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _nearcentre_lib as N  # noqa: E402

G.EPKEY = "blk"
RNG = np.random.default_rng(6162)
OUT = {}

with open(ROOT / "_cache_r5d_nearcentre.pkl", "rb") as fh:
    store = pickle.load(fh)
eng = [r for r in store["V74/r5d"]
       if r["eng"] == 1 and np.isfinite(r.get("damp", np.nan)) and np.isfinite(r["e_24-28"])
       and r["e_24-28"] > 0 and np.isfinite(r.get("rate_lp", np.nan))]
for r in eng:
    r["x_6-9"] = r["e_6-9"] / r["e_24-28"]
    r["x_18-22"] = r["e_18-22"] / r["e_24-28"]
print(f"engaged windows with probe + control band: {len(eng)}  "
      f"({len({r['blk'] for r in eng})} blocks)")

# ================================================================== A. OVERLAP ====================
N.hdr("A. OVERLAP CENSUS -- is there ANY contrast left once rate and speed are held?")
RB = [(0.0, 2.0), (2.0, 5.0), (5.0, 12.0), (12.0, 30.0), (30.0, 1e9)]
RN = ["0-2", "2-5", "5-12", "12-30", "30+"]
VB = [(0.0, 4.0), (4.0, 9.4), (9.4, 15.0), (15.0, 20.0), (20.0, 40.0)]
VN = ["0-4", "4-9.4", "9.4-15", "15-20", "20+"]
print(f"  each cell: n / fraction with damp >= 0.5.  🛑 a cell at 0.00 or 1.00 carries NO contrast\n")
print(f"  {'rate_lp':>9} " + " ".join(f"{v:>12}" for v in VN))
grid = {}
for (rlo, rhi), rn in zip(RB, RN):
    row = []
    for (vlo, vhi), vn in zip(VB, VN):
        s = [r for r in eng if rlo <= r["rate_lp"] < rhi and vlo <= r["v"] < vhi]
        f = float(np.mean([r["damp"] >= 0.5 for r in s])) if s else np.nan
        grid[f"{rn}|{vn}"] = dict(n=len(s), frac=f)
        row.append(f"{len(s):>5}/{f:>5.2f}" if s else f"{'--':>11}")
    print(f"  {rn:>9} " + " ".join(f"{c:>12}" for c in row))
OUT["overlap"] = grid
usable = [(k, v) for k, v in grid.items() if v["n"] >= 12 and 0.15 <= v["frac"] <= 0.85]
print(f"\n  cells with n >= 12 AND damp fraction in [0.15, 0.85] (i.e. real overlap): "
      f"{len(usable)}")
for k, v in usable:
    print(f"      {k:<18} n={v['n']:>3}  damp>=0.5 fraction {v['frac']:.2f}")

# ================================================================== B/C. CONTRASTS ================
KEYS = [("e_6-9", "6-9 Hz raw"), ("e_18-22", "18-22 Hz raw"), ("e_24-28", "24-28 Hz CONTROL"),
        ("x_6-9", "6-9 / control"), ("x_18-22", "18-22 / control")]


def strat_ratio(rs, key, cellfn, nboot=3000, minn=6):
    """Weighted log-ratio of damp-active vs damp-idle over occupied cells, block-resampled."""
    def est(pool):
        by = {}
        for r in pool:
            by.setdefault(cellfn(r), []).append(r)
        num = den = 0.0
        nc = 0
        for c, rr in by.items():
            h = [r for r in rr if r["damp"] >= 0.5]
            l = [r for r in rr if r["damp"] < 0.5]
            if len(h) < minn or len(l) < minn:
                continue
            mh = float(np.median(G.col(h, key)))
            ml = float(np.median(G.col(l, key)))
            if mh <= 0 or ml <= 0:
                continue
            w = 1.0 / (1.0 / len(h) + 1.0 / len(l))
            num += w * np.log(mh / ml)
            den += w
            nc += 1
        return (float(np.exp(num / den)) if den else np.nan), nc
    pt, nc = est(rs)
    blocks = {}
    for r in rs:
        blocks.setdefault(r["blk"], []).append(r)
    ks = list(blocks)
    dr = np.full(nboot, np.nan)
    for i in range(nboot):
        samp = [r for j in RNG.integers(0, len(ks), len(ks)) for r in blocks[ks[j]]]
        dr[i] = est(samp)[0]
    return pt, float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5)), nc


N.hdr("B. RATE-STRATIFIED CONTRAST -- quintiles of rate_lp, pooled over speed")
q = np.percentile([r["rate_lp"] for r in eng], [20, 40, 60, 80])
print(f"  rate_lp quintile edges: {np.round(q, 2)} deg/s\n")


def rq(r):
    return int(np.searchsorted(q, r["rate_lp"]))


print(f"  {'metric':<18} {'ratio':>7} {'95% CI':>18} {'cells':>6}   reading")
for k, kl in KEYS:
    pt, lo, hi, nc = strat_ratio(eng, k, rq)
    rd = ("no contrast" if not np.isfinite(pt) else
          ("damper-active HIGHER" if lo > 1 else
           ("damper-active LOWER" if hi < 1 else "inside 1 -- no effect resolved")))
    print(f"  {kl:<18} {pt:>7.3f} [{lo:>7.3f}, {hi:>7.3f}] {nc:>6}   {rd}")
    OUT.setdefault("rate_quintile", {})[k] = dict(ratio=pt, lo=lo, hi=hi, cells=nc)

N.hdr("C. RATE x SPEED STRATIFIED -- the same estimator on the two-way grid")


def rvq(r):
    return (rq(r), G.binof(r["v"], VB))


print(f"  {'metric':<18} {'ratio':>7} {'95% CI':>18} {'cells':>6}")
for k, kl in KEYS:
    pt, lo, hi, nc = strat_ratio(eng, k, rvq, minn=5)
    print(f"  {kl:<18} {pt:>7.3f} [{lo:>7.3f}, {hi:>7.3f}] {nc:>6}")
    OUT.setdefault("rate_speed", {})[k] = dict(ratio=pt, lo=lo, hi=hi, cells=nc)

N.hdr("D. THE SANITY CHECK THAT DECIDES WHETHER ANY OF THIS IS READABLE")
print("  If the CONTROL band (24-28 Hz) moves with bit7 by as much as the symptom bands do, then")
print("  bit7 is selecting NOISIER WINDOWS, not damped ones, and the raw contrasts are worthless.")
print("  The band-relative rows are the ones that survive that, by construction.\n")
for lab, kk in (("rate quintile", "rate_quintile"), ("rate x speed", "rate_speed")):
    d = OUT[kk]
    print(f"  {lab:<14} control {d['e_24-28']['ratio']:.3f}   "
          f"6-9 raw {d['e_6-9']['ratio']:.3f}   18-22 raw {d['e_18-22']['ratio']:.3f}   "
          f"|  6-9 rel {d['x_6-9']['ratio']:.3f} [{d['x_6-9']['lo']:.3f},{d['x_6-9']['hi']:.3f}]"
          f"   18-22 rel {d['x_18-22']['ratio']:.3f} "
          f"[{d['x_18-22']['lo']:.3f},{d['x_18-22']['hi']:.3f}]")

with open(ROOT / "_r5d_bit7.json", "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print("\nwrote _r5d_bit7.json")
