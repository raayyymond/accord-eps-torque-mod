# Long control "coast more / no ping-pong" toggle config — 2026-10-20

Fork `accord-PTM` @ `311c4cc0` (on the device). Written by `write_long_coast_config.py` (kit codec, cross-checked
against the fork's Galaxy codec at the commit; every key declared FLOAT in `common/params_keys.h`). **Nothing deployed.**
Import in Galaxy: `toggle-config_long-coast_2026-10-20.json`. Undo: `toggle-config_long-coast_2026-10-20_REVERT.json`.
The `.decoded.json` files are the plain-text view of each.
**Import while parked and off-road:** these are "parked personality keys", and Galaxy's restore
(`the_galaxy.py:_restore_toggle_values`) refuses the whole file with a 403 unless off-road state is confirmed.
Values pass its 25–200 bound check (`validate_personality_advanced_value`).

## The delta (4 keys, all Aggressive personality — the live one)

| key | now | proposed | declared default | reason |
|---|---|---|---|---|
| AggressiveJerkAcceleration | 50 | **100** | 50 | a-change cost while aEgo ≥ 0: 125 → 250. Throttle builds half as fast. |
| AggressiveJerkDeceleration | 150 | **100** | 50 | a-change cost while aEgo < 0: 375 → 250. Removes the 3:1 cost flip at aEgo = 0. |
| AggressiveJerkSpeedDecrease | 150 | **100** | 50 | jerk cost while aEgo < 0: 8.25 → 5.5, equal to the aEgo ≥ 0 value (AggressiveJerkSpeed is already 100). |
| AggressiveJerkDanger | 30 | **100** | 100 | slack penalty for entering 0.75 × desired gap: 30 → 100 (declared default). Stops gap intrusion that must then be corrected. |

Net effect: one symmetric MPC cost set (250 / 5.5 / 100), identical to the operator's Standard personality and
smoother than the declared Aggressive default (125 / 2.75 / 100). Following gap and accel/brake profiles unchanged.

## Code trace (EVIDENCE unless marked)

- `LongitudinalPersonality=0` is **aggressive** — `longitudinal_personality_profiles.py:active_personality_id`: `{0: "aggressive", 1: "standard", 2: "relaxed"}`.
- **Follow gap:** the profile JSON wins. `starpilot_following.py:update` uses `resolve_personality_category(...,"following")` when CustomPersonalities and AggressivePersonalityProfile are on; preset `close` is not `dom_default`, so t_follow = `FOLLOWING_PRESET_CURVES["close"] = (1.25, 1.0)` s over 45→70 mph. **AggressiveFollow 1.0 / AggressiveFollowHigh 0.8 are INERT.** The planner then adds a closing-speed bonus (`longitudinal_planner.py:get_dynamic_t_follow`).
- **Jerk keys:** NOT in the profile JSON, so the scalars are LIVE. `starpilot_variables.py` loads them ×0.01. `starpilot_following.py:update` picks the set by **sign of measured aEgo**: aEgo ≥ 0 → (JerkAcceleration, JerkDanger, JerkSpeed); aEgo < 0 → (JerkDeceleration, JerkDanger, JerkSpeedDecrease). `starpilot_planner.py:publish`: `accelerationJerk = A_CHANGE_COST(250) * acceleration_jerk * jerk_scale` (Accord jerk_scale = 1.0), `dangerJerk = DANGER_ZONE_COST(100) * danger_jerk`, `speedJerk = J_EGO_COST(5.5) * speed_jerk`. `long_mpc.py:set_weights` ('acc' mode): `cost_weights = [x_obstacle, 0, 0, 0, a_change_cost, speed_jerk]`, `constraint_cost_weights = [.., .., .., danger_jerk]` (slack on `(gap − 0.75·desired)`), all × a small `dist_factor` when close.
- **'blended' (experimental) mode ignores most of this**: `a_change_cost = 40`, jerk cost 1.0 hard-coded; only JerkDanger still acts. ConditionalExperimental=1 with CELead/CESlowerLead/CEStoppedLead=1 (read on the device) puts the car in blended mode when a lead is **stopped** (vLead < 1 m/s) or much slower (`conditional_experimental_mode.py:slow_lead`). **This delta therefore acts mainly in chill/acc mode — steady following.**
- **LongitudinalActuatorDelay 0.3 is INERT at 311c4cc0.** The param reaches only `starpilot_toggles.longitudinalActuatorDelay`, whose sole reader is `longcontrol.py:update_old_long`, which has **no caller**. The planner (`action_t`, `get_accel_from_plan*`, reaction times) and modeld use `CP.longitudinalActuatorDelay` = 0.5 (`honda/interface.py`, HONDA_BOSCH). Not changed here; it does nothing either way.
- **LongSmoothSeconds 0.3 is INERT**: `modeld.py:_model_smooth_seconds` returns the default (0.3) unless DeveloperUI is on (device: DeveloperUI=0). It smooths only the model's e2e accel (blended mode).
- **Honda Bosch actuator** (`honda/carcontroller.py`): accel clipped to [−3.5, 2.0]; gas = lookup(force × `bosch_gas_factor`) with an **online learner** that moves the gas factor by `gas_error/50 × force` every 20 ms while in PID state (persisted as HondaGasFactorParams), plus a wind-factor learner; gas rise limited to +60/frame; brake mode on below force −0.12, off above −0.02.

## Route evidence — 8 routes, 2026-10-20 (ad/ae on 83fa2e68c8, af–b4 on 311c4cc0b7)

Read with `long_pingpong_read.py` (fork cereal at 311c4cc0, cached per segment, ≤ 8 s cold, ~2 s cached) and
`long_pingpong_planner_vs_actuator.py` (planner-vs-actuator split, 1.4 s for all routes). b2 had no engagement.
Openpilot long was engaged only 2–6 min per route (selfdriveState.enabled ≈ longActive; not a gas-override artefact),
so the sample is ~21 min of lead-following, ~68 s of it behind a stopped/slow lead (all on af).

| route | follow min | blended duty / mode flips per min (following) | a-change weight values, flips/min (chill) | tFollow | dRel band env median / p90 (m) | dRel ping-pong >1 m / >2 m | cmd→aEgo lag | brake pulses (p50 s, p50 cmd) | gas↔brake switches/min | implied gas gain p50 |
|---|---|---|---|---|---|---|---|---|---|---|
| ad | 2.6 | 2 % / 2.6 | 125/375, 213 | 1.04 | 0.55 / 1.49 | 18 % / 7 % | 260 ms | 4 (7.1 s, −0.12) | 2.7 | 0.50 |
| ae | 2.7 | 3 % / 0.7 | 125/375, 215 | 1.00 | 2.12 / 5.35 | 80 % / 52 % | 350 ms | 9 (3.7 s, −0.18) | 5.0 | 0.53 |
| af | 4.5 | 22 % / 2.7 | 125/375, 89 | 1.25 | 0.46 / 1.19 | 15 % / 3 % | 170 ms | 11 (6.5 s, −0.17) | 5.5 | 0.72 |
| b0 | 4.3 | 3 % / 0.2 | 125/375, 58 | 1.25 | 0.35 / 0.70 | 5 % / 0 % | 520 ms | 20 (3.9 s, −0.34) | 8.8 | 0.52 |
| b1 | 3.3 | 0 % / 0 | 125/375, 33 | 1.25 | 0.68 / 1.54 | 27 % / 5 % | 470 ms | 17 (5.1 s, −0.24) | 9.9 | 0.50 |
| b3 | 1.3 | 7 % / 1.6 | 125/375, 122 | 1.14 | 0.53 / 2.08 | 23 % / 11 % | 410 ms | 3 (0.4 s, −0.50) | 3.4 | 0.61 |
| b4 | 2.5 | 5 % / 0.8 | 125/375, 34 | 1.25 | 0.51 / 1.73 | 25 % / 9 % | 310 ms | 12 (4.2 s, −0.48) | 9.0 | 0.60 |

(lag = cross-correlation peak of 2–8 s band-passed command and aEgo in chill following; brake pulses = ACC_CONTROL
BRAKE_REQUEST runs while following in chill, with the median commanded accel during each pulse.)

**What the wire says (EVIDENCE):**
- **Live tune confirmed on every route:** a-change weight 125 when aEgo ≥ 0 and 375 when aEgo < 0 (= 50/150), jerk
  5.5/8.25, danger 30; tFollow 1.25 s at city speed and 1.0–1.04 s on the 83fa2e68c8 highway routes (the "close"
  profile's 70 mph knot). The weight flips 33–215 times per minute while following.
- **There is no large gap ping-pong.** In the 2–8 s band, dRel moves 0.35–0.7 m (median envelope) on six routes, and
  2.1 m on ae (highway). Ego speed band rms is 0.05–0.13 m/s against the lead's 0.18–0.27 m/s, so the car
  ATTENUATES the lead's speed wobble rather than amplifying it. (The first version of the reader scored the gap error
  against the planner's desired distance; that term carries vLead²/5 radar noise and inflated the share to 65–98 %.
  The reader now scores dRel itself.)
- **What does cycle is gas ↔ friction brake: 2.7–9.9 switches per minute, brake requested 12–44 % of following time,
  pulses typically 4–7 s long at a commanded decel of only −0.12 to −0.5 m/s².** On five of seven routes most brake
  pulses are at commands above −0.3 m/s², a decel that drag and engine braking alone would give. That is the
  "should be coasting more" symptom, read off the bus.
- **The planner participates.** The 2–8 s band is present in longitudinalPlan.aTarget itself (rms 0.03–0.11 m/s²,
  correlation with aEgo 0.45–0.73), and the command equals aTarget in that band. The car's response is 1.2–2.2× the
  command there (BELIEF: part of that is grade/noise in aEgo).
- **Stopped/slow lead (af, 4 episodes, 68 s):** no forward-back oscillation. Each episode is one monotone stop
  (aTarget −2.4 → −0.2, smooth through the mode switch), a standstill hold at dRel 6–8 m with brake, and one launch
  when the lead departs. Blended duty there is 59–92 %, with 1–6 mode flips per episode, but aTarget, the command and
  aEgo each reverse exactly once per episode, so mode flipping does not drive an oscillation. The launch is
  brisk: aTarget steps from +0.05 to +0.9–1.7 m/s² within 0.5 s once the lead reaches ~0.5 m/s at 6–7 m.
  The Accord stop-go launch cap (`get_honda_accord_stop_go_accel_cap`) does not apply, because it exits on radar leads.
- **Gas factor:** implied gain is 0.50–0.72 per route and flat within each route (BELIEF: wind factor assumed 1.0).
  No sign of drift tied to the oscillation.

**Verdict on the ranked causes:** cause 3 (mode flipping) is NOT supported, so there is no CEStoppedLead,
CESlowerLead or IncreasedStoppedDistance change. Cause 2 (gas factor) is NOT supported at this resolution. Cause 1
(the aEgo-sign weight switch) is confirmed live and the planner carries the band, so the delta stands unchanged.
The new dominant finding is the **brake-on threshold** (cause 0 below), and it has no param.

## Ranked diagnosis (why it ping-pongs) — revised after the routes

0. **EVIDENCE (bus) — no coast band in the Honda Bosch actuator mapping.** `honda/carcontroller.py:update_honda_bosch_braking`
   requests friction brake as soon as `accel + hill + wind·factor < −0.12` (`BOSCH_BRAKE_FORCE_ON`) and releases above
   −0.02. Below that point the gas command is not zero yet, so there is no command range in which the car simply
   coasts: every small negative excursion of the plan becomes a 4–7 s brake pulse. **No Galaxy param controls this**
   (params_keys.h at 311c4cc0 has none). The fix is code: a coast deadband, e.g. brake on below about −0.35 and off
   above −0.2, with gas held at zero in between. Not implemented; needs a fork change and its own drive.

1. **EVIDENCE (mechanism) / BELIEF (that it is the cause):** the a-change cost flips 125 ↔ 375 (×3) on the sign of measured aEgo. Throttle comes on cheaply, then the brake-side cost is three times heavier, so decel builds late and the gap overshoots both ways. A cost switched by a noisy sign near zero is a classic limit-cycle source. The delta removes it.
2. **BELIEF:** the Bosch gas-factor learner is an extra integrator on accel error with no delay compensation (plant lag ≈ 0.5 s). During every gap correction it learns in the direction of the transient, which adds overshoot. Needs a code change or a route to confirm (log the gas factor).
3. **EVIDENCE (mechanism):** behind a stopped car, CEM switches acc ↔ blended mode. The two modes use different costs (a-change 250·k vs 40) and blended takes min(MPC, model). Flips at the CEM boundary can produce an accel step. Check `selfdriveState.experimentalMode` / CEStatus in the route before touching CEStoppedLead.
4. **EVIDENCE (mechanism):** `get_dynamic_t_follow` raises t_follow while closing and lets it fall back afterwards: a state-dependent setpoint that pushes harder braking when closing. Code-only.
5. **BELIEF, low:** JerkDanger 30 lets the car enter the 0.75 × gap zone cheaply, then the gap cost pulls it back. Only acts at short gaps.
6. **Ruled out by code:** LongitudinalActuatorDelay 0.3 and LongSmoothSeconds 0.3 (both inert, above); AggressiveFollow/High (inert, the profile wins).

## Not covered by this delta

- **Follow gap:** if more room is wanted, change the Aggressive *following* profile from `close` (1.25 → 1.0 s) to `medium` (1.45 → 1.2 s) in Galaxy's personality-profile editor. That is an edit of the whole LongitudinalPersonalityProfiles JSON document, best done in the UI, so it is not in this file.
- **Accel ceiling:** Aggressive acceleration preset `sport` allows 2.0 m/s² at 0 mph. Switching to `standard` softens launch lunges. Also a profile-editor change.
- **Code changes (not implemented):** gate or slow the Bosch gas-factor learner while following a lead; smooth the aEgo-sign switch in `starpilot_following.py` (e.g. hysteresis or use the planned accel, not measured aEgo).

## What would show it worked

Run `python long_pingpong_read.py <route>` and `python long_pingpong_planner_vs_actuator.py <route>` on the next drive.
- **The flip is gone:** a-change weight shows one value (250) and 0 flips per minute.
- **The planner settles:** band rms of aTarget falls below this table's 0.03–0.11 m/s².
- **Fewer brake pulses:** gas↔brake switches per minute and the share of pulses at commands above −0.3 m/s² fall.
  If this metric does not move, the brake-on threshold (cause 0) is the remaining lever, and it needs code.
- **Revert** if closing a large gap becomes noticeably slow.
