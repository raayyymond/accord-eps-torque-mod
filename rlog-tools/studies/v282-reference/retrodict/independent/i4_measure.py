# -*- coding: utf-8 -*-
"""i4 -- measure, per route, the things the loop model needs, and CHECK them against the flown params.

Measured here (EVIDENCE, all from logged signals):
  g      the static angle -> measurement map gain:  la_act = -g * (sa - aoff),  deg -> m/s^2.
         The fork computes measurement = -VM.calc_curvature(radians(sa - aoff), v, roll) * v^2 with
         NO filter, so this must be a tight static fit; R^2 is reported as the control.
  LAF    -(p + i + f) / out, the flown latAccelFactor (must equal SteerLatAccel).
  kp_eff p / cs_err  (pid_log.error is error_with_lsf, so this must equal SteerKP exactly).
  lsf    from the fit of cs_err / (setpoint - la_act) against 1 + lsf/kp  -- confirms the lsf formula
         AND, on the notch routes, is expected to FAIL (the notch sits between them), which is itself
         a check that the notch is live.

ANALYSIS ONLY.  python i4_measure.py <route> [...]
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V  # noqa: E402

FS = 100.0
LOW_SPEED_X, LOW_SPEED_Y, MIN_SPEED = [0, 10, 20, 30], [12, 10.5, 8, 5], 1.0


def lsf_of(v):
    return (np.interp(v, LOW_SPEED_X, LOW_SPEED_Y) / np.maximum(v, MIN_SPEED)) ** 2


def measure(route, vlo=0.0):
    D = np.load(V.CACHE / f"{route}.npz", allow_pickle=True)
    S = V.load(route)
    t = S["t"]
    err = np.interp(t, D["t_cs"], D["cs_err"])
    m = S["active"] & ~S["pressed"] & (S["v"] >= vlo) & np.isfinite(S["la_act"]) & np.isfinite(S["sa"])
    m &= np.isfinite(S["aoff"]) & np.isfinite(S["out"]) & ~S["sat"]
    out = dict(route=route, n=int(m.sum()), sec=float(m.sum() / FS))
    if m.sum() < 1000:
        return out
    x = (S["sa"] - S["aoff"])[m]
    y = S["la_act"][m]
    # -g from a through-origin fit AND from a fit with intercept (report both)
    g0 = -float(np.dot(x, y) / np.dot(x, x))
    A = np.vstack([x, np.ones_like(x)]).T
    sol, *_ = np.linalg.lstsq(A, y, rcond=None)
    g1, c1 = -float(sol[0]), float(sol[1])
    res = y - (-g1 * x + c1)
    out["g_origin"] = g0
    out["g_fit"] = g1
    out["g_intercept"] = c1
    out["g_R2"] = float(1.0 - np.var(res) / np.var(y))
    # g is speed dependent (v^2 / (SR L (1+K v^2))): report it per speed bin
    out["g_bins"] = {}
    for lo, hi in ((5, 10), (10, 15), (15, 20), (20, 25), (25, 99)):
        b = m & (S["v"] >= lo) & (S["v"] < hi)
        if b.sum() < 500:
            continue
        xb, yb = (S["sa"] - S["aoff"])[b], S["la_act"][b]
        out["g_bins"][f"{lo}-{hi}"] = dict(
            g=-float(np.dot(xb, yb) / np.dot(xb, xb)), n=int(b.sum()),
            v=float(np.median(S["v"][b])),
            R2=float(1.0 - np.var(yb + (np.dot(xb, yb) / np.dot(xb, xb)) * xb) / np.var(yb)))
    # LAF
    o = S["out"][m]
    ok = np.abs(o) > 5e-3
    out["LAF"] = float(np.median(-(S["p"][m] + S["i"][m] + S["f"][m])[ok] / o[ok]))
    # kp = p / err
    e = err[m]
    ok2 = np.abs(e) > 1e-3
    out["kp_from_p_over_err"] = float(np.median(S["p"][m][ok2] / e[ok2]))
    # lsf check:  err / (setpoint - la_act) should be 1 + lsf/kp when NO notch is live
    raw = (S["setpoint"] - S["la_act"])[m]
    ok3 = np.abs(raw) > 0.05
    r = e[ok3] / raw[ok3]
    out["err_over_rawerr_med"] = float(np.median(r))
    out["err_over_rawerr_iqr"] = float(np.percentile(r, 75) - np.percentile(r, 25))
    vv = S["v"][m][ok3]
    kp = out["kp_from_p_over_err"]
    pred = 1.0 + lsf_of(vv) / max(kp, 1e-3)
    out["lsf_pred_med"] = float(np.median(pred))
    out["lsf_resid_med"] = float(np.median(r - pred))
    out["v_med_engaged"] = float(np.median(S["v"][m]))
    out["v_med_15plus"] = (float(np.median(S["v"][m & (S["v"] >= 15)]))
                           if (m & (S["v"] >= 15)).sum() > 100 else None)
    out["sec_15plus"] = float((m & (S["v"] >= 15)).sum() / FS)
    del S, D
    return out


if __name__ == "__main__":
    res = {}
    for route in sys.argv[1:]:
        r = measure(route)
        res[route] = r
        print(f"\n=== {route}  {r.get('sec',0):.0f} s usable ({r.get('sec_15plus',0):.0f} s >=15 m/s) ===")
        if "LAF" not in r:
            print("   too little data")
            continue
        print(f"   LAF {r['LAF']:.4f}   kp(p/err) {r['kp_from_p_over_err']:.4f}   "
              f"v_med {r['v_med_engaged']:.1f} (>=15: {r['v_med_15plus']})")
        print(f"   g (origin) {r['g_origin']:.5f}  g (fit) {r['g_fit']:.5f} +{r['g_intercept']:+.4f}  "
              f"R2 {r['g_R2']:.4f}   [m/s^2 per deg]")
        for k, b in r["g_bins"].items():
            print(f"      v {k:6s} n {b['n']:7d} vmed {b['v']:5.1f}  g {b['g']:.5f}  R2 {b['R2']:.4f}")
        print(f"   err/rawerr med {r['err_over_rawerr_med']:.4f} (IQR {r['err_over_rawerr_iqr']:.4f})  "
              f"vs 1+lsf/kp {r['lsf_pred_med']:.4f}   resid {r['lsf_resid_med']:+.4f}")
    json.dump(res, open(HERE / "out_i4_measure.json", "w"), indent=1)
