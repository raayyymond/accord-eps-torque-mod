# M3: the integrator, its hand-torque freezes, and the driver-torque sensor while hands are off (V298, route 79)

**Wall time:** `m3_integrator_freeze.py` runs in **9.0 s** (7.4 s inside the script: load 1.3 s, 13 replays 2.9 s, 14 regressions 2.3 s). It reads only the cache: `r79_a1f5d2_al.npz`, `r79_fork.npz`, the instrument's cached C3B-P replay (used for validation only), and the V298 image's cells. It contains no per-sample Python loop. The I recursion is integer-exact and event-driven. It matches the instrument's cached exact replay with **0 differing words out of 65,969**. The script uses 79 events and takes 16 ms.

**Files:** `m3_lane.py` (the lane, vectorised) · `m3_integrator_freeze.py` (the analysis) · `_scratch/out/r79/m3/m3.json` · `_scratch/out/r79/m3_stdout.txt`.

**Labels:** EVIDENCE means measured on the wire or read from the image. BELIEF means modelled or inherited. I score bands; the operator scores the symptoms.

## 0. Answer

1. **The c_I/c_P value of 1.24 is an artefact of the instrument's regression. It is not a weak integrator in the image.** The structural regressor I is the instrument's replayed I, and the replay **already contains the modelled freezes**. That replayed I carries slow offsets, and the offsets attenuate its coefficient. They come from two replay-timing errors:
   - the instrument replays the **direction-0 ramp** (+33/−16 per tick). V298 runs **direction 2** (+328/−66: 0xC63FC = 328, read from the image) because the fork sends arm 2. The effect is that the replayed I stays frozen for 0.99 s at every engage instead of 0.10 s.
   - the instrument holds the **torque word on the 0x18F frame**. The firmware's word **leads the 0x18F sample by 10 ticks**.

   Two ways of removing the offsets restore the design value:
   - give the regression one intercept per episode and per 10 s window: **c_I/c_P = 2.80–2.83 /s**;
   - band-pass at 0.1–3 Hz: **2.81 /s**.

   The design value is **2.79 /s** (0.44 Hz PI zero). Fixing the replay itself and keeping the instrument's single intercept gives **2.11** (R² 0.950). All of this is EVIDENCE.
2. **The integral is still weakened, but by how often the freeze fires, not by its gain.** The hand rules discard **31 %** of the commanded integration hands-off, weighted by |inc| (only 12.7 % by tick count). Below 8 m/s they discard **42–48 %**. Effective c_I/c_P: **1.45–1.62 /s below 8 m/s**, 1.94 at 8–10, 2.39–2.56 above 10, 1.92 pooled. The ICL bound is never reached (0.00 %). The sar-5 floor is an offset of −18 S/s, which equals a **−0.02° standing error**; it causes no loss of gain. This is EVIDENCE from the replay.
3. **Hands-off, the freezes fire on the wheel's own reaction torque during the operator's "high-jerk / high-torque" manoeuvres.**
   - Of the frames frozen by the "opposing hand" rule, **81 %** have the wheel *accelerating toward* the setpoint and 92 % have it moving toward it.
   - At |α| > 200 deg/s², the sign of the word opposes the sign of α on 79 % of frames.
   - The hand-frozen share of time rises from **3 % at |α| < 25 deg/s² to 62 % at |α| > 400 deg/s²**.

   The sign pattern is EVIDENCE. That no hand was on the wheel is BELIEF: the operator's hands were hovering, and the wire cannot tell hovering from touching.
4. **The fork's O1 override fires on the same twist.** I counted 345 O1 episodes with cs_press == 0, which is **31 per minute of lateral-active time** (13.8 s in total). 291 of them have the shape of a reaction torque. At their onset |α| has p50 394 deg/s². Each episode cuts the error the firmware sees from **4.6° to 1.4°** (p50), and the I is hard-frozen during 94 % of O1 frames. EVIDENCE; the reconstruction is validated on 100 % of O1 frames.

## 1. Sign conventions, checked on route 79

| check | result | status |
|---|---|---|
| 0x18F raw vs carState steeringTorque | raw = −cs_tq on **100.0 %** of rows at a 1-frame lag, so **gp-0x4f60 = −bar = +cs_tq × 1.024** (positive means the hand pushes left, in the θ frame) | EVIDENCE |
| the design's opposing test `(gp-0x4f60 ^ E′) < 0` | "hand pushes away from the setpoint". The flipped-sign counterfactual loses: replay R² 0.428 vs 0.928 | EVIDENCE (model selection) |
| gp-0x4f68 = clamp(\|gp-0x4f60\|) | inherited from the Segment D trace in `docs/guides/GENTLE-EME-CAN-TO-MOTOR-GATING-MAP-2026-07-06.md` | BELIEF (inherited) |
| w18 (0x18F rate) vs d(0x14A)/dt | correlation 0.995; α from the rate vs α from the angle: correlation 0.949 | EVIDENCE |
| hands-off reaction fit (settled, cs_press == 0, n 58,585) | gp-0x4f60 = **−0.69·α − 0.69·ω − 163·sgn(ω) − 61** (α in deg/s², ω in deg/s); R² 0.31. The reaction **opposes the motion**, so while the motor accelerates the wheel toward the setpoint, the word reads as an *opposing* hand | EVIDENCE (sign); the model is BELIEF |

Units: the firmware compares **gp words**: 300 and 512 = 293 and 500 raw. The fork's O1 compares **raw**: 600 and 500 = 614 and 512 gp. **The O1 release threshold equals the firmware's hard-freeze threshold.**

## 2. (a) The torque word while engaged, settled, and cs_press == 0 (EVIDENCE, wire)

| band (m/s) | s | p50 | p90 | p99 | % > 300 | % > 512 | % > 614 (O1 on) |
|---|---|---|---|---|---|---|---|
| <5 | 60 | 196 | 607 | 1103 | 28.6 | 13.6 | 9.9 |
| 5–8 | 65 | 185 | 681 | 1206 | 29.0 | 15.3 | 11.8 |
| 8–10 | 64 | 150 | 422 | 1066 | 18.7 | 7.1 | 5.1 |
| 10–12.5 | 63 | 123 | 309 | 1128 | 10.5 | 4.7 | 3.9 |
| 12.5–15 | 40 | 112 | 291 | 744 | 8.7 | 2.6 | 1.6 |
| 15–22 | 201 | 123 | 262 | 588 | 6.2 | 1.3 | 0.9 |
| >22 | 93 | 114 | 244 | 432 | 3.5 | 0.6 | 0.4 |
| all | 586 | 131 | 344 | 1026 | 12.6 | 5.1 | 3.8 |

| \|α\| (deg/s²) | s | p50 | p90 | p99 | % > 300 | % > 512 | % > 614 | method 2 (0x14A angle) % > 512 |
|---|---|---|---|---|---|---|---|---|
| 0–25 | 369 | 114 | 244 | 523 | 4.0 | 1.0 | 0.8 | 1.1 |
| 25–50 | 77 | 139 | 321 | 955 | 11.9 | 3.1 | 2.3 | 4.3 |
| 50–100 | 61 | 160 | 400 | 1057 | 19.9 | 5.8 | 4.4 | 8.6 |
| 100–200 | 37 | 215 | 615 | 1176 | 36.0 | 14.7 | 10.0 | 18.2 |
| 200–400 | 25 | 316 | 842 | 1266 | 51.8 | 29.6 | 22.0 | 30.5 |
| >400 | 17 | 457 | 988 | 1390 | 68.1 | 43.0 | 32.7 | 44.1 |

The word scales with |α|, and both α methods agree. Below 8 m/s the hands-off p90 (607–681) sits **above** both the 512 freeze and the 614 O1 threshold.

## 3. (b) Freeze conditions

The rule is EVIDENCE (image and design). Applying it at 1 kHz with the 100 Hz word held for 10 ticks is BELIEF. Mask: settled and cs_press == 0.

| band | hard | opposing | A3 stop | ICL | upward crossings of 300 /min | upward crossings of 512 /min | frozen episodes /min | p90 / max (s) |
|---|---|---|---|---|---|---|---|---|
| <5 | 13.7 % | 12.5 % | 3.35 % | 0 | 217 | 127 | 221 | 0.10 / 0.40 |
| 5–8 | 15.4 % | 10.8 % | 3.86 % | 0 | 324 | 175 | 316 | 0.10 / 0.50 |
| 8–10 | 7.1 % | 9.8 % | 0.20 % | 0 | 259 | 92 | 249 | 0.10 / 0.40 |
| 10–12.5 | 4.7 % | 5.1 % | 1.22 % | 0 | 192 | 42 | 191 | 0.10 / 0.30 |
| 12.5–15 | 2.6 % | 5.3 % | 0 | 0 | 162 | 28 | 140 | 0.10 / 0.40 |
| 15–22 | 1.3 % | 4.3 % | 0.04 % | 0 | 134 | 21 | 124 | 0.10 / 0.40 |
| >22 | 0.6 % | 2.5 % | 0 | 0 | 109 | 15 | 95 | 0.10 / 0.10 |
| **all** | **5.1 %** | **6.3 %** | 0.94 % | 0 | **182** | **59** | **172** | 0.10 / 0.70 |

- **Chatter:** the hand freeze toggles **2–5 times per second**, in blips of ≤ 0.1 s (p90). The crossing counts are taken at 100 Hz, so they are a **lower bound** on the 1 kHz count.
- **Coincidence with hard manoeuvres:**
  - by |α| bin (0–25, 25–50, 50–100, 100–200, 200–400, >400 deg/s²), the hard + opposing share is 3.4 / 11.0 / 19.8 / 33.4 / 44.7 / **62.2 %**;
  - by |rate| bin (0–5, 5–15, 15–40, 40–80, >80 deg/s), it is 4.7 / 27.8 / **50.3** / 43.0 / 35.0 %.
- **Growth of |sp − θ|:**

  | | frozen frames | free frames |
  |---|---|---|
  | \|e\| p50 / p90 | 2.0° / 7.2° | 0.6° / 2.4° |
  | share of frames where \|e\| is growing | 38 % | 52 % |
  | mean d\|e\|/dt | **−4.4 deg/s** | +0.6 deg/s |

  Over the 483 frozen episodes of ≥ 50 ms, |e| shrank by more than 0.5° in **217** and grew by more than 0.5° in **60**. **The freeze lands while the wheel is closing on the setpoint, not while the error grows.** It suppresses the I during the transient, and the I then has to build the new curve's hold torque afterwards. EVIDENCE.

## 4. (c) The I-state replay

**Timing scan.** I replayed V298's arithmetic with the direction-2 ramp and swept the torque word's timing. R² of the replay vs the tap (pooled):

| shift (ticks) | −20 | −10 | −5 | 0 (instrument) | +5 | **+10** | +15 | +20 |
|---|---|---|---|---|---|---|---|---|
| R² | 0.777 | 0.805 | 0.817 | 0.834 | 0.906 | **0.928** | 0.914 | 0.882 |

**Primary replay** = V298 image arithmetic + direction-2 ramp + word leading by 10 ticks. It has zero free parameters inside the lane. R² vs the 0x1AB tap, using the instrument's `_score_replay` mask:

| replay | 5–8 | 8–10 | 10–12.5 | 12.5–15 | 15–22 | >22 | pooled |
|---|---|---|---|---|---|---|---|
| instrument (direction-0, cached, exact) | 0.817 | 0.828 | 0.691 | 0.860 | 0.821 | −2.11 | 0.749 |
| direction-2, instrument timing | 0.896 | 0.847 | 0.861 | 0.937 | 0.951 | −2.10 | 0.834 |
| **PRIMARY** | **0.929** | **0.957** | **0.878** | **0.927** | **0.917** | **0.990** | **0.928** |
| primary, no opposing freeze | 0.748 | 0.589 | 0.351 | 0.452 | 0.193 | −2.67 | 0.444 |
| primary, no hand freeze | 0.275 | 0.278 | −0.59 | −0.25 | −0.08 | −7.98 | −0.059 |
| primary, no A3 bound | 0.218 | 0.040 | −2.12 | 0.123 | 0.814 | 0.174 | 0.247 |
| primary, opposing sign flipped | 0.762 | 0.595 | 0.234 | 0.395 | 0.170 | −2.74 | 0.428 |
| I ≡ 0 | 0.148 | 0.009 | −0.04 | 0.009 | 0.049 | −0.01 | 0.102 |

**EVIDENCE (model selection, zero free parameters):** the image's integrator runs, with the hard freeze, the opposing freeze (at the design's sign) and the A3 bound **as designed**. Every counterfactual collapses.

The instrument's R² of −3.1 above 22 m/s came from a **constant offset of 20 LSB in the replayed I** (tap mean −5.1 vs replay −24.9; correlation 0.995). The offset was acquired during low-speed manoeuvres earlier in episode 6, and it vanishes with the corrected timing: offset p50 0.1 LSB, R² 0.990.

**What the I carries** (primary replay; signed shares of |T|):

| regime | s | I share of \|·\| | P / I / D signed share | \|I>>7\| p50 / p90 (S) | at ICL | at the A3 bound | \|e\| p50 / p90 |
|---|---|---|---|---|---|---|---|
| holds (\|ω\| < 2 for ≥ 1 s, \|θ\| ≥ 2°) | 64 | **91 %** | −0.02 / **+1.02** / 0.00 | 1382 / 2500 | 0 | 0 | 0.3° / 1.0° |
| manoeuvres (\|ω\| ≥ 20 or \|α\| ≥ 100) | 95 | 52 % | +0.15 / **+0.88** / −0.02 | 1976 / 5531 | 0 | **7.6 %** | 2.4° / 8.2° |
| all hands-off | 586 | 67 % | +0.09 / +0.93 / −0.01 | 852 / 2690 | 0 | 1.5 % | 0.7° / 2.8° |

**Hold test.** I took window means over 36 holds (57 s) with no intercept: tap = 1.05 P + 0.87 I (R² 0.955), and the median I/(|P| + |I|) is 0.94. **The integrator carries the hold torque, and P is near zero in holds.** EVIDENCE.

**The fork's error clip.** The fork's desired-vs-wheel error exceeded errmax(v) on 10.3 % of lateral-active frames, broken down by band as:

| band (m/s) | <5 | 5–8 | 8–10 | 10–12.5 | 12.5–15 | 15–22 | >22 |
|---|---|---|---|---|---|---|---|
| frames over errmax | 31.7 % | 31.4 % | 4.0 % | 6.2 % | 0.8 % | 0.4 % | 0 % |

This never happens in holds (0 %), so **holds carry no error beyond the clip**. In the clipped frames (low-speed manoeuvres) the I is **hand-frozen on 74–100 %** and at the A3 bound on 0–52 % (by band). The error beyond the clip is therefore carried by neither term: P is capped at errmax and the I is frozen. The mechanism that ties this to the symptom is BELIEF.

## 5. (d) The fork's O1 override (`honda/carcontroller.py::_update_angle`, `values.py` ANGLE_OVERRIDE_ON/OFF/LEAD_S)

**Reconstruction.** O1 turns on when |cs_tq| > 600, stays on until |cs_tq| ≤ 500, and only applies while lateral is active. It is **validated**: co_ang equals clip(θ + 0.06·ω) within 0.02° on **100 %** of reconstructed O1 frames vs 2.1 % of other frames (carOutput row +1). EVIDENCE.

| | value |
|---|---|
| all O1 episodes | 415 (37 /lateral-active min), 100.8 s of 668 s; p50 / p90 / max ≤ 0.05 / 0.1 / 9.2 s |
| with cs_press == 0 throughout (\|tq\| < 1200) | **345 episodes, 13.8 s, 31 per lateral-active minute** |
| … reaction-shaped (sign(tq) = −sign(α), \|α\| ≥ 100 at onset) | **291** |
| … where the hands-off reaction model alone predicts ≥ 360 raw of the same sign | 119 |
| … driver-shaped (sign(tq) = sign(ω)) | 94 |
| onset \|α\| p50 / p90; \|ω\| p50 / p90 | 394 / 710 deg/s²; 23 / 59 deg/s |
| firmware \|sp − θ\|: 30 ms before onset → during | **4.6° → 1.4°** (p50); 11.3° → 2.3° (p90) |
| I hand-frozen during O1 | 94 % of frames (614 gp > 512) |
| after release, co_ang back within 0.5° of cc_ang | p50 0.2 s, p90 2.0 s (this includes the rate, jerk and error-clip limiters) |

So, yes: **most O1 events hands-off happen during a hard manoeuvre, and their torque sign is the wheel's inertial reaction.** Whether a hovering hand added to the twist is BELIEF; the wire cannot separate the two.

## 6. (e) The integral's effective strength

| quantity | value | status |
|---|---|---|
| design: inc = ((E′>>5)·40)>>3, S += I>>7, P = (E′·112)>>8 | **c_I/c_P = 2.79 /s**, T_i 0.358 s, PI zero 0.444 Hz | EVIDENCE (cells read from the V298 image: Ki 40, ICL 8192, Kp 112) |
| ICL 8192 (icl = (8192<<10)>>3) | **never reached** (0.00 % of frames) | EVIDENCE (replay) |
| sar-5 floor | −16 to −19 S/s in every band = **−0.01° to −0.04° of standing error**. E is a multiple of 16, so the floor is an asymmetric step (+10 / −15 per tick), not a dead zone. It is an offset, **not** a gain | EVIDENCE (replay) |
| freeze duty | integration delivered / commanded (\|inc\|-weighted): 0.58 (<5), 0.52 (5–8), 0.70, 0.86, 0.88, 0.90, 0.92 (>22); **0.69 pooled** → **effective c_I/c_P 1.62 / 1.45 / 1.94 / 2.39 / 2.47 / 2.51 / 2.56; 1.92 pooled** | EVIDENCE (replay) |

The structural regression (the instrument's form), re-run in this script. Here c_I/c_P = (c/a) × 2.79, and c_D = d × 0.566:

| I regressor or mask | a | b | c | d | c_I/c_P | R² |
|---|---|---|---|---|---|---|
| instrument (direction-0 I, one intercept): **reproduces 1.24** | 0.931 | 0.643 | 0.414 | −0.239 | **1.24** | 0.892 |
| direction-2 I, instrument timing | 0.902 | 0.654 | 0.484 | −0.120 | 1.50 | 0.901 |
| **primary I, one intercept** | 0.870 | 0.714 | 0.657 | +0.312 | **2.11** | 0.950 |
| primary I, one intercept per episode | 0.928 | 0.859 | 0.827 | 0.769 | 2.49 | 0.980 |
| **primary I, one intercept per episode × 10 s** | 0.958 | 0.970 | 0.966 | 1.119 | **2.81** | 0.999 |
| direction-0 I, one intercept per episode × 10 s | 0.932 | 0.926 | 0.946 | 1.013 | 2.83 | 0.996 |
| **primary I, 0.1–3 Hz band-pass** | 0.959 | 0.967 | 0.965 | 1.134 | **2.81** | 0.997 |
| direction-2 I, instrument timing, never frozen | 0.888 | 0.379 | 0.033 | −1.295 | 0.10 | 0.803 |
| direction-2 I, instrument timing, no hand freeze | 0.957 | 0.551 | 0.190 | −0.759 | 0.55 | 0.835 |

**Verdict on (e).** 1.24 does not match a frozen fraction (freeze duty predicts 1.92, and the regressor already contains the freezes). It does not match the ICL (never reached) or the sar-5 floor (it is an offset, not a gain). **It matches errors-in-variables:** the replayed I carries step offsets (the engage ramp, and freeze timing during low-speed manoeuvres), and those offsets attenuate c under a single pooled intercept. Removing the offsets (two methods) or fixing their two causes restores c ≈ 1 → 2.8 /s. EVIDENCE.

**Event test (weak).** For 15 hands-off manoeuvres with quiet windows on both sides, Δ(tap − replay) = −0.07 × taken − 0.08 × lost. The 90 % CI ×100 is [−13, +2] for taken and [−18, +16] for lost. **No evidence** that the car freezes more or less than the corrected replay, but the sample is small.

## 7. Mechanisms, per operator note

1. **"Small-angle steering seemed robust."** In holds the I carries 91 % of the torque, at |e| p50 0.3°. It is never at ICL or the A3 bound, and hand freezes affect only 3.4 % of time at |α| < 25 deg/s². **Strong.**
2. **"High-angle / high-jerk / high-torque … lacking."** Three things stack in exactly those manoeuvres:
   - the I, which delivers 88 % of the signed output, is hand-frozen on 33–62 % of frames at |α| > 100 deg/s²;
   - reaction-shaped O1 blips cut the firmware error 4.6° → 1.4°;
   - below 8 m/s, the fork's error clip binds on 31 % of lateral-active frames, while the I is frozen.

   **Strong** that these three coincide (EVIDENCE). That they produce the felt deficit is BELIEF.
3. **"Torque/demand indicator did not match the wheel."** Outside M3. One related fact: the term delivering the hold torque is the I (+1.02 signed share in holds), and nothing on the fork side models or shows it. **Weak.**
4. **"Stuttery / ratchety at times."** The hand freeze toggles 172 times/min (182 crossings of 300 per minute; 324 at 5–8 m/s), in blips of ≤ 0.1 s. O1 snaps the setpoint to the wheel (+60 ms) 31 times per lateral-active minute, on the wheel's own reaction torque, and then the rate limiter re-slews. **Moderate:** the timing coincides; causation for the felt ratchet is BELIEF.

## Out of scope, noticed (not pursued)

- **The R1 "D aiding" stop band fired on the same artefact.** With the primary I and a single intercept, d = +0.312 (c_D +0.18). With one intercept per episode × 10 s, d = 1.119 (**c_D +0.63 tap/(deg/s), damping, inside the LIVE band [0.45, 0.70]**). With the band-pass, d = 1.134 (+0.64). The instrument's −0.135 needs the offset-laden direction-0 I regressor. EVIDENCE. **Decision-bearing: the orchestrator should verify this crux itself.**
- **The drive read's replay uses the direction-0 ramp and a 0-tick torque timing.** V298 with arm 2 runs 328/66 (image 0xC63FC / 0xC63FA). The measured torque timing is +10 ticks.
- `drive_read_fastlane.py` raised a SyntaxError mid-session (it is being edited elsewhere). `m3_lane` carries its five helpers instead.

## Open questions

- Why the 10-tick timing? Either the 0x18F packer writes a 10 ms-old word, or the panda timestamps late. This is BELIEF; a UDS read of gp-0x4f60 would settle it, and that needs the operator's consent.
- The cs_press == 0 criterion still includes |tq| up to 1200 raw. The wire cannot separate a hovering hand from no hand.
- The 1 kHz freeze pattern is modelled from a 100 Hz word. The real chatter is at least the figure reported here.
