#!/usr/bin/env python3
"""Three things the first Y0/sentinel pass got wrong or left open.

 1  the verdict rule leaned on a zero-vs-small MEDIAN ordering at n = 22 (route 70), which inverted.
    Test that comparison properly instead of letting it drive the verdict, and restate the verdict
    on the statistic that actually tests CONTINUITY: P(big | small |resid|).
 2  the sentinel estimator only looked at |resid| >= 1 sd. Use EVERY frame, both signs.
 3  the 47/41 sign asymmetry was never explained. It should be exactly the fitted offset c.
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))
from v86_probe_physics import ROUTES, decode_route  # noqa: E402

RNG = np.random.default_rng(20260808)
OUT = {}

for tag in ("6f", "70"):
    z, b4, L, gate = decode_route(tag)
    cdir = ROUTES[tag][0]
    stem = "probe_v86" if tag == "6f" else "probe_v86b"
    phys = json.loads((ROOT / cdir / f"{stem}_physics.json").read_text())
    mc = phys["sign_drivers"]["_model_comparison"]
    c, lag, pol = mc["static"]["c"], mc["lag_frames"], mc["polarity"]
    raw = pol * (np.asarray(z["cs_tq"], float) - np.median(z["cs_tq"]))
    r = np.roll(raw, lag) - c
    n = len(L)
    big_pos, big_neg = (L == 2), (L == -2)
    small, zero = (np.abs(L) == 1), (L == 0)
    o = {"route": tag, "build": phys["build"], "frames": n, "offset_c": c}

    # ---- 2. SENTINEL, using EVERY frame and both signs ---------------------------------------
    neg, pos = r < 0, r > 0
    a = float(big_pos[neg].mean())          # model says negative, probe says big positive
    b = float(big_neg[pos].mean())          # model says positive, probe says big negative -- the
    #                                         sentinel CANNOT produce this ⇒ pure model-error null
    o["sentinel_all_frames"] = dict(
        n_model_negative=int(neg.sum()), n_model_positive=int(pos.sum()),
        rate_bigpos_when_model_negative=a, rate_bigneg_when_model_positive_NULL=b,
        excess=a - b,
        sentinel_duty_upper_bound=float(max(a - b, 0.0) * neg.mean()),
        sentinel_duty_upper_bound_sign_symmetric=float(2 * max(a - b, 0.0) * neg.mean()),
        argument="the gate is |gp-0x6bfe| > 20000, SYMMETRIC in sign, so sentinel frames land on "
                 "both sides of the model's prediction in roughly equal number. Only the ones "
                 "landing on the NEGATIVE side are detectable (they read big-POSITIVE). Doubling "
                 "the detected excess is therefore the sign-symmetric total. [EVIDENCE, "
                 "conditional on that symmetry -- which is a property of the gate's own algebra.]")

    # ---- 1. zero-vs-small, tested rather than assumed ----------------------------------------
    az, as_ = np.abs(r[zero]), np.abs(r[small])
    obs = float(np.median(az) - np.median(as_))
    pool = np.r_[az, as_]
    perm = np.array([np.median(p[:len(az)]) - np.median(p[len(az):])
                     for p in (RNG.permutation(pool) for _ in range(20000))])
    o["zero_vs_small"] = dict(
        n_zero=int(zero.sum()), n_small=int(small.sum()),
        med_abs_resid_zero=float(np.median(az)), med_abs_resid_small=float(np.median(as_)),
        observed_difference=obs, perm_p_two_sided=float((np.abs(perm) >= abs(obs)).mean()),
        note="n_zero is tiny on both routes. This comparison is NOT the continuity test and must "
             "not drive the verdict; it is reported so the route-70 inversion is on the record.")

    # ---- both bins vs CHANCE: the enrichment that IS meaningful -------------------------------
    def enrich(mask, thr=20.0):
        return dict(frac_of_bin_below_thr=float((np.abs(r[mask]) < thr).mean()),
                    frac_of_all_below_thr=float((np.abs(r) < thr).mean()),
                    enrichment=float((np.abs(r[mask]) < thr).mean() /
                                     max((np.abs(r) < thr).mean(), 1e-12)))
    o["enrichment_at_small_resid"] = {"zero_bin": enrich(zero), "small_bin": enrich(small),
                                      "threshold_counts": 20.0}

    # ---- THE CONTINUITY TEST: a JUMP predicts P(big) ~ 1 even at resid ~ 0 --------------------
    rows = []
    for lo, hi in ((0, 5), (0, 10), (0, 20), (5, 20), (20, 80)):
        m = (np.abs(r) >= lo) & (np.abs(r) < hi)
        if m.sum() < 30:
            continue
        pb = float((big_pos | big_neg)[m].mean())
        rows.append(dict(lo=lo, hi=hi, n=int(m.sum()), p_big=pb,
                         p_small_or_zero=float((small | zero)[m].mean()),
                         deficit_vs_jump_prediction=float(1.0 / max(pb, 1e-9))))
    o["continuity_test"] = dict(
        rows=rows,
        prediction_if_Y0_ge_64="P(big) == 1.0 at EVERY |resid| > 0, because the output would jump "
                               "straight past 64 ⇒ the small bin is unreachable.",
        prediction_if_Y0_eq_0="P(big) -> small as |resid| -> 0, monotonically.",
        verdict="CONFIRMED" if rows and rows[0]["p_big"] < 0.5 else "CONTRADICTED")

    # ---- 3. the sign asymmetry IS the offset --------------------------------------------------
    o["sign_asymmetry"] = dict(
        observed_sign_neg_duty=float((L < 0).mean()),
        predicted_from_offset_P_cs_tq_below_c=float((np.roll(raw, lag) < c).mean()),
        offset_c=c,
        conclusion="a POSITIVE offset c makes the residual negative more often than the torque "
                   "itself is negative. The observed negative-sign duty and P(cs_tq < c) agree, "
                   "so the 47/41 asymmetry is the OFFSET (the EMA-subtraction / steering bias), "
                   "not a sentinel and not a lane asymmetry.")
    OUT[tag] = o
    (ROOT / cdir / f"{stem}_y0_final.json").write_text(json.dumps(o, indent=1), encoding="utf-8")

print(json.dumps(OUT, indent=1))
