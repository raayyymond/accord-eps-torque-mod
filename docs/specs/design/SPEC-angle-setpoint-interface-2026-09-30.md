# SPEC 2026-09-30: the angle-setpoint interface between StarPilot and the EPS angle loop

**Status: DESIGN BRIEF. Nothing built, flashed or sent. The fork was read, not edited.**

**Author:** subagent `fork-interface`, working for the orchestrator (`main`).

**Goal served:** THE GOAL box at the top of `docs/STATE.md` (2026-09-30), which calls for a 1 kHz firmware angle loop
in the LKAS lane `FUN_00028ea6`, fed by a StarPilot angle setpoint. This document is step 3 of the goal's order of
work, the "fork interface spec". It is the one agreed exception to the toggle-config-only rule. The operator
implements it, so it is written as a brief, not a patch.

**Inputs this spec stands on:**
- the three traces of 2026-09-30:
  - `docs/traces/TRACE-2026-09-30-lkas-lane-hook-and-setpoint-path.md` (the "hook trace");
  - `…-angle-signal-gp6a00.md` (the "angle trace");
  - `…-speed-driver-torque-lerp-and-ram-homes.md`.
- the plant identification, `analysis-2020accord/studies/v295/plant/V294-PLANT-IDENT-r71b.md`
  §"3.3 The delivered nominal".
- the fork checkout `C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot`, branch **`Dom`**,
  HEAD **`20d24ab79`** ("Accord V294: fix the rev-6.4 tests…"), clean tree, read-only. This is the tree the memory
  index names as the operator's fork; the HEAD has moved since `0f98d8c75`.

**The edit set this spec serves.** The zero-cave set from the hook trace §3:
- x := `gp-0x6a00`;
- `subr` → `add`;
- a = 0, b = 8192, C = 65535;
- sp := `ld.h -0x69ae[gp]`;
- optional: the D edit on `gp-0x6a56`, and the I-reset edit.

It gives `E = 16·(θ_sp − θ)` with `θ_sp = −raw`, in 0.1° counts of `gp-0x6a00`'s own frame.

Every decision-bearing claim is marked **EVIDENCE** (with its method) or **BELIEF**. Code is cited by file plus
function or grep string, never by line number.

---

## 0. The contract in eleven lines, and what is new

| # | the fork MUST | basis |
|---|---|---|
| C1 | Put `raw = round(−10 · θ_des_deg)` in 0xE4 `STEER_TORQUE`, in the frame of `carState.steeringAngleDeg` (raw 0x14A, offset included). | EVIDENCE §1 |
| C2 | Clip raw to ±4000 before packing. The EPS clamps at ±4096; the packer clips nothing and wraps past ±32767. | EVIDENCE §1.4 |
| C3 | While lateral is **allowed but not active**, send the **measured** angle: raw = the 0x14A `STEER_ANGLE` raw field, verbatim, with `STEER_TORQUE_REQUEST = 0`. | EVIDENCE §3 |
| C4 | While lateral is **not allowed** by the panda, send raw = 0 and request = 0. The panda **drops** the frame otherwise. Zero means "centre" to the EPS, so the firmware must not track it (requirement F1, §8). | EVIDENCE §2, §3 |
| C5 | On the first active frame, start the setpoint from the measured angle and slew to the desired angle. | BELIEF §4.4 |
| C6 | Bound the setpoint:<br>• \|θ_sp\| ≤ min(400°, the lat-accel angle at v);<br>• slew ≤ MAX_ANGLE_RATE(v);<br>• **\|θ_sp − θ_meas\| ≤ Δmax(v)**.<br>The panda bounds **none** of these. | EVIDENCE §2; values BELIEF §7 |
| C7 | On driver override, set θ_sp to the measured angle plus a latency lead, and keep the request. Do not keep commanding the model's angle against the hand. | BELIEF §4.5 |
| C8 | Engage the angle mode only when **both** hold: the EPS is the angle firmware (a distinct fwVersion, §5.1) **and** 0x14A byte 4 bits 0–2 == 7 (mode 3, substate 2). Otherwise treat it as a steer fault. | EVIDENCE for the bits; interlock BELIEF |
| C9 | Compute θ_des with the Accord steer-ratio map evaluated at **θ_des**, by a fixed-point iteration, not at the measured angle. | EVIDENCE §4.2 |
| C10 | Set `steerActuatorDelay` / `SteerDelay` to the **inner angle loop's** lag, measured on the first drive. Do not carry torque mode's 0.15–0.25 s. | BELIEF §4.3 |
| C11 | Leave every other 0xE4 field at 0, as today. In particular, byte 2 bits 3:2 (`gp-0x6803`) stay 0, unless §8 F3 adopts them as an interlock. | EVIDENCE §1.2 |

**Findings new this session.** Each one changes the design.

1. 🛑 **The panda bounds nothing on Honda steering except "zero when not allowed".** EVIDENCE:
   `opendbc_repo/opendbc/safety/modes/honda.h`, `honda_tx_hook`, grep `STEER: safety check`. For 0xE4 the only test
   is: if `!(aol_allowed || controls_allowed)` and `data[0] | data[1]` is nonzero, block the frame. There is no
   magnitude limit, no rate limit, no driver-torque check and no measured-angle check.
   ⇒ **Every bound on the angle servo is the fork's or the EPS's.** The EPS keeps its existing torque clamps:
   P 15360, which equals the rail 2461, and lane 3072.
2. 🛑 **"Send the measured angle when not steering" is only legal while lateral is allowed.** When it is not
   allowed, a nonzero field is **blocked**, not zeroed (EVIDENCE, same function: `tx = false`). A blocked frame is
   a gap in 0xE4. The EPS reads 0xE4 gaps as an RX fault, and an RX fault writes the `0x7FFF` sentinel (hook trace §5).
   - With the operator's toggles, `AlwaysOnLateral` is true (EVIDENCE:
     `analysis-2020accord/reference/toggle-backup_latest_20260910.decoded.json`). So "allowed" = ACC main on or
     the LKAS state on, which covers almost all of a drive (EVIDENCE: `safety.h`, grep `aol_allowed =`).
   - The residual cases are ACC main off, and the one-frame race at main-off. In those the field must be 0. On the
     edit set as traced, the EPS then servos toward **0°** for the 2.048 s ramp-down. The sign-hold gate passes
     this only when the lane was already pushing that way.
   ⇒ This is a **firmware requirement** (F1, §8), not something the fork can fix. One in-place halfword solves it,
     and Ghidra confirms its encoding (§8).
3. 🛑 **The stock camera's 0xE4 is accepted by the same engage gate and would be read as an angle.**
   - EVIDENCE, bus-2 census on 12 sampled segments plus route `a6` segments 6–7:
     - The camera sends `STEER_TORQUE_REQUEST = 1` with torque up to **|702|** (472 frames) while its LKAS runs.
     - Its byte 2 bits 3:2 read **0** on 11 of 12 routes and **1** on one (route `76`), never 2.
   - The climb gate accepts `gp-0x6803 ∈ {0, 2}` (memory `accord-the-authority-ramp-five-rates`).
   - If the harness relay closes (comma unplugged, or panda in silent mode after a heartbeat loss), the EPS
     receives the camera's torque command as **θ_sp = −tq/10, up to ±70°**. That holds if the EPS is not already
     latched in a fault; whether it re-engages after the 0xE4 gap is NOT traced, BELIEF.
   - See §7 R3 and §8 F3. The candidate interlock is `gp-0x6803 == 2`, which openpilot can send and the camera
     never sends.
4. **The fwVersion cannot tell the angle firmware from any other modded build.** EVIDENCE (Python byte search):
   - V295's image carries `39990-TVA,A160` at `0x13100`, and the `.rwd` header carries the same string.
   - The fork's `HondaFlags.EPS_MODIFIED` test is `b"," in fw.fwVersion` (`interface.py`, grep `eps_modified = True`).
   - It is true for every modded build: torque mode, rate loop and angle loop alike.
   - A torque fork on the angle firmware sends torque values that the EPS reads as angles. That is the worst case
     of this whole interface. See §5.1.
5. **The fork's controller plumbing already does most of the job.** EVIDENCE, `selfdrive/controls/controlsd.py`,
   grep `SteerControlType.angle`:
   - `steerControlType = angle` selects `LatControlAngle`.
   - In `interfaces.py`, grep `ret.steerControlType != structs.CarParams.SteerControlType.angle`, it **skips** the
     ForceTorqueController and NNFF conversion, so the torque-mode toggles go inert.
   - `LatControlAngle` already returns `CS.steeringAngleDeg` when inactive (`latcontrol_angle.py`, grep
     `angle_steers_des = float(CS.steeringAngleDeg)`).
   - opendbc already ships `apply_steer_angle_limits_vm` (`opendbc/car/lateral.py`).

---

## 1. The field

### 1.1 The frame (EVIDENCE: DBC used by the fork for `HONDA_ACCORD`)

**Which DBC.** `values.py`, grep `HONDA_ACCORD = HondaBoschPlatformConfig`, gives
`Bus.pt: 'honda_civic_hatchback_ex_2017_can_generated'`. From that DBC:

```
BO_ 228 STEERING_CONTROL: 5            (0xE4, 100 Hz, bus 0)
 SG_ STEER_TORQUE         : 7|16@0-  (1,0)    [-4096|4096]   bytes 0-1, big-endian, signed
 SG_ DRIVER_OVERRIDE      : 17|1@0+                          byte 2 bit 1
 SG_ STEER_TORQUE_REQUEST : 23|1@0+                          byte 2 bit 7   -> gp-0x6805
 SG_ CONTROL_STATE        : 26|3@0+                          byte 3 bits 2:0
 SG_ CHECKSUM/COUNTER/STEER_DOWN_TO_ZERO/HAPTIC_WARNING      byte 4
BO_ 330 STEERING_SENSORS  (0x14A, 100 Hz, from the EPS)
 SG_ STEER_ANGLE          : 7|16@0-  (-0.1,0) deg            bytes 0-1
 SG_ STEER_ANGLE_RATE     : 23|16@0- (-1,0)   deg/s          bytes 2-3
 SG_ STEER_SENSOR_STATUS_1/_2/_3 : 34/33/32                  byte 4 bits 2/1/0
BO_ 399 STEER_STATUS      (0x18F, 100 Hz, from the EPS)
 SG_ STEER_TORQUE_SENSOR  : 7|16@0-  (-1,0)
 SG_ STEER_ANGLE_RATE     : 23|16@0- (-0.1,0) deg/s
```

The kit's `rlog-tools/decode/decode_two_angles.py` docstring quotes the same `STEER_ANGLE 7|16@0- (-0.1)` and
`STEER_ANGLE_RATE` factors from the Accord 2018 DBC. Both DBCs agree on every signal used here.

**What the fork packs today.** `hondacan.py`, `create_steering_control`, packs only `STEER_TORQUE`
(`apply_torque if lkas_active else 0`) and `STEER_TORQUE_REQUEST`. `STEER_DOWN_TO_ZERO` is set only on TJA cars, and
the Accord is not one.

**What the wire shows.** EVIDENCE, sendcan census on `a6` segments 6–7:
- 11,596 frames with request 1;
- 346 frames with request 0, every one carrying torque 0;
- byte 2 & 0x7F = 0 and byte 3 & 7 = 0 on every frame.

### 1.2 The sign and scale chain, end to end (EVIDENCE)

| hop | relation | source |
|---|---|---|
| firmware angle | `gp-0x6a00` = 0.1° counts, signed int16 | angle trace §2.1 |
| 0x14A field | `field = −gp-0x6a00` (mode-3 packer, `0x40B04/08`: `ld.h -0x6a00,r14 ; mov r0,r26 ; sub r14,r26`) | angle trace §2.1; hook trace §3.4 |
| openpilot | `steeringAngleDeg = −0.1 · field = gp-0x6a00 / 10` (`carstate.py`, grep `ret.steeringAngleDeg = cp.vl["STEERING_SENSORS"]["STEER_ANGLE"]`) | DBC |
| 0xE4 in | `gp-0x69ae = clamp(−4·raw, ±16384)` (`0x526D2..0x526F2`) | hook trace §1 hops 1–4 |
| setpoint | with the sp edit: `4·sp = −16·raw` and `r26 = 16·θ`, so **E = 16·(−raw − θ)**, giving **θ_sp = −raw** | hook trace §3.3, MIRROR on 20,000 pairs |

**Therefore:**
- `raw = −10 · θ_des_deg` in openpilot's left-positive degrees.
- The **hold value** `−10 · steeringAngleDeg` **is the 0x14A `STEER_ANGLE` raw field itself**.

No offset calibration is needed: the fork reads the EPS's own angle and commands in the same frame and the same
0.1° quantum. This is the same polarity openpilot already uses: `carcontroller.py` notes "steer torque is converted
back to CAN reference (positive when steering right)", and a left (positive) angle gives negative raw.

**Test vectors for the fork's unit test** (EVIDENCE: arithmetic on the chain above):

| θ_des (deg, left +) | raw | bytes 0–1 | firmware θ_sp counts | 0x14A field when reached |
|---|---|---|---|---|
| +12.3 | −123 | `FF 85` | +123 | −123 |
| −45.0 | +450 | `01 C2` | −450 | +450 |
| 0.0 | 0 | `00 00` | 0 | 0 |
| +400.0 | −4000 | `F0 60` | +4000 | −4000 |

### 1.3 Mode-3 dependence (EVIDENCE: angle trace §2.3, §3.2)

The 0x14A angle equals `−gp-0x6a00` only on the mode-3 path (`gp-0x679c == 3`). Outside it, 0x14A carries a
relative accumulator clamped at ±1512°, and `gp-0x6a00` is forced to 0 whenever `gp-0x67fe ∉ {1,2}`.

The fork sees the health state as 0x14A byte 4 bits 0–2 (`STEER_SENSOR_STATUS_3/2/1`):
- **7 on 2,316,807 of 2,318,504 frames** across 91 routes;
- the exceptions are the recorded V75 hard fault, and one cold-start frame at the mode-3 entry, which also steps
  the angle on the bus (route `75`).

⇒ The fork must refuse angle mode unless those bits read 7 (contract C8).

### 1.4 Range and rounding (EVIDENCE)

- **EPS clamp.** `clamp(−4·raw, ±16384)` bounds θ_sp at ±4096 counts = **±409.6°**.
- **Packer.** `opendbc/can/packer.py`, `pack`, computes `ival = floor((value − offset)/factor + 0.5)` with **no
  range clip**, then masks to the signal width. A float above 32767 wraps sign.
- **Fork side.** Clip to ±4000 in the fork (C2) and pass an int, rounded half-away-from-zero or half-up; both
  agree to 0.1°.
- **Physical lock is not measured here.** The fork's steer-ratio map extends to 380° (`HONDA_ACCORD_STEER_RATIO_ANGLE_BP`)
  and its comment cites data to 450°. BELIEF: full lock is near or above 409.6°, so the EPS clamp may sit below
  lock. That is harmless for a clip, but parking near full lock will saturate the setpoint.

---

## 2. What the panda does for HONDA_BOSCH (EVIDENCE: `opendbc_repo/opendbc/safety/modes/honda.h`, `safety.h`)

| item | value |
|---|---|
| TX allow-list | `HONDA_BOSCH_TX_MSGS` includes `{0xE4, 0, 5, .check_relay = true}`. 0xE4 goes on bus 0, 5 bytes, and is relay-checked, so the camera's copy is not forwarded while openpilot owns it. |
| magnitude limit | **none** |
| rate limit | **none**. The fork's `STEER_DELTA_UP/DOWN = 3` is a carcontroller-side torque slew (0.03 × 4096 = 122.88 raw per frame, i.e. 12.3° per frame as an angle). It is not panda-enforced and is meaningless for an angle. |
| `STEER_REQUEST` | not inspected by the panda |
| `STEER_DOWN_TO_ZERO` | not inspected by the panda |
| not allowed: `!(aol_allowed \|\| controls_allowed)` | if `data[0] \| data[1] != 0`, **the frame is blocked** (`tx = false`). The request bit is ignored. |
| `aol_allowed` | `(acc_main_on \|\| lkas_on) && (alternative_experience & ALT_EXP_ALWAYS_ON_LATERAL)` |
| driver-override disengage for steering | none in the Honda mode |

**Reachable range:** whatever the fork sends, up to the EPS clamp of ±409.6°.

**Reachable slew:** unbounded by the panda. The EPS converts any error into torque up to the rail. The fork's own
limits are the only slew bound (§7).

---

## 3. What to send when not steering: the state table

**Two facts drive this table.** Both are EVIDENCE from hook trace §4.
1. The lane keeps running the PID on θ_sp for **2.048 s after `STEER_TORQUE_REQUEST` drops**, while the ramp falls
   16 per tick, and during driver override at fade ≥ 0.297.
2. On the edit set, sp is the raw field read every tick, so whatever the field says is tracked.

| state (fork-side test) | `STEER_TORQUE` | request | what the EPS does | basis |
|---|---|---|---|---|
| A. active: `CC.latActive` | `−10·θ_sp` (limited, §7) | 1 | full servo, ramp up in 0.99 s from engage | §1 |
| B. allowed, inactive: not `latActive`, and (`CC.enabled` or `starpilotCarState.alwaysOnLateralEnabled`) | **0x14A raw field, verbatim** | 0 | ramp-down for 2.048 s with E ≈ 16·(θ(t−τ) − θ(t)). That is a weak rate damper (§4.5). Then skip and I reset. | EVIDENCE for the guard; BELIEF on feel |
| C. not allowed: panda `!(aol\|\|controls)` | **0** (forced) | 0 | **with the edit set as traced, the lane servos toward 0° for up to 2.048 s**, gated by the sign-hold gate (passes only if the lane was already pushing that way, i.e. while unwinding toward centre). **Requirement F1 removes this.** | EVIDENCE (honda.h; hook trace §4, §5) |
| D. first active frame after B | the B value, then slew | 1 | the ramp starts at 0, so the first ~0.1 s carries little authority. I = 0 and E_prev = 0x7FFFFFFF if the preceding ticks were skips. | hook trace §4 "Engage" |
| E. driver override (`steeringPressed`, or a lower fork threshold) | θ_meas + lead (§4.5) | 1 (option O1) or 0 (option O2) | EPS fade f = 0.86 at openpilot's 1200 threshold, down to the 0.297 floor at ≥ 2097 wire | §4.5 |
| F. steer fault / 0x14A bits ≠ 7 / angle-firmware interlock false | B value if allowed, else 0 | 0 | as B or C | C8 |

**The mirror of the panda's condition is the hard part of the B/C boundary.**
- The fork must use the same predicate. `get_lateral_active(...)` in controlsd already takes
  `starpilotCarState.alwaysOnLateralEnabled`.
- The panda flips first, on the RX frame. So at main-off there is a race of at least one frame, in which a nonzero
  field gets blocked.
- BELIEF: one or two blocked frames do not fault the EPS. The same race exists today, because an active torque
  command at main-off is blocked identically. The memory record has STEER_STATUS identically 0 across 3,312 s
  engaged.
- **Check before the drive:** count `pandaStates.safetyTxBlocked` increments against 0x18F `STEER_STATUS` on two
  existing routes. If a blocked frame ever coincides with STEER_STATUS ≠ 0, the B→C transition needs a one-frame
  zero lead (send 0 when `cruiseState.available` drops, one frame early, via the fork's own LKAS/main edge detector).

---

## 4. The setpoint generator

### 4.1 What runs (EVIDENCE: fork `selfdrive/controls/lib/latcontrol_angle.py`, `LatControlAngle.update`)

```
active:   angle_steers_des = degrees(VM.get_steer_from_curvature(-desired_curvature, vEgo, roll)) + angleOffsetDeg
inactive: angle_steers_des = CS.steeringAngleDeg
saturated := |angle_steers_des - steeringAngleDeg| > 2.5 deg   (Honda: not a steer_limited_by_safety brand)
returns (0, angle_steers_des)  -> controlsd sets actuators.steeringAngleDeg
```

- `desired_curvature` has already passed `clip_curvature` (`drive_helpers.py`: jerk 5.0 m/s³ / v², lat-accel 3.0 +
  roll, |κ| ≤ 0.2) and the fork's turn-hold / lane-change curvature shaping in controlsd. Those are unchanged by
  this interface.
- `angleOffsetDeg` (paramsd) is added, so θ_des is in the **raw sensor frame**. That is the frame of 0x14A and
  `gp-0x6a00`. Correct as is.
- The Ascent-specific branches are inert for the Accord.

### 4.2 The steer-ratio map must be evaluated at θ_des (EVIDENCE for the code; BELIEF for the size)

**How the map is applied today.** controlsd `state_control`, grep `get_honda_accord_steer_ratio(steer_angle_deg`:
`VM.update_params(x, sr)` is called with `sr = get_honda_accord_steer_ratio(CS.steeringAngleDeg − angleOffsetDeg,
level)`. That is the ratio at the **measured** angle. It is the right thing for `calc_curvature(θ_meas)`.
`get_steer_from_curvature` then inverts with that same sR. The map (`HONDA_ACCORD_STEER_RATIO_V`, angle-indexed,
16.88 at 0–31° falling to 12.31 at 380°) is a secant compensation curve for `calc_curvature`. Its inverse is
therefore a **fixed point**: θ = κ·sR(θ)/factor.

**The error from using the measured angle.**
- Turn-in from 30° toward 60° at a 20° error: the ratio slope is −0.021/° (16.88 → 16.25 over 31–61°), so the
  error is about 2.5 %, roughly 1.2°.
- Above 236° the slope is 1.27 over 67°, so the error is larger.
- These are transient errors only; they vanish at steady state.

**The fix.** Two fixed-point iterations of `sr = map(θ_des − offset)` inside the Accord branch, using the same
`level` the toggle supplies. It costs microseconds.

### 4.3 The delay parameter (BELIEF; to be measured on drive 1)

- The fork's delay enters `modeld` as `lat_delay = liveDelay.lateralDelay + lat_smooth_seconds` (0.1 s), and sets
  how far ahead the model's curvature is taken (`modeld.py`, grep `lat_action_t = lat_delay`).
- The operator runs `SteerDelay 0.2` with `UseAutoSteerDelay` off (`lagd.py`, grep
  `use_custom_steerActuatorDelay`).
- Under the angle loop, the lag from a θ_sp change to the car's yaw is: transport (CAN, plus the 100 Hz hold of
  θ, plus controlsd; the record's round trip is about 60 ms), plus **the inner closed-loop lag**, plus the vehicle.

**The inner lag, from the identified plant** (BELIEF; spring-damper plant, J negligible below the corner, P-only):
`τ_inner ≈ b / (k + 0.100·Kp)` seconds. Here 0.100·Kp is the hands-off T per degree from the hook trace §3.3
arithmetic (Kp·0.1631·254/256·0.990/1.6).

| band (m/s) | b (T/(deg/s)) | k (T/deg) | τ_inner at Kp 500 | Kp 1000 | Kp 4000 |
|---|---|---|---|---|---|
| 0–5 | 4.94 | 6.5 | 0.087 s | 0.046 s | 0.012 s |
| 5–10 | 5.24 | 20.2 | 0.075 s | 0.043 s | 0.013 s |
| 15–22 | 20.7 | 79.7 | 0.160 s | 0.115 s | 0.043 s |
| 22+ | 26.4 | 55.8 | 0.249 s | 0.168 s | 0.058 s |

(b and k come from `V294-PLANT-IDENT-r71b.md` §3.3, nominal row. The ≥ 10 m/s b is biased high ×1.7–1.9 per G3a.
The I term changes the shape, not the order of magnitude.)

**Reading.**
- The right `SteerDelay` depends on the firmware Kp schedule, which is not set yet.
- It can be **shorter** than torque mode's 0.15–0.25 s if Kp is high at speed. That is the point of the angle loop.
- In the zero-cave set, Kp is keyed on **|θ_sp|** (hook trace §3.3). Highway setpoints are small and low-speed
  turns are large, so an angle-magnitude schedule that is high at small angles is a usable proxy for the b(v) rise.
  BELIEF; for the harness to test.

**Recommendation.**
- Drive 1: `UseAutoSteerDelay` **on**, so lagd learns the angle-mode lag, or a fixed `SteerDelay` equal to the
  harness's τ_inner at 15–22 m/s plus 0.06 s.
- Read the measured lag (§6.3) and fix it for drive 2. A single scalar cannot match a speed-dependent τ_inner. That
  argues for a Kp schedule that flattens τ_inner, which is a firmware or harness decision.

### 4.4 Engage, disengage and the rate limiter

Use `apply_steer_angle_limits_vm` (`opendbc/car/lateral.py`). It already implements "angle is current angle when
inactive": `new_apply_angle = steering_angle` when `not lat_active`. It rate-limits from `apply_angle_last`, so
engage starts at θ_meas automatically (C5). Section 7 gives the limits to feed it.

### 4.5 Driver override and the fork's thresholds

**Thresholds as they stand.**
- openpilot: `steeringPressed = |STEER_TORQUE_SENSOR| > 1200` (`STEER_THRESHOLD` default; the Accord has no
  override in `values.py`). EVIDENCE.
- On StarPilot, `steeringPressed` does **not** drop lateral in the code read here. It feeds the turn-hold
  "nudge-to-commit" logic (controlsd, grep `driver_confirmed`) and the saturation check. EVIDENCE for those uses.
  BELIEF that nothing else releases lateral on a press; selfdrived was not read.

**The EPS fade at those thresholds** (EVIDENCE: hook trace §4; key `gp-0x682f = min(|gp-0x4f60|>>5, 255)`;
wire = raw × 1.024 per memory `accord-wire-torque-is-raw-times-1024`):

| driver torque (wire) | B | f = (255·B & 0xFFFF)>>8 | multiplier |
|---|---|---|---|
| < 524 | 255 | 254 | 0.99 |
| 1200 (openpilot press) | ≈ 222 | 221 | 0.86 |
| 1638 | 179 | 178 | 0.70 |
| ≥ 2097 | 77 | 76 | **0.297 floor** |

**Why the setpoint must yield.** A position servo that keeps its setpoint while the driver holds the wheel away
puts P on the rail once the error exceeds `15360·16/Kp` counts (24.6° at Kp 1000). At the fade floor that is
0.297 × 2461 ≈ **730 T** of resistance, plus whatever I has wound (EVIDENCE: arithmetic on the clamps). That is
why C7 exists.

**Options.** Both BELIEF; the harness and the operator choose.
- **O1, recommended for drive 1.** Keep request = 1.
  - On `steeringPressed`, or on a lower fork hysteresis such as 800 on / 500 off, set θ_sp = θ_meas + θ̇_meas·τ_rt.
    Take the rate from 0x18F `STEER_ANGLE_RATE` (0.1°/s), with τ_rt ≈ 0.05–0.06 s.
  - Reset the limiter's `apply_angle_last` to that value, so the release slews back to the model's angle under the
    normal rate limit.
  - **Without the lead,** the stale hold acts as a damper of **0.100·Kp·τ T per deg/s** against the driver:
    - 3.0 at Kp 500, τ 0.06;
    - 6.0 at Kp 1000, τ 0.06;
    - compare V295's 2.96 at 2 Hz.

    That is about 600 T at a 100°/s hand-over-hand at Kp 1000, before the fade. The lead removes most of it.
  - **The fork cannot reach the I accumulator.** Wound I persists through O1 until a skip. That is the goal's "I
    bleeds on driver torque", which is cave-side (F2, §8).
- **O2.** Drop request on press. The EPS ramps down over 2.048 s (or 0.1 s under F1) and I resets on the skip. The
  cost is the 0.99 s re-engage ramp on every press. Cleaner I handling, worse hand-back feel.

**Interaction with the fork's turn-hold.** controlsd's `turn_hold_curvature` floors curvature at low speed
(blinker-driven). In torque mode a floor was a feedforward the driver could lean against. Under the angle loop it
is a **position hold**. With O1 the press releases it. Without O1 it is a 730 T fight. BELIEF; review before drive 1.

---

## 5. Fork change shortlist: the brief for the operator

This is the minimal set. Everything else in the torque-mode tree (rate-plant FF, observer, friction dither,
LAF/Ki toggles) goes **inert automatically**, because `LatControlTorque` is not instantiated (EVIDENCE §0 item 5).

**Updated for firmware design C1 (2026-09-30, `DESIGN-ANGLE-LOOP-C1-2026-09-30.md` §2.6, §9).** These are **flight
prerequisites** for the C1 image, each with the C1 evidence behind it:
- **F4** (§5.1): a torque fork on the angle image commands angles. C1 does **not** change the version string; the
  bootloader's view of `0x13100` is still untraced.
- **C3/C4/C5** (§5.3 step 6, §4.4): the measured angle while inactive, engage from θ_meas.
- **C8** (§5.5): the engage-time mode-3 gate. Mid-engagement mode-3 exits are already covered in firmware (B2 and the
  ±12000 bail); C8 covers engaging without mode 3.
- **C6 Δmax(v)** (§5.2).
- **O1** (§5.3 step 4): without it the harness's override scenario overshoots 2.9–4.6° at ≤ 8 m/s on every I policy.
- **No integral on the angle error below 8 m/s, none faster than τ_o = 1 s anywhere** (§5.6): at τ_o 0.3 s the outer
  loop has GM 1.5–2.0 dB on credible members at 3 m/s; at 1 s, ≥ 11.9 dB.
- **Camera LKAS off** (operator procedure) until F3 ships (§8).

### 5.1 The interlock first: what decides "angle mode"

`opendbc/car/honda/interface.py`, `_get_params`, `candidate == CAR.HONDA_ACCORD` branch, next to the existing
`eps_modified` scan of `car_fw`.

- **Set:** `ret.steerControlType = SteerControlType.angle` **iff** the EPS `fwVersion` equals the angle firmware's
  marker string **and** an `AccordEpsAngleLoop` param is true.
  - The fw check stops a torque fork from ever meeting the angle firmware unknowingly, and the reverse.
  - The param lets the operator fall back without a reflash.
- **Requires a firmware-side choice (F4, §8):** the angle build must carry a version string no other build has,
  for example `39990-TVA,A16A`. It must keep the comma so `EPS_MODIFIED` still sets.
  - BELIEF: fingerprinting tolerates an unlisted EPS string. Today's `39990-TVA,A160` is already absent from
    `fingerprints.py`, which lists `39990-TVA,A150`, and the car fingerprints fine.
  - UNVERIFIED: whether the bootloader or flasher checks the `0x13100` string or the `.rwd` header against
    anything. The build agent must check before relying on it.
- **Also set:** `ret.steerActuatorDelay` = the angle-mode value (§4.3). Leave `lateralTuning` as PID; it is unused,
  and it keeps the torque conversion off.

### 5.2 `opendbc/car/honda/values.py`, `CarControllerParams`

- Add an `ANGLE_LIMITS = AngleSteeringLimits(...)` for the Accord (§7 table): `STEER_ANGLE_MAX` 400,
  `MAX_LATERAL_ACCEL` = `MAX_LATERAL_JERK` = 3.589 (the module constants), and `MAX_ANGLE_RATE` in degrees **per
  frame**.
- Add a `Δmax(v)` table (the error clip) and the hold-allowed predicate's thresholds.
  - **Under C1** (Kp_eff 490 at ≤ 3.1 m/s, 570 at 8–12, 1243 at 15, 1748 at 19, 1971 at ≥ 26.9 m/s) the §7.1 values
    cap the demanded P at 0.1·Kp_eff·Δmax = **780 T at 5 m/s, 456 T at 10, 710 T at 20, 591 T at 30**, before I.
    P reaches the rail at |e| = 24 576 / Kp_eff degrees: 50° at ≤ 3 m/s, 43° at 8–12, 20° at 15, 12.5° at ≥ 27 m/s.
    (EVIDENCE: arithmetic on the C1 table; the Δmax values stay BELIEF.)

### 5.3 `opendbc/car/honda/carcontroller.py`, `CarController.update`

There is one new branch when `CP.steerControlType == angle`. It skips the torque `rate_limit`/`np.interp` path
entirely.

1. Build a `VehicleModel(CP)` once in `__init__`. Hyundai and Tesla carcontrollers do the same.
2. `apply_angle = apply_steer_angle_limits_vm(actuators.steeringAngleDeg, self.apply_angle_last, CS.out.vEgoRaw,
   CS.out.steeringAngleDeg, CC.latActive, self.params, self.VM)`.
3. `apply_angle = clip(apply_angle, θ_meas − Δmax(v), θ_meas + Δmax(v))` when active.
4. Override (O1): if pressed, set `apply_angle = θ_meas + rate·τ_rt`.
   - **Under C1, align "pressed" with the EPS's I freeze.** C1 freezes its integrator whenever |`gp-0x4f68`| > 512
     internal counts (≈ 524 on the 0x18F wire). Use a fork hysteresis of about **600 wire on / 500 off** rather than
     `steeringPressed` (1200), so θ_sp follows the hand whenever the EPS integrator is frozen (BELIEF: the two
     thresholds should coincide; nothing measured yet).
   - **Release after a long override (declared in the C1 design, M5):** the frozen I is the pre-grab value, so a
     ≥ 3 s override that moved the wheel releases with a 2.0–3.6° settle at 5–8 m/s, 0.8–1.3° at 12.5, ≤ 0.7° at
     ≥ 19 m/s (sim, with O1). The fork's normal rate limit back to the model's angle starts from there.
5. Set `self.apply_angle_last = apply_angle`.
6. Compute the field:
   - active: `raw = int(round(−10·apply_angle))`, clipped ±4000;
   - inactive and hold-allowed: `raw = int(round(−10·CS.out.steeringAngleDeg))`, which is the 0x14A field;
   - otherwise: 0.
7. Set `new_actuators.steeringAngleDeg = apply_angle`, so controlsd's `steer_limited_by_safety` comparison means
   something.

### 5.4 `opendbc/car/honda/hondacan.py`, `create_steering_control`

Add an argument so `STEER_TORQUE` is packed **as given** even when `lkas_active` is False. Today the function
forces 0 (grep `"STEER_TORQUE": apply_torque if lkas_active else 0`). `STEER_TORQUE_REQUEST = lkas_active` is
unchanged, and every other field is untouched.

### 5.5 `opendbc/car/honda/carstate.py`

In angle mode, set `steerFaultTemporary = True` unless `STEER_SENSOR_STATUS_1/2/3` are all 1 (C8). The signals are
in the same message the fork already parses for `STEER_ANGLE`.

### 5.6 `selfdrive/controls/lib/latcontrol_angle.py` or the Accord branch in controlsd

Add the two-iteration fixed point for sR(θ_des) (§4.2), keyed on `HONDA_ACCORD` and
`accord_variable_steer_ratio`.

**Keep the angle path feed-forward (flight prerequisite under C1).** No integral on the measured-angle error below
8 m/s, and none faster than τ_o = 1 s anywhere. EVIDENCE (C1 design §3.6): with the stand-in outer integrator the GM
on credible members at 3 m/s is 1.5–2.0 dB at τ_o 0.3 s and ≥ 11.9 dB at τ_o 1 s; in the time domain even τ_o 1 s adds
1–4 dwell-then-jump events per scenario set at 7–19 m/s (two integrators against stiction).

### 5.7 Toggle config (the normal channel)

- `SteerDelay` / `UseAutoSteerDelay` per §4.3. **Under C1, `UseAutoSteerDelay` on for drive 1.** The C1 inner loop's
  group delay is speed-dependent: 112–171 ms at 0.5 Hz, 84–134 ms at 0.2 Hz (nominal, 8–30 m/s). A single 45 ms
  look-ahead gives 0.935–1.017 in-phase tracking at 8–22 m/s but over-boosts 26–30 m/s to 1.06–1.07 (C1 design §2.2;
  EVIDENCE model, BELIEF on how lagd will settle).
- `AccordEpsAngleLoop` true.

The torque-mode keys may stay in place; they are inert. The flight-read scorer's toggle gate must be told so (§6.5).

**Unit tests the operator should add:**
- the §1.2 test vectors, through `create_steering_control` and `CANPacker`;
- the B/C state table of §3, from synthetic `CC`/`CS`;
- a no-wrap test at ±5000°.

---

## 6. The measurement plan for the one drive

**Every signal used here is already on the wire or in the log.** EVIDENCE, by source:

| signal | source | rate | notes |
|---|---|---|---|
| θ_sp (as sent) | `sendcan` 0xE4: `θ_sp_deg = −raw/10`, plus the request bit | 100 Hz | the logged truth of what the EPS was asked |
| θ_des (pre-limit) | `controlsState.lateralControlState.angleState.steeringAngleDesiredDeg` | 100 Hz | written by `LatControlAngle` |
| θ | 0x14A `STEER_ANGLE` (= `gp-0x6a00`/10, a 100 Hz hold) | 100 Hz | byte 4 bits 0–2 = health; bits 3–7 = cave telemetry if used |
| ω | 0x18F `STEER_ANGLE_RATE` (0.1°/s) | 100 Hz | |
| driver torque | 0x18F `STEER_TORQUE_SENSOR` | 100 Hz | the fade key ×1.024 |
| lane torque T | **CAN 427 (0x1AB) tap**: `sign(T)<<9 \| \|T\|>>3`, T = `gp-0x6b38` | 50 Hz (STATE) | **wire polarity = +sign(cmd)**; reads about 307–310 at the rail |
| status | 0x18F `STEER_STATUS`, `STEER_CONTROL_ACTIVE` | 100 Hz | |

🛑 **Instrument traps.**
- The kit's cereal `epsTelemetry @137` collides with the fork's `starpilotLateralState @137`. Decode fork rlogs with
  the patched schema (memory `accord-cereal-slot-137-collision-and-tap-polarity-plus`).
- Take routes from the device's realdata, never by counter (memory: V293 rev 4).

### 6.1 Pre-registered LIVE / NOT-LIVE / INVERTED signature

The edit is live if the lane torque follows the **angle error**, not the command.

**Window.**
- Hands-off engaged frames: |0x18F torque| < 500 wire and request = 1.
- At least 1.2 s after the engage edge, so the ramp is at 1.
- |θ_sp − θ| below the P-clamp angle, 24.6° at Kp 1000.
- Low-pass both sides at 1 Hz and align θ_sp by the transport delay. The tap is 50 Hz; resample θ to it.

**Regression:** `tap = c0 + c_raw·raw + c_meas·f14A`, where f14A is the 0x14A `STEER_ANGLE` raw field.

**Predictions.**
- The angle loop gives `tap ∝ +(raw − f14A)`. EVIDENCE for the chain: E = 16(θ_sp − θ), and torque mode's measured
  tap polarity is +sign(cmd) for the same sp chain.
- Therefore **c_raw ≈ −c_meas ≈ +Kp/800 tap counts per raw count**, i.e. Kp/80 tap per degree of error, hands-off,
  P-only. EVIDENCE: arithmetic (0.100·Kp T per degree, ÷ 8 for the tap).
- With Ki > 0, add `Σ(raw − f14A)` as a third regressor, or score on the 0.3–3 Hz band, where I is small.
- If the D edit ships, add the 0x18F rate. BELIEF: its coefficient is about 0.16·Kd/8 tap per deg/s, with the
  sign that opposes the rate.

| verdict | condition |
|---|---|
| **LIVE** | `c_meas/c_raw ∈ [−1.25, −0.80]` **and** `c_raw` within ±25 % of Kp/800 (the build's Kp knot at the window's \|θ_sp\|) |
| **NOT LIVE: torque firmware or the wrong image** | \|c_meas\| < 0.2·\|c_raw\|, and the tap reproduces the V295 surface of raw alone (R² ≥ 0.9 on the image surface, as V293 did at 0.986) |
| **INVERTED: positive feedback** | `c_meas/c_raw > 0`. 🛑 This would run the wheel to the clamp within a second. It is the abort signature, and the operator will feel it first. |

### 6.2 The goal's criteria, on the wire

| goal criterion | instrument (existing unless marked) | read | pass |
|---|---|---|---|
| dwell-then-jump | `V293-FLIGHT-READ-HOWTO.md` §7.1: 0.10 s moving mean of \|0x18F rate\| < 0.25 for ≥ 0.2 s, in runs ≥ 2 s, per band 0–5/5–10/10–20/>20 | dwells per minute | **≤ r6c (V282) in every band with ≥ 60 s**. Stricter than the how-to's 3×; this is the goal's own wording. |
| low-speed stick-slip gone | same, 0–5 m/s, plus §7.1's rate-concentration (q75–90 bin ≤ 0.40) | | |
| tracking gain | how-to §7.3: slope of actual on desired lateral accel, 0.5 Hz LP, runs ≥ 10 s, bands <8/8–15/15–22/>22 | | **0.95–1.05 in every band ≥ 8 m/s** |
| turn-hold | how-to §7.3: windows ≥ 1.5 s, \|D\| > 0.5, \|dD/dt\| < 0.3; mean\|actual\| ÷ mean\|desired\| | | **≥ 0.90 in every band ≥ 8 m/s** (the goal also needs the >20 m/s ratio ≤ 1.04 not to over-turn) |
| ring presence | how-to §2 predicate: 2 s windows, 18–22 Hz prominence ≥ 8 on the driver-torque bar, amplitude ≥ 40 | % windows | **≤ 0.5 %** |
| F7 | how-to §3: fixed 103-wire detector, \|angle\| ≥ 30, fdom ≥ 6 | per 100 s | **0** |
| no new 5–30 Hz line | how-to §5 line table, on 0x18F rate and the bar | | no line absent on V282/V295 |
| hard-turn 1.6–3 Hz energy | 0x18F rate band energy in hard-turn windows (`rlog-tools/studies/rev64-goal/`) | | ≤ V282 |
| 20 Hz loop gain | **design-side** (mirror \|P/x\| at 20 Hz), not a wire read | | ≤ V295's 3.85 |

### 6.3 New inner-loop diagnostics

These are REPORT, not gates. They explain a pass or a fail.

1. **Inner hold ratio.** In windows with |dθ_sp/dt| < 2°/s for ≥ 1.5 s and |θ_sp| > 3°, take the median θ/θ_sp per
   band. P-only predicts `1 − k/(k + 0.1·Kp)`: 0.94 at 0–5 m/s and 0.56 at 15–22 m/s for Kp 1000. With I it should
   approach 1. BELIEF (the plant table).
2. **Inner lag.** The cross-correlation peak lag of θ against θ_sp, per band. This is the number §4.3 asks for.
   Also report lagd's `liveDelay.lateralDelayEstimate`.
3. **Dead zone.** In slow-ramp windows (|dθ_sp/dt| 1–5°/s), the error |θ_sp − θ| at each dwell end.
   - P-only predicts Fc/(0.1·Kp) degrees: about 0.76° at 0–5 m/s and 0.04° above 22 m/s, for Kp 1000. BELIEF (the
     plant table; Fc ±129 at 0–5).
   - The 0.1° quantum floors this read.
4. **Fork limiting activity.** The fraction of active frames where `−raw/10 ≠ steeringAngleDesiredDeg` beyond 0.05°,
   split by cause: the rate limit, the Δmax clip, or the lat-accel clip. A setpoint that lives on the limiter is a
   fork tuning finding, not a firmware result.
5. **Override.** Per press: peak |tap| and the time to fall below 20 tap counts after release.

### 6.4 Drive abort signatures (pre-registered)

The operator disengages if he feels any of these, and the read confirms them.
- INVERTED (§6.1).
- Hands-off, request = 1, and |tap| ≥ 300 (the rail) for > 0.3 s.
- |θ − θ_sp| > 10° hands-off for > 0.5 s at > 8 m/s.
- 0x14A byte 4 bits 0–2 ≠ 7 while engaged.
- 0x18F `STEER_STATUS` ≠ 0 while engaged.
- Any sendcan |raw| > 4000.
- After a request drop, |tap| still pushing toward 0° for > 0.2 s. That is the state-C centring of §3, and it means
  F1 is missing.

### 6.5 The scorer needs an angle-mode arm

`v293_flight_read.py` §0 gates read `torqueState`: `kp`, `latAccelFactor` and `branch`. Under `steerControlType =
angle`, `torqueState` is not written (EVIDENCE: controlsd `cs.lateralControlState.angleState = lac_log`). Those
three gates must read N/A, not FAIL.

Attribution moves to:
- `CarParams.steerControlType == angle`;
- the EPS fwVersion in `CarParams.carFw` (the marker string, F4);
- the §6.1 signature.

The how-to's §7.3 desired lateral accel must come from `desiredCurvature·v²`. BELIEF that it already does; check
`v293_symptom_instruments.py`.

---

## 7. Risks, and what bounds each one

### 7.1 Bound table (fork values are BELIEF starting points for the harness to size)

Lat-accel and jerk angles come from the fork's VehicleModel arithmetic: Accord CarSpecs, sf = −0.00070, sR 16.88,
`MAX_LATERAL_ACCEL = MAX_LATERAL_JERK = 3.589` (`lateral.py`). Script:
`_scratch/angle_loop/fork-interface/limits.py`.

| v (m/s) | max angle from 3.59 m/s² | jerk-limited rate (°/s) | proposed MAX_ANGLE_RATE (°/s) | proposed Δmax (°) | servo rate limit (2461 − Fc)/b (°/s, plant §3.3) |
|---|---|---|---|---|---|
| 1.34 | 5477 (use the 400 clip) | 5477 | **120** | 15 | 483 |
| 5 | 400 | 400 | **120** | 15 | 483 / 467 (band edge) |
| 8 | 160 | 160 | **120** | 10 | 467 |
| 10 | 105 | 105 | 105 | 8 | 467 / 250 (band edge) |
| 15 | 50.5 | 50.5 | 50.5 | 5 | 250 / 118 (band edge) |
| 20 | 31.4 | 31.4 | 31.4 | 4 | 118 |
| 30 | 17.8 | 17.8 | 17.8 | 3 | 93 |

**How the proposed columns were chosen.**
- **MAX_ANGLE_RATE** = min(jerk-limited, 120°/s). 120°/s is below the servo's rail-limited rate at every speed, so
  the slew alone never rails P. The jerk limit takes over above about 9 m/s.
- **Δmax** ≥ rate_max·τ_rt + the hold error at the speed's k, so hold authority is not starved. At Kp 1000 it caps
  the fork-demanded P at 0.1·Kp·Δmax: 1500 T at low speed, 300 T at 30 m/s, before I.
- All of it is BELIEF; the GATE 2 harness must re-size it with the chosen Kp schedule.

### 7.2 The risk register

| # | risk | bounded by | residual | E/B |
|---|---|---|---|---|
| R1 | **The servo spends the whole rail to reach any setpoint.** P rails at \|e\| ≥ 15360·16/Kp counts. | the fork's Δmax, slew and angle clips (§7.1); the EPS P clamp = rail 2461, lane 3072, and the fade. The panda bounds none of it. | a fork bug equals the full rail. The unit tests (§5.7) are the guard. | EVIDENCE for the clamps; BELIEF for the values |
| R2 | **Request drop or main-off makes the EPS centre** (state C, §3) | the sign-hold gate (only the same direction) and the 2.048 s ramp | up to 2 s of centring assist while unwinding. **Firmware fix F1.** | EVIDENCE (honda.h, hook trace §4) |
| R3 | **The relay closes and the camera's 0xE4 becomes an angle command** (±70° seen) | nothing on the edit set; the climb gate accepts 0 | a comma crash with the stock LKAS active on the camera. **Firmware fix F3** (require `gp-0x6803 == 2`, sent only by the fork). The operator must keep the stock LKAS off until F3 ships. | EVIDENCE for the camera frames; BELIEF for re-engage after the fault |
| R4 | **A torque fork on the angle firmware**, or the reverse | the fwVersion marker plus the param (§5.1, F4) | none if both are implemented; **today nothing distinguishes them** | EVIDENCE (fw string) |
| R5 | **0xE4 RX fault sentinel** 0x7FFF: sp = 16384 means θ_sp = +409.6°, a hard **left**, P rails for 2.048 s if the lane already pushed left | the sign-hold gate; cal `0xC63F6` 16 → 328 (0.1 s; also shortens normal disengage); downstream delivery cut NOT traced | the same class as on V293–V295 today | EVIDENCE for the lane arithmetic (hook trace §5) |
| R6 | **Mode-3 loss**: `gp-0x6a00` snaps to 0, so θ reads 0 while the wheel is at θ, and the servo drives toward θ_sp from a false 0 | the fork's C8 (bits ≠ 7 means fault) at 100 Hz, ≥ 60 ms late; the EPS's ±1200° bail catches only the +32700 wrap | **a firmware gate on `gp-0x67fe == 2` and `gp-0x679c == 3` is needed** (angle trace §6.3) | EVIDENCE for the mechanism; never observed in 91 routes |
| R7 | **Override fight**: up to 730 T at the fade floor, plus wound I | O1 (§4.5); the fade | wound I until a skip. **Firmware F2** (I bleed). | EVIDENCE for the arithmetic |
| R8 | **Stale feedback**: θ is a 100 Hz hold (1–10 ms) in the EPS and about 60 ms old in the fork | the inner loop is closed in the EPS; the fork's staleness enters only as the setpoint lag and the O1 lead | GATE 2 must include the 10-tick hold (angle trace §1.3: 4° of phase at 2 Hz, about 40° at 20 Hz) | EVIDENCE for the hold |
| R9 | **Setpoint quantisation** of 0.1° in both frames | the fork rounds to the nearest count | a 0.1° quantum is 0.1·Kp/16 S counts, i.e. **10 T at Kp 1000 per LSB step**. The 100 Hz staircase is a candidate excitation of the 20 Hz mode. BELIEF; the harness should check a 1-LSB 100 Hz toggle. | EVIDENCE for the arithmetic |
| R10 | **Steer-ratio map at the measured angle** gives a transient angle error | §4.2 fixed point | under about 2.5 % transient | EVIDENCE for the code; BELIEF for the size |
| R11 | **Turn-hold floors become position holds** against the driver at low speed | O1 | review before drive 1 | BELIEF |

---

## 8. What this interface requires of the FIRMWARE side

These go to the cave designer and the hook tracer.

- **F1. Do not track sp while the request is off.** One in-place halfword does it.
  - Change `0x29A56` `da 05` (`bne 0x29A60`, after `cmp r0,r20` where r20 = ramp ≠ 0) to **`b2 05`**, which is
    `be 0x29A5C`. `0x29A5C` holds `jr 0x2A164`, the skip.
  - The guard becomes: skip iff ramp == 0 **or** request ≠ 1.
  - **The encoding is EVIDENCE.** Ghidra `disassemble_bytes` (dry run) on the V294 program decodes `0x29A48..0x29A64`
    as `cmp r0,r14 ; setfne r20 ; cmp 0x1,r8 ; setfe r8 ; cmp r0,r20 ; bne 0x29a60 ; cmp r0,r8 ; bne 0x29a60 ;
    jr 0x2a164`. Ghidra decodes the existing `b2 05` at `0x290E4` as `be 0x290EA` (+6), so `b2 05` at `0x29A56`
    is `be 0x29A5C`. Python reads `da 05` at `0x29A56` in V295.
  - **The effect is BELIEF and needs the mirror.**
    - On a request drop the PID skips. It feeds S = 0 into the output lag (pole 992/1024 per tick, 32 ms), resets I
      and E_prev, and releases in about 0.1 s instead of 2.048 s.
    - It also covers the override-latch case that the hook trace's §3.5 edit covers (ramp == 0 still skips).
    - **It replaces §3.5, not adds to it.** Applying both makes every tick skip and kills the lane.
  - **The cost:** Honda's 2 s hand-back disappears. A request drop mid-curve is a 0.1 s release, and the wheel's own
    spring takes it back. That is openpilot's normal angle-car behaviour. Flag it to the operator.
- **F2. An I bleed on driver torque** (THE GOAL). Cave-side. The fork cannot reach `gp-0x6dd0`. **I has no wire
  instrument** (hook trace §6), so CLAUDE.md rule 3 applies before any Ki dose.
  - **C1 status (2026-09-30): implemented as a FREEZE, not a bleed** (C1 design §2.3). The cave returns past
    `0x29D7A/0x29D7C` with r6 = 0 when |`gp-0x4f68`| > 512 or the ramp is below 0x8000, so Honda's own I code adds
    nothing; the cave writes no RAM. The freeze predicate is a **wire** predicate (|0x18F| > 524 wire, plus the
    0.99 s after a request edge), so the I is reconstructible from the wire (C1 §6.1).
- **F3. Camera discrimination.**
  - The candidate: require `gp-0x6803 == 2` to climb, and have the fork pack 0xE4 byte 2 bits 3:2 = 2.
  - Bus census: the camera sends 0 or 1, never 2 (EVIDENCE, 12 routes sampled).
  - `gp-0x6803 == 2` also selects the 1 → 6 → 7 chain, with a 328 up-ramp (0.1 s), and the **A/B fade arms**
    `0xCBB54`/`0xCBAE4` instead of `0xCBC34`/`0xCBBC4` (hook trace §2: `r25 = (gp-0x6803 == 2)`). Those tables
    would need the 0/1-arm values written into them. That is cal.
  - The climb gate's compare is an in-place candidate. NOT traced; BELIEF.
  - **Traced for C1 (2026-09-30; EVIDENCE: Ghidra decode `0x29360..0x293C0`, Python census with a positive
    control).** State 1 reads `0x29376 ld.bu -0x6803,r15 ; cmp r0,r15 ; bne 0x293BA`. Changing **one byte**,
    `0x2937C fa 1d` → `f5 1d` (`bne` → `br`), makes the `== 0` arm unreachable, so the lane engages only through the
    `== 2` arm (states 6/7/8). What that switches: up-ramp `0xC63FC` = 328 (0.1 s) instead of `0xC63F8` = 33; state-8
    down-ramp `0xC63FA` = 66; status `gp-0x679f` = 2/4/6 instead of 1/3/5; `gp-0x679e` set; fade-B arm `0xCBAE4[7]`
    → `0xE54FC` (X 24/45/64/80/96/112, Y 255/205/164/125/90/51) instead of `0xE564C` (X 16/26/38/48/64/96,
    Y 255/243/218/179/77/77), so 12 halfwords of cal to copy; fade-A identical. **Not in C1**: `gp-0x6803` has
    readers outside the lane (`0x2A552…0x2A976`, `0x4E87E`) and `gp-0x679e` one (`0x2B35A`), none traced. Until
    then F3 is an operator procedure (camera LKAS off), not a flight blocker.
- **F4. A distinct fwVersion string** for the angle build (§5.1). UNVERIFIED: checksum and bootloader coverage of
  `0x13100` and the `.rwd` header.
- **F5. Validity gates** `gp-0x67fe == 2` and `gp-0x679c == 3` on the lane output (angle trace §6.3). R6 cannot be
  bounded from the fork fast enough.
  - **C0/C1 status:** `gp-0x67fe == 2` is in the guard through B2 (bVar2). Mode 3 leaves only to state 4 on
    `gp-0x67fe ≠ 2` (B2 skips that tick) or to state 1 on a `−0x8000` baseline (θ wraps, the ±12000 bail), so
    mid-engagement exits are covered in firmware (EVIDENCE: angle trace §3.1 + B2). The engage-time case is C8.
    A firmware `gp-0x679c == 3` gate would cost ≈ 10–12 cave bytes; not in C1. BELIEF residual: a baseline that turns
    0x7FFF while mode stays 3 is not excluded by any gate.
- **F6. The sentinel** (R5). The RX fault writes `gp-0x69ae = 0x7FFF` **and** `gp-0x6805 = 0xFF` (hook trace §1
  hop 4f). Under F1, `gp-0x6805 = 0xFF` makes r8 = (`gp-0x6805` == 1) = 0, so the guard should skip on the fault tick
  and the sentinel never reaches P. BELIEF: this is derived from the guard bytes above and the hook trace's
  fault-path stores; it is not mirrored, and the ordering of the RX handler against the lane inside one tick is not
  traced. **If the mirror confirms it, F1 also kills the sentinel pulse, and R5 closes with the same halfword.** This
  is the most valuable single check in this list. If it does not confirm, clamp `0x7FFF` to "hold" in the cave, or
  apply `0xC63F6` 16 → 328.
  - **Confirmed in the mirror (C0 §3.3, and C1's time harness):** with A2 + B2 the sentinel scenarios give a 0.0°
    excursion and ≤ 0.05 s of decay above 50 T at every speed. The residual is the one-tick RX-preemption window
    (task priority untraced) and the timeout path to `gp-0x6805 = 0xFF` on a fork crash (untraced); both are
    **flight-prerequisite traces** under C1.

---

## 9. Open items, and what would change this spec

1. **The F1 mirror run**, including the sentinel tick sequence (§8 F6). If F1 skips on the fault, R5 closes with
   the same halfword.
2. **`pandaStates.safetyTxBlocked` against `STEER_STATUS`** on existing routes (§3). This decides whether the B→C
   race needs a one-frame lead.
3. **Whether the EPS re-engages on camera frames after an 0xE4 timeout fault** (R3). Trace the fault latch
   (`gp-0x6807`) recovery.
4. **The bootloader's view of the version string** (F4).
5. **The harness sizing** of Kp(|θ_sp|), Δmax(v) and MAX_ANGLE_RATE(v) on the plant family. This spec's values
   are placeholders, marked BELIEF.
6. **The physical lock angle** against the 409.6° clamp (§1.4).

**Files.**
- This spec.
- The scratch scripts in `_scratch/angle_loop/fork-interface/`:
  - `cam_e4.py`, `cam_e4_multi.py`: the camera and openpilot 0xE4 census;
  - `limits.py`: the angle limits by speed.
