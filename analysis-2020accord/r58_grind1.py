#!/usr/bin/env python3
"""ROUTES 54 (V71B) and 58 (V71C) -- GRIND #1, on the corpus's own instrument.

PRE-REGISTERED (by the orchestrator, before this ran):
    route 58 (V71C) lands near V67/V68's 109 but WORSE;  route 54 (V71B) lands near stock's 879.

METRIC + ESTIMATOR are `_grind2_lib` unchanged: `e_18-22` = p99 of the analytic 18-22 Hz envelope
of one 2.56 s window on the torsion bar; medians over ENGAGED windows below 20 km/h; CIs resample
EPISODES; every ratio quoted against a split-half null computed FIRST with the same estimator.

🛑 MEMBERSHIP IS TESTED BY SUBSAMPLING AT MATCHED EXPOSURE, NOT BY CI OVERLAP. For each comparison
arm we draw the NEW route's exact block count from that arm's own engaged-creep windows and read the
median -- the distribution the new route's headline would have had if it had been that build.

⊕ EXCESS OVER CONTROL. The raw 18-22 ratio inflates when provoked steering raises the whole floor,
so every contrast is also reported as (18-22 ratio) / (24-28 ratio): a difference-in-differences
against the pre-declared negative control. 1-4 Hz is the exposure-matching validity check.

Writes `_r58_grind1.json`.  Usage: python r58_grind1.py [ep|blk]
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _r58_lib as L  # noqa: E402

L.install_fs()
G.EPKEY = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("ep", "blk") else "blk"
RNG = np.random.default_rng(20260804)
NBOOT, NULLREP = 2000, 300
CREEP = 20 / 3.6
OUT = {"epkey": G.EPKEY}

store = L.records()
NEW = ["V71B/r54", "V71C/r58"]

# the corpus ladder, in the record's own order. `gain` is the peak-velocity r24 price on record.
LADDER = ["V61/r31", "V59/r2c", "V64/r35", "V58/r2b", "V69/r4f", "V70/r50", "V62/r37", "V65/r3a",
          "V65/r3b", "V67/r47", "V68/r4e", "V71B/r54", "V71C/r58"]
RECORDED = {"V61/r31": 2501, "V69/r4f": 746, "V70/r50": 729, "V62/r37": 168, "V67/r47": 109}
# r24 peak-velocity price / r26 price, from the shipped images. See `_r58_lib` for the sweeps.
PRICE = {"V61/r31": (0.000, 1.000), "V59/r2c": (1.000, 1.000), "V64/r35": (1.000, 1.000),
         "V58/r2b": (1.000, 1.000), "V69/r4f": (1.000, 1.000), "V70/r50": (1.000, 1.000),
         "V62/r37": (2.000, 2.000), "V65/r3a": (2.000, 2.000), "V65/r3b": (2.000, 2.000),
         "V67/r47": (2.452, 0.167), "V68/r4e": (2.452, 0.167),
         "V71B/r54": (1.000, 2.000), "V71C/r58": (0.931, 1.000)}

ENG_CREEP = {b: [r for r in L.driving(store.get(b, []), b) if r["eng"] == 1 and r["v"] < CREEP]
             for b in LADDER}

# ------------------------------------------------------------------ §1 the ladder ----------------
L.hdr("§1  ★★ THE LADDER -- median e_18-22, ENGAGED, CREEP (< 20 km/h). Identical instrument.")
print("  `r24x`/`r26x` are the DELIVERED creep multipliers on the two rate-lane paths, swept from")
print("  the shipped images. `on record` is the number already in the kit's ladder -- recomputed")
print("  here rather than quoted, so the instrument's calibration is visible.\n")
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
                   rate50=float(np.median(G.col(rs, "rate"))),
                   ratep95=float(np.median(G.col(rs, "ratep95"))))
    mk = " ★★" if b in NEW else ""
    rec = RECORDED.get(b, "")
    print(f"  {b:<10} {PRICE[b][0]:>6.3f} {PRICE[b][1]:>6.3f} | {len(rs):>5} "
          f"{meds[b]['units']:>6} {meds[b]['v50']:>6.2f} {meds[b]['eff50']:>8.0f} "
          f"{meds[b]['rate50']:>8.1f} | {m:>11.1f} [{lo:>7.1f},{hi:>9.1f}] "
          f"{meds[b]['p90']:>7.0f} {str(rec):>10}{mk}")
OUT["ladder"] = meds

# ------------------------------------------------------------------ §2 subsample membership ------
L.hdr("§2  ★★ MEMBERSHIP BY SUBSAMPLING AT MATCHED EXPOSURE -- not by CI overlap")
print("  For each arm, draw the NEW route's own block count from that arm's engaged-creep windows,")
print("  with replacement, and read the median. P is two-sided: 2*min(P(sim>=obs), P(sim<=obs)).\n")


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
ARMS = {"V71B/r54": ["V71B/r54"], "V71C/r58": ["V71C/r58"],
        "stock pool": L.POOL_KD1, "V62+V65": L.POOL_KD2, "V67+V68": L.POOL_GATED,
        "V69/r4f": ["V69/r4f"], "V70/r50": ["V70/r50"]}
ENG = {k: [r for n in v for r in L.driving(store.get(n, []), n) if r["eng"] == 1]
       for k, v in ARMS.items()}
nulls = {}
print(f"  {'band':<8} {'arm':<14} {'median':>8} {'2.5%':>8} {'97.5%':>8}")
for band in ("1-4", "18-22", "24-28"):
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
# engaged and a manual window can NEVER share a cell and `boot_cellwise` returns NaN over 0 cells
# for any eng/man contrast. (`r50_grind1.py` ss6 carries this defect; its `eng_vs_man` block is
# structurally empty.) `recell` restratifies on the covariates only.
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
L.hdr("§4  ★★ MATCHED CROSS-BUILD CONTRASTS, ENGAGED CREEP -- ratio > 1 = MORE grind #1 on the new "
      "route")
print("  `excess` = (18-22 ratio) / (24-28 ratio): the subject band's move net of the control's.\n")
cc = {}
for new in NEW:
    A = ENG_CREEP[new]
    print(f"  --- {new}")
    print(f"      {'vs':<14} {'18-22':>8} {'[CI]':>19} {'24-28':>8} {'1-4':>8} {'excess':>8} "
          f"{'cells':>6} {'null(18-22)':>20}")
    for other in ("stock pool", "V62+V65", "V67+V68", "V69/r4f", "V70/r50"):
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
        for other in ("stock pool", "V62+V65", "V67+V68", "V69/r4f", "V70/r50"):
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

# ------------------------------------------------------------------ §5 within-route eng/man ------
L.hdr("§5  WITHIN-ROUTE ENGAGED vs MANUAL -- route 58's manual arm is BYTE-FOR-BYTE STOCK")
print("  On route 58 this is a within-route, within-driver, within-day contrast against STOCK.")
print("  On route 54 the dose is UNGATED, so both arms carry it and this is an engagement test only.")
print("  Strata are (v, eff, |rate|) -- `eng` is dropped, or no cell is ever shared.\n")
vet = {}
for b in NEW + ["V69/r4f", "V70/r50", "V62/r37", "V67/r47"]:
    rs = recell(L.driving(store.get(b, []), b), CELLFN["3d (v,eff,rate) -- eng dropped"])
    for rn, (lo, hi) in [("creep", (0.0, CREEP)), ("all speeds", (0.0, 1e9))]:
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

# ------------------------------------------------------------------ §6 the line ------------------
L.hdr("§6  IS THERE A LINE? averaged periodogram, engaged creep, located FREE in 12-30 Hz")
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

(HERE.parent / "_r58_grind1.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {HERE.parent / '_r58_grind1.json'}")
