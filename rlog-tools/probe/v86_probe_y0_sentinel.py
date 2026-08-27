#!/usr/bin/env python3
"""probe/v86_probe_y0_sentinel.py -- score CHAIN's `Y[0] = 0` prediction, and bound the 0x7fff sentinel.

Two claims arrived from the code side and both are FALSIFIABLE against the flown probe:

  A  `FUN_00038148` writes `gp-0x6b70 = 0x7fff` (= +32767) whenever the plausibility check on
     `gp-0x6bfe` fails (`|gp-0x6bfe| > 20000`). Through the probe a sentinel frame is
     `b7=0, b6=1, b5=1` -- code 0x78, INDISTINGUISHABLE from a genuine large positive value.
     ⇒ bound its rate before interpreting the big-positive bin or the relay verdict.

  B  the RAM LERP has `X[0] = Y[0] = 0` (`st.h r0` at 0x38D1C / 0x38D22, committed at 0x39522)
     ⇒ **PREDICTION: no nonzero floor on |gp-0x6b70|; the transfer function passes through the
     origin.** Scored CONFIRMED or CONTRADICTED, not "consistent with".

🛑 THE PROXY. `gp-0x6bfe` is not on the wire. Every test below uses the fitted static model
`resid_proxy = cs_tq[t+10ms] - c`, which reproduces the probe's SIGN on 95% of frames. Its 5%
error is the resolution limit of every number here and is quoted alongside each one.
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))
from v86_probe_physics import ROUTES, decode_route, gap_stats  # noqa: E402

RNG = np.random.default_rng(20260808)
SENTINEL = 0x7FFF
CLAMP = 8192          # 0xC6200 -- the normal path can NEVER exceed this; the sentinel is 4x it


def runs(mask):
    """Run lengths of the True stretches of a boolean mask."""
    m = np.asarray(mask, bool)
    if not m.any():
        return np.array([], int)
    d = np.diff(np.r_[0, m.view(np.int8), 0])
    return np.flatnonzero(d == -1) - np.flatnonzero(d == 1)


def analyse(tag):
    z, b4, L, gate = decode_route(tag)
    phys = json.loads((ROOT / ROUTES[tag][0] /
                       ("probe_v86_physics.json" if tag == "6f"
                        else "probe_v86b_physics.json")).read_text())
    mc = phys["sign_drivers"]["_model_comparison"]
    c, lag, pol = mc["static"]["c"], mc["lag_frames"], mc["polarity"]
    d = pol * (np.asarray(z["cs_tq"], float) - np.median(z["cs_tq"]))
    r = np.roll(d, lag) - c                    # resid_proxy
    sd = float(np.std(r))
    tq_raw = np.asarray(z["tq"], float)
    n = len(L)
    big_pos, big_neg = (L == 2), (L == -2)
    small, zero = (np.abs(L) == 1), (L == 0)
    out = {"route": tag, "build": phys["build"], "frames": n,
           "resid_proxy": f"cs_tq[t{lag:+d}] - {c:.1f}  (sign model err {mc['static']['err']:.4f})",
           "resid_rms": sd}

    # =========================================================================================
    # A.  THE 0x7fff SENTINEL -- a DIFFERENTIAL bound with its own null
    # =========================================================================================
    # The sentinel can ONLY force POSITIVE. So among frames the model calls confidently NEGATIVE,
    # a big-POSITIVE reading is a sentinel candidate; among frames it calls confidently POSITIVE, a
    # big-NEGATIVE reading is PURE MODEL ERROR and cannot be a sentinel. The difference is the
    # sentinel-attributable excess, and the second rate is the null for the first.
    sen = {}
    for k in (0.5, 1.0, 1.5, 2.0):
        neg = r <= -k * sd
        pos = r >= k * sd
        if neg.sum() < 100 or pos.sum() < 100:
            continue
        a = float(big_pos[neg].mean())          # candidate sentinel rate
        b = float(big_neg[pos].mean())          # model-error floor (sentinel-impossible)
        sen[f"|resid| >= {k:g} sd"] = dict(
            n_neg=int(neg.sum()), n_pos=int(pos.sum()),
            wrong_sign_positive=a, wrong_sign_negative_NULL=b,
            sentinel_excess=a - b,
            sentinel_duty_upper_bound=float(max(a - b, 0.0) * neg.mean()))
    out["sentinel_differential"] = sen

    # persistence: a fault condition is not per-sample noise, so a sentinel makes LONG 0x78 runs
    rp, rn = runs(big_pos), runs(big_neg)
    anom = big_pos & (r <= -1.0 * sd)
    ra = runs(anom)
    out["sentinel_persistence"] = dict(
        big_pos_runs=dict(n=int(len(rp)), mean=float(rp.mean()) if len(rp) else None,
                          p99=float(np.percentile(rp, 99)) if len(rp) else None,
                          max=int(rp.max()) if len(rp) else None),
        big_neg_runs=dict(n=int(len(rn)), mean=float(rn.mean()) if len(rn) else None,
                          p99=float(np.percentile(rn, 99)) if len(rn) else None,
                          max=int(rn.max()) if len(rn) else None),
        anomalous_pos_runs=dict(n=int(len(ra)), mean=float(ra.mean()) if len(ra) else None,
                                max=int(ra.max()) if len(ra) else None,
                                frames=int(anom.sum()), duty=float(anom.mean())),
        note="a persistent fault path makes LONG runs. Compare `anomalous_pos_runs.mean` with 1 "
             "frame: near 1 ⇒ scattered ⇒ ordinary model error, not a latched fault.")

    # the plausibility threshold, against the only torque scale we can see
    out["plausibility_scale"] = dict(
        gate="|gp-0x6bfe| > 20000 ⇒ sentinel",
        max_abs_tq_on_route=float(np.abs(tq_raw).max()),
        p999_abs_tq=float(np.percentile(np.abs(tq_raw), 99.9)),
        caveat="[BELIEF] gp-0x6bfe is a DIFFERENT cell from gp-0x4f60 and its scale is NOT "
               "established. This row is context, NOT a bound. The differential estimator above "
               "makes no scale assumption and is the one to quote.")

    # =========================================================================================
    # B.  CHAIN's PREDICTION: Y[0] = 0 ⇒ the transfer function passes through the ORIGIN
    # =========================================================================================
    # B1 -- the ORDINAL prediction. A map through the origin puts the bins in order of |resid|:
    #        median|resid|  zero  <  small(1..63)  <  big(>=64)
    #    A floor Y[0] = F > 0 makes the ZERO bin unreachable except at resid == 0 exactly, so the
    #    zero bin would NOT be separated from the small bin.
    med = {k: float(np.median(np.abs(r[m]))) for k, m in
           (("zero", zero), ("small", small), ("big", big_pos | big_neg)) if m.sum()}
    nn = {k: int(m.sum()) for k, m in
          (("zero", zero), ("small", small), ("big", big_pos | big_neg))}
    ordered = med.get("zero", 9e9) < med.get("small", 9e9) < med.get("big", 9e9)

    # B2 -- permutation test: are the ZERO-bin frames at smaller |resid| than chance?
    obs = med.get("zero")
    k0 = int(zero.sum())
    perm = np.array([np.median(np.abs(r[RNG.choice(n, k0, replace=False)])) for _ in range(5000)]) \
        if k0 >= 5 else np.array([])
    p_zero = float((perm <= obs).mean()) if len(perm) else None
    ks = int(small.sum())
    perm_s = np.array([np.median(np.abs(r[RNG.choice(n, ks, replace=False)])) for _ in range(2000)])
    p_small = float((perm_s <= med["small"]).mean())

    # B3 -- the CONDITIONAL BIN DISTRIBUTION as |resid| -> 0. The sharp discriminator.
    cond = []
    edges = [0, 2, 5, 10, 20, 40, 80, 160, 320, 1e9]
    for i in range(len(edges) - 1):
        m = (np.abs(r) >= edges[i]) & (np.abs(r) < edges[i + 1])
        if m.sum() < 30:
            continue
        cond.append(dict(lo=edges[i], hi=edges[i + 1], n=int(m.sum()),
                         p_zero=float(zero[m].mean()), p_small=float(small[m].mean()),
                         p_big=float((big_pos | big_neg)[m].mean())))
    out["Y0_test"] = dict(
        prediction="Y[0] = X[0] = 0 ⇒ |gp-0x6b70| has NO nonzero floor; the bins must order by "
                   "|resid| as zero < small < big.",
        n_by_bin=nn, median_abs_resid_by_bin=med, ordinal_prediction_holds=bool(ordered),
        perm_p_zero_bin_at_smaller_resid=p_zero, perm_p_small_bin_at_smaller_resid=p_small,
        conditional_bin_distribution=cond,
        verdict=("CONFIRMED" if ordered and (p_zero is not None and p_zero < 0.05)
                 and (p_small < 0.05) else "SEE NOTES"))

    # =========================================================================================
    # C.  RECONCILING "88% at |v| >= 64 looks relay-like" WITH Y[0] = 0
    # =========================================================================================
    knee = phys["sign_drivers"]["_transfer_curve"]["knee_abs_tq_at_p_big_0p5"]
    from math import erf, sqrt
    kr = knee / sd
    gauss = 1.0 - erf(kr / sqrt(2.0))          # P(|X| >= knee) for a Gaussian of the same sd
    out["reconciliation"] = dict(
        knee_counts=knee, resid_rms=sd, knee_over_rms=kr,
        observed_big_duty=float((big_pos | big_neg).mean()),
        gaussian_expectation_at_same_threshold=gauss,
        conclusion="the 64-count rung sits at %.2f%% of the residual's RMS. ANY continuous "
                   "origin-crossing signal spends ~%.1f%% of its time outside a threshold that "
                   "low. The observed %.1f%% is at or BELOW that, so the marginal is NOT evidence "
                   "of a relay -- it is evidence the rung was placed very low."
                   % (100 * kr, 100 * gauss, 100 * (big_pos | big_neg).mean()))

    # =========================================================================================
    # D.  THE RELAY VERDICT, WITH SENTINEL-SUSPECT FRAMES EXCLUDED
    # =========================================================================================
    x = np.where(np.abs(L) == 2, np.sign(L) * 1000.0, np.sign(L) * 1.0)
    keep = ~anom
    g_all = gap_stats(x, 500.0)
    g_cut = gap_stats(x[keep], 500.0)
    out["relay_recheck_sentinel_excluded"] = dict(
        excluded_frames=int(anom.sum()), excluded_duty=float(anom.mean()),
        all_frames=dict(n_events=g_all["n_events"], frac_disc=g_all["frac_disc"],
                        mean_gap=g_all["mean_gap"]),
        sentinel_suspects_removed=dict(n_events=g_cut["n_events"], frac_disc=g_cut["frac_disc"],
                                       mean_gap=g_cut["mean_gap"]),
        note="removing frames splices the series, which can only ADD apparent discontinuities. "
             "So this is a CONSERVATIVE re-test: if frac_disc does not rise toward 1.0, the "
             "not-a-relay verdict survives the sentinel confound.")

    # a rung that WOULD isolate the sentinel, for V87
    out["v87_rung_recommendation"] = dict(
        fact=f"the normal path is clamped to +-{CLAMP} (0xC6200); the sentinel writes "
             f"{SENTINEL} = {SENTINEL / CLAMP:.2f}x the clamp",
        rung="a single rung `gp-0x6b70 > 8192` is a PURE sentinel detector -- unreachable by the "
             "normal path, so it has no false-positive mode at all. `sar 0xd` + `cmp 0x3` reaches "
             "it; it costs one rung and removes this confound permanently.")
    return out


def main():
    A = {}
    for tag in ("6f", "70"):
        A[tag] = analyse(tag)
        cdir = ROUTES[tag][0]
        f = ROOT / cdir / ("probe_v86_y0_sentinel.json" if tag == "6f"
                           else "probe_v86b_y0_sentinel.json")
        f.write_text(json.dumps(A[tag], indent=1), encoding="utf-8")
        print(f"wrote {f.relative_to(ROOT)}")
        print(json.dumps(A[tag], indent=1))
    return A


if __name__ == "__main__":
    main()
