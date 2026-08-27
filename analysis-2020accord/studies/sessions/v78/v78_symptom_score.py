#!/usr/bin/env python3
"""DELIVERABLES 1 and 2 -- V75 scored on V74's own yardstick, and the two symptoms separated.

Every statistic here is the one `studies/sessions/r5d/r5d_ratchet.py` / `studies/sessions/r5d/r5d_falsifiers.py` / `studies/sessions/r5d/r5d_bands.py` computed for
V74, run on route 5e's PRE-FAULT slice through the identical code path (`d6_events.runs` ->
`d6b_events_fixed.bursts` -> `_grind2_lib`). Nothing is re-implemented.

ORDER, and it is not negotiable (`memory/feedback/measurement/feedback-episodes-not-windows.md`):
  0  the SPLIT-HALF NULL for every statistic, on V74's own episodes and on V75's own episodes,
     BEFORE any ratio is printed. A ratio inside its own build's null is not a finding.
  1  the burst inventory -- `duty_rel`, `duty_abs`, burst `duration`, `envp99` -- for the 13-build
     corpus, run-resampled CIs, at engaged v < 12.5 m/s (primary) and engaged creep (indicative).
  2  the band scorecard -- 6-9 (micro ratchet), 18-22 (grind #1), 24-28 (negative control), each as
     an absolute median and as an excess over the 24-28 control, episode-resampled.
  3  V75 vs V74 head to head, stratified on (eng, v, eff, rate) cells so the routes' different speed
     distributions cannot drive the answer, with the MDE beside every ratio.
  4  the paired ratio-of-ratios R = (6-9 relative) / (18-22 relative), the one sub-1.3x statistic
     the V74 session had.

Usage:  python studies/sessions/v78/v78_symptom_score.py   ->  writes _scratch/out/_v78_score.json
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
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _r31_common as C  # noqa: E402
import d6_events as D  # noqa: E402
import v78_symptom_lib as V  # noqa: E402
from d6b_events_fixed import bursts  # noqa: E402

RNG = np.random.default_rng(780606)
OUT = {}
RATCHET, CARRIER = D.RATCHET, D.CARRIER
T_ABS = 600.0
BUILDS = V.CORPUS
PARK = {"V74/r5d": [2, 3, 9], "V75/r5e": [0]}
V.install_fs()


# ------------------------------------------------------------------ estimators (r5d's, verbatim) -
def med_ci_units(vals, units, nb=4000):
    per = {}
    for v, u in zip(vals, units):
        if np.isfinite(v):
            per.setdefault(u, []).append(v)
    ks = list(per)
    if len(ks) < 2:
        return np.nan, np.nan, np.nan, len(ks)
    allv = np.concatenate([per[k] for k in ks])
    dr = np.full(nb, np.nan)
    for i in range(nb):
        j = RNG.integers(0, len(ks), len(ks))
        dr[i] = np.median(np.concatenate([per[ks[k]] for k in j]))
    return (float(np.median(allv)), float(np.nanpercentile(dr, 2.5)),
            float(np.nanpercentile(dr, 97.5)), len(ks))


def ratio_ci(av, au, bv, bu, nb=4000):
    pa, pb = {}, {}
    for v, u in zip(av, au):
        if np.isfinite(v):
            pa.setdefault(u, []).append(v)
    for v, u in zip(bv, bu):
        if np.isfinite(v):
            pb.setdefault(u, []).append(v)
    ka, kb = list(pa), list(pb)
    if len(ka) < 2 or len(kb) < 2:
        return np.nan, np.nan, np.nan
    dr = np.full(nb, np.nan)
    for i in range(nb):
        x = np.median(np.concatenate([pa[ka[j]] for j in RNG.integers(0, len(ka), len(ka))]))
        y = np.median(np.concatenate([pb[kb[j]] for j in RNG.integers(0, len(kb), len(kb))]))
        dr[i] = x / y if y else np.nan
    obs = (np.median(np.concatenate([pa[k] for k in ka]))
           / np.median(np.concatenate([pb[k] for k in kb])))
    return float(obs), float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5))


def split_half_runs(vals, units, nrep=400):
    """The RUN-level split-half null for a run-resampled median ratio: halve a build's own runs."""
    per = {}
    for v, u in zip(vals, units):
        if np.isfinite(v):
            per.setdefault(u, []).append(v)
    ks = list(per)
    if len(ks) < 4:
        return np.nan, np.nan, np.nan
    out = []
    for _ in range(nrep):
        idx = RNG.permutation(len(ks))
        h = len(ks) // 2
        a = np.concatenate([per[ks[i]] for i in idx[:h]])
        b = np.concatenate([per[ks[i]] for i in idx[h:]])
        if len(a) and len(b) and np.median(b) > 0:
            out.append(np.median(a) / np.median(b))
    out = np.array(out, float)
    if not len(out):
        return np.nan, np.nan, np.nan
    return (float(np.median(out)), float(np.nanpercentile(out, 2.5)),
            float(np.nanpercentile(out, 97.5)))


def inventory(build, vhi):
    runs = []
    for _, s, a, b, d, fs in D.runs(build, 0.0, vhi, True, 512):
        x = np.asarray(d["tq"][a:b], float)
        env = np.abs(D.analytic(D.bp(x, fs, *RATCHET)))
        bs = bursts(env, fs)
        v = np.abs(np.asarray(d["cs_v"][a:b], float))
        runs.append(dict(build=build, run=(build, s, a), n=b - a, fs=fs, sec=(b - a) / fs,
                         x=x, env=env, v=float(np.mean(v)), vmin=float(np.min(v)),
                         vmax=float(np.max(v)),
                         duty_rel=float(sum(j - i for i, j, _ in bs) / max(len(env), 1)),
                         duty_abs=float(np.mean(env >= T_ABS)),
                         env_p99=float(np.percentile(env, 99)),
                         env_med=float(np.median(env)),
                         nb=len(bs), durs=[(j - i) / fs for i, j, _ in bs],
                         peaks=[p for _, _, p in bs]))
    return runs


# ================================================================== 1. INVENTORY ==================
INV = {}
for arm_label, VHI in (("engaged, v < 12.5 m/s  (PRIMARY)", 12.5),
                       ("engaged, v <  4.0 m/s  (CREEP -- indicative)", 4.0)):
    V.hdr(f"1. BURST INVENTORY, 13-BUILD CORPUS -- {arm_label}")
    print("  🛑 `duty_rel` is a SHAPE statistic (threshold = 1.8 x the run's OWN median envelope):")
    print("  a build that halves the whole 6-9 Hz signal leaves it unchanged. `duty_abs` (fraction")
    print("  of samples with the 5-12 Hz envelope >= 600 counts) and `envp99` carry the SCALE.\n")
    inv = {b: inventory(b, VHI) for b in BUILDS}
    print(f"  {'build':<10} {'k_ramp':>6} {'runs':>5} {'sec':>7} {'v_med':>6} "
          f"{'duty_rel':>21} {'duty_ABS':>21} {'dur_ms':>19} {'envp99':>19}")
    tab = {}
    for b in BUILDS:
        rs = inv[b]
        if len(rs) < 2:
            print(f"  {b:<10} {V.K_RAMP.get(b, np.nan):>6.4f} {len(rs):>5}   fewer than 2 "
                  f"qualifying runs -- NOT reportable")
            continue
        vv = np.array([r["v"] for r in rs])
        durs = [d_ for r in rs for d_ in r["durs"]]
        du = [r["run"] for r in rs for _ in r["durs"]]
        ru = [r["run"] for r in rs]
        dr_ = med_ci_units([r["duty_rel"] for r in rs], ru)
        da_ = med_ci_units([r["duty_abs"] for r in rs], ru)
        dd_ = med_ci_units(durs, du)
        ep_ = med_ci_units([r["env_p99"] for r in rs], ru)
        tab[b] = dict(k=V.K_RAMP.get(b, np.nan), nrun=len(rs),
                      sec=float(sum(r["sec"] for r in rs)), vmed=float(np.median(vv)),
                      duty_rel=dr_, duty_abs=da_, dur=dd_, envp99=ep_, nburst=len(durs))
        print(f"  {b:<10} {V.K_RAMP.get(b, np.nan):>6.4f} {len(rs):>5} "
              f"{sum(r['sec'] for r in rs):>7.1f} {np.median(vv):>6.2f} "
              f"{dr_[0]:>6.3f} [{dr_[1]:5.3f},{dr_[2]:6.3f}] "
              f"{da_[0]:>6.3f} [{da_[1]:5.3f},{da_[2]:6.3f}] "
              f"{1000 * dd_[0]:>5.0f} [{1000 * dd_[1]:4.0f},{1000 * dd_[2]:5.0f}] "
              f"{ep_[0]:>5.0f} [{ep_[1]:4.0f},{ep_[2]:5.0f}]")
    OUT[f"inventory|{VHI}"] = {k: {kk: (list(vv) if isinstance(vv, tuple) else vv)
                                   for kk, vv in v.items()} for k, v in tab.items()}
    INV[VHI] = inv

    # ---- rank of V75 -------------------------------------------------------------------------
    if "V75/r5e" in tab:
        print("\n  ★ RANK of V75 in the corpus (1 = lowest = best), on each statistic:")
        for key, lab in (("duty_rel", "duty_rel"), ("duty_abs", "duty_abs"), ("dur", "dur_ms"),
                         ("envp99", "envp99")):
            order = sorted([b for b in tab if np.isfinite(tab[b][key][0])],
                           key=lambda b: tab[b][key][0])
            print(f"     {lab:<9} " + "  <  ".join(
                f"{'**' + b.split('/')[0] + '**' if b == 'V75/r5e' else b.split('/')[0]}"
                f"={tab[b][key][0]:.3g}" for b in order))
            OUT.setdefault(f"rank|{VHI}", {})[lab] = [
                (b, float(tab[b][key][0])) for b in order]

    # ---- split-half NULLS, before any ratio ----------------------------------------------------
    print("\n  0. ★★ SPLIT-HALF NULL (a build's own runs, halved, same estimator) -- the floor")
    print("     any ratio must clear. Printed BEFORE the ratios, as the methodology requires.")
    nulls = {}
    for b in ("V74/r5d", "V75/r5e"):
        if b not in tab:
            continue
        rs = inv[b]
        for key, sel in (("duty_rel", lambda r: [r["duty_rel"]]),
                         ("duty_abs", lambda r: [r["duty_abs"]]),
                         ("dur", lambda r: r["durs"]),
                         ("envp99", lambda r: [r["env_p99"]])):
            vals = [x for r in rs for x in sel(r)]
            un = [r["run"] for r in rs for _ in sel(r)]
            nulls[f"{b}|{key}"] = split_half_runs(vals, un)
            p, lo, hi = nulls[f"{b}|{key}"]
            print(f"     {b:<10} {key:<9} null median {p:6.3f}  [{lo:6.3f}, {hi:6.3f}]"
                  + ("   (< 4 runs -- NOT COMPUTABLE)" if not np.isfinite(p) else ""))
    OUT[f"nulls|{VHI}"] = nulls

    # ---- the head-to-head --------------------------------------------------------------------
    if "V75/r5e" in tab:
        print("\n  ★★ V75 vs its predecessors -- run-resampled ratios (V75 / other). < 1 = V75 better")
        print(f"  {'vs':<10} {'duty_rel':>22} {'duty_ABS':>22} {'burst dur':>22} {'env p99':>22}")
        for b in ("V74/r5d", "V73/r5a", "V72/r59", "V67/r47", "V62/r37", "V59/r2c"):
            if b not in tab:
                continue
            A, B = inv["V75/r5e"], inv[b]
            cells = []
            for key, sel in (("duty_rel", lambda r: [r["duty_rel"]]),
                             ("duty_abs", lambda r: [r["duty_abs"]]),
                             ("dur", lambda r: r["durs"]),
                             ("envp99", lambda r: [r["env_p99"]])):
                av = [x for r in A for x in sel(r)]
                au = [r["run"] for r in A for _ in sel(r)]
                bv = [x for r in B for x in sel(r)]
                bu = [r["run"] for r in B for _ in sel(r)]
                cells.append(ratio_ci(av, au, bv, bu))
            print(f"  {b:<10} " + " ".join(f"{p:6.3f} [{lo:5.2f},{hi:6.2f}]"
                                           for p, lo, hi in cells))
            OUT.setdefault(f"ratios|{VHI}", {})[b] = {
                k: list(v) for k, v in zip(("duty_rel", "duty_abs", "dur", "envp99"), cells)}

# ================================================================== 2. BANDS ======================
R = V.records()
KEYS = [("e_6-9", "MICRO RATCHET  6-9 Hz"), ("e_18-22", "GRIND #1     18-22 Hz"),
        ("e_24-28", "CONTROL      24-28 Hz"), ("e_40-49", "GRIND #2     40-49 Hz"),
        ("e_1-4", "DRIVER IN      1-4 Hz")]
G.EPKEY = "ep"


def sub(b, eng=None, vlo=None, vhi=None):
    o = [r for r in R[b] if r["seg"] not in PARK.get(b, [])]
    if eng is not None:
        o = [r for r in o if r["eng"] == eng]
    if vlo is not None:
        o = [r for r in o if r["v"] >= vlo]
    if vhi is not None:
        o = [r for r in o if r["v"] < vhi]
    return o


V.hdr("2. BAND SCORECARD -- p99 analytic band envelope, medians with EPISODE-resampled CIs")
print("  🛑 Route 5e has ZERO engaged windows above 18.7 m/s, so every cross-route arm below is")
print("  capped at 12.5 m/s unless stated. Bands are `_grind2_lib.BANDS`, unchanged.\n")
sc = {}
ARMS = [("engaged, < 12.5 m/s", dict(eng=1, vhi=12.5)),
        ("engaged, CREEP 0.5-4", dict(eng=1, vlo=0.5, vhi=4.0)),
        ("engaged, 9.4-12.5 clean", dict(eng=1, vlo=9.4, vhi=12.5)),
        ("manual, < 12.5 m/s", dict(eng=0, vhi=12.5))]
for lab, kw in ARMS:
    print(f"\n  --- {lab} ---")
    print(f"    {'build':<10} {'n':>4} {'ep':>3} " +
          "".join(f"{k[1][:13]:>26}" for k in KEYS[:3]) + f"{'6-9/ctl':>9}{'18-22/ctl':>10}")
    for b in ("V74/r5d", "V75/r5e", "V73/r5a", "V72/r59", "V67/r47", "V62/r37", "V59/r2c"):
        rs = sub(b, **kw)
        if len(rs) < 12:
            print(f"    {b:<10} {len(rs):>4}   UNPOWERED (<12 windows) -- exposure, not a null")
            continue
        cells = []
        for k, _ in KEYS[:3]:
            p, lo, hi = G.boot_median_ci(rs, k, RNG, nboot=1200)
            sc[f"{lab}|{b}|{k}"] = [p, lo, hi, len(rs)]
            cells.append(f"{p:7.1f}[{lo:6.1f},{hi:7.1f}]")
        ex = {}
        for k, kl in (("e_6-9", "6-9"), ("e_18-22", "18-22")):
            vv = np.array([r[k] / r["e_24-28"] for r in rs
                           if np.isfinite(r[k]) and r.get("e_24-28", 0) > 0], float)
            ex[kl] = float(np.median(vv)) if len(vv) > 8 else np.nan
            sc[f"{lab}|{b}|excess_{kl}"] = ex[kl]
        ne = len({r["ep"] for r in rs})
        print(f"    {b:<10} {len(rs):>4} {ne:>3} " + "".join(f"{c:>26}" for c in cells)
              + f"{ex['6-9']:>9.2f}{ex['18-22']:>10.2f}")
OUT["scorecard"] = sc

# ================================================================== 3. HEAD TO HEAD ===============
V.hdr("3. ★★ V75 vs V74 -- STRATIFIED log-ratio on (eng, v, eff, rate) cells, episode-resampled")
print("  Cells are `_grind2_lib`'s own; a cell enters only if BOTH builds have >= `min_ep` episodes")
print("  and >= 8 windows in it, so the routes' different speed distributions cannot drive it.")
print("  🛑 V75 has 6 engaged episodes total, so `min_ep = 3` empties the table. Both `min_ep = 3`")
print("  (the V74 session's setting) and `min_ep = 2` are reported; the relaxed one is the only")
print("  one with cells, and its CI is correspondingly wide. MDE = exp(2.80 x sd_log).\n")
h2h = {}
for min_ep in (3, 2):
    print(f"  --- min_ep = {min_ep} ---")
    print(f"    {'band':<22} {'ratio V75/V74':>28} {'MDE':>7} {'cells':>6} {'epA':>4} {'epB':>4} "
          f"{'V74 null':>18} {'V75 null':>18}")
    for k, kl in KEYS:
        nA = G.split_half_null(sub("V74/r5d"), k, RNG, nrep=150, min_ep=min_ep)
        nB = G.split_half_null(sub("V75/r5e"), k, RNG, nrep=150, min_ep=min_ep)
        pt, lo, hi, nc, na, nb, tab, draws = G.boot_cellwise(
            sub("V75/r5e"), sub("V74/r5d"), k, RNG, nboot=1200, min_ep=min_ep)
        if not np.isfinite(pt):
            print(f"    {kl:<22}   -- no shared cell at min_ep={min_ep}")
            continue
        sd = float(np.nanstd(draws)) if draws is not None else np.nan
        mde = float(np.exp(2.80 * sd)) if np.isfinite(sd) else np.nan
        h2h[f"{k}|min_ep{min_ep}"] = dict(ratio=pt, lo=lo, hi=hi, mde=mde, cells=nc,
                                          epA=na, epB=nb, nullA=list(nA), nullB=list(nB))
        print(f"    {kl:<22} {pt:9.3f} [{lo:7.3f}, {hi:7.3f}] {mde:>7.3f} {nc:>6} {na:>4} {nb:>4} "
              f"[{nA[1]:6.3f},{nA[2]:6.3f}] [{nB[1]:6.3f},{nB[2]:6.3f}]")
    print()
OUT["head_to_head"] = h2h

# ================================================================== 4. PAIRED R ===================
V.hdr("4. ★ THE PAIRED RATIO-OF-RATIOS  R = (6-9 / 24-28) / (18-22 / 24-28)  -- within-window")
print("  The V74 session's only sub-1.3x statistic. Both bands on the SAME windows, each relative")
print("  to the same 24-28 control, so one shared bootstrap draw cancels route, exposure and driver.")
print("  R > 1 means the damper is doing relatively LESS for the ratchet than for grind #1.\n")


def paired_R(rs, nboot=3000):
    eps = {}
    for r in rs:
        if r.get("e_24-28", 0) > 0 and np.isfinite(r["e_6-9"]) and np.isfinite(r["e_18-22"]):
            eps.setdefault(r["ep"], []).append((r["e_6-9"] / r["e_24-28"],
                                                r["e_18-22"] / r["e_24-28"]))
    ks = list(eps)
    if len(ks) < 3:
        return (np.nan,) * 3 + (len(ks),)
    allv = np.concatenate([eps[k] for k in ks])
    obs = float(np.median(allv[:, 0]) / np.median(allv[:, 1]))
    dr = np.full(nboot, np.nan)
    for i in range(nboot):
        j = RNG.integers(0, len(ks), len(ks))
        z = np.concatenate([eps[ks[m]] for m in j])
        dr[i] = np.median(z[:, 0]) / np.median(z[:, 1])
    return obs, float(np.nanpercentile(dr, 2.5)), float(np.nanpercentile(dr, 97.5)), len(ks)


pr = {}
for lab, kw in (("engaged, < 12.5 m/s", dict(eng=1, vhi=12.5)),
                ("engaged, CREEP 0.5-4", dict(eng=1, vlo=0.5, vhi=4.0)),
                ("engaged, ALL speed", dict(eng=1))):
    print(f"  --- {lab} ---")
    for b in ("V74/r5d", "V75/r5e", "V73/r5a", "V72/r59"):
        o, lo, hi, ne = paired_R(sub(b, **kw))
        pr[f"{lab}|{b}"] = [o, lo, hi, ne]
        print(f"    {b:<10} R = {o:6.3f} [{lo:6.3f}, {hi:6.3f}]   {ne} episodes")
    print()
OUT["paired_R"] = pr

with open(ROOT / "_scratch/out/_v78_score.json", "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print("\nwrote _scratch/out/_v78_score.json")
