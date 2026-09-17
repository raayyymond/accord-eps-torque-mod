"""ALTMETHOD pass 2: NONLINEAR, event-based re-derivation from RAW per-sample signals (one route loaded
at a time, RAM-safe), independent of s3_pass2.py's linear-gain / mean-error machinery entirely.

Physical target: 'ignores self-centring (caster)' predicts one of two nonlinear signatures in the RETURN
window (from end-of-unwind e['j'] to e['j']+3s, non-pressed frames only, the same window s3turns.metrics()
uses for ret_overshoot/ret_err):
  (a) the achieved angle decays to zero SLOWER than the desired angle decays (a first-order lag mismatch
      in the DECAY TIME CONSTANT specifically, not just a mean-error/linear-gain mismatch) -- fit
      y(t) = c + A*exp(-t/tau) to s*aa and s*ap separately from s*ad_shifted, per event, via nonlinear
      least squares, and compare tau_achieved - tau_desired between groups; or
  (b) the achieved angle overshoots TRUE zero (not just 'beyond what was commanded', which
      ret_overshoot_deg already tested and found null) -- because an un-modelled caster torque snaps the
      wheel through centre. Measure, per event: does s*aa (or s*ap) go negative within the return window,
      and by how much/for how long.

This is a genuinely different estimator family (nonlinear curve fit + true-zero-crossing event detection)
from the original's linear mean-error / linear-gain-slope approach.
"""
import sys, json
import numpy as np
from scipy.optimize import curve_fit
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel')
import s3turns as T
import v282cmp as V

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s3_accel__nocastersign__altmethod/'
GM = {"V282": "V282", "V282old": "V282old", "T64": "TQ", "T64B": "TQ", "T5": "TQ", "T4": "TQ"}


def expdecay(t, c, A, tau):
    return c + A * np.exp(-t / max(tau, 1e-3))


def fit_tau(t, y):
    """t starts at 0. Returns (tau, r2) or (nan, nan) if unfit-able."""
    m = np.isfinite(y)
    if m.sum() < 15:
        return np.nan, np.nan
    tt, yy = t[m], y[m]
    c0 = yy[-1]
    A0 = yy[0] - c0
    if abs(A0) < 1.0:  # too flat to fit a decay to (already at/near centre)
        return np.nan, np.nan
    try:
        popt, _ = curve_fit(expdecay, tt, yy, p0=[c0, A0, 0.4],
                             bounds=([-200, -400, 0.03], [200, 400, 4.0]), maxfev=4000)
    except Exception:
        return np.nan, np.nan
    yhat = expdecay(tt, *popt)
    ss_res = np.sum((yy - yhat) ** 2); ss_tot = np.sum((yy - np.mean(yy)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 1e-6 else np.nan
    return float(popt[2]), float(r2)


rows = []
for rk in V.ROUTES:
    R = T.prep(rk)
    G = GM[R["group"]]
    evs, _ = T.find_turns(R)
    n = len(R["t"])
    for e in evs:
        s, P, j = e["s"], e["P"], e["j"]
        r0, r1 = j, min(n, j + 300)
        if r1 - r0 < 30:
            continue
        t = np.arange(r1 - r0) / V.FS
        press = R["pressed"][r0:r1]
        active = R["active"][r0:r1]
        keep = active & ~press
        row = dict(rk=rk, group=G, G=G, v=e["v"], P=P)
        # desired, shifted by the route's own learned lag (same convention as s3turns.metrics default)
        ds = int(round(R["d"] * V.FS))
        ad_shift = T.shift(R["ad"], ds)
        ad_seg = s * ad_shift[r0:r1]
        ad_seg = np.where(keep, ad_seg, np.nan)
        tau_d, r2_d = fit_tau(t, ad_seg)
        row["tau_desired"] = tau_d; row["r2_desired"] = r2_d
        for key in ("aa", "ap"):
            src = np.where(R["pressed"], np.nan, R[key])
            seg = s * src[r0:r1]
            seg = np.where(active[None].reshape(-1) if False else active, seg, np.nan)  # active only (pressed already nan'd)
            tau, r2 = fit_tau(t, seg)
            row[f"tau_{key}"] = tau; row[f"r2_{key}"] = r2
            row[f"dtau_{key}"] = (tau - tau_d) if (np.isfinite(tau) and np.isfinite(tau_d)) else np.nan
            # true-zero overshoot: min of seg after it first drops below 0.3*P (i.e. once it's most of the
            # way back), restricted to kept frames; overshoot_deg = max(0, -min(seg_late))
            thr = 0.3 * P
            below = np.where(keep & np.isfinite(seg) & (seg < thr))[0]
            if len(below):
                k0 = below[0]
                tail = seg[k0:][np.isfinite(seg[k0:]) & keep[k0:]]
                ov = float(max(0.0, -np.nanmin(tail))) if len(tail) else np.nan
                frac_neg = float(np.mean(tail < -1.0)) if len(tail) else np.nan  # frac of the tail sitting >1 deg past true zero
            else:
                ov, frac_neg = np.nan, np.nan
            row[f"truezero_overshoot_deg_{key}"] = ov
            row[f"truezero_negfrac_{key}"] = frac_neg
        rows.append(row)
    print(rk, G, len(evs), flush=True)
    del R

json.dump(rows, open(OUT + 'alt2_events.json', 'w'), indent=1)
print("done", len(rows))
