# REFUTE (stability lens): design C0, the angle loop, 2026-09-30

**Status: ANALYSIS ONLY.** Nothing was built, flashed or sent, and the fork was not touched. Ghidra was not needed:
every number here comes from the lane arithmetic as already decoded (`lane_mirror_v295.lane_tick` with the C0
switches, and the cave listing in design §1.2) plus the r71b plant family.

**Author:** a refuter subagent (Opus), for the orchestrator `main`. My brief was to make C0 FAIL on loop stability
and phase.

**Design under attack:** `docs/specs/design/DESIGN-ANGLE-LOOP-C0-2026-09-30.md`, the GATE 2 section ("GATE 2: magnitude
and phase in every loop the signal is in") and its claim that GATE 2 holds on every credible member with PM ≥ 47.5° and
GM ≥ 12.6 dB.

**How to read this page.**
- Every decision-bearing claim is marked **EVIDENCE** (with its method) or **BELIEF**.
- Files are cited by heading or grep string, never by line number.
- Scripts and their outputs are in `analysis-2020accord/studies/angle_loop/refute_stability/`. The originals are in
  `_scratch/angle_loop/refute-stability/`.

---

## 0. Verdict: FAIL. Do not flash C0 as designed.

**C0 fails its own pre-registered gate H2:**

> Any credible member at any of 3/5/8/12.5/19/26/30 m/s, or at the knot midpoints, shows any of: PM < 45°.

- The credible member `J_hi` has **PM 40.7–44.3° from 10.5 to 12.0 m/s**. The minimum is **40.7° at 11.9 m/s**
  (43 km/h, an ordinary urban speed).
- Both of my methods agree, and the design's own `harness_freq` reproduces the number (§2, F1).
- The design's grid (3/5/8/12.5/19/26/30 m/s) and the H2 midpoint (10.25 m/s, which passes at 45.1°) both miss this
  trough. **The gate as written would let this build through.**

**Two further results, each sufficient on its own for "do not flash" at highway or urban speed:**
- **The damping/inertia combination the identification cannot exclude.** b ÷1.8 (the estimator's own bias
  correction) together with J 0.5 gives **PM 17.3°**, a **2.2 Hz closed-loop pole at ζ 0.13**, and |T_ref| = 3.44 in
  the 1.6–3 Hz hard-turn band. In the nonlinear simulation a 2° step overshoots by 50 %. The J-profile refits that the
  identification's own +50 % rule does not exclude at 10–15 m/s give **PM 20° (J 0.8) and 6.9° (J 1.3, ζ 0.05)** at
  11.9 m/s (F2, F3).
- **Highway stability rests on plant damping in the 3–5 Hz band, which the drive did not identify.** C0 goes unstable
  at 26–30 m/s (a 4.9 Hz pole) once the true b there falls below **0.21× the fitted value**. PM drops below 30° below
  **0.37×**, and below 45° below **0.52×**. The bias-corrected `b_lo` sits at 0.556×, just 7 % above the PM-45
  threshold (F4).

The nominal margins are real. My independent model reproduces them to 0.1° (§1). **The failure is robustness: the
margins collapse between grid points and across combinations of uncertainties the identification itself states.**

---

## 1. Method: an independent model, validated before use

### 1.1 The model

`stab_lin.py` is written from the lane semantics. It does not import `harness_freq`, `harness_time` or any `rec_*`
script; only the plant parameters (data) come from `v294_plant.family()`. Each line of the loop, in order:

| block | model |
|---|---|
| operand | θ held 100 Hz: slot 4 updates on n % 10 == 4, after the PID has read on that tick (angle trace §1.3) |
| fb FIR | r26 = 8θ[n] + 8θ[n−1] (a = 0, b = 8192, `add`) |
| error | E = 160·θ_sp − r26 (deg units) |
| cave | E′ = E·G(v)/256, with G the integer LERP exactly as tabled in design §1.2 (X 691…5990, S 249…0) |
| P | E′·450/256 |
| I | E′·199/32768/(1 − z⁻¹) |
| D | −16·ω_held |
| fade | 254/256 |
| output lag | (507/1024)(1 + z⁻¹)/(32(1 − 992/1024·z⁻¹)) |
| forward | 5346/32768 |
| transport | z⁻ᵈ, d = 2 nominal |
| plant | ZOH-discretised J s² + b s + k (rigid), or a collocated two-mass with motor-side sensing |

**Two analyses run on it:**
- **LTI fundamental.** The hold becomes (1/10)Σ_{a=1..10} z⁻ᵃ. This gives fc, PM, LTI GM and |S|.
- **Exact 10-tick periodic state space.** It gives the monodromy spectral radius, the closed-loop poles, the exact
  GM by bisection, and the delay margin in whole ticks.

### 1.2 Validation (EVIDENCE: `stab_lin.py` self-check, `xcheck_hf.py`)

| check | result |
|---|---|
| nominal PM at 3 / 12.5 / 26 m/s | 64.6 / 69.7 / 59.7°, against the design's 64.6 / 69.7 / 59.7° |
| wheel mode at 3 m/s | 0.60 Hz ζ 0.76, as in design |
| b_lo at 26 m/s | 47.7°, as in design |
| J_hi at 12.5 m/s | 47.8°, against the design's 47.7° |
| exact periodic vs LTI | they agree on stability at every point tested |
| positive control | on the 13–24 Hz two-mass stress plants, V282 is **unstable on 58/240** rows (it ground on the car). The method can return FAIL. |

**Second method on the crux.** I ran the design's own `harness_freq.metrics` (exact lifted loop) at the speeds my grid
flagged. It reproduces my numbers to ±0.1–0.3°.

---

## 2. Findings

### F1. HIGH: the GATE 2 claim is false on a credible member, and the H2 gate cannot see it

**EVIDENCE** from two methods: `stab_scan.py` §1 on a 0.5 m/s grid, and `harness_freq.metrics` on the design's own
harness (`xcheck_hf.py`). The table gives PM in degrees.

| `J_hi` (a credible member per the design's GATE 2 section) | 9.0 | 10.0 | 10.25 | 10.5 | 11.0 | 11.5 | **11.9** | 12.0 | 12.5 | 13.0 m/s |
|---|---|---|---|---|---|---|---|---|---|---|
| harness_freq PM | 49.5 | 45.8 | 45.1 | **44.3** | **42.9** | **41.6** | **40.7** | **42.0** | 47.7 | 50.0 |
| closed-loop wheel mode | 1.70 Hz ζ 0.44 | | | | | | 1.94 Hz ζ 0.36 | | 1.95 Hz ζ 0.43 | |

- **Mechanism (EVIDENCE: arithmetic).** The plant family is interpolated linearly in speed between its fit knots
  3.1 / 8.0 / 11.9 / 17.0 / 26.9 m/s, and the cave between its own knots 8 / 12.5 m/s.
  - At 11.9 m/s, `J_hi`'s b is still low (7.54) while the cave has already raised Kp_eff to 946.
  - At 12.5 m/s, b interpolates up toward 18.1 at 17 m/s, and the margin recovers.
- **The worst point is a plant knot**, and it lies in the band the identification flags as least identified ("10–15:
  every parameter ±100 % or more", `V294-PLANT-IDENT-r71b.md` §3.3).
- **The gate.** H2 checks the design speeds and the cave-knot midpoints. 10.25 m/s passes by 0.1°; 10.5–12.0 m/s is
  never sampled.
- **Fix (EVIDENCE: `stab_fix.py`).** Keeping `J_hi` at PM ≥ 45° needs G ≤ 460–484 (Kp_eff ≤ 809–851) over
  10.5–11.9 m/s. C0 has 467–538 there.
- **Gate fix.** H2 must sweep speed finely (≤ 0.25 m/s), and must include the plant knots 3.1 / 8.0 / 11.9 / 17.0 /
  26.9 m/s.

### F2. HIGH: at 10–16 m/s, inertia the identification does not exclude puts PM below 30°

- **EVIDENCE (the identification).** The J profile at 10–15 m/s costs 0.814 / 0.831 / 0.834 / 0.880 / 0.935 / 0.986
  for J = 0.1 / 0.2 / 0.3 / 0.5 / 0.8 / 1.3 (`V294-PLANT-IDENT-r71b.md`, "The J profile").
  - J = 1.3 is therefore only +21 % above the best.
  - The same report's exclusion standard is "0.5+ is excluded, at +50 % or more cost", applied at 0–5 m/s. **By that
    standard nothing up to J = 1.3 is excluded at 10–15 m/s.**
  - At 15–22 m/s the profile is flat (+4.5 % at J 1.3).
- **EVIDENCE (model).** The self-consistent J-profile refits (b and k refitted at each fixed J, from `p5c.json`),
  under C0 (`stab_jrows.py`):

| refit | 10 | 11 | **11.9** | 12.5 | 14 | 16 | 19 m/s |
|---|---|---|---|---|---|---|---|
| J 0.8 (= `J_hi2`) | 33.2° | 26.0° | **20.2° (1.7 Hz ζ 0.16)** | 27.7° | 36.4° | 45.1° | 44.5° |
| J 1.3 | 26.6° | 15.7° | **6.9° (1.4 Hz ζ 0.05)** | 13.2° | 20.9° | 29.2° | 33.0° |

- **EVIDENCE.** `ms_free`, the free-J fit itself (J 2.08 at 11.9 m/s), is **unstable at 11.5–12.0 m/s** (min PM −3.4°).
- **BELIEF (the design's, not refuted but not evidence).** J is speed-independent hardware, so 0.2 holds at every speed.
  - The identification itself labels this a BELIEF: "J is physically a property of the steering hardware. BELIEF: it is
    speed-independent".
  - It also says the large b at speed is "the vehicle's lateral dynamics acting through the aligning torque, lumped
    into b". **A lumped fit that absorbs vehicle dynamics into b can absorb them into J as well.**
- **What would settle it.** A plant FRF at 1–3 Hz at 10–20 m/s. The r71b drive could not provide one: "Above 10 m/s
  the rate detail is not reproduced (rate R² 0.01–0.10 on 1 s windows)".

### F3. HIGH: two stated uncertainties combined give a 2.2 Hz ring in the hard-turn band

**The design's credible set varies one parameter at a time.** Two uncertainties the identification states separately:
- **b ÷1.8 at ≥ 10 m/s.** This is not a pessimistic corner. It is the estimator's own bias correction: G3a, "b ×1.7–1.9"
  high, "the `b_lo` corner carries that bias correction".
- **J = 0.5.** This is a credible corner.

Combined, under C0 (EVIDENCE: `stab_scan.py` §2, confirmed by `harness_freq` in `xcheck_hf.py`):

| v (m/s) | 10 | 11 | 11.5 | 12 | 13 | 15 | 19 | 22 |
|---|---|---|---|---|---|---|---|---|
| PM | 21.3° | 18.6° | **17.3°** | **17.3°** | 23.0° | 28.3° | 27.5° | 29.8° |
| closed-loop pole | 2.07 Hz ζ 0.16 | 2.15 Hz ζ 0.14 | **2.19 Hz ζ 0.13** | 2.23 Hz ζ 0.13 | 2.41 Hz ζ 0.16 | 2.79 Hz ζ 0.18 | 3.20 Hz ζ 0.18 | 3.17 Hz ζ 0.21 |
| \|T_ref\| max in 1.6–3 Hz | 2.78 | 3.20 | **3.44** | 3.44 | 2.63 | 2.21 | 2.28 | 2.11 |

- **The pattern.** PM is < 30° from 10 to 22 m/s, and < 45° at every speed from 1 to 35 m/s. The exact GM is still
  10.0–10.6 dB, so this is a **ring, not a divergence**.
- **Variants:**
  - b ÷1.9 with J_hi: 15.6°.
  - Adding tau6 (b_lo × J_hi × tau6): 14.4°.
  - b ÷1.8 with J 0.3 (inside J's preferred range at 10–15 m/s): 37.3–38.3° at 10 m/s, < 45° from 10 to 35 m/s.
- **EVIDENCE (independent nonlinear simulation, `stab_nl.py`).** The simulation includes friction (Karnopp, the
  member's own Fc/Fs), 0.1° angle quantisation, the integer lane and the cave. A 2° setpoint step at 11.9 m/s gives:

| plant | overshoot | T rms in 1.6–3 Hz |
|---|---|---|
| nominal | 0.18° | 8.5 |
| J_hi | 0.58° | 14.0 |
| J_hi × b/1.8 | **1.01° (50 %), 3 error zero-crossings** | 17.9 |

- **On the car,** this is the operator's "jerk in hard turns" (R9) and a rise in the goal's hard-turn 1.6–3 Hz energy.
  That is BELIEF on the symptom mapping; the arithmetic above is EVIDENCE.

### F4. HIGH (EVIDENCE model, BELIEF physics): highway stability depends on 3–5 Hz damping that was never identified

**EVIDENCE: thresholds** (`stab_scan.py` §3, `stab_fix.py`). The b-scale (J 0.2, nominal k) at which C0 crosses each
margin:

| v | instability (PM 0) | PM 30 | PM 45 |
|---|---|---|---|
| 26 m/s | **0.207× (b 5.36)** | 0.368× (9.52) | 0.515× (13.3) |
| 19 m/s | 0.196× (4.29) | 0.340× | 0.449× |
| 12.5 m/s | 0.134× | 0.314× | 0.423× |

- **`b_lo` = 0.556× sits 7 % above the PM-45 threshold at 26 m/s.**
- **Lowering the highway gain buys margin.** At Kp_eff 2000, PM 30 needs only b ≥ 6.3 (0.24×). At 2500 it needs
  b ≥ 7.9.

**EVIDENCE: nonlinear simulation** (`stab_nl.py`, `stab_nl2.py`). Inputs: 15-count white road torque (the
identification's own G3a control level) plus a ±0.5° 0.2 Hz lane-keeping setpoint. Wheel-rate rms in 3–6 Hz:

| v | nominal b | b 7 | b 5 |
|---|---|---|---|
| 26 m/s | 0.23 deg/s | 0.79 | **1.96** |
| 30 m/s | 0.23 deg/s | 0.77 | **2.23** |

- From a 0.3° step at 30 m/s with b 5, a **sustained 4–6 Hz limit cycle** forms: 0.69° peak-to-peak, |T| peak 91.
- At 26 m/s with b 5, friction (Fs 6 T) quenches the linear instability after a small step. It does not quench it
  under road noise.

**Why the 3–5 Hz damping is unidentified (EVIDENCE: `V294-PLANT-IDENT-r71b.md`):**
- "Above 10 m/s the rate detail is not reproduced (rate R² 0.01–0.10 on 1 s windows)".
- F4 fires at 10–15 m/s.
- FD coherence z–ω is "0.1–0.5 above 1 Hz in cruise, and the fits degenerate".
- The b estimator is biased ×1.7–1.9 high in its own control.

**Why it may be lower than fitted (BELIEF on the physics).** The identification itself attributes the large b at speed
to lumped vehicle lateral dynamics. If that damping comes from yaw and tire lag, it is frequency-dependent and need not
act at 3–5 Hz. The underlying b at 0–8 m/s is about 5.

**The other side, stated fairly.**
- The measured torque-mode lateral actuator lag (0.15–0.34 s, memory `accord-lateral-actuator-delay-is-speed-dependent…`)
  is consistent with a heavily damped plant **at 0.3–1 Hz**. It says nothing about 3–5 Hz.
- The prior `light_b` world (b 1.58) is already unstable under C0, as the design reports. The design treats that as
  "the prior" and adds REVERT R3.

**C0 is the first build whose highway stability depends on this number.** On the same b = 5 plants, V294 and V295 are
stable (EVIDENCE: `stab_more.py` §3). Their rate operand injects damping instead of stiffness. **Nothing flown to date
measures the plant at 3–5 Hz above 10 m/s, so R3 would be the first measurement, made as a growing oscillation at
highway speed.**

### F5. MEDIUM: the 20 Hz-only metric hides a 5–17 Hz damping regression at highway

**EVIDENCE** (`stab_hf.py` §A). Torque per unit wheel rate, real part, in T counts per deg/s, with the hold included
and d = 2. Positive damps; negative anti-damps.

| | 7 Hz | 10 Hz | 13 Hz | 16 Hz | 20 Hz |
|---|---|---|---|---|---|
| V294 (flew, no grind) | +0.82 | +0.23 | −0.08 | −0.24 | −0.34 |
| V295 | +1.51 | +0.42 | −0.15 | −0.45 | −0.63 |
| V282 (ground at 20 Hz) | +12.6 | +5.05 | −0.05 | −3.53 | −6.39 |
| **C0 @ 26–30 m/s** | **−3.48** | **−2.12** | **−1.45** | −1.06 | −0.76 |
| C0 @ 19 m/s | −2.82 | −1.77 | −1.24 | −0.94 | −0.70 |

- **At 13 Hz, C0 at highway removes about 10× the damping V295 removes**, and more than V282 does there.
- 13 Hz is where the identification sees an ω→bar peak (12–14 Hz, "BELIEF: a lightly damped torsion-bar /
  steering-wheel resonance near 13 Hz"), and where the record has a pre-existing 13–17 Hz line (V289's ring moved to
  15–17 Hz).
- The design's metrics M20 and L20 are evaluated at 20 Hz only, where C0 does look better.

**On the two-mass stress plants:**
- Hands-off, fz 10–20 Hz, r2 0.1–0.5, ζ_w 0.01–0.05: **0/240 unstable** for C0. But C0's least-damped pole is less
  damped than V295's on **171/240** rows (`stab_hf.py` §B).
- Hands-on (arms ×1–5 the wheel inertia, ζ_arm 0.02–0.2): **0/288 unstable** (§C).
- **Caveat.** These stress plants put the lumped b (20–26 at speed) on the motor side, which damps the mode. With
  b = 5 there, the dominant failure is the rigid 4.9 Hz pole of F4, not the flexible mode.
- **Gate fix.** GATE 2 should report Re(T/ω) across 5–25 Hz against V294/V295, not |·| at 20 Hz alone.

### F6. LOW–MEDIUM: the fork outer loop (stand-in, BELIEF on the fork)

**EVIDENCE** (`stab_more.py` §2). L_o = T_ref·e^(−0.06 s)/(τ_o s):

| τ_o | margins |
|---|---|
| 0.3 s | **GM 1.7–1.9 dB** on J_hi and b_lo×J_hi at 3 m/s; 3.9 dB on b_lo×J_hi at 12 m/s (where \|T_ref\| peaks at 3.43) |
| 0.5 s | GM 6.1–6.3 dB on the same members |
| 1.0 s | GM ≥ 12.2 dB everywhere tested |

- The design's rule ("none faster than τ_o = 1 s") is right. **It is binding, not conservative, on the corners.**
- This finding does not refute C0. It makes the fork rule a hard prerequisite.

### F7. LOW: lateness of slot 4 (BELIEF on the bound)

**EVIDENCE** (`stab_scan.py` §4). Running slot 4 late by 10 whole ticks costs 5–10° of PM. On b_lo at 26–30 m/s that
takes PM to 37.3–37.6°. The angle trace bounds the age at 1–10 ms only under the BELIEF that slot 4 completes before the next tick.

---

## 3. What survived the attack (EVIDENCE, same scripts)

- **The modelling is correct.** The nominal-plant margins and wheel modes reproduce to 0.1°.
  - The 100 Hz hold, the 2-tap FIR, the 5.05 Hz output lag and the D on the held rate are modelled correctly in the
    design's harness. My exact periodic model agrees with the LTI fundamental.
  - The rate-former phase (D) is validated to 5 Hz by the identification's G2 (≤ 1.7°). Adding 1.5 ms to the rate
    former changes Re(T/ω) by ≤ 0.1.
- **Exact GM ≥ 12.9 dB** on nominal, b_lo, J_hi and tau6 at the knots and the cave-knot midpoints. The failure mode is
  phase, not gain.
- **The 20 Hz object:**
  - C0 reduces |T/ω| at 20 Hz below V295's.
  - 0/240 hands-off and 0/288 hands-on two-mass rows are unstable, against V282's 58/240.
  - There is no grind risk of V282's kind.
- **The outer loop at τ_o ≥ 1 s** has GM ≥ 12 dB on every member tested.
- **Delay margin** at 26 m/s is ≥ 46 ms on b_lo and > 80 ms on nominal and J_hi.

## 4. What I could not check

- Anything above about 8 Hz is model, not measurement (identification §4). The two-mass parameters are stress cases.
- Hands-on is modelled with generic arm parameters (BELIEF). There is no N·m scale for T counts.
- Friction and stiction at 0–5 m/s (the design's pre-declared miss) were not re-scored here. My lens is linear and ring
  stability.
- The real StarPilot outer loop is not modelled (it is BELIEF in the design too).

## 5. What would turn this FAIL into a PASS (for the designer; not run here)

1. **Clip the cave gain over 9–12.5 m/s.** G ≤ about 460 (Kp_eff ≤ 810) keeps `J_hi` ≥ 45°. A b_lo×J_hi PM ≥ 30° needs
   G ≤ about 380 (Kp_eff ≤ 670).
   - Re-check tracking at 12.5 m/s after the change.
   - Then re-run GATE 2 on a ≤ 0.25 m/s grid that includes 3.1 / 8.0 / 11.9 / 17.0 / 26.9 m/s, with the
     two-uncertainty combinations (b/1.8 × J 0.3–0.5, × tau6) in the credible set.
2. **Highway:** either
   - (a) measure the plant's 1–5 Hz FRF above 10 m/s before flight, for example by a dedicated excitation drive on
     V295 (fork-side), or
   - (b) cap Kp_eff so PM ≥ 30° holds down to b ≈ 0.25× fitted (Kp_eff ≈ 2000), and accept the tracking cost against
     the goal's 0.95 floor.

   Pre-register **R3 as a stop condition at 3.5–5.5 Hz at ≥ 12.5 m/s from the first highway minute**, not as a
   post-hoc revert.
3. **Add Re(T/ω) at 5–25 Hz vs V294/V295 to GATE 2** (F5).
