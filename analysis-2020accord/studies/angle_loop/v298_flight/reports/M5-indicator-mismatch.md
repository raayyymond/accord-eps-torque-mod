# M5: the on-screen torque bar against what the EPS did (route 79, V298, first angle-loop flight)

**Script:** `analysis-2020accord/studies/angle_loop/v298_flight/m5_indicator.py`. It runs only on the caches. **Measured wall time: 1.65 s.** Outputs go to `_scratch/out/r79/m5/m5.json` and `m5.txt`.
**Inputs:** `r79_fork.npz` (controlsState, carControl, carOutput, carState, liveParameters, carParams) and `r79_a1f5d2_al.npz` (the 0x1AB tap, 0xE4, 0x14A and 0x18F), plus `r71b_v294.npz` as the torque-mode reference.
**Populations:**
- **EPS-engaged:** latActive, 0xE4 request = 1, STEER_CONTROL_ACTIVE, v > 3 m/s. 613.6 s.
- **Hands-off:** EPS-engaged, |0x18F bar torque| < 500, and the fork's O1 override not active. 518.3 s.

All of this is on a 20 Hz grid. The tap is the mean and the max|.| over the last 50 ms, in field LSB (T/8, rail 2461 T = 307.6 LSB).

## The answer to note (3), in the operator's terms

**The bar did not show torque.** On this route it showed the fork's *requested* lateral acceleration, with the road-roll estimate subtracted, divided by **0.3247 m/s²**. That divisor is the **stock** Accord's measured lateral-acceleration ceiling.

**What the bar did:**
- It sat **pinned at full (orange) for 60 % of engaged time**.
- When the EPS's delivered lane torque was above a quarter of the rail, the bar was at full 99–100 % of the time.
- When the EPS was nearly idle (< 25 LSB, 8 % of the rail), the bar was still at ≥ 0.9 on 60 % of the time.
- On straight road it leaned to ≥ 0.3 on 84 % of the time, driven by the roll estimate alone.

**What the EPS did:**
- It never reached half of the rail (the tap's engaged p99 is 114 LSB, max 183).
- The fork's error clip **never bound**.

The bar therefore read "maximum effort" through almost every curve and many banked straights, while the motor was at roughly 10–40 % of its rail. The mismatch the operator felt is real and quantified. It runs in one direction: **the bar over-claims**. It never under-claims, because the case "bar low while the EPS works hard" has zero frames. Neither half-rail nor clip-active work ever occurred.

For contrast, in torque mode (V294, route 71b) the bar was the fork's torque command. That command tracks the same tap with **r = 0.96 signed and 0.93 in magnitude** (0.998 hands-off).

## (a) What branch ran, from the fork source (EVIDENCE)

| item | value | source |
|---|---|---|
| branch | **angle**: `controlsState.lateralControlState.which() == 'angleState'` on **100 %** of rows (`ctl_lat_is_angle`) | `torque_bar.py` `TorqueBar._update_state` |
| formula | `x = clip(((a_act − rollc) + (a_des − a_act)) / CP.maxLateralAccel, −1, 1)` if `carControl.latActive`, else 0. Here `a = κ·vEgo²` and `rollc = roll·9.81·interp(v,[5,15],[0,1])`. **The a_act terms cancel, so x = (a_des − rollc)/maxLatAccel.** Checked numerically: max \|full − reduced\| = 0.000. | same |
| filter | `FirstOrderFilter(rc 0.1 s, dt 1/target_fps)`. The rate is 60 fps on non-tizi (mici, comma 4) and 20 on tizi, so both give τ ≈ 0.1 s. Modelled as an exact τ = 0.1 s on the 20 Hz grid. | `torque_bar.py` `TorqueBar.__init__`; `system/ui/lib/application.py` `_DEFAULT_FPS` |
| CP.maxLateralAccel | **0.32467** (cached carParams). This is `MAX_LAT_ACCEL_MEASURED` for `HONDA_ACCORD` in `torque_data/params.toml`, i.e. the **stock-EPS** torqued fit, set by `interfaces.py` `get_std_params` (`ret.maxLateralAccel = get_torque_params()[candidate]['MAX_LAT_ACCEL_MEASURED']`). The UI reads `CarParamsPersistent` (`ui_state.py`), which is the same struct. | `r79_fork.npz` `carparams_json`; fork source |
| rivian_lateral_mode | **Cannot interfere.** `RivianLateralMode.update` sets `mode=None` unless `CP.brand == "rivian"`, and brand is `honda`. The angle branch is entered by `which()=='angleState'` anyway. | `rivian_lateral_mode.py` |
| torque branch (what the bar used to be) | `-carOutput.actuatorsOutput.torque` | `torque_bar.py` |
| widgets | Both UIs use the same `TorqueBar`: `selfdrive/ui/onroad/starpilot/starpilot_onroad_view.py` and `selfdrive/ui/mici/onroad/hud_renderer.py`. The bar is gated by `EnableTorqueBarWidget`. | grep |

Sign check (EVIDENCE): the bar's sign agrees with the tap's sign on 14/14 frames where both are large, and the signed correlation is +0.72. **Direction was right; magnitude was meaningless.**

## (b) The recomputed bar against the EPS

### Bar shape (EVIDENCE, single method: the recompute; the formula is exact from source)

| population | \|x\| ≥ 0.999 (pinned) | displayed ≥ 0.75 (orange) | displayed < 0.3 |
|---|---|---|---|
| EPS-engaged | **0.597** | 0.709 | 0.113 |
| hands-off | 0.551 | 0.676 | 0.126 |

Pinned fraction by speed band (hands-off): 3–8 m/s 0.24, 8–12.5 m/s 0.38, 12.5–17.5 m/s 0.67, 17.5–22 m/s 0.70, > 22 m/s 0.66.

**Roll on straight road.** Straight means |a_des| < 0.1 m/s²; there were 238 s of it.
- The bar was ≥ 0.3 on **84 %** of straight-road time and pinned on **43 %**.
- |rollc| has median **0.28** m/s², p90 0.53, p99 0.75. |roll| has median 2.09°, p90 3.2°.
- So a typical camber estimate alone (0.28/0.3247 ≈ 0.87) fills the bar.
- |a_des| while engaged: p50 0.20, p75 0.62, p90 1.17, p99 2.63 m/s². **Any a_des above 0.32 m/s² pins the bar.**

### Correlations, lag-searched over ±1 s (EVIDENCE)

| pair | engaged r₀ | hands-off r₀ | best lag (hands-off) |
|---|---|---|---|
| bar vs tap (signed) | +0.722 | +0.737 | 0.00 s |
| **\|bar\| vs \|tap\|** | **0.137** (Spearman 0.151) | **0.102** (Spearman 0.107) | 0.00 s |
| bar vs (θsp − θ) | −0.092 | −0.093 | −1.0 s, at the edge of the search window: no peak |
| \|bar\| vs \|θsp − θ\| | −0.018 | −0.081 | — |
| \|bar\| vs (error / clip) | 0.025 | −0.025 | — |
| bar vs 0x18F bar torque | +0.144 | −0.235 | — |
| *control:* \|tap\| vs \|θsp − θ\| | 0.306 | 0.361 | 0.0 s |
| *reference, V294 torque mode:* fork cmd vs tap | **+0.959** (\|·\| 0.930) | **+0.997** | 0.05 s |

Lag is not the problem: the best lags against the tap are 0–0.05 s. Saturation is the problem.

### The mismatch, quantified (EVIDENCE)

| measure | engaged | hands-off |
|---|---|---|
| P(\|tap\| > 150 LSB, half rail) | 0.001 | 0.000 |
| P(error clip active) | **0.000** | 0.000 |
| **bar < 0.3 while (\|tap\| > 150 or clip)**, i.e. bar under-claims | 0 frames | 0 frames |
| P(\|tap\| > 75, quarter rail) | 0.050 (30.4 s) | 0.027 (14.2 s) |
| P(bar < 0.3 \| \|tap\| > 75) | 0.000 | 0.000 |
| P(bar ≥ 0.9 \| \|tap\| > 75) | 0.992 | 1.000 |
| **bar ≥ 0.9 while \|tap\| < 50 and no clip**, i.e. bar over-claims | **0.530 of time** | 0.520 |
| P(EPS idle (< 50) \| bar ≥ 0.9) | **0.828** | 0.865 |
| P(bar ≥ 0.9 \| \|tap\| < 25) | 0.604 | 0.571 |
| \|bar\| p10/p50/p90 given \|tap\| < 25 | 0.25 / 1.00 / 1.00 | 0.23 / 0.99 / 1.00 |

P(EPS idle | bar ≥ 0.9) by speed band (hands-off): 3–8 m/s 0.24, 8–12.5 m/s 0.62, 12.5–17.5 m/s 0.96, 17.5–22 m/s 0.94, > 22 m/s 0.995. **Above 12.5 m/s, a full bar meant an idle EPS almost every time.**

### The error clip never bound (EVIDENCE, two methods)

1. **carOutput vs carState.** `|co_ang − cs_ang| / ANGLE_ERROR_MAX(vEgoRaw)` on latActive frames without override, pairing carOutput row i with carState row i (published in the same card loop; t_co − t_cs median −0.13 ms). Max 0.994, p99 0.56. No frame sits at the bound (tolerance 1e-3 deg). No frame exceeds it, which also supports the pairing.
2. **The wire.** `|θsp(0xE4) − θ(0x14A)| / emax` with request 1: p99 0.61, max 0.994, and > 0.95 on only 0.02 % of frames.

The controller's own **pre-limiter** command `cc_ang` exceeded the clip on 3.8 % of those frames (p99 3.1×). **The rate/jerk limiter in `apply_steer_angle_limits_vm` held the setpoint back before the error clip could act.** See "Out of scope, noticed".

## (c) What the fork could show truthfully in angle mode

Figure of merit: correlation with |tap|, on route 79, hands-off / engaged. All rows are EVIDENCE except the "cost" column, which is BELIEF from a source read.

| candidate | \|·\| corr with \|tap\| | pinned | what it needs | cost |
|---|---|---|---|---|
| **A. The EPS tap itself, T/2461 (the delivered lane torque, the truthful "torque")** | 1 by construction (50 Hz, 8-T quantum) | at the rail only | The fork does **not** parse 0x1AB today (grep `carstate.py`: no `STEER_MOTOR_TORQUE`). The Accord pt DBC `honda_civic_hatchback_ex_2017_can_generated` already has `BO_ 427 STEER_MOTOR_TORQUE` with `MOTOR_TORQUE : 1\|10@0+`, unsigned 10-bit. The cave's encoding is sign = bit 9 and \|T\|>>3 = bits 0–8, so the fork must decode `T = (−1 if f ≥ 512 else 1)·(f & 511)·8` itself. It is on the same bus as STEER_STATUS (src 1 in the kit cache; `hondacan.CanBus` gives Bosch pt = offset + 1). It can travel in the existing **`carState.steeringTorqueEps`**, which is all zero on this route because Honda never fills it, so **no new cereal field** is needed. Then the angle branch of `torque_bar.py` changes. | ~5 lines in `carstate.py` and ~3 in `torque_bar.py`. **RISK:** the CANParser drops a frame whose CHECKSUM/COUNTER fails, and a counter fail makes `can_valid` false (`parser.py` `MessageState.parse`, `CANParser.can_valid`), which means canError and a disengage. Either prove the cave's 0x1AB keeps byte-2 COUNTER/CHECKSUM valid, or register it with `ignore_checksum`/`ignore_counter` and `freq=nan` (the GAS_SENSOR pattern in the same file). |
| B. Rescaled lateral-accel bar: the same formula with maxLatAccel → 3.0 (`DEFAULT_MAX_LAT_ACCEL` in the same file) and **no roll term** | **0.834** / 0.639 (signed 0.897 / 0.781) | 0.3 % / 0.7 % | UI only, one constant and one term | trivial. Still a fork-side **request**, not the EPS output: it cannot show the EPS saturating or lagging. |
| B′. The same with roll kept, at 3.0 | 0.610 / 0.527 | 0.3 % | UI only | trivial. Roll costs about 0.22 of correlation. |
| C. Setpoint error over the clip, `\|co_ang − cs_ang\| / emax(v)` | 0.334 / 0.286 (\|error\| alone 0.361 / 0.306) | never (max 0.994) | UI only (carOutput and carState are already on the UI SubMaster) | trivial. It reads tracking lag, not effort, and the fork-side angle is the 100 Hz held 0x14A. |
| D. Fork limiter hold-back, `cc_ang − co_ang` | not scored as \|tap\| proxy | — | UI only (carControl and carOutput are both subscribed) | trivial. It shows when the **fork** is withholding the setpoint, which is the stage that actually bound on this route. |
| E. 0x18F driver bar torque | 0.230 / 0.018 | — | already `carState.steeringTorque` | It shows the driver, not the motor. Not a demand indicator. |
| Combination | A as the bar length; colour from C or D (orange when the setpoint is being withheld, or the error approaches the clip) | — | A + UI | A's cost and risk |

Scale, measured (EVIDENCE, least squares through the origin): **|tap| ≈ 52 LSB per m/s² of a_des hands-off** (35 engaged). Half rail corresponds to an a_des of about 2.9 m/s², and the rail to about 5.9 m/s². The planner's own ceiling is `clip_curvature` 3.0 m/s². **BELIEF:** a lateral-accel bar normalised at 3.0 would read close to "fraction of half rail".

## Mechanisms for note (3)

| # | mechanism | strength |
|---|---|---|
| 1 | The bar is a lateral-accel **request** normalised by the stale stock value 0.3247, so it saturates at 0.32 m/s² | **strong** (source, plus 60 % pinned, plus \|corr\| 0.10–0.14) |
| 2 | The roll-compensation term moves the bar on straight or banked road while the EPS is idle | **strong** (84 % ≥ 0.3 on straights; dropping roll raises \|corr\| from 0.61 to 0.83 at 3.0) |
| 3 | The bar lags or leads the wheel | **ruled out** (best lag 0–0.05 s) |
| 4 | The bar shows the wrong direction | **ruled out** (signed +0.72, sign agreement 14/14) |
| 5 | The bar under-reports hard EPS work (the error clip or a near-rail tap) | **ruled out on this route** (0 frames: neither occurred) |

## Out of scope, noticed

- **For note (2), "did not feel like 6×".** The EPS lane torque never reached half rail on this route (engaged p99 114 LSB, max 183 of 307.6). The fork's error clip never bound. The stage that limited the setpoint was the fork's **rate/jerk limiter**: `cc_ang` exceeded the clip on 3.8 % of frames, while `co_ang` stayed ≤ 0.994 of it. Together with the planner's 3.0 m/s² curvature clip (≈ 52 LSB per m/s², so about half rail), this suggests the fork, not the firmware, capped authority on this route. **BELIEF:** whether the setpoint, rather than the firmware gain, is the binding cap is for M-panel colleagues to establish. The numbers are in `m5.json`.
- CP.maxLateralAccel 0.3247 is the stock-EPS fit. I have not checked whether anything else in the angle path reads it.

## Open questions

- Does the V298 cave's 0x1AB keep a valid byte-2 COUNTER/CHECKSUM? The kit wire cache stores only bytes 0–1, so this cannot be checked from the cache. It decides whether option A can be parsed with the checks on.
- Is the device a comma 4 (mici, 60 fps) or a tizi (20 fps)? This does not matter for τ, which is 0.1 s either way.
