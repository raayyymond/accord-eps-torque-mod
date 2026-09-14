# The fork's Accord lateral path, and two designs for changing the TRACKED QUANTITY

Subagent `fork`, **2026-09-13**. **NOTHING WAS FLASHED, NOTHING WAS SENT ON ANY BUS, NOTHING WAS
COMMITTED OR PUSHED. The openpilot fork was READ ONLY — not one byte was edited, reverted or stashed
there.** No firmware image was built. This document is a survey and two design plans; it is not a build.

Fork read: `C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot`, branch `Dom`.

> 🛑 **HEAD has moved since the brief.** The brief names `305732c85`; the tree is at **`a357cd2b5`**
> ("galaxy mobile: add the Rebuild Params action to System Tools"), one commit later. `305732c85`
> ("Accord: reshape the variable-ratio map from an 82-route SR-free measurement") is what the car was
> running on route 6f — `initData.params["GitCommit"]` reads `305732c85cbb9f152e2fc23101bd9b0b5320c5ed`
> [EVIDENCE]. The working tree carries the `ModelCurvatureLead` patch, the operator's SR-map refit to
> NOMINAL 16.88, unrelated galaxy/safe-mode churn, and two deleted `frpc_darwin_*` binaries. All left alone.

Every claim below is marked **[E]** EVIDENCE (with the file/function or record document that carries it)
or **[B]** BELIEF. Line numbers are never cited; grep the symbol.

---

## 🔗 RECONCILIATION — read this with `ARC-GROUNDING-TORQUE-MODE-AND-ACCEL-TRACKING-2026-09-13.md`

**Added at the 2026-09-13 close-out. Neither document's body was edited; this note records where the two
agents landed differently and how the session resolved it.**

This file and `docs/research/ARC-GROUNDING-TORQUE-MODE-AND-ACCEL-TRACKING-2026-09-13.md` (agent `arc`)
were written independently, on the openpilot side and the firmware side of the same goal. **They do not
contradict each other on any fact. They differ on which of the operator's two readings to build first.**

| | position |
|---|---|
| **This memo** | **Design B first** — have StarPilot output a **rate target**. The case is §0 below and it is real: `AccordRatePlantFF` is **already a measured inverse of the LKAS assist map**, so Design B is the completion of something already ~80 % built, at no firmware risk |
| **The session's choice** | **Torque mode first** (built as V293). Two reasons, neither disputing this memo's case. **(1) Design B cannot remove the grinding** — V288 rev 2 flew exactly that class (a reference-side setpoint pre-filter): the cave was live, the D-bind duty fell ×0.03 as designed, **and the grinding was unchanged** (19.99 vs 19.93 Hz, KS p 0.18). Nothing on the fork's reference side reaches the 20 Hz ring. **(2) The operator's goal names torque** as what openpilot expects, and torque mode is the **model-independent test** of the in-loop class that V292's flight left open. **Design B is recorded, not falsified — it remains available if V293's answer sends the work back to the reference side** |

**Where the session's dispositions are recorded, and they are not re-litigable afterwards:**
`docs/review/ADVERSARIAL-V293-PREREG-2026-09-13.md` §*"Dispositions decided before the pass"* — in
particular that *"×6 rate setpoint"* has no meaning under torque mode (the arc grounding's §7.3 reaches
the same conclusion from the firmware side), that the 5–9 Hz rise is **gated** rather than merely
reported, and that the **outer loop is gated (B6)** because V276 is the nearest flown relative and it
limit-cycled at 2–4 Hz.

**What this memo's §3.5 recipe is now for:** it is the **first V293 drive**. The pre-registration makes
that drive an **IDENTIFICATION drive, not a symptom drive** — LAF fitted by instrumental variables against
`modelV2.action.desiredCurvature·v²`, **not** from `torqued` — then the tune, then symptom scoring.

**What shipped on the fork side:** one selection — **Testing Ground 9, "Accord EPS Torque Mode",
variant B** (uncommitted, ships on A) — replacing four toggles the operator had to keep consistent by
hand, with the asymmetric mismatch hazard encoded as a step order. It shipped first as a param,
`AccordEpsTorqueMode`, and was reworked onto the slot the same day; all five params are gone, and the
four tune numbers below are now **constants in `latcontrol_vehicle_tunes.py`, not sliders** — so
§3.5's identification has to be planned before the drive, not adjusted between drives. Card:
`docs/guides/TORQUE-MODE-TOGGLE-CHECKLIST-2026-09-13.md`.

---

## 0. The four numbers this whole document turns on

| quantity | value | where it comes from |
|---|---|---|
| openpilot's actuator range | `actuators.torque` ∈ [−1, 1] → `STEER_MAX` **4096** CAN counts | `honda/interface.py` Accord branch, `lateralParams.torqueBP = [0, 4096]`; `CarControllerParams.__init__` takes `torqueBP[-1]` **[E]** |
| the firmware's rate reference at full command | **133.6 deg/s** of steering-wheel rate | derived below from the V280r2/V282 map (top knot 1032 at idx 240) and `fb = 30.891 × 8 = 247.13` counts of E per deg/s **[E-chain, B on the product]** |
| the firmware's peak delivered torque | **2505** EPS torque counts, structurally capped | P clamp `0xC61BC` 15360 before the ×`0xC6CD0` 5346>>15 gain; `memory/accord-lkas-commands-rate-not-torque` **[E]** |
| the fork's identified plant gain | `G(v)` **120 → 70** deg/s per unit torque, 5 → 28.5 m/s | `HONDA_ACCORD_EPS_G_V` in `latcontrol_vehicle_tunes.py`, identified on r34/r35/r39/r3a/r3c **[E]** |

⭐ **The two middle rows are the same number, and nobody has written that down before.** The map's
open-loop scale is 4096 / 28.96 = **141.4 deg/s per unit torque** (saturating at 133.6 at the idx-240
knot); the fork's empirically identified `G(v)` is **0.85× that at 5 m/s and 0.49× at 28.5 m/s**. The
difference is exactly what a closed rate servo with finite loop gain and a load should give
(`L_dc/(1+L_dc)` falling with speed as the rack loads up). ⇒ **`AccordRatePlantFF` is already a
measured inverse of the LKAS assist map.** Design B is therefore not a new idea in this fork; it is
the completion of one that is already 80 % built. **[E]** on both tables, **[B]** on the attribution
of the 0.49–0.85 ratio to closed-loop tracking.

**The derivation of 133.6 deg/s, in full** (V850 is LE; the arithmetic mirrors the decompile):

```python
# The map (V280 rev 2 / V281r3 / V282 / V292 -- forward path byte-identical, BUILD-LINEAGE V280r2 row)
#   slot 7 knots  Y'(X) = round(6 * Ytop * X / 240)  ->  0,52,86,103,138,275,413,550,688,1032
#   top knot: setpoint sp = 1032 at demand index idx = 240
SP_PER_IDX   = 1032 / 240          # = 4.30   setpoint counts per demand-index LSB   [E, lineage]
CNT_PER_IDX  = 16.125736           # 0xE4 wire counts per demand-index LSB           [E, memory]
FB_PER_DPS   = 247.13              # = 30.891 * 8 ; E-units per deg/s at DC          [E, ADV-V287-B]

# the rate loop nulls at  E = 32*sp - fb = 0
def rate_deg_s(cmd_counts):
    idx = cmd_counts / CNT_PER_IDX            # demand index
    sp  = SP_PER_IDX * idx                    # rate setpoint, counts
    return 32.0 * sp / FB_PER_DPS             # deg/s the loop drives toward

# rate_deg_s(3870) = 133.6   (idx 240, the map's ceiling)
# inverse:  cmd_counts = 28.96 * rate_deg_s        <-- THE MAP'S INVERSE, and it is a CONSTANT
```

The map is linear from the origin on V280r2 and later, so **its inverse is one multiply** — 28.96 CAN
counts per deg/s, or 0.007070 of the [−1, 1] output per deg/s. Design B needs nothing more than this.

---

## 1. The Accord lateral path as it runs TODAY

### 1.1 The chain, file by file

```
modelV2.action.desiredCurvature            (20 Hz, camera clock; ZOH to 100 Hz -- the comb)
      |
      |  controlsd.Controls.state_control -> [ModelCurvatureLead.update]  <-- UNCOMMITTED, toggle OFF
      v
  clip_curvature(v, prev, new, roll, jerk_factor)        drive_helpers.py
      |   MAX_LATERAL_JERK 5.0 m/s^3 (rate) . MAX_LATERAL_ACCEL_NO_ROLL 3.0 m/s^2 . MAX_CURVATURE 0.2
      v
  self.desired_curvature  ------------------------------> LatControlTorque.update(...)
                                                              latcontrol_torque.py
      VehicleModel (VM) is parameterised FIRST, and this is where the Accord is special:
        sr = get_honda_accord_steer_ratio(steeringAngleDeg - angleOffsetDeg, level=SteerRatio toggle)
        VM.update_params(stiffnessFactor, sr)
      |
      v
  measurement = -VM.calc_curvature(radians(sa - offset), v, roll) * v^2      [lateral accel, m/s^2]
  future_desired_lateral_accel = desired_curvature * v^2
  expected_lateral_accel = curvature_request_buffer[-delay_frames] * v^2     [lat_delay = 0.20 s]
  desired_lateral_jerk = LPF_1.2Hz( (future - expected)/lat_delay ), clipped +/-2.5 m/s^3
  setpoint = expected_lateral_accel + desired_lateral_jerk * lat_delay
  error    = setpoint - measurement
  error_with_lsf = error * (1 + low_speed_factor / kp)
      |
      +-- GENERIC torque path (NOT taken on this car):
      |     ff = setpoint - roll_comp - latAccelOffset ; ff += friction_scale*get_friction(...)
      |     output_lataccel = pid.update(error_with_lsf, error_rate=-measurement_rate, feedforward=ff)
      |
      +-- ACCORD RATE-PLANT path (TAKEN -- accord_rate_plant_ff default True):
            curv_des      = (setpoint - latAccelOffset*fade) / max(v^2, 1)
            angle_des     = degrees(VM.get_steer_from_curvature(-curv_des, v, roll*fade))
            angle_des_rate= FirstOrderFilter(RC=0.10 s).update( (angle_des - prev)/dt )
            plant_ff      = -get_honda_accord_rate_plant_ff(angle_des, angle_des_rate, v,
                                                            rate_gain, gain_scale, spring_scale)
            friction_tq   = torque_from_lateral_accel(ff - ff_before_friction)   # friction ONLY
            ff_torque     = plant_ff + friction_tq
            ff_lataccel   = ff_torque * LAF
            output_lataccel = pid.update(error_with_lsf, error_rate=-measurement_rate,
                                         feedforward=ff_lataccel, freeze_integrator=...)
            output_torque   = output_lataccel / LAF
      v
  return -output_torque  ->  CC.actuators.torque   (units of [-1, 1])
      |
      v
  HondaCarController.update                          opendbc/car/honda/carcontroller.py
      limited_torque = rate_limit(torque_cmd, last, -STEER_DELTA_DOWN*DT_CTRL, +STEER_DELTA_UP*DT_CTRL)
                        # STEER_DELTA_UP = STEER_DELTA_DOWN = 3 -> +/-0.03 per 10 ms
      apply_torque   = int(interp(-limited_torque * STEER_MAX, STEER_LOOKUP_BP, STEER_LOOKUP_V))
                        # Accord torqueBP/torqueV = [0,4096]/[0,4096] -> the lookup is the IDENTITY
      hondacan.create_steering_control(...)  ->  0xE4 STEER_TORQUE (+ STEER_TORQUE_REQUEST = latActive)
```

**The rate limit in wire units: ±0.03 × 4096 = ±122.88 counts per frame = 12 288 counts/s.** On route 6f
the command actually hit that cap on **0.03 %** of frames (max |Δcmd| 123.0) **[E]**, so it is not a
binding shaper today, but it *is* the thing that makes a step of the setpoint take 33 frames to cross
full scale.

### 1.2 🛑 The panda does not limit this command at all

`opendbc/safety/modes/honda.h`, the `0xE4`/`0x194` block, contains exactly one test: if controls are
not allowed and `data[0] | data[1]` is non-zero, refuse the frame. **There is no magnitude limit, no
rate limit, no driver-torque limit, no RT-window check on Honda.** **[E]** — I read the whole
`honda.h` steer block; the file has no `STEERING_LIMITS` struct for this platform.

⇒ **Both designs below are limited only by openpilot's own `STEER_MAX` 4096 and ±3/frame, and by the
firmware.** Nothing on the panda will catch a sizing error. That raises the cost of getting the
identification wrong, and it is the single strongest argument for the "measure first, then command"
ordering in §3.5.

### 1.3 The LIVE toggle values — read from the wire, not from defaults

Source: `initData.params` of `analysis-2020accord/rlogs/75604b0a432fdc89_0000006f--d876c761bc--0--rlog.zst`,
decoded with `rlog-tools/lib/rlog_parse.py` + the StarPilot cereal copy at `rlog-tools/_scratch/spcereal/`.
Python = `C:/Users/dudei/anaconda3/envs/bin_decompile/python`. **[E]**

| key | route 6f (LIVE) | 2026-09-10 backup | note |
|---|---|---|---|
| `ForceTorqueController` | **1** | True | `LatControlTorque`, confirmed on the wire (`torqueState` on 11 951/11 951 frames) |
| `ForceAutoTune` / `ForceAutoTuneOff` | **0 / 1** | False / True | ⇒ `use_custom_latAccelFactor` and `use_custom_friction` are both True |
| `SteerKP` | **0.9** | 0.9 | measured `p/error` = **0.9000** at p5/p50/p95 |
| `SteerLatAccel` | **6.0** | 6.0 | measured `−(p+i+d+f)/output` = **6.0000** at p5/p50/p95 |
| `SteerFriction` | **0.01** | 0.01 | |
| `SteerRatio` | **16.88** | 16.33 | 🛑 **MOVED.** = `HONDA_ACCORD_STEER_RATIO_NOMINAL` ⇒ scale exactly 1.0000 |
| `SteerRatioStock` | 16.33 | — | the CP value the toggle is measured against |
| `SteerDelay` / `UseAutoSteerDelay` | **0.2 / 0** | 0.2 / False | `liveDelay.lateralDelay` reads **0.2000** flat on the wire |
| `LaneCenteringE2EAuthority` | 0.2 | 0.2 | |
| `LaneChangeSmoothing` | **4** | 6 | moved |
| `HondaLateralPidKp/KiScale` | 1.0 / 1.0 | — | inert on the torque path (one consumer, `latcontrol_pid.py`) |
| `NNFF` / `NNFFLite` | 0 / 0 | — | so `LatControlNNFF` is not substituted |

🛑 **TRAP, and it will bite the next agent: every `Accord*` key is ABSENT from `initData.params`.**
Not zero — absent. So is `KeepLearnedLatAccelOffset`. This is **not** a regression: each absent key's
default in `common/params_keys.h` is byte-for-byte the value the 2026-09-10 backup carried —
`AccordRatePlantFF` "1", `AccordVariableSteerRatio` "1", `AccordFFRateGain` "0.5", `AccordTorqueKi`
"0.30", `AccordTurnFFTaper` "0", `AccordEpsGainScale`/`AccordEpsSpringScale` "1.0",
`KeepLearnedLatAccelOffset` "1" — and `StarPilotVariables.get_value` falls through to that default.
**⇒ The effective live values are the same either way, but the rlog cannot confirm an `Accord*`
toggle's state.** Use the backup or the header default. **[E]** on the absence and on the defaults;
**[B]** on the cause (a params rebuild that stored only non-default keys).

### 1.4 What the loop actually did on route 6f (segments 3 and 6, 7 079 active frames)

| quantity | p5 | p50 | p95 | \|·\| p90 |
|---|---|---|---|---|
| `torqueState.p` | −0.0672 | −0.0044 | +0.0763 | 0.0719 |
| `torqueState.i` | −0.0799 | −0.0381 | +0.0092 | 0.0680 |
| `torqueState.d` | 0 | 0 | 0 | 0 |
| `torqueState.f` | −0.3742 | −0.0222 | +0.2444 | **0.3354** |
| `torqueState.output` | −0.0468 | +0.0108 | +0.0808 | 0.0710 |
| `\|0xE4 cmd\|` (counts) | — | 78 | — | 291 (p99 427, max **481**) |

**[E], all of it.** Three readings:

1. **`d` is identically zero.** `PIDController` is constructed with `k_p` and `k_i` only, so `_k_d` is 0
   and the `error_rate=-measurement_rate` argument is multiplied by nothing. **There is no derivative
   term in the outer loop at all.** The 1.2 Hz jerk filter and the `measurement_rate_filter` are
   computed and, for the D path, discarded.
2. **The feedforward carries the loop:** `f/(p+i+d+f)` median **0.681**, and `|f|` p90 is 4.7× `|p|` p90.
   The rate-plant FF is not a trim; it is the controller.
3. 🛑 **The car uses 11.7 % of the actuator.** Peak |cmd| 481 of 4096 — demand index **29.8** of 254.
   That is the operating point every design below has to serve, and it agrees exactly with the
   record's *"91 % of engaged time sits in Kp's first segment"*.

**A cross-check that validates the STATE note.** Under the generic path the FF would be
`setpoint/LAF`; at the observed `|desiredLateralAccel|` p90 = 1.253 m/s² and LAF 6.0 that is 0.209 of
full scale = 855 counts, against the rate-plant path's actual 291. **×2.9** — inside STATE's
*"`AccordRatePlantFF = False` is NOT conservative (×2.4–4.3 steady FF)"*. Two independent readings
agree. **[E]**

### 1.5 Every Accord-specific branch, and what it does

| symbol | live | what it does | status |
|---|---|---|---|
| `accord_variable_steer_ratio` → `get_honda_accord_steer_ratio` | **True** | In `controlsd.state_control`, replaces `liveParameters.steerRatio` with a 13-knot angle-indexed map, scaled by `SteerRatio/NOMINAL`. Feeds `VM`, so it enters the MEASUREMENT (`calc_curvature`) **and**, on this fork, the rate-plant FF (`get_steer_from_curvature`). The learner is ignored for this platform. | Live. Knots refit 2026-09-12 (83 routes, uncommitted). At `SteerRatio` 16.88 the scale is exactly 1.0000. |
| `accord_rate_plant_ff` → `get_honda_accord_rate_plant_ff` | **True** | Replaces the lat-accel feedforward with `hold + move` = `k(v)·angle_des/G(v) + gain·d(angle_des)/dt/G(v)`, clipped by `get_honda_accord_ff_move_torque_limit(v)` (1.0 below 8 m/s → 1.4 at and above 10). P and I stay in lat-accel space. | Live, and it is the dominant term (§1.4). |
| `accord_ff_rate_gain` | **0.5** | The `gain` on the move term. Docstring: 1.0 over-drives entries on this plant. | Live. |
| `accord_eps_gain_scale` / `accord_eps_spring_scale` | **1.0 / 1.0** | Multiply `G(v)` and `k(v)` from Galaxy so the tables can be corrected after an EPS firmware change without a code push. | Live at unity. **These are the natural knobs if the firmware's map changes.** |
| `accord_torque_ki` | **0.30** | Re-applied to `pid._k_i` every frame in `update`. | Live. |
| `accord_turn_ff_taper` → `get_honda_accord_ff_scale` | **False** | Sigmoid taper (max −30 % above 0.45 m/s²) applied to `ff` **before** `ff_before_friction = ff`. | 🛑 **DEAD under the rate-plant FF** — the rate-plant branch keeps only `ff − ff_before_friction`, the friction increment, and the taper cancels out of that difference exactly. Confirmed by re-reading the branch this session. **[E]** |
| `keep_learned_lat_accel_offset` | **True** | In `get_torque_control_params`: keeps `latAccelOffsetFiltered` even when a custom LAF is set. Before the fix a custom LAF silently zeroed the offset. | Live; wire shows `latAccelOffsetFiltered` ≈ **−0.033** m/s². Folded into `curv_des`, not added as a torque — the docstring's reasoning (on a rate servo a lat-accel bias is an ANGLE bias) is correct. |
| `ModelCurvatureLead` / `accord_curvature_lead` | **False** (default) | Slope-continuous reconstruction of the 20 Hz modelV2 staircase at 100 Hz. | Uncommitted, OFF. `FORK-COMB-RECONSTRUCTION-2026-09-13.md`: −2.4 dB (r39) / −4.2 dB (r63) on the 0xE4 18–22 Hz band, ~−18 % ring, |H| ≥ 1, a lead below ~3.5 Hz and a lag above. |

**torqued, for the record.** `liveTorqueParameters` on route 6f: `useParams` 1, `liveValid` **1**,
`latAccelFactorRaw` **6.24** (p5–p95 5.86–6.67), `frictionCoefficientRaw` 0.137, filtered 1.871 / 0.196.
⇒ 🛑 **Two of the record's statements about torqued need updating.** `accord-backcalc-…-torqued-cannot-
validate-on-the-modded-eps` was measured on r31/r32/r33 at the port defaults, where `liveValid` was 0 on
every tick; on route 6f, with LAF 6.0 and friction 0.01 live, **`liveValid` reads 1 and the raw estimate
6.24 is within 4 % of the toggle**. And the toggle ceilings quoted there are stale: `LAT_ACCEL_FACTOR_MAX_MULT`
is now **10.0** and `STEER_KP_MAX_MULT` **5.0**, so `SteerLatAccel` reaches **16.89** and `SteerKP` **3.0**
without touching `params.toml`. **[E]** on the readings and the constants; **[B]** that the raw 6.24 is a
sound identification — the stale-cache caveat in that memory is not retired by one route. **This is a
report, not a licence to edit those memories.**

---

## 2. What the controller ASSUMES, and how that meets the firmware

### 2.1 The assumption, in the controller's own words

`latcontrol_torque.py`'s header comment is explicit: *"Lateral acceleration achieved by a specific car
correlates to torque applied to the steering rack… This controller applies torque to achieve desired
lateral accelerations."* The generic path is built on exactly that: `torque = lat_accel / latAccelFactor`,
a **static, memoryless, linear** map from torque to lateral acceleration. **[E]**

That assumption is **false on this EPS, and known to be false**. The record:

- `accord-lkas-commands-rate-not-torque`: the 0xE4 command is a **rate reference**, not a torque.
- `accord-backcalc-…`: on V280 rev 2 the measured lat-accel-per-torque is **5 at the lane-change band
  and 9–10 steady**, with `|P| ∝ 1/f` over 0.1–1 Hz — *"the plant is INTEGRATOR-LIKE… so no single LAF
  makes the feedforward exact."*
- The Accord branch's own comment in `latcontrol_vehicle_tunes.py`: *"A lat-accel feedforward
  (setpoint / latAccelFactor) is 3-10× too much torque on this plant; the P term then has to cancel it
  and the loop settles above command."*

**⇒ The fork has ALREADY abandoned the torque-actuator assumption for this car.** `AccordRatePlantFF`
is the abandonment. What remains on the lat-accel assumption is only P, I and the friction increment.

### 2.2 Where the fork encodes an EPS model, and what each parameter means physically

`get_honda_accord_rate_plant_ff` is the whole model. The identification, quoted from the constant block:

```
steering wheel rate [deg/s] = G(v) * torque  -  k(v) * angle        torque in [-1, 1]
```

| parameter | table | physical meaning | how it should move if the firmware changes |
|---|---|---|---|
| `G(v)` | `HONDA_ACCORD_EPS_G_V` = 120, 95, 85, 70 at v = 5, 12.5, 18.5, 28.5 m/s | **closed-loop DC gain of the LKAS rate servo**, deg/s of wheel rate per unit command. §0 shows this is 0.49–0.85 × the map's own open-loop scale of 141.4. | ∝ the map's slope. A map ×2 ⇒ `AccordEpsGainScale` ×2 (or re-identify). |
| `k(v)` | `HONDA_ACCORD_EPS_K_V` = 0.17, 0.28, 0.35, 0.45, 0.50 s⁻¹ at v = 4, 8, 12.5, 18.5, 28.5 | **return-spring rate**: how fast the wheel unwinds per degree of angle with zero command. Rises with speed = self-aligning torque rising with speed. This is a PLANT property, not a firmware one. | Unchanged by a firmware edit. `AccordEpsSpringScale` exists for load changes (tyres, alignment). |
| `hold = k·angle/G` | — | the steady command that **holds** an angle against the spring: 0.03–0.06 for 5–25 deg. | scales as 1/`G`. |
| `move = gain·d(angle_des)/dt / G` | `rate_gain` 0.5 | the command that **moves** the wheel at the planned rate. **This is exactly the map's inverse** applied to the planned wheel rate. | scales as 1/`G`. |
| `move` clamp | 1.0 below 8 m/s → 1.4 at/above 10 | the jerk limit becomes a steering-rate limit ∝ 1/v², so below ~8 m/s the move term alone would exceed full scale. | keep. |

🛑 **The `G(v)` table's speed dependence is the load, not the servo.** The servo's arithmetic (map, Kp
248 flat, Kd 128, Ki 0, clamps, ×6 gain) has no speed term on the V282/V292 forward path. So `G(v)`
falling 120 → 70 is the rack getting harder to turn, i.e. the closed loop's DC tracking ratio falling.
**[B]**, but it is the reading the numbers support and it matters: it means `G(v)` would have to be
**re-identified after any map change**, not merely rescaled by the map's ratio.

### 2.3 The meeting point, stated plainly

| what openpilot sends | what the firmware does with it |
|---|---|
| `actuators.torque` ∈ [−1, 1], meant as torque | multiplied by 4096, rate-limited ±123/frame, put on 0xE4 |
| 0xE4 STEER_TORQUE | **look-up in the assist map** → a rate setpoint (linear, ×6 of stock, ceiling 1032 at idx 240) |
| — | `E = 32·sp − fb`, `fb` = a two-sample sum of measured wheel rate, DC gain 30.891 |
| — | `P = E·Kp>>8` with **Kp 248 flat**, `D = ΔE·128>>3`, **Ki = 0**; P clamped 15360 |
| — | ×5346>>15, output clamp → motor. **Peak 2505** torque counts, structurally |

**The mismatch is not a scale error, it is an order error.** openpilot believes it commands a variable
whose DC gain to lateral acceleration is finite; the firmware gives it a variable whose DC gain to
lateral acceleration is unbounded (a rate command integrates into angle, which integrates into heading).
Every consequence in the record follows from that one fact: LAF cannot be identified stably; the
integrator was rejected on principle by the operator (V283, *"it goes against what openpilot is
modelling its output as, a torque"*); `torqued`'s buckets do not fill; the feedforward is 3–10× too big.

---

## 3. DESIGN A — make the EPS a TORQUE actuator

### 3.1 🛑 Ground it first: this is V279's class, and V279 is already BUILT

**Before anything else.** `docs/BUILD-LINEAGE.md`, heading
*"### V279 — PURE FEEDFORWARD: the rate PID opened into a linear torque map (2026-09-02, NOT FLOWN — THE
FLIGHT CANDIDATE)"*. It exists as an image (`a165b1a5…423485`, rev 2) and an rwd (`ea0d7dfd…532985b`),
passed 710/710 of its own checks plus a mechanism proof and two adversaries, and **has never been driven**.

| cell | V268 | V279 | what it is |
|---|---|---|---|
| `0xC62E6` | 7680 | **0** | feedback clamp → the PID's feedback operand is forced to 0; `E = 32·sp` |
| Kd bank `0xCB7D4` | 128 / 64 | **0** | D = 0 |
| map bank `0xC9A88` | Honda Y (ceiling 172) | **Y = 2X**, ceiling 480 | the reference, linearised |
| Kp bank `0xCB994` | 248…717 | **256 flat** | `P = 32·2·idx·256>>8 = 64·idx` exactly |

Delivered `= 64·idx × 5346 >> 15` → **2505 at idx 240 = 6× stock, unchanged**; linear to cmd ≈ 3886.
Slope **0.645 EPS torque counts per CAN count**. **[E], lineage.**

⇒ **Design A does not need a new firmware idea. It needs V279 rebased onto V282/V292 and flown.**
Anyone proposing "make the EPS a torque actuator" as novel has not read the lineage. What V279 was
missing is the thing this document is for: the StarPilot tune to fly it with.

**And one measurement since then makes it more attractive, not less:**
`accord-with-the-loop-open-there-is-no-18-22hz-object` (2026-09-13, 35 routes, 4 759 s lateral-disengaged):
with the LKAS rate loop open there is **no 18–22 Hz object at all**; ζ_open ≥ 0.05 or the mode is not
modal. V279 opens that loop **by construction** (feedback clamp 0, Kd 0). ⇒ **the grinding's mechanism
is removed, not attenuated.** Likewise the 7 Hz high-angle stutter, which
`accord-v278r3-high-angle-stutter-is-p-desaturating-on-a-stalled-wheel` attributes to **P desaturating**
— with `E = 32·sp` there is no desaturation event, because E no longer depends on the wheel. **[E]** on
both records; **[B]** that the symptoms therefore disappear, because neither has been driven open-loop.

**The cost, and it is the whole argument against:** rate feedback **is** this lane's damping
(`accord-scaling-a-setpoint-does-not-scale-its-feedback`; V276's damping fraction 0.94 → 0.57, V279's is
**0** by construction). The rack is then damped only mechanically, and the *only* electronic damping left
is openpilot's 100 Hz loop through a 0.20 s delay. V279's own risk note pre-registers the failure mode:
**a new 1–2.5 Hz wallow**.

### 3.2 The firmware side of Design A, sized

T = k·cmd with **k = 0.645** EPS counts per CAN count gives 2505 at cmd 3886 — V282's authority exactly,
and the "no authority cut" rule is honoured by construction. If Design A is rebased onto V292 the same
four cells apply; the V292 error-feedback cave at `0xC4C00` becomes **dead code** (it repairs the
feedback filter's floors, and there is no feedback), which is a build-hygiene item, not a hazard.
**[B]** — I did not re-derive V279's cells from the image this session; that is a firmware-side job and
must be done from the built image before any flash.

### 3.3 The fork patch plan

**Turn OFF, in this order:**

1. `AccordRatePlantFF` → **False**. This is the whole point: with a torque actuator the generic
   lat-accel feedforward `setpoint/LAF` becomes correct, and the plant-inverse feedforward becomes wrong.
   The branch falls through to the generic `output_lataccel = pid.update(..., feedforward=ff)`.
   ⚠ Setting it False **raises** the steady feedforward ×2.4–4.3 at today's LAF (§1.4). **Do not set it
   False while the rate-servo firmware is on the car.**
2. `AccordTurnFFTaper` → the decision is now live again. It is dead today; with the rate-plant FF off it
   becomes a real −30 % taper above 0.45 m/s². **Leave it False** for the identification drive — it is a
   shaping choice and it would bias the LAF fit.
3. `AccordEpsGainScale` / `AccordEpsSpringScale` → inert once the rate-plant FF is off. Leave at 1.0.
4. `AccordCurvatureLead` → leave **OFF**. It is a comb fix for a symptom Design A removes structurally,
   and it is a lag above 3.5 Hz.
5. `AccordVariableSteerRatio` → **leave True.** See §3.4.

**No code change is required for Design A.** Every branch it needs is already switchable from Galaxy.
That is a real advantage: the fork side of Design A is four toggles and a tune.

**Set:**

| toggle | first-drive value | reasoning |
|---|---|---|
| `ForceAutoTuneOff` | **1** (already) | keeps the custom LAF/friction in the loop and stops `paramsd` learning over the vehicle model |
| `SteerLatAccel` (LAF) | 🛑 **UNKNOWN — must be identified.** Start at the **port 1.689** | see §3.5. Range is now [0.845, 16.89]. |
| `SteerFriction` | **0.01** (already) or 0.025 | see §3.5 |
| `SteerKP` | **0.3** for the first drive | see §3.6 |
| `AccordTorqueKi` | **0.15** | halve it for the first drive; the integrator is the term the operator distrusts and it is the one that hides a mis-sized LAF |
| `SteerDelay` | **0.2** (already) | unchanged; it is a plant property |

### 3.4 What happens to the SR map under Design A

`get_honda_accord_steer_ratio` sits in **two** places today (its own docstring says so): the
measurement path (`VM.calc_curvature`) and the rate-plant FF (`VM.get_steer_from_curvature`). Under
Design A the second consumer disappears and the map reverts to a pure measurement-path correction.

**Keep it.** The 83-route refit is an SR-free measurement of the rack's real ratio-vs-angle shape, and
it is independent of the EPS firmware (its own comment records the check: a stock-firmware 98 %-manual
route reads 15.82 where a V289r1 83 %-engaged route reads 15.88). Removing it would put the
over-delivery on roundabouts and 90°+ corners straight back.

⭐ **But the LEVEL's meaning changes, and this is a trap.** Today a high level pushes twice in the same
direction (asks for more angle AND reads back less curvature), which the docstring flags. Under Design A
it pushes only once — through the measurement. So **the level's sensitivity roughly halves**, and a
level that felt right on the rate-plant FF will feel different. `SteerRatio` 16.88 (scale 1.0000) is the
right starting point and should not be moved during identification. **[B]**, from the structure.

### 3.5 The identification recipe — the part that actually decides whether Design A works

🛑 **`torqued` cannot be trusted to do this.** Two reasons, both in the record: its caps were outside
the car on the modded EPS (`accord-backcalc-…`), and even where `liveValid` now reads 1 (§1.5) its
estimate is a TLS through central buckets over a 250–1250 s filter, on a plant whose gain is about to
change discontinuously. **Identify by hand from the first drive's rlog, then set the toggles.**

**What to measure.** For a torque actuator the claim under test is `a_lat = LAF · τ + offset`, with
`τ` the delivered command in [−1, 1] units.

**Instruments, all already on the wire:**

| quantity | source | why this one |
|---|---|---|
| `a_lat` | `livePose` yaw rate × `vEgo`, roll removed — **not** `VM.calc_curvature` | SR-free on both sides; the record's own `straight_understeer_sr.py` §F instrument. Using the vehicle model would make the fit depend on the SR map it is supposed to be independent of. |
| `τ` | `carOutput.actuatorsOutput.torqueOutputCan / 4096` | what was actually sent, after the rate limit — not `actuators.torque` |
| hands-off gate | `carState.steeringPressed` False **and** `steeringTorque` inside its noise band | the driver's torque is an unmeasured second input |
| engagement gate | 0xE4 `STEER_REQUEST` **and** 0x18F SCA — **lateral** engaged | `feedback-engaged-means-lateral-engaged-and-v276-is-not-a-reference` |
| lag | shift `τ` forward by `SteerDelay` = 0.20 s before pairing | matches the controller's own delay model |

**The fit.** Ordinary least squares is **biased low** in closed loop (the record says so explicitly).
Use **instrumental variables** with `modelV2.action.desiredCurvature · v²` as the instrument — it is
correlated with the command and uncorrelated with the plant's own disturbance. `backcalc_laf_friction.py`
and `backcalc_extract.py` in `analysis-2020accord/studies/optune/` already implement both estimators;
reuse them rather than writing a third.

**Sample size.** The record's r31 fit used 567 paired points and produced a usable IV slope. Require:

- **≥ 400 hands-off, laterally-engaged, v > 15 m/s frame pairs per |τ| bucket**, in **≥ 4 buckets**
  spanning |τ| 0.05 → 0.50, so the fit has leverage instead of a pivot at the origin;
- **≥ 2 buckets above |τ| = 0.25** — this is the condition `torqued` fails on this car, and it is the
  one that decides whether the slope is identified or interpolated;
- both signs represented within 30 % of each other, so a road-crown offset cannot masquerade as slope.

At 100 Hz that is ~4 s per bucket of *qualifying* frames, i.e. a few minutes of mixed highway with
deliberate lane offsets. **This is compatible with the "one short symptomatic drive" law** — the drive
is a *tune* drive, not a symptom drive, and it should be flown before any symptom scoring.

**Friction.** Measure the **hysteresis half-width** of the `τ` → `a_lat` relation, not a gain: sweep
slowly through zero and read the width of the dead band. The record measured 0.116 torque on stock,
0.054 on V112, 0.028 on V278r3, 0.013–0.030 on V280 rev 2 ⇒ friction ≈ **0.025** there. 🛑 **Do not
inherit that number.** Every one of those was measured on a **rate servo**, where the servo hides the
rack's static friction behind its own loop gain. On a torque actuator the rack's Coulomb friction is
exposed directly and the half-width should be **larger**. Measure it on the Design A drive; start at
0.01 (today's value, deliberately low) so the first drive under-compensates rather than kicking.

**What "LAF 5–10" in the record actually was, and why it must not be reused.** The
`accord-backcalc-…` memory's *"lat-accel per torque 5 at the lane-change band, 9-10 steady"* and route
6f's `latAccelFactorRaw` 6.24 are both **rate-servo** numbers: a constant command drives a constant
wheel *rate*, so the lat-accel-per-command rises without bound as frequency falls, and "9–10 steady" is
just the value at the bottom of the measurement band. On a torque actuator a constant torque gives a
constant angle (balanced by the self-aligning torque), so the DC gain is **finite and smaller**. ⇒
**LAF for Design A is an unknown that must be measured, and the record contains no estimate of it.**
Expect it to land **below** 6.0. **[B]**, but structurally forced.

### 3.6 Kp, Ki and the stability budget for Design A

The small-signal outer-loop gain is `Gc = (kp + lsf)/LAF + friction/threshold` (the friction term is
LAF-independent — `get_friction` returns `±friction·LAF` and the output is divided by LAF). With
`STANDARD_FRICTION_THRESHOLD` ≈ 0.30 the friction slope is `friction/0.30` in torque units.

- At today's live values (kp 0.9, LAF 6.0, friction 0.01) the friction term is **0.033** against a
  proportional term of **0.15** — friction is 18 % of the loop gain. Under the port defaults it was
  60–80 %. The operator's 0.01 has already solved the friction-dominance problem.
- 🛑 **The gain margin scales as 1/LAF, and LAF is about to fall.** If the identified LAF comes back at,
  say, 2.0, then holding `SteerKP` at 0.9 **triples** the proportional loop gain. **Start at
  `SteerKP` 0.3 and raise it only after the LAF is fitted**, not before.
- **Ki.** `AccordTorqueKi` 0.30 is high for a plant that no longer integrates. Halve it to 0.15 for the
  first drive. The operator has already rejected the integrator once on principle (V283); a mis-sized
  LAF with a live integrator is exactly the configuration that hides the error until it is a wallow.

**Rate limits.** No change. ±3/frame is not binding (§1.1) and cutting it would be added lag.

---

## 4. DESIGN B — the EPS stays a RATE servo, StarPilot outputs a TARGET ANGULAR VELOCITY

### 4.1 The control law

```python
# --- Design B, in the units the fork already uses -------------------------------------------
# 1. desired wheel angle, through the SR map (unchanged from today)
curv_des   = (setpoint - latAccelOffset * roll_fade) / max(v**2, 1.0)
angle_des  = degrees(VM.get_steer_from_curvature(-curv_des, v, roll * roll_fade))   # deg, +left

# 2. the OUTER loop is now on ANGLE, and its output is a RATE
angle      = CS.steeringAngleDeg - params.angleOffsetDeg                            # deg
angle_err  = angle_des - angle
rate_ff    = FirstOrderFilter(RC=0.10).update((angle_des - prev_angle_des) / dt)    # deg/s
rate_target= KP_ANGLE * angle_err + FF_RATE * rate_ff                               # deg/s

# 3. the map's inverse is ONE CONSTANT (the map is linear from the origin on V280r2+)
CMD_PER_DPS = 28.96          # 0xE4 counts per deg/s   (derivation in section 0)
torque_cmd  = clip(rate_target * CMD_PER_DPS / 4096.0, -1.0, 1.0)                   # [-1, 1]

# 4. the spring still has to be held -- the servo nulls RATE, not ANGLE, so a held angle
#    needs a standing command.  This term is get_honda_accord_rate_plant_ff's `hold`,
#    and it must SURVIVE into design B:
torque_cmd += k_of_v(v) * angle_des / G_of_v(v)
```

**Why the hold term survives.** The rate servo drives `E = 32·sp − fb` to zero, i.e. it nulls the wheel
*rate*, not the wheel *angle*. With `rate_target = 0` at a held angle the servo commands zero and the
return spring unwinds the wheel at `k(v)·angle` deg/s. So Design B still needs the hold term that
`get_honda_accord_rate_plant_ff` already computes. **Design B is not "replace the plant FF"; it is
"keep the hold term, and drive the move term from an ANGLE error instead of from `d(angle_des)/dt` alone."**

### 4.2 What `AccordRatePlantFF` already does of this — and what is missing

| Design B needs | already in the fork? |
|---|---|
| `angle_des` from curvature through the SR map | ✅ exactly, `curv_des` → `get_steer_from_curvature` |
| `d(angle_des)/dt`, filtered | ✅ `accord_angle_des_rate_filter`, RC 0.10 s |
| the map's inverse (deg/s → command) | ✅ **as `1/G(v)`**, and `G(v)` is the *measured* closed-loop version — strictly better than the map's nominal 141.4 |
| the spring hold term | ✅ `k(v)·angle/G(v)` |
| a move-term clamp for the low-speed jerk blow-up | ✅ `get_honda_accord_ff_move_torque_limit` |
| engage priming so re-engagement does not step `angle_des` | ✅ the inactive branch primes `accord_prev_angle_des` |
| **angle FEEDBACK: `KP_ANGLE · (angle_des − angle)`** | ❌ **missing.** Today the feedback is P/I on **lateral-accel** error, and it goes through `latAccelFactor`. |
| **`rate_gain` = 1.0** | ❌ it is 0.5, i.e. the move term is deliberately half-sized because *"1.0 over-drives entries on the plant"* — which is what you would expect when there is no angle feedback to catch the shortfall |

⇒ **Design B is a two-line change to an existing, flown branch.** Replace the lat-accel P/I with an
angle-error P, and restore `rate_gain` toward 1.0 because the feedback now closes the gap.

### 4.3 The patch plan, concretely

**New toggles** (`common/params_keys.h`, `starpilot/common/starpilot_variables.py`, the Galaxy layout
`starpilot/common/assets/device_settings_layout.json`, and the layout test):

| key | type | default | range |
|---|---|---|---|
| `AccordAngleRateMode` | BOOL | **0** (off) | — |
| `AccordAngleKp` | FLOAT | **2.0** | 0.0 – 6.0, units s⁻¹ |

**In `latcontrol_torque.py`, inside the existing `if self.is_honda_accord and accord_rate_plant_ff:`
block**, after `plant_ff_torque` is computed and before `ff_torque = plant_ff_torque + friction_torque`:

- compute `angle = CS.steeringAngleDeg - params.angleOffsetDeg`;
- `angle_rate_cmd = accord_angle_kp * (angle_des - angle)` in deg/s;
- add `-angle_rate_cmd / gain` (same sign convention and same `G(v)` divisor as the move term, same
  `move_limit` clamp) to the plant feedforward;
- when `AccordAngleRateMode` is on, **set the PID's contribution to zero** — simplest and most
  auditable is `self.pid.update(0.0, ...)` with `freeze_integrator=True`, so `pid_log.p/i` keep logging
  zero rather than silently carrying a second, redundant feedback path. **Do not leave both loops live.**

**Keep unchanged:** the SR map (it is load-bearing here — `angle_des` comes through it, so the refit
matters more under Design B than under Design A), `SteerDelay`, the rate limit, `clip_curvature`.

**Set:** `AccordFFRateGain` **0.5 → 1.0** once angle feedback is live; `AccordTorqueKi` becomes inert
(the PID is muted) — leave the toggle where it is rather than deleting it.

### 4.4 The outer-loop stability question, sized

The outer loop is now `angle_err → rate_target → (inner servo) → wheel rate → ∫ → angle`. With the
inner servo approximated as unity gain plus lag, the open loop is `KP_ANGLE/s · e^{-sT}`, `T` = the
total delay: `SteerDelay` 0.20 s (measured flat on the wire) plus the inner loop's own lag.

| `KP_ANGLE` [s⁻¹] | crossover | phase from 0.20 s delay | phase margin (delay only) |
|---|---|---|---|
| 1.5 | 0.239 Hz | 17.2° | 72.8° |
| 2.0 | 0.318 Hz | 22.9° | 67.1° |
| 3.0 | 0.477 Hz | 34.4° | 55.6° |
| 3.93 | 0.625 Hz | 45.0° | 45.0° |
| 6.0 | 0.955 Hz | 68.8° | 21.2° |

⇒ **`KP_ANGLE` = 2.0 s⁻¹ is the right default and 3.0 is the ceiling for a first drive.** The inner
loop's lag has to come out of that margin: at a ~5–8 Hz closed-loop bandwidth it adds roughly 0.02–0.03 s,
worth a further 2–4° at 0.3 Hz. **[B]**, arithmetic shown so it can be checked.

**Separation of timescales.** A 0.3 Hz outer loop against an inner loop whose crossover resonance is at
**20 Hz** is a factor of ~65. That is comfortable, and it is the same reasoning STATE already records for
the existing patch: *"the rate-plant FF is bandwidth-blind to a 10 Hz inner loop (~2 % perturbation)."*

**The `B7` gate.** The record's standing outer-loop clause — `0.38 × |T(3.9 Hz)| ≤ 0.5`, where 0.38 is the
adverse bound on openpilot's own loop gain at 3.9 Hz and `T` is the inner servo's complementary
sensitivity (`ADV-V292-B` §6.3: 0.4072, PASS; over 0.5 at 9–10 Hz) — is a statement about the **inner**
loop's closed-loop gain, and Design B does not change the inner loop at all. But it constrains
`KP_ANGLE`: the 0.38 figure is today's outer-loop gain at 3.9 Hz, and `KP_ANGLE/ω` at 3.9 Hz is
2.0/24.5 = **0.082**, well under it. ⇒ **Design B as specified makes the B7 clause easier, not harder.**
**[B]**, and worth re-deriving properly if Design B is ever cut.

### 4.5 🛑 The hazard that decides this design

**Nothing StarPilot does to the reference can touch the 20 Hz grinding.** This is measured, not argued:

- **V288 rev 2 flew** (`accord-v288r2-flew-grind-unchanged-excitation-side-class-exhausted`). A setpoint
  pre-filter cave went in, the cave was **LIVE** (b4.5 agrees with the mirror 99.5 %), the D-clamp bind
  duty fell **×0.03 as designed** — and the grinding was **UNCHANGED**: same 19.99 vs 19.93 Hz line
  (KS p 0.18), 258 vs 239 episodes/h, env-peak p50 126 vs 127 (MW p 0.92). **[E]**
- The conclusion recorded there is binding: *"the 20 Hz ring's amplitude is governed by the LOOP's
  damping, not by the reference… do not propose another reference-side filter."*
- The comb patch is the same lesson in the fork: it removes 63–66 % of the camera-locked leg and still
  moves the 0xE4 18–22 Hz band only −2.4/−4.2 dB, against a pre-registered −6 dB null. **[E]**

⇒ **Design B is a TRACKING-QUALITY design, not a grinding fix.** It changes what the command means and
should fix the structural mismatch (no LAF to identify, no integrator, feedforward correct by
construction). It will do **nothing** for the 20 Hz grinding, which needs the firmware-side in-loop
class — V292 or its successor. Any claim to the contrary contradicts V288's flown null.

The 7 Hz high-angle stutter is a different matter: it is P desaturating on a stalled wheel, and Design B
replaces the lat-accel P with an angle P whose command is a *rate*, which cannot saturate the same way
because the map's ceiling (133.6 deg/s) is far above any reachable wheel rate (route 6f, v > 4 m/s:
|steeringRateDeg| p99 **110**, max **161** — and those include manual driving). **[B]**, worth stating
as a prediction to be scored.

---

## 5. Comparison, the operator's rules, and a recommendation

### 5.1 Against the operator's fork rules

The rule, quoted from `HANDOFF-2026-09-13-V291-LOOP-OPENING-BUILT-NOT-CLEARED.md` §5:
> *"The 2026-09-10 fork rule still governs: fork changes for grinding only, no LPF, no added lag, no
> authority cut."*

| rule | Design A | Design B |
|---|---|---|
| **fork changes for grinding only** | ⚠ **Arguable both ways.** The fork change is *enabling* work for a firmware change that removes the grinding's mechanism (loop open ⇒ no 18–22 Hz object, 35 routes). It is not itself a grinding fix. | 🛑 **FAILS as written.** V288's flown null says the reference side cannot reach the 20 Hz ring. Design B is a tracking-quality change. It needs the operator to relax or re-scope the rule. |
| **no LPF** | ✅ adds none. The existing 1.2 Hz jerk filter and 0.10 s rate filter are untouched. | ✅ adds none (reuses the existing 0.10 s `accord_angle_des_rate_filter`). |
| **no added lag** | ✅ none added in the fork. ⚠ The firmware side *removes* the feedback path, which removes the phase it contributed — a change, not a lag. | ✅ none added. An angle-error P term is a lead relative to today's lat-accel error (angle is measured directly; lat-accel is angle through `calc_curvature`). |
| **no authority cut** | ✅ peak 2505 preserved by `k = 0.645`. ⚠ At the identification LAF the *commanded* torque at a given lat accel will change; the **ceiling** does not. | ✅ peak unchanged. The map's rate ceiling 133.6 deg/s is above the reachable range, so the command is not clipped in normal driving. |

### 5.2 Head to head

| | **Design A — torque actuator** | **Design B — rate target** |
|---|---|---|
| firmware work | V279's four cells, rebased onto V282/V292. **Already built once, never flown.** | **None.** V282/V292 as-is. |
| fork work | **four toggle flips**, no code | ~40 lines in one branch + 2 toggles + layout + tests |
| fixes the structural mismatch? | ✅ completely — LAF becomes identifiable, the FF becomes correct, the integrator becomes meaningful | ✅ completely — no LAF in the path at all, and the operator's objection to the integrator disappears with it |
| 20 Hz grinding | ✅ **removes the mechanism** (loop open ⇒ no object, 35 routes) — **[B]**, never driven | ❌ **untouched.** V288's flown null. Needs the firmware side. |
| 7 Hz stutter | ✅ no P on rate error ⇒ nothing to desaturate — **[B]** | ✅ probably, different reason (§4.5) — **[B]** |
| authority | ✅ 2505 preserved | ✅ 2505 preserved |
| what it costs | 🛑 **all electronic damping of the rack.** Damping fraction 0 by construction; V279's own pre-registered risk is a new **1–2.5 Hz wallow**. Everything now rests on a 0.3–0.6 Hz outer loop through a 0.20 s delay. | the fork owns the loop shape, so a fork bug is now a steering bug; and the firmware's 20 Hz resonance stays until a V292-class build lands |
| what it needs before flying | a fresh **LAF and friction identification drive** (§3.5) — the tune cannot be inherited | nothing measured; the plant tables `G(v)`/`k(v)` already exist and were identified on this exact map |
| interpretability from ONE short drive | ⚠ poor — a tune drive *and* a symptom drive | ✅ good — the prediction is tracking quality, readable from `angle_des − angle` |

### 5.3 Recommendation — **[BELIEF]**

**Do Design B first, and hold Design A as the answer if the firmware-side in-loop class runs out.**

Four reasons:

1. **Design B costs no firmware risk and no new measurement.** The plant is already identified on this
   exact map, at this exact authority. Design A's tune is *unknown* and the only instrument that could
   supply it (`torqued`) is the one the record says cannot. A drive spent identifying LAF is a drive not
   spent on the symptom, and the kit's scarcest resource is symptomatic drives.
2. **Design A throws away the damping the kit has spent forty builds learning to shape.** V291/V292's
   whole class is *"open the rate loop above ~8 Hz"* — a **frequency-selective** opening that keeps the
   loop's authority below 8 Hz and its damping where the rack needs it. V279 opens it **at every
   frequency**. The record's own framing makes V292 the measured, bounded version of Design A's idea,
   and it is already built, cleared and waiting for the operator's decision.
3. **The operator has already ruled on the adjacent question.** On V283 he rejected the integrator *"on
   principle as well as on the drive"* because it contradicts what openpilot models its output as. That
   is an argument for making the *command* honest, which is Design B's core, and it is satisfied without
   removing the servo.
4. **Design B's residual is nameable and Design A's is not.** Design B will not fix the grinding, and we
   can say so in advance and pair it with the firmware lever. Design A's residual is *"a new 1–2.5 Hz
   wallow, maybe"* — a symptom nobody has driven and no instrument is pre-registered for.

🛑 **What each design needs FROM THE FIRMWARE SIDE:**

- **Design B needs nothing** — and that is its point. It runs on V282 today and on V292 unchanged (the
  forward path is byte-identical: map ×6, Kp 248, Kd 128, Ki 0, clamps, ×6 gain, peak 2505). ⚠ One
  caveat: V292 lowers the feedback lag pole 16.53 → 9.94 Hz, which changes the inner loop's closed-loop
  phase. `G(v)` is a **DC** gain and is unaffected, but if `AccordFFRateGain` is raised toward 1.0, do it
  on the build that will actually fly, not across a firmware change.
- **Design A needs V279 rebased** onto the current base, re-derived from the built image, with its own
  adversarial pass — and it needs the identification drive **before** any symptom scoring.

🛑 **And one instruction that binds either way:** `AccordRatePlantFF = False` is **not** a conservative
setting. It raises the steady feedforward ×2.4–4.3 (STATE, and §1.4's independent ×2.9 check). It is
safe **only** on a firmware image whose LKAS lane is a torque map. Nobody should flip it "to go back to
stock behaviour" on a rate-servo build.

---

## 6. Residuals and things I did not close

1. **I did not re-derive V279's four cells from its built image.** The table in §3.1 is quoted from
   `docs/BUILD-LINEAGE.md`. Before any Design A flash that must be read from the image, per the
   adversarial-pass rule.
2. **The 133.6 deg/s figure chains three record constants** (map top knot 1032 at idx 240; 16.125736
   wire counts per index; 247.13 E-counts per deg/s). Each is EVIDENCE in its own document; the product
   is my arithmetic and has not been checked against a second method. It is the number Design B's
   `CMD_PER_DPS` rests on, so it deserves one.
3. **`liveTorqueParameters` now reads `liveValid` 1 with `latAccelFactorRaw` 6.24** on route 6f, which
   is a change from the state two memories record. I have **not** edited those memories — reporting only.
4. **`lat_delay` = `liveDelay.lateralDelay` + `get_control_lateral_smooth_seconds(...)`.** I confirmed
   `liveDelay.lateralDelay` = 0.2000 flat on the wire but did not evaluate the smooth-seconds term for
   Honda; the delay budget in §4.4 uses 0.20 s and is therefore slightly optimistic.
5. **I did not verify why the `Accord*` params are absent from `initData.params`.** The consequence is
   closed (defaults match), the cause is not.
6. **`AccordCurvatureLead` and `AccordCurvatureLeadGain` are absent from the live params too**, so the
   patch would run at its code defaults (False / 0.75) if the operator does nothing. That is the
   intended state.

---

**Records read for this document:** `CLAUDE.md`; the `firmware-iteration` skill; memories
`project-starpilot-fork-lateral-state-2026-09-10`, `accord-forks-variable-sr-map-is-too-flat-measured-2026-09-10`,
`accord-starpilot-torque-controller-the-033-multiplier-was-inert`,
`accord-backcalc-the-car-needs-friction-0025-and-laf-5-to-10-torqued-cannot-validate-on-the-modded-eps`,
`accord-honda-kp-ki-scale-never-acted-kp-is-0600-on-all-60-routes`, `accord-lkas-commands-rate-not-torque`,
`accord-scaling-a-setpoint-does-not-scale-its-feedback`,
`feedback-the-operator-runs-force-torque-controller-check-toggles-not-defaults`,
`project-operator-starpilot-toggles-decoded-2026-09-03`, `feedback-openpilot-means-starpilot-dom-branch`,
`accord-v288r2-flew-grind-unchanged-excitation-side-class-exhausted`,
`accord-with-the-loop-open-there-is-no-18-22hz-object`; kit docs `docs/STATE.md` (decision box + FORK
paragraph), `docs/BUILD-LINEAGE.md` (V279, V280 rev 2, V281 rev 3, V282, V283, V292),
`docs/research/FORK-COMB-RECONSTRUCTION-2026-09-13.md`,
`docs/handoffs/2026-09/HANDOFF-2026-09-13-V291-LOOP-OPENING-BUILT-NOT-CLEARED.md`,
`docs/review/ADV-V292-B-LOOP-2026-09-13.md`, `docs/review/ADV-V287-B-UNITS-STRATA-2026-09-06.md`.
