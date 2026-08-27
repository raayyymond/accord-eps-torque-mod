#!/usr/bin/env python3
"""Task #5 -- PART D/E/F: re-price the dose-response ladder, test monotonicity, do grind #2, and
attack the confounds.

🛑 Statistical rules, each of which has already retracted a claim in this kit:
  * every CI resamples EPISODES (contiguous runs of the engagement mask), never windows;
  * every ratio is quoted against that build's OWN split-half null, computed with the identical
    estimator, and the null is computed BEFORE the ratio is read;
  * the response is the record's own statistic -- median `e_18-22` (leakage-controlled p99 analytic
    band envelope, `_grind2_lib.win_env`) over engaged windows in the speed stratum;
  * every population carries a SPEED CENSUS, because a moving wheel order smears differently in a
    wide-speed route than a narrow one.
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
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G          # noqa: E402
import _r50_lib as R50           # noqa: E402  -- registers V68/r4e, V69/r4f, V70/r50
import _t5_ratekey_lib as T      # noqa: E402
import _t5_samples as S          # noqa: E402
from _t5_analyze import CREEP, HWY, IMG, NOMINAL, ORDER, ZERO_LANE, hdr, slab   # noqa: E402

RNG = np.random.default_rng(20260804)


# ------------------------------------------------------------------ estimators -------------------
def ep_median_ci(vals, eps, nboot=4000, agg=np.median):
    """(point, lo, hi) for agg(vals), resampling EPISODES with replacement."""
    vals, eps = np.asarray(vals, float), np.asarray(eps)
    ok = np.isfinite(vals)
    vals, eps = vals[ok], eps[ok]
    if not len(vals):
        return np.nan, np.nan, np.nan, 0, 0
    ue = np.unique(eps)
    per = [vals[eps == e] for e in ue]
    draws = np.empty(nboot)
    for b in range(nboot):
        i = RNG.integers(0, len(per), len(per))
        draws[b] = agg(np.concatenate([per[j] for j in i]))
    return (float(agg(vals)), float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5)),
            len(vals), len(ue))


def split_half_null(vals, eps, nrep=600, agg=np.median):
    """The build's own noise floor: halve ITS OWN episodes, take the ratio of the two halves."""
    vals, eps = np.asarray(vals, float), np.asarray(eps)
    ok = np.isfinite(vals) & (vals > 0)
    vals, eps = vals[ok], eps[ok]
    ue = np.unique(eps)
    if len(ue) < 4:
        return np.nan, np.nan, np.nan
    out = []
    for _ in range(nrep):
        p = RNG.permutation(len(ue))
        h = len(ue) // 2
        A = np.isin(eps, ue[p[:h]])
        Bm = np.isin(eps, ue[p[h:]])
        if A.sum() < 8 or Bm.sum() < 8:
            continue
        a, b = agg(vals[A]), agg(vals[Bm])
        if a > 0 and b > 0:
            out.append(a / b)
    if not out:
        return np.nan, np.nan, np.nan
    o = np.array(out)
    return float(np.exp(np.median(np.log(o)))), float(np.percentile(o, 2.5)), \
        float(np.percentile(o, 97.5))


def spearman(x, y):
    rx, ry = _rank(x), _rank(y)
    rx, ry = rx - rx.mean(), ry - ry.mean()
    d = np.sqrt((rx ** 2).sum() * (ry ** 2).sum())
    return float((rx * ry).sum() / d) if d > 0 else np.nan


def _rank(a):
    a = np.asarray(a, float)
    o = np.argsort(a, kind="mergesort")
    r = np.empty(len(a), float)
    r[o] = np.arange(len(a), dtype=float)
    # average ties
    for v in np.unique(a):
        m = a == v
        if m.sum() > 1:
            r[m] = r[m].mean()
    return r


# ------------------------------------------------------------------ the window records -----------
def wrec_response(build, band="e_18-22", eng=1, vlo=0.0, vhi=1e9):
    """The record's OWN statistic: per-window band envelope from `_grind2_lib.wrecs`."""
    rs = _WRECS[build]
    sel = [r for r in rs if r["eng"] == eng and vlo <= r["v"] < vhi]
    return (np.array([r[band] for r in sel], float),
            np.array([str(r["ep"]) for r in sel]),
            np.array([r["v"] for r in sel], float))


print("building window records with the record's own instrument (_grind2_lib.wrecs) ...", flush=True)
R50.install_fs()
_WRECS = {b: G.wrecs(b) for b in ORDER}
print("  done", flush=True)


def main():
    store = S.load()

    # =============================================================================================
    hdr("PART D1 -- the RESPONSE, recomputed (not quoted): median e_18-22, engaged, creep")
    print("  Speed census beside every cell, because the response is compared across routes whose")
    print("  speed distributions differ. `nep` is the number of engagement episodes = the CI's unit.")
    resp = {}
    RESP_VHI = 20 / 3.6      # the stratum the RECORDED ladder used -- reproduces 2501/879/168/109/746
    for vhi, vlab in ((CREEP, "creep <14.4 km/h"), (RESP_VHI, "creep <20 km/h")):
        print(f"\n  --- {vlab} ---")
        print(f"    {'build':10s} {'median':>9s} {'  [95% CI]':>20s} {'nwin':>6s} {'nep':>5s} | "
              f"{'v p25':>6s} {'v p50':>6s} {'v p75':>6s} | {'split-half null':>26s}")
        for b in ORDER:
            v, ep, sp = wrec_response(b, "e_18-22", eng=1, vhi=vhi)
            if not len(v):
                print(f"    {b:10s}  (no engaged windows in this stratum)")
                continue
            m, lo, hi, n, nep = ep_median_ci(v, ep)
            nl, nlo, nhi = split_half_null(v, ep)
            if vhi == RESP_VHI:
                resp[b] = (m, lo, hi, n, nep, v, ep)
            print(f"    {b:10s} {m:9.1f} {'[%7.1f, %7.1f]' % (lo, hi):>20s} {n:6d} {nep:5d} | "
                  f"{np.percentile(sp, 25):6.2f} {np.percentile(sp, 50):6.2f} "
                  f"{np.percentile(sp, 75):6.2f} | "
                  f"{('%.3f [%.3f, %.3f]' % (nl, nlo, nhi)) if np.isfinite(nl) else 'n/a (<4 episodes)':>26s}")

    # =============================================================================================
    hdr("PART D2 -- THE LADDER, priced three ways")
    print("  nominal@603  = the dose the design quoted, at rateKey 603 (V67 arm labelled 2.00)")
    print("  repriced     = MEDIAN per-sample delivered multiplier over that build's OWN grind-#1")
    print("                 burst samples (env18 >= 300, engaged, creep <20 km/h), scale A")
    print("  repricedB    = the same on scale B")
    rows = []
    for b in ORDER:
        if b not in resp:
            continue
        sl = slab(store, b, eng=1, vhi=RESP_VHI)
        rp = {}
        for nm, scale in (("A", T.SCALE_A), ("B", T.SCALE_B)):
            if b in ZERO_LANE:
                rp[nm] = 0.0
                continue
            m = sl["env18"] >= 300
            if m.sum() < 20:
                m = np.ones(len(sl["env18"]), bool)
            sc = T.speed_counts(sl["v"][m]).astype(np.int64)
            rk = (sl["rate"][m] * scale).astype(np.int64)
            rp[nm] = float(np.median(T.delivered(IMG[b], sc, rk, np.ones(len(sc), bool))))
        rows.append((b, NOMINAL[b], rp["A"], rp["B"], *resp[b]))
    print(f"\n    {'build':10s} {'nom@603':>8s} {'repricedA':>10s} {'repricedB':>10s} | "
          f"{'median e_18-22':>15s} {'[95% CI]':>20s} {'nwin':>6s} {'nep':>5s}")
    for b, nom, ra, rb, m, lo, hi, n, nep, _v, _e in rows:
        print(f"    {b:10s} {nom:8.3f} {ra:10.3f} {rb:10.3f} | {m:15.1f} "
              f"{'[%7.1f, %7.1f]' % (lo, hi):>20s} {n:6d} {nep:5d}")

    print("\n  ---- MONOTONICITY ----")
    for lab, k in (("nominal@603", 1), ("repriced scale A", 2), ("repriced scale B", 3)):
        x = np.array([r[k] for r in rows], float)
        y = np.array([r[4] for r in rows], float)
        rho = spearman(x, y)
        # CI: resample the WINDOWS' episodes inside each build, recompute each median, re-rank.
        draws = []
        for _ in range(2000):
            yy = []
            for r in rows:
                v, ep = r[9], r[10]
                ue = np.unique(ep)
                per = [v[ep == e] for e in ue]
                i = RNG.integers(0, len(per), len(per))
                yy.append(np.median(np.concatenate([per[j] for j in i])))
            draws.append(spearman(x, np.array(yy)))
        d = np.array(draws)
        print(f"    Spearman(dose {lab:17s}, median e_18-22) = {rho:+.3f}  "
              f"[{np.percentile(d, 2.5):+.3f}, {np.percentile(d, 97.5):+.3f}]  (n={len(x)} routes)")
    # collapsed to one point per DOSE LEVEL, which is what "the ladder" means
    print("\n    collapsed to one point per distinct re-priced dose (routes pooled inside a dose):")
    for lab, k in (("nominal@603", 1), ("repriced A", 2)):
        agg = {}
        for r in rows:
            agg.setdefault(round(r[k], 2), []).append(r)
        xs = sorted(agg)
        ys = [float(np.median(np.concatenate([q[9] for q in agg[d]]))) for d in xs]
        print(f"      {lab:12s}: " + "  ".join(f"{d:g}x->{y:.0f}" for d, y in zip(xs, ys))
              + f"   Spearman = {spearman(np.array(xs), np.array(ys)):+.3f}")

    # =============================================================================================
    hdr("PART E -- GRIND #2: where does 40-49 Hz live on the rate axis, and is it one curve?")
    for vlo, vhi, vlab in ((0.0, CREEP, "creep <14.4 km/h"), (HWY, 1e9, "highway >=50 km/h")):
        print(f"\n  --- {vlab}, engaged, burst = env40 >= 150 counts amplitude ---")
        print(f"    {'build':10s} {'nburst':>7s} {'%':>6s} | {'rate p50':>8s} {'p90':>7s} {'p99':>7s}"
              f" | {'A rk p50':>9s} {'p90':>8s} {'p99':>8s} {'%>=1126':>8s} {'%>=1500':>8s}"
              f" | {'delivA':>7s} {'delivB':>7s}")
        for b in ORDER:
            sl = slab(store, b, eng=1, vlo=vlo, vhi=vhi)
            if sl is None:
                continue
            m = sl["env40"] >= 150
            if m.sum() < 20:
                print(f"    {b:10s} {int(m.sum()):7d} {100 * m.mean():5.2f}%  (too few)")
                continue
            rc = sl["rate"][m]
            rkA = rc * T.SCALE_A
            dl = {}
            for nm, scale in (("A", T.SCALE_A), ("B", T.SCALE_B)):
                if b in ZERO_LANE:
                    dl[nm] = 0.0
                    continue
                sc = T.speed_counts(sl["v"][m]).astype(np.int64)
                rk = (rc * scale).astype(np.int64)
                dl[nm] = float(np.median(T.delivered(IMG[b], sc, rk, np.ones(len(sc), bool))))
            print(f"    {b:10s} {int(m.sum()):7d} {100 * m.mean():5.2f}% | {np.percentile(rc, 50):8.1f} "
                  f"{np.percentile(rc, 90):7.1f} {np.percentile(rc, 99):7.1f} | "
                  f"{np.percentile(rkA, 50):9.1f} {np.percentile(rkA, 90):8.1f} "
                  f"{np.percentile(rkA, 99):8.1f} {100 * (rkA >= 1126).mean():7.2f}% "
                  f"{100 * (rkA >= 1500).mean():7.2f}% | {dl['A']:7.3f} {dl['B']:7.3f}")

    print("\n  --- grind #2 RESPONSE: median e_40-49 per build, engaged, both strata ---")
    for vlo, vhi, vlab in ((0.0, CREEP, "creep"), (HWY, 1e9, "highway")):
        print(f"    {vlab}:")
        for b in ORDER:
            v, ep, sp = wrec_response(b, "e_40-49", eng=1, vlo=vlo, vhi=vhi)
            if len(v) < 8:
                print(f"      {b:10s} n={len(v)}  (underpowered)")
                continue
            m, lo, hi, n, nep = ep_median_ci(v, ep)
            print(f"      {b:10s} {m:9.2f} [{lo:8.2f}, {hi:8.2f}]  nwin={n:5d} nep={nep:3d} "
                  f"v p50={np.percentile(sp, 2):.1f}-{np.percentile(sp, 98):.1f} m/s")

    # =============================================================================================
    hdr("PART F -- CONFOUNDS")
    print("  F1. Does the re-pricing depend on SPEED rather than RATE? V69/V70's surface is shaped")
    print("      in BOTH. Delivered multiplier by speed bin, at the MEASURED burst rateKey.")
    print(f"    {'build':10s}" + "".join(f"{s:>9s}" for s in ("0-2 m/s", "2-4", "4-6", "6-10",
                                                             "10-14", "14+")))
    bins = [(0, 2), (2, 4), (4, 6), (6, 10), (10, 14), (14, 1e9)]
    for b in ORDER:
        cells = []
        for lo, hi in bins:
            sl = slab(store, b, eng=1, vlo=lo, vhi=hi)
            if sl is None or len(sl["v"]) < 50:
                cells.append("      -- ")
                continue
            if b in ZERO_LANE:
                cells.append(f"{0.0:9.3f}")
                continue
            m = sl["env18"] >= 300
            if m.sum() < 20:
                m = np.ones(len(sl["env18"]), bool)
            sc = T.speed_counts(sl["v"][m]).astype(np.int64)
            rk = (sl["rate"][m] * T.SCALE_A).astype(np.int64)
            cells.append(f"{np.median(T.delivered(IMG[b], sc, rk, np.ones(len(sc), bool))):9.3f}")
        print(f"    {b:10s}" + "".join(cells))

    print("\n  F2. NEGATIVE CONTROL band 24-28 Hz (pre-declared): median e_24-28, engaged creep.")
    print("      A dose effect that shows up here too is exposure, not the mode.")
    for b in ORDER:
        v, ep, sp = wrec_response(b, "e_24-28", eng=1, vhi=CREEP)
        if len(v) < 8:
            print(f"    {b:10s} n={len(v)}  (underpowered)")
            continue
        m, lo, hi, n, nep = ep_median_ci(v, ep)
        print(f"    {b:10s} {m:9.2f} [{lo:8.2f}, {hi:8.2f}]  nwin={n:5d} nep={nep:3d}")

    print("\n  F3. EXPOSURE-MATCHING validity check, band 1-4 Hz (the driver's own input).")
    for b in ORDER:
        v, ep, sp = wrec_response(b, "e_1-4", eng=1, vhi=CREEP)
        if len(v) < 8:
            print(f"    {b:10s} n={len(v)}  (underpowered)")
            continue
        m, lo, hi, n, nep = ep_median_ci(v, ep)
        print(f"    {b:10s} {m:9.1f} [{lo:8.1f}, {hi:8.1f}]  nwin={n:5d} nep={nep:3d}")


if __name__ == "__main__":
    main()
