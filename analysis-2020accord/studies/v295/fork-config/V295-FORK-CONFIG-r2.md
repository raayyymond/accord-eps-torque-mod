# V295 fork toggle config "r2": design on the V295 harness

Subagent `fork-config`, 2026-09-30. **Design only.**
- Nothing was sent, flashed or deployed. No commit.
- The fork (`Dom 20d24ab79`) was read through `git show` / `git grep` only. Its working tree was not touched.
- STATE, memory, BUILD-LINEAGE and the harness were not edited.

Every decision-bearing claim is marked **[E]** EVIDENCE (with its method) or **[B]** BELIEF. Symptoms are the operator's to score; everything here is a band or a simulation.

The pre-registered FAIL criteria were written at 15:29 PDT, before any candidate number: `CRITERIA-fork-config.md`.

---

## 0. Bottom line

1. **The pre-registered FAIL sentence fired.** No config built from existing params passes gates G1–G11 *and* meets the win condition (8–22 m/s tracking **and** turn-hold ≥ +0.05 on both `nominal` and `light_b` under `lp`) on every robustness replicate. [E] `out/f7_gates_s*.txt`, `out/f11_robust*_out.txt`, `out/f6_hunt_gate_*_out.txt`.
   - The written consequence is **r2 = r1 unchanged**. `toggle-config_V295_r2.json` is **byte-identical** to the flown V294 r1 file (sha256 `38ba2950…`).
   - So drive (2) under the gated answer would repeat drive (1).
2. **The design does have a best candidate, which fails two gates.** Because the operator asked for a second config to fly, it is written under a name that states its failures: **`toggle-config_V295_r2alt_KiHigh0.8_GATE-FAIL-G4-G8.json`**.
   - The change is **one key: `AccordTorqueKiHigh` 0.0 → 0.8.** This is the fork's existing Accord Ki schedule: Ki stays 0.3 below 8 m/s, then ramps linearly to 0.8 at 18 m/s and above.
   - Every other key keeps its r1 value: SteerKP 0.9, AccordTorqueKi 0.3, SteerLatAccel 14.0, SteerFriction 0.011, KeepLearnedLatAccelOffset true, every torque-mode term off, LaneCentering on.
   - **Below 8 m/s it is r1, exactly** [E: the schedule code, `get_honda_accord_torque_ki`; the drive sim shows 0–5 m/s Δ ≤ 0.001; the hunt test is identical to r1 at every member and crown for ≤ 5 m/s].
   - Predicted, as r71b plus the sim delta over 4 plant members × 2 disturbance models × 2 seeds × 2 warm-start forms:

     | band | tracking, r71b → predicted | turn-hold, r71b → predicted |
     |---|---|---|
     | 8–22 m/s | 0.83 → **0.88–0.89** | 0.68 → **0.73–0.80** |
     | 15–22 m/s | 0.83 → 0.92–0.93 | 0.67 → 0.75–0.83 |
     | 22+ m/s | 0.92 → 0.96–0.97 | 0.94 → 0.96–0.99 |

     No band exceeds 1.0, so there is no predicted oversteer. [E model; B car]
   - **The gates it fails, both in the two worlds the harness trusts least:**
     - **G8**: loop-generated hard-turn 1.6–3 Hz wheel rate at 15–22 m/s is ×1.13–1.22 in the plant-alone `lp` world on `nominal`. The pooled-r1 value is ×1.17, which is +0.027 deg/s absolute, about 2 % of the drive's level at that speed. Under disturbance replay (`full`) it is ≤ ×1.08.
     - **G4**: on the lightly damped, high-friction `light_b` prior only, it produces a slow **0.6° p-p, 0.2–0.9 Hz straight-road weave at 22 m/s** under a large crown torque (1.5 × breakaway). r1 reads 0.0° there. This is the "hunt at speed" revert class, in the pessimistic world.
3. **Why nothing passes cleanly: every lever is fenced from a different side.** [E, harness]
   - **Anything that changes the loop below 8 m/s** fails the low-speed gates (G6/G9/G4: straight-road wander and stick-slip at 0–5 m/s). That covers lower LAF, higher Ki_low and lower Kp.
     - Below 8 m/s the low-speed factor dominates.
     - Kp enters there only through (1 + lsf/Kp), which *multiplies* the integrator and the friction relay.
   - **The only speed-selective knob is the Ki schedule.** At speed:
     - KiHigh ≥ 0.6 creates the `light_b` crown hunt (G4).
     - Every schedule raises the plant-alone hard-turn 1.6–3 Hz by 10–17 % (G8).
     - Gate-clean schedules (KiHigh 0.5) reach only +0.03 to +0.04, below the win threshold and below the ±0.06 one-drive scatter.
   - **SteerKP is flat.** No existing param lowers Kp at speed without changing low speed.
4. **Knob verdicts** [E harness unless marked]:

   | knob | verdict |
   |---|---|
   | SteerLatAccel | **14.0 stays.** Lowering it helps every band (+0.03 at 12.5, +0.06–0.10 at 11), but raises low-speed straight 1–3 Hz ×1.33 / ×1.83 (G6) and hard-turn 1.6–3 Hz (G8) |
   | SteerFriction | **0.011 stays.** F 0 and F 0.005 fail G11 (J-style error ×1.10–1.24 at ≥ 15 m/s; F 0 also loses 0.03 hold). F 0.016 fails G6. Describing-function margin: the relay must reach ×6 its flown slope before any loop goes marginal |
   | AccordTorqueKi | **0.3 stays.** 0.4–0.5 fails G9 / G4 at 0–5 m/s |
   | AccordTorqueKiHigh | **0 (gated) or 0.8 (r2alt).** |
   | SteerKP | **0.9 stays.** 0.75 helps G8 but trips low-speed G4; 0.6 fails G11 |
   | KeepLearnedLatAccelOffset | **true stays.** On r71b it is a live, valid learner doing real work (§3.5) |
   | SteerDelay / UseAutoSteerDelay | **unchanged.** ±0.1 s moves tracking ≤ 0.002 and trips G6 or G8 |

---

## 1. Pre-registered gates, and which candidate trips which

The gates are copied from `CRITERIA-fork-config.md`. Candidates are named Kp / Ki_low / KiHigh; LAF is 14 and F is 0.011 unless stated.

| gate | C 0.9/0.3/0.8 = **r2alt** | A 0.75/0.4/0.8 | B 0.75/0.4/0.6 | H 0.9/0.3/0.5 | E 0.9/0.5 flat |
|---|---|---|---|---|---|
| G1 outer, identified family (Ms ≤ 1.6, GM ≥ 3, PM ≥ 35°) | PASS | PASS | PASS | PASS | PASS |
| G2 `light_b` 17–27 m/s vs V294+r1 | PASS | PASS | PASS | PASS | PASS |
| G3 relay DF sweep ×[0, 2] | PASS (×6 to marginal) | PASS | PASS | PASS | PASS |
| G4 hunt (time domain) | **FAIL**: `light_b` 22 m/s, crown 1.5, 0.6° at 0.2–0.9 Hz, both seeds | **FAIL** (15 hits, low speed + `light_b` 17/22) | **FAIL** (13) | FAIL (1 point, see §5) | **FAIL** (14, low speed) |
| G5 oversteer | PASS | PASS | PASS | PASS | PASS |
| G6 straight 1–3 Hz ×1.3 | PASS | PASS | PASS | PASS | PASS |
| G7 1–5 Hz line +3 dB | PASS | PASS | PASS | PASS | PASS |
| G8 hard-turn 1.6–3 Hz ×1.10 | **FAIL** (lp nominal 15–22: ×1.13–1.22) | FAIL on seed 0 (×1.14) | PASS | FAIL on seed 0 (×1.17) | FAIL on seed 0 (×1.16) |
| G9 straight 0.3–1 Hz ×1.3 | PASS | **FAIL** skip-3 s (×1.33–1.37, 4–5 members, 0–5 m/s) | **FAIL** skip-3 s | PASS | **FAIL** skip-3 s |
| G10 divergence / slew | PASS | PASS | PASS | PASS | PASS |
| G11 J ×1.10 at ≥ 15 m/s | PASS | PASS | PASS | PASS | PASS |
| WIN, 8–22 Δtrk / Δhold, nominal lp | +0.065 / +0.058 | +0.080 / +0.078 | +0.057 / +0.056 | **+0.029 / +0.036 (no)** | **+0.048 (no)** / +0.055 |
| WIN, `light_b` lp | +0.062 / +0.096 | +0.078 / +0.121 | +0.060 / +0.094 | +0.032 / +0.051 | +0.051 / +0.077 |

Stages 1–3 (100+ candidates, `out/f7_gates_s1/s2/s3_out.txt`) failed the same way, only more often:
- LAF ≤ 12.5 fails G6/G8/G10.
- F ≤ 0.005 fails G11; F 0.016 fails G6.
- Kp ≤ 0.6 fails G11.
- Kp 0.9 with KiHigh ≥ 1.0 fails G8.

---

## 2. Method, and the controls that make the numbers usable

- **Harness.** `v295_harness.py`, unedited. `fc_lib.VecPort` subclasses its proven port with per-lane Kp, Ki(v), KiHigh, LAF, friction, offset and delay.
  - `get_friction`'s `np.interp` is evaluated per friction group, so an r1 row equals the harness port bit for bit.
  - The fork's own `get_honda_accord_torque_ki` is asserted equal to `Fork.ki_at` on a grid, and `HONDA_ACCORD_KI_SCHEDULE_V_BP == (8, 18)` is asserted.
- **V295 cells.** Read from the V295 image by address, hash `5c044d65…`. They equal `Cells.v294().replace(fb_b=1050)` exactly. [E: two readers, `out/f0` in `f0_probe.py`]
- **Controls** (`out/f1_control_out.txt`) [E]:
  - VecPort(r1) against the harness ForkPort, closed loop, 84 lanes: max |Δ| = **0.0** on ang, cmd, p, i, f, T and la_act.
  - V294+r1 on `lp` nominal reproduces the harness's retrodiction row to 3 decimals: .840 / .865 / .586 / .764 / .917.
  - Outer-loop algebra against a direct `outer_frf` call, 40 random forks: rel. diff 5e-8. That residual is LAF float32 (the fork's capnp field) against float64.
- **Noise floor.** A duplicated r1 lane-set (`r1dup`) runs in every batch. Its tracking and hold differences are ≤ 0.002, and its band ratios are 0.96–1.05. [E]
- **Robustness** (`f11_robust.py`). The whole identified family plus `light_b`, 10 members × 21 chunks, on each of:
  - two sensor-noise seeds;
  - with and without the first 3 s of every chunk. This is the warm-start form: at LAF 14, "scaled" equals "logged";
  - `lp` and `full`.

  A candidate must pass on all four replicates.
- **Hunt test (G4, `f3`/`f6`).** A synthetic straight at constant speed with zero demand:
  - a constant crown torque of 0, 0.6 or 1.5 × Fs;
  - the Karnopp plant, the real fork port, the byte-exact lane, the Honda limiter and the 22 ms pipe;
  - 60 s per run, scored on the last 30 s.

  Positive controls (`out/f3_hunt_out.txt`): F 0.05, Ki 1.2, KiHigh 3 and LAF 9 each hunt somewhere. The instrument discriminates.
- **Second method for turn-hold (`f5_static.py`).** A quasi-static fixed point built from r71b's own wire, with no simulated plant:
  - the static gain comes from actual lat-accel against delivered torque in steady turns;
  - the integrator enters as its measured equivalent gain.

  For C: 8–22 m/s hold +0.043 (intercept form) to +0.061 (through-origin form), against the sim's +0.047…+0.112. Both methods agree on direction and ranking, and neither puts 22+ above 1.02. [E: r1's fixed point reproduces the measured hold within 0.03 (intercept) / 0.09 (through-origin). The intercept regression is poorly conditioned, R² 0.001–0.53, so read the pair as a range, not a number]

---

## 3. What each knob does (why it is where it is)

### 3.1 SteerLatAccel (feedforward level) [E, stage 1]
- Lowering LAF lifts every band roughly uniformly:

  | LAF | tracking / hold gain | 0–5 m/s straight 1–3 Hz, lp nominal |
  |---|---|---|
  | 12.5 | +0.03 | ×1.33 |
  | 11 | +0.06–0.10 | ×1.83 |
  | 10 | +0.08–0.15 | ×2.02–2.09 |

  15–22 m/s hard-turn 1.6–3 Hz rises ×1.13–1.56, and at LAF ≤ 11 the slew-limited share rises ×2.5–3 at 0–5 m/s.
- **Mechanism** [E, code]. Below 8 m/s the fork's P path is (Kp + lsf)·e / LAF with lsf 5–14, so LAF is the only knob on low-speed loop gain, and SteerKP cannot offset it.
- The wire's deficit (turn-hold 0.67–0.69 at 8–22 m/s against 0.94 at 22+) is **speed-shaped**. A single LAF cannot match it without either over-driving the low-speed loop or over-delivering at 22+. The static method predicts LAF 11 reaches 1.08 at 22+.

### 3.2 SteerFriction (the relay) [E, stage 2 + `f12`]
- Its torque slope is F/0.30·(1 + lsf/Kp). That is **+57 % of P at every speed** with r1 (F·LAF/(0.3·Kp)), and its amplitude is 0.011 torque = 45 CAN counts regardless of LAF.
- Removing or halving it hurts the thing the operator calls "loose":
  - F 0: 8–22 m/s hold −0.027 and J ×1.12–1.16.
  - F 0.005: J ×1.10–1.24 with any schedule.
- F 0.016 fails G6 at 0–5 m/s (×1.31, b_lo).
- DF (`f12`): the first destabilising relay multiple is **×6** of the flown slope (`light_b` 26.9 m/s), and it is the same for every finalist and for r1.
- **So 0.011 is the harness optimum among {0, 0.005, 0.008, 0.011, 0.016}.**
- [B] It under-compensates the plant's 76 T Coulomb friction at 3 m/s (the relay is 29 T) and over-compensates it at speed (4–8 T). A single existing param cannot fix both.

### 3.3 AccordTorqueKi / AccordTorqueKiHigh [E]
- **Ki_low.** The live integral gain is Ki·(1 + lsf/Kp), which is ×17 at 3 m/s.
  - Raising Ki_low to 0.4–0.5 raises the straight-road 0.3–1 Hz wander at 0–5 m/s ×1.32–1.45 on 4–5 identified members once the warm start is excluded (G9).
  - It also moves which points stick-slip in the hunt test (G4).
  - Its gain is straight delivery +0.07–0.13 at 0–10 m/s ("loose at low speed").
  - The cost falls on the same symptom class as route 70's dwell-then-jump, so it is not taken.
- **KiHigh (the schedule).** It changes nothing below 8 m/s.

  | KiHigh | 8–22 m/s Δtracking (nominal) | gate cost |
  |---|---|---|
  | 0.5 | +0.029 | – |
  | 0.8 | +0.065 | – |
  | 1.0 | +0.08–0.09 | – |
  | 2.0 | +0.13–0.2 | – |
  | ≥ 0.6 | – | the `light_b` crown hunt at 17–22 m/s (G4) at every Kp tested (0.75 / 0.8 / 0.9) |
  | any | – | the plant-alone hard-turn 1.6–3 Hz at 15–22 m/s ×1.10–1.17 against pooled r1 (G8) |

- Rev 4 (route 75) flew KiHigh 2.5 through a different feedforward on V293. That is record, not evidence for this plant + fork path.

### 3.4 SteerKP [E]
- At low speed Kp is almost irrelevant to P, because lsf dominates. It appears in (1 + lsf/Kp), which multiplies Ki_eff and the relay.
- Kp 0.75 therefore raises both ×1.19 at 3 m/s and trips G4 at low speed (J_hi 4 m/s: 0.7° against 0.0).
- At speed, Kp 0.75 **helps** G8 (A: pooled ×1.10 against C's ×1.17) and `light_b` 27 m/s margins (GM 2.7 → 2.9).
- Kp 0.6 fails G11 (J ×1.11–1.23).
- **SteerKP is flat**, so the speed separation that would help does not exist in the params.

### 3.5 KeepLearnedLatAccelOffset [E, `f10_offset_status.py`]
- On r71b the learner is live: liveValid 1, useParams 1, calPerc 100 for the whole drive.
  - The filtered offset moves −0.10 → −0.18 (p50 −0.151); the raw value is −0.24.
- On straights (v > 8 m/s, |plan| < 0.2, 255 s), the offset (+0.145 m/s² added to the command) plus the integrator (+0.149) ≈ roll compensation (+0.301).
- The pair cancels a roll bias. Turning the offset off would double the straight-road bias the integrator must hold. **Keep true.**

### 3.6 SteerDelay / UseAutoSteerDelay [E, stage 6]
- lat_delay −0.126 s (→ 0.30 s): 8–22 m/s Δ ≤ 0.002, and it fails G6 (22+ straight 1–3 Hz ×1.34).
- +0.10 s: Δ ≤ 0.002, and it fails G8 (×1.17–1.41).
- There is no clear gain, so neither is touched. liveDelay read 0.326 s constant on r71b.

---

## 4. Outer-loop margins (V295 cells, relay slope included) [E model; B car]

Identified family (9 members): worst Ms / minimum GM / minimum PM.

| v m/s | r1 (V295) | r2alt (C) | A |
|---|---|---|---|
| 3.1 | 1.34 / 11.5 / 70° | identical | 1.37 / 10.8 / 66° |
| 5.0 | 1.28 / 11.4 / 90° | identical | 1.30 / 10.9 / 85° |
| 8.0 | 1.23 / 10.7 / 134° | identical | 1.24 / 10.5 / 132° |
| 12 | 1.20 / 11.3 / 137° | 1.21 / 11.2 / 128° | 1.21 / 11.4 / 122° |
| 22 | 1.11 / 14.2 / 121° | 1.12 / 14.1 / 112° | 1.11 / 15.4 / 109° |
| 26.9 | 1.14 / 12.5 / 134° | 1.15 / 12.2 / 112° | 1.13 / 13.6 / 109° |

`light_b` (the pessimistic prior), Ms / GM / PM:

| v m/s | V294+r1 (flew) | V295+r1 | r2alt (C) |
|---|---|---|---|
| 17 | 2.00 / 2.6 / 50° | 1.63 / 4.2 / 57° | 1.67 / 4.1 / 55° |
| 22 | 2.43 / 2.0 / 39° | 1.78 / 3.3 / 50° | 1.83 / 3.2 / 48° |
| 26.9 | 3.07 / 1.7 / 31° | 1.96 / 2.7 / 45° | 2.01 / 2.6 / 43° |

V295's trim bought most of the `light_b` highway margin. r2alt spends about 4 % of it, and the linear outer loop is not what fails. The G4 hunt is a nonlinear stick-slip effect that the linear margins cannot see.

---

## 5. Defects, surprises, and post-hoc items (disclosed, not hidden)

1. **G4 floor (clarification).** A 0.25° floor was added to the "×2" clause before any candidate G4 result, after the control run showed r1 at 0.0–0.1°: with 0.1° angle LSBs, 0.1 vs 0.0 would otherwise be "×2". The as-written verdict (no floor) is printed beside it and only *adds* failures. No candidate was rescued by the floor.
2. **G4 point noise.** H's single G4 hit is (nominal, 8 m/s, crown 0.6): 0.3° against r1's 0.1° in its batch. r1 reads 0.3° at that same point in another batch. It is scored FAIL as written; the within-noise reading is BELIEF.
3. **G8 instrument noise [E].**
   - r1's own plant-alone 15–22 m/s hard16 varies 0.149–0.163 deg/s between replicates, so the r1dup/r1 ratio runs 0.96–1.05.
   - The candidates' absolute values are stable: A 0.170–0.174, H 0.175–0.176, C 0.182–0.184.
   - The per-replicate gate was applied as written. The pooled view (A ×1.10, H ×1.12, C ×1.17) is context only.
   - The harness itself says the 15–22 m/s *static* plant is wrong (V295-HARNESS §10.6), and this band's `lp` numbers are DIRECTIONAL.
4. **The win band.** The "8–22 m/s" pooled band was added to the metrics after stage 1, because the criteria wording needed it. Stage 1's win column is therefore empty; stages 2+ carry it.
5. **`f6` batch rule.** Every batch now carries its own r1, because the sensor-noise stream is drawn per row. This was fixed before the first finalist run.
6. **Static second method.** The intercept regression is poorly conditioned. The through-origin form was added after the first run, and both are reported.
7. **Not modelled** (harness §9): hands-on, engage and override behaviour; the planner reacting to a car that delivers more; anything above 8 Hz. Nothing here speaks to grinding.

---

## 6. Complaint predictions (operator's words; the bands behind them)

| complaint | gated r2 (= r1) | r2alt (KiHigh 0.8) |
|---|---|---|
| "Loose/understeer at highway turns" | unchanged | **better, small.** 22+ tracking +0.03…+0.045, hold +0.02…+0.045, predicted 0.96–0.99. That is inside the ±0.06 one-drive scatter. 15–22 m/s turns: tracking +0.09…+0.10, hold +0.07…+0.16. [E model / B car] |
| "Loose on straights and turns at low speed" | unchanged | **unchanged below 8 m/s by construction** [E, code + sims]. 5–10 m/s tracking +0.01…+0.02 [E model]. The 0–5 m/s friction deficit is not addressable by a single existing param without low-speed stick-slip (§3.2–3.3) [B] |
| "Jerky on hard turns at medium speed" | unchanged by the fork (V295's firmware is the lever) | **5–10 m/s unchanged** (hard16 ×0.99–1.05). **15–22 m/s possibly slightly worse**: plant-alone ×1.13–1.22, replay ≤ ×1.08. [B: it could give back part of V295's gain at 15–22 m/s] |
| "No grinding or stuttering" | unchanged | [B] unchanged. Only the < 1 Hz integrator changes; HF is not modelled |

---

## 7. PRE-REGISTERED WIRE READ: separating the fork config from the firmware on the same drive

**Firmware** (unchanged by any fork config) [E: ADV-B-units-instrument-V295]:
- The c1/c2 OLS on the tap against the byte-exact march must read **c1 ≈ 0.99 [0.97, 1.01]** and **c2 ≈ 1.84**. c2 > 1.45 means V295 is live; c2 ≈ 0.99 means the ECU is V294; c2 < 0 means inverted.
- A fork config changes the command, not the firmware's response to it, so c1/c2 must read the same on drive (1) and drive (2).
- Precondition: the analyst's march reproduces r71b first (pooled c2 0.99 ± 0.03).

**Fork, initData.params** (`gitCommit 20d24ab79…`, dirty False), all 26 keys:

| key | drive (1) and gated r2 (= r1) | r2alt |
|---|---|---|
| AccordTorqueKiHigh | 0.0 | **0.8** |

The other 25 keys are identical in every file:
- SteerKP 0.9, AccordTorqueKi 0.3, SteerLatAccel 14.0, SteerFriction 0.011, KeepLearnedLatAccelOffset 1;
- AccordRatePlantFF 0, AccordHoldMap 0, AccordFrictionHyst 0, AccordRateLoopGain 0, AccordErrorNotchQ 0, AccordRefFilter 0, AccordDobHz 0, AccordHoldLevel 0, AccordFrictionHystBand 0, AccordDither 0, AccordDitherGate 1, AccordJerkLpHz 1.2, AccordFFRateGain 0.5, AccordEpsGainScale 1.0, AccordEpsSpringScale 1.0, AccordTurnFFTaper 0;
- ForceAutoTuneOff 1, ForceAutoTune 0, AdvancedLateralTune 1, LaneCentering 1.

The runtime `starpilotToggles.accord_torque_ki_high` must read 0.8 (the fork clamps it to 0–6; `known()` must be true).

**100 Hz reads** (method = V294-FLIGHT-ATTRIBUTION-r71b §B):

| read | r1 (drive 1, as r71b) | r2alt (drive 2) |
|---|---|---|
| Kp = torqueState.p / error | 0.9000 | 0.9000 |
| Ki = Δi / (0.01·error), unfrozen frames, **by vEgo bin** | 0.300 flat | **0.300 below 8; 0.40 at 10; 0.50 at 12; 0.65 at 15; 0.80 at ≥ 18 m/s** (linear 8 → 18) |
| LAF = (p+i+d+f)/−output, unsaturated | 14.000 | 14.000 |
| friction plateau of f (minus lat-accel terms) | 0.154 m/s² = 0.011 torque = 45 CAN counts | same |
| integrator share, ≥ 15 m/s | 0.26–0.41 | +0.01…+0.05 |

**The Ki(v) read is the only fork difference between the drives, and it must be seen before anything is attributed to r2alt.**

**Expected by band** (r71b + sim delta; drive (1) is expected to reproduce r71b within the firmware's ≤ 0.004 outer-loop effect):

| band | tracking, drive (1) → r2alt | turn-hold, drive (1) → r2alt |
|---|---|---|
| 5–10 | 0.87 → 0.88–0.89 | 0.80 → 0.80–0.83 |
| 10–15 | 0.58 → 0.63–0.65 | 0.51 → 0.50–0.55 |
| 15–22 | 0.83 → 0.92–0.93 | 0.67 → 0.75–0.83 |
| 22+ | 0.92 → 0.96–0.97 | 0.94 → 0.96–0.99 |
| **8–22** | **0.83 → 0.88–0.89** | **0.68 → 0.73–0.80** |

One-drive scatter at 120 s is ±0.06 tracking and ±0.12–0.15 turn-hold.

**What a null licenses.**
- If Ki(v) reads the schedule and 8–22 m/s tracking lands within drive (1) ± 0.06, this one drive **cannot distinguish** r2alt from r1. That is *not* evidence the schedule failed.
- Tracking at 15–22 m/s **below** drive (1) by more than 0.06 contradicts the model.
- If Ki(v) reads 0.3 flat, the key did not land: attribute nothing.

**REVERT signature** (to r1 = `toggle-config_V295_r2_REVERT_to_V294_r1.json`, byte-identical to the flown r1):
- tracking > 1.05 or turn-hold > 1.10 in any band (oversteer; route 70's failure mode);
- a **0.2–1.5 Hz straight-road weave at ≥ 15 m/s** (the `light_b` hunt the design predicts: about 0.6° p-p of wheel);
- a 2.0–2.7 Hz rate line more than 3 dB above drive (1)'s (route 71-old's 2.34 Hz class);
- 4 Hz chatter (the relay; F is unchanged, so this is not expected);
- darty on-centre (straight-road 1–5 Hz rate more than ×1.3 drive (1)).

---

## 8. Files

Written with `open(..., "x")`, re-read from disk, and decoded by **both** the kit codec and the fork's own `decode_parameters` (extracted by AST from `git show 20d24ab79:starpilot/system/the_galaxy/utilities.py`, sha `5143618c…`).
- The kit positive control (the operator's 2026-09-10 backup) passes.
- Fork encode equals kit encode on all 22 reference pairs.

| file (`analysis-2020accord/reference/`) | what | sha256 |
|---|---|---|
| `toggle-config_V295_r2.json` | **gated r2 = r1** (26 keys, Δ = none) | `38ba295023e231eea49c294d846ef1f73ba99e2b4945e98a2ebb1edf37b3aa76` (= r1 file) |
| `toggle-config_V295_r2.decoded.json` | | `50eac1ad36be6f9b53d7c25003c247cbbd184e529f0befa603e7ed502674c722` |
| `toggle-config_V295_r2_REVERT_to_V294_r1.json` (+ .decoded) | r1 | same two hashes |
| `toggle-config_V295_r2alt_KiHigh0.8_GATE-FAIL-G4-G8.json` | **r2alt**: r1 + AccordTorqueKiHigh 0.8 | `c428be3238315b87639f9581241d08bb6fad2109d5beec206b8985c47f21b50b` |
| `toggle-config_V295_r2alt_KiHigh0.8_GATE-FAIL-G4-G8.decoded.json` | | `149a64738a0a4e27e7324d09b4d27a871aa43bad5edfe14a0031cd1e432abe13` |
| `toggle-config_V295_r2alt_…_REVERT_to_V294_r1.json` (+ .decoded) | r1 | `38ba2950…` / `50eac1ad…` |

The wrapper is r1's own form (format / version / settingsCount / data). **Nothing is deployed; Galaxy restore is the operator's action.**

**Scripts** (all in this folder, outputs in `out/`):

| script | job |
|---|---|
| `CRITERIA-fork-config.md` | the pre-registered gates |
| `fc_lib.py` | per-lane fork port, sim, metrics, outer loop, hunt |
| `fc_codec.py` | kit and fork codecs |
| `f0_probe.py` | V295 cells from the image, plant members |
| `f1_control.py` | bit-identity and retrodiction controls |
| `f2_outer.py` | G1–G3 over a 1944-point grid |
| `f3_hunt.py` | G4 positive controls |
| `f4_sweep.py` + `f4b_make_spec.py` / `f4c_make_spec3.py` | drive sweeps (stages s1–s3, s6) |
| `f5_static.py` | second method |
| `f6_hunt_gate.py` | G4 |
| `f7_gates.py` / `f7b_detail.py` | gates and detail |
| `f8_codec_check.py` | codec controls |
| `f9_write_config.py` | the writer |
| `f10_offset_status.py` | the learned offset |
| `f11_robust.py` | robustness (s4, s5) |
| `f12_outer_fin.py` | finalists' margins and DF |
| `f13_final_numbers.py` | the pre-registration numbers |


---

## Orchestrator's ruling (2026-09-30, after both adversaries)

**Drive (2) flies `toggle-config_V295_r2alt_KiHigh0.8_GATE-FAIL-G4-G8.json`** (sha256 c428be32…): r1 + `AccordTorqueKiHigh` 0.8 — the
fork's existing Ki schedule, Ki 0.3 below 8 m/s rising linearly to 0.8 at ≥ 18 m/s. The gated r2 (= r1 byte for byte, 38ba2950…)
would make drive (2) a repeat of drive (1); the operator asked for a second config, and the only speed-selective knob that
exists is this schedule. Its two gate failures (G4 light_b straight weave at 17–27 m/s, 12/24 points vs 2/24 for drive (1) and
6–8/24 for the flown V294+r1, same 0.5–0.7° amplitude; G8 plant-alone hard-turn 1.6–3 Hz at 15–22 m/s ×1.09–1.14 vs the flown
state, lower per unit of turning motion, ×0.95 under replay) both sit in the worlds the harness trusts least. REVERT file:
`toggle-config_V295_r2alt_KiHigh0.8_GATE-FAIL-G4-G8_REVERT_to_V294_r1.json` (= r1, verified byte-identical by the orchestrator).

**Corrected read and revert signature (binding; adversary W/X changes adopted):**
- Attribution: the runtime `starpilotPlan` toggles (first value + changes, timestamped) and the **Ki(v) read = di/(0.01·error) by
  vEgo bin: 0.300 below 8 m/s, 0.33 / 0.40 / 0.50 / 0.66 / 0.80 at 8–9 / 10 / 12 / 15 / ≥ 18 m/s** (r1: 0.3000 flat) are
  PRIMARY; initData counts only if the restore happened before the route started (restore PARKED, confirm "Restored 26 toggle
  settings." with no "Skipped"). Kp 0.9000, LAF 14.000, friction plateau 0.157 m/s² unchanged. Diff the full lateral initData set
  between the two drives (SteerRatio, NNFF/NNFFLite, ForceTorqueController, UseAutoSteerDelay, SteerDelay, LatSmoothSeconds,
  SafeMode, LaneChange*) and log latAccelOffsetFiltered + liveDelay at each start.
- Firmware: the c1/c2 read must march drive (2)'s OWN command (reusing drive (1)'s regressors biases c1 to 1.03–1.11); expect
  c1 0.99, c2 1.84 on both drives.
- Primary outcome band: **15–22 m/s tracking gain** (predicted 0.83 → 0.92–0.93; power 0.95 at ≥ 120 s of hands-off engaged
  exposure, 0.07 at 60 s); pooled 8–22 is speed-mix sensitive and cannot decide +0.06. 22+ (+0.03–0.045) is inside the scatter.
  Below 8 m/s Ki is r1's, but the integrator STATE carried in from above 8 m/s is not (open-loop |di| p95 1.9 m/s² in the first
  10 s; closed-loop effect ≤ 0.001).
- Revert, RELATIVE to drive (1): tracking gain > 1.05 in any band ≥ 8 m/s (turn-hold alone cannot — its scatter is ±0.12–0.15);
  0.2–1.5 Hz straight-road wheel-rate rms or weave incidence on matched ≥ 15 m/s hands-off straights ≥ ×1.5 drive (1) over ≥ 5
  qualifying 10 s windows (NO CALL below that; the absolute "0.6° weave" equals r71b's own background 0.50–0.60°); a 2.0–2.7 Hz
  rate line > +3 dB over drive (1) on sustained curves ≥ 19 m/s; 4 Hz chatter (not expected, friction unchanged); "darty"
  only as straight hands-off 1–5 Hz wheel rate ≥ ×1.3 at ≥ 15 m/s over ≥ 120 s.
- New stated risk: a light hand correction that does NOT set steeringPressed winds the integrator ~2.5× faster at ≥ 18 m/s and the
  post-release swing to the other side is ~1.7× larger (~0.1 m/s², < 1° of wheel, 2–4 s). Flagged presses are unaffected.
- The low-speed complaint is NOT addressed by any existing param: every knob that changes the loop below 8 m/s (LAF, Ki_low, Kp)
  raises 0–5 m/s straight wander / stick-slip ×1.3–2.1 on the identified family. A single `SteerLatAccel` cannot fit a
  speed-shaped deficit (14 → 10 over-drives low speed and over-delivers at 22+).
