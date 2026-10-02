# M6: the goal criteria on V298, route 79, by speed band and amplitude

**Wall time:** `m6_goal_scoring.py` runs in 7.9 s inside the script and 9.4 s in total. `m6_large_events.py` runs in 1.5 s inside and 3.0 s in total. Both read only the cache, with no rlog reads and no per-sample Python loops.
**Outputs:** `_scratch/out/r79/m6/m6_goal_scoring.{txt,json}` and `m6_large_events.{txt,json}`.
**Route:** r79_a1f5d2_al (V298 A16A, fork Dom 2712e1336). References: r6c and r39 (V282), and r71b_v294 (V294, standing in for V295).
**Labels:** EVIDENCE means measured on the wire or the fork logs, with the method given. BELIEF means modelled or inherited. These are band scores. The operator scores the symptoms.

## 0. Reproduction gate (EVIDENCE)
My vectorised loader rebuilds the drive read's own numbers exactly:
- **Tracking:** 0.989 / 0.976 / 0.895 (8-15 / 15-22 / >22 m/s). The 15-22 turn-hold minimum is 0.900 (n 8).
- **nl_sim dwell-then-jump:** 0.00 / 2.62 / 0.96 / 2.00 / 1.47 / 0.65 / 0.59 per minute.
- **Symptom-instrument dwells/min:** 4.70 / 1.16 / 4.47 / 3.53.
- **18-22 Hz engaged/disengaged:** 1.83.

The fork's error clip also reproduces exactly from the logs. On every carOutput frame, |co_ang − carState angle| ≤ ANGLE_ERROR_MAX(vEgoRaw), with a largest excess of 7e-6°. Source: `carcontroller.py::_update_angle`.

## 1. Exposure (seconds; engaged = request & SCA & 0x18F present; free = not steeringPressed)
| band (m/s) | engaged | free | free by \|θsp\| <5 / 5-20 / >20° | free by \|dθsp/dt\| <20 / 20-60 / >60 °/s | free runs ≥15 s (goal form) |
|---|---|---|---|---|---|
| <3 | 57 | 41 | 20 / 11 / 10 | 29 / 8 / 4 | 0 |
| 3-8 | 136 | 93 | 32 / 26 / 35 | 61 / 17 / 15 | 0 |
| 8-12 | 116 | 106 | 53 / 29 / 24 | 98 / 7 / 1 | 1 (12 s) |
| 12-18 | 182 | 179 | 134 / 41 / 3 | 177 / 2 / 0 | 4 (84 s) |
| 18-25 | 90 | 88 | 36 / 51 / 1 | 88 / 0 / 0 | 1 (40 s) |
| >25 | 89 | 89 | 89 / 0 / 0 | 89 / 0 / 0 | 1 (85 s) |

**The amplitude split is confounded with speed.** Large setpoints (>20°) and fast setpoints (>20 °/s) happen almost only below 12 m/s. At those speeds, driving breaks into pieces shorter than the goal scorer's 15-s run. So the goal's tracking and turn-hold criteria only reach small-to-medium manoeuvres at ≥12 m/s. Large manoeuvres are read in §6 instead, with windows and events.

## 2. Verdict table
| criterion (goal bar) | <3 | 3-8 | 8-12 | 12-18 | 18-25 | >25 | method |
|---|---|---|---|---|---|---|---|
| tracking 0.95-1.05 (≥60 s) | NT | NT | NT (12 s: 0.990) | **FAIL 0.939** [CI 0.854-1.021] | NT (40 s: 0.977) | **PASS 0.989** [0.935-1.007] | OLS on 0.5 Hz LPF, 5-s block bootstrap |
| drive-read bands | — | — | 8-15 NT (24 s) | 15-22 **PASS 0.976** | | >22 **FAIL 0.895**, fragile, see §5 | `angle_loop_drive_read.tracking_and_hold` |
| turn-hold ≥0.90 | NT | NT | NT (n 0) | pass, n 2, min 0.943 | pass, n 1, 1.002 | pass, n 1, 0.997 | drive-read form |
| dwell-then-jump ≤ V282 (dwells/min @0.25) | **FAIL** 7.42 vs 0.37/0.66 | ≈ 0.90 vs 0.86/0.00 | **FAIL** 3.83 vs 0.00/0.44 | **FAIL** 4.94 vs 0.57/0.65 | **FAIL** 4.00 vs 0.00/0.00 | **FAIL** 3.38 vs 0.28/0.00 | `v293_symptom_instruments.dwells` form (r6c / r39) |
| ring presence ≤0.5 % | PASS (UB 0.00) | PASS (UB 0.00) | PASS (UB 1.49*) | PASS (UB 0.00) | PASS | PASS | drive read pooled 0.00 % + my amplitude-clause upper bound |
| F7 = 0 /100 s | 0 (22 s ≥30°) | 0 (68 s) | 0 (17 s) | 0 (4 s) | NT | NT | `strongturn_r32_r33.fixed_thr_episodes` (17 episodes, 0 F7) |
| no new 5-30 Hz line | PASS | PASS | PASS | PASS | PASS (9.0/9.4 Hz 6.4 dB, also on r6c and r71b) | PASS | Welch 256 excess dB vs all 3 refs |
| 18-22 Hz eng/dis ≤ V294 r71b | 1.44 vs 1.35 | **2.12 vs 1.36** | **2.14 vs 1.41** | **1.38 vs 0.94** | **2.00 vs 1.60** | 0.88 vs 1.08 | Welch 256; pooled 1.83 vs 1.23 (V282 3.40/3.92) |
| hard-turn 1.6-3 Hz wheel-rate ≤ V282 | 7.9 vs 3.0/4.5 | **9.6 vs 4.3/4.6** | **6.0 vs 1.5/2.3** | 13.6 (3 s) | NT | NT | w18 band-pass, \|θ\|≥20°, free; pooled 8.48 vs 3.45/4.02 °/s |

NT means not testable: under 60 s, or no qualifying runs or holds. *The 8-12 upper bound comes only from the amplitude clause (18-22 Hz bar ≥ 40 on 3 of ~200 windows). The record's full predicate gives 0 present windows pooled.

**Plain summary.**
- **Pass:** ring, F7 and new lines everywhere they can be tested; tracking at >25 m/s and 15-22 m/s; turn-hold where tested, though n is only 1-8.
- **Fail:**
  - tracking at 12-18 m/s, but its CI straddles 0.95;
  - drive-read >22 m/s, which is fragile (§5);
  - the V282 dwell bar in 5 of 6 bands;
  - 18-22 Hz eng/dis against V294 in 5 of 6 bands. It is still about half of V282's.
  - hard-turn 1.6-3 Hz wheel-rate energy against V282, which is setpoint-driven (§6.4).
- **Not testable:** all tracking and turn-hold below 12 m/s, which is exactly where the large manoeuvres are.

## 3. Tracking split by amplitude (EVIDENCE; 4-s windows inside goal runs, classed by max|θsp_LPF|)
| band | track | demeaned | lag-compensated (best lag) | \|sp\|<5 slope (s) | 5-20 slope (s) | >20 | median excursion ratio <5 / 5-20 |
|---|---|---|---|---|---|---|---|
| 12-18 | 0.939 | 0.941 | 0.977 (460 ms) | **0.815** (44) | 0.948 (32) | — | 0.85 / 1.08 |
| 18-25 | 0.977 | 0.977 | 1.009 (380 ms) | **0.635** (16) | 0.957 (20) | — | 0.72 / 1.09 |
| >25 | 0.989 | 0.989 | 1.008 (260 ms) | 0.986 (84) | — | — | 0.99 |
| 8-12 | 0.990 | — | 1.004 (240 ms) | — | — | 0.952 (8) | — / — (>20: 1.22) |

**Against the fork's pre-limit desired angle** (carControl.actuators.steeringAngleDeg), the results are the same to ±0.003 at ≥12 m/s, because the limiter is ≤5.7 % active there (§6). In the drive-read bands: 0.989 / 0.975 / **0.846** (>22).

**Small corrections at speed are the under-tracked class.** The <5° slopes are 0.64-0.82 at 12-25 m/s, while the 5-20° slopes are 0.95-0.96. Almost all of the deficit is lag: lag compensation lifts every band to 0.98-1.01. This is the design's own pre-declared M-N2 ("small-signal in the dip, in-phase gain ≈ 0.51 (±1°)"), now measured on the car.

## 4. Frequency response θ/θsp, hands-off (EVIDENCE: H1 Welch 10.24 s, 75 % overlap, coherence gate 0.6; * = coherence < 0.6)
| band (windows) | 0.1 Hz | 0.2 Hz \|H\| / phase / lag | 0.5 Hz | 1.0 Hz | −3 dB bandwidth | peak \|H\| | xcorr lag, 2nd method (0.1-2 Hz) |
|---|---|---|---|---|---|---|---|
| 8-12 (3) | 0.99 | 1.01 / −7° / 104 ms | 1.15 / −49° / 278 | 1.36 / −48° / 137 | — (3 windows; unreliable) | 1.43 @1.07 | 70 ms |
| 12-18 (24) | 0.94 | 0.91 / −28° / 399 ms | 0.65* / −53° / 304 | gated | not reached before coherence edge 0.49 Hz | 0.91 @0.2 | 437 ms |
| 18-25 (16) | 0.96 | 0.95 / −23° / 322 ms | 0.76 / −55° / 312 | 0.71 / −46° / 131 | **0.59 Hz** | 0.95 @0.29 | 278 ms |
| >25 (31) | 0.96 | 0.96 / −21° / 293 ms | 0.90 / −39° / 220 | 0.82 / −58° / 165 | **1.07 Hz** | 0.96 @0.2 | 264 ms |
| 8-18 (47) | 0.99 | 0.92 / −21° / 292 ms | 0.63* | 0.50* | 0.39 Hz | 0.92 | 134 ms |
| all >3 m/s, \|sp\|>20 (10) | 1.02 / 66 ms | 1.04 / 62 ms | **1.10 / 50 ms** | 0.86 / 109 ms | >1 Hz | 1.10 | — |
| all >3 m/s, \|sp\|<5 (59) | 0.89 / 852 ms | 0.89 / 541 ms | 0.75 / 287 ms | 0.55* | ~0.6 Hz | 0.89 | — |
| all >3 m/s, \|sp\| 5-20 (65) | 0.91 / 464 ms | 0.90 / 394 ms | 0.66 / 315 ms | 0.53* | ~0.5 Hz | 0.91 | — |

- **Bandwidth.** The measured closed-loop bandwidth is **about 0.4-0.6 Hz at 8-25 m/s and about 1.1 Hz above 25 m/s** (EVIDENCE). The setpoint-to-angle lag is **about 260-440 ms** at 0.2-0.5 Hz above 12 m/s (two methods agree to within about 60 ms at 18-25 and >25).
- **No resonance.** No coherent peak exceeds 0.96 at ≥12 m/s.
- **Design comparison (BELIEF; inherited, not re-derived).** The design pages put the curve-hold crossover at 0.45-0.65 Hz in the G dip (C3-rev2-A §Ki) and give tier-A PM ≥ 58.8° (C3-rev2 §3). Earlier C1 gains put the crossover at about 0.55 / 0.4 / 0.7 Hz at 12.5 / 17 / 26 m/s. **The measured bandwidth is therefore what the design itself set.** The missing peak fits PM ≳ 60°, but that inference assumes a second-order response (BELIEF).
- **Amplitude dependence (EVIDENCE).** In 8-18 m/s, the lag at 0.1 Hz is 1188 / 510 / 148 ms for |sp| <5 / 5-20 / >20°. That is a nonlinear, friction-like small-signal deficit. Above 18 m/s it does not appear (345 vs 347 ms). Large windows lag only 50-66 ms, but they come from lower speeds, so amplitude and speed are confounded.

## 5. The >22 m/s tracking FAIL (0.895)
Each candidate cause, tested against the measurements:

| candidate | test | result |
|---|---|---|
| **Exposure, plus one band-edge transient** | Only one 89-s run, setpoint SD 1.8°. Its last ~1.5 s (t ≈ 1023.7-1025.2 s) is a turn-in at 25→22 m/s: θsp −3 → −15° in about 1 s, θ 2-3.5° behind. The run is then cut by the 22 m/s band edge mid-ramp, so filtfilt cuts across it. | **This is the cause (EVIDENCE).** Dropping the last 1 s gives 0.950; the last 2 s, 0.985. The ≥25 m/s part (87 s) gives 0.980, first half 0.995, second half 0.868. Bootstrap CI for my >25 band: 0.935-1.007. |
| gain deficit | \|H\| at 0.1/0.2 Hz is 0.96/0.96; the lag-compensated slope is 0.964 (whole run) and 1.008 (>25) | small: a ~4 % low-frequency gain shortfall plus phase |
| phase lag | best shift 240 ms (drive-read band), FRF lag 220-370 ms | **real contributor**: the transient is a ramp, and 250-300 ms × 15 °/s ≈ 3.5° |
| the 4.5-6° error clip | clip-active frames in the run: 0.0 %. The largest firmware error, 3.5°, is below the 6.2° bound at 23 m/s. | **ruled out** (EVIDENCE, exact clip reconstruction) |
| the integrator | mean error +0.02°, intercept +0.09°, \|H(0.1 Hz)\| 0.96, tap p95 25 LSB, 0 % at rail | **not the cause.** The steady-state error is nil. The low-frequency lag (300-370 ms at 0.1-0.2 Hz) fits the slow integral (c_I/c_P 1.24 /s in the drive read), but it is not what produced the 0.895. |
| errors-in-variables | 1/reverse slope 0.926 | brackets [0.895, 0.926]; not the explanation |

**Verdict:** the >22 FAIL is a **single-run exposure artefact concentrated in one 1.5-s turn-in at the band edge**. Under it is a real **~250-300 ms ramp-following lag**. It is not the clip, and not a DC integrator deficit. With ≥60 s of one run, the pre-registered clause technically fires. I read the band as **NOT DECISIVE**, not as a gain deficit.

## 6. Large manoeuvres, note 2 (EVIDENCE; `m6_large_events.py`)
### 6.1 Events: peak |desired| ≥ 20° (25 events; medians, with p90 in brackets)
| band | n | \|des\| / \|sp\| / \|θ\| peak ° | peak rate °/s: des / sp / θ | peak \|tap\| LSB (rail 308) | max \|θ−sp\| (firmware) | max \|θ−des\| (end to end) | fraction limited / at 1.2°-per-frame cap | pressed |
|---|---|---|---|---|---|---|---|---|
| <3 | 3 | 266 / 287 / 287 | 164 / 157 / 153 | 84 [118] | 13.9 [16.1] | 97 [104] | 0.91 / 0.75 | 0.42 |
| 3-8 | 18 | 149 / 155 / 154 | 118 / **124** / 126 | 96 [133] | 12.5 [15.6] | 56 [168] | 0.88 / 0.32 | 0.48 |
| 8-12 | 3 | 39 / 32 / 38 | 53 / 90 / 85 | 85 [132] | 11.4 | 39 | 0.39 / 0.18 | 0.06 |
| all | 25 | 138 / 131 / 130 | 82 / 124 / 131 | 92 [138] | 12.5 [15.9] | **55 [126]** | **0.84 / 0.28** | 0.41 |

- Hands-free events only (n 6): limited 0.42, at the cap 0.33, firmware error 12.3°, end-to-end error 35.6°, tap max **183 LSB**.
- Across all events, peak |θ| / peak |sp| is **0.998** (p10 0.986), and peak θ-rate / peak sp-rate is **0.98**.

### 6.2 Who limits the setpoint (carOutput frames while latActive)
| band | limited (\|des−co\|>0.5°) | error clip | 1.2°/frame rate cap | other: VM lateral-accel/jerk, O1 override | of "other", pressed |
|---|---|---|---|---|---|
| <3 | 48.8 % | 0.3 % | 48.4 % | 51.3 % | 62 % |
| 3-8 | **60.3 %** | 0.7 % | 38.8 % | 60.5 % | 71 % |
| 8-12 | 19.9 % | 0.0 % | 15.7 % | 84.3 % | 49 % |
| 12-18 / 18-25 / >25 | 4.7 / 5.7 / 0.0 % | 0 | 4.3 / 3.7 / 0 % | rest | 43 / 43 / 0 % |

### 6.3 Authority used (engaged and free; |tap| by firmware error)
| \|θ−sp\| class | s | \|tap\| median / p90 / max LSB | at rail |
|---|---|---|---|
| 0-1° | 349 | 11 / 41 / 169 | 0 % |
| 3-6° | 36 | 36 / 83 / 173 | 0 % |
| ≥10° | 4.7 | 48 / 109 / **183** | **0 %** |

**Reading for note 2, "large manoeuvres lacking" (EVIDENCE).**
- **Firmware tracking.** The firmware loop follows the setpoint it receives: peak reach 0.998, rate 0.98, about 100 ms behind (12.5° of error at a 124 °/s ramp).
- **The fork limits the setpoint.** In large manoeuvres, the wire setpoint is held back for 84 % of event time (median). At 3-8 m/s its peak rate sits on the fork's 120 °/s cap (124 °/s measured through a 2 Hz LPF). The planner's desired angle runs a median 55° (p90 126°) ahead of the wheel.
- **The clamp is never reached.** The firmware never uses more than **183 LSB ≈ 1464 T, 60 % of the 2461 rail**, even with ≥10° of error. This holds in every band (0.0 % of frames at the rail).
- **Stiffness, not authority.** At low speed, the delivered stiffness is about 8 LSB per degree (c_P ≈ 0.83 tap per 0.1° wire count, from the drive read). The firmware would need roughly 37° of error to reach its clamp.
- **The driver was often on the wheel.** It was pressed for 41 % of large-event frames. Most of the "other" limiting below 8 m/s is the O1 override (setpoint follows the hand).

### 6.4 Hard-turn 1.6-3 Hz wheel-rate energy is commanded (EVIDENCE)
In the same stratum, the wire setpoint's own 1.6-3 Hz rate content is 18.6 / 14.1 / 7.0 °/s at <3 / 3-8 / 8-12 m/s. The wheel's is 7.9 / 9.6 / 6.0 °/s, a ratio of 0.42-0.86. The excess over V282 comes in through the setpoint, not from the loop. The only band with ratio > 1 is 12-18 m/s (1.72), on just 3 s.

## 7. Dwells / ratchet split by amplitude (EVIDENCE; note 4)
**nl_sim dwell-then-jump** (references θsp; computed on r79 only, because the V282 and V294 routes have no angle setpoint):

| band | per min | events by \|θsp\| <5 / 5-20 / >20 | events by setpoint rate <20 / 20-60 / >60 °/s | jump median |
|---|---|---|---|---|
| <3 / 3-8 | 0.00 / 0.00 | — | — | — |
| 8-12 | 1.64 | 2 / 1 / 0 | 3 / 0 / 0 | 0.30° |
| 12-18 | 1.65 | 4 / 1 / 0 | 5 / 0 / 0 | 1.00° |
| 18-25 | 1.33 | 1 / 1 / 0 | 2 / 0 / 0 | 0.25° |
| >25 | 0.68 | 1 / 0 / 0 | 1 / 0 / 0 | 0.30° |

**Symptom-instrument dwells/min** (per-minute in |θ| <5 / 5-20 / >20, each over its own engaged time):

| route | <3 | 3-8 | 8-12 | 12-18 | 18-25 | >25 |
|---|---|---|---|---|---|---|
| r79 V298 | 7.42 [17.5/–/0] | 0.90 [1.7/2.2/0] | 3.83 [4.6/1.9/4.6] | 4.94 [4.8/5.9/–] | 4.00 [6.6/2.3/–] | 3.38 [3.4/–/–] |
| r6c V282 | 0.37 | 0.86 | 0.00 | 0.57 | 0.00 | 0.28 |
| r39 V282 | 0.66 | 0.00 | 0.44 | 0.65 | 0.00 | 0.00 |
| r71b V294 | 37.3 | 8.77 | 6.36 | 9.85 | 10.0 | 2.65 |

**Reading:** all 11 setpoint-referenced dwell-then-jump events are at |θsp| < 20° with a slow setpoint (<20 °/s). None is in large or fast manoeuvres. That makes the ratchet a **small-correction phenomenon at ≥8 m/s**. It sits 4-10× above V282 and 2-5× below V294.

## 8. What can and cannot be concluded
- Dwell rates are counts on 90-180 s per band (11 dwell-then-jump events in total). Treat any per-class rate built on fewer than 5 events as indicative only.
- **Not measured here:** a goal-form tracking or turn-hold score below 12 m/s. The route has no 15-s free run there, so the goal's own definition cannot score it.

## Out of scope, noticed
1. **Torque bar (note 3).** In angle mode the comma-screen bar is `clip(lateral-accel estimate / CP.maxLateralAccel)` (`selfdrive/ui/onroad/starpilot/torque_bar.py::_update_state`, EVIDENCE from source). carParams maxLateralAccel is **0.3247 m/s²**. Without the roll term, my reconstruction puts it at full scale on **about 40 % of latActive frames** (BELIEF: roll omitted). Meanwhile the real lane torque never exceeds 60 % of the rail. The bar and the EPS's own effort are unrelated quantities.
2. The error clip is almost never the binding limiter (≤0.7 % of limited frames). The rate cap and the VM or override stages are.
3. A 9.0-9.4 Hz line (6.4 dB) at 18-25 m/s is also present on r6c (10.2 Hz) and r71b (9.4 Hz). It looks like road or plant, not a new line.
