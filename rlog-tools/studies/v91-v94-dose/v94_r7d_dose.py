#!/usr/bin/env python3
r"""V94's DOSE-IN-FORCE test on route 7d — the direct successor to the V91/V92 ×1.5 null.

🛑 WHY THIS RUNS FIRST, AGAIN.  Routes 78/79 measured the ×1.5 dose INERT at `gp-0x6b26`
(engaged cell-stratified ratio 0.99 [0.91, 1.26] against a pre-registered 1.50, MANUAL control
1.009 [0.982, 1.047]).  If V94's ×0.25 is also inert, every band number on route 7d is measuring
a car whose calibration did not change, and must not be reported as a firmware effect.

===================================================================================================
V94 IS THE FIRST BUILD TO DOSE THE MANUAL RECORD, AND THAT IS THE WHOLE POINT
===================================================================================================
    mode 24 (MANUAL)          Y × 0.50   -> the manual arm should read 0.50, not 1.00
    modes 26 / 27 (ENGAGED)   Y × 0.25
    0xC640A / 0xC640C fallbacks × 0.75
Three distinct factors ⇒ the ratio against route 77 NAMES THE LIVE BRANCH:
    0.25 ⇒ mode 26/27 is the engaged record (the kit's standing assumption)
    0.50 ⇒ the car reads MODE 24 IN BOTH STATES — the suspected cause of the V91/V92 null
    0.75 ⇒ a FALLBACK constant is live; the mode records are dead
    1.00 ⇒ inert again; something upstream is wrong

===================================================================================================
★ THE `sar 1` PACKER MAKES |gp-0x6b26| EXACTLY RECOVERABLE — a first for this kit
===================================================================================================
    wire = floor(5n/2)      n even -> wire = 5n/2      (wire ≡ 0 mod 5)  -> n = 2·wire/5
                            n odd  -> wire = (5n-1)/2  (wire ≡ 2 mod 5)  -> n = (2·wire+1)/5
⇒ the inversion is EXACT, count for count.  Under `sar 3` (routes 77/78) it is not: wire =
floor(5n/8) leaves an interval 1.6 counts wide, so their medians are coarsely quantised.

🛑 AND THE `wire × 8/5` CONVENTION IS BIASED AT SMALL VALUES, WHICH IS ALL THIS ROUTE HAS.
   `floor(5n/8) = w`  ⇒  n ∈ [ceil(8w/5), ceil(8(w+1)/5) − 1].  For w = 1 that is n ∈ {2, 3},
   yet the convention reports 1.6.  At the medians this drive actually produces (1–3 counts) the
   convention UNDERSTATES the baseline by ~35 %, which INFLATES every ratio.  So the comparison is
   run under two reconstructions and both are reported:
   (a) LEGACY  — r77/r78 = wire × 8/5, the convention routes 78/79 were published under;
   (b) MIDPOINT — r77/r78 = the midpoint of the exact pre-image interval.  🛑 (b) is the one to
       believe on this route; (a) is carried only so the numbers are comparable to the record.
   A first re-packing attempt (r7d pushed back through the sar-3 packer) was DISCARDED: it
   quantises the small counts to zero, the per-cell median becomes 0, and the geometric mean
   collapses to 0.  That is an artefact of the estimator, not a measurement, and it is recorded
   here so nobody re-derives it.

🛑 THE LIMITATION THAT MATTERS, STATED UP FRONT.  `gp-0x6b26 = −K · gp-0x6c2c` and `gp-0x6c2c` is
   EPS-motor ACCELERATION.  The ratio estimates K's change ONLY IF the acceleration distribution is
   matched between routes.  The operator reports the car shaking violently on this build — which is
   itself a change in motor acceleration.  A ratio ABOVE 0.25 therefore does NOT cleanly falsify
   the dose; it is consistent with (gain × 0.25) × (input × m).  The input is estimated separately
   below and reported beside the ratio, never folded into it.

🛑 EXPOSURE.  Route 7d never exceeded 6.2 km/h, so the standard 5-bin speed partition collapses to
   one cell.  The speed bins here are RE-CUT for the low-speed regime and applied IDENTICALLY to
   every route.  Bootstrap is over EPISODES (contiguous engaged / manual runs), never frames.

Usage:  python studies/v91-v94-dose/v94_r7d_dose.py
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
CACHE = ROOT / "analysis-2020accord"
sys.path.insert(0, str(HERE))

import v91_v92_dose_in_force as DIF   # noqa: E402  -- the SAME estimator routes 78/79 were scored with

# ---- re-cut the speed partition for a drive that never left the parking lot.
#      Applied identically to every route, so the comparison stays matched.
DIF.SPEED_BINS = [(0.0, 0.5), (0.5, 2.0), (2.0, 4.0), (4.0, 6.2)]
DIF.RATE_BINS = [(0.0, 1.0), (1.0, 3.0), (3.0, 6.0), (6.0, 13.0), (13.0, 25.0), (25.0, 50.0),
                 (50.0, 1e9)]
DIF.MIN_CELL = 25                    # 0.5 s of 50 Hz 427 per cell per route
DIF.NBOOT = 4000
RNG = np.random.default_rng(20260811)
DIF.RNG = RNG

SAR3_SCALE = 8.0 / 5.0
V94_EXPECT = {"engaged": 0.25, "manual": 0.50}


# ======================================================================================
def invert_sar1(wire):
    """EXACT inverse of `wire = floor(5n/2)`.  Asserts every sample is on the legal lattice."""
    w = np.asarray(wire, np.int64)
    r = w % 5
    assert bool(np.all((r == 0) | (r == 2))), (
        "a 427 wire value is off the `sar 1` lattice -- route 7d is not V94, or the tap is wrong")
    n = np.where(r == 0, 2 * w // 5, (2 * w + 1) // 5)
    assert bool(np.all(((n * 5) >> 1) == w)), "sar-1 inversion does not round-trip"
    return n.astype(np.int64)


def midpoint_sar3(wire):
    """Midpoint of the exact pre-image of `wire = floor(5n/8)`.  Unbiased where × 8/5 is not."""
    w = np.asarray(wire, np.int64)
    lo = -(-8 * w // 5)                      # ceil(8w/5)
    hi = -(-8 * (w + 1) // 5) - 1            # ceil(8(w+1)/5) - 1
    hi = np.maximum(hi, lo)
    assert bool(np.all(((lo * 5) >> 3) == w)), "sar-3 pre-image lower bound does not round-trip"
    assert bool(np.all(((hi * 5) >> 3) == w)), "sar-3 pre-image upper bound does not round-trip"
    return (lo + hi) / 2.0


def arrays(route, stem, sar):
    """427 samples with engagement / speed / rate interpolated onto the 50 Hz 0x1AB grid."""
    z, rt, v, lat, rate = DIF.load(route, stem)
    t = np.asarray(z["ab_t1ab"], float)
    wire = np.asarray(z["ab_mt"], int)
    if sar == 1:
        n = invert_sar1(wire)
        counts = n.astype(float)             # EXACT
        mid = n.astype(float)                # nothing to reconstruct
    else:
        counts = wire * SAR3_SCALE           # the legacy convention
        mid = midpoint_sar3(wire)
    return dict(t=t, wire=wire, counts=counts, mid=mid,
                lat=DIF.onto(t, rt, lat, "bool"), v=DIF.onto(t, rt, v) * 3.6,
                rate=DIF.onto(t, rt, rate))


def arm(tag, A, B, sel_a, sel_b, key, stat=np.median):
    av, ac = A[key][sel_a], DIF.cell_id(A["v"], A["rate"])[sel_a]
    bv, bc = B[key][sel_b], DIF.cell_id(B["v"], B["rate"])[sel_b]
    aep, _ = DIF.episodes_of(sel_a)
    bep, _ = DIF.episodes_of(sel_b)
    aep, bep = aep[sel_a], bep[sel_b]
    r, rows = DIF.stratified_ratio(av, ac, bv, bc, stat)
    if not rows:
        print(f"\n  --- {tag} ---\n    🛑 NO COMMON CELLS (test frames {int(sel_a.sum()):,}, "
              f"baseline {int(sel_b.sum()):,}) -- ARM UNSCOREABLE")
        return dict(ratio=float("nan"), ci=[float("nan")] * 2, n_cells=0,
                    n_test=int(sel_a.sum()), n_base=int(sel_b.sum()), cells=[],
                    n_episodes_test=int(len(np.unique(aep))))
    lo, hi, nb = DIF.boot_ratio(av, ac, aep, bv, bc, bep, stat)
    print(f"\n  --- {tag} ---")
    print(f"    common cells {len(rows)}   test frames {int(sel_a.sum()):,}   baseline "
          f"{int(sel_b.sum()):,}   episodes {len(np.unique(aep))}/{len(np.unique(bep))}")
    print(f"    {'cell':<40} {'n_test':>7} {'n_base':>7} {'test':>8} {'base':>8} {'ratio':>7}")
    for c, na, nb_, ma, mb, rr in sorted(rows, key=lambda x: -x[1]):
        print(f"    {DIF.cellname(c):<40} {na:>7,} {nb_:>7,} {ma:>8.2f} {mb:>8.2f} {rr:>7.3f}")
    print(f"    ⇒ STRATIFIED RATIO {r:.4f}   95 % CI [{lo:.4f}, {hi:.4f}]   ({nb} episode draws)")
    return dict(ratio=r, ci=[lo, hi], n_cells=len(rows), n_test=int(sel_a.sum()),
                n_base=int(sel_b.sum()), n_episodes_test=int(len(np.unique(aep))),
                cells=[dict(name=DIF.cellname(c), n_test=na, n_base=nb_, test=ma, base=mb,
                            ratio=rr) for c, na, nb_, ma, mb, rr in rows])


def branch_verdict(r, ci):
    if not np.isfinite(r):
        return "🛑 UNSCOREABLE -- no common cells"
    cand = {"mode 26/27 record LIVE (×0.25)": 0.25, "MODE 24 IN BOTH STATES (×0.50)": 0.50,
            "a FALLBACK constant LIVE (×0.75)": 0.75, "INERT -- nothing changed (×1.00)": 1.00}
    inside = [k for k, v in cand.items() if ci[0] <= v <= ci[1]]
    near = min(cand, key=lambda k: abs(np.log(r / cand[k])))
    if not inside:
        return (f"🛑 NO pre-registered branch lies in the CI [{ci[0]:.3f}, {ci[1]:.3f}]. "
                f"Nearest is {near}. UNEXPLAINED -- do not name a cause.")
    if len(inside) == 1:
        return f"⇒ {inside[0]}  (the only pre-registered branch inside the CI)"
    return (f"⚠ AMBIGUOUS -- the CI admits {len(inside)} branches: " + "; ".join(inside) +
            f".  Point estimate nearest {near}.")


# ======================================================================================
def main():
    print("=" * 100)
    print(" V94 DOSE-IN-FORCE, route 7d.  Baselines: route 77 (V90) and route 78 (V91).")
    print(" 🛑 route 79 (V92) is EXCLUDED -- its 427 was repointed to gp-0x6bbe and carries no b26.")
    print("=" * 100)
    A = arrays("7d", "r7d", sar=1)
    B77 = arrays("77", "r77", sar=3)
    B78 = arrays("78", "r78", sar=3)

    res = {"speed_bins": DIF.SPEED_BINS, "rate_bins": DIF.RATE_BINS, "min_cell": DIF.MIN_CELL,
           "nboot": DIF.NBOOT,
           "note": ("route 7d never exceeded 6.2 km/h; the speed partition is re-cut for the "
                    "low-speed regime and applied identically to every route.")}

    # ---- the exact-inversion receipt
    n = invert_sar1(A["wire"])
    print(f"\n  |gp-0x6b26| recovered EXACTLY from the sar-1 wire on all {len(n):,} 427 frames "
          f"(lattice + round-trip both asserted).")
    print(f"    counts p50/p75/p90/p95/p99/max = " +
          "/".join(f"{np.percentile(n, p):.0f}" for p in (50, 75, 90, 95, 99)) + f"/{n.max()}")
    for tag, m in (("engaged", A["lat"]), ("manual", ~A["lat"])):
        c = n[m]
        print(f"    {tag:8s} n={len(c):>6,}  " +
              "  ".join(f"p{p}={np.percentile(c, p):>6.1f}" for p in (50, 75, 90, 95, 99)) +
              f"  max={c.max()}")
    res["r7d_counts_exact"] = dict(
        n=int(len(n)), **{f"p{p}": float(np.percentile(n, p)) for p in (50, 75, 90, 95, 99)},
        max=int(n.max()),
        engaged={f"p{p}": float(np.percentile(n[A['lat']], p)) for p in (50, 75, 90, 95, 99)},
        manual={f"p{p}": float(np.percentile(n[~A['lat']], p)) for p in (50, 75, 90, 95, 99)})

    # ---- the build's own headline prediction, tested on its own terms
    print("\n  --- THE BUILD'S OWN PREDICTION: r7d's WIRE distribution reproduces route 78's ---")
    print("      🛑 This is NOT an identity test (V90/V91 produce the same wire), but it IS the")
    print("         build's stated sizing claim, so it is scored.")
    hdr = f"    {'route':<14}" + "".join(f"{'p' + str(p):>8}" for p in (50, 75, 90, 95, 99)) + \
          f"{'max':>8}"
    print(hdr)
    wpred = {}
    for tag, W in (("r7d (V94)", A["wire"]), ("r78 (V91)", B78["wire"]), ("r77 (V90)", B77["wire"])):
        wpred[tag] = [float(np.percentile(W, p)) for p in (50, 75, 90, 95, 99)] + [float(W.max())]
        print(f"    {tag:<14}" + "".join(f"{v:>8.0f}" for v in wpred[tag]))
    print("      predicted for r7d (from the build script): p75/p90/p95/p99/max  5/10/17/37/137")
    res["wire_percentiles"] = wpred

    # ---- ARM 1 / 2, both reconstructions, and a p75 sensitivity away from the quantisation floor
    for key, label in (("mid", "MIDPOINT RECONSTRUCTION  ★ believe this one on this route"),
                       ("counts", "LEGACY `wire × 8/5`  (biased low at small counts -- carried "
                                  "only for comparability with the published r78/r79 numbers)")):
        print("\n" + "=" * 100)
        print(f" {label}")
        print("=" * 100)
        for bname, B in (("r77 (V90)", B77), ("r78 (V91)", B78)):
            k = f"{key}_vs_{bname[:3]}"
            e = arm(f"ARM 1 · ENGAGED vs {bname}   (V94 predicts 0.25)", A, B,
                    A["lat"], B["lat"], key)
            e["verdict"] = branch_verdict(e["ratio"], e["ci"])
            print(f"    {e['verdict']}")
            m = arm(f"ARM 2 · MANUAL vs {bname}   (🛑 V94 predicts 0.50 -- the manual record was "
                    f"DOSED for the first time)", A, B, ~A["lat"], ~B["lat"], key)
            m["verdict"] = branch_verdict(m["ratio"], m["ci"])
            print(f"    {m['verdict']}")
            res[k] = dict(engaged=e, manual=m)

    print("\n" + "=" * 100)
    print(" SENSITIVITY: the same arms on the per-cell p75 instead of the median.  The medians on")
    print(" this route sit at 1-3 counts, i.e. ON the quantisation floor; p75 is away from it.")
    print("=" * 100)
    p75 = lambda x: float(np.percentile(x, 75))          # noqa: E731
    for bname, B in (("r77 (V90)", B77), ("r78 (V91)", B78)):
        e = arm(f"ARM 1 p75 · ENGAGED vs {bname}", A, B, A["lat"], B["lat"], "mid", p75)
        e["verdict"] = branch_verdict(e["ratio"], e["ci"])
        print(f"    {e['verdict']}")
        m = arm(f"ARM 2 p75 · MANUAL vs {bname}", A, B, ~A["lat"], ~B["lat"], "mid", p75)
        m["verdict"] = branch_verdict(m["ratio"], m["ci"])
        print(f"    {m['verdict']}")
        res[f"p75_vs_{bname[:3]}"] = dict(engaged=e, manual=m)

    # ---- the clip / rail check, pre-declared revert trigger
    print("\n" + "=" * 100)
    print(" CLIP CHECK (pre-declared REVERT TRIGGER) -- a railed lane is sign(gp-0x6c2c)×511,")
    print(" the V80 Coulomb-relay mechanism, 'the worst grinding ever'.")
    print("=" * 100)
    clip = {}
    for tag, cnt, lat in (("r7d (V94)", n.astype(float), A["lat"]),
                          ("r77 (V90)", B77["mid"], B77["lat"]),
                          ("r78 (V91)", B78["mid"], B78["lat"])):
        d = dict(max_counts=float(cnt.max()), frac_ge_500=float((cnt >= 500).mean()),
                 frac_ge_400=float((cnt >= 400).mean()),
                 eng_max=float(cnt[lat].max()) if lat.any() else float("nan"),
                 man_max=float(cnt[~lat].max()) if (~lat).any() else float("nan"))
        clip[tag] = d
        print(f"    {tag:<12} max |b26| {d['max_counts']:>7.1f} of the ±511 clamp "
              f"({100*d['max_counts']/511:>5.1f} %)   ≥400 duty {d['frac_ge_400']:.6f}   "
              f"≥500 duty {d['frac_ge_500']:.6f}   eng max {d['eng_max']:>6.1f}  "
              f"man max {d['man_max']:>6.1f}")
    res["clip"] = clip

    # ---- the input-side caveat, quantified rather than asserted
    print("\n" + "=" * 100)
    print(" 🛑 THE INPUT IS NOT INDEPENDENT OF THE SYMPTOM -- quantified, not hand-waved")
    print("=" * 100)
    print("    gp-0x6b26 = −K · gp-0x6c2c (motor ACCELERATION).  A ratio above 0.25 is consistent")
    print("    with (K × 0.25) × (acceleration × m).  The implied m for each observed ratio:")
    for k in [x for x in res if x.startswith("mid_vs_")]:
        for a in ("engaged", "manual"):
            r = res[k][a]["ratio"]
            if np.isfinite(r):
                exp = V94_EXPECT[a]
                print(f"      {k:<16} {a:<8} ratio {r:.3f}  ⇒ implied input multiplier "
                      f"m = {r/exp:.2f}×  (if the ×{exp} gain IS in force)")
                res[k][a]["implied_input_multiplier"] = float(r / exp)

    (CACHE / "_scratch/cache/r7d" / "v94_dose.json").write_text(json.dumps(res, indent=1, default=float))
    print("\n  wrote analysis-2020accord/_scratch/cache/r7d/v94_dose.json")


if __name__ == "__main__":
    main()
