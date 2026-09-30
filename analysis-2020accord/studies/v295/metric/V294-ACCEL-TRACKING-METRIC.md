# The operator's goal metric as an instrument, and V294 scored on it

Subagent `metric`, 2026-09-30. This is analysis only. Nothing was sent, flashed, committed or pushed. No fork file and no firmware artifact was touched.

The operator's goal, verbatim: *"comma LKAS command output vs second derivative of steering angle sensor output."*

- **Code:** `accel_tracking_metric.py` (route id → tables, json, npz) and `accel_tracking_compare.py` (cross-route tables and figures, rebuilt from the saved outputs).
- **Output:** everything is in `out/`. The full text is `out/metric_out.txt`, one block per route, and `out/compare_out.txt`, the cross-route tables.
- **Tags:** every claim below is marked **EVIDENCE**, with its method, or **BELIEF**.
- **Symptoms:** these are the operator's to score. Everything here is a band or a transfer function, not a symptom verdict.

## Bottom line

1. **The metric can be measured from the angle sensor up to about 4–5 Hz on the torque-mode builds, and only up to about 1.4–2.5 Hz on the rate-servo builds.**
   - Method: I compared α_θ (Savitzky–Golay d²/dt² of the 0x14A angle) with α_ω (SG d/dt of the 0x18F rate) on hands-off engaged windows. EVIDENCE.
   - The two agree with coherence ≥ 0.9 and phase within 5° from 0.2 Hz up to:
     - 4.3 Hz on V294;
     - 4.7–5.3 Hz on the V293 routes;
     - 1.4–2.5 Hz on V282/V292, where the wheel accelerates about 50× less.
   - Above that, only α_ω (the rate derivative) is usable. It is not quantisation-limited to 15 Hz.
2. **Scaled against the 0x14A steering-wheel angle, the 0x18F rate (x, the V294 trim's own operand) is not 8 counts per deg/s everywhere.**
   - The angle moves 1.13–1.17× more than the integrated rate within ±20° of centre. Beyond 80° it moves 0.96–0.98×.
   - This holds on all 7 routes and all 4 builds. EVIDENCE: 0.5 s angle-change vs rate-integral spans binned by angle, plus the α_θ/α_ω spectral gain.
   - The 1.19–1.21 centre-to-lock ratio matches the fork's variable-ratio map, 16.84 → 14.17 (1.19).
   - BELIEF on the mechanism: x is rack-side (motor) motion behind a variable-ratio rack.
   - Consequence: on centre, 1 deg/s of steering-wheel rate is about 6.9 counts of x, not 8. That makes the trim's gain per unit of steering-wheel acceleration about 0.86× the design value on centre.
3. **The trim is in the delivered torque, at the design gain and phase.** The metric's closed-loop transfer cannot isolate its effect, and the next item gives the reason. EVIDENCE: the 427 tap regressed per band on the byte-exact FF of the command plus α_ω.

   | band | measured \|K\| | 95 % CI | phase | design | fraction of design | V293 null (3 routes) |
   |---|---|---|---|---|---|---|
   | 0.3–1 Hz | 0.193 | 0.183–0.202 | +157° | 0.202 at +159° | 0.96 | 0.010–0.040 |
   | 1–3 Hz | 0.128 | 0.124–0.132 | +114° | 0.151 at +121° | 0.85 | 0.019–0.026 |
   | 3–8 Hz | 0.060 | 0.056–0.062 | +66° | 0.058 at +68° | 1.03 | 0.001–0.004 |

   - K is in tap counts per deg/s² of α_ω. Phases on V294 match the design to within 7°. The V293 null phases are incoherent.
   - In 1–3 Hz the α-term is 8.7 counts rms against 15.5 counts of FF. The delivered torque's 1–3 Hz content is 11.5 counts, **0.74× of what the command's FF asks for**.
4. **The literal metric is dominated by the fork's reaction to the wheel in 1–8 Hz on the torque-mode builds, V294 included.** There, cmd→α is not what the firmware makes the wheel do. EVIDENCE, three ways:
   - **(a) Pre-registered M4.** The instrument-variable estimate uses desiredLateralAccel as the instrument. It falls outside the H1 CI ×/÷1.25 at 13 of 24 coherent bins on V294, and at 0 bins below 1 Hz.
   - **(b) What the command is made of.** In 1–3 Hz the band-passed command is 0.96 R² the fork's P term and 0.67 R² the wheel angle 40 ms earlier. In 3–8 Hz it is 0.92 R² the P term.
   - **(c) The phase points the wrong way for a torque plant.** α leads the command by +14° to +37° in 1–3 Hz (lag scan −20 to −60 ms), which is the opposite of what a torque actuator can do.
   - Positive control: on V282, where the EPS rate loop dominates, H1 equals the IV and reads the known rate servo. |α/cmd| is roughly proportional to f, the phase is +80° to +105°, and the rate gain is 0.016–0.032 deg/s per count, within a factor of 2 from 0.4 to 5 Hz.
5. **What the transfer looks like against the ideal α = G·cmd (flat, 0°):**
   - **Spring/hold band (≤ 1 Hz), actuator branch:**
     - IV phase is +85° (0–5 m/s) up to ±180° (above 10 m/s), so the command holds angle and does not accelerate the wheel.
     - |α/cmd| is 0.02–0.2 deg/s² per count at 0.4 Hz. H1 rises as f^2.7–3.7 (all speeds).
     - A joint regression puts **0.55–0.95 of the command's variance on k·θ and 0–0.03 on J·α**.
   - **1.4–4 Hz:** H1 is not flat either. On V294 it goes as f^1.1 (all speeds; −0.2 to 2.5 by speed band) at +12° to +23°, which is the fork-feedback signature ((2πf)²/K).
   - **2.9–5.1 Hz, where the IV is coherent:** the actuator branch on V294 reads 0.46–2.9 deg/s² per count. At all speeds it is 1.44 at +41° (2.9 Hz) and 0.99 at −13° (5.1 Hz). The phase scatters from −139° to +161° across speed bands, so **no usable shape can be read from the actuator branch above 1 Hz on these drives**. BELIEF: it is the closest thing to "flat", but it has too few coherent bins to call it a band.
   - **Above about 5 Hz:** the output lag (5.05 Hz) and the loss of coherence roll it off. I cannot resolve that from these drives.
6. **V294 against V293 on the literal metric (gain-phase R², hands-off, all speeds):**

   | band | V294 R² | V293 range | V294 \|G\| | V293 \|G\| range | V294 position |
   |---|---|---|---|---|---|
   | 0.3–1 Hz | 0.37 | 0.08–0.12 | 0.44 | 0.09–0.16 | above |
   | 1–3 Hz | 0.55 | 0.41–0.66 | 1.88 | 1.73–2.05 | inside |
   | 3–8 Hz | 0.16 | 0.26–0.68 | 2.48 | 3.42–4.41 | below every V293 route |

   - The fork also differs between these routes, and the command decomposition shows it changes what the command is. On V294, 0.91 of the 0.3–1 Hz command is the P term; on V293 it is 0.16–0.54. So **these differences cannot be assigned to the trim**.
   - Actuator branch (IV) at the 239 bin-pairs coherent on both builds:

     | band | median V294/V293 | IQR | CI-separated lower | CI-separated higher |
     |---|---|---|---|---|
     | 0.3–1 Hz | 1.08 | 0.76–1.95 | 3 | 3 |
     | 1–3 Hz | 0.78 | 0.34–1.18 | 5 | 0 |
     | 3–8 Hz | 0.86 | 0.50–2.16 | 4 | 1 |

   - The pre-registered prediction (lower gain at 0.5–2 Hz) is **not contradicted and not confirmed**.
   - The only consistent separation is at ≥ 22 m/s, 2.1–3.1 Hz: V294 is 0.16–0.31× r75/r76. That V294 cell rests on 71 s and 2 bootstrap blocks, so it is not decision-grade.

## 0. Criteria: written before computing, and what fired

The criteria text is verbatim in the script header. Post-hoc changes are declared there as P1–P5 and PC2.

| # | criterion (pre-registered) | outcome |
|---|---|---|
| M1 | Measurable where coh ≥ 0.9, gain 1.00 ± 0.10, phase ± 15°. FAIL if the band does not reach 1 Hz. | **As written it reaches 4.3 Hz on V294.** On r70/r75/r76 it gives only 0.78–1.76, 0.2–1.17 and 0.98–1.37 Hz, and **none** on V282/V292. The gain clause is what failed: the α_θ/α_ω gain is the static wheel/rack ratio κ(angle) = 0.96–1.17, not 1. **Adjudicated**: gain inside the measured κ envelope (0.93–1.20), coherence and phase unchanged. That gives 0.2–4.9 Hz (V294), 0.2–4.7/5.3/5.1 Hz (V293), 0.2–1.8 and 0.2–2.5 Hz (V282), and 0.2–1.4 Hz (V292, ±10 % form). **No FAIL**: every route reaches 1 Hz. |
| M2 | Nulls (5 s block-shuffled command, time-reversed command) must read R² ≤ 0.02. Above 0.05 is a FAIL. Welch null coherence ≤ 3/n. | **Rows:**<br>• V294 max 0.018: PASS.<br>• r6c 0.015: PASS.<br>• r39 0.020: PASS.<br>• r70 0.033, r75 0.021 and r76 0.029 break the ≤ 0.02 clause but stay below the FAIL line (WARN).<br>• **r6d FAILS on one row** (1–3 Hz at 0–5 m/s, 21 s, reversed-null 0.209). That row and every row under 30 s is now **VOID** (declared post-hoc) and excluded from the tables.<br>**Welch null coherence:** the median is ≤ 0.04 in every group with ≥ 12 windows and ≤ 0.03 on V294. The 5-window r6d 0–5 m/s group reads 0.34, the 1/n bias. The p95 over 0.3–10 Hz exceeds 3/n in 10 of 42 groups, by up to 1.5×, and never on V294. Read coherence below about 5/n as zero. |
| M3 | Positive control: α_syn = G·u(t − 80 ms) + n, with n = α_θ − κ·α_ω (measured), must recover G within 5 %, lag within 10 ms, and R² within 0.05 of the ceiling. | **FAILS as written on 9–17 of 20–24 rows per route**, mostly in 0.3–1 Hz (G off 5–21 %, lag off 20–50 ms). Cause: the measured noise series is correlated with the command, because κ depends on angle and the wheel/rack motion differs. **PC2** uses the same noise block-shuffled, so it has the same spectrum and is independent of u. It passes on all rows but 0–4 per route: V294 fails only 0.3–1 Hz at 22+ m/s (G −14 %), and the failing rows are all in the ≥ 15 m/s or short-exposure cells. On V294 all speeds, PC2 recovers G at 1.000 / 1.001 / 0.994 and lag 80/80/80 ms, with R² 0.990/0.983/0.629 against ceilings 0.991/0.984/0.641 (0.3–1 / 1–3 / 3–8 Hz). The spectral PC recovers \|H\|/G within 0.99–1.02 and phase within 4° from 0.4 to 5 Hz. **Treat the 0.3–1 Hz lag/G as low-confidence; its R² is fine.** |
| M4 | Closed-loop bias: where coh(la_des, u) ≥ 0.3, the IV must lie inside the H1 CI ×/÷ 1.25, else H1 is BIASED. | **H1 is BIASED above 1 Hz on the torque-mode builds.** Biased bins:<br>• V294 (all speeds): 13/24.<br>• V294 by speed band: 10–12 of 25–31 per band, except 2/38 at 0–5 m/s.<br>• r70: 5/19 (all speeds), and up to 19/30 per speed band.<br>• V282/V292: 2–7 of 24–39.<br>Below 1 Hz: 0–2 biased everywhere. |
| M5 | Surprise if the tap→α plant differs by more than ×1.5 between V293 and V294. | The tap→α IV had too few coherent bins to read. **Replaced** by the trim-footprint regression (section 3), which answers the same question directly: the tap equals FF(cmd) + K·α with K at design on V294 and near zero on V293. |
| pred | V294 cmd→α gain lower than V293 by 1/\|1 + 0.21 L P\|, most at 0.5–2 Hz. | **Not testable on H1** (M4). On the IV the median V294/V293 ratio is 0.78 (IQR 0.34–1.18) in 1–3 Hz and 1.08 in 0.3–1 Hz. Direction consistent, not significant. |

## 1. Signal engineering

- **The streams.** The 0x14A angle is on an exact 0.1° grid at 100 Hz, and the kit record says so too. The 0x18F rate is 0.125 deg/s per LSB (x/8) at 100 Hz.
  - Every stream goes back on its own nominal frame counter (`creep20_loop_id.dejitter`).
  - The angle is taken as the nearest nominal 0x14A sample to each 0x18F instant. The median offset is under 1 ms.
  - The command (0xE4 TX-echo, bus 129) is zero-order-held at the 0x18F instants.
- **The time base is causal.** The FF part of the 427 tap has phase −13° to −20° at 1–3 Hz and −40° to −45° at 3–8 Hz. That is the 5.05 Hz output-lag pole (−19° and −44° at the band centres) with no extra delay. EVIDENCE: trim-footprint fit.
- **Why a raw double difference is useless.** On the angle it has a white-quantiser floor of 0.1/√12·‖h‖ = 707 deg/s² rms, while the signal is about 110 deg/s² rms hands-off.
- **The differentiators.**

  | estimate | filter | noise gain ‖h‖ | passband vs ideal | white-quantiser floor |
  |---|---|---|---|---|
  | α_θ | SG(21, 5), deriv 2 | 476 | within 1 % to 2 Hz, −1.7 % at 3 Hz, −11 % at 5 Hz, −3 dB at 6.8 Hz | 13.7 deg/s² rms |
  | α_ω | SG(9, 3), deriv 1 | 33.8 | within 1 % to 5 Hz, −3.7 % at 8 Hz, −3 dB at 14.6 Hz | 1.2 deg/s² rms |

  - Every spectrum is divided by the SG response, so it is compensated. The band scores use Butterworth band-passes, zero-phase, applied inside each engaged run with the edges trimmed.
- **Measured noise (r71b).** Here "noise" means the part of α_θ incoherent with α_ω (`fig1`). SNR by frequency:

  | frequency | SNR of α_θ |
  |---|---|
  | 0.4–3 Hz | 19–23 dB |
  | 4 Hz | 15 dB |
  | 5 Hz | 8.5 dB |
  | 8 Hz | 3.4 dB |
  | 10 Hz | 0.6 dB |

  - Below 4 Hz the incoherent part is 5× (4 Hz) to about 10⁴× (0.4 Hz) the white-quantiser model. It is physical: κ(angle) and wheel-versus-rack motion.
  - From 8 to 15 Hz it meets the quantiser model, so α_θ is quantisation-limited there.
  - α_ω's quantiser floor is 3–4 decades below its PSD out to 15 Hz.
- **κ(angle): the wheel/rack ratio (EVIDENCE, 7 routes, `fig1` lower left).**

  | \|angle\| | ratio d(angle)/∫(0x18F rate) |
  |---|---|
  | 0–5° | 1.135–1.162 |
  | 5–10° | 1.135–1.168 |
  | 10–20° | 1.128–1.157 |
  | 20–40° | 1.118–1.132 |
  | 40–80° | 1.053–1.058 |
  | 80–160° | 0.974–0.981 |
  | > 160° | 0.961–0.965 |

  - The same shape appears on V282, V292, V293 and V294, so it is the car, not the firmware.
  - Record note, a report and not an edit: "x = 8.00 counts per deg/s exactly" (HANDOFF-2026-09-23) holds against the 0x14A rate field, which is the same x. **Against the steering-wheel angle derivative it is 6.9 counts per deg/s on centre and 8.3 beyond 80°.**
- **The kit's |bar| < 400 hands-off mask is biased for this metric.** EVIDENCE.
  - Hands-off, the 0x18F driver-torque sensor reads the wheel's own inertia: bar ≈ 0.48–0.57 counts per deg/s² on torque-mode routes and about 1.2–1.5 on V282/V292. On r71b the fit is R² 0.33.
  - The |α| p90 is 75 deg/s² at |bar| < 400 and 716 at |bar| ≥ 400.
  - Using that mask cuts V294's 1–3 Hz R² from 0.55 to 0.26.
  - This instrument therefore uses openpilot's own steeringPressed flag, dilated by ±0.5 s.

## 2. The instrument (what each number is)

- **Frames.**
  - "Laterally engaged" means 0xE4 STEER_REQUEST and 0x18F SCA.
  - Hands-off means steeringPressed is false, dilated ±0.5 s.
  - Hands-on means engaged and pressed.
  - Speed bands are 0–5, 5–10, 10–15, 15–22 and 22+ m/s.
  - The command-amplitude tercile is the rms of the 0.3–8 Hz band-passed command over ±2.56 s, split per speed band.
  - The bootstrap resamples 60 s blocks of route time.
- **(a) Transfer function.**
  - H1 = S_uα/S_uu, from Welch 5.12 s Hann windows at 50 % overlap that lie fully inside hands-off engaged time.
  - IV = S_rα/S_ru with r = desiredLateralAccel, reported only where coh(r, u) ≥ 0.3.
  - Both carry 95 % block-bootstrap CIs on |H| and phase, and both are SG-compensated.
  - Nulls: window-permuted and time-reversed command coherence.
- **(b) Scalar score per band (0.3–1, 1–3, 3–8 Hz, plus 0.3–8 Hz).** Two fits:
  - The requested **lag scan**, α_B = G·u_B(t − lag) with lag from −100 to +300 ms. It runs into its edge in the spring band.
  - A **gain-phase fit**, α_B = a·u_B + b·H[u_B] with H the Hilbert quadrature. This gives R², |G| and a phase, where + means α leads.
  - Also reported: sp = map(cmd), the tap T, α_ω, terciles, hands-on, the |bar| mask, nulls, and PC1/PC2.
- **(c) Static nonlinearity.**
  - The 0.3–8 Hz band-passed α is binned against the command at the best lag.
  - Slopes are fitted left and right and at |u_B| < 100 / 100–300 / ≥ 300 counts.
  - "Stuck" share is the fraction of frames with |ω| < 2 deg/s, by |u_B|.
- **(d) Where the command goes.** u = J·α + b·ω + k·θ + F·tanh(ω/2) + c, with 8 Hz low-pass signals and the response advanced by the best lag, fitted per speed band. Reported: each term's variance share and its unique (drop-one) share. Only the broadband form is used; see P5.
- **(e) Trim footprint.**
  - Model: T_B = c·FF(cmd)_B + c'·H[FF_B] + K·α_ω,B + K'·H[α_ω,B], per band and speed.
  - FF is the V293/V294 image surface times the fade, read from the image by `v293_flight_read.cells_for`.
  - The same regression is run on every reference route, which is what makes it a null.
- **(f) Command decomposition.** R² of u_B on the fork P term, on desiredLateralAccel and on the wheel angle, each at its best lag. The slope on the angle gives K, and the H1 that pure feedback would produce is (2πf)²/K.

## 3. V294 (r71b) on the instrument

**Exposure.** 704 s hands-off laterally engaged: 79 / 192 / 205 / 158 / 71 s by speed band. Hands-on 53 s.

**Literal metric, hands-off (gain-phase R² [95 % CI], |G| in deg/s² per 0xE4 count, phase; + means α leads).**

| band | all speeds | 0–5 | 5–10 | 10–15 | 15–22 | 22+ |
|---|---|---|---|---|---|---|
| 0.3–1 Hz | 0.37 [0.26, 0.53], 0.44, +51° | 0.45, 0.44, +53° | 0.40, 0.56, +48° | 0.10, 0.17, +25° | 0.13, 0.10, +89° | 0.22, 0.06, +97° |
| 1–3 Hz | 0.55 [0.47, 0.62], 1.88, +25° | 0.66, 1.30, +37° | 0.58, 2.33, +22° | 0.69, 2.54, +15° | 0.62, 2.71, +14° | 0.30, 0.90, +22° |
| 3–8 Hz | 0.16 [0.12, 0.20], 2.48, +18° | 0.33, 1.68, −1° | 0.12, 2.49, +15° | 0.32, 6.85, +35° | 0.47, 7.40, +44° | 0.35, 3.34, +46° |

- **Lag scan.** In 1–3 Hz, R² 0.55 at lag **−40 ms** (CI −40 to −30), meaning α leads. In 3–8 Hz, R² 0.16 at −10 ms. In 0.3–1 Hz, 0.29 at the −100 ms edge.
- **The other channels.**
  - α_ω gives the same R² as α_θ to within 0.03.
  - **sp = map(cmd)** gives the same R² as the command to within 0.01 on every route. The map is linear here, so sp is not a separate observable. EVIDENCE.
  - **The tap T** gives R² 0.32 / 0.17 / 0.29 on V294 in the three bands. On V293 the tap R² equals the command's (for example 0.66 against 0.65 in 1–3 Hz), because T there is FF(cmd). The drop on V294 is the trim in the delivered torque.
- **Terciles, 1–3 Hz.** The lowest dynamic-amplitude third (rms below 18–30 counts) reads R² 0.13–0.23. The top third reads 0.37–0.74.
- **Nonlinearity.** EVIDENCE for the statistics. The friction/stiction mechanism is BELIEF, because in closed loop the relation mixes both directions.
  - For |u_B| < 60 counts the wheel is at rest 70–82 % of the time.
  - The small-signal slope is 0.37 deg/s² per count at |u| < 100, against 0.89 at 100–300 and 0.54 at ≥ 300.
  - Left and right slopes are 0.624 and 0.605 at all speeds. They split to 0.97/0.75 at 5–10 m/s and 0.60/0.46 at 15–22 m/s.
  - The raw, un-high-passed relation of α to the command has R² 0.004: the hold torque produces no acceleration.
- **Hands-on.** R² 0.30 and |G| 1.12 in 1–3 Hz, against 0.55 and 1.88 hands-off. With the driver's hand on, α per command is about 0.6× the hands-off value.
- **Where the command goes (hands-off, broadband).**
  - k·θ takes 0.68–0.94 of the command variance (unique share 0.67–0.92).
  - J·α takes 0.000–0.026, b·ω 0.000–0.21 (only at 0–5 m/s), and F·sign(ω) up to 0.07.
  - The spring k rises with speed: 9 / 15 / 25 / 43 / 55 counts per degree.
- **Closed loop.** The command decomposition gives P-term R² 0.91 / 0.96 / 0.92 in the three bands. In 1–3 Hz, u_B ≈ −K·θ_B(t − 20…70 ms) with K = 23–53 counts per degree (R² 0.39–0.86). That predicts H1 = 2.2–5.1 deg/s² per count, against the measured |G| of 0.90–2.71, so H1 is a mixture dominated by feedback.
- **A 5 Hz line (surprise).** The r1 config passes a 5.1 Hz line (and one at about 10 Hz) from desiredLateralAccel into the command: coherence 0.81 on r71b against about 0.0–0.03 on r75/r76. It is small: 3.9 counts rms in 4.85–5.35 Hz against 2.1 counts rms in 5.6–6.1 Hz. Its origin is BELIEF (a planner artefact). It happens to be the exogenous probe behind V294's IV at 5.1 Hz: 0.99 deg/s² per count at −13°.

## 4. References

| route | build | fork (initData; Kp read from p/err) | hands-off s |
|---|---|---|---|
| r70_v293 `00000070--717f5a7866` | V293 | 4247cb09e rev 1, generic torque, Kp 0.300 | 765 |
| r75_v293r4 `00000075--6c8687d5bd` | V293 | 08a5a7064 rev 4, plant FF + rate loop, Kp 0.850 | 758 |
| r76_v293r5 `00000076--d0b7ea7e4d` | V293 | e44b6cd31 rev 5, DOB, Kp 1.000; **cache built this session** | 462 |
| r6c `0000006c--2bc842dbac` | V282 | 57410c3b, Kp 0.900 | 2969 |
| r39 `00000039--f56039af87` | V282 | 8a28dcef, Kp 0.800 | 754 |
| r6d_v292 `0000006d--5e7b4d2ceb` | V292 | Kp 0.900 | 541 |

- **Build from the wire.** The trim-footprint regression works as a build fingerprint:
  - K ≈ 0 (≤ 0.04) on r70/r75/r76, which is loop-open V293-class;
  - |K| 0.5–2.5 at +27° to +86° on r6c/r39/r6d, the rate loop reacting to wheel motion;
  - design K on r71b.
  - EVIDENCE for each route's class. Which exact image flew on the references is the record's attribution (BELIEF here).
- **V282/V292 act as a rate servo on the metric.**
  - 1–3 Hz R² 0.68–0.80, but |G| only 0.22–0.26 (α per count is about 8× smaller than on torque mode) at +87° to +95°.
  - Below 10 m/s their commands spend 0.86 to more than 1.0 of variance on b·ω (the share passes 1.0 through collinearity): the command is a rate.
  - The rate loop's reaction to wheel acceleration (|K| 0.80–1.32 in 1–3 Hz) is **6–10× V294's trim** (0.128). This is the size of the inner loop the operator liked, measured on the same axis.

## 5. What the operator's ideal (α = G·cmd, flat, 0°) would need (BELIEF, for the designer)

- On torque mode, 55–95 % of the command holds angle against the spring (k 7–92 counts per degree, rising with speed), and 0–3 % accelerates the wheel.
- A literal "α tracks cmd" at ≤ 1 Hz would need the ECU to supply the hold torque from the angle, a +k·θ term. That is positive feedback on angle, a class this kit has never built. It is also the fork FF's job today.
- Above the wheel mode (about 1–2 Hz) the actuator branch should be closer to flat. This is BELIEF: the V294 IV points at 2.9–5.1 Hz (0.46–2.9 deg/s² per count) scatter too much in phase to confirm it.
- **This metric cannot score a firmware PID change from ordinary driving on the torque-mode builds**, because the fork's P term dominates the command in the very band where a firmware change would act.
- A firmware edit would have to be scored on these instead:
  - the trim footprint (section 3), which is exact and already works;
  - the IV at coherent bins.

  Alternatively the drive needs exogenous command content, which is a fork-side question and out of scope here.

## Surprises and open issues

- **κ(angle) of 1.16 → 0.965.** The x = 8 counts per deg/s claim is qualified, and the trim's on-centre gain per unit of steering-wheel acceleration is 0.86× design. Two methods, 7 routes. The rack mechanism is BELIEF.
- **The kit's |bar| < 400 hands-off mask** deletes exactly the high-acceleration frames. Any past census that used it on hands-off acceleration, jerk or ring content is biased toward quiet frames. BELIEF about which censuses are affected: I did not audit them.
- **The literal metric is a closed-loop, two-direction quantity on torque mode.** This is decision-bearing for the session goal.
- **M3 fails as written** on 9–17 rows per route. PC2 passes on all but 0–4, so 0.3–1 Hz lag/G is low-confidence.
- **M2 WARN** (nulls 0.020–0.033) on r39/r70/r75/r76, **FAIL** on one r6d row, which is now VOID. Welch null p95 reaches up to 1.5× 3/n in 10 of 42 groups.
- **Thin bootstrap.** The IV comparison at 22+ m/s (V294 0.16–0.31× r75/r76 at 2–3 Hz) rests on 71 s and 2 bootstrap blocks. More V294 highway hands-off exposure would decide it.
- **The 5 Hz line** in r1's command: origin unknown, amplitude about 4 counts.
- **Not done:**
  - a byte-exact 1 kHz march for the FF part of the trim footprint (I used the steady-state surface plus a free gain/phase per band; FF gain 0.54–1.00);
  - hands-on analysis beyond the band scores;
  - V292 beyond r6d (r6e and r6f not run);
  - V282 routes 64/65 (not cached).

## Files

All under `analysis-2020accord/studies/v295/metric/`.

**Scripts**
- `accel_tracking_metric.py` (sha256 679417c04a3339f0…). Run it with no arguments, or with `r71b_v294 r70_v293 …`, or with `--route <id>`.
- `accel_tracking_compare.py` (dbc8519e644be9ff…).
- `_build_r76_cache.py` (ed4eafaf18284550…).

**Outputs in `out/`**
- Text: `metric_out.txt` (ea63561dbab06f78…) and `compare_out.txt` (df7caf7ccb39cff0…).
- One `metric_<tag>.json` and one `tf_<tag>.npz` per route. `metric_r71b_v294.json` is fd8c75358c5980cc…; `tf_r71b_v294.npz` is 23748b5ba10a5f15….
- Figures:

  | file | contents |
  |---|---|
  | `fig1_signal_engineering.png` | SG responses, α_θ/α_ω coherence, κ(angle), noise floors |
  | `fig2_cmd_to_alpha_bode.png` | H1 and IV by speed band, with the ideal and the (2πf)²/K feedback curve |
  | `fig3_band_scores.png` | band scores |
  | `fig4_nonlinearity.png` | nonlinearity |
  | `fig5_spring_leak.png` | spring leak |
  | `fig6_command_decomposition.png` | command decomposition |
  | `fig7_trim_footprint.png` | trim footprint against design |

**Determinism.** Two consecutive r71b runs gave byte-identical json and npz, and the r71b json from the full 7-route run matches them. `compare_out.txt` rebuilds identically from the saved files.

**Caches built (gitignored, regenerable)**
- `analysis-2020accord/_scratch/cache/v280/r76_v293r5{.npz,_b4.npz,_marks.json,_params.json}`
- `rlog-tools/studies/grind/_scratch/cs_r76_v293r5.npz`
- `rlog-tools/studies/grind/_scratch/cs_r6d_v292.npz`
- `rlog-tools/_scratch/cache/75604b0a432fdc89_00000076--d0b7ea7e4d/CACHE-POINTER.json`
