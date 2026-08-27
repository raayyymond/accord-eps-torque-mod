#!/usr/bin/env python3
"""V76 (route 65) symptom sizing -- T1 (grind#1), T2 (ratchet), T3 (matched-speed census),
T4 (grind#2 vs its design prediction), T5 (dose-response, extending `studies/sessions/v78/v78_symptom_dose.py`'s ladder).

Reuses the ESTABLISHED harness end to end -- `_grind2_lib.wrecs` / `boot_cellwise` /
`split_half_null` / `episodes` -- rather than inventing a parallel estimator. V74/r5d and V75/r5e
come out of `v78_symptom_lib.records()` UNCHANGED (read-only, exactly as `studies/sessions/v78/v78_symptom_dose.py`
consumes them); V76/r65 comes out of `v77sizing_lib.records()`, this session's own extract.

Usage:  python v77sizing_symptom_dose.py   ->  writes _scratch/out/_v77sizing_symptoms.json
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
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import v77sizing_lib as V76  # noqa: E402
import v78_symptom_lib as V  # noqa: E402

RNG = np.random.default_rng(770076)
OUT = {}

V.install_fs()
BASE = V.records()                          # V59..V75, READ-ONLY (owned by sibling sessions)
MINE = V76.records()                        # V76/r65 alone, this session's own pickle
R = dict(BASE)
R.update(MINE)

BUILDS3 = ["V74/r5d", "V75/r5e", "V76/r65"]
PARK = {"V74/r5d": [2, 3, 9], "V75/r5e": [0], "V76/r65": [0, 10]}
VLO, VHI_CREEP = 0.5, 4.17                  # >=0.5 (drop near-stationary) .. 15 km/h, the brief's cut
V_BINS_CENSUS = [(0.0, 0.5), (0.5, 2.0), (2.0, 4.17), (4.17, 8.0), (8.0, 14.0), (14.0, 30.0)]


def creep(b, eng=1):
    return [r for r in R[b] if r["seg"] not in PARK.get(b, []) and r["eng"] == eng
            and VLO <= r["v"] < VHI_CREEP]


def allv(b, eng=1):
    return [r for r in R[b] if r["seg"] not in PARK.get(b, []) and r["eng"] == eng]


def episodes_ratio(recsA, recsB, key, rng, nboot=3000, agg=np.median):
    """Unpaired median-ratio A/B, episode-resampled independently on each side (different routes)."""
    epA, epB = G.episodes(recsA), G.episodes(recsB)

    def pt(A, B):
        va = np.concatenate([G.col(e, key) for e in A]) if A else np.array([])
        vb = np.concatenate([G.col(e, key) for e in B]) if B else np.array([])
        va, vb = va[np.isfinite(va)], vb[np.isfinite(vb)]
        if not len(va) or not len(vb):
            return np.nan
        ma, mb = agg(va), agg(vb)
        return ma / mb if mb > 0 else np.nan

    obs = pt(epA, epB)
    if not (len(epA) and len(epB)) or not np.isfinite(obs):
        return dict(ratio=obs, lo=np.nan, hi=np.nan, nepA=len(epA), nepB=len(epB))
    draws = np.full(nboot, np.nan)
    for i in range(nboot):
        ia = rng.integers(0, len(epA), len(epA))
        ib = rng.integers(0, len(epB), len(epB))
        draws[i] = pt([epA[j] for j in ia], [epB[j] for j in ib])
    draws = draws[np.isfinite(draws)]
    lo, hi = (float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))) if len(draws) \
        else (np.nan, np.nan)
    return dict(ratio=float(obs), lo=lo, hi=hi, nepA=len(epA), nepB=len(epB), ndraws=len(draws))


def _strat_v(eA, eB, key, min_ep, min_win, agg, want_table=False):
    """Shared core: stratify by SPEED BIN ONLY (`_grind2_lib.V_BINS`), log-ratio A/B."""
    A, B = {}, {}
    for e in eA:
        for r in e:
            A.setdefault(G.binof(r["v"], G.V_BINS), []).append(r)
    for e in eB:
        for r in e:
            B.setdefault(G.binof(r["v"], G.V_BINS), []).append(r)
    num = den = 0.0
    tab = []
    for c in sorted(set(A) & set(B)):
        ra, rb = A[c], B[c]
        nea, neb = len({r["ep"] for r in ra}), len({r["ep"] for r in rb})
        if nea < min_ep or neb < min_ep or len(ra) < min_win or len(rb) < min_win:
            continue
        sa, sb = G.cell_stat(ra, key, agg), G.cell_stat(rb, key, agg)
        if not (np.isfinite(sa) and np.isfinite(sb)) or sa <= 0 or sb <= 0:
            continue
        w = 1.0 / (1.0 / nea + 1.0 / neb)
        num += w * np.log(sa / sb)
        den += w
        if want_table:
            tab.append((c, len(ra), len(rb), nea, neb, sa, sb, sa / sb, w))
    return (num / den if den else np.nan), tab


def self_null_speed(recs, key, rng, nrep=400, min_ep=1, min_win=4, agg=np.median):
    """The build's own noise floor, speed-stratified the SAME way `speed_stratified_ratio` is --
    randomly halve its own episodes and run the identical estimator on both halves.
    """
    eps = G.episodes(recs)
    out = []
    for _ in range(nrep):
        idx = rng.permutation(len(eps))
        h = len(eps) // 2
        a, b = [eps[i] for i in idx[:h]], [eps[i] for i in idx[h:]]
        v, _ = _strat_v(a, b, key, min_ep, min_win, agg)
        if np.isfinite(v):
            out.append(float(np.exp(v)))
    out = np.array(out, float)
    if not len(out):
        return np.nan, np.nan, np.nan
    return (float(np.exp(np.nanmedian(np.log(out)))),
            float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5)))


def speed_stratified_ratio(recsA, recsB, key, rng, nboot=3000, min_ep=2, min_win=5, agg=np.median):
    """Like `_grind2_lib.boot_cellwise`, but stratifying on SPEED BIN ONLY (`_grind2_lib.V_BINS`),
    not the full 4-way (eng, v, effort, rate) cell.

    The full cell is too fine for a single ~11-15-episode route: with exposure this limited almost
    every 4-way cell holds one episode, so `boot_cellwise`'s own `min_ep=3` default clears NOTHING
    (see the run this replaced -- cells=0 on every T1/T2 line). Speed is the ONE axis this session's
    brief makes MANDATORY (`accord-averaged-spectrum-needs-matched-speed-distributions`); dropping
    the other two axes trades some residual effort/rate confounding for the power to say anything at
    all, and that trade is disclosed via `ncells`/`table` in the return, not hidden.
    """
    epA, epB = G.episodes(recsA), G.episodes(recsB)
    point, tab = _strat_v(epA, epB, key, min_ep, min_win, agg, want_table=True)
    if not np.isfinite(point):
        return dict(ratio=np.nan, lo=np.nan, hi=np.nan, ncells=len(tab), nepA=len(epA),
                    nepB=len(epB), table=tab)
    draws = np.full(nboot, np.nan)
    for i in range(nboot):
        ia = rng.integers(0, len(epA), len(epA))
        ib = rng.integers(0, len(epB), len(epB))
        draws[i] = _strat_v([epA[j] for j in ia], [epB[j] for j in ib], key, min_ep, min_win, agg)[0]
    draws = draws[np.isfinite(draws)]
    lo, hi = ((float(np.exp(np.percentile(draws, 2.5))), float(np.exp(np.percentile(draws, 97.5))))
              if len(draws) else (np.nan, np.nan))
    return dict(ratio=float(np.exp(point)), lo=lo, hi=hi, ncells=len(tab), nepA=len(epA),
               nepB=len(epB), table=tab)


# =====================================================================================================
V.hdr("T3 (done FIRST, on purpose) -- PER-BUILD SPEED CENSUS, engaged windows, all speeds")
# necessary but NOT sufficient per memory -- printed before any band-power number is quoted, so the
# ratios below can be read against it rather than the other way round.
census = {}
print(f"  {'build':<10}" + "".join(f"{lo:>5.1f}-{hi:<5.1f}" for lo, hi in V_BINS_CENSUS)
      + f"{'total s':>10}{'nep':>6}")
for b in BUILDS3:
    rs = allv(b)
    eps = G.episodes(rs)
    row = []
    for lo, hi in V_BINS_CENSUS:
        n = sum(1 for r in rs if lo <= r["v"] < hi)
        row.append(n)
    total_s = len(rs) * 1.28   # NFFT=256 @ ~100Hz window length in seconds (informal, HOP overlap
                                # means this over-counts unique seconds; kept as a relative gauge only)
    print(f"  {b:<10}" + "".join(f"{n:>11d}" for n in row) + f"{total_s:>10.0f}{len(eps):>6d}")
    census[b] = dict(v_bins=row, nep=len(eps))
OUT["census"] = census
print("\n  ⇒ if the three builds' speed distributions above are NOT comparable, a raw (unstratified)")
print("    band-power ratio between them is confounded by wheel-order content -- see the WARNING")
print("    below the T1/T2 tables for which builds this affects.")

# occupancy overlap check, the actual mandatory test (memory: averaged-spectrum-needs-matched-speed)
V.hdr("T3b -- CELL OCCUPANCY OVERLAP (the test `boot_cellwise` enforces structurally)")
for a, b in (("V76/r65", "V74/r5d"), ("V76/r65", "V75/r5e")):
    ca = {r["cell"] for r in creep(a)}
    cb = {r["cell"] for r in creep(b)}
    print(f"  {a} vs {b}  (creep, engaged): {a} has {len(ca)} cells, {b} has {len(cb)} cells, "
          f"{len(ca & cb)} SHARED -- boot_cellwise uses ONLY the shared cells, so a build's own "
          f"narrow-speed contamination cannot leak into the ratio unmatched.")
    OUT.setdefault("cell_overlap", {})[f"{a}|{b}"] = dict(nA=len(ca), nB=len(cb), shared=len(ca & cb))

# =====================================================================================================
V.hdr("T1 -- GRIND #1 (18-22 Hz), engaged creep (0.5-15 km/h). Split-half null FIRST, then ratios.")
nulls1 = {}
for b in BUILDS3:
    rs = creep(b)
    n = self_null_speed(rs, "e_18-22", RNG)
    nulls1[b] = n
    print(f"  {b:<10}  split-half null (own noise floor)  {n[0]:6.3f} [{n[1]:6.3f}, {n[2]:6.3f}]"
          f"   (n_windows={len(rs)}, n_ep={len(G.episodes(rs))})")
print()
r1 = {}
for a, b in (("V76/r65", "V74/r5d"), ("V76/r65", "V75/r5e"), ("V75/r5e", "V74/r5d")):
    o = speed_stratified_ratio(creep(a), creep(b), "e_18-22", RNG)
    inside_null = np.isfinite(o["lo"]) and (o["lo"] <= 1.0 <= o["hi"])
    print(f"  {a:<10}/{b:<10}  18-22 Hz  {o['ratio']:6.3f} [{o['lo']:6.3f}, {o['hi']:6.3f}]  "
          f"v-cells={o['ncells']} nepA={o['nepA']} nepB={o['nepB']}"
          + ("  <= inside its own null" if inside_null else ""))
    r1[f"{a}|{b}"] = o
OUT["t1_grind1"] = dict(null=nulls1, ratio=r1)

print("\n  NEGATIVE CONTROL, 24-28 Hz (pre-declared, between the modes -- should read ~1.0):")
for a, b in (("V76/r65", "V74/r5d"), ("V76/r65", "V75/r5e")):
    o = speed_stratified_ratio(creep(a), creep(b), "e_24-28", RNG)
    print(f"  {a:<10}/{b:<10}  24-28 Hz  {o['ratio']:6.3f} [{o['lo']:6.3f}, {o['hi']:6.3f}]  "
          f"v-cells={o['ncells']}")
    OUT.setdefault("t1_negctrl", {})[f"{a}|{b}"] = o

# =====================================================================================================
V.hdr("T2 -- MICRO-RATCHET (6-9 Hz), engaged creep. Split-half null FIRST, then ratios.")
nulls2 = {}
for b in BUILDS3:
    rs = creep(b)
    n = self_null_speed(rs, "e_6-9", RNG)
    nulls2[b] = n
    print(f"  {b:<10}  split-half null (own noise floor)  {n[0]:6.3f} [{n[1]:6.3f}, {n[2]:6.3f}]")
print()
r2 = {}
for a, b in (("V76/r65", "V74/r5d"), ("V76/r65", "V75/r5e"), ("V75/r5e", "V74/r5d")):
    o = speed_stratified_ratio(creep(a), creep(b), "e_6-9", RNG)
    inside_null = np.isfinite(o["lo"]) and (o["lo"] <= 1.0 <= o["hi"])
    print(f"  {a:<10}/{b:<10}  6-9 Hz   {o['ratio']:6.3f} [{o['lo']:6.3f}, {o['hi']:6.3f}]  "
          f"v-cells={o['ncells']} nepA={o['nepA']} nepB={o['nepB']}"
          + ("  <= inside its own null" if inside_null else ""))
    r2[f"{a}|{b}"] = o
OUT["t2_ratchet"] = dict(null=nulls2, ratio=r2)

# also: does V76 SHOW the ratchet/grind1 at all, vs its own negative control (presence, not just ratio)
V.hdr("T1b/T2b -- DOES V76 SHOW EITHER LINE AT ALL?  band vs its OWN 24-28 Hz control, same build")
for key, lab in (("e_18-22", "grind#1 18-22 Hz"), ("e_6-9", "ratchet 6-9 Hz")):
    for b in BUILDS3:
        rs = creep(b)
        eps = G.episodes(rs)
        pairs = []
        for e in eps:
            for r in e:
                if r.get("e_24-28", 0) > 0 and np.isfinite(r[key]):
                    pairs.append((r[key] / r["e_24-28"], r["ep"]))
        if not pairs:
            continue
        by_ep = {}
        for v, ep in pairs:
            by_ep.setdefault(ep, []).append(v)
        keys = list(by_ep)
        pts = [np.median(v) for v in by_ep.values()]
        draws = np.full(2000, np.nan)
        for i in range(2000):
            idx = RNG.integers(0, len(keys), len(keys))
            draws[i] = np.median([np.median(by_ep[keys[j]]) for j in idx])
        lo, hi = np.percentile(draws, [2.5, 97.5])
        print(f"  {lab:<18} {b:<10}  rel.excess {np.median(pts):6.3f} [{lo:6.3f}, {hi:6.3f}]  "
              f"(nep={len(by_ep)})")
        OUT.setdefault("presence", {})[f"{key}|{b}"] = dict(med=float(np.median(pts)),
                                                            lo=float(lo), hi=float(hi),
                                                            nep=len(by_ep))

# =====================================================================================================
V.hdr("T4 -- GRIND #2 (30-49 Hz) vs the DESIGN PREDICTION at 42/85/255 deg/s, V76 vs V75 (+V74 context)")
print("  Design prediction [EVIDENCE, byte-derived, docs/HANDOFF-2026-08-07-v76-...]: V76/V75 = "
      "0.57x / 0.61x / 0.76x at 42/85/255 deg/s (200/400/1200 raw rate counts).")
print("  Tested here on ENGAGED windows (all speeds -- grind#2 is a rate phenomenon, not creep-only), "
      "band 30-49 Hz.\n")
RATE_BANDS = [(30.0, 60.0, "~42"), (65.0, 110.0, "~85"), (200.0, 320.0, "~255")]
PRED = {"~42": 0.57, "~85": 0.61, "~255": 0.76}
g2 = {}
for lo, hi, lab in RATE_BANDS:
    rows = {}
    for b in BUILDS3:
        rs = [r for r in allv(b) if lo <= r["rate"] < hi]
        rows[b] = rs
        print(f"  {lab:<6} deg/s  {b:<10}  n_windows={len(rs):5d}  n_ep={len(G.episodes(rs)):3d}")
    if len(rows["V76/r65"]) >= 8 and len(rows["V75/r5e"]) >= 8:
        r76v75 = episodes_ratio(rows["V76/r65"], rows["V75/r5e"], "e_30-49", RNG)
        print(f"    V76/V75  30-49 Hz  {r76v75['ratio']:.3f} [{r76v75['lo']:.3f}, {r76v75['hi']:.3f}]"
              f"   predicted {PRED[lab]:.2f}")
        g2[lab] = dict(v76_v75=r76v75, predicted=PRED[lab])
    else:
        print(f"    V76/V75  30-49 Hz  -- underpowered (n<8 on one side)")
        g2[lab] = dict(v76_v75=None, predicted=PRED[lab], underpowered=True)
    if len(rows["V74/r5d"]) >= 8 and len(rows["V75/r5e"]) >= 8:
        r74v75 = episodes_ratio(rows["V74/r5d"], rows["V75/r5e"], "e_30-49", RNG)
        print(f"    V74/V75  30-49 Hz  {r74v75['ratio']:.3f} [{r74v75['lo']:.3f}, {r74v75['hi']:.3f}]"
              f"   (context, not a prediction)")
        g2[lab]["v74_v75"] = r74v75
    print()
OUT["t4_grind2"] = g2

with open(ROOT / "_scratch/out/_v77sizing_symptoms.json", "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print("wrote _scratch/out/_v77sizing_symptoms.json")
