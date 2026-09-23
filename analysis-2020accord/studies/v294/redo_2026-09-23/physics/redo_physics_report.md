# V294 control physics: an independent redo

The author is redo-physics (Opus, a subagent). The date is 2026-09-23. Nothing was flashed, no CAN was sent and no repo file was edited.
Every script and output file is in this scratchpad, named `rp*.py` and `rp*_out.txt`.
I did my own derivation first (rp1 to rp7b) and only afterwards read `v294_design.py` (rp8).

## Verdict in one paragraph

**No finding here says "do not flash" on the physics of the image.**
- The operand, gain, sign, stability, 20 Hz margin and outer-loop benefit all hold.
- **Two of the brief's FAIL criteria fire as written.**
  - **ζ× falls below 1 at speeds of 8 m/s and below.** The claimed ζ× numbers come from a quasi-static formula. Exact closed-loop poles give ×0.89 at 5 m/s, and ×0.78 to ×0.92 across 2–5 m/s. The plant is BELIEF.
  - **The within-drive instrument as specified cannot tell live from null.** It has the wrong units. On real V293 null routes it reads a positive "live-like" slope.
- **The instrument failure is fixable offline, with no image change.** The fix is verified on the same real data and needs three parts:
  - a byte-exact dynamic predictor;
  - a regressor that includes the output lag;
  - feedforward nuisance terms.
- **Four smaller corrections.**
  - The 180° crossing sits at 19–24 Hz, not about 26 Hz or 40 Hz. That puts it on the 20 Hz line, but the effect there is negligible.
  - Max |L| is 1.1–1.2, not 1.7.
  - The trim goes one-sided near the rail.
  - "PID" is a misnomer.
- **A risk the page does not state.** The V294 fork config is essentially route 71's config. On the V293 plant my model makes it unstable at 19 m/s and above, at 2.4–2.7 Hz; route 71 measured 2.34 Hz. **If the trim is not live, route 71's limit cycle is the expected symptom at speed.**

| # | claim | result |
|---|---|---|
| 1 | The operand is a 1st-order LP on α at 2.0 Hz. It settles to exactly 0, with no bias. | **PASS.** Pole 2.0335 Hz. Exact 0 at every constant x. Dither strictly under 2 counts. |
| 2 | 1.85 T per deg/s. Cap binds at about 230 deg/s or 2900 deg/s². | **PASS with correction.** 1.75 at 2.0 Hz; 1.85 is the value at 2.4 Hz. Below the pole, K_α is 0.2097 T per deg/s². The cap bounds are right. The trim goes one-sided at idx 236 and above. |
| 3a | The trim never assists below its 180° crossing. | **PASS** |
| 3b | ζ× 1.02 / 1.16 / 1.49 / 1.82 / 2.05 | **FALSIFIED, and the brief's FAIL criterion fires.** Exact values are 0.89 / 1.00 / 1.29 / 1.43 / 1.73 on the map k, or 0.92 / 1.05 / 1.39 / 1.81 / 2.28 on the design's own levelled k. |
| 3c | \|L\| < 1 at every −180° crossing | **PASS.** 0.023 at 20.8 Hz. No encirclement. No unstable pole in any of more than 3,000 variants. |
| 3d | 20 Hz: −26.7 dB, 2.08 vs 44.9 | **CONFIRMED.** 2.079 vs 44.90. V294 is 4–6 % of V282's controller at every frequency from 1 to 60 Hz. |
| 3e | Anti-damps only from about 26 Hz (docstring says about 40 Hz) | **CORRECTED.** Depends on transport delay: 33 / 24 / 19 / 15 Hz at 1 / 2 / 3 / 5 ms. Negligible in size. |
| 4 | "PID + FF on acceleration" | **Not honest naming.** It is P-only on 2 Hz-lagged acceleration, plus FF. Ki and Kd must be 0 because of the structure, not by choice. "I = V282's loop" holds as a class, not as a gain. |
| 5 | Outer-loop PM | **PASS at nominal.** Light world gains 12–53°. Identified world loses 7° at most. The criterion fires only in corner cases where at least 49° of margin remains. |
| 6 | Instrument | **FAIL as specified; PASS with the fix.** Verified on real V293 routes 70–75, using a synthetic-live positive control. |

## Claim 1: the operand (EVIDENCE: integer arithmetic, brute force)

This integer mirror is written from the instruction list. Its output matches the golden model's `lkas_fb_lag` on 100,000 of 100,000 ticks (rp1):
```python
s_new = ((1011*s) >> 10) + ((567*x) >> 10)   # 0x28F8E..0x28FA2, sar floors
r26   = clamp(s_new - s, +-1024)              # 0x28FA4 subr r9,r26 ; clamp 0xC62E6
s     = s_new                                  # 0x28FA8
```

**The transfer function.** Let p = 1011/1024 and g = 567/1024. Then R(z)/X(z) = g(1 − z⁻¹)/(1 − p z⁻¹).
- The pole sits at −ln(p)/(2π·1 ms) = **2.0335 Hz**.
- Relative to acceleration, this is a first-order low-pass at the pole. It matches the continuous 1/(1+s/ω_p) to within 0.01° and 0.1 % from 0.1 to 50 Hz, because the half-sample delay cancels the discretisation phase.
- The DC gain from α to r26 is g·Ts/(1−p) = 0.043615 r26 per x-count/s. That is **0.34892 r26 per deg/s²** at x = 8 counts per deg/s (the x scale is EVIDENCE).
- The high-frequency gain of |r26/x| tends to g = 0.5537, and to 0.5572 at Nyquist.
- A float simulation of the recursion matches the formula to 5 digits at 1, 2 and 20 Hz.

**It settles to exactly 0.** At constant x, F(s) = ⌊a·s/1024⌋ + c is non-decreasing, so every orbit is monotone and bounded. It reaches a fixed point, where r26 = s_new − s = 0 exactly.
- Brute force covered all 24,001 values of x in ±12000, from 4 starting states each (0, ±2²⁰, random). Every one reached 0; the worst took 822 ticks.
- The state has a fixed-point interval 78–79 counts wide (= 1/(1−p)). That is hysteresis in s, not in the operand.

**Dither.** Write s_int = p·s + g·x + e with e in (−2, 0]. Then r26_int − r26_lin = e_n − (1−p)·Σ pᵏ e₍n−1−k₎, which lies strictly inside ±2.
- Observed extremes of the difference were about ±1.16 on white noise, ramps, sines and random walks, with an rms near 0.41 and a mean of 0.0000.
- An adversarial random search reached 1.96.
- Worst case is therefore under 2 operand counts, which is under 1.2 T counts before the output lag.

**No dead zone.** Under constant acceleration the operand pulse-width-modulates between adjacent integers, and its mean equals the linear value to 4 digits even at 0.125 deg/s².

## Claim 2: gain through the chain (EVIDENCE: two independent methods)

The chain is:

T = −3.75 · (254/256) · H_out · (5346/32768) · r26

- **DC.** T is −0.60109 T counts per r26 count. **K_α is 0.20974 T counts per deg/s²** below the pole.
- **Clamp.** The clamp of 1024 gives P = 3840, then S = 3810, then T = 615.5 counts, which is 0.250 of the rail.
- **Two methods agree.** The linear z-domain product and the golden model's integer `lkas_fb_lag` + `lkas_rate_pid_tick` marched on integer sines agree to within 1 % and 1°.

| f (Hz) | T per deg/s | phase re rate | T per deg/s² | rate at which \|r26\| = 1024 |
|---|---|---|---|---|
| 0.5 | 0.637 | −110° | 0.203 | 962 deg/s |
| 1 | 1.160 | −127° | 0.185 | 521 |
| 2 | **1.747** | −156° | 0.139 | 328 |
| 2.4 | **1.847** | −165° | 0.123 | 301 |
| 3 | 1.907 (the peak) | −177° | 0.101 | 277 |
| 10 | 1.184 | +128° | 0.019 | 234 |
| 20 | 0.652 | +110° | 0.005 | 231 |

**Correction.** "1.85 per deg/s of 2 Hz-band rate" is the 2.4 Hz value; at 2.0 Hz it is 1.75.
- Resulting trim: 17.5 T counts at 10 deg/s, and 154–163 at 88 deg/s.
- The cap claim is right. It binds at 231 deg/s or more for content at 10 Hz and up, 328 deg/s at 2 Hz, and **2935 deg/s²** below the pole.
- The int32 figure is right: 0.246 of 2³¹ at x = 12000, where the fixed point is s = 523,3xx.

**Mixture at 2–3 Hz.** Adversary A's "97 % damping / 26 % inertia at 2–3 Hz" is correct: e^(−j165°) = −0.966 − 0.259j.

**New: the P clamp makes the trim one-sided near the rail.** P = 15·sp − 3.75·r26 is clamped at ±15360. When 15·sp approaches 15360, the trim can only reduce |T|.
- The delivered trim gain at 2 Hz and 40 deg/s is 1.75 up to idx 230. It falls to 1.23 at idx 236, 0.91 at 238, 0.77 at 239 and 0.59 at 240.
- This rectifies the trim into a small bias of up to about 15 counts away from the command.
- It cannot destabilise anything. The circle criterion for a sector [0,1] needs Re L > −1, and min Re L is −0.108 to −0.145 at every speed and in both worlds.

## Claim 3: the wheel mode and the plant modes

**Setup.**
- Plant, BELIEF, from the fork's `latcontrol_vehicle_tunes.py` @ `54ff1ea39`:
  - J = 8e-5 u/(deg/s²);
  - k(v) from the map (the design additionally applies the hold level: ×1.15 at 12.5 m/s and below, ramping to ×1.45 at 17.5 m/s and above);
  - b light = 6e-4, or identified b = 1/G(v).
- u converts to T at **2625.4 T counts per u**. That is the V293 surface slope of 10.336 T per idx × 4096 / 16.125736. K_α/J then comes out at 0.999.
- The closed loop is exact discrete time at 1 kHz:
  - ZOH plant;
  - a rate former taking a 3 ms position difference (BELIEF);
  - the integer-derived controller;
  - a transport delay of d ticks.
- A continuous 4th-order model gives the same ζ to within 0.01 (rp3b).

**3b: the damping ratio of the wheel mode, from exact closed-loop poles** (rp3, rp3b, rp3c):

| pole | 5 m/s | 8 | 12.5 | 19 | 26 | (light b, map k) |
|---|---|---|---|---|---|---|
| 16.5 Hz | 0.77 | 0.82 | 0.92 | 0.97 | 1.08 | |
| 8 Hz | 0.79 | 0.84 | 0.97 | 1.03 | 1.16 | |
| **2.0 Hz (shipped)** | **0.89** | **1.00** | 1.29 | 1.43 | 1.73 | |
| 1.4 Hz | 0.95 | 1.10 | 1.50 | 1.70 | 2.13 | |

**Why the claimed numbers differ (rp8).** `v294_design.mode_analysis` reproduces 1.02 / 1.16 / 1.49 / 1.82 / 2.05 exactly. It evaluates b_eff/(2√(k·J_eff)) at an iterated frequency, which is a perturbation estimate.
- On the design's own inputs (levelled k, J, b), exact poles give **0.92 / 1.05 / 1.39 / 1.81 / 2.28**.
- The quasi-static formula overstates the low-speed benefit by about 10 %. It understates it at 26 m/s.

**Low-speed detail, light b, map k:**

| v (m/s) | ζ open → trim | mode frequency (Hz) | step overshoot | decay rate σ |
|---|---|---|---|---|
| 2 | 0.73 → 0.57 | 0.82 → 0.52 | 3.7 → 11.7 % | ×0.50 |
| 5 | 0.56 → 0.50 | 1.07 → 0.69 | 12 → 18 % | ×0.57 |
| 8 | 0.465 → 0.465 | | | |

- ζ× crosses 1.00 at 8.0 m/s.
- **Worst case across the robustness grid is 0.55–0.61.** The grid covered b from 3e-4 to 6e-3, k ×0.5 to ×2, K/J 0.5 to 2 and delay d from 0 to 8 ticks. The worst case is at 3 m/s with K/J = 2 and k ×0.5.
- **Mechanism.** At low speed the mode (0.5–1 Hz) sits below the 2 Hz pole, where the trim is almost pure inertia. J_eff/J is about 1.7 there, so ζ falls as 1/√J_eff and the damping added cannot keep up.
- **The trim never removes energy-damping.** b_eff > b at every frequency below the 180° crossing.
- At speed, overshoot improves: 41 → 27 % at 26 m/s.
- **But the absolute decay rate σ falls at every speed below about 21 m/s.** The heavier mode is slower. This is the honest "heavier wheel" cost.

**Engaged (fork loop closed, Padé, rp5b).** The least-damped closed-loop pair behaves differently from the plant-alone mode:

| world | v (m/s) | V293 | V294 |
|---|---|---|---|
| light | 3–12.5 | 0.06–0.15 | **0.28** |
| light | 19 | **−0.010 (unstable)** | +0.22 |
| light | 26 | **−0.060 (unstable)** | +0.15 |
| identified | all | 0.75–0.95 | 0.65–0.83 (×0.82–0.87) |

So the plant-alone FAIL at 8 m/s and below does not carry over to the engaged loop in the light world.

**3c: loop gain** (rp3, rp9). Light b, map k, d = 1 tick, m = 3:
- max |L| is 0.84–1.14 at 1.3–2.2 Hz, with phase +12° to +20°.
- With levelled k it is 1.08–1.19, not 1.7.
- The −180° crossing is at 20.8 Hz with **|L| = 0.023**. In the identified world it is at 23.7–30.3 Hz with |L| 0.010–0.017.
- 1 + L has zero encirclements. Every closed-loop |z| is below 1.
- Across 3,456 variants of delay, window, gain, k and b there were **zero unstable closed loops**.

**3e: where the added torque crosses 180° of lag re acceleration** (rp4; Td = sensor + compute + actuator delay, BELIEF):

| Td | 0 ms | 1 | 2 | 3 | 4 | 5 | 8 |
|---|---|---|---|---|---|---|---|
| crossing | none | 33.4 Hz | 23.6 | **19.2** | 16.6 | 14.8 | 11.6 |
| worst anti-damping, as % of the trim's 2.4 Hz damping | 0 | 3.9 % | 7.5 % | 10.8 % | 13.8 % | 16.7 % | 24.5 % |

- A 3 ms rate-former window plus about 1 ms of compute and actuation gives a plausible Td of 2–3 ms. That places the crossing **at the 20 Hz plant line**, not at "about 26 Hz" (the memory) or "about 40 Hz" (the design docstring).
- The size is negligible:
  - Re Cr at 20 Hz is −0.019 T/(deg/s) at Td = 3 ms.
  - V294's |Cr| is 4.1–6.0 % of V282's at every frequency from 1 to 60 Hz. V282's controller is 44.90 P-counts per x-count at 20 Hz; V294's is 2.079. The ratio is 0.0463, or −26.69 dB, which confirms the claim.

**Collocated two-mass family** (rp4). Flexible mode at 12–40 Hz, J_w/J from 0.2 to 0.8, ζ_open 0.02–0.05:
- V294 was never unstable.
- The worst relative change in the flexible mode's ζ is −13 % at d = 2, −20 % at d = 5 and −30 % at d = 8. All three are in the J_w/J = 0.8 family, where V282 itself goes unstable.
- In the J_w/J = 0.2 family the change is −1 to −2 %. That family reproduces V282's recorded near-marginal ring, with ζ 0.003–0.03 at 20–31 Hz.
- **Scale-free check.** V282's rigid-body crossover in this plant lands at 13.7 Hz, against the recorded 17–21 Hz. This roughly corroborates the high-frequency scale of J·2625.
- **The 15–17 Hz pole** was a V289 loop pole with the rate loop live. V294's |L| there is at most 0.05, so the trim cannot recreate it.

## Claim 4: is it "PID + feedforward on acceleration"? (EVIDENCE for the algebra)

No. It is **P-only on a 2 Hz-lagged acceleration, plus FF on the demand.** Physically it is a lagged virtual inertia that acts as a damper at 2–3 Hz. Both other terms are ruled out by the structure, not by choice.

**The I term.** The I path integrates deadband(E>>5)·Ki/8, and S gains I>>7.
- **E = 4·sp − r26 carries the feedforward.** Any Ki > 0 therefore integrates the command.
  - A held turn at sp = 100 gives E>>5 = 12, so 8 counts get past the deadband each tick.
  - At Ki = 100 the integrator reaches its clamp (1,310,720, which is S = 10240, about 1,650 T counts) in about 13 s.
- **The acceleration part telescopes exactly.** Σ r26 = s − s₀, the 2 Hz-lagged rate itself (×43.6).
  - So I on this operand is rate feedback: V282's class. **As a class statement it holds.**
  - As a gain statement it does not. The linear gain is (Ki/32768)·43.6·LP per x-count. Matching V282's P+D, about 30 P per x at 2 Hz, needs Ki of about 3×10⁴; at 20 Hz it needs about 3.3×10⁵.
  - The deadband (|E>>5| ≤ 4, i.e. |r26| < 160) also blocks all small signals.
- **Result.** The I path would be mostly feedforward wind-up and very little damping.

**The D term.** dE = 4·Δsp − Δr26. That has two problems:
1. **A setpoint kick on every 100 Hz 0xE4 step.** This is the V282-era D-bind excitation.
2. **Jerk feedback is anti-damping below about 3.2 Hz** (= √(2.03·5.05)). Cr_D = (Kd/8)(1−z⁻¹)·Cr_P has phase +113° at 2 Hz and +67° at 5 Hz. The anti-damping band is exactly where the wheel mode lives, 0.7–2.7 Hz.
3. A negative Kd flips the sign: it damps below about 3.2 Hz, but becomes a flat-gain anti-damper at 20 Hz.

## Claim 5: the fork's outer loop (BELIEF plant; the fork source was read at `54ff1ea39`)

**Loop model** (rp5, rp5b, rp5c, rp5d):
- Measurement is v²·curvature(θ) from the steering angle, so there is no yaw dynamics in the loop.
- error_lsf = e·(1 + lsf/kp).
- Controller: kp 0.9 flat (controlsd overwrites it), ki 0.3, LAF 14, friction slope 0.011/0.30.
- The jerk LPF and delay compensation act on the reference side.
- Round trip: 25 ms pure delay + the explicit 5 Hz output lag + 100 Hz ZOH, about 62 ms in total.
- Vehicle model: Accord specs, slip factor −7.0e-4.

**Phase margin at the first crossover, V293 plant → V294 plant (nominal):**

| world | 3 m/s | 5 | 8 | 12.5 | 19 | 26 |
|---|---|---|---|---|---|---|
| light b | +29 → +40 | +31 → +46 | +28 → +50 | +19 → +61 | **−3 → +44** | **−20 → +34** |
| identified b | +91 → +85 | +103 → +96 | +119 → +114 | +145 → +145 | +131 → +129 | +128 → +126 |

- The light-world V293 instability at 19 and 26 m/s has its phase crossover at 2.39–2.60 Hz with |L| 1.06–1.41. **Route 71 measured a 2.34 Hz limit cycle above 20 m/s** with Kp 0.85, LAF 14 and friction 0.011. The model reproduces the record, which supports the light-world plant.
- **V294's fork config is route 71's config**, with Kp 0.9 instead of 0.85.
- ⇒ **If the trim is not live, expect route 71's limit cycle on hard curves at 19 m/s and above.** That is both a risk and a free secondary signature.

**Sensitivity grid.** 1,008 cases: 7 speeds × 4 b worlds × map/levelled k × J ×0.5/1/2 × τ 15/25/40 ms × friction on/off.
- **V294 never destabilised a loop that was stable on V293.** It stabilised 247 that were not.
- Among V293-stable cases, the lowest V294 PM was **+18°** (V293 had +4° there).
- The phase lost *at the fork's own crossover* exceeded 10° in 117 of 1,008 corner cases. The worst loss was 27°, at J ×0.5 and 3 m/s, and at least 49° of PM remained.
- **14 cases stay unstable even with V294.** They are b ≤ 3e-4 at 19 m/s and above, plus 32 m/s in the light world. All 14 were also unstable on V293. That is fork-tune risk that the trim does not fully cover.

**Criterion.** "PM loss > 10° at the fork's crossover" is not met at nominal: the largest loss is 7°, in the identified world at 5 m/s. It is met only in the corners above, where absolute margin stays large.

**Pole ladder** (rp8b, rp8c). One cal cell, with b rescaled to hold K/J = 1.
- A lower pole restores low-speed ζ×: a = 1018 (0.94 Hz) gives ζ× 1.07 at 5 m/s, and a = 1020 gives 1.26.
- But it costs outer-loop PM at speed in the light world. At 26 m/s the PM is +34° shipped, +18° at a = 1018 and +5° at a = 1020.
- The shipped 2 Hz pole is the right compromise for the high-speed complaint. The low-speed ζ× is its price.

## Claim 6: the within-drive instrument

### Problems with it as specified
1. **Units.** "Slope ≈ +1.85 T counts per deg/s" is |T/rate| at 2.4 Hz. It is not a regression slope on "the 2 Hz LPF rate, differenced".
   - On R = −d/dt LPF₂.₀₃(0x18F rate) in deg/s², the expected slope is **+0.21**, and only if the output lag is matched. Without it, the slope is attenuated to about 0.07–0.12.
   - Per 10 ms frame difference it would be +21.
2. **It fails on real null data.** V293 forces r26 = 0, so its routes are a true null (rp7, rp7b). I ran the estimator exactly as specified (the flight read's static surface predictor, best lag, regressor R, no nuisance terms) on 20 hands-off engaged 20 s windows from routes 70–75.
   - It read **+0.021 median, 5–95 % [−0.027, +0.087]**. Route 73 read +0.055 and route 71 +0.031.
   - A live trim read by the same estimator gives +0.067, 5–95 % [−0.002, +0.13].
   - **The distributions overlap, so one episode cannot tell them apart.** That is a design failure by the brief's own criterion.
   - Cause: the static predictor ignores the 5 Hz output lag. The null residual is then a filtered copy of the command, and the command drives the wheel.
3. **Sensitive to feedforward gain error** (simulation, rp6). A ±5 % FF gain error, the size of the fade and taper uncertainty the record carries, shifts the as-specified slope by about ±0.05.
   - At 8 m/s with a +5 % error, a null reads −0.035. By the pre-registered sentence, that would be called "sign inverted".

### Fix (EVIDENCE on real data, rp7b)
- **Predictor.** March the integer chain at 1 kHz on the route's own command, including the fade and the output lag. Align the tap instant to the ms. The null residual falls to 7–26 counts rms (the static predictor gives 8–31).
- **Regressor.** R_m = the 5.05 Hz output-lag replica of −d/dt LPF₂.₀₃(0x18F rate)·f_s. This is the firmware's own r26 path in deg/s².
- **Nuisance terms.** FF_pred and dFF_pred/dt.
- **Positive control.** A synthetic live: the V294 trim computed by the integer chain from the route's own 0x18F rate, injected into the real tap.
- **Result, all 20 windows:**
  - null **+0.004** [−0.037, +0.024];
  - live **+0.196** [+0.145, +0.233], which is about K_α = 0.2097;
  - **20/20 correct in both arms** at a threshold of 0.10.
- **Rule for the drive:**
  - β > +0.10 means live;
  - |β| < 0.04 means null;
  - anything else is inconclusive.
- These windows are cruise with a wheel-rate rms of only 1–2 deg/s, where the trim is sub-LSB per frame. The 8-count tap quantisation is dithered away by regression over about 1,000 frames.

### Polarity, from the data
- In the tap's own sign convention, high-passed feedforward torque correlates positively with the acceleration of **+wire** at 0 ms lag. The correlation is +0.28 to +0.57 on all 5 routes.
- ⇒ The trim sees x = +wire, and the expected slope on R = −d/dt(0x18F) is **positive**. The claim's sign stands. (EVIDENCE)
- **An inverted sign would not show up as a subtle regression.** With the plant alone it is marginally unstable at 19–26 m/s (σ +0.2 to +0.4 s⁻¹ at 2.1–2.3 Hz). With the fork loop closed, the simulation runs away (wheel-rate rms 460–830 deg/s), bounded only by the 615-count clamp. The operator would feel it at once.

## EVIDENCE vs BELIEF
- **EVIDENCE:**
  - the operand algebra, pole, DC gain, settling and dither (integer, brute force, cross-checked against the golden model);
  - the chain gain (two methods);
  - the 20 Hz ratio;
  - x = 8 counts per deg/s (the record);
  - the fork's controller structure (source at `54ff1ea39`);
  - the real-data null and positive-control results;
  - the polarity leg.
- **BELIEF:**
  - J, b and k(v): the fork's fitted plant. The light world is corroborated by reproducing route 71's 2.3–2.6 Hz instability.
  - The transport delay Td from x-sample to motor torque, assumed 2–3 ms.
  - The rate-former window of 3 ms.
  - The two-mass structure.
  - The outer-loop round trip: the fork's budget of 60 ms.
  - The vehicle-model constants.
  - Every ζ×, PM and anti-damping frequency depends on these.

## Scripts
All paths below are in the scratchpad.

| script | covers |
|---|---|
| `rp1_operand.py` | claim 1 |
| `rp2_chain.py` | claim 2 |
| `rp3_wheel_mode.py`, `rp3b_diag.py`, `rp3c_speed_sweep.py` | wheel-mode ζ |
| `rp4_hf_modes.py` | 20 Hz, 180° crossing, two-mass family |
| `rp5_outer_loop.py`, `rp5b_sensitivity.py`, `rp5c_pm_at_fc.py`, `rp5d_minpm.py` | outer loop |
| `rp6_instrument.py` | closed-loop instrument simulation |
| `rp7_v293_null.py`, `rp7b_dynamic_pred.py` | real-data null, fix, polarity, positive control |
| `rp8_compare.py`, `rp8b_ladder.py`, `rp8c_ladder_outer.py` | design-script comparison and pole ladder |
| `rp9_misc.py` | inverted sign, levelled \|L\| |

Every script has a matching `*_out.txt` output file.
