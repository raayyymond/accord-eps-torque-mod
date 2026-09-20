# -*- coding: utf-8 -*-
"""WHAT IS THE LOOP ACTUALLY CLOSED ON?  A check that decides how every later number is read.

latcontrol_torque.py:252-253
    measured_curvature = -VM.calc_curvature(radians(CS.steeringAngleDeg - angleOffsetDeg), vEgo, roll)
    measurement       = measured_curvature * vEgo**2
so `actualLateralAccel` -- the signal the PID subtracts from the setpoint -- is the STEERING ANGLE
put through a kinematic model, NOT a measured yaw.  If that is right, then
  (a) the fork's lateral loop is a steering-ANGLE loop, and the vehicle is OUTSIDE it;
  (b) the plant inside the loop is exactly torque -> wheel angle, i.e. the EPS and the steering
      mechanics -- which is where the V282 -> V293 change lives;
  (c) "wheel motion that does not become yaw" is invisible to the loop by construction.
Test: regress y on the angle-derived prediction frame by frame, and compare the angle channel with
the INDEPENDENT livePose yaw*v.

out: U1B-OUT.txt
"""
import numpy as np
import ulib as U
import v282cmp as V

G = 9.81
LB_TO_KG, STD_CARGO = 0.453592, 136.0
M = 3279 * LB_TO_KG + STD_CARGO
WB = 2.83
AF = WB * 0.39
AR = WB - AF
TSF_FACTOR = 0.8467
CIVIC_M, CIVIC_WB = 1326.0 + STD_CARGO, 2.70
CIVIC_CTF = CIVIC_WB * 0.4
CIVIC_CTR = CIVIC_WB - CIVIC_CTF
cF = 192150.0 * TSF_FACTOR * M / CIVIC_M * (AR / WB) / (CIVIC_CTR / CIVIC_WB)
cR = 202500.0 * TSF_FACTOR * M / CIVIC_M * (AF / WB) / (CIVIC_CTF / CIVIC_WB)
SF1 = M * (cF * AF - cR * AR) / (WB ** 2 * cF * cR)

L = ["IS THE LOOP'S MEASUREMENT THE STEERING ANGLE?  (EVIDENCE: frame-by-frame reconstruction)", ""]
L.append(f"{'route':<10}{'fam':<9}{'n':>8}{'corr(y, angle model)':>22}{'slope':>9}{'resid/rms':>11}"
         f"{'corr(y, yawpose)':>18}{'|yaw|/|y|':>11}")
for rt in U.FAMILY:
    S = U.load(rt)
    D = np.load(V.CACHE / f"{rt}.npz", allow_pickle=True)
    t = S["t"]
    roll = np.interp(t, D["t_lp"], D["roll"])
    sR = np.interp(t, D["t_lp"], D["sR"])
    stiff = np.interp(t, D["t_lp"], D["stiff"])
    aoff = np.interp(t, D["t_lp"], D["aoff"])
    v = S["v"]
    sf = SF1 / np.maximum(stiff, 0.1)
    cfac = 1.0 / (1.0 - sf * v ** 2) / WB
    # vehicle_model.calc_curvature(angle, v, roll) = curvature_factor*angle/sR + roll_comp
    curv = cfac * np.radians(S["sa"] - aoff) / sR + (G * roll) / ((1.0 / sf) - v ** 2)
    yhat = -(-curv) * v ** 2          # measurement = -calc_curvature(...)*v^2 ; sign handled below
    yhat = -curv * v ** 2
    m = U.usable(S, 8.0) & np.isfinite(yhat)
    a, b = S["y"][m], yhat[m]
    c = float(np.corrcoef(a, b)[0, 1])
    sl = float(np.dot(a, b) / np.dot(b, b))
    resid = float(np.std(a - sl * b) / np.std(a))
    yp = S["la_pose"][m]
    c2 = float(np.corrcoef(a, yp)[0, 1])
    rat = float(np.std(yp) / np.std(a))
    L.append(f"{U.SHORT[rt]:<10}{S['fam']:<9}{m.sum():>8d}{c:>22.5f}{sl:>9.4f}{resid:>11.4f}{c2:>18.4f}{rat:>11.3f}")
    del S, D
L.append("")
L.append("READ: corr ~1.000 and residual ~0 => `actualLateralAccel` IS the steering angle through the")
L.append("kinematic model.  The fork's lateral loop is therefore an ANGLE loop; the vehicle (angle -> yaw)")
L.append("sits OUTSIDE it, and wheel motion that does not become yaw is invisible to the feedback.")
out = "\n".join(L)
open("U1B-OUT.txt", "w").write(out)
print(out)
