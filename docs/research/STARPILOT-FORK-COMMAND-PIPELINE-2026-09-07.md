# StarPilot fork — lateral command pipeline trace (Accord, Dom branch)

Date: 2026-09-07. HEAD at trace time: `0f98d8c75` "Accord: apply the learned latAccelOffset in the
rate-plant path, harden safe mode and params rebuild". Fork root:
`C:\Users\dudei\Desktop\Projects\openpilots\raayyymond-StarPilot\StarPilot`. Read-only trace, no
edits made.

All claims below are EVIDENCE with a file:function/line cite unless marked BELIEF.

## 1. Rates and where each stage runs

| Stage | Rate | Evidence |
|---|---|---|
| modeld (vision model, produces `modelV2.action.desiredCurvature`) | 20 Hz | `selfdrive/modeld/constants.py:16` `MODEL_FREQ = 20` |
| controlsd main loop (`Controls.run`) | 100 Hz | `selfdrive/controls/controlsd.py:947` `Ratekeeper(100, ...)` |
| `state_control()` reads `modelV2` via `SubMaster` | latest-value, no interpolation | `selfdrive/controls/controlsd.py:511,600` — `self.sm['modelV2']`; SubMaster returns the last received message, it does not interpolate between publishes |
| `lateralManeuverPlan` (an alternate curvature source at controlsd.py:597-598) | test/maneuver-only, not live | `selfdrive/selfdrived/selfdrived.py:196` lists it in `ignore` (avg-freq/valid checks skipped) and ties it to `StarPilotEventName.lateralManeuver` at `selfdrived.py:388-390` — a maneuver-test event, not the normal driving path. In normal driving `self.sm.valid['lateralManeuverPlan']` is False, so controlsd falls to `model_v2.action.desiredCurvature` (controlsd.py:600) |
| `clip_curvature` (ISO jerk/accel clamp on the curvature actually used) | every 100 Hz frame | `selfdrive/controls/controlsd.py:803` calls `selfdrive/controls/lib/drive_helpers.py:25` `clip_curvature`, run unconditionally each controlsd tick regardless of whether modelV2 updated that tick |
| `LatControlTorque.update()` (PID + Accord rate-plant FF) | 100 Hz | called every `state_control()` at controlsd.py:809, `dt = DT_CTRL = 0.01` |
| `CarController.update()` (Honda), packs `STEERING_CONTROL` (0xE4) | 100 Hz (one call, one steering CAN frame, every update) | `opendbc_repo/opendbc/car/honda/carcontroller.py:377` `can_sends.append(hondacan.create_steering_control(...))` runs unconditionally on every `update()` call, no `frame % N` gate |

**Consequence, EVIDENCE:** `modelV2.action.desiredCurvature` is a genuine 20 Hz staircase at its
source (held constant for ~5 controlsd ticks between modeld publishes, `MODEL_FREQ=20` vs
controlsd's 100 Hz). But that raw staircase is NOT what reaches the PID or the CAN bus directly —
see §2.

## 2. What already smooths the command on this fork (contradicts "nothing smooths it")

> 🛑🛑 **STAGE 1 BELOW IS FALSIFIED IN PRACTICE — flag added 2026-09-10 by subagent `modelrate`.**
> `clip_curvature`'s **binding fraction is 0.000** in every route × stratum of six routes spanning
> V112 → V289 (r22, r35, r39, r5e_v288, r62_v289, r63_v289), engaged, v<12 and v≥12 alike — measured
> by direct equality of `|Δ desiredCurvature|` against its own bound
> `MAX_LATERAL_JERK · jerk_factor / v_ego² · DT_CTRL`, on `controlsState.desiredCurvature` logged at
> 100 Hz. **It only removes the staircase discontinuity when it BINDS, and on this record it never
> does.** `controlsState.desiredCurvature` is bit-identical to the latest
> `modelV2.action.desiredCurvature` on **60–71 % of engaged ticks at v < 12 m/s**, and the plan is a
> **pure ZOH** (rms in-hold deviation exactly 0.000e+00 on all six routes). **The raw 20 Hz staircase
> reaches the PID undigested, and it puts a phase-locked 20 Hz comb on the 0xE4 wire on every build.**
> Evidence and consequences: `rlog-tools/studies/grind/MODELD-CADENCE-VS-RING-2026-09-10.md` §2, §3, §5′.
> ⚠ At least two orchestrator briefs inherited the claim below; the *code read* is correct, the
> *operational consequence* is not. Stages 2 and 3 are untouched by this flag.

Three independent smoothing/shaping stages sit between the 20 Hz model staircase and the CAN frame,
all present today on `main`/Dom:

1. **`clip_curvature` — an ISO lateral-jerk slew limiter, run every 100 Hz tick.** 🛑 *See the flag
   above: measured binding fraction 0.000; the smoothing claimed here does not occur in practice.*
   `selfdrive/controls/lib/drive_helpers.py:25-51`. `max_curvature_rate = MAX_LATERAL_JERK
   (5.0 m/s^3) * jerk_factor / v_ego**2`; `new_curvature` is clamped to
   `prev_curvature ± max_curvature_rate * DT_CTRL` every frame (`controlsd.py:803`,
   `self.desired_curvature` is fed forward frame-to-frame as `prev_curvature`). This runs whether
   or not modelV2 published that tick, so the value the PID sees ramps continuously at 100 Hz
   between the 20 Hz plan updates — it is not a literal LPF (constant-slope ramp, not exponential),
   but it removes the raw staircase discontinuity before the PID ever sees it.
   🛑 **FALSIFIED IN PRACTICE 2026-09-10 — binding fraction 0.000, the clamp never engages, the plan
   is a pure ZOH and the staircase survives to the PID intact. See the flag at the head of §2.**
2. **`jerk_filter` — a true first-order LPF on the desired lateral jerk, inside `LatControlTorque`.**
   `selfdrive/controls/lib/latcontrol_torque.py:90` `FirstOrderFilter(0.0, 1/(2*pi*1.2), dt)`
   (1.2 Hz cutoff), applied at `latcontrol_torque.py:282` to `raw_lateral_jerk` before it is used to
   build `setpoint` (`latcontrol_torque.py:284`: `setpoint = expected_lateral_accel +
   desired_lateral_jerk * lat_delay`). `expected_lateral_accel` itself is the delayed
   `curvature_request_buffer` sample (`latcontrol_torque.py:277`) of the ALREADY-slewed
   `desired_curvature` from §1's clip_curvature, not the raw model value — so the setpoint the PID
   tracks has already passed through one slew limiter and one 1.2 Hz LPF.
3. **Accord-specific: `accord_angle_des_rate_filter` — a first-order LPF on the rate-plant
   feedforward's derivative term.** `latcontrol_torque.py:156,581` `FirstOrderFilter(0.0,
   HONDA_ACCORD_FF_RATE_RC, dt)`, `HONDA_ACCORD_FF_RATE_RC = 0.10` s
   (`selfdrive/controls/lib/latcontrol_vehicle_tunes.py:113`) — filters `d(angle_des)/dt` before it
   becomes the feedforward "move" torque term (`latcontrol_vehicle_tunes.py:2193-2212`,
   `get_honda_accord_rate_plant_ff`).

**BELIEF:** these three stages together likely round off most of the energy at 20-25 Hz that a raw
20 Hz staircase would otherwise inject, but this trace did not simulate/measure the resulting
spectrum — that would need offline replay of a route through this exact code path, not just a code
read.

## 3. What is NOT filtered

- **The PID `setpoint` itself has no direct LPF** — only its jerk *component* is filtered (§2.2);
  the `expected_lateral_accel` term is a raw (delayed) buffer sample of the already-slewed
  curvature, so any residual discreteness in `desired_curvature` reaches `error` unfiltered except
  via clip_curvature's slew.
- **The final `output_torque` (P+I+FF combined) is not low-pass filtered** for the Accord.
  `latcontrol_torque.py:597-598` (`is_honda_accord` branch) computes `output_lataccel` from
  `self.pid.update(...)` and converts straight to `output_torque` with no filter call afterward,
  before returning `-output_torque` (`latcontrol_torque.py:748`).
- **`carcontroller.py`'s Honda path has exactly one command LPF, and it is scoped to a different
  car/mode, not the Accord.** `get_civic_bosch_modified_torque_lpf_tau`
  (`opendbc_repo/opendbc/car/honda/carcontroller.py:27-66`) computes a variable time-constant LPF
  applied at `carcontroller.py:294-298` (`self.torque_lpf = alpha*torque_cmd + (1-alpha)*self.torque_lpf`)
  — but only when `self._modified_civic_standard_active()` is true
  (`carcontroller.py:252-253`: `CP.carFingerprint == CAR.HONDA_CIVIC_BOSCH and
  HondaFlags.EPS_MODIFIED`). For the Accord (`CAR.HONDA_ACCORD`) this branch is never entered
  (`carcontroller.py:286`: `if self._modified_civic_standard_active(): ...`), so `torque_cmd` passes
  through unfiltered into the rate limiter next.
- **The rate limiter downstream of all of this is a hard slew clamp, not an LPF.**
  `carcontroller.py:306` `rate_limit(torque_cmd, self.last_torque, -STEER_DELTA_DOWN*DT_CTRL,
  STEER_DELTA_UP*DT_CTRL)`; `STEER_DELTA_UP = STEER_DELTA_DOWN = 3`
  (`opendbc_repo/opendbc/car/honda/values.py:39-40`, comment "min/max in 0.33s for all Honda" — full
  range in ~0.33 s at 100 Hz). `rate_limit` (`opendbc_repo/opendbc/car/__init__.py:95-96`) is a pure
  `np.clip` on the delta — no memory of shape, just a slope cap. It does not decay or integrate, so
  it cannot itself "freeze an integrator" the way an IIR LPF's internal state could.

**EVIDENCE, direct answer to the "LPF freezes the integrator" claim as it applies to THIS fork:**
there is no output-command LPF in the Accord's path in `carcontroller.py` today (the only such LPF
gates on Civic Bosch Modified, `carcontroller.py:286`), so the specific claimed interaction — an
output-side LPF in `carcontroller.py` masking/freezing the PID integrator via `freeze_integrator` —
does not apply to the Accord as currently built on this branch. The claim may describe a different
fork/version, a hypothetical the observer is proposing, or the Civic path (misattributed to Honda in
general). The Accord's `freeze_integrator` conditions are unrelated to any LPF:
`latcontrol_torque.py:557-558` — `steer_limited_by_safety or CS.steeringPressed or CS.vEgo <
low_speed_reset_threshold or unwind_detected`.

## 4. `SteerDelay`, `SteerKP` and other Steer* toggles on this fork

- **`SteerKP`** overwrites the PID's Kp table on EVERY controlsd frame, unconditionally, for any
  non-`pid`-tuning car: `selfdrive/controls/controlsd.py:449-450`
  ```
  if hasattr(self.LaC, "pid") and self.CP.lateralTuning.which() != "pid":
      self.LaC.pid._k_p = self.starpilot_toggles.steerKp
  ```
  Default value is the stock car's own Kp (`starpilot/common/starpilot_variables.py:704`
  `steerKp = KP` where `KP` is `CP.lateralTuning.torque.kp`-derived — for the torque controller this
  is the module-level `KP = 0.6` constant in `latcontrol_torque.py:28`, matching the kit's memory
  that measured kp flat at 0.6 on all routes). This corroborates the EPS-kit memory
  (`accord-honda-kp-ki-scale-never-acted-kp-is-0600-on-all-60-routes.md`) directly at the code level:
  the toggle always wins and the platform-file Kp never survives past frame 1 unless the toggle is
  set to match it.
- **`SteerDelay`** feeds `steerActuatorDelay` (`starpilot_variables.py:774`), which becomes
  `lat_delay` in controlsd (`controlsd.py:806`: `lat_delay = self.sm["liveDelay"].lateralDelay +
  lat_smooth_seconds`) — it sets the buffer lookback (`delay_frames`,
  `latcontrol_torque.py:276-277`) used to align `expected_lateral_accel` with the plant's actual
  response lag, and separately scales the jerk-to-setpoint term (`setpoint = expected_lateral_accel
  + desired_lateral_jerk * lat_delay`, `latcontrol_torque.py:284`). It is a delay/lead-compensation
  parameter, not a smoothing knob — larger `SteerDelay` shifts the setpoint further ahead in time
  via the jerk term, it does not lower-pass anything.
- **Other Steer* toggles** (`SteerFriction`, `SteerLatAccel`, `SteerRatio`) feed
  `get_torque_control_params` (`controlsd.py:353-380`) → `latAccelFactor`/`friction` in the torque
  tune, or the Accord's variable-ratio rack level (`controlsd.py:481-491`,
  `get_honda_accord_steer_ratio`). None of them touch filtering.

## 5. Diagram — target → PID → apply_torque → 0xE4

```
modeld @ 20 Hz
  └─ modelV2.action.desiredCurvature  (raw 20 Hz staircase)
       │
       ▼  [controlsd @ 100 Hz, state_control()]
new_desired_curvature  (turn-hold / turn-lead / lane-centering shaping — controlsd.py:600-757,
                        BELIEVED not relevant to steady-state grind, not traced here)
       │
       ▼
clip_curvature()  ── ISO jerk slew limiter, 5 m/s^3, runs every 100 Hz tick regardless of
       │              modelV2 update cadence — drive_helpers.py:25, controlsd.py:803
       ▼
self.desired_curvature  (continuously-ramping curvature, no more raw staircase)
       │
       ▼  [LatControlTorque.update(), latcontrol_torque.py:229]
curvature_request_buffer (delay-compensating history) ──► expected_lateral_accel
raw_lateral_jerk ──► jerk_filter (1.2 Hz FirstOrderFilter) ──► desired_lateral_jerk
       │
       ▼
setpoint = expected_lateral_accel + desired_lateral_jerk * lat_delay      (latcontrol_torque.py:284)
error = setpoint - measurement (yaw-derived curvature*v^2)                (latcontrol_torque.py:296)
       │
       ├─ Accord branch (is_honda_accord, accord_rate_plant_ff toggle default True):
       │     angle_des = f(curv_des) via VehicleModel                    (latcontrol_torque.py:579-580)
       │     angle_des_rate = accord_angle_des_rate_filter.update(...)   (0.10 s LPF, line 581)
       │     plant_ff_torque = get_honda_accord_rate_plant_ff(...)       (hold + move terms, vehicle_tunes.py:2193)
       │     ff_lataccel = lateral_accel_from_torque(plant_ff_torque + friction_torque)
       │     output_lataccel = pid.update(error, feedforward=ff_lataccel, freeze_integrator=...)
       │     output_torque = torque_from_lateral_accel(output_lataccel)  (latcontrol_torque.py:596-598)
       │
       ▼
steer = -output_torque   (latcontrol_torque.py:748)  ──►  actuators.torque (controlsd.py:815)
       │
       ▼  [CarController.update(), carcontroller.py:266]
torque_cmd = actuators.torque                                            (carcontroller.py:284)
  [Civic-Bosch-Modified-only LPF branch — NOT taken for Accord]          (carcontroller.py:286-298)
limited_torque = rate_limit(torque_cmd, last_torque, ±3/frame)           (carcontroller.py:306, 100 Hz)
apply_torque = interp(-limited_torque*STEER_MAX, STEER_LOOKUP_BP/V)      (carcontroller.py:321)
       │
       ▼
hondacan.create_steering_control(..., apply_torque, CC.latActive, ...)   (hondacan.py:120-129)
       │
       ▼
STEERING_CONTROL (0xE4)  @ 100 Hz, every update() call, no frame-skip gate
```

## 6. Recent commit history — command-smoothing-relevant changes

`git log` on the four files, summarized (full titles in the raw log; dates from `git show -s --format=%ad`):

- **`latcontrol_torque.py`** (last ~25 commits): the newest three are all 2026-09-07/09-05/09-03 and
  are the Accord rate-plant-feedforward arc — `0f98d8c75` (apply learned latAccelOffset in the
  rate-plant path), `7e8f60823` (Accord patch switches: EPS gain/spring scales), `a6e2759fa`
  (rate-plant feedforward + Galaxy patch switches), plus the steer-ratio commits
  (`dcade4dcc`/`5f50a6c01`, 09-05/09-03). None of these touch `clip_curvature`, `jerk_filter`, or add
  any new output LPF — they are all in the feedforward/measurement half of the controller. No commit
  in this file's history adds or removes a setpoint-side LPF beyond the existing `jerk_filter`
  (present at least as far back as this trace's history window went; not independently dated here).
- **`controlsd.py`**: `a6e2759fa` (same rate-plant-FF commit, wiring `starpilot_toggles` into
  `LaC.update`), `dcade4dcc`/`5f50a6c01` (SteerRatio level plumbing for the Accord's variable-ratio
  rack). No `clip_curvature`/jerk-limit changes appear in the visible window.
- **`carcontroller.py` (Honda)**: newest is `1a3b24323` "Honda Accord 11G: add scoped CAN-FD control
  integration" (unrelated to steering smoothing — MVL CAN-FD radar/ACC ownership). The one
  command-LPF-adding commit in this file's history is **`b77341c80` "honda lpf", dated 2026-05-01**
  (four months before this trace), which added `get_civic_bosch_modified_torque_lpf_tau` and its
  call site — scoped to Civic Bosch Modified only, confirmed absent from the Accord's code path
  (§3). The adjacent `f69599fab` "honda wobble" (same date) is presumably the symptom commit that
  motivated it — EVIDENCE is the pairing/date only; this trace did not read that diff's content.
- **`hondacan.py`**: only `1a3b24323` (CAN-FD radar) and `32185c0c2` "honda" in recent history —
  nothing steering-smoothing-related; `create_steering_control` (hondacan.py:120) has no filtering
  logic and none was added/removed recently.

## 7. Cheapest openpilot-side knob to smooth the command further

**BELIEF**, not yet validated by measurement/replay:

- The cheapest *already-existing* knob is **`SteerDelay`** (`lat_delay`), since raising it increases
  how far ahead the jerk-derived lead term projects the setpoint (`latcontrol_torque.py:284`) — but
  this changes lead/lag shaping, not a low-pass cutoff, and risks overshoot if increased just to
  "smooth" the command; it is the wrong knob for the observer's literal ask.
- There is **no existing exposed toggle that raises the `jerk_filter` cutoff or adds a setpoint
  LPF** for any car including the Accord. The only precedent for a command-side LPF
  (`get_civic_bosch_modified_torque_lpf_tau`) is hard-coded to one other car/mode with no toggle.
- The **structurally cheapest new knob**, following the fork's existing pattern, would be adding a
  `FirstOrderFilter` on `setpoint` (or on `torque_cmd` in `carcontroller.py`, mirroring the Civic
  path but gated on `is_honda_accord` instead) with a Galaxy-toggle-controlled RC, the same pattern
  already used for `HONDA_ACCORD_FF_RATE_RC` (`latcontrol_vehicle_tunes.py:113`) and the
  `AccordEpsGainScale`/`AccordEpsSpringScale` switches (`7e8f60823`). This was NOT built or tested in
  this trace — it is a code-location recommendation only, based on where the existing Accord-specific
  toggles already live.
- **Caveat on the whole premise (BELIEF):** given §2, a target-side LPF is not "unfiltered" territory
  on this fork — `clip_curvature`'s jerk slew and the 1.2 Hz `jerk_filter` already remove most of the
  raw 20 Hz step discontinuity before the PID sees it. Any further target-side LPF would stack on
  top of these two, not replace an absent filter. Whether that stacking helps or over-smooths the
  Accord's identified rate-servo plant (`HONDA_ACCORD_EPS_G_BP`/`K_BP` tables,
  `latcontrol_vehicle_tunes.py:108-111`) is unverified — this trace read code, it did not run a
  route through it.
