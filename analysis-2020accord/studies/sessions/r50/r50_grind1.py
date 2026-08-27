#!/usr/bin/env python3
"""ROUTE 50 / V70 -- GRIND #1, and the orchestrator's pre-registered peak-velocity prediction.

THE PREDICTION (pre-registered by the orchestrator from the image bytes, before any measurement):
V69/V70 edit only Y[0..1] of rec0/rec1 -- the flat [0,400] rate segment -- so above rateKey ~1400
they are byte-identical to stock. `gp-0x6ac0` is |rate|, so the gain index sweeps 0 -> peak -> 0
twice per oscillation cycle and a damper acts in phase with velocity => what matters is the gain at
PEAK VELOCITY. Priced at creep (A_rk = 1927) that is 0.000 / 1.000 / 1.000 / 2.000 / 2.452 / 1.000
for V61 / stock / V69 / V62-V65 / V67-V68 / V70, which is MONOTONE against the measured medians
2501 / 879 / 746 / 168 / 109 / ?.  ==> V70's engaged-creep median should land near STOCK (~879),
NOT near V69's 746 and NOT near V62's 168.  A result near 168 REFUTES the hypothesis.

METRIC + ESTIMATOR are `_grind2_lib` unchanged (identical instrument to every prior route):
`e_18-22` = p99 of the analytic 18-22 Hz envelope of one 2.56 s window on the torsion bar;
`boot_cellwise` = stratified log-ratio over (eng, speed, effort, |rate|) cells, CI over EPISODES;
every ratio quoted against a split-half null computed FIRST with the identical estimator.

Writes `_scratch/out/_r50_grind1.json`.  Usage: python studies/sessions/r50/r50_grind1.py [ep|blk]
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
import _r50_lib as L  # noqa: E402

L.install_fs()
G.EPKEY = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("ep", "blk") else "blk"
RNG = np.random.default_rng(20260804)
NBOOT, NULLREP = 2000, 300
OUT = {"epkey": G.EPKEY}

store = L.records()
BUILD = "V70/r50"
CREEP = 20 / 3.6      # < 20 km/h, the kit's creep cut

# ---------------------------------------------------------------- ss0 route inventory ------------
L.hdr("ss0  ROUTE 50 EXPOSURE -- how much data is actually here")
print("  ⚠ 181.6 s over 3 segments; seg 0 is 61.6 s PARKED. Everything downstream is power-limited.\n")
inv = {}
print(f"  {'seg':>4} {'n':>6} {'dur s':>7} {'v max':>7} {'lat %':>7} {'eng s':>7} {'man s':>7} "
      f"{'creep-eng s':>12}")
for s in (0, 1, 2):
    d = G.load(s, G.BUILDS[BUILD]["cache"], G.BUILDS[BUILD]["pfx"])
    t = np.asarray(d["t"], float)
    fs = G.fs_of(d)
    lat = np.asarray(d["cc_lat"], float) > 0.5
    v = np.abs(np.asarray(d["cs_v"], float))
    ce = int((lat & (v < CREEP)).sum())
    print(f"  {s:>4} {len(t):>6} {t[-1] - t[0]:>7.1f} {v.max():>7.2f} {100 * lat.mean():>7.1f} "
          f"{lat.sum() / fs:>7.1f} {(~lat).sum() / fs:>7.1f} {ce / fs:>12.1f}")
    inv[str(s)] = dict(n=len(t), dur=float(t[-1] - t[0]), vmax=float(v.max()), fs=float(fs),
                       lat=float(lat.mean()), eng_s=float(lat.sum() / fs),
                       man_s=float((~lat).sum() / fs), creep_eng_s=float(ce / fs))
OUT["exposure"] = inv

r50 = store[BUILD]
print(f"\n  window records: {len(r50)}  "
      f"(engaged {sum(r['eng'] == 1 for r in r50)}, manual {sum(r['eng'] == 0 for r in r50)})")
print(f"  episodes (unit='{G.EPKEY}'): {len({r[G.EPKEY] for r in r50})}   "
      f"engaged {len({r[G.EPKEY] for r in r50 if r['eng'] == 1})}")

# ---------------------------------------------------------------- ss1 the medians ---------------
L.hdr("ss1  ★ THE HEADLINE NUMBER -- median e_18-22, ENGAGED, CREEP (< 20 km/h), every build")
print("  This is the exact statistic the orchestrator's prediction table is written in. The prior")
print("  builds are RE-COMPUTED here (not quoted) so the calibration of the instrument is visible.\n")

PRED = {"V61/r31": (0.000, 2501), "V59/r2c": (1.000, None), "V64/r35": (1.000, None),
        "V58/r2b": (1.000, None), "V69/r4f": (1.000, 746), "V62/r37": (2.000, 168),
        "V65/r3a": (2.000, None), "V65/r3b": (2.000, None), "V67/r47": (2.452, 109),
        "V68/r4e": (2.452, None), "V70/r50": (1.000, None)}
ORDER = ["V61/r31", "V59/r2c", "V64/r35", "V58/r2b", "V69/r4f", "V62/r37", "V65/r3a", "V65/r3b",
         "V67/r47", "V68/r4e", "V70/r50"]

print(f"  {'build':<10} {'peak-v gain':>11} | {'n':>5} {'units':>6} {'v p50':>6} {'eff p50':>8} "
      f"{'rate p50':>8} | {'e18-22 p50':>11} {'[95% CI]':>18} {'p90':>8}")
meds = {}
for b in ORDER:
    rs = [r for r in store.get(b, []) if r["eng"] == 1 and r["v"] < CREEP]
    if len(rs) < 4:
        print(f"  {b:<10} {PRED[b][0]:>11.3f} |  *** n={len(rs)} TOO FEW ***")
        meds[b] = dict(n=len(rs))
        continue
    m, lo, hi = G.boot_median_ci(rs, "e_18-22", RNG, nboot=NBOOT)
    v = G.col(rs, "e_18-22")
    meds[b] = dict(n=len(rs), units=len({r[G.EPKEY] for r in rs}), gain=PRED[b][0],
                   med=float(m), lo=float(lo), hi=float(hi), p90=float(np.percentile(v, 90)),
                   v50=float(np.median(G.col(rs, "v"))), eff50=float(np.median(G.col(rs, "eff"))),
                   rate50=float(np.median(G.col(rs, "rate"))))
    mk = " ★★" if b == BUILD else ""
    print(f"  {b:<10} {PRED[b][0]:>11.3f} | {len(rs):>5} {meds[b]['units']:>6} "
          f"{meds[b]['v50']:>6.2f} {meds[b]['eff50']:>8.0f} {meds[b]['rate50']:>8.1f} | "
          f"{m:>11.1f} [{lo:>7.1f},{hi:>8.1f}] {meds[b]['p90']:>8.0f}{mk}")
OUT["creep_medians"] = meds

print("\n  Pooled by peak-velocity gain (the prediction's own x-axis):")
POOLS = {"0.000  V61": ["V61/r31"], "1.000  stock V58+V59+V64": L.POOL_KD1,
         "1.000  V69": ["V69/r4f"], "2.000  V62+V65": L.POOL_KD2,
         "2.452  V67+V68": L.POOL_GATED, "1.000  ★ V70": [BUILD]}
pooled = {}
for k, names in POOLS.items():
    rs = [r for n in names for r in store.get(n, []) if r["eng"] == 1 and r["v"] < CREEP]
    if len(rs) < 4:
        print(f"    {k:<26} n={len(rs)} TOO FEW")
        continue
    m, lo, hi = G.boot_median_ci(rs, "e_18-22", RNG, nboot=NBOOT)
    pooled[k] = dict(n=len(rs), units=len({r[G.EPKEY] for r in rs}), med=float(m),
                     lo=float(lo), hi=float(hi))
    print(f"    {k:<26} n={len(rs):>5} u={pooled[k]['units']:>4}  median {m:>8.1f} "
          f"[{lo:>7.1f}, {hi:>8.1f}]")
OUT["pooled_by_gain"] = pooled

# ---------------------------------------------------------------- ss2 the nulls -----------------
L.hdr("ss2  THE NOISE FLOOR FIRST -- split-half null inside each arm, identical estimator")
ARMS = {"V70/r50 (2x<10, 1x>=50)": [BUILD], "Kd=2.00 pool V62+V65": L.POOL_KD2,
        "Kd=2 gated V67+V68": L.POOL_GATED, "Kd=1.00 stock pool": L.POOL_KD1,
        "V69/r4f (4x<10)": ["V69/r4f"]}
ENG = {k: [r for n in v for r in store.get(n, []) if r["eng"] == 1] for k, v in ARMS.items()}
print(f"  {'band':<8} {'arm':<26} {'median':>8} {'2.5%':>8} {'97.5%':>8}")
nulls = {}
for band in ("1-4", "18-22", "24-28", "30-40"):
    for k, rs in ENG.items():
        m, lo, hi = G.split_half_null(rs, "e_" + band, RNG, nrep=NULLREP)
        nulls[(band, k)] = (m, lo, hi)
        print(f"  {band:<8} {k:<26} {m:>8.3f} {lo:>8.3f} {hi:>8.3f}")
    print()
OUT["nulls"] = {f"{b}|{k}": [float(x) for x in v] for (b, k), v in nulls.items()}


def contrast(A, B, key, label, nullkey=None, min_ep=3, min_win=8):
    r, lo, hi, nc, na, nb, tab, _ = G.boot_cellwise(A, B, key, RNG, nboot=NBOOT,
                                                    min_ep=min_ep, min_win=min_win)
    s = (f"  {label:<44} {r:>7.3f}  [{lo:>6.3f}, {hi:>7.3f}]  cells={nc:>2}  "
         f"units {na:>3}/{nb:>3}")
    if nullkey and nullkey in nulls and np.isfinite(nulls[nullkey][1]):
        nl, nh = nulls[nullkey][1], nulls[nullkey][2]
        inside = np.isfinite(r) and nl <= r <= nh
        s += f"   null [{nl:.3f}, {nh:.3f}]  {'INSIDE NULL' if inside else '*** OUTSIDE'}"
    print(s)
    return dict(ratio=float(r), lo=float(lo), hi=float(hi), ncells=int(nc),
                unitsA=int(na), unitsB=int(nb),
                cells=[[list(c), na_, nb_, nea, neb, sa, sb, ratio, w]
                       for c, na_, nb_, nea, neb, sa, sb, ratio, w in tab])


def cellshare(A, B, min_ep=3, min_win=8):
    def occ(rs):
        c = {}
        for r in rs:
            c.setdefault(r["cell"], []).append(r)
        return c
    ca, cb = occ(A), occ(B)
    shared, qual = set(ca) & set(cb), []
    for c in sorted(shared):
        nea = len({r[G.EPKEY] for r in ca[c]})
        neb = len({r[G.EPKEY] for r in cb[c]})
        if nea >= min_ep and neb >= min_ep and len(ca[c]) >= min_win and len(cb[c]) >= min_win:
            qual.append(c)
    return len(ca), len(cb), len(shared), qual


# ---------------------------------------------------------------- ss3 matched contrasts ---------
L.hdr("ss3  ★★ MATCHED CROSS-BUILD CONTRASTS -- V70 vs each pool, ENGAGED, CREEP (< 20 km/h)")
print("  ratio > 1 = MORE 18-22 Hz on V70 = grind #1 worse than the comparison arm.\n")
A_creep = [r for r in ENG["V70/r50 (2x<10, 1x>=50)"] if r["v"] < CREEP]
cc = {}
for other in ("Kd=1.00 stock pool", "V69/r4f (4x<10)", "Kd=2.00 pool V62+V65",
              "Kd=2 gated V67+V68"):
    Bm = [r for r in ENG[other] if r["v"] < CREEP]
    na, nb, ns, qual = cellshare(A_creep, Bm)
    print(f"  --- vs {other}  |  V70 {na} cells, other {nb}, shared {ns}, QUALIFYING {len(qual)}")
    if not qual:
        print("      🛑 ZERO QUALIFYING SHARED CELLS at min_ep=3/min_win=8 -- relaxing to 2/4 "
              "and flagging it.")
    for band, lbl in (("18-22", "GRIND #1  18-22 Hz"), ("24-28", "neg control 24-28 Hz"),
                      ("30-40", "neg control 30-40 Hz"), ("1-4", "validity  1-4 Hz")):
        me, mw = (3, 8) if qual else (2, 4)
        cc[f"{other}|{band}"] = contrast(A_creep, Bm, "e_" + band,
                                         f"{lbl} vs {other.split()[0]}",
                                         nullkey=(band, other), min_ep=me, min_win=mw)
        cc[f"{other}|{band}"]["relaxed"] = not bool(qual)
    print()
OUT["creep_contrasts"] = cc

# ---------------------------------------------------------------- ss4 all speeds ----------------
L.hdr("ss4  SAME CONTRASTS, ALL SPEEDS (route 50 tops out at 16.95 m/s = 61 km/h)")
allc = {}
for other in ("Kd=1.00 stock pool", "V69/r4f (4x<10)", "Kd=2.00 pool V62+V65",
              "Kd=2 gated V67+V68"):
    na, nb, ns, qual = cellshare(ENG["V70/r50 (2x<10, 1x>=50)"], ENG[other])
    print(f"  --- vs {other}  |  shared {ns}, QUALIFYING {len(qual)}")
    for band in ("18-22", "24-28", "1-4"):
        me, mw = (3, 8) if qual else (2, 4)
        allc[f"{other}|{band}"] = contrast(ENG["V70/r50 (2x<10, 1x>=50)"], ENG[other],
                                           "e_" + band, f"{band} Hz vs {other.split()[0]}",
                                           nullkey=(band, other), min_ep=me, min_win=mw)
    print()
OUT["allspeed_contrasts"] = allc

# ---------------------------------------------------------------- ss5 speed census --------------
L.hdr("ss5  🛑 SPEED CENSUS -- an averaged/pooled comparison is only valid on matched speeds")
print(f"  {'arm':<26} {'n':>5} | " + " ".join(f"{n:>7}" for n in L.VBIN_NAMES))
cen = {}
for k, rs in ENG.items():
    v = G.col(rs, "v")
    h = [int(((v >= lo) & (v < hi)).sum()) for lo, hi in L.VBINS_V70]
    cen[k] = h
    print(f"  {k:<26} {len(rs):>5} | " + " ".join(f"{x:>7}" for x in h))
OUT["speed_census"] = cen

# ---------------------------------------------------------------- ss6 within-route veto ---------
L.hdr("ss6  WITHIN-ROUTE ENGAGED vs MANUAL on route 50 -- the order/route-confound veto")
print("  A tyre or engine order does not care about LKAS. Within one route every route confound")
print("  cancels; only speed must be matched, which boot_cellwise does by construction.\n")
vet = {}
for rn, (lo, hi) in [("all speeds", (0.0, 1e9)), ("creep < 5.556 m/s", (0.0, CREEP))]:
    A = [r for r in r50 if r["eng"] == 1 and lo <= r["v"] < hi]
    Bm = [r for r in r50 if r["eng"] == 0 and lo <= r["v"] < hi]
    print(f"  --- {rn}   engaged n={len(A)} u={len({r[G.EPKEY] for r in A})} | "
          f"manual n={len(Bm)} u={len({r[G.EPKEY] for r in Bm})}")
    if len(A) < 4 or len(Bm) < 4:
        print("      *** TOO FEW")
        continue
    for band in ("18-22", "24-28", "1-4"):
        vet[f"{rn}|{band}"] = contrast(A, Bm, "e_" + band, f"eng/man {band} Hz",
                                       min_ep=2, min_win=4)
OUT["eng_vs_man"] = vet

(HERE / "_scratch/out/_r50_grind1.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE / '_scratch/out/_r50_grind1.json'}")
