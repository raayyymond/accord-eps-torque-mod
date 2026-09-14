# The StarPilot fork's lateral torque path under the V293 toggle config

**Fork**: `C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot`, branch `Dom`,
HEAD `4247cb09e`, working tree clean (verified `git rev-parse HEAD`, `git status --porcelain`).
**Date**: 2026-09-13. **Method**: full read of `latcontrol_torque.py`, `latcontrol.py`, `common/pid.py`,
`drive_helpers.py`, the lateral half of `controlsd.py`, the Accord block of `latcontrol_vehicle_tunes.py`,
`starpilot_variables.py`, `torqued.py`, `lagd.py`, `vehicle_model.py`, plus three independent subagent
sweeps over the car controller / 0xE4 packer, the param surface, and the cereal logging.

Every claim below is marked **EVIDENCE** (with the file and function or grep string read) or **BELIEF**.
Cited by heading / function name, never by line number.

---

## 0. HEADLINE

**The fork carries an explicit plant model for this car, and the V293 config switches it off.**

`HONDA_ACCORD_EPS_G_V` / `HONDA_ACCORD_EPS_K_V` in
`selfdrive/controls/lib/latcontrol_vehicle_tunes.py` encode

```
steering wheel rate [deg/s] = G(v) * torque - k(v) * angle        torque in [-1, 1]
```

identified on routes r34/r35/r39/r3a/r3c (2026-09-02..04, 20 Hz grid, engaged hands-off, R 0.95-0.99 at
zero lag), i.e. **on the V280+ rate-servo firmware**. Its own comment states the case the operator is now
describing from the seat:

```
# A lat-accel feedforward (setpoint / latAccelFactor) is 3-10x too much
# torque on this plant; the P term then has to cancel it and the loop settles above command.
```

With `AccordRatePlantFF = false` the controller takes the generic `else` branch and reverts to exactly
that lat-accel feedforward. **So V293 runs the model the fork itself documented as wrong for a rate
plant, on a firmware that is no longer a rate plant.** Whether it is right for V293 is the open question,
and the answer is one number: the true torque-to-lat-accel gain. EVIDENCE, full read of
`LatControlTorque.update`.

---

## 1. THE PATH, END TO END

All at 100 Hz. `controlsd.Controls.run` and `card.card_thread` both use `Ratekeeper(100)`;
`DT_CTRL = 0.01`. `CarController.update` is called from `card.step` -> `CI.apply` every iteration with no
modulo gate, so **0xE4 is sent at 100 Hz**. EVIDENCE.

### Stage A - desired curvature (`Controls.state_control`)

`model_v2.action.desiredCurvature` when `latActive`, else `self.curvature` (the measured value, so
re-engagement does not step). Then the fork's low-speed turn-hold block, the turn-lead block,
`lane_centering.update`, then:

```python
self.desired_curvature, curvature_limited = clip_curvature(CS.vEgo, self.desired_curvature,
                                                           new_desired_curvature, lp.roll, jerk_factor)
```

`clip_curvature` (in `drive_helpers.py`) enforces `MAX_LATERAL_JERK = 5.0` m/s^3, `MAX_LATERAL_ACCEL_NO_ROLL
= 3.0` m/s^2 and `MAX_CURVATURE = 0.2`, and returns `curvature_limited`.

### Stage B - the delay budget

```python
lat_smooth_seconds = get_control_lateral_smooth_seconds(self.CP.brand, CS.vEgo, self.CP.lateralSmoothSeconds)
lat_delay = self.sm["liveDelay"].lateralDelay + lat_smooth_seconds
```

`get_control_lateral_smooth_seconds` returns `LAT_SMOOTH_SECONDS` for every brand except rivian and
subaru. `LAT_SMOOTH_SECONDS = 0.1` (`selfdrive/modeld/modeld.py`). **There is no speed term for Honda.**
`lagd` sets `liveDelay.lateralDelay = starpilot_toggles.steerActuatorDelay` when
`use_custom_steerActuatorDelay`, which is `advanced_lateral_tuning and not use_auto_steer_delay`. The
operator has `UseAutoSteerDelay = False`, so the learner is bypassed and the stored `SteerDelay = 0.2`
wins. **Effective `lat_delay = 0.30 s`, `delay_frames = 30`.** EVIDENCE.

`starpilot/common/lateral_delay.py`: `full_lateral_delay(v) = v + LATERAL_CONTROL_SOFTWARE_DELAY (0.2)`,
and `CP.steerActuatorDelay = 0.1` for Honda, so `SteerDelayStock = 0.3`. The operator runs 0.2, i.e.
**0.1 s LESS lookahead than stock.**

### Stage C - `LatControlTorque.update`

Sign frame is left-positive inside; `steer_max = 1.0` from `LatControl.__init__`.

```python
measured_curvature = -VM.calc_curvature(math.radians(CS.steeringAngleDeg - params.angleOffsetDeg), CS.vEgo, params.roll)
measurement = measured_curvature * CS.vEgo ** 2
future_desired_lateral_accel = desired_curvature * CS.vEgo ** 2

delay_frames = int(np.clip(lat_delay / self.dt, 1, self.request_buffer_len))      # = 30
expected_lateral_accel = self.curvature_request_buffer[-delay_frames] * CS.vEgo ** 2
self.curvature_request_buffer.append(desired_curvature)
raw_lateral_jerk = np.clip((future_desired_lateral_accel - expected_lateral_accel) / max(lat_delay, self.dt), -2.5, 2.5)
desired_lateral_jerk = np.clip(self.jerk_filter.update(raw_lateral_jerk), -2.5, 2.5)   # LPF 1.2 Hz
setpoint = expected_lateral_accel + desired_lateral_jerk * lat_delay

measurement_rate = np.clip(self.measurement_rate_filter.update((measurement - self.previous_measurement)/self.dt), -2.5, 2.5)

low_speed_factor = (np.interp(CS.vEgo, LOW_SPEED_X, LOW_SPEED_Y) / max(CS.vEgo, MIN_SPEED)) ** 2
current_kp = np.interp(CS.vEgo, self.pid._k_p[0], self.pid._k_p[1])      # == SteerKP, flat
error = setpoint - measurement
error_with_lsf = error * (1 + low_speed_factor / max(current_kp, 1e-3))
pid_log.error = float(error_with_lsf)

roll_offset_fade  = np.interp(CS.vEgo, FF_ROLL_OFFSET_FADE_BP, FF_ROLL_OFFSET_FADE_V)   # [0.5,2.5]->[0,1]
roll_compensation = params.roll * ACCELERATION_DUE_TO_GRAVITY * roll_offset_fade
ff = future_desired_lateral_accel - roll_compensation
ff -= self.torque_params.latAccelOffset * roll_offset_fade
ff += friction_scale * get_friction(error_with_lsf + JERK_GAIN*friction_jerk, lateral_accel_deadzone,
                                    friction_threshold, self.torque_params)

# V293 takes the ELSE arm (accord_rate_plant_ff false):
output_lataccel = self.pid.update(pid_log.error, error_rate=-measurement_rate, speed=CS.vEgo,
                                  feedforward=ff, freeze_integrator=freeze_integrator)
output_torque = output_lataccel / latAccelFactor
return -output_torque, 0.0, pid_log
```

Constants: `LOW_SPEED_X = [0,10,20,30]`, `LOW_SPEED_Y = [12,10.5,8,5]`, `MIN_SPEED = 1.0`,
`MAX_LAT_JERK_UP = 2.5`, `LP_FILTER_CUTOFF_HZ = 1.2`, `JERK_GAIN = 0.22`,
`FF_ROLL_OFFSET_FADE_BP = [0.5, 2.5]`, `FF_ROLL_OFFSET_FADE_V = [0.0, 1.0]`,
`LAT_ACCEL_REQUEST_BUFFER_SECONDS = 1.0`, `VERSION = 2`.

PID limits are `+/- lateral_accel_from_torque(1.0) = +/- latAccelFactor`, so the sum clips at +/-6.0
lat accel and `output_torque` at +/-1.0. `update_limits()` is re-run on every
`update_live_torque_params` call. EVIDENCE.

**No Accord arm exists in the long per-vehicle output-scaling `elif` chain that follows**, so nothing
scales `output_torque` afterwards. EVIDENCE, read of the whole chain. The one reachable exception is
`elif flm_surface_active and self.flm_surface_profile_key and not CS.steeringPressed:`, and FLM is off.

`freeze_integrator = (steer_limited_by_safety or CS.steeringPressed or CS.vEgo < low_speed_reset_threshold
or unwind_detected)`, with `low_speed_reset_threshold = max(CP.minSteerSpeed, 0.3) = 0.3` m/s. Below that
the PID is also `reset()` every frame.

### Stage D - the car controller (`opendbc/car/honda/carcontroller.py`)

```python
torque_cmd = float(actuators.torque)
limited_torque = rate_limit(torque_cmd, self.last_torque, -3*DT_CTRL, 3*DT_CTRL)
self.last_torque = limited_torque
apply_torque = int(np.interp(-limited_torque * 4096, [-4096,0,4096], [-4096,0,4096]))
```

`rate_limit` is `np.clip(new, last+dw, last+up)`. The lookup is an **identity**, so it only clamps. The
**sign flip lives here**: `actuators.torque` is left-positive, `apply_torque` is right-positive.
`int()` truncates toward zero.

- `STEER_MAX = CP.lateralParams.torqueBP[-1] = 4096` (from `interface.py`, `[[0,4096],[0,4096]]`).
- `STEER_DELTA_UP = STEER_DELTA_DOWN = 3`, class-level in `values.py`, commented "for all Honda".
  **`+/-0.03 per frame = 122.88 counts/frame = 12288 counts/s; 0 to full scale in 0.333 s.**
- `STEER_DRIVER_ALLOWANCE` / `MULTIPLIER` / `FACTOR` **do not exist for Honda**. Honda does not call
  `apply_std_steer_torque_limits` or `apply_driver_steer_torque_limits`. The limiter is **not**
  driver-torque aware.
- `HondaFlags.EPS_MODIFIED` does **not** raise `torqueBP` on the Accord (unlike Civic/CRV), so
  `STEER_MAX` stays 4096 regardless. Under ForceTorqueController it is inert entirely.
- The fork's only insertion on this path is a speed/delta-scheduled LPF gated on `CAR.HONDA_CIVIC_BOSCH`,
  **dead for this car**. `mvl_accord_mode` is gated on `CAR.HONDA_ACCORD_11G`, the 2023-25 CAN-FD car,
  also dead. `starpilot_toggles` is passed into `CarController.update` and **never referenced in the
  body** - StarPilot toggles have zero effect on the Honda CAN TX stage.

### Stage E - the packer and the wire

```python
def create_steering_control(packer, CAN, apply_torque, lkas_active, tja_control):
  values = {"STEER_TORQUE": apply_torque if lkas_active else 0,
            "STEER_TORQUE_REQUEST": lkas_active}
  if tja_control: values["STEER_DOWN_TO_ZERO"] = lkas_active
  return packer.make_can_msg("STEERING_CONTROL", CAN.lkas, values)
```

`tja_control` is False for the Accord (`BOSCH_TJA_CONTROL` is Acura MDX only). DBC `BO_ 228
STEERING_CONTROL`, signal `STEER_TORQUE : 7|16@0-`, **signed big-endian, factor 1, offset 0**, so
**counts are 1:1** and full scale is +/-4096.

Byte census of the 5-byte frame as openpilot emits it:

| byte | contents |
|---|---|
| 0 | `STEER_TORQUE` high byte, two's complement |
| 1 | `STEER_TORQUE` low byte |
| 2 | `0x80` engaged / `0x00` not. bit1 `DRIVER_OVERRIDE` **never written -> always 0** |
| 3 | **always `0x00`.** bits 2-0 `CONTROL_STATE` **never written -> always 0** |
| 4 | CHECKSUM (auto) + COUNTER (auto) + `STEER_DOWN_TO_ZERO`=0 + `HAPTIC_WARNING`=0 |

This is the direct confirmation of the kit memory *"the override-taper ARM is a 0xE4 field openpilot
sends as 0"*. Nothing in this fork can set it without a code change. EVIDENCE.

**Panda safety enforces NO magnitude, rate, driver-allowance or RT-interval limit on 0xE4.** The entire
steer check in `opendbc/safety/modes/honda.h` is a block-when-not-allowed test on `data[0]|data[1]`.
Grep for `steer_torque_cmd_checks|SteeringLimits|max_steer|max_rate_up|driver_torque_allowance` over that
file returns zero hits. **The only ceilings are the `np.interp` clamp to +/-4096 and the EPS firmware
itself.** EVIDENCE.

### The rate limiter is inside a loop with the integrator

`controlsd.publish` sets
`self.steer_limited_by_safety = abs(CC.actuators.torque - CO.actuatorsOutput.torque) > 1e-2`,
and that flag is one of the `freeze_integrator` terms. EVIDENCE.

### Unit boundaries

`desiredCurvature` 1/m. `setpoint`, `measurement`, `error`, `p`, `i`, `d`, `f` all m/s^2.
`output_torque` / `actuators.torque` dimensionless in [-1,1]. `apply_torque` counts, +/-4096.

---

## 2. THE PLANT MODEL THE CONTROLLER ASSUMES

### Under V293 (rate-plant OFF): a static, speed-independent gain

`lat_accel = latAccelFactor * torque`, from `torque_from_lateral_accel_linear` in
`opendbc/car/interfaces.py`. **Honda does not override it** (grep of `honda/interface.py`). So
`SteerLatAccel = 6.0` IS the assumed plant gain, and it divides P, I and the feedforward **together** -
it is a single overall authority scalar, not a feedforward trim.

The clamp constant in `starpilot_variables.py` carries the fork's own measurement:

```python
# the plant's measured lat-accel-per-torque is 12-15 (IV at 0.2 s = 12-15, FIR DC 12.9,
# |P(0.1 Hz)| = 10.7 on one route), so the platform default of 1.689 is 6-7x below truth
LAT_ACCEL_FACTOR_MAX_MULT = 10.0
```

**If 12 to 15 still holds on V293, 6.0 is low by 2 to 2.5x, so the feedforward over-commands by that
factor and the integrator spends its range cancelling it.** Directly testable on the V293 drive.
EVIDENCE for the constant and the comment; BELIEF that 12-15 transfers to V293, since it was measured on
the previous firmware.

### The rate-servo model that V293 turns off

`selfdrive/controls/lib/latcontrol_vehicle_tunes.py`:

```python
HONDA_ACCORD_EPS_G_BP = [5.0, 12.5, 18.5, 28.5]        # m/s
HONDA_ACCORD_EPS_G_V  = [120.0, 95.0, 85.0, 70.0]      # deg/s per unit torque
HONDA_ACCORD_EPS_K_BP = [4.0, 8.0, 12.5, 18.5, 28.5]   # m/s
HONDA_ACCORD_EPS_K_V  = [0.17, 0.28, 0.35, 0.45, 0.50] # 1/s (return spring: rate per deg of angle)
HONDA_ACCORD_FF_RATE_GAIN = 0.5
HONDA_ACCORD_FF_RATE_RC   = 0.10    # s, first-order filter on d(angle_des)/dt
HONDA_ACCORD_FF_ANGLE_LIMIT_DEG = 400.0
HONDA_ACCORD_FF_MOVE_TORQUE_LIMIT_BP = [8.0, 10.0]     # m/s
HONDA_ACCORD_FF_MOVE_TORQUE_LIMIT_V  = [1.0, 1.4]
HONDA_ACCORD_TORQUE_KI = 0.30
```

```python
def get_honda_accord_rate_plant_ff(angle_des_deg, angle_des_rate_dps, v_ego, rate_gain=0.5,
                                   gain_scale=1.0, spring_scale=1.0):
  angle_des_deg = clip(angle_des_deg, -400, 400)
  gain   = interp(v_ego, G_BP, G_V) * max(gain_scale, 0.1)
  spring = interp(v_ego, K_BP, K_V) * spring_scale
  hold_torque = spring * angle_des_deg / gain
  move_limit  = interp(v_ego, [8.0, 10.0], [1.0, 1.4])
  move_torque = clip(rate_gain * angle_des_rate_dps / gain, -move_limit, move_limit)
  return hold_torque + move_torque
```

What it would have commanded, computed:

| v (m/s) | G (deg/s per torque) | k (1/s) | hold torque @10 deg | move torque @20 deg/s | move limit |
|---|---|---|---|---|---|
| 3 | 120.0 | 0.170 | 0.0142 | 0.0833 | 1.00 |
| 5 | 120.0 | 0.198 | 0.0165 | 0.0833 | 1.00 |
| 10 | 103.3 | 0.311 | 0.0301 | 0.0968 | 1.40 |
| 15 | 90.8 | 0.392 | 0.0431 | 0.1101 | 1.40 |
| 20 | 81.7 | 0.459 | 0.0562 | 0.1224 | 1.40 |
| 28.5 | 70.0 | 0.500 | 0.0714 | 0.1429 | 1.40 |

Note how small the hold torques are: 0.014 to 0.071 for a 10 deg wheel angle. Compare the generic
feedforward, which at 6.0 latAccelFactor commands `setpoint/6.0`, e.g. 0.167 torque for 1.0 m/s^2.
**That contrast is the fork's own "3-10x too much torque" claim.**

### The feedback measurement path

`VM.calc_curvature(sa, u, roll) = curvature_factor(u) * sa / sR + roll_compensation(roll, u)`,
`curvature_factor(u) = (1-chi)/(1-sf*u**2)/l`, `sf = calc_slip_factor(VM)`.
With the Accord's derived parameters (mass 1487.3 kg after `STD_CARGO_KG`, wheelbase 2.83,
centerToFront 1.104, tireStiffnessFactor 0.8467 through `scale_tire_stiffness`):
**`sf = -6.99987e-4`**, `curvature_factor` falls from 0.35311 at 1 m/s to 0.21678 at 30 m/s.

**There is no IMU term.** `actualLateralAccel` is derived from the steering angle alone.
`sR` is set per frame by `get_honda_accord_steer_ratio`, and **`liveParameters.steerRatio` is logged but
IGNORED** while `AccordVariableSteerRatio` is on. EVIDENCE.

The SR map (refit at this HEAD, 83 routes):

```python
HONDA_ACCORD_STEER_RATIO_ANGLE_BP = [0,23,31,61,76,95,116,151,178,227,236,303,380]   # deg
HONDA_ACCORD_STEER_RATIO_V = [16.88,16.88,16.88,16.25,15.97,15.45,15.03,14.68,14.45,14.09,14.25,12.98,12.31]
HONDA_ACCORD_STEER_RATIO_NOMINAL  = 16.88
HONDA_ACCORD_STEER_RATIO_LEVEL_MIN = 0.60   # toggle 10.13
HONDA_ACCORD_STEER_RATIO_LEVEL_MAX = 1.25   # toggle 21.10
ratio = interp(|steer_angle_deg|, BP, V);  if level: ratio *= clip(level/16.88, 0.60, 1.25)
```

**It is ANGLE-indexed, not speed-indexed.** With the stored `SteerRatio = 16.33` and `ForceAutoTuneOff`
forcing `use_custom_steerRatio` true, the level scale is `16.33/16.88 = 0.96742`, so the served curve is
16.330 on centre falling to 11.909 at 380 deg.

### The learner state - a correction to a belief I was handed

`torqued.py`: `self.use_params = CP.brand in ALLOWED_CARS and CP.lateralTuning.which() == 'torque'`, and
`ALLOWED_CARS = ['toyota', 'hyundai', 'rivian', 'honda']`. **honda IS in the list**, and lateralTuning is
`torque` under ForceTorqueController. **So `liveTorqueParameters.useParams` is TRUE on this car.**
EVIDENCE. (This contradicts a subagent BELIEF that torqued never validates; that belief confused
`useParams`, a static platform flag, with `liveValid`, the per-fit sanity flag.)

Consequently in `controlsd.get_torque_control_params`:

```python
keep_learned_offset = getattr(starpilot_toggles, "keep_learned_lat_accel_offset", True)
if use_live_params:
  if not use_custom_lat_accel or keep_learned_offset:
    lat_accel_offset = torque_params.latAccelOffsetFiltered      # <- TAKEN, every frame
  if not use_custom_lat_accel: lat_accel_factor = ...            # NOT taken (custom forced by ForceAutoTuneOff)
  if not use_custom_friction:  friction = ...                    # NOT taken
```

**`latAccelOffset` is LIVE and enters the V293 feedforward.** It starts at `0.0`
(`initial_params = {'latAccelFactor': offline, 'latAccelOffset': 0.0, 'frictionCoefficient': offline}`)
and the filter only moves inside `if self.filtered_points.is_valid():`. But it is restored at boot from
the cached `LiveTorqueParameters` blob when `cache_ltp.liveValid` and the restore key matches, **so it
can carry a value learned under an older firmware.** Read it off the wire at 4 Hz before assuming 0.
EVIDENCE for the plumbing, BELIEF for the practical value.

`paramsd.resolve_vehicle_model_params` returns `(starpilot_toggles.steerRatio, 1.0)` outright when
`force_auto_tune_off`, so `stiffnessFactor` is pinned at 1.0.

---

## 3. THE `f` FIELD - EXACT EXPRESSION AND WHY `f/D` READS 0.747 RISING WITH |D|

### `torqueState.f` is NOT computed from `desiredLateralAccel`. That is the whole discrepancy.

```python
future_desired_lateral_accel = desired_curvature * CS.vEgo ** 2        # the CURRENT command
setpoint = expected_lateral_accel + desired_lateral_jerk * lat_delay   # the 0.30 s DELAYED command + jerk lead
pid_log.desiredLateralAccel = float(setpoint)                          # <- the denominator you used
ff = future_desired_lateral_accel - roll_compensation                  # <- the numerator starts HERE
pid_log.f = float(self.pid.f)  ;  self.pid.f = feedforward = ff        # in the V293 else-arm
```

`f/desiredLateralAccel` is therefore `ff/setpoint`, and **`ff` never sees `setpoint`.** EVIDENCE.

### The exact formula under this config

```python
roll_offset_fade  = np.interp(vEgo, [0.5, 2.5], [0.0, 1.0])
ff = desiredCurvature * vEgo**2  -  roll * 9.81 * roll_offset_fade  -  latAccelOffset * roll_offset_fade
pid_log.f = float(ff)          # units: m/s^2 of lateral acceleration
```

Every other term in the chain is off for this car and config, verified by reading the whole chain:

| Term | Why it is zero or one |
|---|---|
| `ff_scale` | `use_bolt_ff_scaling` is Bolt only |
| the per-vehicle `elif` chain | has **no `HONDA_ACCORD` arm**; `is_civic_bosch_modified` is false |
| `get_honda_accord_ff_scale` turn taper | gated on `accord_turn_ff_taper`, which is **false** |
| FLM surface scaling | `flm_surface_active` false, no trial profile on the device |
| trailer scaling | `trailer_load_kg` is 0 |
| `get_friction` | `SteerFriction = 0.0` makes it interp between `+/- friction*latAccelFactor = +/-0` -> **exactly 0** |
| deadzone boost | `torque_deadzone_boost = kfDEPRECATED`, and `configure_torque_tune` calls `tune.init('torque')`, zeroing it |

**So `f` is the command minus a constant, with no gain applied.** No nonlinear map, no low-signal taper.
`f` is in lat-accel units, same as `p`, `i`, `desiredLateralAccel`. Only `output` is in torque units.

### This reproduces the reported numbers

A **constant additive subtraction** is exactly what makes a ratio rise with magnitude.
Fitting the reported bins to `f/D = 1 - C/|D|`:

| bin mid \|D\| | reported ratio | implied C (m/s^2) | equivalent road roll |
|---|---|---|---|
| 0.45 | 0.560 | 0.198 | 1.16 deg |
| 0.75 | 0.665 | 0.251 | 1.47 deg |
| 1.10 | 0.758 | 0.266 | 1.55 deg |
| 1.65 | 0.867 | 0.220 | 1.28 deg |

**C is constant at 0.234 +/- 0.03 m/s^2 across a 3.7x range of |D|.** A multiplicative gain would have
given a flat ratio. The subtracted term is ~0.23 m/s^2, equivalent to 1.37 deg of road roll.

### Sign and size of `latAccelOffset`, and where it comes from

- **Source**: `liveTorqueParameters.latAccelOffsetFiltered`, published at 4 Hz by `torqued.py`, taken
  every frame because `KeepLearnedLatAccelOffset = 1` AND `useParams` is true on honda.
- **Sign convention**: it is *subtracted* from `ff`, so a POSITIVE `latAccelOffset` REDUCES a
  right-positive command and INCREASES the magnitude of a left command. It is a **fixed-sign** bias,
  not sign-following.
- **Size**: filter initial value 0.0; only moves when the fit passes `filtered_points.is_valid()`;
  restored at boot from the `LiveTorqueParameters` cache if that cache was `liveValid`.
- **The comment in `torqued.get_msg` is explicit** that the toggles are NOT published here and that this
  same message is cached and restored as the filters' initial state next boot.

**Discriminator**: roll is sign-following on a banked road (camber into the turn), `latAccelOffset` is
fixed-sign. If the reported ratios were binned on `|D|` and are consistently below 1 in BOTH turn
directions, the term is ROLL. If the ratio is below 1 one way and above 1 the other, it is the OFFSET.

### How to reproduce 0.747 exactly from logged fields

Regress, on engaged frames only (`torqueState.active == True`):

```
torqueState.f  ~  controlsState.desiredCurvature * carState.vEgo**2
                + roll_offset_fade * liveParameters.roll
                + roll_offset_fade
```

The first coefficient must come out at **exactly 1.000**, the second at **-9.81**, and the third is
**`-latAccelOffset`**. If it does, the formula is confirmed and camber is separated from the learned
offset. Then read `liveTorqueParameters.latAccelOffsetFiltered` directly to close it.

### Which params move `f`

| Param | Effect on `f` |
|---|---|
| `KeepLearnedLatAccelOffset` | Set false -> `latAccelOffset` drops to 0.0, removing that part of C. **The only toggle that touches C.** |
| `SteerLatAccel` | **NONE.** It does not appear in `ff`. It divides `f` only later, at `output_torque = (p+i+d+f)/latAccelFactor`. |
| `SteerFriction` | None at 0.0. Above 0 it adds a sign-following term up to `+/- friction*latAccelFactor`. |
| `AccordTurnFFTaper` | Currently off. On, it multiplies `f` by `1 - 0.30*sigmoid((|setpoint|-0.45)/0.12)`, a genuine multiplicative taper - the ratio would FALL at high \|D\|, the opposite of what is seen. |
| `SteerDelay` | Moves `desiredLateralAccel` but NOT `f`, so it moves the ratio without touching the feedforward. |

Cross-checks available: `torqueState.actualLateralAccel == controlsState.curvature * vEgo**2` to machine
precision, and `carControl.actuators.curvature == controlsState.desiredCurvature`.

---

## 4. EVERYTHING THAT VARIES WITH SPEED

### The synthesis first: the angle-domain loop gain is FLAT

The V293 plant responds in the steering-angle domain, so that is the frame to judge the loop in.
Computed from the code with the real `VehicleModel` slip factor and the served steer ratio:

| v (m/s) | curvature_factor | low-speed factor | P effective | counts per deg of angle error | relative to 3 m/s |
|---|---|---|---|---|---|
| 1 | 0.35311 | 140.42 | 140.72 | 36.3 | 1.04 |
| 2 | 0.35237 | 34.22 | 34.52 | 35.5 | 1.02 |
| 3 | 0.35114 | 14.82 | 15.12 | 34.9 | 1.00 |
| 5 | 0.34728 | 5.06 | 5.36 | 34.0 | 0.97 |
| 7.5 | 0.33997 | 2.10 | 2.40 | 33.5 | 0.96 |
| 10 | 0.33024 | 1.10 | 1.40 | 33.8 | 0.97 |
| 15 | 0.30528 | 0.380 | 0.680 | 34.1 | 0.98 |
| 20 | 0.27606 | 0.160 | 0.460 | 37.1 | 1.06 |
| 25 | 0.24581 | 0.068 | 0.368 | 41.2 | 1.18 |
| 30 | 0.21678 | 0.028 | 0.328 | 46.7 | 1.34 |
| 35 | 0.19023 | 0.020 | 0.320 | 54.5 | 1.56 |

**`low_speed_factor` exists precisely to cancel the `v^2` in the error, and it does so almost
perfectly.** The P loop gain in the angle domain is 33 to 37 counts per degree from 1 m/s all the way to
20 m/s, rising only 1.34x by 30 m/s.

**That explains the observation directly. A 2 Hz ring at 0-5 m/s and an elevated 2 Hz line at 10-20 m/s
are the same instability, because the controller applies the same angle-domain gain at both.** There is
nothing speed-selective to blame. What changed is the plant.

Two consequences for tuning:

- **`SteerKP` cannot fix the low-speed ring.** At 3 m/s it contributes 0.3 of an effective 15.1, so
  driving it to its 3.0 ceiling moves the gain by 18%. Below ~7 m/s it is nearly inert.
- **`SteerLatAccel` scales the angle-domain loop gain uniformly at every speed**, because
  `output_torque = (p+i+d+f)/latAccelFactor` divides P, I and the feedforward together. Taking it from
  6.0 toward the 12-15 the fork's own comment records as measured would **halve the loop gain everywhere
  AND cut the feedforward over-command**, with one number.

**There is no derivative term to damp any of this.** `LatControlTorque.__init__` constructs
`PIDController([INTERP_SPEEDS, KP_INTERP], KI, rate=1/self.dt)` with no third positional argument, so
`k_d` defaults to `0.` and `_k_d` is assigned **nowhere** outside `common/pid.py`. `self.d = self.k_d *
error_rate` is identically zero, and `torqueState.d` is always 0.0. With a plant that integrates torque
into angle, a P-only loop has only the plant's own damping for phase margin. EVIDENCE, both files read.

### Live and speed-dependent

1. **`kappa` to lat-accel, both directions, goes as `v^2`.** `measurement = measured_curvature*vEgo**2`,
   `future_desired_lateral_accel = desired_curvature*vEgo**2`.
2. **`low_speed_factor`** `= (interp(vEgo,[0,10,20,30],[12,10.5,8,5]) / max(vEgo,1.0))**2`. The dominant
   term, and **hard-coded**.
3. **`roll_offset_fade`** `= interp(vEgo,[0.5,2.5],[0,1])`. Kills roll compensation and the learned
   offset below 2.5 m/s.
4. **`VM.curvature_factor(u)`** `= (1-chi)/(1-sf*u**2)/l`, `sf = -6.99987e-4`. Understeer. Falls 39% from
   1 to 30 m/s and sits in **both** the measurement and `get_steer_from_curvature`.
5. **`clip_curvature`**: `max_curvature_rate = 5.0*jerk_factor/v**2` and the ceiling
   `(+/-3.0 + roll*g)/v**2`, both `1/v^2`, plus the hard `MAX_CURVATURE = 0.2`:

   | v (m/s) | max dK/dt (1/m/s) | = deg/s of wheel | K ceiling | = deg ceiling |
   |---|---|---|---|---|
   | 1 | 5.0000 | 13248.6 | 0.20000 | 529.9 |
   | 3 | 0.5556 | 1480.3 | 0.20000 | 532.9 |
   | 5 | 0.2000 | 538.8 | 0.12000 | 323.3 |
   | 10 | 0.0500 | 141.7 | 0.03000 | 85.0 |
   | 20 | 0.0125 | 42.4 | 0.00750 | 25.4 |
   | 30 | 0.0056 | 24.0 | 0.00333 | 14.4 |

   **It is completely non-binding at low speed.** Nothing upstream smooths the command at 0-5 m/s.
6. **`expected_lateral_accel = curvature_request_buffer[-30] * vEgo**2`** replays a buffered *curvature*
   at the *current* `v^2`, so the delayed reference is speed-coupled even at constant curvature. This is
   deliberate; the code comment explains it.
7. **`low_speed_reset_threshold = max(CP.minSteerSpeed, 0.3) = 0.3 m/s`.** Below it the PID is reset
   every frame and the integrator frozen.
8. **`sat_check_min_speed = 10.0`**, so `torqueState.saturated` cannot trip below 10 m/s.
9. **`standstill` gate**: `abs(vEgo) <= max(minSteerSpeed, 0.3) or CS.standstill` drops `latActive`.
10. **The fork's turn-hold and turn-lead blocks** in `Controls.state_control`, gated by
    `CURVATURE_HOLD_RELEASE_SPEED`, `CURVATURE_HOLD_HARD_SPEED`, `CURVATURE_HOLD_PLAN_SOURCE_SPEED`,
    `TURN_LEAD_MIN_SPEED`, `TURN_LEAD_MAX_SPEED`, `TURN_LEAD_FULL_SPEED`. These live in the 0-5 m/s band
    and can override `new_desired_curvature`, **but only while a blinker is on.** Gate any low-speed
    analysis on `leftBlinker or rightBlinker` to separate them.

### Speed-dependent but INERT in this config

11. `get_center_chatter_friction_jerk_deadzone`, speed BP `[0,5,12,25]` -> `[0.08,0.12,0.18,0.18]` times a
    lat-accel weight `[0,0.18,0.35]` -> `[1,1,0]`. Feeds friction only.
12. `get_standard_friction_threshold(vEgo) = max(_gm_base_friction_threshold_default(vEgo), 0.30)`.
    Feeds friction only.
13. `lateral_accel_deadzone`, zero because `steeringAngleDeadzoneDeg` is 0 from `configure_torque_tune`.
14. `HONDA_ACCORD_EPS_G_BP`, `EPS_K_BP`, `get_honda_accord_ff_move_torque_limit` BP `[8,10]`.
    Rate-plant only, and rate-plant is off.
15. `measurement_rate`, filtered at 2.0 Hz and clipped +/-2.5. Feeds `d`, which is zero.

### Explicitly NOT speed-dependent

16. **The steer-ratio map is ANGLE-indexed.** `get_honda_accord_steer_ratio(steer_angle_deg, level)`
    interpolates on `|steer_angle_deg|` only.
17. **`current_kp` is FLAT.** `controlsd.update` overwrites `pid._k_p` every tick with
    `[[0],[SteerKP]]`, so `KP_INTERP = [250,120,65,30,11.5,5.5,3.5,2.0,0.6]` is **dead code**.
18. **The lag compensation is ONE SCALAR.** `lat_delay = liveDelay.lateralDelay + LAT_SMOOTH_SECONDS`,
    and `get_control_lateral_smooth_seconds` returns the constant 0.1 for every brand except rivian and
    subaru. With `UseAutoSteerDelay` false, `liveDelay.lateralDelay` is pinned to `SteerDelay = 0.2`.
    **Total 0.30 s at every speed. The measured 0.15-0.25 s speed-dependent lag cannot be tracked
    without code.**
19. **The Honda rate limiter has NO speed term.** `STEER_DELTA_UP = STEER_DELTA_DOWN = 3`, class-level,
    "for all Honda": `+/-0.03/frame`, 122.88 counts/frame, 0 to full in 0.333 s. `STEER_MAX = 4096`, flat.
20. The `raw_lateral_jerk` clip at `+/-2.5 m/s^3` has no speed term, though it acts on a `v^2`-scaled
    quantity.
21. **Panda safety imposes no magnitude, rate or driver-torque limit on 0xE4 at all.**

### One structural note on the 2 Hz

`setpoint = expected + LPF_{1.2Hz}(future - expected)` is a **complementary filter**. At DC the setpoint
equals the current command; **above ~1.2 Hz it reverts to the 0.30 s delayed command.** So near 2 Hz the
*reference* carries a full 0.30 s of delay. That is a reference-path delay, not a feedback-path one, so
it does not by itself close an unstable loop, but the controller's target at 2 Hz is a third of a second
stale while the P term chases it at ~35 counts/deg with no derivative.

To test: compare `torqueState.desiredLateralAccel` against `controlsState.desiredCurvature * vEgo**2` in
the 1-4 Hz band and look for the phase split.

---

## 5. THE PARAM SURFACE

Storage is the **literal ASCII of the value**. `SteerKP = 0.3` is stored as `"0.3"`, not `"30"`.
EVIDENCE: `get_value` uses `self.params.get(key)` then `cast`, and the operator's decoded backups show
plain floats. The only `conversion=` multipliers on the lateral side are for `TrailerLoad` and the
`ReduceLateralAcceleration*` percent keys.

**`params_keys.h` field layout**: `{"Key", {FLAGS, TYPE, default_value, stock_value, tuning_level, tier}}`.

The V293 file is a **10-key delta** on top of the 2026-09-10 backup. Effective config, with the inherited
keys that also matter:

| Key | Declared default | V293 effective | Code clamp | Read cadence |
|---|---|---|---|---|
| `AccordRatePlantFF` | `"1"` (TRUE) | **false** | bool | every frame |
| `SteerKP` | `"0.0"` -> platform 0.6 | **0.3** | `STEER_KP_MIN 0.05` .. `0.6*STEER_KP_MAX_MULT(5.0) = 3.0` | **every 100 Hz tick**, overwrites `pid._k_p` |
| `AccordTorqueKi` | `"0.30"` | **0.15** | 0.05 .. 1.0 | every frame, `pid._k_i` rewritten |
| `SteerFriction` | platform 0.21205 | **0.0** | 0 .. 1 | every frame |
| `SteerLatAccel` | platform 1.68933 | **6.0** | `LAF*0.5 = 0.845` .. `LAF*10.0 = 16.893` | every frame |
| `ForceAutoTuneOff` | `"1"` | **true** | forces `use_custom_*` TRUE regardless of value equality | live |
| `ForceAutoTune` | `"0"` | **false** | gated on `not has_auto_tune` | live |
| `AdvancedLateralTune` | `"1"` | **true** | master gate on Delay/Friction/KP/LatAccel/Ratio | live |
| `KeepLearnedLatAccelOffset` | `"1"` | **true** | - | every frame |
| `AccordTurnFFTaper` | `"0"` | **false** | bool | every frame |
| `SteerDelay` *(inherited)* | stock 0.3 | **0.2** | 0.01 .. 1.0 | via `liveDelay`, 4 Hz |
| `UseAutoSteerDelay` *(inherited)* | `"1"` | **false** | - | forces the custom delay |
| `SteerRatio` *(inherited)* | 16.33 | **16.33** | `sr*0.5 .. sr*1.5`, then the Accord map clamps to **10.13 .. 21.10** | every frame |
| `AccordVariableSteerRatio` | `"1"` | **true** | - | every frame |
| `AccordFFRateGain` | `"0.5"` | 0.5 | 0.0 .. 1.5 | **INERT** (rate-plant off) |
| `AccordEpsGainScale` | `"1.0"` | 1.0 | 0.5 .. 2.0 | **INERT** |
| `AccordEpsSpringScale` | `"1.0"` | 1.0 | 0.0 .. 2.0 | **INERT** |

All seven `Accord*` keys are declared in `common/params_keys.h` at tuning level 2 with
`SETTINGS_SIMPLE`, so `known(...)` is true and the V293 delta's values do take effect. **Verified
directly** - this matters, because an unknown key would have silently kept `AccordRatePlantFF` at its
`True` default.

### Precedence traps

- **`ForceAutoTuneOff = 1` forces `use_custom_*` TRUE even when the value equals stock.** Python
  precedence: `bool(a != b) and C and not D or E` parses as `((a!=b) and C and not D) or E`, with
  `E = force_auto_tune_off`. Same shape for friction, latAccelFactor and steerRatio. Verified.
- `use_custom_steerActuatorDelay = advanced_lateral_tuning and not use_auto_steer_delay`. It does **not**
  depend on whether `SteerDelay` differs from stock.
- `SteerRatio` is clamped twice, and the Accord map's `[0.60, 1.25]` is the tighter one on the high side:
  the UI offers up to 24.495 but the map caps the effect at 21.10.

### Latched (need a reboot)

`ForceTorqueController`, `NNFF`, `NNFFLite`, `AlwaysOnLateral`. Everything else takes effect on the next
toggle broadcast (~1 Hz, background thread in `starpilot_process.py` triggered by
`StarPilotTogglesUpdated`).

### Dead toggles

- **`SteerOffset` / `SteerOffsetStock`** - declared, but appear ONLY in `params_keys.h` and in three list
  literals in `the_galaxy.py`. **No runtime consumer. Setting it does nothing.**
- `HondaLateralPidKpScale` / `KiScale` - require `lateralTuning == "pid"`; inert under
  ForceTorqueController.
- `LatSmoothSeconds` - `_model_smooth_seconds` returns the default unless `DeveloperUI` is on, and the
  operator has it off.
- `ReduceLateralAcceleration{Rain,RainStorm,Snow,LowVisibility}` - read into toggle attributes with no
  consumer found outside `starpilot_variables.py`.

### Resulting gains under the V293 config

| v (m/s) | low-speed factor | P effective | torque per m/s^2 of TRUE error | counts per m/s^2 |
|---|---|---|---|---|
| 3 | 14.82 | 15.12 | 2.520 | 10324 |
| 5 | 5.06 | 5.36 | 0.894 | 3661 |
| 10 | 1.10 | 1.40 | 0.234 | 957 |
| 20 | 0.16 | 0.46 | 0.077 | 314 |
| 30 | 0.028 | 0.328 | 0.055 | 224 |

Feedforward static gain is `1/6.0 = 0.167` torque per m/s^2, i.e. **683 counts per m/s^2, at every
speed**. Integrator: `i += 0.15 * 0.01 * error_with_lsf` per frame in lat-accel space.

---

## 6. WHAT THE CONTROLLER CANNOT EXPRESS TODAY

### Expressible with existing params (a delta `.json` suffices)

- Overall torque authority, via **`SteerLatAccel`**, 0.845 to 16.893. The single knob for the static
  torque-to-lat-accel gain; moves P, I and feedforward together; **scales the angle-domain loop gain
  uniformly at every speed.**
- High-speed P, via **`SteerKP`**, 0.05 to 3.0 (~9x span at 30 m/s, ~18% at 3 m/s).
- Integral, via **`AccordTorqueKi`**, 0.05 to 1.0.
- A fixed scalar lookahead, via **`SteerDelay`**, 0.01 to 1.0.
- A 30% sharp-turn feedforward cut, via **`AccordTurnFFTaper`**. **Note the capability change**: under
  rate-plant FF this taper cancelled out, because `friction_torque = torque_from_lateral_accel(ff -
  ff_before_friction)` removed it. **With rate-plant OFF it multiplies the live feedforward.** It is a
  usable lever again: sigmoid onset at 0.45 m/s^2, width 0.12.
- Curvature-measurement level, via **`SteerRatio`**, effective 10.13 to 21.10.
- Friction compensation, via **`SteerFriction`**, 0 to 1.

### Needs code

- **A speed-dependent torque-to-lat-accel gain.** Verified three ways: (a) no lateral key in
  `params_keys.h` is JSON-typed except the FLM set; (b) `starpilot_variables.py` builds exactly ONE
  list-valued toggle, `steerKp`, and it is a single knot at speed 0 so it is flat; (c) no `interp` on
  `vEgo` in the lateral files takes a toggle value. **`SteerLatAccel` is one scalar.**
- **A speed-dependent delay.** One scalar, and Honda's `lat_smooth_seconds` is a constant 0.1. The
  measured 0.15 s motorway / 0.25 s at 3-8 m/s cannot be tracked.
- **Low-speed P authority.** Governed by the hard-coded `LOW_SPEED_Y = [12,10.5,8,5]`. `SteerKP` is
  effectively a highway-only knob.
- **Any derivative or damping term.** `k_d` is structurally 0.
- Restoring the `KP_INTERP` schedule; reshaping the turn-taper onset/width, `FF_ROLL_OFFSET_FADE_BP`,
  the jerk deadzones, `MAX_LAT_JERK_UP`, `JERK_GAIN`, `LP_FILTER_CUTOFF_HZ`, `JERK_LOOKAHEAD_SECONDS`.
- Anything touching the rate-plant tables' SHAPE (only their scale is exposed, and only when rate-plant
  FF is on).

### One partial exception: `FLMActiveOverrides`

The **only** JSON lateral-tuning key (`{PERSISTENT, JSON, "{}", "{}", 2}`). It carries 5-knot speed
tables at `FLM_FRICTION_SPEED_KNOTS = [0, 5, 10, 15, 25]` m/s for the base friction threshold
(`_flm_base_friction_threshold`), a speed-banded centre deadband, curvy-speed weights, and a
`low_speed_angle_assist_max_torque` that acts AFTER the PID.

**Reachable on the Accord**: `get_flm_surface_profile_key` finds no rich profile
(`FLM_RICH_PROFILE_CARS` is Bolt/Ioniq6/EV6/Prius/Camry) and falls through to
`FLM_UNIVERSAL_PROFILE_KEY = "torque_universal"`.
**Gate**: `FLMTrialApplied` AND `FLMActiveProfileId` AND `flm_runtime_overrides_active()`. **None of
those three keys appear in ANY of the operator's backups**, so FLM has never been used on this car.
It is a JSON blob rather than a slider, and **it does not reach the feedforward gain itself.**

---

## 7. WHAT THE RLOG CARRIES

`controlsState.lateralControlState.torqueState` (`controlsState @7`, 100 Hz) and
`starpilotLateralState @137` (100 Hz), published in the **same `Controls.publish` call**, so they align
index-for-index. Decimation in `services.py` is **qlog-only**: `loggerd.cc` writes every message of a
`should_log` service to the rlog at full rate.

| Field | Expression | Trap |
|---|---|---|
| `active` | True only in the active branch | **Gate everything on this.** Inactive frames leave every other field at capnp defaults. |
| `error` | `error_with_lsf` | Inflated by `1 + lowSpeedFactor/SteerKP`. At 5 m/s with SteerKP 0.3 that is **x17.9**. Not a physical error. |
| `p` | `SteerKP * error` | `p/error` reads `SteerKP` exactly. Attribution channel. |
| `i` | integral of `0.15*0.01*error` | m/s^2. Frozen on safety-limit / steeringPressed / v<0.3 / unwind. `*0.8` on steering release. |
| `d` | `k_d * error_rate` | **ALWAYS 0.0.** |
| `errorRate` | never assigned | **ALWAYS 0.0.** |
| `f` | `ff`, see section 3 | lat-accel units. Under V293 equals `starpilotLateralState.feedforward`. |
| `output` | `-output_torque`, [-1,1] | Equals `carControl.actuators.torque` exactly, same frame. |
| `actualLateralAccel` | `measurement` | From steering ANGLE through the variable-SR map, **not the IMU**. |
| `desiredLateralAccel` | `setpoint` | **Delayed 0.30 s plus a jerk lead. NOT the raw command.** |
| `desiredLateralJerk` | LPF 1.2 Hz, clipped +/-2.5 | m/s^3 |
| `saturated` | latched via `_check_saturation` | Trips only past `steerLimitTimer = 0.8 s`, above 10 m/s, hands off. **Not an instantaneous rail flag.** |
| `version` | `2` | **2 = `LatControlTorque`. 0 = `LatControlNNFF`, where `error` is in torque space and this table is WRONG.** |

`starpilotLateralState` fields: `active`, `frictionThreshold`, `frictionScale`, `feedforward`,
`frictionJerk`, `frictionJerkDeadzone`, `lowSpeedFactor`, `unwindDetected`. **`lowSpeedFactor` is what
un-inflates `error`.**

Torque on the wire: `carControl.actuators.torque` pre-limiter, `carOutput.actuatorsOutput.torque`
post-limiter, `carOutput.actuatorsOutput.torqueOutputCan` as counts. **Use the post-limiter value for
plant identification** - the +/-122.88 counts/frame slew is a live nonlinearity, and `torqued.handle_log`
itself uses `-msg.actuatorsOutput.torque`. `torqueOutputCan` is computed BEFORE the `latActive` gate, so
it disagrees with the wire while disengaged. The raw 0xE4 frame is in `sendcan`.

`carControl.actuators.steeringAngleDeg` is **always 0.0** on this car (`lateral_output = 0.0`).
`actuators.lateralControlMode` is Rivian-only, always `inactive`.

### Decoder hazard

The kit's `epsTelemetry` and this fork's `starpilotLateralState` share **both** slot `@137` **and** capnp
type id `@0xc2243c65e0340384`. A kit decoder reading a fork rlog silently mis-decodes, reporting
`engageSmCut` true on 100% of engaged frames and every byte probe 0. Use the fork's own `cereal/`, or the
verbatim copy at `rlog-tools/_scratch/spcereal/`.

### Attribution channels

`initData.params` (the whole Params store at segment start, ground truth for every toggle),
`initData.gitCommit/gitBranch/gitRemote`, `starpilotPlan.starpilotToggles` (plain JSON, ~1 Hz, empty
string on non-broadcast frames), `carParams @69` (every 50 s), `liveTorqueParameters @94` (4 Hz),
`liveDelay @146` (4 Hz), `liveParameters @61` (20 Hz).

---

## 8. LOOSE ENDS

1. **The operator's stored `SteerKP` was 0.9 before the delta**, which was exactly the ceiling under the
   old `STEER_KP_MAX_MULT = 1.5` (`0.6 * 1.5 = 0.9`). That mult is now 5.0. **0.9 may have been a clamp
   artefact rather than a chosen value**, and the V293 delta's 0.3 is a real choice against a ceiling
   of 3.0.
2. **`latAccelOffset` may be a stale cached value** learned under an older firmware. Read
   `liveTorqueParameters.latAccelOffsetFiltered` off the V293 rlog before assuming 0.
3. The Civic interface carries the comment *"max request allowed is 4096, but request is capped at 3840
   in firmware"*. Whether the 2020 Accord's EPS clamps below 4096, and what V293's torque map does at the
   top of the range, is a firmware question for the kit's own rail measurements (memory: rail 2461), not
   this file tree. **Not verified here. BELIEF.**
