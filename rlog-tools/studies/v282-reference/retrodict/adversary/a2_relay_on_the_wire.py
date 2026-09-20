"""A2 - is the SteerFriction relay visible IN THE LOG, and how big was it on each route?

In the plant-FF branch the logged feedforward is
    cs_f = (plant_ff + friction_torque + inner) * LAF
and the relay's own contribution is
    friction_torque * LAF = get_friction(err + 0.22*jerk_dz) = F * LAF * clip(err/0.30, -1, 1)
i.e. a RAMP that saturates at +/- F*LAF within +/-0.30 m/s^2 of error.  Nothing else in ff
depends on the instantaneous error, so a step of height 2*F*LAF across err = 0, with a
+/-0.30-wide ramp, is the relay's fingerprint.

Predicted step height 2*F*LAF, from each route's own params:
    r71  2*0.011*14   = 0.308      r73  2*0.21205*14 = 5.94
    V282 2*0.01 *6    = 0.120      r72  0 (F = 0)
"""
import json
import os
import numpy as np

CACHE = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v282ref"
PARAMS = json.load(open(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/hsurface/surface/params_all.json"))

ROUTES = ["00000064--ce6b0b0ebb", "00000070--717f5a7866", "00000071--f2c9d073a3",
          "00000072--8001fc3048", "00000073--79fd149dd8", "00000075--6c8687d5bd",
          "0000006d--05e83bb04f"]

print(f"{'route':22} {'F(param)':>9} {'LAF':>5} {'pred step':>10} {'meas step':>10} {'n-':>6} {'n+':>6}  verdict")
print("-" * 92)
for key in ROUTES:
    z = np.load(os.path.join(CACHE, key + ".npz"))
    t = z["t_cs"]
    act = z["cs_active"] > 0.5
    err, ffw = z["cs_err"], z["cs_f"]
    v = np.interp(t, z["t_cst"], z["vego"])
    sp = np.interp(t, z["t_cst"], z["spress"]) > 0.5
    sel = act & ~sp & (v >= 15.0) & np.isfinite(err) & np.isfinite(ffw)
    e, f = err[sel], ffw[sel]
    del z
    # the relay is fully saturated for |e| > 0.30; compare the plateau either side, using a
    # band close enough to zero that the smooth (angle-driven) part of ff is near-symmetric
    lo = (e > -1.2) & (e < -0.35)
    hi = (e > 0.35) & (e < 1.2)
    step = float(np.median(f[hi]) - np.median(f[lo])) if (lo.sum() > 50 and hi.sum() > 50) else np.nan
    pa = PARAMS[key]
    F = float(pa["SteerFriction"]) if pa["SteerFriction"] not in ("ABSENT", None) else float("nan")
    LAF = float(pa["SteerLatAccel"])
    pred = 2 * F * LAF
    v_ = "relay LIVE" if abs(step) > 0.5 * max(pred, 0.05) and pred > 0.05 else ("no relay" if pred < 0.05 else "?")
    print(f"{key:22} {F:9.5f} {LAF:5.1f} {pred:10.3f} {step:10.3f} {int(lo.sum()):6d} {int(hi.sum()):6d}  {v_}")
