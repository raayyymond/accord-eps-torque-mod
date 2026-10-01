# REFUTE (friction / nonlinear lens) — DESIGN C0, 2026-09-30

**Verdict: FAIL — do not flash C0 as designed.** The design makes four decision-bearing claims. Each is falsified in
simulation by a scenario it did not run, and three of those simulations use the time harness's own `run()` and the
design's own C0 row. One defect is in the integer arithmetic of the design itself and can be fixed at zero byte
cost. Highway behaviour survived every attack on this lens (§6).

**Author:** subagent `refute-friction` (Opus), for the orchestrator `main`.

**What was run:**
- No image was built, nothing was sent, nothing was flashed. The fork was not touched.
- Ghidra was used read-only, in one `dry_run` disassembly of the V294 program (`0x29D76..0x29D83`).
- Scripts: `analysis-2020accord/studies/angle_loop/refute_friction/`.
- JSON caches: `_scratch/angle_loop/refute-friction/` (gitignored, regenerable).

## 0. What a FAIL looks like (written before the runs)

C0 FAILS on this lens if any of the following holds:
- (a) A self-sustained limit cycle or hunting with a constant setpoint, at any speed.
- (b) Friction-made dwell-then-jump at ≥ 8 m/s, or inside the 5–10 m/s band. The design predicts 0 events at ≥ 8 m/s,
  and its §7.2 makes the 5–10 m/s band a goal FAIL.
- (c) A dead zone that pushes the goal's tracking gain outside 0.95–1.05 at ≥ 8 m/s at lane-keeping amplitudes.
- (d) An override-release lurch above the design's quoted 0.27–0.84° (≥ 12.5 m/s) / 2.2° (8 m/s), in any
  driver-torque regime it did not test.
- (e) An engage or handover transient the design did not quantify, of a size the operator would feel.

## 1. Method (EVIDENCE)

**The lane: `fric_lib.LaneC0`.**
- It is the time harness's byte-exact `LaneVec` arithmetic, with the C0 cave inserted as the design's §1.2 listing
  computes it:
  - G = G(i) + (((v − X(i))·S(i)) >> 12), walked over the 7-row table including the 0xFFFF sentinel row;
  - E' = (E·G) >> 8;
  - I8 −= I8 >> 6 when |gp-0x4f68| > 1024.
- Guard: A2 + B2 (the PID runs iff ramp ≠ 0 ∧ request == 1).
- Cals: the C0 values (a 0, b 8192, C 65535, DB 0, Ki 199, ICL 4096, DCL 10240, Kp 450 flat, Kd 16 on −rate).

**Checks on the lane:**
- `selfcheck.py` CHECK 1: with the cave off, LaneC0 equals `lane_mirror_v295.lane_tick` (x = angle, sum, sp = 69ae,
  D = rate) with **0 mismatches in 40 000 random ticks**. That run includes skips and a varying driver torque, so the
  fade is exercised.
- CHECK 2: the cave table equals Honda's divq LERP within 1 count over v = 0..65535.

**The plant and sensors:**
- The plant is `harness_time.PlantVec`'s Karnopp model (10 kHz sub-steps). I generalised it to per-column parameters
  and added a torque disturbance.
- Sensors, 100 Hz hold and fork frame are identical to `harness_time.run`.

**Independent re-runs.** Findings 1, 3 and 4 were re-run on the harness's own code:
- `harness_time.run()` and `metrics()`;
- `rec_time.LaneCave`;
- the design's own row `rec_time6.cands()[0]`.

Those scripts are `expA2_harness_midspeeds.py`, `expB3_hunt_harness.py` and `expH_biascorrected.py`. They reproduce
the design's own 5 m/s row exactly (6 events, max snap 1.75°), which is a consistency control.

**Controls:**
- **Friction off** (`fric = 0`): it removes every slow-ramp event (0/24 cells) and isolates the integer effect in §3.
- **A re-based table** (Kp_base 225, Ki_base 100, G ×2): the same Kp_eff and Ki_eff at every speed. It isolates the
  e5 quantiser.

**Ghidra** (V294 program, `disassemble_bytes` dry run, `0x29D76..0x29D83`) confirms the cave's return point:
- the return is to `0x29D7A mov r16,r6`, then `0x29D7C sar 0x5,r6`;
- so e5 = E' >> 5 acts on the **cave-scaled** E'.

The saved decompile `_scratch/angle_loop/sentinel_gates/dec_28ea6_v294.c` (grep `>> 5;`) shows the same structure:
- `iVar31 = iVar31*4 - uVar35; uVar35 = iVar31 >> 5;`
- then `(I8>>3) + ((exc*Ki)>>3)`.

## 2. FINDING 1 (HIGH): the light-hand override winds the integrator to its clamp, then lurches 1–9° on release

The design quoted 0.27–0.84°. Script: `expC_lighthand.py`.

**What the harness did not test.** The harness's `ov_*` scenarios script the driver-torque word at **2400**, which puts
the fade at its 77/256 floor **and** turns the cave's bleed on. The cave bleeds only when **|gp-0x4f68| > 1024**.

**Fade at the bleed threshold** (EVIDENCE, the fade LERP at `0x2A0B4`):
- At |tq| = 1024 (i682f = 32), fadeB is 231 and f = 230/256 = **0.90**.
- At |tq| ≤ 1024 the lane therefore runs at 90–100 % authority, and the integrator has nothing to bleed it.
- 1024 internal counts is about 1000 on the 0x18F wire (wire = gp-0x4f60 × 125/128).
- Above 1024, the bleed switches on with no transition band: at 1024 vs 1025 the fade is identical (230) and only the
  bleed differs.

**Scenario.** The driver holds the wheel δ off a constant setpoint, then releases over 30 ms:
- the hand is the harness's own stiff hand;
- the setpoint is a straight road, θ_sp = 0;
- no fork O1.

Results, nominal plant (EVIDENCE, sim):

| v (m/s) | δ | hold | \|tq\| ≤ 1000: T fought / I share / release overshoot | \|tq\| ≥ 1100 (bleed on): overshoot |
|---|---|---|---|---|
| 26 | 0.5° | 1 s | 431 T / 350 T / **1.04°** | 0.15° |
| 26 | 1.0° | 1 s | 774 / 606 / **1.79°** | 0.30° |
| 26 | 2.0° | 3 s | 1 017–1 077 / 606–663 (the ICL clamp) / **1.86–1.88°** | 0.59–0.61° |
| 19 | 1.0° | 1 s | 746 / 606 / **1.99°** | 0.27° |
| 12.5 | 1.0° | 1 s | 372 / 300 / **2.21°** | 0.21° |
| 12.5 | 2.0° | 1–3 s | 748–817 / 606–663 / **4.44–4.50°** | 0.47–0.51° |
| 8 | 1.0° | 3 s | 489–518 / 447–484 / **5.81–5.84°** | 0.14–0.16° |
| 8 | 2.0° | 3 s | 696–753 / 606–663 / **7.98–8.03°** | 0.48–0.51° |
| 5 | 2.0° | 3 s | 686–737 / 606–663 / **8.80–8.86°** | 0.06–0.12° |

**How to read it:**
- **Overshoot.** The lurch is ×3–×70 the bleed-on value. At ≥ 12.5 m/s it is 1.0–4.5°, against the design's quoted
  0.27–0.84°.
- **Resistance.** At highway, a 0.5° hold for 3 s is resisted by **~690 T, of which 663 T is the I at its clamp.**
  V295's measured override resistance (STATE) is p99 307 T, max 554 T.
- **Fork O1 does not cover it** (BELIEF). In openpilot the Honda `steeringPressed` threshold is 1200 wire by default
  (BELIEF, not verified in the fork). If so, O1 never covers the |wire| ≲ 1000 band. That band holds every touch the
  design's own instrument classes as hands-on (500–1000 wire).

**What is EVIDENCE and what is BELIEF:**
- **EVIDENCE:** the bleed gate, the fade value and the simulated lurch.
- **BELIEF:** how often a real light hand stays below 1024 counts. No N·m scale exists for gp-0x4f60 vs T counts.

This is V283's known failure class (override/release lurch), reached through a driver-torque regime the design never
simulated.

## 3. FINDING 2 (HIGH): the integrator is blind to a +1 LSB error below ~11.5 m/s, and friction adds a dead zone, so small-amplitude tracking leaves 0.95–1.05 at 8–19 m/s

Scripts: `expG_smallamp.py`, `expH2_bc_ramps_amp.py`, and the control inline in the session.

**Integer defect in the design (EVIDENCE: arithmetic of `0x29D7C sar 5` on the cave's E', confirmed by Ghidra in §1).**
- One angle LSB is E' = 16·G/256 = G/16 counts.
- For G < 512, a **+1 LSB** error gives E' < 32, so **e5 = 0**: the integrator never sees it.
- A −1 LSB error gives e5 = −1. The resulting I increment per tick, at Ki 199:

| v (m/s) | G | e5 for +1 / −1 LSB | I increment per tick for +1 / −1 LSB |
|---|---|---|---|
| 3–11 | 256–492 | 0 / −1 | 0 / −25 |
| 12–15 | 543–896 | 1 / −2 | 24 / −50 |
| 19 | 1 421 | 2 / −3 | 49 / −75 |
| 26 | 1 706 | 3 / −4 | 74 / −100 |

- So DB = 0 still leaves a **one-sided 0.1° I dead band below ~11.5 m/s**. The design's DB adjudication (§2.3) did not
  see it.
- With the I idle, small errors run P-only. The DC gain is then Kp_T/(Kp_T + k) = **0.75 at 8 m/s and 0.78 at 10 m/s.**

**Friction off** (isolates the integer defect). Harness-definition tracking gain (slope of the 100 Hz wire angle on the
setpoint):
- ±0.2° and ±0.3° at 8 and 10 m/s: **0.75–0.87**;
- ±0.5°: 0.91–0.94.

**Fix check (EVIDENCE, sim A/B).** A re-based table (Kp_base 225, Ki_base 100, G ×2) gives the same Kp_eff and Ki_eff
at every speed. With friction off it restores the gain to 0.91–1.01. It costs **zero extra bytes**, and the overflow
budget still holds: |E·G| ≤ 8.8·10⁸ < 2³¹.

**Friction on, nominal plant** (EVIDENCE, sim):

| v (m/s) | amplitude | gain at 0.2 Hz | gain at 0.5 Hz | wheel stuck |
|---|---|---|---|---|
| 8 | ±0.2° | 0.88 | 0.14 | 56–60 % |
| 8 | ±0.3° | 0.93 | 0.48 | 40–45 % |
| 8 | ±0.5° | — | 0.79 | — |
| 8 | ±1° | — | 0.91 | — |
| 10 | ±0.2–0.3° | 0.66–0.94 | 0.33–0.58 | — |
| 12.5 | ±0.2–1° | **1.056–1.074** (above the window) | — | — |
| 19 | ±0.2–0.3° | — | 0.90–0.93 | — |

- The re-base fixes the 0.2 Hz shortfall (0.71–0.93 → 1.00–1.10; at 10 m/s ±0.3° it overshoots to 1.10).
- It does **not** fix 0.5 Hz (0.14–0.75 remains). That part is stiction against C0's deliberately low 8–12.5 m/s gain
  (60–100 T/deg against Fs 18–19 T).

**Other members:**
- F_hi and J_hi: 0.5 Hz gain −0.12 … 0.83 at ±0.2–0.5° at 8–12.5 m/s.
- F_lo (half friction) still fails: 0.58–0.93 at ±0.2–0.5°.

**Why the design's tracking claim does not stand.** The design's "≥ 8 m/s: tracking 0.995–1.02 / 0.98–1.05" was scored
only at the harness's amplitudes: ±9 / 3.6 / 1.5 / 0.9° at 8 / 12.5 / 19 / 26 m/s.

**BELIEF:** how much of the on-car band score comes from small-amplitude driving. Straight-road lane keeping at
8–12.5 m/s is mostly below ±1°.

## 4. FINDING 3 (HIGH): in the plant report's own bias-corrected world, C0 fails the harness's own gates at 8, 12.5 and 19 m/s

Scripts: `expH_biascorrected.py` (the harness's own code) and `expH2_bc_ramps_amp.py`.

**Why this world.** `V294-PLANT-IDENT-r71b.md` (grep `G3a`) says the estimator of record is biased at ≥ 10 m/s:
- b is ×1.7–1.9 too high;
- Fc is ×0.46–0.58 too low;
- Fc is −24 % at 5–10 m/s;
- "read 8–16 T".

The family carries the two corrections as **separate** corners (b_lo, F_hi). The design ran each corner alone. The
evidence-preferred world has **both**.

**The member `bc`:**
- b_lo's b;
- friction ×2 at the ≥ 10 m/s knots and ×1.3 at the 8 m/s knot.

**Results, harness `run()`, C0 row (EVIDENCE):**

| v (m/s) | tg0.2 / tg0.5 | hold slips (harness `stick` gate requires 0) |
|---|---|---|
| 8 | 0.997 / 0.965 | **1** (st) |
| 12.5 | 1.015 / 0.976 | **2** (rh) |
| 19 | 0.988 / **0.949** (`track` gate fails) | **1** (st) |
| 26 / 30 | pass | 0 |

**Small amplitude on `bc`:**
- 19 m/s, 0.5 Hz: the gain is **0.930–0.950 at every amplitude from ±0.3° to ±2°**.
- 12.5 m/s: 0.50–0.91 at 0.5 Hz, and 1.06–1.11 at 0.2 Hz, for ±0.3–1°.
- Slow ramps (0.25–0.5°/s): 1–11 dwell-then-jump events at 8–12.5 m/s, with snaps of 0.27–0.50°.

## 5. FINDING 4 (MEDIUM-HIGH): the stick-slip region is wider than declared, and it includes a self-sustained hunting limit cycle

Scripts: `expA2_harness_midspeeds.py`, `expB2_hunt_map.py`, `expB3_hunt_harness.py` and `expA_ramps.py`.

**The design's own harness at the speeds its table skips** (EVIDENCE, harness `run()` with the C0 row). Totals over the
five tracking scenarios:

| v (m/s) | stick events | max snap |
|---|---|---|
| 5.0 | 6 | 1.75° (reproduces the design's own row) |
| **5.5** | **4** | 1.67° |
| **6.0** | **2** | — |
| 6.5–22 | 0 | — |

- 5.5 and 6 m/s sit inside the **5–10 m/s band**.
- The design's §7.2 classes "dwell-then-jump above r6c in any band ≥ 5 m/s" as **FAILED its stated goal**, not as the
  pre-declared miss.

**Hunting at a constant setpoint.** The setpoint is held 40 s, with no disturbance and no reference motion. This is a
limit cycle, not a correction artefact.

| world | speed | p2p | T p2p | period | slips per 20 s | basis |
|---|---|---|---|---|---|---|
| nominal | 3–5 m/s | 0.23–0.39° | 129–189 T | 7–11 s | 3–5 | EVIDENCE: the harness's own `run()` with LaneCave (independent of fric_lib) and fric_lib |
| F_hi | 5–7 m/s | 0.22–0.50° | 134–258 T | — | 3–5 | EVIDENCE: fric_lib only; initial-condition dependent — the harness's own step-entry runs on F_hi at 5–7 m/s did not hunt |

- In fric_lib, the nominal 3–5 m/s case occurs for hold angles 0.3–8°.
- **Mechanism (3 m/s trace):**
  1. The wheel sticks 1 LSB past θ_sp.
  2. e5 = −1 integrates the I by −25 per tick over about 6 s.
  3. The wheel breaks away and jumps 0.37° to the far side.
  4. The I integrates back, and the cycle repeats.
- **Meaning:** "low-speed stick-slip gone" is unreachable even on a dead-straight road at a constant setpoint. Friction
  compensation (the design's C1) does not obviously cure an integral-action hunt (BELIEF).

**Slow ramps (curve entry at 0.25–0.5°/s), harness detector (a).**

| world | speed | events | snap |
|---|---|---|---|
| nominal | 5–7 m/s | 9–12 per 16 s of ramp | — |
| nominal | 8–12.5 m/s | 1 each | 0.21–0.46° |
| F_hi | 8 m/s | 9 | 0.39–0.54° |
| F_hi | 10–12.5 m/s | 1–3 | 0.30–0.55° |
| friction off (control, nominal and F_hi, 6–12.5 m/s) | — | **0** | — |

- The friction-off control isolates friction as the cause.
- The harness never ran a ramp slower than 2.5°/s.

**Comparison with V282 (BELIEF).** The record's r6c ratchet is 0.39–0.64 dwells/min (STATE / V293 memory). V282 is a
high-gain rate servo and is not simulated here, so the ≤ V282 comparison is not computable in sim.

## 6. FINDING 5 (MEDIUM): load handover at engage and after co-steering is unquantified (3–6° droop), plus I wind-up during the ramp-in

Scripts: `expD_engage.py` and `expF_costeer.py`.

**Engage in a held curve.** The fork sends the measured angle at the engage frame and then holds it (spec C3/C5, as the
design assumes). The driver lets go at engage.

| v (m/s) | curve angle | droop | then overshoot | I at 1 s | peak T |
|---|---|---|---|---|---|
| 3 | 45° | **6.3°** | 2.3° | 508 T | 476 T |
| 5 | 25° | **6.2°** | 2.0° | 476 T | 433 T |
| 8 | 15° | **5.9°** | 1.5° | 425 T | 369 T |
| 12.5 | 6° | 1.9° | 0.5° | — | — |
| 19 | 2.5° | 0.9° | 0.2° | — | — |

- **Cause of the overshoot:** the I charges at full rate during the 0.99 s ramp-in while the output is attenuated.
- **Release after the ramp-in completes:** the droop is still **3.4° at 3–8 m/s** (I = 0, P-only pickup of k·θ0).

**Co-steering, then release.**
- The cave's bleed is **sign-blind**: a hand helping the turn with |tq| > 1024 drains the I that carries the curve.
- Droop after release at 5–8 m/s on 15–25° curves:
  - 2.9–3.5° with the bleed on;
  - 1.7–4.4° without it;
  - 0.6–1.3° at 12.5 m/s.

**EVIDENCE vs BELIEF:**
- **EVIDENCE:** the simulation.
- **BELIEF:** the spring k at large angle (sat model), and whether V282 behaved better here. Its stiff rate loop resists
  any motion, which suggests it did.

## 7. Where C0 SURVIVED this lens (EVIDENCE, sim)

**Highway holds, 19–30 m/s.** Scripts: `expB_holds.py`, `expB2_hunt_map.py`.
- Setup:
  - 30 s holds;
  - members nominal, F_lo, b_lo, J_hi and F_hi;
  - disturbance d = 0, a 1.5·Fs crown, or a 0.05 Hz 2·Fs drift.
- Result: no quantiser limit cycle and no low-frequency hunt.
  - T rms in 5–30 Hz: 0.08–1.41 counts;
  - T rms in 0.3–5 Hz: ≤ 5.3 counts;
  - slips: 0;
  - error p2p: ≤ 0.13°.
- This is consistent with the design's LSB cap (Kp_eff 3000).
- The uniform quantiser is BELIEF, as the design states.

**Constant-setpoint holds at 6–12.5 m/s** (nominal, J_hi, b_lo): no hunting.

## 8. Smaller items

- **Mirror vs listing mismatch.** `rec_time.LaneCave` bleeds `((I8>>3)>>6)<<3`. The cave listing bleeds `I8 >> 6`.
  The two differ in rounding: in the listing, negative I stalls at about −56 and positive I at about +7.
  - Behaviour impact: negligible.
  - Gate impact: H1's "byte-exact mirror built from the built image" must use the listing's arithmetic, not LaneCave's.
- **The e5 floor is asymmetric at every speed** (§3 table). Under dither, the I sees a −½-count bias, which favours
  one-sided creep.

## 9. What would have to change (BELIEF until simulated in full and adversarially checked)

1. **Re-base the cave table: G ×2, Kp_base 225, Ki_base 100.** Same Kp_eff and Ki_eff, same bytes. This removes the
   +1 LSB integrator blind spot below 11.5 m/s (EVIDENCE for the friction-free effect).
2. **Close the bleed cliff.** Options:
   - bleed on |tq| above the hands-off threshold (about 500 wire);
   - scale the bleed by (1 − f);
   - freeze I while |tq| is above about 500.

   Each option must then be re-checked against the co-steer droop of §6.
3. **Low-speed and 8–12.5 m/s friction.** No gain safe on the credible family beats stiction at lane-keeping amplitudes.
   This needs friction compensation (the design's C1), sized from the drive. It also needs a decision on whether the
   integral-action hunt at 3–7 m/s is acceptable.
4. **Engage handover.** Hold the I at zero, or freeze it while ramp < 0x8000, to stop the ramp-in wind-up. The load
   pickup itself (3–6° at ≤ 8 m/s) needs either a fork-side torque feed-forward or the operator's acceptance on the page.

## 10. Reproduce

```
cd analysis-2020accord/studies/angle_loop/refute_friction
python selfcheck.py                         # LaneC0 == lane_mirror_v295 (0 / 40000), cave table vs Honda LERP
python expC_lighthand.py                    # finding 1 (3 s hold); add "3.0,8.0,12.5,19.0,26.0 1.0" for the 1 s hold
python expG_smallamp.py nominal             # finding 2; also F_lo,F_hi,J_hi
python expH_biascorrected.py                # finding 3 (harness's own run())
python expH2_bc_ramps_amp.py
python expA2_harness_midspeeds.py nominal   # finding 4 (harness's own run())
python expB3_hunt_harness.py                # hunting, harness's own run()
python expB2_hunt_map.py nominal            # hunting map; "F_hi,J_hi,b_lo 5.0,6.0,7.0,8.0,10.0,12.5,19.0"
python expA_ramps.py nominal                # slow ramps; also F_hi,J_hi,b_lo,F_lo
python expD_engage.py ; python expF_costeer.py   # finding 5
python expB_holds.py nominal                # highway survival (+ F_lo/b_lo/J_hi/F_hi "8.0,12.5,19.0,26.0,30.0")
```

Every script uses the `bin_decompile` env (`python`). Seeds are fixed. Each run takes 5–40 s.
