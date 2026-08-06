#!/usr/bin/env python3
"""INDEPENDENT REPLICATION on route 5a: is grind #1 an ANGLE effect or a STEERING-ACTIVITY effect?

A peer established on another route that the operator's "near zero angle" does NOT survive
rate-matching -- 18-22 Hz energy flat from 0-25 deg once steering rate is controlled, with the real
covariate being steering ACTIVITY (at |ang| < 3 deg, energy 205 -> 1385 as rate goes <8 -> 8-20
deg/s). This file tests that claim on `_cache_r5a` WITHOUT assuming it, because a contradiction would
matter as much as a replication.

Three things, in order:
  1. THE 2-D TABLE with a per-cell EXPOSURE CENSUS. 🛑 "EMPTY" IS NOT "NULL".
  2. ANGLE effect WITHIN rate strata, and RATE effect WITHIN angle strata -- the actual
     deconfounding, each with an episode-resampled CI and a split-half null.
  3. Which covariate survives the other: a stratified contrast both ways round.

🛑 `rate` here is `_grind2_lib`'s own per-window mean |rate_c| (CAN 0x14A bytes 2:3, deg/s) -- the
same covariate the corpus cells are built on, so this is comparable to every prior route.
🛑 Windows are cut inside engagement runs and binned by their OWN mean covariates afterwards, never
masked before cutting (the creep-script convention that manufactured nulls once).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parent

import _grind2_lib as G  # noqa: E402
import _r5a_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RNG = np.random.default_rng(31337)
out = {}
R = L.records()
v73 = [r for r in R["V73/r5a"] if r["seg"] != 17 and r["eng"] == 1]
print(f"V73 engaged windows (parked segment dropped): {len(v73)}")

AB = [(0, 3), (3, 8), (8, 15), (15, 25), (25, 1e9)]
ALB = ["0-3", "3-8", "8-15", "15-25", ">25"]
RB = [(0, 8), (8, 20), (20, 40), (40, 1e9)]
RLB = ["<8", "8-20", "20-40", ">40"]
CREEP = (0.5, 4.0)


def cell(rs, alo, ahi, rlo, rhi, creep=True):
    o = [r for r in rs if alo <= r["ang"] < ahi and rlo <= r["rate"] < rhi]
    if creep:
        o = [r for r in o if CREEP[0] <= r["v"] < CREEP[1]]
    return o


for creep, tag in ((True, "ENGAGED CREEP 0.5-4 m/s"), (False, "ENGAGED, ALL SPEEDS")):
    L.hdr(f"1. e_18-22 BY |ANGLE| x |RATE|, {tag}  -- median (n windows / episodes)")
    print(f"{'|ang| deg':>10s} " + "".join(f"{'rate ' + x:>22s}" for x in RLB))
    tabl = {}
    for (alo, ahi), al in zip(AB, ALB):
        row = f"{al:>10s} "
        for (rlo, rhi), rl in zip(RB, RLB):
            rs = cell(v73, alo, ahi, rlo, rhi, creep)
            ne = len({r["ep"] for r in rs})
            if len(rs) < 5:
                row += f"{'-- n=' + str(len(rs)) + ' UNPWR':>22s}"
                tabl[(al, rl)] = (len(rs), ne, None)
                continue
            m = float(np.median([r["e_18-22"] for r in rs]))
            row += f"{f'{m:8.0f} ({len(rs)}w/{ne}e)':>22s}"
            tabl[(al, rl)] = (len(rs), ne, m)
        print(row)
    out["table_creep" if creep else "table_all"] = {f"{a}|{b}": list(v) for (a, b), v in tabl.items()}
    # exposure census in seconds
    print(f"\n{'EXPOSURE s':>10s} " + "".join(f"{'rate ' + x:>22s}" for x in RLB))
    for (alo, ahi), al in zip(AB, ALB):
        row = f"{al:>10s} "
        for (rlo, rhi), rl in zip(RB, RLB):
            n = len(cell(v73, alo, ahi, rlo, rhi, creep))
            row += f"{n * 1.28:22.1f}"
        print(row)

# ------------------------------------------------------------------ 2. deconfounding -------------
L.hdr("2. THE DECONFOUNDING -- each covariate's effect WITHIN strata of the other")


def contrast(A, B, key="e_18-22", nboot=1500, **kw):
    pt, lo, hi, nc, na, nb, tab, _ = G.boot_cellwise(A, B, key, RNG, nboot=nboot, **kw)
    return pt, lo, hi, nc, na, nb


print("2a. ANGLE effect (|ang|<3 vs |ang| 8-25) held WITHIN each rate stratum, engaged all speeds")
print(f"    {'rate stratum':>14s} {'n lo-ang':>9s} {'n hi-ang':>9s} {'ratio':>7s} "
      f"{'95% CI':>18s} {'null':>18s}  verdict")
for (rlo, rhi), rl in zip(RB, RLB):
    A = [r for r in v73 if r["ang"] < 3 and rlo <= r["rate"] < rhi]
    B = [r for r in v73 if 8 <= r["ang"] < 25 and rlo <= r["rate"] < rhi]
    if len(A) < 8 or len(B) < 8:
        print(f"    {rl:>14s} {len(A):9d} {len(B):9d}   UNPOWERED -- exposure, not a null")
        continue
    pt, lo, hi, nc, na, nb = contrast(A, B, min_ep=1, min_win=2)
    _, nl, nh = G.split_half_null(B, "e_18-22", RNG, nrep=200, min_ep=1, min_win=2)
    if not np.isfinite(pt):
        print(f"    {rl:>14s} {len(A):9d} {len(B):9d}   no shared cell -- UNPOWERED")
        continue
    v = "ANGLE MATTERS" if (lo > nh or hi < nl) else "flat (inside null)"
    print(f"    {rl:>14s} {len(A):9d} {len(B):9d} {pt:7.3f} [{lo:7.3f},{hi:7.3f}] "
          f"[{nl:7.3f},{nh:7.3f}]  {v}")
    out.setdefault("angle_within_rate", {})[rl] = [pt, lo, hi, nl, nh, len(A), len(B)]

print("\n2b. RATE effect (rate 8-20 vs rate <8) held WITHIN each angle stratum, engaged all speeds")
print(f"    {'angle stratum':>14s} {'n hi-rate':>10s} {'n lo-rate':>10s} {'ratio':>7s} "
      f"{'95% CI':>18s} {'null':>18s}  verdict")
for (alo, ahi), al in zip(AB, ALB):
    A = [r for r in v73 if alo <= r["ang"] < ahi and 8 <= r["rate"] < 20]
    B = [r for r in v73 if alo <= r["ang"] < ahi and r["rate"] < 8]
    if len(A) < 8 or len(B) < 8:
        print(f"    {al:>14s} {len(A):10d} {len(B):10d}   UNPOWERED -- exposure, not a null")
        continue
    pt, lo, hi, nc, na, nb = contrast(A, B, min_ep=1, min_win=2)
    _, nl, nh = G.split_half_null(B, "e_18-22", RNG, nrep=200, min_ep=1, min_win=2)
    if not np.isfinite(pt):
        print(f"    {al:>14s} {len(A):10d} {len(B):10d}   no shared cell -- UNPOWERED")
        continue
    v = "RATE MATTERS" if (lo > nh or hi < nl) else "flat (inside null)"
    print(f"    {al:>14s} {len(A):10d} {len(B):10d} {pt:7.3f} [{lo:7.3f},{hi:7.3f}] "
          f"[{nl:7.3f},{nh:7.3f}]  {v}")
    out.setdefault("rate_within_angle", {})[al] = [pt, lo, hi, nl, nh, len(A), len(B)]

# ------------------------------------------------------------------ 3. the peer's exact claim ----
L.hdr("3. THE PEER'S EXACT NUMBERS, re-measured here: at |ang| < 3 deg, e_18-22 vs rate")
print(f"    {'rate deg/s':>12s} {'n win':>6s} {'ep':>4s} {'expo s':>8s} {'median':>9s} "
      f"{'[95% CI]':>20s}")
for (rlo, rhi), rl in zip(RB, RLB):
    rs = [r for r in v73 if r["ang"] < 3 and rlo <= r["rate"] < rhi]
    ne = len({r["ep"] for r in rs})
    if len(rs) < 5:
        print(f"    {rl:>12s} {len(rs):6d} {ne:4d} {len(rs) * 1.28:8.1f}   UNPOWERED")
        continue
    p, lo, hi = G.boot_median_ci(rs, "e_18-22", RNG, nboot=1500)
    print(f"    {rl:>12s} {len(rs):6d} {ne:4d} {len(rs) * 1.28:8.1f} {p:9.1f} [{lo:8.1f},{hi:8.1f}]")
    out.setdefault("peer_check", {})[rl] = [len(rs), ne, p, lo, hi]
print("\n    peer reported 205 -> 1385 going <8 -> 8-20 deg/s at |ang| < 3 deg.")

L.hdr("4. AND THE CONVERSE: at LOW rate (<8 deg/s), is there any angle dependence left?")
print(f"    {'|ang| deg':>12s} {'n win':>6s} {'ep':>4s} {'expo s':>8s} {'median':>9s} "
      f"{'[95% CI]':>20s}")
for (alo, ahi), al in zip(AB, ALB):
    rs = [r for r in v73 if alo <= r["ang"] < ahi and r["rate"] < 8]
    ne = len({r["ep"] for r in rs})
    if len(rs) < 5:
        print(f"    {al:>12s} {len(rs):6d} {ne:4d} {len(rs) * 1.28:8.1f}   UNPOWERED")
        continue
    p, lo, hi = G.boot_median_ci(rs, "e_18-22", RNG, nboot=1500)
    print(f"    {al:>12s} {len(rs):6d} {ne:4d} {len(rs) * 1.28:8.1f} {p:9.1f} [{lo:8.1f},{hi:8.1f}]")
    out.setdefault("angle_at_low_rate", {})[al] = [len(rs), ne, p, lo, hi]

with open(ROOT / "_r5a_rate_vs_angle.json", "w") as fh:
    json.dump(out, fh, indent=1, default=float)
print("\nwrote _r5a_rate_vs_angle.json")
