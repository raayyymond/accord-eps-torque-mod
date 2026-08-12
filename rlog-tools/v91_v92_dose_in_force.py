#!/usr/bin/env python3
r"""THE DOSE-IN-FORCE TEST for V91 (route 78) and V92 (route 79) -- SCORING-2026-08-11 §10.1,
run EXACTLY as pre-registered, BEFORE any band scoring.

🛑 WHY THIS RUNS FIRST.  V64's null was on the GATE, not the hypothesis, and it was read as a result
for weeks.  If the ratio's CI contains 1.00, EVERY band result on these routes is UNINTERPRETABLE.

===================================================================================================
THE TWO ROUTES CARRY DIFFERENT INSTRUMENTS FOR THE SAME CELL -- this is the whole subtlety
===================================================================================================
ROUTE 78 (V91): CAN 427 = clamp(|gp-0x6b26| * 5 >> 3, 0, 0x3FF)   <- SAME as route 77 (V90).
    ⇒ a DIRECT, continuous, 50 Hz comparison of the dosed cell against its own undosed baseline.
    |gp-0x6b26| = wire * 8/5.  Quantised at 1.6 counts/LSB.

ROUTE 79 (V92): CAN 427 was REPOINTED to gp-0x6bbe.  `gp-0x6b26` survives on the wire ONLY as the
    1-bit rung `byte7 b7 = |gp-0x6b26| >= 15` at 100 Hz.
    ⇒ the dose test becomes a DUTY comparison, and the prediction is derived by pushing route 77's
    own measured |gp-0x6b26| samples through the dose and the SAME threshold:
        predicted duty = P( 1.5 * |b26_77| >= 15 )  ==  P( |b26_77| >= 10 )
    🛑 T=15 lands between wire LSBs (15/1.6 = 9.375), so the threshold is applied to COUNTS
       reconstructed from the wire, and the quantisation is reported, not hidden.

===================================================================================================
THE THREE PRE-DECLARED ARMS (§10.1) -- all stratified, none route-averaged
===================================================================================================
1. ENGAGED, CELL-STRATIFIED (speed bin x wheel-rate bin -- the same partition the band estimator
   uses).  Median |gp-0x6b26| ratio V91 / route 77 must equal 1.50, tol +-15 % => [1.275, 1.725],
   CI excluding 1.00.
   🛑 A raw route-average percentile comparison is NOT acceptable: |gp-0x6b26| runs p50 2.3 at
      <1 °/s against 19.9 at 13-50 °/s, so an unmatched comparison confounds dose with drive.
2. MANUAL -- the built-in negative control.  The ratio MUST be 1.00.  The dose is on the ENGAGED
   record (mode 26/27) only; mode 24 is MANUAL and was NOT edited.  If manual scales too, the wrong
   record was written and the build must be pulled regardless of what the bands say.
3. PER SPEED BIN.  `0xCBE74` is a speed-indexed LERP, so a whole-row xN must give xN at EVERY
   speed.  A ratio that varies with speed means only some breakpoints were edited.

PRE-DECLARED READINGS (verbatim from §10.1):
    ratio ~1.50 engaged, ~1.00 manual, flat across speed  => DOSE IN FORCE.  Bands interpretable.
    ratio CI CONTAINS 1.00                                => DOSE NOT IN FORCE.  🛑 Bands are then
                                                             uninterpretable and must NOT be
                                                             reported as a falsification.
    ratio strictly between 1.00 and 1.50, or speed-dependent => PARTIAL DOSE.  Report per bin.
    ratio ~1.50 in BOTH arms                              => WRONG RECORD.  Pull the build.

THE CLIP CHECK, also pre-declared as a REVERT TRIGGER IN ITS OWN RIGHT:
    predicted clamp duty exactly 0.000000, and `wire` NEVER reaching 319 (the wire value of a lane
    railed at +-511).  Any repeated wire == 319 means the lane is spending time at
    sign(gp-0x6c2c) x 511 -- a COULOMB RELAY, the V80 mechanism, "the worst grinding ever".

🛑 BOOTSTRAP OVER EPISODES, NOT WINDOWS (standing kit rule).  Window/frame bootstraps manufacture
   significance.  The CI here resamples ENGAGEMENT EPISODES (and, for manual, contiguous manual
   runs) with replacement, recomputing the whole stratified estimator each draw.

Usage:  python v91_v92_dose_in_force.py
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CACHE = ROOT / "analysis-2020accord"

RNG = np.random.default_rng(20260811)
NBOOT = 4000

SPEED_BINS = [(0.0, 5.0), (5.0, 20.0), (20.0, 50.0), (50.0, 80.0), (80.0, 1e9)]
RATE_BINS = [(0.0, 1.0), (1.0, 3.0), (3.0, 6.0), (6.0, 13.0), (13.0, 25.0), (25.0, 50.0),
             (50.0, 1e9)]
MIN_CELL = 40                      # frames per cell per route, both routes, to use the cell

WIRE_TO_COUNTS = 8.0 / 5.0         # 427 sar-3 packing:  counts = wire * 8/5
RAILED_WIRE = 319                  # (511 * 5) >> 3
DOSE = 1.5
T_RUNG = 15.0                      # byte7 b7 threshold, in COUNTS of gp-0x6b26


# ======================================================================================
def load(route, stem):
    z = np.load(CACHE / f"_cache_r{route}" / f"{stem}.npz", allow_pickle=True)
    rt = np.asarray(z["t"], float)
    v = np.abs(np.asarray(z["cs_v"], float))
    lat = np.asarray(z["cc_lat"], float) > 0.5
    ang = np.asarray(z["cs_ang"], float)
    dt = np.gradient(rt)
    dt[dt <= 0] = np.median(dt[dt > 0]) if (dt > 0).any() else 0.01
    rate = np.abs(np.gradient(ang) / dt)
    return z, rt, v, lat, rate


def onto(t_target, rt, arr, kind="lin"):
    if kind == "bool":
        return np.interp(t_target, rt, arr.astype(float)) > 0.5
    return np.interp(t_target, rt, arr)


def episodes_of(mask):
    """Contiguous-run id for each True frame; -1 elsewhere.  The bootstrap unit."""
    eid = np.full(len(mask), -1, int)
    k, run = 0, False
    for i, x in enumerate(mask):
        if x:
            if not run:
                k += 1
                run = True
            eid[i] = k - 1
        else:
            run = False
    return eid, k


def wire_arrays(route, stem):
    """427 samples with engagement / speed / rate interpolated onto the 50 Hz 0x1AB grid."""
    z, rt, v, lat, rate = load(route, stem)
    t = np.asarray(z["ab_t1ab"], float)
    wire = np.asarray(z["ab_mt"], int)
    return dict(t=t, wire=wire, counts=wire * WIRE_TO_COUNTS,
                lat=onto(t, rt, lat, "bool"), v=onto(t, rt, v) * 3.6, rate=onto(t, rt, rate))


def rung_arrays(route, stem):
    """byte7 b7 (|gp-0x6b26| >= 15) on the 100 Hz 0x14A grid.  V92 only."""
    z, rt, v, lat, rate = load(route, stem)
    t = np.asarray(z["raw14_t"], float)
    b7 = (np.asarray(z["raw14_b7"], int) & 0x80) != 0
    return dict(t=t, hit=b7, lat=onto(t, rt, lat, "bool"), v=onto(t, rt, v) * 3.6,
                rate=onto(t, rt, rate))


# ======================================================================================
def cell_id(v, rate):
    sb = np.full(len(v), -1, int)
    for i, (lo, hi) in enumerate(SPEED_BINS):
        sb[(v >= lo) & (v < hi)] = i
    rb = np.full(len(rate), -1, int)
    for i, (lo, hi) in enumerate(RATE_BINS):
        rb[(rate >= lo) & (rate < hi)] = i
    ok = (sb >= 0) & (rb >= 0)
    cid = np.where(ok, sb * len(RATE_BINS) + rb, -1)
    return cid


def stratified_ratio(a_vals, a_cid, b_vals, b_cid, stat=np.median):
    """Common-cell stratified ratio: per-cell stat ratio, weighted by the harmonic-ish min count.

    🛑 Only cells populated on BOTH routes contribute -- that is what makes it a matched
    comparison rather than a confound between two different drives.
    """
    cells, num, den, wts, rows = [], [], [], [], []
    for c in np.unique(a_cid[a_cid >= 0]):
        sa, sb = a_vals[a_cid == c], b_vals[b_cid == c]
        if len(sa) < MIN_CELL or len(sb) < MIN_CELL:
            continue
        ma, mb = stat(sa), stat(sb)
        if mb <= 0:
            continue
        w = float(min(len(sa), len(sb)))
        cells.append(int(c)); num.append(ma); den.append(mb); wts.append(w)
        rows.append((int(c), len(sa), len(sb), float(ma), float(mb), float(ma / mb)))
    if not cells:
        return float("nan"), []
    w = np.array(wts, float)
    r = np.array(num, float) / np.array(den, float)
    return float(np.exp(np.sum(w * np.log(r)) / w.sum())), rows      # weighted GEOMETRIC mean


def boot_ratio(a_vals, a_cid, a_ep, b_vals, b_cid, b_ep, stat=np.median, nboot=NBOOT):
    ua, ub = np.unique(a_ep), np.unique(b_ep)
    out = np.full(nboot, np.nan)
    ia = {e: np.flatnonzero(a_ep == e) for e in ua}
    ib = {e: np.flatnonzero(b_ep == e) for e in ub}
    for k in range(nboot):
        pa = np.concatenate([ia[e] for e in RNG.choice(ua, len(ua), replace=True)])
        pb = np.concatenate([ib[e] for e in RNG.choice(ub, len(ub), replace=True)])
        r, _ = stratified_ratio(a_vals[pa], a_cid[pa], b_vals[pb], b_cid[pb], stat)
        out[k] = r
    out = out[np.isfinite(out)]
    return (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)),
            int(len(out)))


def cellname(c):
    s, r = divmod(c, len(RATE_BINS))
    slo, shi = SPEED_BINS[s]
    rlo, rhi = RATE_BINS[r]
    return (f"v {slo:.0f}-{'+' if shi > 1e8 else f'{shi:.0f}'} km/h  "
            f"rate {rlo:.0f}-{'+' if rhi > 1e8 else f'{rhi:.0f}'} °/s")


# ======================================================================================
def arm(tag, A, B, sel_a, sel_b, stat=np.median):
    """One pre-declared arm.  A = test route, B = baseline route 77."""
    av, ac = A["counts"][sel_a], cell_id(A["v"], A["rate"])[sel_a]
    bv, bc = B["counts"][sel_b], cell_id(B["v"], B["rate"])[sel_b]
    aep, _ = episodes_of(sel_a)
    bep, _ = episodes_of(sel_b)
    aep, bep = aep[sel_a], bep[sel_b]
    r, rows = stratified_ratio(av, ac, bv, bc, stat)
    lo, hi, nb = boot_ratio(av, ac, aep, bv, bc, bep, stat)
    print(f"\n  --- {tag} ---")
    print(f"    common cells used: {len(rows)}   test frames {sel_a.sum():,}   "
          f"baseline frames {sel_b.sum():,}   episodes {len(np.unique(aep))}/{len(np.unique(bep))}")
    print(f"    {'cell':<42} {'n_test':>7} {'n_r77':>7} {'test':>8} {'r77':>8} {'ratio':>7}")
    for c, na, nb_, ma, mb, rr in sorted(rows, key=lambda x: -x[1])[:16]:
        print(f"    {cellname(c):<42} {na:>7,} {nb_:>7,} {ma:>8.2f} {mb:>8.2f} {rr:>7.3f}")
    print(f"    ⇒ STRATIFIED RATIO {r:.4f}   95 % CI [{lo:.4f}, {hi:.4f}]   ({nb} boot draws)")
    return dict(ratio=r, ci=[lo, hi], n_cells=len(rows), n_test=int(sel_a.sum()),
                n_base=int(sel_b.sum()),
                cells=[dict(cell=c, name=cellname(c), n_test=na, n_base=nb_, test=ma,
                            base=mb, ratio=rr) for c, na, nb_, ma, mb, rr in rows])


def verdict(name, r, ci, expect):
    if not np.isfinite(r):
        return "🛑 NO COMMON CELLS -- test could not run"
    contains1 = ci[0] <= 1.0 <= ci[1]
    if expect == 1.5:
        if contains1:
            return ("🛑🛑 DOSE NOT IN FORCE -- the CI CONTAINS 1.00.  Every band result on this "
                    "route is UNINTERPRETABLE and must NOT be reported as a falsification.")
        if 1.275 <= r <= 1.725:
            return "✅ DOSE IN FORCE (within the pre-registered ±15 % window [1.275, 1.725])"
        if r < 1.275:
            return (f"⚠ PARTIAL DOSE -- ratio {r:.3f} is below the pre-registered window but its "
                    f"CI excludes 1.00.  Report the effective multiplier per bin; do not average.")
        return f"⚠ OVER-DOSE -- ratio {r:.3f} above [1.275, 1.725]"
    if contains1:
        return "✅ NEGATIVE CONTROL HOLDS (CI contains 1.00 -- the manual record was NOT edited)"
    return ("🛑🛑 NEGATIVE CONTROL FAILED -- the MANUAL arm scales.  Mode 24 is MANUAL; if it moved, "
            "the WRONG RECORD was written.  PULL THE BUILD.")


# ======================================================================================
def clip_check(tag, A):
    w = A["wire"]
    lat = A["lat"]
    out = dict(route=tag, n=int(len(w)), max_wire=int(w.max()),
               max_counts=float(w.max() * WIRE_TO_COUNTS),
               n_at_rail=int((w >= RAILED_WIRE).sum()),
               frac_at_rail=float((w >= RAILED_WIRE).mean()))
    print(f"\n  --- CLIP CHECK, {tag} (pre-declared REVERT TRIGGER) ---")
    print(f"    max wire {out['max_wire']} of 1023  =  {out['max_counts']:.1f} counts of the "
          f"±511 clamp   ({100*out['max_counts']/511:.1f} % of the rail)")
    print(f"    frames at the railed wire value {RAILED_WIRE}: {out['n_at_rail']:,} "
          f"({100*out['frac_at_rail']:.6f} %)")
    strata = {}
    for lo, hi in ((5.0, 20.0), (20.0, 50.0), (50.0, 1e9)):
        for rlo, rhi in ((13.0, 50.0), (1.0, 13.0)):
            s = lat & (A["v"] >= lo) & (A["v"] < hi) & (A["rate"] >= rlo) & (A["rate"] < rhi)
            if s.sum() < 20:
                continue
            strata[f"v{lo:.0f}-{hi if hi < 1e8 else 999:.0f} r{rlo:.0f}-{rhi:.0f}"] = dict(
                n=int(s.sum()), max_wire=int(w[s].max()),
                frac_at_rail=float((w[s] >= RAILED_WIRE).mean()))
    out["binding_strata"] = strata
    for k, d in strata.items():
        print(f"      {k:<22} n={d['n']:>6,}  max wire {d['max_wire']:>4}  "
              f"rail duty {d['frac_at_rail']:.6f}")
    out["verdict"] = ("✅ NO CLIPPING -- the lane is an honest measurement, not a Coulomb relay"
                      if out["n_at_rail"] == 0 else
                      "🛑🛑 THE LANE IS RAILING -- sign(gp-0x6c2c)×511 is the V80 relay mechanism. "
                      "REVERT TRIGGER.")
    print(f"    {out['verdict']}")
    return out


# ======================================================================================
def main():
    print("=" * 99)
    print(" DOSE-IN-FORCE, SCORING-2026-08-11 §10.1 -- run BEFORE any band scoring")
    print("=" * 99)
    R77 = wire_arrays("77", "r77")
    R78 = wire_arrays("78", "r78")
    res = {"baseline": "route 77 (V90, undosed)", "min_cell": MIN_CELL,
           "speed_bins": SPEED_BINS, "rate_bins": RATE_BINS, "nboot": NBOOT}

    print("\n" + "=" * 99)
    print(" ROUTE 78 == V91.  427 still carries |gp-0x6b26| ⇒ DIRECT continuous test.")
    print("=" * 99)
    res["v91_engaged"] = arm("ARM 1 · ENGAGED, cell-stratified median |gp-0x6b26|  (expect 1.50)",
                             R78, R77, R78["lat"], R77["lat"])
    res["v91_engaged"]["verdict"] = verdict("engaged", res["v91_engaged"]["ratio"],
                                            res["v91_engaged"]["ci"], 1.5)
    print(f"    {res['v91_engaged']['verdict']}")

    res["v91_manual"] = arm("ARM 2 · MANUAL negative control  (expect 1.00 -- mode 24 NOT edited)",
                            R78, R77, ~R78["lat"], ~R77["lat"])
    res["v91_manual"]["verdict"] = verdict("manual", res["v91_manual"]["ratio"],
                                           res["v91_manual"]["ci"], 1.0)
    print(f"    {res['v91_manual']['verdict']}")

    # ---- ARM 3: per speed bin, engaged
    print("\n  --- ARM 3 · PER SPEED BIN, engaged (0xCBE74 is a speed-indexed LERP: "
          "a whole-row ×N must give ×N at EVERY speed) ---")
    per = {}
    for lo, hi in SPEED_BINS:
        sa = R78["lat"] & (R78["v"] >= lo) & (R78["v"] < hi)
        sb = R77["lat"] & (R77["v"] >= lo) & (R77["v"] < hi)
        if sa.sum() < 200 or sb.sum() < 200:
            print(f"    v {lo:.0f}-{hi if hi < 1e8 else 999:.0f}: n={sa.sum():,}/{sb.sum():,} "
                  f"-- too few, skipped")
            continue
        av, ac = R78["counts"][sa], cell_id(R78["v"], R78["rate"])[sa]
        bv, bc = R77["counts"][sb], cell_id(R77["v"], R77["rate"])[sb]
        r, rows = stratified_ratio(av, ac, bv, bc)
        per[f"{lo:.0f}-{hi if hi < 1e8 else 999:.0f}"] = dict(
            ratio=r, n_test=int(sa.sum()), n_base=int(sb.sum()), n_cells=len(rows),
            p50_test=float(np.median(av)), p50_base=float(np.median(bv)),
            p90_test=float(np.percentile(av, 90)), p90_base=float(np.percentile(bv, 90)))
        d = per[f"{lo:.0f}-{hi if hi < 1e8 else 999:.0f}"]
        print(f"    v {lo:>3.0f}-{hi if hi < 1e8 else 999:>3.0f} km/h  n {sa.sum():>6,}/"
              f"{sb.sum():>6,}  cells {len(rows):>2}  p50 {d['p50_test']:>6.2f} vs "
              f"{d['p50_base']:>6.2f}   p90 {d['p90_test']:>6.2f} vs {d['p90_base']:>6.2f}"
              f"   RATIO {r:.3f}" if np.isfinite(r) else
              f"    v {lo:.0f}-{hi:.0f}: no common cells")
    res["v91_per_speed"] = per

    res["v91_clip"] = clip_check("route 78 (V91)", R78)
    res["v90_clip"] = clip_check("route 77 (V90, baseline)", R77)

    # ---- raw percentile table, for the record (NOT the test)
    print("\n  --- RAW ENGAGED PERCENTILES (context only -- NOT the pre-registered test) ---")
    tab = {}
    for tag, A in (("route 77 (V90)", R77), ("route 78 (V91)", R78)):
        c = A["counts"][A["lat"]]
        tab[tag] = {f"p{p}": float(np.percentile(c, p)) for p in (50, 75, 90, 95, 99, 99.9)}
        tab[tag]["max"] = float(c.max())
        tab[tag]["n"] = int(len(c))
        print(f"    {tag:<16} n={len(c):>6,}  " +
              "  ".join(f"p{p}={np.percentile(c, p):>6.1f}" for p in (50, 75, 90, 95, 99)) +
              f"  max={c.max():.1f}")
    res["raw_engaged_percentiles"] = tab

    # ==================================================================================
    print("\n" + "=" * 99)
    print(" ROUTE 79 == V92.  427 was REPOINTED ⇒ the dose survives only as byte7 b7 (a DUTY).")
    print("=" * 99)
    R79 = rung_arrays("79", "r79")
    # predicted duty: push route 77's OWN |b26| samples through the dose and the same threshold
    c77 = R77["counts"]
    lat77 = R77["lat"]
    pred_all = float(np.mean(DOSE * c77 >= T_RUNG))
    pred_eng = float(np.mean(DOSE * c77[lat77] >= T_RUNG))
    undosed_all = float(np.mean(c77 >= T_RUNG))
    undosed_eng = float(np.mean(c77[lat77] >= T_RUNG))
    print(f"\n  Route 77's own |gp-0x6b26| pushed through the SAME threshold T={T_RUNG:.0f} counts:")
    print(f"    undosed  duty  all {undosed_all:.4f}   engaged {undosed_eng:.4f}")
    print(f"    ×1.5     duty  all {pred_all:.4f}   engaged {pred_eng:.4f}   <-- THE PREDICTION")
    print(f"    observed on r79  all {R79['hit'].mean():.4f}   "
          f"engaged {R79['hit'][R79['lat']].mean():.4f}")
    print("  ⚠ Route-average duty confounds dose with drive composition.  The cell-stratified "
          "version below is the test.")

    # cell-stratified duty comparison: per cell, observed r79 duty vs predicted-from-r77 duty
    a_cid = cell_id(R79["v"], R79["rate"])
    b_cid = cell_id(R77["v"], R77["rate"])
    rows, wts, lr = [], [], []
    for c in np.unique(a_cid[a_cid >= 0]):
        sa = R79["hit"][(a_cid == c) & R79["lat"]]
        sb = c77[(b_cid == c) & lat77]
        if len(sa) < MIN_CELL or len(sb) < MIN_CELL:
            continue
        obs = float(sa.mean())
        pred = float(np.mean(DOSE * sb >= T_RUNG))
        und = float(np.mean(sb >= T_RUNG))
        rows.append((int(c), len(sa), len(sb), obs, pred, und))
        if und > 0 and obs > 0:
            wts.append(float(min(len(sa), len(sb))))
            lr.append(np.log(obs / und))
    print(f"\n  --- CELL-STRATIFIED DUTY, ENGAGED (cells populated on BOTH routes) ---")
    print(f"    {'cell':<42} {'n_r79':>7} {'n_r77':>7} {'obs':>7} {'pred×1.5':>9} {'undosed':>8}")
    for c, na, nb_, obs, pred, und in sorted(rows, key=lambda x: -x[1])[:16]:
        print(f"    {cellname(c):<42} {na:>7,} {nb_:>7,} {obs:>7.3f} {pred:>9.3f} {und:>8.3f}")
    obs_vs_undosed = float(np.exp(np.sum(np.array(wts) * np.array(lr)) / np.sum(wts))) \
        if wts else float("nan")
    print(f"    ⇒ stratified duty ratio  observed / UNDOSED-baseline = {obs_vs_undosed:.4f}")
    print(f"      (a duty is a nonlinear function of the dose, so this is NOT expected to be 1.50; "
          f"the pre-registered\n       comparison is observed-vs-PREDICTED, cell by cell, above.)")
    res["v92_rung_duty"] = dict(
        predicted_all=pred_all, predicted_engaged=pred_eng,
        undosed_all=undosed_all, undosed_engaged=undosed_eng,
        observed_all=float(R79["hit"].mean()),
        observed_engaged=float(R79["hit"][R79["lat"]].mean()),
        stratified_obs_over_undosed=obs_vs_undosed,
        cells=[dict(cell=c, name=cellname(c), n_r79=na, n_r77=nb_, obs=obs, pred=pred,
                    undosed=und) for c, na, nb_, obs, pred, und in rows])

    (CACHE / "_cache_r78" / "dose_in_force.json").write_text(
        json.dumps(res, indent=1, default=float))
    print("\n  wrote analysis-2020accord/_cache_r78/dose_in_force.json")
    return res


if __name__ == "__main__":
    main()
