# The creep-regime 20 Hz line: the rate loop's own crossover mode, not a transmitted mechanical line

Subagent `creep20`, 2026-09-03. Script `creep20_loop_id.py` (this folder; output `_scratch/creep20_loop_id.txt`). Routes r31 (V278 rev 3),
r32/r33 (V280 rev 2, old tune), r34 (V280 rev 2, new tune); caches `analysis-2020accord/_scratch/cache/v280/r3{1,2,3,4}.npz`. Analysis only.

**Symptom (operator's words):** "very very attenuated grind #1 still present at 3–6 mph", engaged, hands light, V280 rev 2. Instrument: the
20 Hz line on the torsion bar (0x18F b0–1), the wheel rate (b2–3) and the CAN-427 delivered-torque tap T (0x1AB) together.

## 0. Headline

1. **The 20 Hz T ripple IS the rate PID's own P+D response to the 20 Hz wheel rate** [EVIDENCE]. The FUN_00028ea6 mirror run open-loop on
   the measured rate with the V280 map reproduces the tap's 18–22 Hz content in every window: amplitude 141 vs 132 (operator's t 338 s), band
   correlation 0.82–0.88, coherence 0.98–0.99, phase a constant +23…+33° (= a 3–4 ms fixed offset between the two CAN streams, not physics).
   Per route the sim/meas amplitude ratio is 1.04–1.14. **D carries slightly more of it than P** (D/P = 1.75 analytically at Kp 295; sim
   D 67 vs P 53 T-counts on r34's creep line windows). Low-passing the rate below 15 Hz removes 79 % of the ripple; freezing the command
   removes 23 % (part of which is Kp falling with idx).
2. **The line is engaged-only and its presence and amplitude scale with the loop's gain Kp(idx), not with torque level, wheel rate, speed or
   angle** [EVIDENCE]. Manual creep: 0 of 132 windows (bar 18–22 amp 13 raw). Engaged creep: idx 0 → 13 % present (amp 21), idx 1–20 → 42 %
   (51), idx 20–60 → 83 % (120), idx > 60 → 73 % (107); Spearman amp↔idx +0.63, amp↔|T| +0.12, amp↔|rate| +0.26. At idx 0 the loop is still
   closed (E = −fb, T ≠ 0) at its lowest Kp 248; the engaged-mode base-assist record is the same at idx 0 and idx 40, so the idx dependence
   isolates the LKAS lane's loop gain.
3. **The frequency is fixed at 20.3–21.0 Hz on all four routes and does not track any state** [EVIDENCE, 491 line windows]: over p10–p90 of
   |rate| (5–93 deg/s, an 18× range) it moves +0.5 Hz where cogging/mesh would move 2.7 → 48 Hz; over speed 1.6–5.2 m/s +0.3 Hz; over angle
   3–212° −0.2 Hz; over |T| 115–959 −0.4 Hz; over idx 11–240 **+0.6 Hz (ρ +0.13, p 0.005)** — the only significant tracker, in the direction and
   size the loop model predicts for Kp 248 → 470 (crossover 21.1 → 21.5 Hz).
4. **The loop's crossover sits at 17–21 Hz with ~35–60° phase margin and a sensitivity peak Ms 2–3 at 19–23 Hz** [BELIEF for the absolute
   margins — the off-line plant estimate has coherence 0.3–0.6; EVIDENCE that |L_in(20)| ≈ 1: the identity in §1.3]. **The D term is what puts
   the crossover there**: with Kd 0 the same plant gives |L(20)| 0.37, crossover 7 Hz, PM 22°, Ms 4.0 at 8.7 Hz (a worse loop, lower); Kd 64:
   |L(20)| 0.51, Ms 3.8 at 8.6 Hz. A 2.5 Hz output-lag pole (1008/253) gives |L(20)| 0.39, Ms 2.0.
5. **It is a lightly-damped closed-loop resonance excited by broadband input, not a self-sustained limit cycle** [EVIDENCE for the two
   hands-light windows, BELIEF in general]: in the operator's t 419–422 s and 437–440 s windows every clamp is at 0.00–0.05 duty — the chain is
   linear — yet the line is present at a stable, moderate amplitude (T ripple 71–75 on a 134–199 level). A linear loop cannot sustain a limit
   cycle; if PM were ≤ 0 the ripple would grow until it railed. Only the t 336–342 s window rails P (0.23), and it is the loudest (bar 173 raw).
6. **Not a mechanical column resonance transmitted by the loop** [BELIEF, from the off-line plant shape]: G = rate/T from 10 to 22 Hz shows a
   ×1.3 bump and a phase falling smoothly −28 → −73° (a ~10 ms effective delay), not the 180° flip and sharp peak of a mechanical mode; and
   a mechanical mode would be present disengaged and would not scale with Kp(idx).
7. **Two tautologies the reader must not mistake for evidence:** (a) at a spectral line inside a closed loop, the "plant" any estimator returns
   is 1/H_Tr = the inverse controller, so L_in(line) = −1 by construction once §1.3's identity holds — the L_in-at-20-Hz number cannot itself
   say limit cycle vs transmitted; (b) T-vs-rate phase equals the controller's phase whether the loop generates or transmits the line.
   The discriminators are items 2, 3, 5 and 6, not the phase of T against the rate.

**What this licenses (sizing statements, not build proposals):** the ripple is set by Kd and the output-lag pole first, Kp second — the open-loop
T 18–22 content on r34's creep line windows goes ×0.63 (Kd 0), ×0.75 (Kd 64), ×0.50 (lag pole 2.5 Hz), ×0.94 (Kp cap 341 = V281), ×1.01
(single-sample fb). But the closed-loop consequence of Kd 0/64 is a loop with its resonance moved DOWN to ~8 Hz with a larger peak (Ms 3.8–4.0)
— the band of the high-angle 7 Hz stutter — so "less D" trades the 20 Hz creep line for a worse 8 Hz loop. That trade is the decision, and the
absolute margins behind it carry the coherence caveat.

## 1. Plant and loop at 10–25 Hz, creep stratum

Stratum: lateral engaged (SCA ∧ STEER_REQUEST), v 1–3 m/s, |bar| < 400 raw, all four routes; runs ≥ 1.28 s; 28.0 s / 25 Welch windows pooled
(nperseg 64 at 50 Hz, 0.78 Hz bins) — r31 8 s, r32 10 s, r34 10 s, r33 has no run long enough. **The creep stratum is thin; every number below
is from 28 s.**

### 1.0 Timing — the part earlier readers did not do [EVIDENCE]
Logged CAN receive times are batch-jittered: raw dt p1/p99 = 0/19.5 ms on 0x18F (frames arrive in pairs), 9.8/30 ms on 0x1AB. A 10 ms error is
half a cycle at 20 Hz. Each stream was put back on its nominal frame counter (fitted period: 0x18F 10.0002–10.0003 ms, 0x1AB exactly 2× it,
0xE4 10.044–10.047 ms = openpilot's own loop; drops detected as steps in the lower envelope of t − k·P). Residual t_logged − t_nominal on 0x18F
and 0x1AB: p50 4.5 ms, p90 8.5 ms, 64 % > 3 ms — the receive latency is a broad 0–10 ms, so the reconstruction matters. Spectra in Part 1 and 4
are taken at the tap's own nominal instants (50 Hz), the 100 Hz streams resampled there with a 1 kHz FIR. End-to-end check: T_sim vs T_meas
at 20 Hz has coherence 0.98–0.99 and a **constant** phase +23…+33° in every window of every route = a fixed ~3.9 ms inter-stream offset (the
tap reads ~4 ms later than the 0x18F rate snapshot it responds to). A constant offset is what a correct clock model leaves behind.

### 1.1 G = rate_x / T, |G| ×10⁻³ deg/s per T count, phase deg (sign −1 applied, same rule as `plant_id_v278r3_tap.py`)

| f Hz | direct \|G\| / ph / coh_Tr | cmd-IV \|G\| / ph / coh_cT / coh_cr | bar-IV \|G\| / ph / coh_qT / coh_qr |
|---|---|---|---|
| 10 | 42.9 / −35 / 0.51 | 67.1 / −28 / 0.64 / 0.79 | 60.0 / −51 / 0.54 / 0.53 |
| 15 | 41.4 / −42 / 0.31 | 95.7 / −42 / 0.39 / 0.63 | 95.3 / −41 / 0.28 / 0.45 |
| 18 | 54.5 / −56 / 0.74 | 57.4 / −54 / 0.56 / 0.46 | 58.4 / −59 / 0.80 / 0.68 |
| **20** | **52.8 / −69 / 0.79** | **71.1 / −64 / 0.31 / 0.45** | **59.1 / −70 / 0.88 / 0.88** |
| 22 | 34.8 / −65 / 0.41 | 51.4 / −73 / 0.32 / 0.29 | 45.1 / −85 / 0.66 / 0.45 |
| 25 | 14.3 / 0 / 0.12 | (Nyquist of the 50 Hz tap — unusable) | |

The tap is 50 Hz: **nothing above 25 Hz is observable on T**; 30 Hz is not measurable on this instrument (bar and rate go to 40 Hz on the 100 Hz
streams, §1.5). nperseg 128 (11.5 s, 5 windows) gives the same picture: 47.5/−62 direct, 54.0/−60 bar-IV at 20 Hz. Per route, direct at 20 Hz:
r31 45.1/−40 (coh 0.63), r32 43.9/−69 (0.70), r34 60.4/−74 (0.94). At the line all three estimators converge on the same value because at a
line any instrument coherent with it returns r/T (§0 item 7). Off the line the coherences are 0.3–0.6 and the estimates scatter ±40 %.
[EVIDENCE at 18–22 Hz; BELIEF for the shape at 10–15 and 22–25 Hz]

Creep idx p10/p50/p90 = 2/12/39 → Kp(idx) 256/295/399 from the LERP X 0,68,112,136,208 / Y 248,512,645,696,696 (read from the V280r2 image).

### 1.2 The D term at 20 Hz [EVIDENCE, arithmetic]
D = ΔE·128>>3 = 16·ΔE per 1 ms tick; on a 20 Hz sinusoid |ΔE| = 2·sin(π·20/1000)·|E| = 0.1256·|E|, so |D|/|P| = 16·0.1256/(Kp/256) =
**2.07 at Kp 248, 1.75 at Kp 295, 1.09 at Kp 470**. D leads P by 90° − 3.6°. The rate PID is a PD loop whose D dominates at the line.

### 1.3 The controller identity: measured T per deg/s vs the firmware's own L_fw(Kp 295, Kd 128, lag 992/507, fb 923/1560, one tick) [EVIDENCE]

| f Hz | \|H_Tr\| meas | ph meas | \|L_fw\| | ph L_fw | ratio | Δph |
|---|---|---|---|---|---|---|
| 10 | 11.6 | −145 | 23.7 | −58 | 0.49 | −87 |
| 15 | 7.4 | −138 | 18.1 | −68 | 0.41 | −70 |
| 18 | 13.5 | −124 | 15.9 | −73 | 0.85 | −51 |
| **20** | **15.0** | **−111** | **14.7** | **−76** | **1.03** | **−35** |
| 22 | 11.8 | −115 | 13.6 | −79 | 0.87 | −37 |

At the line the measured T-per-rate magnitude equals the firmware controller's to 3 %; the −35° is the same ~4 ms stream offset Part 4 finds
(+28°). Off the line (10–15 Hz, coherence 0.3–0.5) the ratio falls to 0.4–0.5: there T is not dominated by the rate response (setpoint motion
and noise). **T's 20 Hz content is the loop's own P+D acting on the 20 Hz rate**, confirmed independently by the time-domain mirror in Part 4.

### 1.4 L_in = L_fw · G, 2–24 Hz [|L(20)| ≈ 1 is EVIDENCE via §1.3; the margins are BELIEF — off-line G has coherence 0.3–0.6]

| G source | Kp | \|L\|/ph @ 15 | @ 18 | @ 20 | @ 22 | PM @ f_c | GM | Ms @ f |
|---|---|---|---|---|---|---|---|---|
| direct | 295 | 0.75/−110 | 0.86/−129 | **0.77/−145** | 0.47/−144 | 90° @ 10.2 Hz | none | 2.03 @ 8.6 |
| direct | 248 | 0.71/−106 | 0.83/−125 | 0.74/−141 | 0.46/−140 | 56° @ 7.2 | none | 1.81 @ 8.6 |
| direct | 341 | 0.80/−114 | 0.91/−133 | 0.81/−149 | 0.49/−147 | 86° @ 10.3 | none | 2.19 @ 8.6 |
| direct | 470 | 0.94/−123 | 1.04/−141 | 0.91/−157 | 0.55/−155 | 35° @ 18.4 | none | 2.64 @ 19.5 |
| cmd-IV | 295 | 1.73/−110 | 0.91/−127 | **1.04/−140** | 0.70/−152 | 40° @ 21.2 | none | 2.34 @ 22.7 |
| cmd-IV | 248 | 1.64/−106 | 0.87/−123 | 1.00/−136 | 0.68/−148 | 45° @ 21.1 | none | 2.08 @ 22.7 |
| cmd-IV | 470 | 2.17/−123 | 1.10/−140 | 1.23/−152 | 0.81/−164 | 24° @ 21.5 | none | 4.31 @ 22.7 |
| bar-IV | 295 | 1.73/−109 | 0.93/−132 | **0.87/−146** | 0.61/−164 | 50° @ 17.6 | 1.75× @ 23.4 | 2.93 @ 22.7 |
| bar-IV | 470 | 2.16/−121 | 1.12/−145 | 1.02/−158 | 0.71/−175 | 24° @ 21.1 | 1.32× @ 22.4 | 4.63 @ 22.7 |

Reading: **|L_in(20 Hz)| = 0.8–1.0 at phase −140…−158°; the loop's unity crossing is at 17–21 Hz and its sensitivity peak (Ms 2–3, rising to
4.3–4.6 at Kp 470) sits at 19–23 Hz — exactly where the line is.** The −145° includes the ~4 ms stream offset (§1.0); correcting it moves the
phase toward −173°, i.e. toward the Barkhausen point — but at the line that is the tautology of §0 item 7 and must not be read as a margin
measurement. The predicted crossover shift with Kp (248 → 470: 21.1 → 21.5 Hz) is the +0.4 Hz that Part 2 measures as +0.6 Hz over idx 11 → 240.

Counterfactual loops (direct G, Kp 295): **Kd 0 → |L(20)| 0.37 ∠+157°, crossover 7.1 Hz, PM 22°, GM 1.42× @ 8.2 Hz, Ms 4.0 @ 8.7 Hz** ;
Kd 64 → 0.51 ∠−163°, PM 38° @ 7.2 Hz, Ms 3.8 @ 8.6 ; lag 960/1014 (10 Hz pole, same DC) → 1.44 ∠−132°, PM 51° @ 21.7 ; lag 1008/253 (2.5 Hz
pole) → 0.39 ∠−152°, PM 123° @ 3.9 Hz, Ms 2.0 @ 8.6 ; fb single-sample ×2 → 0.77 ∠−142°, unchanged. **The 20 Hz mode exists because Kd 128
lifts the loop gain there; take D away and the loop's resonance drops to ~8 Hz with a larger peak.** [BELIEF — same coherence caveat]

### 1.5 Bar vs rate: what the operator feels [EVIDENCE — same 0x18F frame, no inter-stream timing]
H_qr = bar per deg/s of rate_x at 15/18/20/22 Hz: 18.3/−71°, 17.7/−79°, **20.3/−70° (coh 0.88)**, 11.6/−63°; on the 100 Hz streams to 40 Hz:
22.3/−73 (15), 22.4/−66/coh 0.94 (20), 12.1/−83 (25), 7.3/−80 (30), 4.5/−66 (35), 4.4/−65 (40). Phase ≈ −70° with |H| falling with f is the
spring relation bar ≈ −k·θ_column: **at 20 Hz the column oscillates under the motor while the hand wheel stays put, and the torsion bar reports
the twist** (a wheel dragged along would read +90°). This is the mechanical picture, not a discriminator — both hypotheses predict it.
Pooled creep PSD lines 12–45 Hz: bar 20.12 Hz ×4.0, rate 20.20 Hz ×4.2; bar PSD 358/249/3.9/1.3 at 10/20/30/40 Hz (no 30 or 40 Hz line).

## 2. Frequency vs state [EVIDENCE]
2 s windows, step 0.5 s, engaged, v < 6 m/s, all routes: 909 windows, line present (prominence ≥ 8 over the local floor and bar 18–22 amp ≥ 40)
in 491 (54 %); 197 of 401 creep windows. f_line mean 20.61, sd 2.03, p10/p50/p90 18.72/20.32/23.45 Hz; the rate's line agrees with the bar's
within 0.5 Hz in 73 %.

| route | build | n | f mean ± sd | p10/p90 | \|rate\| p10/p90 deg/s | v m/s | \|T\| p50 | idx p50 | amp p50 |
|---|---|---|---|---|---|---|---|---|---|
| r31 | V278 rev 3 | 123 | 20.33 ± 2.02 | 18.4/23.5 | 6.4/74.7 | 1.7–5.1 | 387 | 33 | 109 |
| r32 | V280r2 old tune | 57 | 20.99 ± 1.80 | 19.4/23.4 | 3.5/82.6 | 1.0–4.3 | 195 | 16 | 77 |
| r33 | V280r2 old tune | 109 | 20.87 ± 1.99 | 19.1/23.9 | 6.2/97.6 | 1.7–4.5 | 373 | 52 | 116 |
| r34 | V280r2 new tune | 202 | 20.54 ± 2.08 | 18.7/23.3 | 5.1/101.7 | 1.7–5.4 | 455 | 40 | 107 |

| state | Spearman ρ (p) | OLS slope | Δf over p10–p90 | a proportional law would give |
|---|---|---|---|---|
| \|rate\| 5.2–92.8 deg/s | +0.09 (0.039) | +0.006 ± 0.005 Hz per deg/s | **+0.50 Hz** | cogging/mesh: 2.7 → 47.9 Hz |
| v 1.6–5.2 m/s | +0.06 (0.17) | +0.09 ± 0.13 Hz per m/s | +0.33 Hz | tyre/road: 9.5 → 31.9 Hz |
| \|angle\| 3–212° | +0.01 (0.87) | −0.001 ± 0.002 | −0.17 Hz | — |
| \|T\| 115–959 | −0.04 (0.42) | −0.000 ± 0.001 | −0.38 Hz | — |
| **idx 11–240** | **+0.13 (0.005)** | +0.003 ± 0.002 Hz per idx | **+0.60 Hz** | loop: Kp 248 → 470 predicts +0.4 Hz (§1.4) |
| \|bar\| 141–1690 | +0.02 (0.73) | — | −0.19 Hz | — |

By |rate| tertile: 2.3–10.5 deg/s 20.49 Hz, 10.5–51.6 20.47, 51.6–170 20.89. By idx: 0 → 18.89 ± 1.46 (n 12), 1–20 → 20.54 ± 1.47, 20–60 →
20.46 ± 1.45, > 60 → 20.84 ± 2.54. By speed: < 1 m/s 20.39, 1–2 20.29, 2–3 20.56, 3–6 20.74. **Verdict: fixed at ~20.5 Hz; not motor speed,
not road speed, not angle, not torque; a weak rise with Kp(idx) of the size the loop model predicts.** Same on rev 3 (map ×2) and V280 (×6),
old and new StarPilot tune. Manual creep (132 windows, |bar| p50 1966 — hand-over-hand parking): **0 present, bar 18–22 amp 13/26 raw p50/p90.**

## 3. Excitation [EVIDENCE]
- **No 20 Hz line in the 0xE4 command.** cmd PSD in the creep pools falls 133 → 15.1 → 5.5 → 4.3 from 10 to 40 Hz, most prominent 12–45 Hz
  line 29.6 Hz ×2.0 (nothing). P(cmd changes frame to frame) 0.96–1.00 — no 20 Hz staircase; |Δcmd| autocorrelation has only a mild lag-5 bump
  (+0.35…+0.45 vs +0.14…+0.38 at lags 3/6), the planner's 20 Hz cadence leaking faintly. Coherence cmd↔T 0.31–0.56 and cmd↔bar 0.37–0.48 at
  18–22 Hz is the outer loop echoing the ripple (openpilot's controller reads the 100 Hz angle/rate), not driving it; freezing the command in
  the open-loop mirror removes 23 % of T's 18–22 content, part of which is Kp falling as idx drops (§4).
- **Presence and amplitude follow the loop's gain, not the torque level.** Creep windows: amp↔idx ρ +0.63, amp↔cmd +0.33, amp↔|rate| +0.26,
  amp↔|T| +0.12, amp↔|bar| +0.12. By |T|: 1–100 → 27 % present (amp 39), 100–300 → 59 % (75), > 300 → 47 % (68). By idx: **0 → 13 % (21),
  1–20 → 42 % (51), 20–60 → 83 % (120), > 60 → 73 % (107).** Engaged idx > 10 and |T| > 100: 70 % present, amp 92.
- **The line is never seen with the rate loop open.** When engaged the loop is closed even at idx 0 (E = −fb, T ≠ 0: no engaged window has
  |T| < 16), and 13 % of those windows carry a faint line at Kp 248; disengaged (S = 0, the LKAS PID does not run) 0 %. Engaged-mode base-assist
  is the same at idx 0 and idx 40, so the 13 % → 83 % step is the LKAS lane's loop gain, not the engaged base-assist change.

## 4. Chain mirror on the operator's seconds and on every creep line window [EVIDENCE]
V280 map (image), Kp(idx), Kd 128, ZOH command at 1 kHz, two-sample fb, lag 992/507, gain 5346, open loop on the measured rate (1 kHz FIR
reconstruction of the de-jittered 0x18F rate). T_sim sampled at the tap's instants; 18–22 Hz amplitudes at 50 Hz (and at 1 kHz for the sim).

| r34 window | v | idx | \|bar\| | \|T\| meas/sim | corr | **18–22 amp meas / sim (P, D)** | corr_band / phase / coh | rails P D S cap |
|---|---|---|---|---|---|---|---|---|
| t 336–342 s | 2.5 | 30 | 375 | 416 / 434 | 0.77 | **132 / 141 (110, 98)** | 0.88 / +28° / 0.99 | 0.23 0.02 0.09 0.00 |
| t 419–422.5 s | 2.1 | 11 | 148 | 192 / 194 | 0.98 | **75 / 87 (52, 63)** | 0.86 / +28° / 0.99 | 0.00 0.00 0.00 0.00 |
| t 437–440.5 s | 10.6 | 18 | 280 | 136 / 136 | 0.89 | **71 / 78 (50, 64)** | 0.88 / +27° / 1.00 | 0.05 0.01 0.02 0.00 |

All present creep windows, per route (medians): r31 amp meas 70 / sim 74 (P 48, D 57), corr_band 0.84, phase +33°; r32 58 / 60 (35, 50), 0.82,
+32°; r33 85 / 96 (68, 68), 0.87, +23°; r34 74 / 84 (53, 67), 0.88, +26°. The kit-style linear-interpolated command gives the same (141.6 vs
140.7). **The mirror reproduces the tap's 20 Hz ripple to 4–14 % with the right waveform; D carries 55 % of it, P 45 %.**

Open-loop counterfactuals, same measured rate, r34 creep line windows (18–22 T amp, × as-built 84):

| change | amp sim (P, D) | × as-built | on the t 336–342 window |
|---|---|---|---|
| Kd 0 | 53 (53, 0) | **0.63** | 110 |
| Kd 64 | 63 (53, 35) | 0.75 | 118 |
| Kp cap 341 (V281) | 79 (39, 67) | 0.94 | 119 |
| lag 960/1014 (10 Hz pole) | 163 (99, 124) | 1.94 | 261 |
| lag 1008/253 (2.5 Hz pole) | 42 (27, 34) | **0.50** | 72 |
| fb single-sample ×2 | 85 (53, 67) | 1.01 | 141 |
| rate low-passed < 15 Hz | 18 (13, 12) | **0.21** | 31 |
| cmd frozen | 65 (33, 60) | 0.77 | 75 |
| cmd frozen and rate < 15 Hz | ~7 | 0.08 | 8 |

**79 % of the 20 Hz T ripple comes through the rate feedback, ~20 % through the setpoint (the outer loop's echo), and the output-lag pole and
Kd are the terms that size it; Kp cap 341 barely touches it (−6 %).** These are open-loop numbers: closing the loop with Kd 0/64 moves the
resonance to ~8 Hz (§1.4), which is the real cost.

## 5. What is settled and what is not
- **Settled [EVIDENCE]:** the 20 Hz T ripple is the rate PID's P+D response to the 20 Hz rate (mirror: amp within 4–14 %, corr 0.82–0.88,
  coh 0.98–0.99, constant phase); the line is engaged-only, its presence and amplitude scale with Kp(idx) and not with |T|, |rate|, v or angle;
  its frequency is fixed at 20.3–21.0 Hz on rev 3 and V280, old and new tune, moving only +0.6 Hz with idx; there is no 20 Hz line in the
  command; in the hands-light creep windows the chain is linear (rails 0.00) while the line persists at stable amplitude — so it is a
  resonance being excited, not a self-sustained limit cycle.
- **Inferred [BELIEF]:** the rate loop's unity crossing is at 17–21 Hz with PM ~35–60° and Ms 2–3 rising toward 4.5 at Kp 470; the D term
  (D/P 1.75 at 20 Hz) is what places it there; the plant has no mechanical mode at 20 Hz (a ×1.3 bump, phase −28 → −73° from 10 to 22 Hz). Rests
  on 28 s of creep data with off-line coherence 0.3–0.6, and at the line every estimator returns the inverse controller (tautology §0.7).
- **Not resolvable on this instrument:** anything above 25 Hz on T (50 Hz tap); whether the true line is 20 Hz or its 80 Hz alias on the
  100 Hz streams (both bar and rate would fold 80 → 20; the IMU shows nothing either way); the broadband source that rings the mode (road,
  motor torque ripple, the outer loop's echo) — it is not the command, and the 24–28 Hz control floor is flat.
- **Timing lesson for the kit:** the prior "T 18–22 = 81" readings used the 100 Hz-interpolated tap (attenuated ~0.6 at 20 Hz by the 50 Hz hold
  and the batch jitter); at the tap's own instants the same window reads 132. Any 20 Hz phase work must de-jitter the streams first
  (`dejitter()` here) — the logged receive latency is a broad 0–10 ms.

## 6. Files
`creep20_loop_id.py` · `_scratch/creep20_loop_id.txt` (full output, 2 m 47 s run) · caches `analysis-2020accord/_scratch/cache/v280/r3{1,2,3,4}.npz` ·
constants from the V280r2 / V278r3 images via `lowcmd_loopgain_v112_v278_v280.read_build` · chain arithmetic from `v280_map_profiles` ·
`L_fw`/`margins` copied from `kpflat_sizing.py` (that module runs on import).
