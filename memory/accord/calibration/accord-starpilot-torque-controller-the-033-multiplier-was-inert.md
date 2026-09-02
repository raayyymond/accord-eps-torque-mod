---
name: accord-starpilot-torque-controller-the-033-multiplier-was-inert
description: The operator's StarPilot runs LatControlTorque on EVERY logged route (60/60, torqueState 92,456/92,456 frames on r2e). His HondaLateralPidKpScale/KiScale = 0.33 is gated on lateralTuning.which()=="pid" and has NEVER been active; the ","->EPS_MODIFIED 0.5 factor is on the Accord's PID branch and is DISCARDED by configure_torque_tune. What actually compensated the 6x EPS gain was torqued's LIVE latAccelFactor (raw 4.5-5.2 on V276, clipped to 2.196). kp is a FLAT 0.6 (controlsd overrides the speed schedule with SteerKP), ki 0.35, friction 0.212 port / ~0.17 live, LAF 2.14 live. On V279 the FRICTION term is 60-80% of the loop gain at the 3.9 Hz crossover; GM 2.1x at 30 m/s (extrapolated). First move: SteerFriction 0.212 -> 0.08; SteerLatAccel to the toggle max 2.53; leave SteerKP 0.6 (ceiling 0.9); read latAccelFactorRaw and edit params.toml:14 if raw > 2.5.
metadata:
  type: reference
---

# StarPilot runs the TORQUE controller; the 0.33 multiplier was INERT -- 2026-09-02 [EVIDENCE, orchestrator-verified]

Verified in `openpilots/raayyymond-StarPilot/StarPilot` @ e631b24:
```
starpilot_variables.py:689   honda_pid_lateral = car_make=="honda" and CP.lateralTuning.which()=="pid" and not is_angle_car
                     :690-691 HondaLateralPidKpScale/KiScale  condition=honda_pid_lateral -> 1.0 on a torque CP
interfaces.py:190-198        toggles ("force_torque_controller","nnff","nnff_lite") -> configure_torque_tune(): OVERWRITES lateralTuning
honda/interface.py:139-142   Accord: if eps_modified: pid.kpV/kiV = 0.3/0.09  -- on the PID branch, discarded above
controlsd.py:124-125         if which() != "pid": LaC.pid._k_p = steerKp  (flat 0.6; the 250->0.6 speed schedule is replaced)
torque_data/params.toml:14   "HONDA_ACCORD" = [1.689, 0.325, 0.212]   (LAT_ACCEL_FACTOR, MAX_LAT_ACCEL, FRICTION)
```
Rlog census (all 60 routes in `analysis-2020accord/rlogs`): `lateralTuning.which()=='torque'` and
`lateralControlState.which()=='torqueState'` on every one. torqueState.p / error = 0.600 at p5/p50/p95 over
5,982 active frames on r2e -> kp is flat 0.6 (EVIDENCE).

**What this means.**
- The operator believed 0.5 x 0.33 ~ 1/6 compensated the 6x EPS torque. **Neither factor has ever been active on the
  torque path.** What compensated was `torqued`'s live `latAccelFactor` (raw 4.5-5.2 on the V276 rate loop, 3.0 on
  1x builds), CLIPPED by the sanity bound to <= 1.3 x 1.689 = 2.196; the value in use drifted 1.73 -> 2.14 on r2e.
- The loop as run: `error_with_lsf = error*(1+lsf/kp)`; `ff = future_desired_latAccel - roll - offset +
  friction*get_friction(...)` where `get_friction` is a SATURATING LINEAR (slope friction/0.3 in torque units, LAF
  cancels), `output_torque = pid.update(...)/LAF`, x4096 onto CAN 1:1. **No friction "relay" -- a saturating linear;
  it cannot sustain a limit cycle alone if the linear loop with its full slope has margin.**
- **V279 (pure feedforward, 0.645 EPS torque counts per CAN count):** |L| at the 3.9 Hz phase crossover =
  [kp_eff + fricSlope] x (4096/LAF) x 0.645 x |G(3.9)| x latAccel/deg(v), |G| = 5.5e-4 deg/count (r2e, hands-on).
  Friction is 60-80% of that gain at every speed. GM: 6.8x @7.5 m/s, 5.4x @13, 3.6x @20, 2.8x @25, 2.1x @30 (>=30
  extrapolated). LAF barely moves it (friction's torque-space slope is LAF-independent).
- The feedforward becomes REAL torque on V279: 1 m/s^2 desired at LAF 1.689 -> 1563 EPS counts = 62% of the 2505
  peak = 3.7x stock's peak, before any error term. The torque-mode LAF is not derivable from any flown log (BELIEF:
  well above 1.689); torqued will report it in `liveTorqueParameters.latAccelFactorRaw` but USES a value capped at
  2.196; the SteerLatAccel toggle caps at 1.5x = 2.53; higher needs `params.toml:14`.

**First-drive settings (derived, BELIEF on the >=30 m/s rows):** SteerFriction 0.212 -> **0.08** first (GM 2.1x ->
3.6x at 30 m/s); SteerLatAccel -> **2.53** (toggle max); SteerKP **leave 0.6**, ceiling 0.9 and only with friction
<= 0.08; no Ki lever exists on this path; **ForceAutoTuneOff** so the clipped live LAF does not fight the custom one.
The 0.33 can stay -- it is inert. Verify `lateralControlState.which()=='torqueState'` on every drive.
Watch for a 3-4 Hz shimmy ABOVE ~25 m/s that grows with speed and vanishes under a little steady torque (friction in
its linear band hitting the margin): SteerFriction down first, then SteerLatAccel up.

See [[accord-the-rate-loop-is-a-bang-bang-servo-p-rails-at-e-440]] and
[[feedback-the-operator-runs-force-torque-controller-check-toggles-not-defaults]].

## Re-verified by the orchestrator on the operator's ACTUAL tree, `openpilots/StarPilot` @ 3d4c625de (2026-09-02)
The agent had traced the older fork `openpilots/raayyymond-StarPilot/StarPilot` @ e631b24. On HEAD:
- `latcontrol_torque.py:152-153` sets the Accord's torque PID to kp 0.8 (last knot) / ki 0.15 flat (`HONDA_ACCORD_TORQUE_KP/KI`,
  `latcontrol_vehicle_tunes.py:77-78`) -- but `controlsd.py:443-444` overwrites `_k_p` with the `SteerKP` toggle EVERY frame
  (`starpilot_variables.py:757`: default KP = 0.6, range 0.3-0.9, gated on is_torque_car). Effective: **kp = SteerKP, ki = 0.15**.
- `honda_lateral_pid_kp_scale` has exactly ONE consumer in the whole tree: `latcontrol_pid.py:119-125`. Inert on torque.
- No EPS_MODIFIED effect on the Accord torque path (only `is_civic_bosch_modified` scales LAF). `params.toml:14` unchanged.
- torqued caps: LAF 1.3x = 2.196, friction 1.5x = 0.318 (`torqued.py:25,27`).
**Always trace `openpilots/StarPilot`, and re-check after the operator pulls.**
