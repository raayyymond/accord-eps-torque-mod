# StarPilot (Dom @3d4c625de) torque-controller and torqued math — 2026-09-02, subagent `opmath`

Reconstructed by the orchestrator from opmath's report (the agent's own file never landed on disk). Source: `C:\Users\dudei\Desktop\Projects\openpilots\StarPilot`,
branch `Dom`, HEAD 3d4c625de. Files: `selfdrive/controls/lib/latcontrol_torque.py`, `selfdrive/controls/controlsd.py` (:353–374 `get_torque_control_params`,
:443–444 kp overwrite, :485–495), `selfdrive/locationd/torqued.py` (:235,237 filtered-field overwrite), `opendbc_repo/.../honda` torque data, `common/params_keys.h:340`,
`system/manager/manager.py:569–571`. All EVIDENCE from source unless marked. Operator toggles: `analysis-2020accord/reference/toggle-backup(2).decoded.json`.

## 1. The control law as run on this car (torque controller)

Torque units [−1, 1]; ×4096 to the CAN 0xE4 command 1:1 after a ±0.03/frame rate limit.

```
T = clip(SteerKP·e' + I + FF_la + LAF·friction·sat((e' + 0.22·j_f)/0.30), −LAF, +LAF) / LAF
  = [SteerKP·e' + I + FF_la]/LAF + friction·sat((e' + 0.22·j_f)/0.30)          (unsaturated)

e'      = (setpoint − m)·(1 + lsf(v)/SteerKP),   lsf = (interp(v,[0,10,20,30],[12,10.5,8,5]) / v)²   (0.028 at 30 m/s)
m       = curvature(steering angle, vehicle model with steerRatio·14/16.33)·v²      ← from the STEERING ANGLE, not the IMU
setpoint= a_req(t − lat_delay)·v² + j_des·lat_delay
j_des   = LPF_1.2Hz(clip((a_fut − a_exp)/lat_delay, ±2.5)),   lat_delay = liveDelay.lateralDelay + 0.1
FF_la   = (a_fut − 9.81·roll − latAccelOffset)·(1 − 0.10·sigmoid((|setpoint| − 0.45)/0.12))   (Accord taper, ≤ 10 %, only above 0.45 m/s²)
j_f     = jerk beyond a centre deadzone (0.18 m/s³ at ≥ 12 m/s; zero when |setpoint| > 0.35)
FRICTION_THRESHOLD = 0.30 m/s² (lat-accel units, all speeds; the GM speed curve tops at 0.27, max() gives 0.30)
kp = SteerKP, flat (controlsd.py:443–444 overwrites _k_p every frame; default 0.6, clamp 0.3–0.9); ki = 0.15 flat (Accord override); kd = 0.
```

`get_friction` multiplies by LAF and `torque_from_lateral_accel` divides by it → **the friction term in torque units is `friction·sat(x/0.30)`, independent
of LAF**; slope friction/0.30 = 0.707 per m/s² at 0.212. "," / EPS_MODIFIED and HondaLateralPidKp/KiScale are inert on this path (PID branch only,
discarded by `configure_torque_tune`).

## 2. torqued (`torqued.py`)

x = −carOutput.actuatorsOutput.torque (shifted by lag = liveDelay.lateralDelay); y = v·yaw_rate_calibrated(livePose) − 9.81·sin(roll).
Qualify: latActive over [t−2 s, t+lag], no steeringPressed, v > 15 m/s, |x| > 0.02, |y| ≤ 1.0. 8 buckets over x ∈ [−0.5, 0.5] (|x| ≥ 0.5 dropped),
1500 per bucket; valid when bucket counts ≥ [100,300,500,500,500,500,300,100] and total ≥ 4000.
Fit: 2000 random rows [x, 1, y], SVD total-least-squares, v3 = (a, b, c): `latAccelFactorRaw = −a/c`, `latAccelOffsetRaw = −b/c`,
`frictionCoefficientRaw = 1.5·std((y − slope·x)/sqrt(1 + slope²))` (perpendicular residual; 0.764·σ_y at LAF 1.689).
Caps on the FILTERED path only: LAF clip [1.182, 2.196] (0.7–1.3 × 1.689), friction clip [0.106, 0.318] (0.5–1.5 × 0.212), offset unclipped; then
FirstOrderFilter with rc = decay 50 → 250 stepped at 4 Hz (effective τ 250–1250 s). useParams = True for Honda.

**Precedence** (controlsd.py:353–374, 485–495): custom toggle > live filtered > CarParams. `use_custom_X = (SteerX differs from CP by ≥ 0.01 and not
ForceAutoTune) OR ForceAutoTuneOff`. Branch default ForceAutoTuneOff = True (params_keys.h:340, manager.py:571) — **but the operator's backup has
ForceAutoTune = True, ForceAutoTuneOff = False, Steer* = stock**, so the controller takes the live FILTERED values, which fall back to CarParams (1.689/0.212)
whenever `liveValid` is false. torqued.py:235,237 overwrite the *Filtered log fields with the toggle values when custom is on → *Filtered = what the
controller used; *Raw = the untouched fit.

## 3. Small-signal outer gain (linear band |e' + 0.22·j_f| < 0.30)

```
dT/de = (1 + lsf/SteerKP)·[SteerKP/LAF + friction/0.30]    torque per m/s²  (×4096 for CAN counts)   + integral 0.15·(1 + lsf/kp)/(LAF·s)
```
At 30 m/s, kp 0.6, LAF 1.689, friction 0.212: P part 0.372, friction part 0.739, total 1.111 → friction is ~67 % at every speed ≥ 20 m/s.
Friction 0.212 → 0.08: total −41 %. LAF 1.689 → 2.196: −8 % (touches only P/FF). SteerKP 0.6 → 0.3: −14 % only (the friction part RISES via lsf/kp).
ki/kd are not knobs. At lane-change error 0.05–0.1 m/s² the friction term contributes ~150–315 CAN counts vs P ~76–152. The friction input includes
0.22·j_des (up to 0.55 > 0.30), so planned jerk alone can saturate it during the ramp → the incremental gain collapses to the P part mid-manoeuvre.
Fit on x = e' + 0.22·frictionJerk, not on e.

## 4. Log fields and Params keys

carParams.lateralTuning.torque.{latAccelFactor, friction, latAccelOffset}; controlsState.lateralControlState.torqueState.{error(=e'), p, i, d, f(=FF incl.
friction, lat-accel units), output(=−T), actualLateralAccel(=m), desiredLateralAccel(=setpoint), desiredLateralJerk, saturated}; kp_used = p/error;
starpilotLateralState.{frictionThreshold, frictionScale, feedforward, frictionJerk, frictionJerkDeadzone, lowSpeedFactor, unwindDetected} (100 Hz);
liveTorqueParameters.{latAccelFactorRaw, latAccelOffsetRaw, frictionCoefficientRaw, *Filtered, liveValid, useParams, totalBucketPoints, calPerc, decay};
liveDelay.lateralDelay; liveParameters.{steerRatio, stiffnessFactor, angleOffsetDeg, roll}; carOutput.actuatorsOutput.torque; carControl.latActive;
livePose yaw/roll; starpilotPlan.starpilotToggles (JSON). Params: SteerKP, SteerFriction, SteerLatAccel (+ *Stock), ForceAutoTune, ForceAutoTuneOff,
ForceTorqueController, SteerDelay/UseAutoSteerDelay, SteerRatio. Decode identity: −output·LAF = p + i + f before the ±LAF clip.

Not verified from source (BELIEF): whether an FLM trial is applied (frictionThreshold ≠ 0.30 in starpilotLateralState would show it).
