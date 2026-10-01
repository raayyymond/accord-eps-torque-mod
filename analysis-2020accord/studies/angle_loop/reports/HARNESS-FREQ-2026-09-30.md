# HARNESS-FREQ 2026-09-30: the angle loop, exact discrete, on the identified plant family

Subagent `harness-freq`, for the orchestrator. Analysis only. Nothing was built, flashed or sent; the fork was not
touched. Ghidra was used read-only (`disassemble_bytes` with `dry_run`, V294 program, code-identical to V295 in the lane).

- **Script:** `analysis-2020accord/studies/angle_loop/harness_freq.py`. Outputs go to `_scratch/angle_loop/harness_freq/`
  (gitignored, regenerable; every file is under 256 KB).

| command | runtime | writes |
|---|---|---|
| `python harness_freq.py --selftest` | about 1 min | the five cross-checks, `selftest.txt` |
| `python harness_freq.py` | about 15 min | sections 0–11 in `out_part1..3.txt`, `out.json` (designs, windows, schedules, stress), `sweep_v<speed>.csv` (the full grid) |
| `python harness_freq.py --egain` | about 3 min | section 7b, the recommended single-schedule design, in `egain_part1.txt` |
| `python harness_freq.py --bode` | needs `out.json` | the Bode tables in `bode_part1.txt`, one plotting FRF per design in `bode_<n>.json` |
- **Inputs it reads:** the V295 cals, little-endian from the image (sha `5c044d65…` asserted by
  `lane_mirror_v295.load_cal`); the byte-exact lane mirror `lane_mirror_v295.py`; the plant family
  `studies/v295/plant/v294_plant.family()`; the V289/V290 20 Hz fits `rlog-tools/studies/grind/_scratch/loopshape20_plants.json`.

Every decision-bearing claim is marked **EVIDENCE** (with the method) or **BELIEF**.

---

## 0. Headline

1. **The harness is the bytes, and the edited lane is negative feedback on the angle.** EVIDENCE (§2).
   - The byte-exact integer mirror and the model agree to 0.99–1.02× and ≤ 0.5° at 0.5–20 Hz.
   - The record's 20 Hz numbers reproduce exactly: 3.850 / 2.079 / 44.900.
   - The exact periodic (100 Hz hold) loop equals its LTI fundamental to 0.2 %.
   - It flags V282 as near-marginal on the rigid plant and unstable on 23 of the 63 stress plants carrying the record's
     20 Hz modes. **It can return
     "do not flash".**
2. **The crossover gain must span 4.5× with speed.** EVIDENCE (§6): this is the plant, not the loop.
   - At 3–8 m/s the plant is inertia above about 4 Hz. At 19–30 m/s it is 1/(b·s) with b 22–26.
   - Kp for a 3.0 Hz crossover is 1090–1320 at 3–8 m/s, about 2400 at 12.5, about 4770 at 19 and about 5700 at 26–30.
   - DC gain is 0.1002·Kp T counts per deg.
3. **A FLAT Kp cannot meet the goal, and an ANGLE-INDEXED Kp is identical to flat.** EVIDENCE (§8b, §8c).
   - **Best flat (cal-only):** Kp 1100, Kd 24, Ki 177. It gives a 2.95–3.0 Hz crossover at PM 46–53° at 3–8 m/s.
     At 19–30 m/s the crossover is 0.59–0.62 Hz, with |T_ref| 0.53–0.95 over 0.1–1 Hz. **Tracking FAILS at ≥ 12.5 m/s.**
   - **Angle-indexed is flat:** every knot's safe Kp equals the 3 m/s edge. 3 m/s can reach every angle
     (θ_max(3 m/s) = 865 deg at 3 m/s²), and the safe edge rises monotonically with speed for every (Kd, Ki) tested.
     The road-geometry bound is BELIEF.
4. **A SPEED schedule is required.** That is a cave, minimal form: one speed-LERP gain g(v) applied to E, so P and I
   scale together; Kd flat. It meets every frequency-domain criterion at 6 of 7 speeds on the nominal plant.
   EVIDENCE (§9).
   - Kd 16, PI corner 0.3 Hz.
   - Kp_eff 896 / 960 / 1028 / 2335 / 4628 / 4628 / 4628 at 3 / 5 / 8 / 12.5 / 19 / 26 / 30 m/s.
   - Crossover 2.43–2.93 Hz, PM 46–55°, exact GM 12–15 dB.
   - M20 1.99–3.44 against V295's 3.58. |L(20)| is at or below V295's at every speed.
   - No 5–30 Hz peak on T_ref or T. Turn-hold ≥ 0.99. Tracking 0.96–1.02 at ≥ 8 m/s.
   - The one miss is a 2.43 Hz crossover at 3 m/s.
   - A two-schedule variant (Kd(v) as well: 24 → 8) meets all 7 (§8d).
5. **It is NOT robust across the credible family, and the binding unknown is b at speed.** EVIDENCE for the numbers
   (§10); which member is real is BELIEF.
   - On `b_lo` and `J_hi` the nominal design drops to PM 17–36°.
   - **The family-robust schedule is Kp_eff 637 / 682 / 730 / 1178 / 3070 / 3520 / 3520.** It crosses at 1.6–2.1 Hz on
     the nominal and at 2.4–3.4 Hz with PM 45–53° on `b_lo`. `b_lo` is the identification's own bias-corrected b at
     speed (G3a: b over-estimated ×1.7–1.9).
   - On the prior `light_b` world, the safe edge is 300–394 at every speed. The robust schedule is UNSTABLE there at
     ≥ 12.5 m/s. That world is disfavoured by held-out R², but the highway gain rests entirely on b being 14–26, not 1.6.
   - **The robust schedule is the dose this harness supports flying first.**
   - It also keeps |T_ref| ≤ 1.01 in the 1.6–3 Hz hard-turn band. The nominal design amplifies the setpoint there by
     1.09–1.27, a +0.8…+2.1 dB peak near crossover. EVIDENCE.
   - The closed-loop wheel mode is the pre-registered discriminator (§10): 2.4–2.7 Hz at ζ 0.64–0.67 if the nominal is true at 19–30 m/s; 4.0–4.3 Hz at
     ζ 0.33–0.37 if `b_lo` is; an unstable 4.9–5.1 Hz oscillation if `light_b` is.
6. **What the 100 Hz hold costs.** EVIDENCE (§5, §11).
   - 5.9° of phase at a 3 Hz crossover and 39.6° at 20 Hz.
   - The 5 Hz output lag costs 30.7° at 3 Hz, five times more. **The output lag, not the hold, limits the low-speed
     crossover.**
   - A fresh 1 kHz operand (a cave rebuilding `gp-0x6a00` at 1 kHz) buys +5.8–5.9° PM and +5–7 dB GM at the same gains,
     and +7–15 % Kp at low speed.
   - But it **raises** M20 by 7 %, because it removes the hold's 0.936 attenuation. At 26–30 m/s the safe Kp then
     *falls* from 5683 to 5307.
   - It is worth a cave only for resolution (item 9a), not for phase.
7. **The modelled 20 Hz modes are left as they are.** EVIDENCE (§12), BELIEF that the stress plants bracket the real
   object.
   - The stress plants are the two-mass 16–24 Hz family (r2 0.2–0.8, ζ 0.02–0.05) and the three V289/V290 fits.
   - On every one, the angle loop holds the flexible mode's ζ within −0.02…+0.015 of the open plant, the same class
     as V295.
   - **The record's V282 goes UNSTABLE on 23 of the 63 stress rows** (positive control). The held angle loop is
     unstable on none.
8. **The D on the held rate (edit 5) is required below 19 m/s, and it is capped by the 20 Hz bar.** EVIDENCE (§6).
   - P-only PM at a 3 Hz crossover is 8–23° at 3–8 m/s.
   - Kd 24 gives 45–57° with Ki ≤ 150, and 40–49° with Ki 400.
   - Kd 32 alone exceeds V295's M20 (3.78–3.83) at every speed.
   - At 26–30 m/s, Kd must be ≤ 8 for a 3 Hz crossover (Kd 16 gives M20 3.97–4.03).
9. **Three nonlinear items the linear harness cannot score.** Static and describing-function estimates, BELIEF (§13).
   The time-domain harness must test each.
   - **(a) The 0.1 deg LSB of `gp-0x6a00`.** At the highway gains, one LSB is 31–46 T counts (E-gain schedules; 48–57
     for §8d), against static friction of 6–9. That predicts a relay limit cycle near f180 ≈ 8–9 Hz: about 11–16 T
     counts, 0.007–0.014 deg, 0.4–0.7 deg/s. **This is a candidate NEW 8–9 Hz line.** At ≤ 12.5 m/s friction holds it.
   - **(b) The stock I deadband (DB 4) is a ±0.85 deg dead zone.** In highway turns (1.4–8 deg) the I never engages.
     Turn-hold is then the P-only 0.78–0.89, which **FAILS ≥ 0.90**. DB 1 gives 0.92–0.99 for turns of 3.6 deg and
     more. Very gentle highway turns (1.4–3 deg at 26–30 m/s) stay at 0.86–0.90. A small DB at low speed invites
     PI-plus-stiction hunting: the friction band is 0.98–1.35 deg at 3 m/s. If the cave applies g(v) to E before the I's
     `E>>5`, the zone shrinks as 1/g(v): 0.85 deg at parking speed and about 0.15 deg on the highway (BELIEF).
   - **(c) The static friction band is Fs/(Kp′+k).** That is 0.98–1.35 deg at 3 m/s and 0.011–0.015 deg at 26 m/s,
     against torque mode's 2Fc/k of 23.6 and 0.16 deg: 7–24× stiffer against Coulomb friction. It is the frequency-domain reason to
     expect a smaller dwell-then-jump.
10. **The strict reading of "no new 5–30 Hz line" fails every 2.5–3.5 Hz design.** EVIDENCE (§7).
    - Under that reading, |S| ≤ +3 dB in 5–30 Hz. Max |S| there is +3.3…+5.2 dB at 4–7 Hz; that is the waterbed just
      above crossover, not a lightly damped pole.
    - The nominal E-gain design is at +3.3…+4.5 dB.
    - The robust schedule (crossover about 2 Hz) passes it: max |S| +1.9…+2.6 dB.
    - **Which reading the goal means is the orchestrator's call.**
11. **A hazard any speed-schedule cave must design out.** EVIDENCE in the linear model, BELIEF on the trigger.
    - On a speed fault, `gp-0x6a5e` slews toward 80 km/h. The highway gain (Kp 3520–4628) at 3–8 m/s is **unstable**:
      4.9–5.4 Hz, ρ 1.019–1.052 per 10 ms.
    - The cave must fall back to the low-speed gain when `gp-0x67f4` flags the speed invalid.

---

## 1. What the harness models (every block is a line of the decompiled arithmetic, linearised)

Units: θ is the plant angle in deg, + left. It equals `gp-0x6a00`/10 and openpilot's `steeringAngleDeg`. u is the
plant input torque in T counts, + left. u = −T, where T is `gp-0x6b38` in the 427 tap's sign.

| block | bytes | model (1 kHz, z = e^{jωT}, T = 1 ms) |
|---|---|---|
| operand | `0x28F4C ld.h -0x6a00[gp],r7` (edit 1) | op = 10·θ (0.1 deg counts) |
| 100 Hz hold | slot 4 writes `gp-0x6a00`/`gp-0x6a56` on 1 tick in 10, after slot 0 | **exact:** a real register, lifted 10-tick monodromy. **LTI fundamental:** (1/10)·Σ_{a=1..10} z^−a. **Continuous:** e^{−s·5.5 ms}·sinc(f·10 ms). **Fresh:** 1 |
| fb filter | `0x28F86..0x28FA4`, a = 0, b = 8192, `add` (edit 2) | r26 = 8·op[n] + 8·op[n−1] |
| error | `0x29D6A ld.h -0x69ae` (edit 4), `0x29D76 shl 2`, `0x29D78 sub` | E = 160·θ_sp − r26 (θ_sp in deg) |
| P | `0x29E36 mul ; 0x29E3E sar 8` | Kp/256·E |
| I | `0x29D7C sar 5 ; 0x29DA8 mul Ki ; 0x29DB2 sar 3 ; 0x29F18 sar 7` (Ghidra re-read here) | Ki/32768·E/(1 − z^−1), deadband DB = 0 in the linear model |
| D | edit 5: `0x29EDE subr r0,r7 ; 0x29EE0 ld.h -0x6a56[gp],r8` | −Kd·x_held/8, x = 8·(θ[n] − θ[n−3])/3 ms (the 3 ms former is the record's BELIEF) |
| fade | `0x2A0B4..0x2A0C2`, hands-off f = ((255·255)&0xFFFF)>>8 | 254/256 |
| output lag | `0x2A174..0x2A1B0` (Ghidra re-read here), oa 992, ob 507 | (507/1024)(1 + z^−1)/(32(1 − (992/1024)z^−1)): 5.05 Hz, DC 0.990 |
| forward gain | `0x2A1EE` 5346, pol `gp-0x6752` = −1 | u = +5346/32768·y |
| transport | the record's T → wheel-acceleration delay | z^−2 nominal (0 and 6 ms in the `tau0`/`tau6` members) |
| plant | `v294_plant.family()` | θ/u = 1/(J s² + b s + k), ZOH at 1 kHz, plus the 20 Hz stress modes (§12) |

**DC scale (EVIDENCE, arithmetic from the image cals):** u = 0.10018·Kp T counts per deg of angle error. D adds
0.1603·Kd T counts per deg/s. The I builds at 0.783·Ki T counts per deg per second. The PI corner is
f_I = 7.8125·Ki/(2π·Kp) Hz.

**Loop:** L = C_fb·P, with C_fb = fade·H_out·FWD·z^−d·[(Kp/256 + Ki/32768/(1−z^−1))·R(z)·OP(z) + Kd·H(z)·RF(z)].
The reference path is C_ref = fade·H_out·FWD·z^−d·(Kp/256 + I)·160. The setpoint enters without the FIR and without
the hold. Then T_ref = C_ref·P/(1+L), S = 1/(1+L), T = L/(1+L).

**Linear only.** These are not modelled here: the integer floors, the clamps (P 15360, sum 15360, lane 3072), the I
deadband, Coulomb friction and the 0.1 deg LSB of `gp-0x6a00`. §13 gives static estimates for the last three; the
time-domain harness owns them.

## 2. Validation (EVIDENCE: `--selftest`, output in `_scratch/angle_loop/harness_freq/selftest.txt`)

1. **The record's 20 Hz numbers are reproduced exactly** (fresh x, ideal differentiator):
   - V295 |P/x| = 3.850
   - V294 = 2.079
   - V282 = 44.900

   With the 100 Hz hold and the 3 ms former they are 3.583, 1.935 and 41.783.
2. **The analytic FRF equals the tick-by-tick state space** to a relative error of 2·10⁻¹³ (T_ref, 0.3–45 Hz, LTI
   modes).
3. **The byte-exact integer lane matches the model.** `lane_mirror_v295.lane_tick` was run with edits 1–5, pol −1, and
   a sinusoidal angle passed through an emulated age-1..10 hold. Against **−C_fb**, measured/model is 0.990–1.018× in
   magnitude and ≤ 0.5° in phase, at 0.5–20 Hz, for P, P+I, P+D and P+I+D.
   - This proves u = −C_fb·θ: **the edited lane is NEGATIVE feedback on the angle.**
   - The residual is the integer floors and the 0.1 deg LSB.
4. **The exact periodic loop and its LTI fundamental agree** (closed loop, θ_sp sine, 12.5 m/s). They agree to 0.2 % at
   3 Hz and to all printed digits at 1, 10 and 20 Hz. **The fold-back of the hold's images is negligible below
   30 Hz.** The margins below therefore use the LTI fundamental. Every stability verdict and gain margin is the exact
   lifted one.
5. **The hold kernel, three ways:**

| form | 3 Hz | 20 Hz |
|---|---|---|
| exact ages 1–10 | 0.9985, −5.94° | 0.9361, −39.60° |
| e^{−s·5.5 ms}·sinc | 0.9985, −5.94° | 0.9355, −39.60° |
| e^{−s·5 ms}·sinc (textbook ZOH) | −5.40° | −36.0° |
| ages 0–9 | −4.86° | −32.4° |

The textbook form is 0.5 ms short, because the age is 1–10 ticks, not 0–9.

**Positive control on the method:** on the identified rigid plant, the record's V282 has a 0.6–0.8 dB gain margin and a
13.8–14.3 Hz pole at ζ 0.02–0.03 at 3–8 m/s (§4). On 23 of the 63 stress plants carrying the record's 20 Hz modes (§12) it is UNSTABLE. V282
ground at 17–21 Hz on the car. **The harness can return "do not flash".**

## 3. The plant used (`v294_plant.family()`; linear in speed between the fit knots 3.1/8/11.9/17/26.9 m/s)

| v m/s | J | b | k | Fc / Fs | roots of J s² + b s + k (Hz) | prior `light_b` (BELIEF) J / b / k |
|---|---|---|---|---|---|---|
| 3 | 0.200 | 4.94 | 6.5 | 76 / 95 | 3.71, 0.22 | 0.21 / 1.58 / 6.5 |
| 5 | 0.200 | 5.05 | 11.8 | 52 / 65 | 3.61, 0.41 | 0.21 / 1.58 / 9.3 |
| 8 | 0.200 | 5.24 | 20.2 | 13.5 / 18.9 | 3.42, 0.75 | 0.21 / 1.58 / 13.7 |
| 12.5 | 0.200 | 11.04 | 30.8 | 14.9 / 17.6 | 8.32, 0.47 | 0.21 / 1.58 / 23.4 |
| 19 | 0.200 | 21.82 | 74.9 | 7.2 / 9.1 | 16.8, 0.57 | 0.21 / 1.58 / 28.3 |
| 26 | 0.200 | 25.89 | 57.9 | 4.7 / 6.0 | 20.2, 0.36 | 0.21 / 1.58 / 34.3 |
| 30 | 0.200 | 26.41 | 55.8 | 4.4 / 5.6 | 20.7, 0.34 | 0.21 / 1.58 / 35.1 |

Units are T counts per deg/s², per deg/s and per deg. The plant is overdamped at every speed.

- **Above ~4 Hz at 3–8 m/s it is J-dominated** (inertia). **Between 0.4 and 20 Hz at 19–30 m/s it is b-dominated**
  (1/(b·s)).
- **This single fact sets the whole design.** The P gain that gives a 3 Hz crossover is 4.5× larger at highway speed
  than at parking speed.
- **Corners carried** (EVIDENCE that they exist in the family; their physics is the identification report's):
  - `J_lo`/`J_hi`/`J_hi2`: J 0.1/0.5/0.8, refitted as a whole.
  - `b_lo`: b ÷1.8 at ≥ 10 m/s, ×0.7 below.
  - `b_hi`: b ×1.5.
  - `tau0`/`tau6`: 0 and 6 ms delay. These bracket the brief's 2–3 ms.
  - `ms_free`: J free per band; **J = 2.03 at 12.5 m/s**.
  - `light_b`: the prior.
- **CREDIBLE set = nominal, J_lo, J_hi, b_lo, b_hi, tau0, tau6.**
- **STRESS set = J_hi2, ms_free, light_b.**
  - BELIEF: J is a hardware property, and the J profile excludes ≥ 0.5 at 0–5 m/s (+50 % held-out cost).
  - `light_b` predicts the drive worse than every identified member (identification report §5).
- **The 20 Hz mode**, as the record represents it (§12; NOT identified on r71b):
  - **Collocated two-mass** (redo audit rp4 / `v294_plant.with_mode20`): f2 16/20/24 Hz, wheel share r2 0.2/0.5/0.8,
    ζ2 0.02/0.05. The motor angle is sensed, which matches `gp-0x6a00`'s source `gp-0x6cc4`.
  - **The V289/V290 multiplicative fits** (`loopshape20_plants.json`): 'resonant' 21.0 Hz ζ 0.010; 'smooth+mode'
    22.5 Hz ζ 0.05; 'weak-mode' 22.25 Hz ζ 0.04, κ 0.3.

## 4. The 20 Hz bars, defined, and the references on the same plants

The goal says "20 Hz loop gain ≤ V295's". This harness carries three comparable measures. All are physical: they
include the 100 Hz hold that V295 itself had.

- **M20**, the record's measure: controller output S (P-counts, before the fade) per count of the TRUE wheel rate
  x = 8·dθ/dt, at 20 Hz.
  - It is normalised to V295's downstream chain if the output lag is changed.
  - For an angle loop: M20 = |C_S(20 Hz)|/(8·2π·20).
  - **V295 = 3.58** with its hold (3.85 in the record's no-hold convention). V294 = 1.93. V282 = 41.78.
- **L20 = |L(20 Hz)|** on the same plant member.
  - V295: 0.044 (3–8 m/s), 0.041 (12.5), 0.034 (19), 0.031 (26–30).
  - It falls with speed because b rises.
- **Re Cr(20)** is the torque per unit wheel rate, real part, in T counts per deg/s. Negative means it removes damping
  from a collocated 20 Hz mode.
  - V295 −0.79, V294 −0.43, V282 −8.38.
  - With the hold included, all three are anti-damping at 20 Hz. The redo audit's no-hold rp4 had V282 at +2.6
    (damping) at Td 2 ms. BELIEF that this sign flip is part of why V282 ground; the hold-record report owns that thread.

Gates used below:

- M20 ≤ V295's 3.58.
- L20 ≤ V295's L20 on the same member.

## 5. What the 100 Hz hold costs (EVIDENCE: arithmetic, `out_part1.txt` §1)

Phase of the operand path (hold, then the FIR), held vs fresh, and the other lags in the same loop:

| f | held | fresh | **hold cost** | output lag (5.05 Hz) | 2 ms transport |
|---|---|---|---|---|---|
| 1 Hz | −2.16° | −0.18° | **−1.98°** | −11.2° | −0.7° |
| 2 Hz | −4.32° | −0.36° | **−3.96°** | −21.6° | −1.4° |
| 2.5 Hz | −5.40° | −0.45° | **−4.95°** | −26.3° | −1.8° |
| 3 Hz | −6.48° | −0.54° | **−5.94°** | −30.7° | −2.2° |
| 3.5 Hz | −7.56° | −0.63° | **−6.93°** | −34.7° | −2.5° |
| 6 Hz | −12.96° | −1.08° | **−11.88°** | −49.9° | −4.3° |
| 13 Hz | −28.1° | −2.3° | **−25.7°** | −68.8° | −9.4° |
| 15 Hz | −32.4° | −2.7° | **−29.7°** | −71.4° | −10.8° |
| 17 Hz | −36.7° | −3.1° | **−33.7°** | −73.5° | −12.2° |
| 20 Hz | −43.2° | −3.6° | **−39.6°** (\|H\| 0.936) | −75.8° | −14.4° |

**At a 3 Hz crossover the hold costs 5.9° of phase margin. The 5 Hz output lag costs 30.7° there, five times more.**
The output lag, not the hold, is what limits the low-speed crossover (§6, §14).

## 6. The 3.0 Hz crossover by speed and D gain (nominal member, Ki = 0; `out_part*` §4 has every Ki variant)

Each cell gives Kp for fc = 3.0 Hz / PM / exact GM in dB / M20. ✗ marks a failed safety gate: PM < 45, GM < 6 dB,
M20 > 3.58 or |L(20)| > V295's.

| v m/s | Kd 0 | Kd 8 | Kd 16 | Kd 24 | Kd 32 |
|---|---|---|---|---|---|
| 3 | 1317 / 15° / 3.4 / 0.76 ✗ | 1290 / 26° / 7.0 / 1.27 ✗ | 1216 / 37° / 11.4 / 2.07 ✗ | **1087 / 49° / 14.1 / 2.94** | 878 / 63° / 14.8 / 3.82 ✗ |
| 5 | 1304 / 18° / 3.9 / 0.76 ✗ | 1277 / 29° / 7.5 / 1.26 ✗ | 1203 / 40° / 11.9 / 2.07 ✗ | **1072 / 52° / 14.4 / 2.94** | 860 / 66° / 15.0 / 3.82 ✗ |
| 8 | 1292 / 23° / 4.6 / 0.75 ✗ | 1264 / 34° / 8.2 / 1.26 ✗ | 1189 / 44.8° / 12.6 / 2.06 ✗ | **1056 / 57° / 14.8 / 2.93** | 840 / 71° / 15.3 / 3.81 ✗ |
| 12.5 | 2465 / 39° / 7.8 / 1.43 ✗ | 2448 / 44.8° / 10.0 / 1.79 ✗ | **2408 / 51° / 12.4 / 2.46** | 2342 / 56° / 14.5 / 3.26 | 2250 / 62° / 15.5 / 4.10 ✗ |
| 19 | **4781 / 51° / 10.4 / 2.78** | 4771 / 54° / 11.8 / 3.03 | 4748 / 56° / 13.3 / 3.51 | 4712 / 59° / 14.8 / 4.15 ✗ | ✗ |
| 26 | **5676 / 49° / 10.7 / 3.30** | 5666 / 51° / 12.0 / 3.53 | 5646 / 54° / 13.3 / 3.97 ✗ | 5616 / 56° / 14.7 / 4.55 ✗ | 5575 / 58° / 15.9 / 5.23 ✗ |
| 30 | **5791 / 48° / 10.8 / 3.36** | 5782 / 51° / 12.0 / 3.60 ✗ | 5762 / 53° / 13.3 / 4.03 ✗ | ✗ | ✗ |

**Read (EVIDENCE):**

- **Low speed needs D.** The inertia plant plus about 39° of controller lag at 3 Hz leaves P-only at 15–23°.
- **High speed cannot afford D.** D alone contributes about 0.116·Kd to M20 (2.8 at Kd 24, 3.7 at Kd 32), and P on the
  angle at highway gains already contributes 2.8–3.4. The two add roughly in quadrature.
- **Kd 32 is never inside the 20 Hz bar.**
- **No single Kd satisfies both ends** at a 3.0 Hz crossover. This is why §8d schedules Kd too. The single-schedule
  design in §9 instead accepts 2.4–2.6 Hz at the ends with Kd 16.
- Every row also fails the strict |S| reading (+3.3 to +5.2 dB at 4–7 Hz), §7.

## 7. Safe Kp windows per speed (nominal; `out_part*` §5)

The window is the contiguous block of grid Kp (49 log steps, 300–8000) that passes EVERY safety gate. The gates are:

- PM ≥ 45° and exact GM ≥ 6 dB;
- M20 ≤ 3.58 and |L(20)| ≤ V295's;
- max(|T_ref|, |T|) ≤ +3 dB over 5–30 Hz;
- no 5–50 Hz closed-loop pole with ζ < 0.2;
- stable.

Each cell gives:

- the upper edge;
- its value under the strict |S| reading, in brackets;
- the crossover at that edge, in Hz;
- the smallest Kp meeting performance, or ✗ if no safe Kp performs.

Performance means fc ≥ 2.5 Hz, and at ≥ 8 m/s also tracking 0.95–1.05 over 0.1–1 Hz and turn-hold ≥ 0.90.

| Kd, I | 3 | 5 | 8 | 12.5 | 19 | 26 | 30 |
|---|---|---|---|---|---|---|---|
| 0, Ki 0 | 637 (637), 1.83, ✗ | 682 (682), 1.93, ✗ | 782 (782), 2.14, ✗ | 2037 (1549), 2.59, ✗ | 5307 (3070), 3.25, ✗ | 6085 (3520), 3.17, ✗ | 6085 (3770), 3.12, ✗ |
| 8, fI 0.2 | 730 (730), 2.04, ✗ | 782 (782), 2.16, ✗ | 896 (896), 2.38, ✗ | 2181 (1549), 2.74, 2181 | 5307 (3070), 3.26, ✗ | 5683 (3770), 3.01, 4628 | 5683 (3770), 2.96, 4628 |
| 16, fI 0.2 | 896 (782), 2.45, ✗ | 960 (782), 2.58, 960 | 1100 (782), 2.82, ✗ | 2501 (1659), 3.06, 2037 | 4628 (3520), 2.93, ✗ | 4628 (4037), 2.55, 4628 | 4628 (4037), 2.51, 4628 |
| 24, fI 0.2 | 1100 (730), 2.95, 837 | 1178 (730), 3.09, 837 | 1262 (782), 3.22, ✗ | 2678 (1776), 3.26, 2037 | 3288 (3288), 2.20, ✗ | 3288 (3288), 1.89, ✗ | 3288 (3288), 1.86, ✗ |

- **The safe upper edge rises monotonically with speed for every (Kd, I) pair.** EVIDENCE (§8c prints all six best
  pairs).
- **That is the whole reason a flat or an angle-indexed Kp fails.**
- At ≥ 19 m/s, `✗` with fI 0.2 is the PI's slow tail. |T_ref| dips to 0.93 at 0.1–0.3 Hz; fI 0.3 fixes it (§9).

## 8. The three schedule types

### 8a. Kp-only speed schedule (Kd flat, Ki flat or ∝ Kp)

This is `out_part*` §6a. **The best is Kd 16, fI 0.2, which passes at 4 of 7 speeds.**

- The misses are tracking 0.93 at 8 and 19 m/s, and fc 2.45 at 3 m/s.
- **A flat Ki is worse than Ki ∝ Kp.** A flat Ki puts the PI corner at 7.8125·Ki/(2π·Kp). That corner falls 4.5×
  from parking to highway, so the low speed loses PM, or the highway I is too slow to hold.

### 8b. FLAT Kp (cal-only)

This is `out_part*` §6b. **The best flat Kp is 1100, with Kd 24 and Ki 177 (fI 0.2).**

| v m/s | 3 | 5 | 8 | 12.5 | 19 | 26 | 30 |
|---|---|---|---|---|---|---|---|
| fc Hz | 2.95 | 2.98 | 3.00 | 1.55 | 0.62 | 0.60 | 0.59 |
| PM | 46° | 49° | 53° | 86° | 111° | 99° | 98° |
| tracking \|T_ref\|, 0.1–1 Hz | 1.01–1.06 | 1.00–1.01 | 0.93–0.98 ✗ | 0.81–0.97 ✗ | 0.54–0.90 ✗ | 0.53–0.94 ✗ | 0.53–0.95 ✗ |

- **Across the credible family the flat Kp must drop to 782**, where `b_lo` binds at 3 m/s. The crossover is then
  2.43–2.46 Hz at 3–8 m/s and 0.34–0.39 Hz at 19–30 m/s.
- **VERDICT: a flat Kp FAILS the goal's tracking criterion at every speed ≥ 8 m/s.** EVIDENCE.

### 8c. ANGLE-INDEXED Kp (cal-only: the 5-knot Kp record keyed by idx = 0.620·|θ_sp| deg)

A knot at |θ_sp| = θ is reachable by every speed with θ_max(v) = (180/π)·L·SR·a_lat/v² ≥ θ. The inputs are L 2.83 m,
SR 16 and a_lat ≤ 3 m/s²; all three are BELIEF. The knot angles are:

| speed | 3 m/s | 5 | 8 | 12.5 | 19 | 26 | 30 m/s |
|---|---|---|---|---|---|---|---|
| θ_max | 865 deg | 311 | 122 | 50 | 21.6 | 11.5 | 8.6 deg |
| idx | 536 | 193 | 75 | 31 | 13 | 7 | 5 |

- Every angle, small ones included, is reachable at 3 m/s.
- So every knot's safe Kp is min over reachable speeds of the safe edge, which is **the 3 m/s edge at every knot**.
  EVIDENCE: `out_part*` §6c prints the six best pairs, all monotone, all with equal knots.
- **The angle-indexed schedule is the flat schedule.** It could only help if the slowest speed tolerated the MOST gain,
  and the plant says the opposite.
- **There is also a hidden coupling (EVIDENCE: the setpoint chain, TRACE §1).** idx is computed through the
  driver-torque taper. A driver grab drives idx → 0, which selects the knot-0 Kp. That is harmless for a flat table and
  matters for any non-flat one.

### 8d. Kp AND Kd by speed, Ki ∝ Kp (fI 0.3)

This is `out_part*` §6d. It needs both LERP keys moved to speed, or a cave; that is BELIEF and not traced.

| v m/s | 3 | 5 | 8 | 12.5 | 19 | 26 | 30 |
|---|---|---|---|---|---|---|---|
| Kp | 1100 | 1100 | 1123 | 2401 | 4766 | 5656 | 5683 |
| Kd | 24 | 24 | 24 | 24 | 8 | 8 | 8 |
| Ki | 265 | 265 | 271 | 579 | 1150 | 1365 | 1371 |
| fc Hz | 2.92 | 2.94 | 3.00 | 3.00 | 3.00 | 3.00 | 2.96 |
| PM | 45° | 48° | 51° | 50° | 48° | 45° | 46° |
| M20 | 2.93 | 2.93 | 2.94 | 3.26 | 3.02 | 3.52 | 3.53 |
| tracking | (n/a) | (n/a) | 0.98–1.00 | 1.00–1.02 | 0.96–0.99 | 1.00–1.03 | 1.00–1.03 |

- **It passes every gate and every performance criterion at all 7 speeds on the nominal plant.**
- It is the most aggressive design. Across the credible family its edges are 782 / 782 / 896 / 1351 / 2867 / 3070 /
  3070 (`out_part*` §7).

## 9. The recommended mechanism: ONE speed schedule on E (`--egain`, `egain_part1.txt`)

Suppose the cave multiplies E by g(v) after `0x29D78`, before the I's `E>>5` and the P's `E·Kp`. Then P and I scale
together and the PI corner is fixed. D (edit 5, on the held rate) is untouched. This is BELIEF about the cave, which is
not designed or traced; the loop arithmetic is EVIDENCE.

**Kd 16 with fI 0.3 is the best single-schedule pair: 6 of 7 speeds pass.** Kd 12 passes 5; Kd 20 passes 5 and fails
26–30 on tracking; fI 0.25 and 0.35 are worse.

| v m/s | 3 | 5 | 8 | 12.5 | 19 | 26 | 30 |
|---|---|---|---|---|---|---|---|
| **design** Kp_eff | 896 | 960 | 1028 | 2335 | 4628 | 4628 | 4628 |
| Ki_eff (= 0.2413·Kp) | 216 | 232 | 248 | 563 | 1117 | 1117 | 1117 |
| fc Hz | 2.43 ✗ | 2.56 | 2.69 | 2.90 | 2.93 | 2.55 | 2.51 |
| PM / exact GM | 46° / 15 | 46° / 15 | 48° / 14 | 47° / 12 | 52° / 13 | 55° / 15 | 55° / 15 |
| M20 (bar 3.58) | 1.99 | 2.00 | 2.02 | 2.42 | 3.44 | 3.44 | 3.44 |
| tracking 0.1–1 Hz | n/a | n/a | 0.97–0.99 | 0.99–1.02 | 0.96–0.99 | 1.00–1.02 | 1.00–1.02 |
| \|T_ref\| max, 1.6–3 Hz | 1.23 | 1.22 | 1.17 | 1.27 | 1.15 | 1.10 | 1.09 |
| max \|S\|, 5–30 Hz | +3.3 dB | +3.5 | +3.7 | +4.5 | +4.3 | +3.5 | +3.5 |
| **ROBUST** Kp_eff | **637** | **682** | **730** | **1178** | **3070** | **3520** | **3520** |
| Ki_eff | 154 | 165 | 176 | 284 | 741 | 849 | 849 |
| fc Hz, nominal / `b_lo` | 1.90 / 2.38 | 2.02 / 2.53 | 2.12 / 2.69 | 1.62 / 2.71 | 2.06 / 3.37 | 2.01 / 3.27 | 1.98 / 3.22 |
| PM, nominal / `b_lo` | 61° / 46° | 62° / 46° | 66° / 48° | 74° / 53° | 68° / 48° | 63° / 45° | 63° / 46° |
| tracking, nominal | n/a | n/a | 0.92–0.99 ✗ | 0.91–0.99 ✗ | 0.92–0.99 ✗ | 0.99–1.00 | 1.00–1.00 |
| \|T_ref\| max, 1.6–3 Hz (nominal) | 1.01 | 0.98 | 0.91 | 0.84 | 0.92 | 0.99 | 0.99 |
| max \|S\|, 5–30 Hz (nominal) | +2.4 dB | +2.5 | +2.6 | +1.9 | +2.6 | +2.5 | +2.5 |

**Notes on the schedule.**

- **Why ROBUST.** Kp_eff = min(design, credible-family safe edge). `b_lo` binds everywhere except 12.5 m/s, where `J_hi`
  binds.
- **In cell terms.** Equivalently: a base Kp record flat at 637, Ki 154 and Kd 16, with g(v) = 1.000 / 1.071 / 1.146 /
  1.849 / 4.819 / 5.526 / 5.526.
- **Speed knots in `gp-0x6a5e` units** (64 counts per km/h, i.e. 230.4 per m/s): 691 / 1152 / 1843 / 2880 / 4378 /
  5990 / 6912.
- **Overflow (EVIDENCE: arithmetic).** E·Kp_eff stays below 2³¹ for Kp_eff ≤ 10922, even with the 0x7FFF sentinel.
  The maximum here is 4628.

## 10. Robustness across the family, and the pre-registered drive observable

**The nominal design (Kp_eff 896…4628), PM / exact GM by member:**

| v | nominal | J_lo | J_hi | b_lo | b_hi | tau0 | tau6 | J_hi2 | ms_free | light_b |
|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 46/15 | 58/16 | 36/16 | 31/12 | 61/19 | 48/17 | 43/12 | 37/18 | 42/15 | 5/3 |
| 8 | 48/14 | 61/15 | 36/14 | 31/10 | 65/19 | 50/16 | 44/11 | 36/15 | 37/14 | 1/0 |
| 12.5 | 47/12 | 60/18 | **17/5** | **18/5** | 60/18 | 49/14 | 43/10 | 4/1 | unstable | unstable |
| 19 | 52/13 | 58/17 | 34/8 | 26/6 | 63/18 | 54/15 | 48/11 | 23/6 | 10/3 | unstable |
| 26 | 55/15 | 60/19 | 46/11 | 33/8 | 63/20 | 57/17 | 51/12 | 42/10 | 44/11 | unstable |

**Credible-family safe edges per speed** (min over nominal, J_lo, J_hi, b_lo, b_hi, tau0, tau6; Kd 16, fI 0.3):

| speed | 3 | 5 | 8 | 12.5 | 19 | 26 | 30 m/s |
|---|---|---|---|---|---|---|---|
| edge | 637 | 682 | 730 | 1178 | 3070 | 3520 | 3520 |
| binding member | `b_lo` | `b_lo` | `b_lo` | `J_hi` | `b_lo` | `b_lo` | `b_lo` |

Stress-member edges: `J_hi2` 682–4322, `ms_free` 452–4628, `light_b` 321–368.

**Pre-registration: what one short drive shows.** These are the exact closed-loop wheel modes (least-damped pair below
8 Hz) under the ROBUST schedule. Each column is what the 0x14A angle should show if that member were the truth.

| v | nominal | b_lo | J_hi | light_b (prior) |
|---|---|---|---|---|
| 3 | 2.25 Hz ζ 0.71 | 2.69 Hz ζ 0.45 | 1.51 Hz ζ 0.51 | 2.89 Hz ζ 0.16 |
| 8 | 2.78 Hz ζ 0.58 | 3.15 Hz ζ 0.37 | 1.91 Hz ζ 0.41 | 3.17 Hz ζ 0.11 |
| 12.5 | 1.86 Hz ζ 0.81 | 3.42 Hz ζ 0.40 | 2.26 Hz ζ 0.38 | **UNSTABLE 3.8 Hz** |
| 19 | 2.72 Hz ζ 0.64 | 4.28 Hz ζ 0.33 | 2.94 Hz ζ 0.41 | **UNSTABLE 4.9 Hz** |
| 26 | 2.50 Hz ζ 0.66 | 4.07 Hz ζ 0.36 | 2.57 Hz ζ 0.54 | **UNSTABLE 5.1 Hz** |

- **A 4–4.3 Hz ring at ≥ 19 m/s means `b_lo`.** The design could then not be raised.
- **A 2.4–2.7 Hz well-damped mode means the nominal.** The dose could then rise toward the design.
- **A growing 5 Hz oscillation means the prior world.** Stop.
- The 0x14A angle at 100 Hz resolves all three. The orchestrator owns turning this into an instrument and a prereg.

## 11. What a fresh 1 kHz operand buys (`out_part*` §8; a cave that rebuilds `gp-0x6a00` at 1 kHz)

The comparison is held vs fresh, at the same gains (the §8d design):

| v | PM held → fresh | exact GM held → fresh | M20 held → fresh | safe edge held → fresh (fc there) |
|---|---|---|---|---|
| 3 | 45.1 → 50.8 | 14.0 → 21.3 | 2.93 → 3.13 | 1100 (2.92) → 1178 (3.04) |
| 5 | 47.8 → 53.6 | 14.2 → 21.5 | 2.93 → 3.13 | 1100 (2.94) → 1262 (3.18) |
| 8 | 51.1 → 57.0 | 14.3 → 21.6 | 2.94 → 3.14 | 1262 (3.20) → 1351 (3.32) |
| 12.5 | 50.5 → 56.4 | 14.0 → 21.1 | 3.26 → 3.48 | 2678 → 2678 |
| 19 | 47.8 → 53.7 | 11.3 → 15.7 | 3.02 → 3.23 | 4956 (3.09) → 5307 (3.27) |
| 26 | 45.3 → 51.2 | 11.4 → 16.1 | 3.52 → **3.76** | 5683 (3.01) → **5307 (2.86)** |

- **Phase (EVIDENCE):** +5.8–5.9° PM at every speed, which is exactly the hold's 5.9° at 3 Hz.
- **The 20 Hz bar (EVIDENCE):** M20 rises 7 %. The hold's |H(20)| = 0.936 was attenuating the operand at 20 Hz. V295's
  bar includes its own hold, so the fresh loop hits the bar sooner at highway gains.
- **Ages 0–9 instead of 1–10** (slot 4 landing before slot 0 in the activation tick): +1.0–1.1° PM. That is
  negligible.
- **Verdict (BELIEF).** Freshness alone is not worth a cave for this loop. A cave that reads the motor-count angle is
  worth it for **resolution** (§13a): `gp-0x6cc4`, 32.17 counts per 0.1 deg, is about 0.003 deg per count. The frame
  rebuild must reproduce `gp-0x6a00`'s 0–7.3 deg correction table; `gp-0x69ca` alone is off by that table and by the
  1/1.155 slope near centre (tracer-angle).

## 12. The 20 Hz plant mode, as the record models it (`out_part*` §9)

These are exact lifted closed-loop poles; each cell gives the ζ of the least-damped 10–50 Hz pole. The stress plants:

- the collocated two-mass family, f2 16/20/24 Hz, r2 0.2/0.5/0.8, ζ2 0.02/0.05 (redo-audit rp4);
- the V289/V290 multiplicative fits.

Selected rows (the angle loop is the §8d design):

| plant | v | open | V295 | V282 | angle, held | angle, fresh |
|---|---|---|---|---|---|---|
| two-mass 20 Hz r2 0.2 ζ 0.02 | 3 | 0.044 | 0.041 | **−0.020 UNSTABLE** | 0.040 | 0.043 |
| two-mass 20 Hz r2 0.5 ζ 0.02 | 3 | 0.117 | 0.101 | **−0.075 UNSTABLE** | 0.100 | 0.112 |
| two-mass 16 Hz r2 0.5 ζ 0.02 | 3 | 0.140 | 0.130 | **−0.091 UNSTABLE** | 0.120 | 0.139 |
| two-mass 20 Hz r2 0.2 ζ 0.02 | 26 | 0.078 | 0.081 | 0.150 | 0.077 | 0.079 |
| V289 'resonant' 21.0 Hz ζ 0.010 | 3 | 0.010 | 0.025 | **UNSTABLE** | 0.025 | 0.016 |
| V289 'resonant' | 26 | 0.010 | 0.012 | **UNSTABLE** | 0.024 | 0.021 |
| V289 'smooth+mode' 22.5 Hz ζ 0.05 | 12.5 | 0.050 | 0.064 | **UNSTABLE** | 0.066 | 0.059 |

- **Across the 45 rows where a lightly damped mode exists** (r2 ≤ 0.5, and the multiplicative fits), the held angle
  loop moves ζ by −0.022…+0.016 from the open plant. It is unstable on none of the 63 rows. EVIDENCE.
- **V282 is unstable on 23 of the 63.** That is the positive control.
- At r2 0.8 the flexible mode is overdamped by b at speed, so there is no mode to de-damp; those rows print 25 or 50 Hz
  with ζ > 0.75.
- BELIEF: the real 20 Hz object lies inside this bracket. The r71b drive could not identify anything above about 8 Hz.

## 13. The nonlinear items (static and describing-function estimates; `out_part*` §10, `egain_part1.txt`)

### 13a. The 0.1 deg LSB of `gp-0x6a00`

One LSB moves the P torque by Kp·0.01002 T counts. Near an LSB boundary the quantiser is a relay. Its DF limit cycle
sits at the phase crossover f180, with angle amplitude 2·LSB·|L(f180)|/π and torque fundamental |C_fb(f180)|·2·LSB/π.

| schedule (Kd 16, fI 0.3) | v m/s | T per LSB | Fs | f180 | LC torque | LC angle / wheel rate | verdict |
|---|---|---|---|---|---|---|---|
| ROBUST | 3–12.5 | 6.4–11.8 | 95–18 | 8.6–9.9 Hz | 4.9–5.7 | 0.006–0.008 deg / 0.35–0.43 deg/s | friction holds |
| ROBUST | 19–30 | 30.8–35.3 | 9.1–5.6 | 9.0–9.1 Hz | 10.6–11.8 | 0.007–0.008 deg / 0.41–0.44 deg/s | **LC plausible** |
| design | 3–12.5 | 9.0–23.4 | 95–18 | 7.1–7.4 Hz | 5.3–9.5 | 0.011–0.015 deg / 0.5–0.7 deg/s | friction holds |
| design | 19–30 | 46.4 | 9.1–5.6 | 7.9–8.3 Hz | 15.9–16.3 | 0.011–0.014 deg / 0.57–0.70 deg/s | **LC plausible** |

(The §8d design is 47.8–56.9 T per LSB and 17.7–20.8 T at 7.0–7.2 Hz at 19–30 m/s; `out_part*` §10.)

**BELIEF: a new 8–9 Hz tone at highway speed is the most likely line this loop adds.** The 100 Hz hold quantises
limit-cycle periods to whole 10 ms, i.e. 100/n Hz: 8.3 or 9.1 Hz. Each relay switch is one LSB of the angle the fork also reads. The time-domain
harness must run the integer lane with the 0.1 deg quantiser and Karnopp friction before any dose. The cures are a finer
operand (cave, §11) or a lower highway gain.

### 13b. The integrator deadband `0xC62E4` (DB, stock 4)

`exc = (E>>5) ∓ DB` stops the I for e in [−2DB, 2DB+1] counts: ±0.85 deg at DB 4, ±0.25 deg at DB 1. The I engages
only when the P-only error kθ/(Kp′+k) exceeds that.

| v | turn at a_lat 0.5 / 1 / 2 m/s² | design: P-only, DB 4, DB 1 | robust: P-only, DB 4, DB 1 |
|---|---|---|---|
| 8 | 20 / 41 / 81 deg | 0.84; 0.96–0.99; 0.99 | 0.78; 0.96–0.99; 0.99 |
| 12.5 | 8.3 / 17 / 33 deg | 0.88; 0.89–0.97; 0.96–0.99 | 0.79; 0.89–0.97; 0.96–0.99 |
| 19 | 3.6 / 7.2 / 14 deg | 0.86; **0.86–0.94**; 0.92–0.98 | 0.80; **0.80–0.94**; 0.92–0.98 |
| 26 | 1.9 / 3.8 / 7.7 deg | 0.89; **0.89**; 0.89–0.96 | 0.86; **0.86–0.88**; 0.86–0.96 |
| 30 | 1.4 / 2.9 / 5.8 deg | 0.89; **0.89**; 0.89–0.95 | 0.86; **0.86**; 0.86–0.95 |

- **With the stock DB 4 the I is inert in highway turns, and turn-hold FAILS ≥ 0.90.** EVIDENCE for the arithmetic;
  static, so BELIEF for the drive.
- Lowering DB to 1 (cal) fixes it except for 1.4–3 deg turns. At 3 m/s the friction band (0.98–1.35 deg) is then 4–5×
  the dead zone: the textbook PI-plus-stiction hunting set-up.
- **The E-gain cave resolves both if g(v) is applied before `E>>5`** (BELIEF on the cave): the zone in degrees becomes
  0.85/g(v), so 0.85 deg at 3 m/s and 0.15–0.18 deg at 19–30 m/s.

### 13c. Friction band versus torque mode

| v | angle loop Fs/(Kp′+k) | torque mode 2Fc/k |
|---|---|---|
| 3 | 0.98 (design) / 1.35 (robust) deg | 23.6 deg |
| 8 | 0.15 / 0.20 deg | 1.33 deg |
| 26 | 0.011 / 0.015 deg | 0.16 deg |

The angle loop is 7–24× stiffer against Coulomb friction. That is the frequency-domain argument that dwell-then-jump
shrinks. BELIEF; it is static, and the I and the LSB interact with it.

## 14. The output lag `0xC63EC`/`0xC63EE` is not available (`out_part*` §11)

The pole is moved with the DC held at 0.990, and the 3.0 Hz crossover is kept (§8d Kd(v)):

| oa / ob (pole) | 3 m/s: Kp, PM, M20 | 12.5 m/s: Kp, PM, M20 | 26 m/s: Kp, PM, M20 |
|---|---|---|---|
| 992 / 507 (5.05 Hz, as built) | 1153, 42.9°, 2.94 | 2401, 50.5°, 3.26 | 5656, 45.3°, 3.52 |
| 979 / 713 (7.15 Hz) | 1046, 53.6°, **4.02** | 2227, 59.7°, **4.41** | 5275, 53.4°, **4.54** |
| 960 / 1014 (10.3 Hz) | 986, 61.7°, **5.43** | 2132, 66.9°, **5.93** | 5068, 60.0°, **5.94** |

- **Every move buys 10–20° of PM and breaks the 20 Hz bar.** EVIDENCE. The lag stays at 992/507.
- This agrees with the record's strike of the same cells on V282 (BUILD-LINEAGE, "Struck the same day"), for a
  different reason: the 20 Hz bar here, GM there.

## 15. RECOMMENDED CAL SETS

The common base is the TRACE §3 edit set. Bytes are from that trace; this harness only verified the arithmetic they
produce (§2.3):

- **edits 1, 2, 4:** angle operand, add, setpoint from `gp-0x69ae`.
- **edit 5:** D on −rate.
- **edit 6:** I reset on ramp 0. It is needed once Ki > 0.
- **cals:** a `0xC63E8` = 0x0000, b `0xC63EA` = 0x2000 (8192), C `0xC62E6` = 0xFFFF.
- **D clamp:** `0xC61B6` = 10240 (the stock value; V295 has 0).
- **unchanged:** P clamp `0xC61BC` 15360, I clamp `0xC61BA` 10240, output lag 992/507, lane clamp 3072.

**Records at the live selector 7.** The kit measured selector 7 on the wire; only these records act:

- **Kp record:** `0xCB994[7]` → `0xE5378`. n = 5. X at `0xE537A` = 0, 68, 112, 136, 208 (idx). Y at `0xE5384`.
- **Kd record:** `0xCB7D4[7]` → `0xE511C`. n = 4. X at `0xE511E` = 0, 11, 22, 32. Y at `0xE5126`.
- **Scalars:** Ki `0xC63E6` and DB `0xC62E4`.

Slots 0–9 point to distinct records (EVIDENCE: Python LE read of both pointer tables).

| schedule | needs | Kp Y (5) | Kd Y (4) | Ki | DB | meets the goal? (frequency domain, nominal) |
|---|---|---|---|---|---|---|
| **A. Speed schedule, ROBUST (recommended first dose)** | a cave: g(v) on E, with knots 691 / 1152 / 1843 / 2880 / 4378 / 5990 / 6912 in `gp-0x6a5e` units and g = 1.000 / 1.071 / 1.146 / 1.849 / 4.819 / 5.526 / 5.526; held at g(3 m/s) whenever `gp-0x67f4` flags speed invalid | 637 flat | 16 flat | 154 | 4 (zone scales as 1/g if g precedes `E>>5`) | Passes every safety gate on every credible member (by construction of the edge; LTI GM in the scan), and the strict \|S\| on the nominal. Crossover 1.6–2.1 Hz on the nominal (2.4–3.4 on `b_lo`). Tracking 0.91–0.99 at 8–19 m/s on the nominal. Drive-identifiable (§10) |
| A′. Speed schedule, nominal design | same cave, g = 1, 1.071, 1.147, 2.606, 5.165, 5.165, 5.165 on a base of 896 | 896 flat | 16 flat | 216 | 4, or 1 (§13b) | 6 of 7 speeds (2.43 Hz at 3 m/s). PM 17–36° on `b_lo`/`J_hi`; setpoint gain 1.09–1.27 at 1.6–3 Hz |
| A″. Kp and Kd by speed (§8d) | both LERPs speed-keyed (BELIEF: key swaps or a cave) | 1100 / 1100 / 1123 / 2401 / 4766 / 5656 / 5683 | 24 / 24 / 24 / 24 / 8 / 8 / 8 | ∝ Kp, 0.2413·Kp | — | 7 of 7 on the nominal; least robust |
| **B. FLAT (cal-only)** | none | 1100 ×5 (782 credible-robust) | 24 ×4 | 177 (126) | 4 | **NO.** Fails tracking at ≥ 8 m/s (crossover 0.34–0.62 Hz at 19–30 m/s) |
| **C. Angle-indexed (cal-only)** | none | identical to B at every knot (§8c) | — | — | — | **NO**, same as B |

## 16. Pre-registered criteria, what fired, and what this harness cannot see

**Written before the sweep was scored:** the safety gates of §7, without the strict |S| reading, and the performance
criteria of §7.

**Fired:**

- **The strict |S| reading.** It was added after the first pass, and it is stated as such everywhere it appears.
- **Tracking at 8 and 19 m/s** for a PI corner of 0.2 Hz.
- **Every safety gate on `light_b`.**
- **PM ≥ 45° on `b_lo`/`J_hi`** for every 3 Hz design.

**Could have returned "do not flash" and did:** for V282 (§2) and for every flat or angle-indexed design at highway
speed (tracking). It did not for the robust speed schedule on the identified members.

**Cannot see:**

- the integer floors, the clamps (P 15360 binds at e = 15360·16/Kp: 43–386 counts, 4.3–38.6 deg, across the schedules), the I deadband, Coulomb friction
  and the LSB (§13);
- the sentinel and fault transients (TRACE §5);
- engage and disengage (the ramp, the sign-hold gate);
- the driver-torque fade below 254/256 (f floor 0.297 scales the whole loop down, so it is safe-side for stability);
- the fork's 100 Hz outer loop and its 60 ms round trip;
- the 13 Hz torsion line (BELIEF in the identification);
- everything above about 8 Hz in the real plant, which r71b did not identify.

**The time-domain harness must take, in order:**

1. 13a (LSB);
2. 13b (DB and hunting);
3. the fault and engage transients with the speed-fault fallback;
4. the fork interface.

## 17. Bode tables (LTI fundamental; `bode_part1.txt` has all designs and speeds)

Rows are |L|, ∠L in degrees, |T_ref| (θ/θ_sp) and |S|. For V295 the T_ref row is its complementary T, because V295's
setpoint is a torque command, not an angle.

**ROBUST E-gain schedule (Kd 16, fI 0.3)**

| v, gains | row | 0.05 | 0.1 | 0.3 | 0.5 | 1 | 1.6 | 2 | 2.5 | 3 | 4 | 5 | 7 | 10 | 13 | 15 | 17 | 20 | 25 | 30 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v  3.0 Kp   637 Ki  154 Kd  16 | \|L\| | 58.554 | 28.258 | 7.940 | 4.359 | 2.024 | 1.214 | 0.946 | 0.731 | 0.585 | 0.402 | 0.292 | 0.172 | 0.092 | 0.056 | 0.043 | 0.033 | 0.024 | 0.015 | 0.010 |
|  | angL | -95 | -99 | -105 | -106 | -110 | -116 | -120 | -126 | -132 | -142 | -152 | -168 | 173 | 157 | 148 | 139 | 126 | 106 | 87 |
|  | \|Tref\| | 1.003 | 1.012 | 1.066 | 1.097 | 1.090 | 1.011 | 0.926 | 0.794 | 0.649 | 0.402 | 0.245 | 0.103 | 0.038 | 0.018 | 0.012 | 0.008 | 0.005 | 0.003 | 0.001 |
|  | \|S\| | 0.017 | 0.036 | 0.129 | 0.239 | 0.517 | 0.840 | 1.032 | 1.219 | 1.332 | 1.379 | 1.324 | 1.201 | 1.101 | 1.054 | 1.037 | 1.025 | 1.014 | 1.004 | 0.999 |
| v 12.5 Kp  1178 Ki  284 Kd  16 | \|L\| | 23.156 | 11.803 | 4.465 | 2.952 | 1.608 | 1.012 | 0.800 | 0.624 | 0.504 | 0.352 | 0.260 | 0.158 | 0.087 | 0.055 | 0.042 | 0.033 | 0.024 | 0.015 | 0.010 |
|  | angL | -88 | -86 | -83 | -85 | -95 | -105 | -111 | -118 | -124 | -135 | -144 | -161 | 179 | 163 | 153 | 144 | 130 | 110 | 90 |
|  | \|Tref\| | 0.998 | 0.994 | 0.970 | 0.952 | 0.913 | 0.841 | 0.776 | 0.679 | 0.578 | 0.399 | 0.272 | 0.135 | 0.057 | 0.028 | 0.019 | 0.014 | 0.009 | 0.005 | 0.003 |
|  | \|S\| | 0.043 | 0.084 | 0.213 | 0.313 | 0.551 | 0.819 | 0.969 | 1.111 | 1.201 | 1.261 | 1.245 | 1.172 | 1.096 | 1.055 | 1.038 | 1.027 | 1.015 | 1.005 | 1.000 |
| v 26.0 Kp  3520 Ki  849 Kd  16 | \|L\| | 36.661 | 18.527 | 6.577 | 4.107 | 2.099 | 1.288 | 1.008 | 0.778 | 0.623 | 0.426 | 0.309 | 0.182 | 0.098 | 0.060 | 0.045 | 0.036 | 0.026 | 0.016 | 0.011 |
|  | angL | -89 | -89 | -89 | -93 | -101 | -111 | -116 | -123 | -129 | -140 | -150 | -166 | 174 | 159 | 149 | 140 | 128 | 108 | 89 |
|  | \|Tref\| | 1.000 | 0.999 | 0.994 | 0.992 | 0.993 | 0.985 | 0.961 | 0.901 | 0.807 | 0.586 | 0.407 | 0.212 | 0.099 | 0.055 | 0.039 | 0.029 | 0.020 | 0.011 | 0.007 |
|  | \|S\| | 0.027 | 0.054 | 0.150 | 0.239 | 0.467 | 0.756 | 0.946 | 1.150 | 1.292 | 1.382 | 1.338 | 1.213 | 1.108 | 1.059 | 1.040 | 1.028 | 1.016 | 1.005 | 1.000 |

**V295 (rate operand, held)**

| v, gains | row | 0.05 | 0.1 | 0.3 | 0.5 | 1 | 1.6 | 2 | 2.5 | 3 | 4 | 5 | 7 | 10 | 13 | 15 | 17 | 20 | 25 | 30 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v  3.0 Kp   960 Ki    0 Kd   0 | \|L\| | 0.006 | 0.022 | 0.125 | 0.230 | 0.435 | 0.571 | 0.607 | 0.611 | 0.587 | 0.504 | 0.415 | 0.278 | 0.161 | 0.101 | 0.078 | 0.061 | 0.044 | 0.027 | 0.018 |
|  | angL | 164 | 150 | 109 | 85 | 47 | 13 | -5 | -25 | -42 | -69 | -91 | -122 | -154 | -177 | 170 | 158 | 143 | 119 | 98 |
|  | \|Tref\| | 0.006 | 0.022 | 0.129 | 0.220 | 0.325 | 0.366 | 0.378 | 0.388 | 0.394 | 0.397 | 0.385 | 0.314 | 0.187 | 0.113 | 0.084 | 0.065 | 0.046 | 0.028 | 0.018 |
|  | \|S\| | 1.006 | 1.019 | 1.034 | 0.956 | 0.748 | 0.641 | 0.623 | 0.635 | 0.671 | 0.787 | 0.927 | 1.132 | 1.165 | 1.113 | 1.083 | 1.060 | 1.036 | 1.013 | 1.002 |
| v 12.5 Kp   960 Ki    0 Kd   0 | \|L\| | 0.001 | 0.005 | 0.037 | 0.082 | 0.185 | 0.264 | 0.293 | 0.310 | 0.314 | 0.296 | 0.266 | 0.202 | 0.132 | 0.089 | 0.070 | 0.056 | 0.041 | 0.026 | 0.018 |
|  | angL | 171 | 163 | 133 | 109 | 67 | 34 | 17 | -2 | -18 | -44 | -65 | -98 | -133 | -160 | -174 | 173 | 155 | 130 | 107 |
|  | \|Tref\| | 0.001 | 0.005 | 0.038 | 0.084 | 0.170 | 0.215 | 0.228 | 0.237 | 0.241 | 0.241 | 0.234 | 0.204 | 0.144 | 0.097 | 0.075 | 0.059 | 0.043 | 0.027 | 0.018 |
|  | \|S\| | 1.001 | 1.005 | 1.025 | 1.024 | 0.922 | 0.815 | 0.779 | 0.763 | 0.768 | 0.813 | 0.880 | 1.008 | 1.094 | 1.090 | 1.075 | 1.059 | 1.039 | 1.017 | 1.005 |
| v 26.0 Kp   960 Ki    0 Kd   0 | \|L\| | 0.001 | 0.003 | 0.018 | 0.038 | 0.079 | 0.112 | 0.124 | 0.133 | 0.136 | 0.133 | 0.124 | 0.103 | 0.076 | 0.057 | 0.048 | 0.040 | 0.031 | 0.022 | 0.015 |
|  | angL | 170 | 160 | 127 | 103 | 66 | 37 | 22 | 5 | -8 | -31 | -49 | -78 | -110 | -135 | -150 | -164 | 178 | 150 | 125 |
|  | \|Tref\| | 0.001 | 0.003 | 0.018 | 0.038 | 0.077 | 0.102 | 0.111 | 0.118 | 0.120 | 0.119 | 0.114 | 0.100 | 0.078 | 0.059 | 0.050 | 0.042 | 0.032 | 0.022 | 0.015 |
|  | \|S\| | 1.001 | 1.002 | 1.011 | 1.008 | 0.967 | 0.916 | 0.896 | 0.883 | 0.881 | 0.896 | 0.922 | 0.974 | 1.024 | 1.041 | 1.043 | 1.040 | 1.032 | 1.019 | 1.009 |
