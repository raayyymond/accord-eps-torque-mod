#!/usr/bin/env python3
r"""ROBUSTNESS + the CONTROLS THAT DECIDE, for the measured steering-ratio study.

Runs after `studies/steering-ratio/measure_steering_ratio.py`.  What it adds, and why each one exists:

  C1'  ⭐ THE SYNTHETIC NULL -- replaces the useless within-speed-bin shuffle.
       Shuffling `delta` against `theta` destroys the SIGN relation, so every bin median goes to
       ~0 and the "swing" statistic becomes a ratio of two numbers near zero -- its null
       distribution came out [-1.43, +1.49], which cannot reject anything.  The RIGHT null is:
       rebuild `delta` from a CONSTANT-RATIO rack (no notch), inject the MEASURED residual noise,
       and run the identical pipeline.  If the pipeline returns swing = 1.000, the notch is real;
       if it returns ~1.09, the notch is an artefact of binning/noise/offset/atan.
       ⊕ Its twin, the RECOVERY control: rebuild `delta` from the MEASURED curve + the same noise;
       the pipeline must return the measured swing.

  C2'  THE SECANT-vs-LOCAL CONSISTENCY CHECK.  A flat LOCAL ratio beyond 120 deg does NOT imply a
       flat SECANT ratio there -- the secant is a running average from centre out and is still
       relaxing toward the local plateau.  So "secant flatness" is the WRONG positive control.
       This predicts the secant curve FROM the local curve and checks it matches.

  C3'  THE INDEPENDENT-BAND SHAPE CHECK.  5-8 m/s has exposure out to 85 deg -- enough to see the
       notch's ONSET and its upper flank in a speed band that shares no samples with the primary.

  C4'  UNDERSTEER GRADIENT K, fitted (not assumed) by requiring the CENTRE ratio to be
       speed-invariant, and the residual speed-dependence after the fit.

  C5'  SENSITIVITY -- theta0, wheelbase L, smoothing window, steadiness thresholds, bin edges.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import ratio_lib as R  # noqa: E402
import measure_steering_ratio as M  # noqa: E402

OUT = R.ROOT / "analysis-2020accord" / "_scratch/cache/ratio"
CTRL = {}
CENTRE_LO, CENTRE_HI = 3.0, 50.0     # the FLOOR window: bins the measurement shows to be flat


def swing2(th, ratio):
    """swing = median(local ratio over the FLAT FLOOR 3..50 deg) / median(plateau >= 120 deg).
    🛑 Excludes the 0-3 deg bin: at 1-5 m/s a 2 deg wheel angle is ~0.0012 rad/s of yaw, at or
    below the residual IMU bias -- that bin has no power and it is the noisiest in every curve."""
    th = np.asarray(th, float); r = np.asarray(ratio, float)
    c = np.isfinite(th) & (th >= CENTRE_LO) & (th < CENTRE_HI) & np.isfinite(r)
    p = np.isfinite(th) & (th >= M.PLATEAU_LO) & np.isfinite(r)
    if not c.any() or not p.any():
        return np.nan
    return float(np.nanmedian(r[c]) / np.nanmedian(r[p]))


def boot_stat(A, m, th0, yawkey, fn, K=0.0, nboot=1500, seed=3, L=R.L_WB, dlt_override=None):
    th_c = A["s_ang"][m] - th0
    if dlt_override is None:
        dlt = np.arctan(A[yawkey][m] * (L + K * A["v_ref"][m] ** 2) / A["v_ref"][m]) * R.RAD
    else:
        dlt = dlt_override
    blk = A["blk"][m]
    c = M.curve_from(th_c, dlt, M.BINS)
    pt = fn(c[0], c[2])
    rng = np.random.default_rng(seed)
    ub, inv = np.unique(blk, return_inverse=True)
    order = np.argsort(inv, kind="stable")
    bnds = np.searchsorted(inv[order], np.arange(len(ub) + 1))
    by = [order[bnds[i]:bnds[i + 1]] for i in range(len(ub))]
    outs = []
    for _ in range(nboot):
        sel = np.concatenate([by[p] for p in rng.integers(0, len(ub), len(ub))])
        cc = M.curve_from(th_c[sel], dlt[sel], M.BINS)
        s = fn(cc[0], cc[2])
        if np.isfinite(s):
            outs.append(s)
    return {"point": float(pt),
            "ci95": [float(np.percentile(outs, 2.5)), float(np.percentile(outs, 97.5))],
            "n_blocks": int(len(ub)), "n": int(m.sum())}


# ======================================================================================
#  C1'  THE SYNTHETIC NULL and its RECOVERY twin
# ======================================================================================
def synthetic_controls(A, m, th0, nrep=200, seed=5):
    th_c = A["s_ang"][m] - th0
    v = A["v_ref"][m]
    yaw = A["yawA0"][m]
    dlt = np.arctan(yaw * R.L_WB / v) * R.RAD
    ta, sec, loc, _ = M.curve_from(th_c, dlt, M.BINS)

    # the measured delta(theta) curve, as a monotone interpolant through the SIGNED bin medians
    s = np.sign(th_c); s[s == 0] = 1
    knots_t = np.concatenate([[0.0], ta[np.isfinite(ta)]])
    knots_d = np.concatenate([[0.0], (ta / sec)[np.isfinite(ta)]])
    o = np.argsort(knots_t)
    d_meas = np.interp(np.abs(th_c), knots_t[o], knots_d[o]) * s
    resid = dlt - d_meas                      # the estimator's own noise, empirically

    Rflat = float(np.nanmedian(loc[ta >= M.PLATEAU_LO]))
    d_flat = th_c / Rflat                     # a CONSTANT-RATIO rack -- no notch at all

    rng = np.random.default_rng(seed)
    vb = np.digitize(v, [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5])
    null, recov = [], []
    for _ in range(nrep):
        rs = resid.copy()
        for b in np.unique(vb):                # resample the noise WITHIN speed bins
            q = np.flatnonzero(vb == b)
            rs[q] = resid[rng.choice(q, len(q), replace=True)]
        for src, acc in ((d_flat, null), (d_meas, recov)):
            c = M.curve_from(th_c, src + rs, M.BINS)
            x = swing2(c[0], c[2])
            if np.isfinite(x):
                acc.append(x)
    null, recov = np.array(null), np.array(recov)
    real = swing2(ta, loc)
    o = {"real_swing": float(real),
         "NULL_constant_ratio_rack": {"median": float(np.median(null)),
                                      "ci95": [float(np.percentile(null, 2.5)),
                                               float(np.percentile(null, 97.5))],
                                      "truth": 1.0},
         "RECOVERY_measured_rack": {"median": float(np.median(recov)),
                                    "ci95": [float(np.percentile(recov, 2.5)),
                                             float(np.percentile(recov, 97.5))],
                                    "truth": float(real)},
         "n_rep": int(nrep), "plateau_ratio_used": Rflat}
    o["NULL_PASS"] = bool(abs(o["NULL_constant_ratio_rack"]["median"] - 1.0) < 0.02
                          and real > np.percentile(null, 97.5))
    o["RECOVERY_PASS"] = bool(abs(o["RECOVERY_measured_rack"]["median"] - real) < 0.03)
    return o


# ======================================================================================
#  C2'  secant PREDICTED from local -- the right way to read the plateau
# ======================================================================================
def secant_from_local(c):
    th = np.array(c["theta"], float); loc = np.array(c["local"], float)
    sec = np.array(c["secant"], float)
    ok = np.isfinite(th) & np.isfinite(loc) & np.isfinite(sec)
    th, loc, sec = th[ok], loc[ok], sec[ok]
    # integrate 1/local from the first bin outward, anchored on the first bin's measured secant
    d = np.zeros(len(th)); d[0] = th[0] / sec[0]
    for i in range(1, len(th)):
        d[i] = d[i - 1] + (th[i] - th[i - 1]) / (0.5 * (loc[i] + loc[i - 1]))
    pred = th / d
    q = th >= M.PLATEAU_LO
    return {"theta": th.tolist(), "secant_measured": sec.tolist(),
            "secant_predicted_from_local": pred.tolist(),
            "plateau_max_abs_pct_error": float(np.max(np.abs(pred[q] / sec[q] - 1)) * 100),
            "PASS": bool(np.max(np.abs(pred[q] / sec[q] - 1)) < 0.02)}


# ======================================================================================
#  C4'  fit the understeer gradient K by demanding a SPEED-INVARIANT centre ratio
# ======================================================================================
def fit_K(A, th0):
    bands = [(1, 5), (5, 8), (8, 12), (12, 16), (16, 20), (20, 25), (25, 34)]

    def centre_ratio(K, lo, hi):
        m = (R.base_mask(A, vmin=lo, vmax=hi) & R.steady_mask(A)
             & (np.abs(A["s_ang"] - th0) > 4) & (np.abs(A["s_ang"] - th0) < 34))
        if m.sum() < 300:
            return np.nan, 0
        d = np.arctan(A["yawA0"][m] * (R.L_WB + K * A["v_ref"][m] ** 2) / A["v_ref"][m]) * R.RAD
        s = np.sign(A["s_ang"][m] - th0)
        return float(np.median(np.abs(A["s_ang"][m] - th0)) / np.median(d * s)), int(m.sum())

    grid = np.linspace(0.0, 0.006, 121)
    best, bestK = np.inf, 0.0
    for K in grid:
        vals = [centre_ratio(K, lo, hi)[0] for lo, hi in bands]
        vals = np.array([x for x in vals if np.isfinite(x)])
        cv = float(np.std(vals) / np.mean(vals))
        if cv < best:
            best, bestK = cv, float(K)
    rows = []
    for lo, hi in bands:
        r0, n = centre_ratio(0.0, lo, hi)
        r1, _ = centre_ratio(bestK, lo, hi)
        rows.append({"v_lo": lo, "v_hi": hi, "n": n, "centre_ratio_K0": r0,
                     "centre_ratio_Kfit": r1})
    return {"K_fit_s2_per_m": bestK, "residual_CV_after_fit": best,
            "Kv2_over_L_at_5ms": float(bestK * 25 / R.L_WB), "bands": rows}


# ======================================================================================
def main():
    A = M.prep()
    M.qa(A)
    th0 = M.fit_theta0(A, "A")
    prim = R.base_mask(A, vmin=1.0, vmax=5.0) & R.steady_mask(A)

    print("\n=== ⭐ C1' SYNTHETIC NULL + RECOVERY (replaces the shuffle) ===")
    sc = synthetic_controls(A, prim, th0)
    CTRL["synthetic"] = sc
    print(f"  real swing (floor {CENTRE_LO:.0f}-{CENTRE_HI:.0f} deg / plateau) = "
          f"{sc['real_swing']:.4f}")
    n = sc["NULL_constant_ratio_rack"]
    print(f"  NULL     constant-ratio rack + measured noise -> {n['median']:.4f} "
          f"{np.round(n['ci95'], 4).tolist()}   (truth 1.000)   "
          f"{'PASS' if sc['NULL_PASS'] else 'FAIL'}")
    r = sc["RECOVERY_measured_rack"]
    print(f"  RECOVERY measured rack     + measured noise -> {r['median']:.4f} "
          f"{np.round(r['ci95'], 4).tolist()}   (truth {sc['real_swing']:.4f})   "
          f"{'PASS' if sc['RECOVERY_PASS'] else 'FAIL'}")

    print("\n=== C2' SECANT PREDICTED FROM LOCAL (why 'secant flatness' is the wrong control) ===")
    cA = M.curve_boot(A, prim, th0, "yawA0", nboot=400, seed=21)
    sfl = secant_from_local(cA)
    CTRL["secant_from_local"] = sfl
    for t, sm, sp in zip(sfl["theta"], sfl["secant_measured"],
                         sfl["secant_predicted_from_local"]):
        if t >= 60:
            print(f"   |th| {t:7.1f}   secant measured {sm:6.3f}   predicted from local "
                  f"{sp:6.3f}   err {100 * (sp / sm - 1):+5.2f} %")
    print(f"  plateau max |err| = {sfl['plateau_max_abs_pct_error']:.2f} %  ->  "
          f"{'PASS' if sfl['PASS'] else 'FAIL'}")

    print("\n=== C3' INDEPENDENT BAND 5-8 m/s (shares NO samples with the primary) ===")
    m58 = R.base_mask(A, vmin=5.0, vmax=8.0) & R.steady_mask(A)
    bins58 = np.array([1, 3, 5, 8, 11, 15, 20, 26, 34, 43, 54, 68, 85, 105], float)
    c58 = M.curve_boot(A, m58, th0, "yawA0", nboot=400, seed=23, bins=bins58)
    CTRL["band_5_8"] = c58
    print("   |th| deg      n    LOCAL ratio  [95% CI]     (band 5-8 m/s, K=0)")
    for i, t in enumerate(c58["theta"]):
        if np.isfinite(t):
            print(f"  {t:8.1f} {c58['n_bin'][i]:7d}   {c58['local'][i]:7.2f} "
                  f"[{c58['local_lo'][i]:6.2f},{c58['local_hi'][i]:6.2f}]")

    print("\n=== C4' UNDERSTEER GRADIENT K (fitted, not assumed) ===")
    K = fit_K(A, th0)
    CTRL["K_fit"] = K
    print(f"  K = {K['K_fit_s2_per_m']:.5f} s^2/m   residual CV of the centre ratio across "
          f"7 speed bands = {K['residual_CV_after_fit']:.4f}")
    print(f"  K v^2 / L at 5 m/s = {K['Kv2_over_L_at_5ms'] * 100:.2f} %  "
          f"<- the ENTIRE model error the primary band can carry")
    print("    v band     n     centre ratio K=0   centre ratio K=fit")
    for b in K["bands"]:
        print(f"    {b['v_lo']:>2}-{b['v_hi']:<2} {b['n']:7d}      {b['centre_ratio_K0']:8.2f}"
              f"           {b['centre_ratio_Kfit']:8.2f}")

    print("\n=== C5' SENSITIVITY of the headline swing ===")
    CTRL["sensitivity"] = {}
    base = boot_stat(A, prim, th0, "yawA0", swing2, nboot=800, seed=31)
    print(f"  BASELINE (th0={th0:+.2f}, L=2.830, win=0.5 s, rate<25, K=0): "
          f"{base['point']:.4f} {np.round(base['ci95'], 4).tolist()}")
    CTRL["sensitivity"]["baseline"] = base
    for lab, kw in (("theta0 = -3.25", dict(th0=th0 + 1.0)),
                    ("theta0 = -5.25", dict(th0=th0 - 1.0)),
                    ("theta0 =  0.00", dict(th0=0.0)),
                    ("L = 2.750 m", dict(L=2.750)),
                    ("L = 2.910 m", dict(L=2.910)),
                    ("K = 0.0021", dict(K=0.0021))):
        s = boot_stat(A, prim, kw.get("th0", th0), "yawA0", swing2, K=kw.get("K", 0.0),
                      L=kw.get("L", R.L_WB), nboot=600, seed=31)
        CTRL["sensitivity"][lab] = s
        print(f"  {lab:16s} -> {s['point']:.4f} {np.round(s['ci95'], 4).tolist()}")

    for win in (0.25, 1.0):
        A2 = M.prep(win_s=win)
        th2 = M.fit_theta0(A2, "A")
        p2 = R.base_mask(A2, vmin=1.0, vmax=5.0) & R.steady_mask(A2)
        s = boot_stat(A2, p2, th2, "yawA0", swing2, nboot=600, seed=31)
        CTRL["sensitivity"][f"smooth={win}s"] = s
        print(f"  smooth = {win:4.2f} s   -> {s['point']:.4f} {np.round(s['ci95'], 4).tolist()}")
    A2 = M.prep()
    for rm, dm in ((10.0, 0.15), (60.0, 1.0)):
        p2 = R.base_mask(A2, vmin=1.0, vmax=5.0) & R.steady_mask(A2, rate_max=rm, dyaw_max=dm)
        s = boot_stat(A2, p2, th0, "yawA0", swing2, nboot=600, seed=31)
        CTRL["sensitivity"][f"rate<{rm}"] = s
        print(f"  steadiness rate<{rm:<5.0f} -> {s['point']:.4f} "
              f"{np.round(s['ci95'], 4).tolist()}   ({p2.sum() * R.DT:.0f} s)")

    print("\n=== C6' the SUB-BAND disagreement, opened up ===")
    CTRL["subband_curves"] = {}
    for lo, hi in ((1.0, 2.5), (2.5, 3.5), (3.5, 5.0)):
        mm = R.base_mask(A, vmin=lo, vmax=hi) & R.steady_mask(A)
        c = M.curve_boot(A, mm, th0, "yawA0", nboot=300, seed=41)
        CTRL["subband_curves"][f"{lo}-{hi}"] = c
        floor = np.nanmedian([x for t, x in zip(c["theta"], c["local"])
                              if np.isfinite(t) and CENTRE_LO <= t < CENTRE_HI])
        print(f"  v {lo}-{hi} m/s  {c['seconds']:5.0f} s   floor(3-50) {floor:6.2f}   "
              f"plateau {c['plateau_local']:6.2f}   swing {floor / c['plateau_local']:.4f}")
        print("      " + "  ".join(f"{t:.0f}:{x:.1f}" for t, x in zip(c["theta"], c["local"])
                                   if np.isfinite(t)))

    (OUT / "controls.json").write_text(json.dumps(CTRL, indent=1, default=float))
    print(f"\nwrote {OUT / 'controls.json'}")


if __name__ == "__main__":
    main()
