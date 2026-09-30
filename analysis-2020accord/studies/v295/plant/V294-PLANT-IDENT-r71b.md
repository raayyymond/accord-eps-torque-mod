# V294 plant identification: route `75604b0a432fdc89_00000071--a7b8ba5d9d` (kit tag `r71b_v294`)

Subagent "plant", 2026-09-30. Analysis only: nothing was sent, flashed, committed or pushed. The fork and every firmware
artifact were read, never written. Every number below comes from a script in this directory, and its output file sits
next to it. Claims are marked **EVIDENCE** (with the method) or **BELIEF**. Units are the PID's own:
- **T** is the delivered lane torque gp-0x6b38, in T counts (the 427 tap's unit; rail 2461). + means steer right.
- **x** is the wheel-rate operand, in counts, at 8 per deg/s.
- **θ** is the angle in deg and **ω** the rate in deg/s, both + left.
- **u = −T** is the plant input.
- **J** is in T counts per deg/s², **b** per deg/s, **k** per deg, and **F** in T counts.
- To convert to the PID's x unit, divide J and b by 8.

## 0. Bottom line

1. **The 1 kHz lane model the design will rely on is VALIDATED on the drive.** EVIDENCE, `p2_trim_out.txt`.
   - The measured trim (the tap minus the byte-exact feedforward march) matches the byte-exact analytic trim over
     0.5–5 Hz wherever coherence is ≥ 0.5. Gain is ×0.91–1.11 (median 1.02); phase is −6° to +9° (median −0.1°).
   - The measured trim runs about 2 ms behind the analytic one. The tap's alignment is uncertain by ±4 ms.
   - The fb clamp never binds: max |r26| is 637 of 1024.
   - The trim is 1.6–8 % of the feedforward rms by band.
2. **Inertia J ≈ 0.2 T counts per deg/s², identified only at 0–5 m/s (0.1–0.3).** EVIDENCE, J profile `p5c_jprofile_out.txt`.
   - That equals the prior 8e-5 u (0.21), so the shipped K_α/J = 0.2097/0.2 ≈ **1.05** (0.7–2.1 across 0.1–0.3).
   - At 5–10 m/s J is weakly constrained (best 0.5, flat 0.1–1.3). At 10–15 m/s J ≤ 0.3–0.5 is preferred. Above
     15 m/s this drive does not constrain J at all: hands-off cruise excites too little.
3. **The identified plant is heavily DAMPED and friction-dominated, not the prior's lightly damped wheel mode.**
   - The open-plant ζ is 1.3–4.0 by band, against the prior's 0.2–0.35.
   - **EVIDENCE that it predicts better:** on held-out 20 s replays from the command alone, the identified family gives
     rate R² 0.22–0.76. The prior "light-b" world gives −0.73 to −1.88 above 10 m/s.
   - **BELIEF on the physics:** the large b at speed is the vehicle's lateral dynamics acting through the aligning
     torque, lumped into b.
   - This estimator overstates b ×1.7–1.9 at speed in its own control (G3a), so b is uncertain at speed; the `b_lo`
     corner carries that bias correction.
4. **Friction dominates small signals.** EVIDENCE.
   - Coulomb friction is about 76 counts at 3 m/s, falling to 13–16 at 8–12 m/s and 4–8 at 17–27 m/s.
   - The hysteresis band 2F_c/k is 23° at 3 m/s and 1.3° at 8–12 m/s.
   - Low-amplitude dynamic stiffness at 0.3–0.6 Hz is ×4–10 the high-amplitude value (stick).
5. **Transport delay T → wheel acceleration is 2 ms, with a range of 0–6 ms.** EVIDENCE: the 6–20 Hz cross-correlation
   peaks at 2 ms (r 0.45–0.65) and the 4–15 Hz one at 6 ms. The output-error delay scans prefer 0–5 ms.
6. **Above ~8 Hz, T → rate is NOT identifiable from this drive.** EVIDENCE.
   - The IV coherence is ≤ 0.06.
   - The direct estimate there is 0.37× the inverse controller, a feedback artefact.
   - ω → bar shows a magnitude peak at 12–14 Hz (coherence 0.4–0.5), but no clean second-order. BELIEF: a torsion-bar
     / steering-wheel resonance near 13 Hz. This is not identified; the two-mass members are stress cases only.
7. **The acceleration operand's noise is not a grinding risk at any pole tested.** EVIDENCE: the byte-exact lane with
   measured sensor noise.
   - The rate sensor noise is x std 1.93 counts (0.24 deg/s), white at 100 Hz.
   - That gives r26 1.3 counts rms and **0 T counts** at the shipped cells: the y→T quantiser needs |y| ≥ 7.
   - At a 16.5 Hz pole with K_α held, T noise is 0.35 counts rms (≤ 0.11 per 5 Hz band). It is linear in Kp.
   - The tap's 5–25 Hz content matches the march to 0.66–0.87 counts rms.
8. **VERDICT on readiness. The plant is PARTIALLY ready; say it plainly to the design agents.**
   - It reproduces the drive's angle in every band (held-out 20 s angle R² 0.66–0.93).
   - It reproduces the rate at 0–10 m/s (0.76 / 0.54), and beats the prior everywhere at speed.
   - **By my own pre-registered F4 it is NOT READY at 5–10 and 10–15 m/s.** On held-out 1 s windows, the 5–10 m/s
     angle R² is 0.43 and the 10–15 m/s rate R² is 0.10.
   - Above 10 m/s the rate detail is not reproduced (rate R² 0.01–0.10 on 1 s windows, 0.22–0.41 on 20 s), and its
     inertia is unconstrained.
   - No member diverged under the shipped cells (F5 does not fire).
   - Design conclusions must be **robust across the family**; a gain tuned to one member is not supported by this drive.

Symptoms are the operator's to score. Nothing here says anything about how the car felt.

## 1. Pre-registered criteria (`CRITERIA-plant.md`, written before any number) and what fired

| id | criterion | result |
|---|---|---|
| G1 | the live march matches the tap to ≤ 10 counts rms, hands-off | **PASS**: 3.64 counts rms, R² 0.9998 (the null march: 14.8) |
| G2 | d(angle)/dt agrees with x/8 to 2 % | **PASS**: slope 1.020 hands-off (1.0004 on all engaged), phase ≤ 1.7° to 5 Hz |
| G3a | estimators recover a known plant within 15 % | **The estimator of record (multiple-shooting OE) PASSES at ≤ 10 m/s and is BIASED at ≥ 10 m/s**: J +23–37 %, b ×1.7–1.9, k +17–22 %, Fc ×0.46–0.58. The equation-error OLS and IV FAIL the equivalent control at every speed (§3.2) |
| G3b | the zero-lag alignment control | model march against the analytic trim: gain ×0.97–1.12, phase ≤ 10° in 0.5–5 Hz (the up-sampling's cost) |
| F1 | J not identifiable anywhere (CI > ±50 %) | **does not fire**: 0–5 m/s gives 0.1–0.3 (exactly ±50 % around 0.2; borderline, stated) |
| F2 | IV and frequency-domain methods disagree by > ×2 in the best bands | **FIRES as written.** The FD fits degenerate (friction makes the linear FRF amplitude-dependent), and the equation-error IV varies ×1.5–5. Both are structurally unfit for a stick-slip plant (§3.2 control). They were replaced by the output-error estimator, which is controlled |
| F3 | measured trim vs model > 20 % or > 20° in 0.5–5 Hz (coherence ≥ 0.5) | **does not fire**: ×0.91–1.11, −6° to +9° |
| F4 | held-out angle R² < 0.5 or rate R² < 0.3 in a band with ≥ 60 s | **FIRES at 5–10 (angle 0.43) and 10–15 m/s (rate 0.10)** on 1 s windows. 0–5, 15–22 and 22+ have < 60 s held-out and are reported, not gated |
| F5 | any member diverges under the shipped cells | **does not fire** (14 members × 5 bands × 2 replay forms) |
| S1 | J ≠ prior by > ×2 | no (0.2 vs 0.21) |
| S2 | ζ_open < 0.1 or > 0.7 | **FIRES**: ζ_open 1.3–4.0, overdamped in every band |
| S3 | fb clamp binds > 0.1 % | no: never binds (max |r26| 637) |
| S4 | a coherent 13–17 / 18–22 Hz line in T → rate | no in T → rate (coherence ≤ 0.06). ω → bar has a magnitude peak at 12–14 Hz (§4) |
| S5 | trim rms > 25 % of the FF rms | no: 1.6–8 % |
| S6 | OLS vs IV differ by > 30 % on J | **FIRES**: ×1.5–5 on the drive. The control shows both are biased (§3.2) |

## 2. The trim as measured (task 2): `p1_gates.py`, `p2_trim.py`

**Measured trim** = T_tap − quant(T_null(tick)), where T_null is the byte-exact 1 kHz feedforward march from the
route's own command, with every constant read from the V294 image. **Model trim** = T_live − T_null, the same march
with the trim on, fed the 0x18F rate. **Analytic** = the linear 1 kHz chain from the image cells:
- R = g(1−z⁻¹)/(1−pz⁻¹) with a = 1011 and b = 567
- then Kp 960/256
- then taper 254/256
- then the output lag 992/507
- then the gain 5346/32768

It is evaluated at the tap instants over 113 windows of 5.12 s, hands-off engaged.

| f Hz | measured T per deg/s, phase | analytic | gain ratio | Δphase | coherence |
|---|---|---|---|---|---|
| 0.59 | 0.82, 77° | 0.74, 67° | 1.11 | +9° | 0.82 |
| 0.98 | 1.15, 59° | 1.14, 53° | 1.01 | +6° | 0.83 |
| 1.56 | 1.58, 36° | 1.56, 35° | 1.02 | 0° | 0.76 |
| 1.95 | 1.90, 24° | 1.73, 25° | 1.10 | −1° | 0.78 |
| 2.54 | 1.91, 11° | 1.87, 12° | 1.02 | −1° | 0.74 |
| 2.93 | 1.93, 4° | 1.90, 5° | 1.01 | −1° | 0.80 |
| 3.91 | 1.71, −17° | 1.88, −10° | 0.91 | −6° | 0.51 |
| 5.08 | 1.51, −36° | 1.76, −23° | 0.86 | −13° | 0.32 |

- **F3 does not fire.** The measured trim runs about 2.2 ms behind the analytic one over 1–8 Hz (at the −4 ms tap offset).
  - The offset itself is uncertain: the live march and the V293 FF-only record both give −4 ms, while a null-march fit
    gives 0 ms. At the 0 ms offset the equivalent delay would be 8.4 ms.
  - BELIEF: the ECU's 1 kHz x is ~2 ms behind the 0x18F sample.
- **fb clamp.** |r26| = 1024 on **0** engaged ticks; max 637, p99.9 368. The P clamp (15360) binds on 0.058 % of
  engaged ticks, all driver-override frames. EVIDENCE: the byte-exact march.
- **Trim against the feedforward, hands-off engaged** (T counts; the measured column is the tap minus the null march):

| band | FF rms / p99 | trim rms / p99 (model) | trim rms / p99 (measured) | trim/FF rms |
|---|---|---|---|---|
| 0–5 | 314 / 1155 | 25.2 / 132 | 26.0 / 128 | 0.080 |
| 5–10 | 310 / 933 | 19.4 / 95 | 19.5 / 96 | 0.063 |
| 10–15 | 197 / 788 | 9.3 / 43 | 9.8 / 40 | 0.047 |
| 15–22 | 204 / 576 | 5.6 / 25 | 6.3 / 24 | 0.027 |
| 22+ | 184 / 498 | 3.0 / 12 | 4.5 / 16 | 0.016 |

Across all engaged frames, including hands-on, the maximum |trim| is 309 counts.

## 3. The plant (task 1)

### 3.1 What each method gave, in order run

| method | script | outcome |
|---|---|---|
| frequency-domain FRF: direct, IV on the FF torque, IV on the setpoint | `p3_plant_fd.py` | **Unusable for J.** Coherence z–ω is 0.1–0.5 above 1 Hz in cruise, and the fits degenerate (J → 0 or k → 0). Dynamic stiffness at 0.3–0.6 Hz is 200–400 T/deg in low-amplitude windows against 26–92 in high-amplitude ones: friction (stick) dominates the linear FRF. EVIDENCE |
| time-domain equation error: OLS, IV-ff, IV-sp (per-run constants, all frames, tanh friction) | `p4_plant_td.py` | OLS J 0.02–0.13, IV-ff 0.13–0.23 (**OLS → IV moved J ×1.5–5**); b goes negative at speed under IV. The first-stage R² for α is only 0.1–0.47 (weak instruments). A first version with 5 s block constants absorbed the Coulomb term; it is superseded, and its docstring says so |
| **known-truth control of the equation-error estimators** | `p4b_ee_on_synth.py` | In a simulated world (J 0.20, the flown command, the byte-exact lane, 15-count road noise, no outer loop), OLS gives J ×0.64–1.75 and k ×0.38–0.98. **IV-ff, a VALID instrument there, gives J ×0.74–2.41 and b NEGATIVE at speed**: the same pathology seen on the drive. **The equation-error model is misspecified for stick-slip (friction during stick is not F·sgn(ω)), so neither OLS nor IV numbers are decision-grade.** EVIDENCE |
| 20 s free-run output error | `p5_oe_fit.py` | **VOID.** It was run with a c0 sign bug (§7). Its outputs carry a VOID header |
| **multiple-shooting output error (estimate of record)** | `p5b_ms_fit.py` | 1 s windows, each started from the measured θ/ω and the march's exact lane state. The command drives the byte-exact lane, closed through the simulated x. One offset per window. **Its G3a with real per-window offsets recovers J/b/k/F within 11 % at ≤ 10 m/s** (Fc −24 % at 5–10) **and is biased at ≥ 10 m/s** (J +23–37 %, b ×1.7–1.9, Fc ×0.46–0.58) |
| **J profile** | `p5c_jprofile.py` | J fixed at 0.1 / 0.2 / 0.3 / 0.5 / 0.8 / 1.3, with b/k/F refitted and scored held-out (below) |
| bar torque as a motor-side input | `p5b_ms_fit.py --bar` | The equation-error fit suggested the bar absorbs the inertia (coefficient 0.27–0.31, J → 0). **In the output-error test it does not.** The fitted gain → 0.00–0.09 and held-out is unchanged. That BELIEF is not supported. EVIDENCE |

### 3.2 The J profile: how well THIS drive constrains inertia (held-out cost of 1 s windows; lower is better)

| J | 0–5 | 5–10 | 10–15 | 15–22 | 22+ |
|---|---|---|---|---|---|
| 0.1 | **0.187** | 0.741 | **0.814** | 4.83 | 1.494 |
| 0.2 | **0.186** | 0.708 | 0.831 | 4.78 | 1.475 |
| 0.3 | 0.204 | 0.686 | 0.834 | 4.70 | **1.473** |
| 0.5 | 0.279 | **0.671** | 0.880 | **4.66** | 1.484 |
| 0.8 | 0.414 | 0.684 | 0.935 | 4.67 | 1.509 |
| 1.3 | 0.595 | 0.721 | 0.986 | 4.87 | 1.554 |

**EVIDENCE:** J is identified at 0–5 m/s (0.1–0.3; 0.5+ is excluded, at +50 % or more cost). It is weak at 5–10 and 10–15.
It is flat, so unconstrained, at 15–22 and 22+. J is physically a property of the steering hardware. BELIEF: it is
speed-independent, so **0.2 is carried as the nominal at every speed**, with 0.1 / 0.5 / 0.8 corners.

### 3.3 The delivered nominal: the J-profile row at J = 0.2 (`v294_plant.family()["nominal"]`)

Schedule knots sit at the fit windows' mean speeds: 3.1 / 8.0 / 11.9 / 17.0 / 26.9 m/s.

| band | J (T/(deg/s²)) | b (T/(deg/s)) | k (T/deg) | Fc / Fs (T) | ζ_open | undamped √(k/J)/2π | 2F_c/k |
|---|---|---|---|---|---|---|---|
| 0–5 | 0.2 [0.1–0.3] | 4.94 | 6.5 | 76 / 95 | 2.2 | 0.91 Hz | 23° |
| 5–10 | 0.2 [0.1–1.3] | 5.24 | 20.2 | 13.5 / 18.9 | 1.3 | 1.60 Hz | 1.3° |
| 10–15 | 0.2 [≤ 0.5] | 9.76 | 24.3 | 15.8 / 18.6 | 2.2 | 1.75 Hz | 1.3° |
| 15–22 | 0.2 [free] | 20.7 | 79.7 | 7.9 / 10.0 | 2.6 | 3.18 Hz | 0.20° |
| 22+ | 0.2 [free] | 26.4 | 55.8 | 4.4 / 5.6 | 3.95 | 2.66 Hz | 0.16° |

In the PID's x units, J_x = 0.025 T counts per (count/s) and b_x = b/8.

- **CIs.** From the leave-parent-out jackknife of the free-J fit (`p5b_ms_out.txt`, 95 %):
  - 0–5: b ±0.18, k ±12, Fc ±129
  - 5–10: b ±1.4, k ±5.8, Fc ±5.9
  - 10–15: every parameter ±100 % or more
  - 15–22: b ±14, k ±54, Fc ±4
  - 22+: b ±10, k ±26, Fc ±0.9

  Add the G3a bias at ≥ 10 m/s (b high ×1.7–1.9, Fc low ×0.5), which the `b_lo` and `F_hi` corners carry.
- **Two readings of k.** k here is the 1 s-horizon ("dynamic") stiffness, with the < 0.5 Hz part removed by the
  per-window offset. It exceeds the prior hold-map k at 15–22 m/s (80 against 28). BELIEF: the tire's instantaneous
  aligning stiffness before the car yaws. The static hold map is a different quantity. The spring's saturation sat(v)
  is the prior's, fixed and not fitted (BELIEF).

**Family members** (`v294_plant.family()`), each speed-scheduled:
- `nominal`.
- `J_lo`, `J_hi` and `J_hi2` (J 0.1 / 0.5 / 0.8): each is **refitted as a whole** at its J, so it is self-consistent.
- `b_lo`: b ÷1.8 at ≥ 10 m/s, ×0.7 below.
- `b_hi`: b ×1.5.
- `F_lo` and `F_hi`: friction ×0.5 and ×2.
- `tau0` and `tau6`: 0 ms and 6 ms delay.
- `ms_free`: J free per band.
- `light_b`: the prior, BELIEF.
- Stress variants built with `member.with_mode20(f2, zeta2, r2)`; the validation ran `+mode13` (13 Hz, ζ 0.1) and
  `+mode20` (20 Hz, ζ 0.05).

### 3.4 Against the prior identifications

- **Prior** (`rlog-tools/studies/grind/V293-PLANT-IDENT-2026-09-13.md` + the 2026-09-14 memory): J 8e-5 u = 0.21 T;
  ζ 0.2–0.35; mode 1.0–2.1 Hz; Coulomb 0.012 u = 31 T; static 0.020 u = 52 T.
  - **J agrees** where this drive can see it (0–5 m/s).
  - **Friction disagrees in shape.** The prior's single Coulomb value (31 T) is ×2 this drive's at 8–12 m/s (13–16)
    and ×4–7 at 17–27 m/s (4–8), while this drive's low-speed value (76 at 3 m/s) is ×2.4 the prior's. Friction here is
    strongly speed-dependent (tire scrub at low speed, BELIEF). At speed the fit trades friction for damping, and its
    G3a says Fc there is about ×0.5 too low, so read 8–16 T.
  - **Damping disagrees**, as §0.3 says.
- **Redo physics** (`redo_physics_report.md`): its ζ× (0.89 / 1.00 / 1.29 / 1.43 / 1.73 at 5 / 8 / 12.5 / 19 / 26 m/s) were
  computed on the light-b world.
  - My independent exact-pole code (`v294_plant.linear_poles`) reproduces them as 0.88 / 1.00 / 1.29 / 1.43 / **1.60**:
    four match to 0.01, and 26 m/s differs by 8 % (unexplained).
  - **On the identified family the open plant has no oscillatory wheel mode.** With the V294 lane closed, the linear
    loop shows a **3.8–4.2 Hz pair at ζ 0.74–0.87** at ≤ 12 m/s and nothing oscillatory at 17–27 m/s. BELIEF: this is
    the lane's 2 Hz/5 Hz dynamics against J. For J 0.5 it is 2.0–2.8 Hz at ζ 0.87–0.96.
  - This pair is what a stronger trim will move first.

## 4. High-frequency facts and noise (task 3): `p6_hf_noise.py`

- **T → rate, 5–30 Hz: NOT identifiable.** EVIDENCE over 418 windows.
  - The IV coherence (FF torque → ω) is ≤ 0.06 above 8 Hz.
  - The direct estimate has coherence 0.15–0.57, but its magnitude is 0.37× (IQR 0.31–0.45) the inverse of the
    controller, with a +31° phase offset. With the trim closed on the rate, the direct HF estimate tracks −1/C (the
    rate's own noise drives the trim), not the plant.
  - The 50 Hz tap cannot see above 25 Hz, and the modelled 100 Hz torque above 25 Hz is built from the measured rate
    itself, so it is circular.
- **ω → bar (hands-off, the bar a pure output of the motor-side rate).**
  - |H| rises roughly as f from 2 to 8 Hz (9 → 43 bar per deg/s; phase +58° to +78°).
  - It **peaks at 12–14 Hz** (52 bar per deg/s, phase dipping to +46°, coherence 0.41–0.51), falls to 23–28 at
    16–20 Hz, and rises again at 25–30 Hz. The strict mask gives the same shape.
  - A clean second-order wheel-on-bar fit failed: f_t ran to the bound. **BELIEF: a lightly damped torsion-bar /
    steering-wheel resonance near 13 Hz**, consistent with the record's pre-existing 13–17 Hz line.
  - No peak at 18–22 Hz.
  - The two-mass parameters (f2, ζ2, J_w/J) are **not identified**: `+mode13` and `+mode20` are stress cases.
- **Rate sensor noise** (EVIDENCE).
  - At standstill, not engaged, untouched: x std **1.93 counts (0.24 deg/s)**, lag-1 autocorrelation 0.04 (white at
    100 Hz), with a +1.3-count offset.
  - In engaged quiet cruise the 15–50 Hz PSD is about 0.1 counts²/Hz, which is 2.3 counts white-equivalent.
  - The 100 Hz samples cannot show the 1 kHz colour; white at 1 kHz is assumed below (BELIEF).
- **Operand and torque noise through the byte-exact lane** (sp = 0, 60 s, σ_x 1.93):

| pole (a, b) | r26 rms | T rms | T in 5–10 / 10–15 / 15–20 / 20–30 Hz |
|---|---|---|---|
| shipped 2.03 Hz (1011, 567) | 1.28 | **0.000** | 0 / 0 / 0 / 0 |
| 4 Hz, K_α kept (999, 1090) | 2.40 | 0.012 | ≤ 0.002 each |
| 8 Hz, K_α kept (974, 2181) | 4.35 | 0.13 | 0.03–0.04 each |
| 16.5 Hz, K_α kept (923, 4405) | 8.54 | 0.35 | 0.10–0.11 each |
| any pole with b kept at 567 | 1.28 | 0.000 | 0 |

- The shipped trim's sensor-noise torque is **quantised away** by the output stage: T = floor(y·5346/32768), so y must
  reach 7 for T to move by 1.
- The noise is linear in Kp: ×10 gain at 16.5 Hz would give about 3.5 counts rms.
- Measured: the tap against the live march in quiet cruise, 5–25 Hz, gives a residual of **0.66–0.87 counts rms per
  band**, below the 8-count quantiser. No unmodelled HF torque is detectable.
- **Consequence (BELIEF):** for a stronger loop the grinding risk is closed-loop de-damping of HF structure (the
  ~13 Hz resonance, the unidentified 20 Hz object), not sensor noise times gain. This drive cannot size that margin.

## 5. The deliverable simulator and its validation (task 4)

`v294_plant.py` gives:
- `family()`: the members of §3.3.
- `Lane294`: the byte-exact V294 lane, batch, **tick-for-tick equal to the golden model's `lkas_fb_lag` +
  `lkas_rate_pid_tick` on 12,000 random ticks**. Overrides: fb_a, fb_b, fb_clamp, kp, e_shift.
- `simulate()`: 1 kHz, batch.
  - Karnopp stick-slip.
  - Saturating spring.
  - Speed schedule.
  - A 3 ms rate former, back-filled at the start.
  - Transport delay.
  - An optional collocated two-mass mode.
  - Open loop on T, or closed through the lane.
  - x-noise option.
- `linear_frf()`.
- `linear_poles()` and `wheel_mode()`: exact 1 kHz poles.
- `--selftest`: PASS (lane against the golden model, step and mode frequency, friction breakaway, rate former).

`oe_lib.py` holds the segment and window replays. Validation is `p7_validate.py`, on **held-out** data only, with the
route command driving the byte-exact lane and then the scheduled plant, one offset nuisance per segment or window:

| member | band | **20 s free-run** angle R² / rate R² | **1 s windows** angle R² / rate R² / skill vs hold-ω |
|---|---|---|---|
| nominal | 0–5 | 0.93 / 0.76 | 0.92 / 0.24 / 0.80 |
| nominal | 5–10 | 0.81 / 0.54 | **0.43** / 0.43 / 0.82 |
| nominal | 10–15 | 0.87 / 0.41 | 0.78 / **0.10** / 0.83 |
| nominal | 15–22 | 0.66 / 0.24 | 0.71 / 0.01 / 0.83 |
| nominal | 22+ | 0.90 / 0.22 | 0.41 / 0.09 / 0.78 |
| light_b (prior) | 0–5 / 5–10 / 10–15 / 15–22 / 22+ | 0.78 / 0.20 · 0.82 / 0.52 · 0.58 / **−1.88** · 0.77 / **−0.73** · 0.70 / **−0.90** | 0.52 / −1.09 · 0.51 / 0.50 · 0.33 / −1.08 · 0.32 / −0.83 · −0.56 / −0.56 |

- Tap R² is 0.94–0.999 everywhere; it is dominated by the known feedforward.
- Every other member is within about ±0.05 of the nominal. `J_hi2` is worse at 0–5.
- **F4 fires at 5–10 and 10–15 m/s. F5 does not fire.** Full table: `p7_validate_out.txt`.

## 6. What the design agents may and may not rely on

- **Rely on (EVIDENCE):**
  - The byte-exact lane: `Lane294` equals the golden model, and the drive validates the trim's gain and phase at
    0.5–4 Hz.
  - x = 8 counts per deg/s.
  - K_α = 0.2097 T per deg/s² below the pole.
  - J ≈ 0.2 at low speed.
  - Transport delay 0–6 ms.
  - The fb clamp has headroom (637 of 1024).
  - The operand noise is negligible.
  - The prior light-b world predicts this drive worse than the identified family at every speed above 10 m/s.
- **Do not rely on:**
  - J above 10 m/s.
  - b and friction at speed (biased by the estimator).
  - Anything above ~8 Hz (not identifiable here; the ~13 Hz resonance is BELIEF).
  - The long-horizon (< 0.5 Hz) plant, which the per-window offset removes by construction.
  - The fork's outer loop: it is not simulated. The replay feeds the flown command, and the command itself contains the
    outer loop's reaction to wheel motion. EVIDENCE: the FF torque correlates with α at negative lags, 2–8 Hz.
- **Design rule this implies (BELIEF):** score every candidate on the whole family, including `light_b` and the
  two-mass stress members, and prefer candidates whose ranking does not flip across members.

## 7. Defects found in my own work, all fixed before this report (reports, per the brief)

1. **The c0 sign was inverted** in `oe_lib.Batch.c0` and `WindowBatch.c0`: the plant needs c0 = mean(Jα + bω + spring +
   F − u), and the first version returned its negative. Every fit before the fix is VOID:
   - `p5_oe_out.txt` and `p5_oe_strict_out.txt` carry VOID headers;
   - the first p5b and p5b-bar runs were overwritten.

   The G3a synthetic worlds had zero offset and could not see it; the G3a of record now has N(0, 40) per-window offsets.
2. **The rate-former history was initialised flat**, so x read 0 for the first 3 ticks. That gave a spurious trim pulse
   of up to about 130 counts at 50 deg/s at every replay start. It is fixed, and a self-test was added.
3. **Replay windows were banded by their parent segment's speed**: a 6 m/s hard-turn unwind was scored with 12 m/s
   parameters. They are now banded by their own speed.
4. **The schedule knots sat at band centres**: at 0–5 m/s the steep friction-vs-speed curve dropped held-out 1 s rate
   R² from 0.75 to 0.03. The knots are now at the fitted mean speeds.
5. The first p4 variant (5 s block fixed effects) absorbed the Coulomb term. It is superseded.

## 8. Files (all in `analysis-2020accord/studies/v295/plant/`)

- **Criteria:** `CRITERIA-plant.md`
- **Libraries:** `plib.py`, `frf.py`, `oe_lib.py`
- **Deliverable:** `v294_plant.py`
- **Scripts and outputs:**
  - `p1_gates` (G1/G2, sign, clamp)
  - `p2_trim` (task 2)
  - `p3_plant_fd`
  - `p4_plant_td` and `p4b_ee_on_synth`
  - `p5_oe_fit` (VOID outputs kept)
  - `p5b_ms_fit` (estimate of record; `_synth`, `_bar`)
  - `p5c_jprofile`
  - `p6_hf_noise` (task 3)
  - `p7_validate` (task 4)
- **Caches** (gitignored; regenerable with `python plib.py --rebuild` in about 8 s):
  - `_scratch/cache/plant_r71b_v294.npz`
  - `_scratch/*.json` and `*.npz`
