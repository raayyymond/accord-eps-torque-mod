# HOLD-RECORD-CHECK 2026-09-30: the 100 Hz feedback hold and the kit's 20 Hz record

Subagent `hold-record`, for the orchestrator. Analysis only. Nothing was built, flashed or sent.
Script: `analysis-2020accord/studies/angle_loop/hold_record_check.py`. It is deterministic and reads the V282 cals little-endian
from the V282 image, asserting sha `0ea98d06…`. Its output is in `_scratch/angle_loop/holdrec/out.txt`.

## 0. Headline

1. **The hold is real.** I re-verified the crux myself. **[EVIDENCE]**
   - The dispatcher `FUN_00014be4` activates slot 4 only when `counter % 10 == 4`. Ghidra `disassemble_bytes 0x14be4`
     shows `0x14C28 mov 0xa,r7 ; divq r7,r8,r10 ; cmp 0x4,r10 ; bne ; mov 0x4,r6 ; jarl 0x861e0`. Slot 0 is activated
     unconditionally at `0x14BF6`.
   - The slot table entry pointers are `0x2214A` at `0xBB928` (slot 0) and `0x22CA0` at `0xBB9E8` (slot 4). I read them
     with a Python LE scan of the V295 image.
   - The PID call `0x22522 → FUN_00028ea6` sits in the slot-0 body. The rate producer `0x22de2 → FUN_0003f776` sits in the
     slot-4 body. I decoded both `jarl`s from the bytes.
   - `FUN_0003f776` (decompiled) is a **pure scale** of the 1 kHz rate: `x = pol·((gp-0x6abe·48·1159)>>15)`, saturated
     to ±12000 and zeroed if |raw| > 13000. There is no filter.
   - `FUN_00055c42` (0x18F, decompiled) packs `-gp-0x6a56` directly. **The wire rate is the same 100 Hz sample the PID
     holds.**
   - **Not re-verified:** that the dispatcher runs once per 1 ms tick. That rests on the kit's dwell measurement and the
     tracer.
2. **The record already contained the hold. It called it a "3.9 ms inter-stream offset" and charged it to the PLANT.**
   **[EVIDENCE for the arithmetic; BELIEF (strong) for the identity]**
   - creep20 fed its byte-exact mirror the 0x18F rate through a zero-phase up-sampler (`up1k = resample_poly`), so the
     mirror ran without the hold.
   - It measured T_meas lagging T_sim by a constant +23…+33° at 20 Hz (3.2–4.6 ms), with amplitude meas/sim 0.946 / 0.967.
   - The hold predicts 32.4° (4.5 ms beyond the one tick the mirror and L_fw already carry) to 39.6°, with |H| = 0.936.
     Both phase and amplitude match.
   - A pure CAN timestamp offset would leave the amplitude ratio at 1.000.
   - Every later loop study then multiplied the tap plant by `exp(-jω·3.9 ms)` (`TAU_STREAM = 0.0039` in
     `loopshape20_*`, `mode_nature_v289_*`, `design290b_candidates.py`). **So the record's closed-loop L carries the hold
     to within 1–1.6 ms. Its LOOP conclusions stand. Its ATTRIBUTION and its PLANT phase are wrong.**
3. **The V294/V295 models omit the hold entirely.** The V295 harness feeds the lane `x = plant.sense()` every tick, and
   `advlib.inner_L` uses τ 2 ms + a 3 ms former + a ZOH half-tick. They are short by 5.5 ms: 4° at 2 Hz and 39.6° at
   20 Hz. **[EVIDENCE: the code]** Their "τ9" stress row (9 ms) is the realistic case, not a stress case.
4. **ANGLE loop:** the hold on `gp-0x6a00` plus the 2-tap FIR costs **4.3° at 2 Hz, 6.5° at 3 Hz and 8.6° at 4 Hz**.
   A fresh `gp-0x69ca` costs 0.4–0.7°. That is small but real. Budget about 6° of PM at a 3 Hz crossover, or take the
   fresh angle. **[EVIDENCE, arithmetic]**
5. **A D term on the held rate `gp-0x6a56` is a poor damper above ~20 Hz.**
   - The damping share (cos of the hold lag) is 0.77 at 20 Hz, 0.35 at 35 Hz, 0 at 45.5 Hz, and **negative (anti-damping)
     above 45.5 Hz**.
   - The hold aliases: a plant line at 80 or 120 Hz is read as 20 Hz.
   - A D for the 20 Hz mode should read the fresh 1 kHz `gp-0x6abe` instead, and needs scale and pol handling (§5).
     **[EVIDENCE arithmetic; the design note is BELIEF]**

## 1. The hold kernel, exact

With ages a = 1…10 ticks (slot 0 runs before slot 4 in the activation tick, as traced), the fundamental is
H(f) = mean_a e^{-jω·a·1ms}, which is a mean delay of 5.5 ms. With ages 0…9 it is 4.5 ms. A time-domain least-squares
check on a simulated held sinusoid reproduces it to 4 decimals (script §1, last column).

| f Hz | \|H\| | ∠ a1–10 | ∠ a0–9 | 2 ms | 3 ms | 3.9 ms |
|---|---|---|---|---|---|---|
| 2 | 0.999 | −4.0° | −3.2° | −1.4° | −2.2° | −2.8° |
| 7 | 0.992 | −13.9° | −11.3° | −5.0° | −7.6° | −9.8° |
| 13 | 0.973 | −25.7° | −21.1° | −9.4° | −14.0° | −18.3° |
| 15 | 0.964 | −29.7° | −24.3° | −10.8° | −16.2° | −21.1° |
| 16.63 | 0.956 | −32.9° | −26.9° | −12.0° | −18.0° | −23.3° |
| 17 | 0.954 | −33.7° | −27.5° | −12.2° | −18.4° | −23.9° |
| 20 | 0.936 | −39.6° | −32.4° | −14.4° | −21.6° | −28.1° |
| 26 | 0.893 | −51.5° | −42.1° | −18.7° | −28.1° | −36.5° |

**Fold partners: the loop's are 80/120/180/220 Hz, not 480/520 Hz.** The staircase carries a unit 20 Hz input as
0.236 at 80 Hz and 0.160 at 120 Hz. In reverse, a plant line at 80 or 120 Hz enters the PID exactly as a 20 Hz one would.

## 2. V282's two-sample-sum feedback on a held input

V282's feedback filter is a 923 / b 1560 / SUM, which gives DC 30.891 and a pole at 16.53 Hz. I ran it integer-exact.

- On 9 ticks out of 10, the `1+z⁻¹` sum adds two **identical** input samples. Its zero is at 500 Hz, so it does nothing
  against the 100 Hz staircase.
- Within one 10-tick hold, the pole moves s 65 % of the way to the new level. The step response to one held update of
  +400 is 0, 609, 1766, 2808, … and does not settle within the hold.

| f Hz | fresh \|r26/x\| ∠ | held \|r26/x\| ∠ | held/fresh | closed form H_fb·H_hold | image @100−f / fund |
|---|---|---|---|---|---|
| 7 | 28.44 −23.0° | 28.21 −36.8° | 0.992 −13.9° | 28.21 −36.8° | 0.014 |
| 16.63 | 21.76 −45.2° | 20.79 −78.2° | 0.956 −32.9° | 20.79 −78.2° | 0.054 |
| 20 | 19.65 −50.5° | 18.40 −90.0° | 0.936 −39.5° | 18.40 −90.1° | 0.079 |
| 26 | 16.53 −57.6° | 14.77 −109.1° | 0.894 −51.5° | 14.77 −109.1° | 0.142 |

The filter is linear in the fundamental: held = fresh × H_hold, exactly. **[EVIDENCE, two methods agree]**

Cross-check against the record: my V282 electronics give |C| 14.11 T per deg/s at 19.96 Hz. MODE-NATURE quotes |Re| 14.095,
so the magnitude matches. My phase is −64.9° against its −75.7°. The 10.8° difference is exactly the record's one tick plus
the ZOH half-tick (1.5 ms at 20 Hz). **So the record's electronics already carry one tick of sensor age, and the hold adds
4.5 ms beyond that, not 5.5 ms.**

## 3. The record: what changes, what stands

### 3a. CHANGES: `docs/traces/TRACE-2026-09-10-command-intersample-zoh.md`, ADDENDUM Check 3 "No staleness/hold from a slower producer"

**WRONG.** The phase masks it compared (`0x930` ⊆ `0xd38`) gate on the run-mode byte `gp-0x67fa`, not on the tick. The
producer sits in slot 4, which runs at 100 Hz. **[EVIDENCE, §0]**

Its "correction to the frame of the question" is **REVERSED**. It said the fold partners for 20 Hz are the CAN broadcast's
(80/120/180/220 Hz), not the loop's (~480/520 Hz). In fact **the loop samples at 100 Hz too, so 80/120/180/220 Hz ARE the
loop's fold partners.** Its 1 kHz |H_fb| table is correct arithmetic, but moot for aliasing, because the aliasing happens at
the slot-4 sampler, upstream of the filter.

Its Q2/Q4 material on the command-side ZOH is unaffected.

### 3b. CHANGES (attribution), STANDS (loop number): `rlog-tools/studies/grind/CREEP-20HZ-LOOP-ID-2026-09-03.md` "1.0 Timing"

The "fixed ~3.9 ms inter-stream offset … a constant offset is what a correct clock model leaves behind" is, on this
evidence, **the controller's feedback hold, not CAN timing**. The phase matches (3.2–4.6 ms measured against 4.5 ms
predicted beyond the mirror's tick). The amplitude matches (0.946 / 0.967 measured against 0.936).

- **BELIEF (strong), not EVIDENCE.** A TX-schedule offset between 0x18F and 0x1AB cannot be excluded from timing alone.
- **Discriminator:** re-run creep20 Part 4 with the mirror fed a **held** rate (ages 1–10 from the slot-4 tick), and check
  that |T_meas/T_sim| follows 0.984 / 0.964 / 0.936 / 0.901 at 10 / 15 / 20 / 25 Hz rather than 1.000.

### 3c. STANDS (loop), CHANGES (plant phase): `rlog-tools/studies/grind/MODE-NATURE-V289-RECENSUS-2026-09-09.md` "THE PLANT, BACKED OUT FROM THE TWO MEASURED LINE FREQUENCIES"

The back-out computed the plant as −180° minus the electronics, with the electronics taken without the hold. The tap
plant was "offset-corrected" by 3.9 ms. Both therefore absorbed the hold into the PLANT, which is why they agreed to 4–8°.

Charging the hold to the controller instead (4.5 ms beyond the record's tick):

| | record back-out | tap (corr) | physical plant (hold removed) | tap RAW | diff |
|---|---|---|---|---|---|
| V282 @19.96 Hz | −104.3° | −100° | **−72.0°** | −71.5° | −0.5° |
| V289 @16.63 Hz | −80.3° | −88° | **−53.4°** | −65.0° | +11.6° (error bar ±9.1) |

- **The physical plant lags about 30° less at 16–20 Hz than the record states.** The two-point "20 ms equivalent delay"
  comes down to about 15.5 ms.
- **The loop conclusions are unchanged.** That covers: the 16.63 Hz pole as V289's crossover; "the relocation was fully
  predictable from the notch skirt"; the plant-mode verdict for 20 Hz; and the falsified clamp explanation. All of these
  live in the loop L, and L contained the hold.

### 3d. STANDS, ±1 Hz: the −180° crossing at 19–24 Hz, and V282's PM at the 16.63 Hz pole

The record's L = L_fw (with its one tick) × G_tap × e^{−jω·3.9ms}. The true L = L_fw × H_hold(beyond one tick) × G_tap.
The residual is:

| f Hz | residual phase | \|·\| | shift of the crossing at the record's −8.9°/Hz |
|---|---|---|---|
| 7 | −1.5 … −4.0° | 0.992 | −0.2 … −0.45 Hz |
| 16.63 | −3.6 … −9.6° | 0.956 | −0.4 … −1.1 Hz |
| 20 | −4.3 … −11.5° | 0.936 | −0.5 … −1.3 Hz |
| 24 | −5.2 … −13.8° | 0.909 | −0.6 … −1.6 Hz |

The first value in each range is the a0–9 residual, the honest one given the record's tick. The second is a1–10, which
double-counts that tick.

- **V282 at 16.63 Hz:** |L| is 1.08 at −153.6° (PM 26.4°), or at worst −159.6° (PM 20.4°), not the recorded 1.13 / 30°.
- **V289** spent −30.1°, which leaves its PM at −3.7 … −9.7°. That is marginally *unstable* on the linear reading, where the
  record had about 0°.
  - The flown V289 pole was ζ +0.029, so the record's "spent essentially all of it" stands. The extra few degrees are
    within the back-out's ±9° error bar.

**No ranking changes.** That includes the four plant families, the V290 schedule cap, the V291/V292 loop-opening class
(7 Hz residual −1.5 … −4°), and V288's reference-side null.

### 3e. Common factor, ranking unchanged: the |P/x| at 20 Hz ladder (V282 44.90, V281r3 ~19, V295 3.85, V294 2.08)

These are lane-only numbers. The hold multiplies every one of them by 0.936 ∠−39.6° at 20 Hz. The ordering, and the goal
criterion "20 Hz loop gain ≤ V295's", are unaffected if they are compared like for like.

### 3f. CHANGES ("nominal" moves to τ ≈ 7.5–9 ms): the V294/V295 design and adversary models

Affected: `analysis-2020accord/studies/v295/design/harness/v295_harness.py`; `robust-joint/adv_stability/advlib.py` (whose
`inner_L` has ZOH + 2 ms + 3 ms former); `p-gain/ADV-stability-p-gain.md`; and `robust-joint/ADV-stability-robust-joint.md`.

- They feed the lane fresh x every tick, so the hold is missing in full: −2.0 / −4.0 / −5.9 / −15.8 / −39.6° at
  1 / 2 / 3 / 8 / 20 Hz. **[EVIDENCE: harness grep string `x = plant.sense()`]**
- Consequences. Their "at 2 ms delay only" findings are the optimistic case. The p-gain adversary's "at 6–9 ms, T1 flips
  to anti-damping (ζ 0.0740 → 0.0716 V294 → 0.0708 candidate)" and the robust-joint adversary's "A's trim is
  anti-damping at 20 Hz for any transport delay ≥ 2 ms" are the **realistic** rows.
- These were small and V295 flew without grinding (operator), so no verdict flips. But the label "nominal 2 ms" is wrong.
  The inner-loop margins (Ms ≤ 1.14, GM ≥ 16 "even at 9 ms") still hold, because τ9 ≈ the true total.

### 3g. OPEN: the r71b plant ID (`analysis-2020accord/studies/v295/plant/V294-PLANT-IDENT-r71b.md`)

It reports "transport delay T → wheel acceleration is 2 ms (0–6)" and a "−4 ms tap offset" from the live march and the V293
FF-only record. A null-march fit gave 0 ms.

If the −4 ms is the hold, which lives in the controller, then shifting T by it corrupts the physical T→accel delay by about
4 ms in a direction I could not establish from the document. **BELIEF; re-run the march with a held x.** The J/b/k/Fc fits
are low-frequency (≤ 3 Hz, where the hold is ≤ 6°) and are probably little affected. **[BELIEF]**

### 3h. Not explained by the hold

- **The ×0.69 magnitude anomaly in the derivative-ratio alias test** (`memory/accord/instruments/accord-alias-resolution-via-derivative-ratio.md`).
  Both 0x14A channels are slot-4 samples taken at the same instant, so the feedback hold cannot act between them.
- **The GATE2 boost-direction "34.7° = 12.8 ms at 7.5 Hz"** (`docs/review/GATE2-2026-08-20-boost-direction.md`). The hold
  could supply 11–14° of it, **only if** that lane reads `gp-0x6a56`, which I did not check.
- **The V291 "~24° and ×1.6 unexplained" at 7.3 Hz** (`docs/specs/design/DESIGN-V291-FBLP-2026-09-13.md` D2.3). A
  magnitude factor of 1.6 is not a hold signature (|H| 0.99 at 7 Hz).

### 3i. Re-opened: "20 Hz vs 80/120 Hz alias" (`memory/accord/mechanism/accord-r24-pumps-at-7hz-and-damps-at-20hz-...md`, Open)

This is now a **loop** question, not just an instrument question.

- The PID cannot tell a 20 Hz wheel line from an 80/120 Hz one.
- Its staircase output carries 0.236 / 0.160 images at 80 / 120 Hz. The output lag passes 0.048 at 100 Hz.
- The derivative-ratio test excluded the twin for the 27 Hz V81 line. **It should be run on the V282 `idx ≥ 20` 20 Hz
  windows before any design treats the 20 Hz object as a 20 Hz mode.** **[BELIEF that it will confirm 20 Hz; the
  fresh-ratio method is EVIDENCE-grade]**

### 3j. Correction to `memory/accord/firmware/accord-lkas-feedback-is-a-100hz-hold-and-the-zero-cave-angle-loop-edit-set.md`

It says "a 10-tick hold is ~36° of phase at 20 Hz on top of the 2–3 ms delay the record modelled". The correct statement:

- **39.6° in total at 20 Hz.**
- Against the 20 Hz loop studies (creep20 / loopshape20 / MODE-NATURE / V290 / V291), which absorbed it as the 3.9 ms
  offset, only **4–11°** is unmodelled.
- Against the V294/V295 harness and adversaries, which fed fresh x, the full 39.6° is missing.
- I did not edit the file. Proposed for the orchestrator.

## 4. The ANGLE loop

| f Hz | `gp-0x6a00` held + 2-tap FIR | `gp-0x69ca` fresh + FIR | hold alone |
|---|---|---|---|
| 2 | −4.3° | −0.4° | −4.0° |
| 3 | −6.5° | −0.5° | −5.9° |
| 4 | −8.6° | −0.7° | −7.9° |
| 8 | −17.3° | −1.4° | −15.8° |

- At a 2–4 Hz crossover the hold costs **4–8° of phase margin** with a magnitude above 0.997. It is small next to the fork's
  ~60 ms round trip, but it is not free. Choosing `gp-0x69ca` recovers it, at the frame-mismatch cost listed in the angle
  trace (gain 0.87 near centre, 0–7.3° offset shape). **[EVIDENCE, arithmetic]**
- **100 Hz staircase ripple** of a P angle loop on the held angle. The output lag |H(100 Hz)| is 0.0483. The resulting T
  ripple is 0.15 / 0.75 / 3.0 lane counts at 10 / 50 / 200 deg/s with Kp 960, and 0.64 / 3.2 / 12.9 with Kp 4096, against
  the 2461 rail. **That is negligible as torque.** It is a 100 Hz tone, though, and whether it is audible is unmeasured.
  **[EVIDENCE arithmetic; audibility BELIEF]**
- **The integrator** (enters as I>>7) is unaffected at these frequencies.

## 5. A D term on the held rate (optional edit 5)

Damping share = cos(hold lag):

| f | 2 Hz | 7 Hz | 16.63 Hz | 20 Hz | 26 Hz | 35 Hz | 45 Hz | 50 Hz |
|---|---|---|---|---|---|---|---|---|
| share | 0.998 | 0.971 | 0.839 | 0.771 | 0.623 | 0.353 | 0.016 | −0.156 |

- **D stops damping at 45.5 Hz** (55.6 Hz if the ages are 0–9). That is inside the hold's own 50 Hz Nyquist, and every line
  at 100 − f folds back with the wrong phase.
- The kit has a recorded ~45 Hz mode under driver load (`accord-grind2-is-a-45hz-mode-under-driver-load.md`, later disputed
  by `accord-three-grinds-are-one-frequency.md`). A held-rate D is neutral to anti-damping there.
- **Design note [BELIEF]:** to damp the 20 Hz plant mode, read the fresh `gp-0x6abe` (1 kHz) instead. Two cautions:
  - The scale is ×48·1159/32768 = 1.698, with pol `gp-0x6752` (recorded as −1). FUN_0003f776's |raw| > 13000 → 0
    plausibility zeroing does **not** apply to a direct read. Both would need handling.
  - I did not verify that `gp-0x6abe`'s producer runs before `0x22522` in slot 0. The tracer reports it as fresh at 1 kHz.
    **Verify before any build.**
- For the angle loop's own 2–4 Hz job, a held-rate D is fine: its share is 0.97–1.0 below 7 Hz.

## 6. Pre-registered FAIL conditions for this check

This check would have returned "the hold changes the record's loop conclusions" if either of the following had held.
Neither did.

- The record's L had excluded the hold. It included it as the 3.9 ms.
- The residual had exceeded the back-out's ±9° error bar at 16.63 and 20 Hz. It is −3.6 / −4.3° on the honest age
  convention, and −9.6 / −11.5° on the double-counted one.

## 7. Next steps

1. Re-run creep20 Part 4 with a held-rate mirror. This is the discriminator for §3b.
2. Run the derivative-ratio alias test on the V282 `idx ≥ 20` 20 Hz windows (§3i).
3. Re-state the V295-family harness with the hold, so the τ 2 ms nominal gives way to the hold plus τ.
4. Re-run the r71b march with a held x (§3g).
5. Bound the slot-4 latency (a 1 kHz tap of a slot-4 cell).
6. Verify the ordering of the `gp-0x6abe` producer within slot 0.
