# ADV-stability: adversary "stability" against the dynamics lens's A1017 (0xC63E8 1011 -> 1017)

Subagent `adv-stability`, 2026-09-30. **Design review only.** Nothing was built, flashed or sent, and no CAN traffic was
generated. The fork, `../accord-firmwares`, STATE, memory, lineage and the golden model were not touched, and nothing was
committed. Every decision-bearing claim is marked **[E]** EVIDENCE (with its method) or **[B]** BELIEF. The operator scores
symptoms; everything here is a transfer function, an eigenvalue or a simulation.

- FAIL criteria, written before any number of mine: `ADV-stability-CRITERIA.md`.
- Scripts and outputs: `adv_stability/` (listed in section 9).

---

## 0. Verdict

**REFUTED as pre-registered, on criterion F-e only: the design's direction claim does not hold on every member.**

- **Stability: A1017 survives every stability attack.** That covers the inner loop, the 20 Hz question, the outer loop with
  the unchanged fork law, and the nonlinear traps (F-a, F-b, F-c, F-d). I could not make it unstable, less damped in a
  meaningful way, or louder above 8 Hz on any plant, delay, J or b corner I tried.
- **What fails is the claim itself.** The design says A1017 moves the jerk band the right way, or within +/-4 %, "on every
  plant member under both disturbance models". On the J-heavy side of the family, under the plant-alone model (`lp`), the
  hard-turn 1.6-3 Hz band at 5-10 m/s rises:
  - my J-0.5 corner (nominal b/k/F, J 0.5, not refitted): x1.06-1.07, robust over 4 of 4 runs;
  - the harness's own refitted J_hi2 and my light_b J x2.5 corner: x1.02-1.05.
- Two cautions on how much that failure weighs:
  - It uses the designer's own method and metric, and that metric is NOT FIT in the harness.
  - My second method (synthetic hard turns in my own engine) does **not** reproduce it: those members read pooled medians of
    x0.98-0.99, with per-cell medians of x0.89-1.07.
- **So the sign of A1017's effect on "jerky on hard turns at medium speed" is not robust across J.** The plant study itself
  puts J at 5-10 m/s at "best 0.5, flat 0.1-1.3". The adverse corners are about as large as the claimed benefit (x0.94-0.98).
- **If the orchestrator judges my non-refitted J corner out of scope, the correct verdict is SURVIVES_WITH_CHANGES.** The
  required changes are in section 8. Every one of them is to the page, not to the lever.

**Two more pre-registered clauses fired as written. I adjudicate both, and neither is a real failure:**
- **F-c, Ms clause (5 cells).** In all 5 the V294 loop is itself linearly unstable (GM 0.62-0.80), and A1017 raises GM in
  every one. Ms is not a margin for a loop that encircles -1.
- **F-b (2 cells).** My mode selector picked the wrong pair. With a robust selector the ratio minimum is 0.979.

**Things the design page does not say and must:**
1. Under driver torque, A1017 pushes back harder on the driver. On r71b's own hands-on frames the trim torque rises x1.44 in
   rms and x1.47 at p99. That is after the firmware's own taper on driver torque.
2. On a hard turn-in, the 1.6-3 Hz motion moves in time, from the ramp into the 1-4 s settle that follows it.
3. The design says the trim is "not anti-damping" at 25 Hz. That is true only at zero extra delay. With the plant's 2 ms, both
   builds are anti-damping at 17-25 Hz. A1017's increment is 0.1-0.4 % of V282's size.

---

## 1. Central numbers: reproduced exactly, by two methods [E]

Method 1 is my own z-domain lane (`advlin.LaneLin`), written from the census listing, with the 3 ms rate former.
Method 2 is time-domain: a sampled sine wheel angle goes through my integer rate former (round) into my own **integer** lane
(`s0 MyLane`), and the gain and phase are least-squares fitted. `s1_central_out.txt`.

| quantity | design | method 1 | method 2 | result |
|---|---|---|---|---|
| damping part at 2 / 2.5 / 3 / 5 Hz, V294 (T per deg/s) | 1.61 / 1.83 / 1.91 / 1.60 | 1.611 / 1.826 / 1.906 / 1.595 | 1.611 / 1.826 / 1.906 / 1.595 | exact |
| same, A1017 | 2.17 / 2.19 / 2.11 / 1.52 | 2.169 / 2.189 / 2.109 / 1.518 | 2.168 / 2.189 / 2.109 / 1.517 | exact |
| damping peak | 3.15 -> 2.32 Hz | 1.910 at 3.15 Hz -> 2.197 at 2.32 Hz | - | exact |
| \|T/x\| A1017 / V294 at 9 / 13 / 17 / 20 / 25 / 30 Hz | 1.01 / 1.01 / - / 1.00 / 1.00 / 1.00 | 1.0147 / 1.0056 / 1.0021 / 1.0007 / 0.9994 / 0.9987 | - | exact |
| \|P/x\| at 20 Hz: V294 / A1017 / V282 | 2.079 / 2.080 / 44.90 | 2.079 / 2.080 / 44.900 | - | exact |
| K_alpha (T per deg/s^2); pole | 0.210 -> 0.390; 2.03 -> 1.09 Hz | 0.2097 -> 0.3895; 2.033 -> 1.092 Hz | - | exact |
| int32 worst a*s margin at \|x\| = 12000 | 4.06 -> 2.17 | 4.058 -> 2.172 (arithmetic) | integer march at x = +12000: 4.059 -> 2.173 | exact |
| b_max(1017); fb clamp binds at | 1232; 2935 -> 1580 deg/s^2 | 1231.8; 2935 -> 1580 | - | exact |

**Spot checks required by the brief [E]:**
- **The lane.** My lane matches the golden model (`lkas_fb_lag` + `lkas_rate_pid_tick`) with 0 mismatches over 48,000 ticks
  at 1011 and 48,000 at 1017, on T and r26. The harness `Lane` also matches the golden model on the same ticks, with 0
  mismatches, including C-clamp binds (2,979 and 7,738) and \|x\| up to 12000. `s0`.
- **The cells.** Every cell was read by address from the V294 image (sha checked). The candidate bytes are `F3 03 -> F9 03`
  (1017). `s0`.
- **One retrodiction row.** V294, nominal, `lp`, tracking gain by band 0.840 / 0.865 / 0.586 / 0.764 / 0.917. This is
  identical to V295-HARNESS section 6: PASS. `s5`.

**C4, the nonlinear byte-exact replay of all of r71b [E]** (`s6`, my lane):
- It is bit-exact to plib's march on all 1,020,390 ticks, live and null. That march fits the 427 tap to 3.64 counts.
- Max \|r26\|: 637 -> 790.
- fb-clamp binds: 0 -> 0.
- P binds while engaged: 458 -> 344.
- Max a*s margin: 17.79 -> 10.35.

---

## 2. (a) The inner acceleration loop: SURVIVES [E model, B car]

**Method.** I used my own exact-ZOH discretisation (matrix exponential), not the harness's semi-implicit Euler. Each cell is
solved two ways: as one closed-loop state matrix (eigenvalues), and as a Nyquist of my return ratio (GM, PM, Ms).
- **Cross-check against the harness `loop_frf`** (nominal, 12 m/s). \|L\| agrees to 4 digits at 1-20 Hz. The closed-loop pair
  is 3.93 Hz, zeta 0.856, against the harness's 3.91 Hz, 0.861.
- **Grid: 2,520 cells.** Nine rigid members: nominal, J_lo, J_hi, J_hi2, J_0.3, b_lo, b_hi, ms_free, light_b. Crossed with
  5 speeds, delay tau {0, 2, 3, 4, 6, 9, 12} ms (x1 to x3 of the ~4 ms measured), J x {0.5, 1, 1.5, 2.5} and b x {0.5, 1}.
  `s2_inner_grid_out.txt`.

| F-a clause | result |
|---|---|
| A1017 unstable where V294 is stable | **0 cells** (V294 unstable: 0) |
| A1017 GM < 3 or PM < 30 deg where V294 GM >= 6 | **0 cells** |
| a pair below 8 Hz with zeta_A < 0.3 and < 0.9 zeta_V | **0 of 2,520** |

**Worst corners, V294 -> A1017.**
- Minimum GM per member:
  - nominal 6.52 -> 5.96;
  - J_lo 4.59 -> 4.29;
  - b_lo 5.72 -> 5.16;
  - light_b 4.65 -> 4.08.
- All four minima sit at J x0.5, b x0.5 with a 12 ms delay, for V294 and A1017 alike.
- Over the grid, the GM ratio A1017/V294 runs from 0.855 to 1.002 (median 0.904). At nominal delay GM falls 6-12 %: for
  example, nominal at 3.1 m/s goes 42.2 -> 38.9.
- Ms rises by <= 0.04 at nominal delay, J and b, and by at most 0.13 anywhere on the grid (a light_b corner, 1.46 -> 1.59).

**Minimum zeta of the pair below 8 Hz rises on the lightly damped members:**
- light_b 0.184 -> 0.260;
- J_hi2 0.236 -> 0.258;
- ms_free 0.111 -> 0.119.

**How zeta_lo changes across all cells:**
- The median change is +0.007 and p5 is -0.044.
- zeta_lo is lower on 31 % of cells. The largest "drops" are mode switching: for example, at J x0.5 with 12 ms, J_lo's least
  damped pair becomes a 7.8 Hz pair at zeta 0.46.

**The ceiling this implies [E model].** A1017 costs 0-15 % of inner GM, and every case is still >= 4. The trim loop
is weak on the identified family (\|L\| 1-3 Hz 0.05-0.4), so there is nothing near a boundary.

---

## 3. (b) The 20 Hz question: SURVIVES, with one wording correction [E model, B car]

**Gain [E].** A1017 sits at \|P/x\|(20 Hz) = 2.080, against V294's 2.079 and V282's 44.90. \|T/x\| at 13-30 Hz is x0.999-1.006
of V294; V294 is 4.3-5.1 % of V282. So A1017 is 0.046 x V282 at 20 Hz.

**Phase and the sign of damping under delay [E, `s1` (b1)].** Damping part in T per deg/s; + means damping.

| added delay | V294 at 13 / 17 / 20 / 25 Hz | A1017 | A1017 - V294 as % of V282's \|T/w\| (18.6 / 15.7 / 14.0 / 11.8) |
|---|---|---|---|
| 0 ms | 0.375 / 0.185 / 0.103 / 0.023 | 0.313 / 0.145 / 0.073 / 0.004 | -0.33 / -0.26 / -0.21 / -0.17 % |
| +2 ms (the plant's transport) | 0.227 / 0.025 / **-0.059 / -0.139** | 0.161 / -0.016 / **-0.089 / -0.158** | -0.35 / -0.26 / -0.22 / -0.16 % |
| +6 ms | -0.083 / -0.289 / -0.363 / -0.409 | -0.152 / -0.328 / -0.388 / -0.421 | -0.37 / -0.24 / -0.18 / -0.10 % |

What the table shows:
- **The sign does not survive the delay for EITHER build.** With the plant's own 2 ms of transport, V294 and A1017 are both
  mildly anti-damping at 20-25 Hz. With 6 ms they are anti-damping from 13 Hz up.
- The design's section 4.2 line, "at 25 Hz ... still not anti-damping", is true only at zero added delay.
- A1017 adds 0.02-0.07 T per deg/s of anti-damping at 13-20 Hz. That is **0.1-0.4 % of V282's reaction** at the same
  frequency, far below F-b's 5 % anchor.

**Closed-loop stress modes [E model]** (`s3`, `s3b`). The grid is 300 cells:
- 10 two-mass modes: the harness's mode13, mode20 and mode20_lo, plus 16 Hz zeta 0.02, 25 Hz zeta 0.03, r2 0.2-0.8 and others;
- collocated sensing (the physical case) **and** non-collocated sensing;
- 5, 12 and 25 m/s;
- delay 2 to 12 ms.

Results:
- **The least-damped pair in 5-45 Hz, A1017/V294:** minimum 0.979, median 1.002, maximum 1.044. A1017 is unstable on 0 cells.
- The worst case is m13z05r5 at 12 m/s with 12 ms: 0.327 -> 0.320.
- **Cross-check against the harness `stress_damping`.** mode20 at 5 m/s: mine 0.0753, the harness's 0.0764. Every harness
  member agrees within 0.004.
- **Sanity: the model has teeth.** V282 in the same model is unstable on 193 of 300 cells. On the collocated mode20 at
  5 m/s, V282 takes zeta from 0.0746 (open) to 0.007 at 6 ms and to -0.005 at 9 ms. That is consistent with the on-car
  zeta 0.016. V294 and A1017 leave the same mode at 0.075.
- **The two F-b flags were artefacts.** On m20z05r8 the structural pair moves below 8 Hz, and both builds are at zeta 0.5-0.9.

---

## 4. (c) The outer loop with the unchanged fork law: SURVIVES [E model, B world]

### 4.1 Linear analysis

**Method.** I wrote my own outer return ratio from the fork port's r1 arithmetic:
- the lsf factor, the PI, the SteerFriction saturation slope, 1/LAF, x4096;
- a 100 Hz ZOH plus the pipe;
- the FF path at 1 kHz;
- my plant with the inner loop closed;
- the fork reading the wheel-side angle.

**Cross-check against the harness `outer_frf` [E]:**

| member | build | mine: Ms / GM / PM | harness: Ms / GM / PM |
|---|---|---|---|
| nominal, 8 m/s | V294 | 1.185 / 10.37 / 145.1 | 1.185 / 10.41 / 145.3 |
| light_b, 26.9 m/s | V294 | 3.091 / 1.68 / 30.7 | 3.066 / 1.69 / 31.1 |
| light_b, 26.9 m/s | A1017 | 2.450 / 1.86 / 48.5 | 2.440 / 1.87 / 48.9 |

**Grid: 4,032 cells** (`s4_outer_out.txt`):
- 12 members, including the stress modes;
- speeds 3.1-26.9 m/s;
- J x {0.5, 1, 1.5, 2.5};
- inner delay 2 / 6 / 12 ms;
- pipe 22 / 44 ms;
- steer ratio 16.84 (centre) and 13.5 (hard-turn angles).

Each cell is also swept over the SteerFriction slope fraction {0, 0.25, 0.5, 0.75, 1}. That sweep is the describing-function
test: the friction term is a saturation whose describing function spans (0, 1] of its small-signal slope.

| F-c clause | result |
|---|---|
| GM_A < 0.9 GM_V | **0 cells**. GM ratio (minimum over the describing-function sweep): min **1.003**, median 1.048, max 1.457. **A1017 never lowers the outer GM.** |
| Ms_A > 1.1 Ms_V | **5 cells: fired as written.** All 5 are light_b cells with a 44 ms pipe and J x1.5-2.5 at 22-27 m/s, where V294 itself is linearly unstable (GM 0.62-0.80) and A1017's GM is higher (0.80-1.01). Ms is not a margin there. The Ms ratio median is 0.982 and p95 0.997 |
| a describing-function crossing (GM < 1 at some friction fraction) for A1017 only | **0 cells** |

**Low-speed-factor region [E model].**
- Nominal at 3.1 m/s: PM 87.8 -> 85.3 deg (-2.5 deg), GM 11.04 -> 11.79.
- light_b at 3.1 m/s: PM 41.9 -> 51.5 deg, GM 4.47 -> 5.42.
- **This is the only place any margin moves the wrong way: identified members lose 2-4 deg of PM at 3-5 m/s.** The lowest
  PM is still 74.8 deg (b_lo at 3.1 m/s, unchanged).

**BELIEF world.** V294 is itself linearly unstable in 29 light_b pipe-44 ms corners. That is the prior's pessimistic corner,
and it is not the car the operator drove.

### 4.2 Nonlinear closed loop

**Method.** My integer lane, my own plant integrator (0.2 ms sub-stepped Karnopp stick-slip with a saturating spring), my
census demand chain, the Honda limiter, and the harness ForkPort, which is gated bit-identical to the real fork.
- Paired inputs and noise.
- 18 scenarios on 8 members (`s7`), and the same over 6 seeds (`s8`, `s9`):
  - hard turns at 8 / 12 / 16 / 20 m/s, 1.5 and 3 m/s^2;
  - on-centre with 25 T of crown plus 10 T of 0.2-3 Hz road torque, at 3.1 to 27 m/s;
  - slaloms at 0.3-1 Hz.

**Hard-turn 1.6-3 Hz** on the harness-style mask (frames with \|plan\| >= 1.5), per-member median of A1017/V294:

| member | median |
|---|---|
| nominal | 0.985 |
| J_lo | 0.976 |
| J_hi2 | 0.988 |
| b_lo | 0.968 |
| F_hi | 0.983 |
| light_b | 0.909 |
| light_b J x2.5 | 0.959 |
| light_b b x0.5 | 0.843 |

This is favourable on every member. [E sim]

**It is not uniform in time [E sim]:**
- The ramps mostly fall: median x0.96, range x0.69-1.20 over 64 cells (`s7`).
- The **1-4 s settle after a hard turn-in rises** on many cells, for example:
  - nominal, 8 m/s, 3 m/s^2: x1.16 [1.12, 1.28];
  - F_hi, same turn: x1.17;
  - light_b, 12 m/s, 3 m/s^2: x1.56;
  - b_lo, 12 m/s, 3 m/s^2: x1.99 [1.31, 2.58].
- The late hold falls.
- Lateral-acceleration overshoot on light_b-world members rises by 1-3 points (for example 0.165 -> 0.188).

**On-centre hunting, over 6 seeds [E sim]:**
- 0.3-5 Hz rate median ratio: 0.93-1.00 on every member and speed.
- Single-seed flips happen in both directions (maximum x1.22, lb_b0.5x at 17 m/s). They are chaotic, not systematic.

**Limit cycles after the turn [E sim].** A sustained 0.5-5 Hz post-turn oscillation (0.4-1.4 Hz stick-slip hunting):

| | cells, of 384 |
|---|---|
| V294 | 209 |
| A1017 | 202 |
| V294 only | 26 |
| A1017 only | 19 |

**A1017 creates no new limit cycle.** It flips bistable light_b cells both ways.

**Slaloms [E sim].**
- Identified members: gain and phase are unchanged within 1-9 %.
- light_b world: gain is closer to 1 at 0.6 Hz, and the 1.6-3 Hz rate falls x0.67-0.85.
- On lb_J2.5x at 12 m/s, 1 Hz, gain 1.46 -> 0.97. V294 resonates there and A1017 damps it.

---

## 5. (d) Nonlinear traps: SURVIVES, with one undisclosed feel cost

| trap | result |
|---|---|
| int32 | worst case 2.17 at the \|x\| = 12000 bail edge (integer march); 10.35 on r71b. Nothing wraps within the reachable x. [E] |
| fb clamp C | 0 binds on r71b (max 790 of 1024). It binds at 1580 deg/s^2 below the pole. [E] |
| P clamp | engaged binds 458 -> 344 on r71b. [E] |
| restart pulse, my integer lane | 14 / 43 / 144 / 419 -> **17 / 52 / 174 / 503 T** at 10 / 30 / 100 / 300 deg/s, and above 50 T for 0 / 0 / 159 / 252 -> **0 / 31 / 269 / 433 ms**. That matches the design exactly and stays below the 616 T cap. [E] |
| 100 Hz staircase | The FF path is byte-identical. The trim's \|T/x\| at 40 / 50 / 100 / 200 Hz is x0.998 / 0.998 / 0.997 / 0.997. Nothing is added there. [E arithmetic; `s13`] |
| friction stick-slip, noise-free on-centre | mean dwell-then-jump amplitude 0.177 -> 0.163 deg; peak alpha median ratio 0.999-1.000. [E sim] |
| **driver torque (hands-on, engaged), r71b's own 91 s** | trim torque after the firmware's own driver-torque taper: **rms 38.9 -> 56.0 T (x1.44), p99 166 -> 244 T, max 309 -> 429 T**. On 80-84 % of ticks with \|alpha\| > 300 deg/s^2 the trim opposes the driver's acceleration. [E replay, `s6`] |
| synthetic fast driver steer, 0 -> 90 deg in 0.3 s | peak 528 -> 607 T at taper 254, and 159 -> 182 T at taper 76. Impulse x1.41. **fb clamp binds 10 -> 223 ticks.** Below the 616 T cap: the arithmetic holds. [E] |
| 3-8 Hz | The trim is x1.02-1.05 larger at 5-8 Hz and 7-10 deg more spring-like. Its damping part at 7 Hz falls 10 %. The 3-8 Hz wheel rate rises: up to x1.08 under `lp` on identified members, and x1.11-1.13 on the light_b-world members at 0-5 m/s under `full`. The inner pair at 3.8-4.2 Hz changes zeta by <= 0.01. [E model / sim] Its relation to the record's 7 Hz stutter is BELIEF: that was a rate-servo loop cycle, absent in torque mode. |

**The driver-torque row is the one risk the design does not state.** It frames the added inertia only as "slower / heavier in
quick transitions" of the LKAS-commanded motion. The same trim opposes the **driver's** wheel acceleration, at x1.44 the
torque, until the taper cuts it at \|bar>>5\| >= 48 / 64. [B: the feel]

---

## 6. (e) Does it move the complaints across the family? Only partly

**Full-family sweep** (`s5`). The harness engine, 23 members: all 18 harness members plus my corners light_b J x0.5 and x2.5,
light_b b x0.5, light_b with a 6 ms delay, and nominal with J 0.5 not refitted. Candidate and V294 run in one batch, under
both `full` and `lp`.
- **`full` (the counterfactual on r71b's road): hard-turn 1.6-3 Hz <= x1.010 on every member and band.** Favourable or
  neutral everywhere. Tracking gain changes by <= 0.0044 and turn-hold by <= 0.016. [E sim]
- **`lp` (the loop's own behaviour).** Paired, from s10: noise-free run [3 noise seeds].

| member | 5-10 m/s | 15-22 m/s | 22+ m/s |
|---|---|---|---|
| nominal | 0.994 [1.00, 1.00, 1.00] | 0.99 [0.91-1.02] | 0.99 [0.96-1.07] |
| J_hi2 (refitted J 0.8) | **1.025 [1.030, 1.021, 1.039]** | 0.99 [0.95-1.06] | 1.00 [0.98-1.04] |
| **nom_J0.5nr (J 0.5, not refitted)** | **1.063 [1.060, 1.064, 1.071]: F-e FIRES** | 0.96 [0.93-1.07] | 0.99 [0.94-0.99] |
| lb_J2.5x | **1.050 [1.034, 1.041, 1.041]** | 1.03 [1.01-1.03] | **1.08 [1.05-1.09]** (s5: 1.113) |
| light_b | 0.896 | 0.855 | 0.874 |
| b_hi (s5 single seed 1.055) | 0.99 | 1.005 [0.98, 1.00, 1.12]: **noise** | 0.99 |

- **J_hi** (refitted J 0.5) reads x1.023 at 5-10 in s5 (single seed).
- **The sign of the 5-10 m/s effect follows J:**
  - J <= 0.3 or light damping: x0.89-0.99;
  - J >= 0.5: x1.02-1.07.
- **r_mid (1-3 Hz) stays favourable or neutral everywhere** (x0.51-1.006 over all 23 members, both disturbance models). The
  adverse sign is specific to the hard-turn mask.
- **Second method** (`s12`: my engine, synthetic hard turns) on the same heavy-J members gives pooled medians:
  - nom_J0.5nr 0.990;
  - J_hi 0.976;
  - J_hi2 0.988, but +7.4 % in the 12 m/s, 3 m/s^2 cell.

  **The two methods disagree on the sign for heavy J.** I cannot say which scenario the car's roads resemble. [B]
- **The literal goal metric** (`s11`: closed-form alpha per 0xE4 count, my model). At 1 Hz, worst over speed and J:
  - identified members **x0.852-0.953** (b_lo at J x0.5 is the worst);
  - light_b **x0.76**.

  F-e's thresholds (0.85 and 0.75) are not crossed. The design's "2-13 % less" should read "up to 15 %".
- **The other two complaints.** Tracking gain and turn-hold stay within +/-0.004 and +/-0.016 on all 23 members. "Loose" and
  "understeer" are not reached, as the design says. [E sim]

---

## 7. What a FAIL looked like, and what fired

| criterion | fired? | adjudication |
|---|---|---|
| central numbers C1-C4 | reproduced exactly | - |
| F-a inner | no | - |
| F-b 20 Hz | 2 cells as written | mode-selection artefact; robust minimum ratio 0.979 [E `s3b`] |
| F-c outer | Ms clause on 5 cells as written | all 5 are cells where V294 is unstable (GM < 1); A1017 raises GM in each; no GM or describing-function failure anywhere |
| F-d traps | no | new risk reported: resistance to the driver's steering x1.44 |
| **F-e direction** | **yes: nom_J0.5nr 5-10 m/s `lp` x1.06, 4 of 4 runs** | on the harness's own refitted J_hi and J_hi2 the same cell reads x1.02-1.04 (same sign, under 5 %); my second method gives x0.99. **The design's "every member" claim is false on the J axis; the effect's sign at medium speed is model- and J-dependent** |

---

## 8. What must change on the design page for A1017 to stand (reports, not edits)

1. **Retract "the direction holds on all members" / "right way or within +/-4 % on every plant member under both disturbance
   models".** Replace it with the conditional form:
   - under `full`, favourable or neutral on all 23 members (<= x1.01);
   - under `lp`, favourable at J <= 0.3 and on the light-damping world, and **x1.02-1.07 at 5-10 m/s on J >= 0.5 members**.

   The plant study's best J at 5-10 m/s is 0.5.
2. **Add the driver-torque cost to section 10 and to the COST-CHECK sentence.**
   - The trim opposes the driver's own wheel acceleration at x1.44 the torque: rms 39 -> 56 T, p99 166 -> 244 T, max
     309 -> 429 T on r71b hands-on frames, after the taper.
   - A fast driver steer now binds the fb clamp (10 -> 223 ticks).
   - An operator report of "heavier when I steer it myself" is this edit, not an instrument fault.
3. **Add the settle-window caveat to the NULL sentence.**
   - In closed-loop simulation, A1017 moves 1.6-3 Hz motion out of the turn-in ramp and into the 1-4 s after it (x1.1-2.0 on
     many hard-turn cells), and raises the light-damping world's overshoot by 1-3 points.
   - "Jerky after turn-in" or "overshoots then settles" is therefore a predicted possible outcome of this edit. It should
     revert to 1011 and not be read as "not trim-damping-limited".
4. **Correct section 4.2.** "At 25 Hz ... it is still not anti-damping" holds only at zero added delay. With the plant's
   2 ms, both builds are anti-damping at 20-25 Hz (V294 -0.06 / -0.14, A1017 -0.09 / -0.16 T per deg/s). A1017's increment is
   0.1-0.4 % of V282's reaction, and stress-mode zeta changes by <= 2.1 %.
5. **Restate the 1 Hz literal-metric cost** as up to 15 % on identified members (b_lo corner) and 24 % on light_b.
6. **State the margins that move the wrong way:**
   - identified-member outer PM at 3-5 m/s falls 2-4 deg (lowest still 74.8 deg);
   - inner GM falls 0-15 % (lowest still 4.1).

---

## 9. Files (all in `analysis-2020accord/studies/v295/design/dynamics/`)

**Criteria**
- `ADV-stability-CRITERIA.md`: pre-registered.

**Scripts and outputs** (all in `adv_stability/`)

| script | output | what it does |
|---|---|---|
| `s0_lane_spotcheck.py` | `_out.txt` | my integer lane; golden-model and harness-lane spot check; cells by address |
| `advlin.py` | - | my linear library: exact-ZOH plant; inner loop as a state matrix and a Nyquist; outer loop; alpha/cmd |
| `s1_central.py` | `_out.txt` | C1-C3 by two methods; the 13-25 Hz damping sign against delay |
| `s2_inner_grid.py` | `_out.txt`, `.json` | F-a, 2,520 cells |
| `s3_hf_stress.py` + `s3b_probe.py` | `_out.txt` | F-b, 300 cells including V282 as the anchor |
| `s4_outer.py` | `_out.txt`, `.json` | F-c, 4,032 cells with the describing-function sweep |
| `s5_sweep_family.py` | `_out.txt`, `.json`, `s5_log.txt` | F-e, the harness engine on 23 members; also the retrodiction spot check |
| `s6_replay_r71b.py` | `_out.txt` | C4; the nonlinear byte-exact replay of r71b; driver-torque frames; synthetic fast steer |
| `s7_closedloop.py` | `_out.txt`, `.json` | my nonlinear closed-loop scenarios |
| `s8_seeds_diag.py` | `_out.txt` | 6-seed hard-turn and on-centre statistics; the settle-window finding |
| `s9_post_turn.py` | `_out.txt` | limit-cycle census after the turn |
| `s10_fe_seeds.py` | `_out.txt` | F-e adjudication: noise-free run plus 3 seeds |
| `s11_alpha_cmd.py` | `_out.txt` | literal metric over the family and J corners; restart pulse |
| `s12_heavyJ_turns.py` | `_out.txt` | the second method for F-e |
| - | `s13_hf_extra_out.txt` | the trim at 5-400 Hz |

**Defects in my own work, reported rather than hidden.**
1. s2's first run crashed on an empty `min()`: PM is infinite where \|L\| < 1 everywhere. It was fixed with `default=inf`, and
   the output file is from the fixed run.
2. s3's first mode selector returned NaN when a pair left the 8-45 Hz window. That produced 2 false F-b flags; `s3b`
   re-scored the grid with a 5-45 Hz least-damped selector.
3. The dwell and jump detector in `s7` cannot work with sensor noise on (the noise is 0.24 deg/s against a 0.25 threshold), so
   jump statistics come from the noise-free run only.
4. My nonlinear engine uses constant speed and synthetic demand. It has no road residual except the on-centre case. Its 1.6-3
   Hz levels are 3-10 % of the drive's, so like the harness it is NOT FIT for magnitudes.
