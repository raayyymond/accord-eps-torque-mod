#!/usr/bin/env python3
r"""⭐ THE FULL-CORPUS POOL OF THE dCMD/dt HANDS-ON ARM -- the operator's own regime.

WHY.  Every dCMD/dt result so far is hands-off-dominated.  Under the D3 arm definition the
hands-ON arm became measurable but returned +0.0256 with per-route half-widths of +-0.13 to +-0.30
-- unable to distinguish zero from the hands-off +0.09.  Pooling more exposure is the only fix that
needs no new drive.

🛑🛑 A CORRECTION TO MY OWN COST ESTIMATE, MADE BEFORE ANY RESULT IS QUOTED.
I told the orchestrator the corpus's 994.9 s of engaged hands-on was "one script away."  **That was
wrong, and the error was mine: I assumed the caches existed.**  Disk inventory:
    * 49 routes have rlogs in `analysis-2020accord/rlogs/` (~440 segments)
    * **only 10 have caches in the current schema** -- r77 r78 r79 r7d r7e r7f r80 r81 r82 r85
    * the `_cache_r4*_ratchet.npz` files are an OLDER schema without `sc_t`/`seg` and cannot be
      pooled here without re-extraction
So the 994.9 s figure spans routes whose caches are NOT on disk.  What is poolable TODAY is stated
exactly below, against the 994.9 s target, and the cost of closing the gap is costed rather than
hand-waved.

🛑 THE LOADER BUG, AND WHY IT DOES NOT BITE HERE.  The recorded failure is a glob that matched only
the whole-route file `r<NN>.npz` and silently skipped the per-segment `r<NN>s<M>.npz` caches.  This
file **deliberately uses the WHOLE-ROUTE file and only that**, because the per-segment caches DO NOT
CARRY `seg` (verified: `missing=['seg']` on every one of them) and `seg` is required to split
episodes without bridging a segment gap.  Nothing is skipped, because nothing per-segment is wanted.
Every route actually loaded is enumerated in the output with its own second count -- **the exposure
accounting is printed, not assumed.**

THE ESTIMATOR.  Rank-residualise `y` (6-9 Hz vs 32-38 Hz band contrast of column torque) and `R`
(log10(1 + median |dCMD/dt|)) on `log|wheel rate|` and `log speed` **WITHIN EACH ROUTE**, then pool
the residuals and correlate.  Residualising within route removes route-level offsets, which a naive
pooled rank would conflate with the effect.  CI by bootstrap over **EPISODES** across the pooled
set, carrying the route label so an episode is always resampled whole.

ARM DEFINITION: **D3 -- window-MEDIAN |cs_tq| against 1200**, per
`memory/reference/measurement/reference-accord-steeringpressed-mask-excludes-the-symptom-regime.md`.  A median over 128
samples has no leverage from 2-38 Hz content, which is why the memory prefers it.  🛑 NOT the
>=0.95 purity rule: override is a point process with a 2-frame median run, so a purity rule over
128 frames returns essentially nothing.  That was my error and it is not repeated.

⊕ The memory's `Re(Z)` warning does NOT apply to this endpoint: it concerns an IMPEDANCE and
prescribes band POWER for symptom scoring.  This is a band-power CONTRAST of column torque, so it
never inherited the `Re(Z)` selection defect.  Stated so the warning is not over-applied.

Usage:  python studies/misc/dcmd_dt_corpus_pool.py
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
from scipy import stats

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
AN = ROOT / "analysis-2020accord"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(AN))

import dcmd_dt_hypothesis as H          # noqa: E402
import dcmd_dt_grip as G                # noqa: E402

OUT = AN / "sessions/v100"
RNG = np.random.default_rng(20260813)
THR = 1200.0
TARGET_S = 994.9                        # the memory's corpus engaged hands-on total
FS = 100.0


def discover():
    """Every whole-route cache on disk, in the current schema.  ENUMERATED, not globbed blind."""
    found = []
    for d in sorted(AN.glob("_cache_r*")):
        if not d.is_dir():
            continue
        stem = d.name.replace("_cache_", "")
        f = d / f"{stem}.npz"
        if not f.exists():
            print(f"    {d.name}: no whole-route {stem}.npz -- SKIPPED, and reported")
            continue
        try:
            z = np.load(f, allow_pickle=True)
            need = {"t", "seg", "cc_lat", "cs_tq", "cs_rate", "cs_v", "tq", "e4tq"}
            miss = need - set(z.files)
            if miss:
                print(f"    {stem}: MISSING {sorted(miss)} -- cannot pool, reported")
                continue
            found.append(stem)
        except Exception as exc:
            print(f"    {stem}: unreadable ({type(exc).__name__}) -- reported")
    return found


def main():
    print("=" * 112)
    print("  ⭐ FULL-CORPUS POOL, dCMD/dt HANDS-ON ARM (D3), control band 32-38 Hz")
    print("=" * 112)
    print("\n  DISK INVENTORY -- what is actually poolable today:")
    stems = discover()
    print(f"    {len(stems)} whole-route caches usable: {' '.join(stems)}")

    rows_all = []
    census = {}
    print(f"\n  {'route':6s} {'eng s':>8s} {'ON s':>8s} {'win tot':>8s} {'win ON':>7s} "
          f"{'win OFF':>8s} {'eps ON':>7s}")
    for stem in stems:
        try:
            D = G.build(stem)                       # R, y (32-38 contrast), lr, lv, ep, v
            z = np.load(AN / f"_cache_{stem}" / f"{stem}.npz", allow_pickle=True)
            atq = np.abs(np.asarray(z["cs_tq"], float))
            press = np.asarray(z["cs_press"], float) > 0.5
            eng = np.asarray(z["cc_lat"], float) > 0.5
            d = H.load(stem)
            _rw, eps = H.windows_for(d)
        except Exception as exc:
            print(f"  {stem:6s}  -- build failed ({type(exc).__name__}), reported and skipped")
            continue
        med = []
        for a_, b_ in eps:
            for s in range(0, (b_ - a_) - H.NPERSEG + 1, H.HOP):
                med.append(float(np.median(atq[a_ + s:a_ + s + H.NPERSEG])))
        med = np.array(med)
        if len(med) != len(D["R"]):
            print(f"  {stem:6s}  -- window count mismatch {len(med)} vs {len(D['R'])}, SKIPPED")
            continue
        on = med >= THR
        # residualise WITHIN ROUTE, then pool
        for tag, sel in (("on", on), ("off", ~on)):
            if sel.sum() < 20:
                continue
            y, R = D["y"][sel], D["R"][sel]
            C = np.column_stack([np.ones(sel.sum()), stats.rankdata(D["lr"][sel]),
                                 stats.rankdata(D["lv"][sel])])
            ry, rr = stats.rankdata(y), stats.rankdata(R)
            ey = ry - C @ np.linalg.lstsq(C, ry, rcond=None)[0]
            er = rr - C @ np.linalg.lstsq(C, rr, rcond=None)[0]
            for k in range(sel.sum()):
                rows_all.append((tag, stem, int(D["ep"][sel][k]), ey[k], er[k]))
        on_s = float((eng & press).sum() / FS)
        census[stem] = dict(engaged_s=float(eng.sum() / FS), hands_on_s=on_s,
                            n_windows=len(med), n_on=int(on.sum()), n_off=int((~on).sum()),
                            n_eps_on=int(len(set(D["ep"][on].tolist()))) if on.any() else 0)
        c = census[stem]
        print(f"  {stem:6s} {c['engaged_s']:8.1f} {c['hands_on_s']:8.1f} {c['n_windows']:8,} "
              f"{c['n_on']:7,} {c['n_off']:8,} {c['n_eps_on']:7d}")

    tot_on_s = sum(c["hands_on_s"] for c in census.values())
    print(f"\n  ⭐ EXPOSURE ACCOUNTING, PRINTED NOT ASSUMED:")
    print(f"     engaged hands-on POOLED = {tot_on_s:.1f} s  against the corpus target "
          f"{TARGET_S:.1f} s  =  **{100*tot_on_s/TARGET_S:.1f} %**")
    print(f"     shortfall = {TARGET_S - tot_on_s:.1f} s, held in routes whose caches are NOT on "
          f"disk (49 routes have rlogs; {len(stems)} have caches).")

    res = {"per_route": census, "pooled_hands_on_s": tot_on_s, "target_s": TARGET_S,
            "frac_of_target": tot_on_s / TARGET_S, "routes_loaded": stems}

    print("\n" + "=" * 112)
    print("  POOLED RESULT (within-route residuals, bootstrap over EPISODES)")
    print("=" * 112)
    for tag in ("on", "off"):
        sub = [r for r in rows_all if r[0] == tag]
        if len(sub) < 50:
            print(f"  {tag}: only {len(sub)} windows -- not pooled")
            continue
        ey = np.array([r[3] for r in sub])
        er = np.array([r[4] for r in sub])
        key = np.array([f"{r[1]}#{r[2]}" for r in sub])
        rho = float(np.corrcoef(er, ey)[0, 1])
        uk = np.unique(key)
        idx = {k: np.where(key == k)[0] for k in uk}
        boots = []
        for _ in range(4000):
            pick = RNG.choice(uk, len(uk), True)
            ii = np.concatenate([idx[k] for k in pick])
            if np.std(er[ii]) == 0 or np.std(ey[ii]) == 0:
                continue
            boots.append(float(np.corrcoef(er[ii], ey[ii])[0, 1]))
        lo, hi = float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))
        res[f"pooled_{tag}"] = dict(rho=rho, ci=[lo, hi], n_windows=len(sub),
                                    n_episodes=len(uk), half_width=(hi - lo) / 2,
                                    excludes_zero=bool(lo > 0 or hi < 0))
        star = "  ⭐ THE OPERATOR'S REGIME" if tag == "on" else ""
        print(f"  HANDS-{tag.upper():4s} partial rho = {rho:+.4f}  95 % CI [{lo:+.4f}, {hi:+.4f}]  "
              f"half-width +-{(hi-lo)/2:.4f}   n={len(sub):,} windows / {len(uk)} episodes{star}")

    if "pooled_on" in res and "pooled_off" in res:
        a, b = res["pooled_on"], res["pooled_off"]
        print(f"\n  ⇒ hands-ON half-width +-{a['half_width']:.4f} "
              f"(was +-0.13 to +-0.30 per route).")
        if a["excludes_zero"]:
            print("    ⭐ THE HANDS-ON CI EXCLUDES ZERO -- the operator's own regime is RESOLVED.")
        else:
            need = (a["half_width"] / 0.09) ** 2
            print(f"    🛑 THE HANDS-ON CI STILL CONTAINS ZERO.  To resolve an effect of +0.09 the")
            print(f"       half-width must fall below ~0.09, needing about {need:.1f}x the current")
            print(f"       hands-on exposure = ~{tot_on_s*need:.0f} s.  The full 994.9 s corpus "
                  f"gives {TARGET_S/tot_on_s:.2f}x, which is "
                  f"{'ENOUGH' if TARGET_S/tot_on_s >= need else 'NOT ENOUGH'}.")
            res["extra_exposure_factor_needed"] = float(need)
        print(f"    hands-OFF stays at {b['rho']:+.4f} [{b['ci'][0]:+.4f}, {b['ci'][1]:+.4f}], "
              f"{b['n_windows']:,} windows -- the reference arm.")
        res["on_vs_off_overlap"] = bool(a["ci"][0] <= b["rho"] <= a["ci"][1])
        print(f"    hands-OFF point estimate lies INSIDE the hands-ON CI: "
              f"{res['on_vs_off_overlap']}  ⇒ the two arms are "
              f"{'NOT distinguishable' if res['on_vs_off_overlap'] else 'DISTINGUISHABLE'}.")

    (OUT / "dcmd_dt_corpus_pool.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"\n  wrote {OUT / 'dcmd_dt_corpus_pool.json'}")
    return res


if __name__ == "__main__":
    main()
