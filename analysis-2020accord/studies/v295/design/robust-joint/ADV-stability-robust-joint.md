# ADV "stability" vs robust-joint candidate A (0xC63EA b 567 → 1106): the dynamics attack

Adversary subagent `stability`, 2026-09-30. **Design review only.** Nothing was built, flashed or sent, and there was
no CAN traffic. No fork, firmware artifact, STATE, memory, lineage or golden-model file was touched, and nothing was
committed. Scripts and outputs are in `robust-joint/adv_stability/`. The FAIL criteria were written before any number
was computed (`adv_stability/ADV-stability-robust-joint-CRITERIA.md`). Every decision-bearing claim is marked **[E]**
EVIDENCE (with its method) or **[B]** BELIEF. These are bands and models; the operator scores the symptoms.

---

## 0. Verdict: SURVIVES_WITH_CHANGES

Candidate A is **dynamically safe on every plant consistent with the on-car record**. The central numbers reproduce
from my own code. The HF risk is bounded against V282's flight rather than against assumed stress modes, and it is
small.

A has one trade-off the design did not score. **It moves the outer loop's sensitivity peak down into 0.5–1 Hz at
0–12 m/s**, and in closed-loop replay the lateral error in that band rises on every plant member. That is a plausible
path to a slightly worse *"Loose on straights and turns at low speed"*. The design's headline claim, *"no complaint
proxy gets worse on any of 15 plant members"*, is therefore **false as stated**, and has to be corrected before the
page or the flight sentence goes out.

🛑 **The pre-registration fired by its letter on five rules, and I adjudicated all five after the fact** (§1).
- F-IN-2, F-IN-3 and F-OUT-1 fired only on plant hypotheses where V282 or V294 is itself linearly unstable. The flights
  contradict those hypotheses.
- F-HF-1 fired on 2 plants at an 18 ms delay where ζ_A = 0.38.
- F-HF-2 fired by a hair: 10.5–12 % against a 10 % threshold.
- F-OUT-2 fired on the light_b prior only, as a forced 0.59 Hz response. It is not a limit cycle.

If the orchestrator holds the letter of the pre-registration, the verdict is REFUTED. I do not, for the reasons in §1.

---

## 1. Pre-registered rules: what fired, and the post-hoc adjudication

| rule | fired by the letter? | where | adjudication (post hoc, flagged) |
|---|---|---|---|
| R1–R5 reproduction | no, all PASS | §2 | — |
| F-IN-1 (unstable) | **no** | 0 of 1,360 rigid and 0 of 3,768 two-mass cases | — |
| F-IN-2 (GM < 2 / PM < 45 / Ms > 2) | **yes**, 13 cases | light_b × J 0.5 (× b 0.56 or 1.0) at delay 12–18 ms | V282 is linearly unstable on all 13 (ρ 1.03) [E, my eigenvalues]. V282 flew with 0 % clamp binding (record), so these plants are contradicted. **Not a failure.** |
| F-IN-3 (ζ_A < 0.8·min and < 0.10) | **yes**, 145 cases | two-mass r2 0.8, delay 6/9/18 ms (21/42/82) | V282 is linearly unstable on all 145 (ρ 1.04–1.05). On the 1,702 record-consistent plants: **0 hits**. **Not a failure.** |
| F-HF-1 (A < 0.8·ζ_open, or > 25 % of V282's de-damping) | **yes**, 2 of 147 calibrated plants | delay 18 ms, ζ_open 0.62–0.66 | ζ_A = 0.38–0.40 (V294 0.45–0.47). My rule had no absolute floor, which is a specification error. **Not a failure.** |
| F-HF-2 (anti-damping > 10 % of V282's) | **yes, marginally** | 20 Hz, delay 4/6 ms: 12 % / 10.5 % | The eigenvalue and nonlinear effect on V282-calibrated plants is 3–11 % of V282's (§4). **Marginal; reported, not failed.** |
| F-OUT-1 (outer GM / Ms) | **yes by the Ms clause**, 27 cases | light_b corners, pipe 40–62 ms, sR gain 1.4 | Every one has V294 GM < 1 (linearly unstable), so Ms is not a margin there. A's GM is higher in all 27. On V294-stable cases: **0 hits**. |
| F-OUT-2 (limit cycle / +3 dB) | **yes, marginally**, light_b only | replay light_b lp chunk 0 (8.0 m/s): +3.14 dB at 0.59 Hz. One on-centre realisation (12 m/s): +3.5 dB | The replay line is a forced response to the planner's 0.59 Hz content. The on-centre case is not robust: the median over 9 realisations is ×0.73. No limit cycle on any member. **The mechanism is real (§5.2) but it is not a stability failure.** |
| F-NL-1 (C clamp > 1 %) | no | 0.0000 % every member, all ticks and hard turns | — |
| F-NL-2 (circle criterion) | no | min Re L −0.29 (family, delay ≤ 6 ms); −0.55 (all corners) | — |
| F-NL-3 (restart pulse > 288) | no | 284 T | margin 4 T |
| F-NL-4 (stick-slip +20 %) | no | events 64 → 60, jump 1.02 → 0.93° | — |
| F-NL-5 (taper loop) | no | **[B]** | trim share of the sum 0.03 → 0.12; taper-loop gain up by ≤ ~6 % |
| F-DIR-1 (jerk proxy up) | no | ×0.67–0.98 everywhere under common random numbers (CRN) | — |
| F-DIR-2 (α/cmd down) | no (1–8 Hz aggregate) | 3–8 Hz sub-band −0.023 at worst | — |
| F-DIR-3 (tracking / turn-hold > 0.01) | turn-hold +0.010..+0.014 (5–10 m/s, full) | slightly *tighter* | trivial. **The real miss is the 0.5–1 Hz error (§5.2), which this rule did not name.** |

The adjudications of F-IN-2, F-IN-3, F-OUT-1 and F-HF-1 rest on one filter I added after seeing the hits.
**A plant hypothesis must let the flown builds behave as flown:**
- V282 linearly stable, with every 5–45 Hz mode at ζ ≥ 0.010;
- V294 with every 5–45 Hz mode at ζ ≥ 0.03.

The filter is EVIDENCE-grounded, because the V282 clamp census read 0.0 % binding in every stratum and V294 flew with
ring presence 0.5 %. It is still post hoc.

---

## 2. Reproduction: every central number, my own code [E]

My own integer lane (`advlib.MyLane`) reads the cells by address from the image and asserts the V294 sha256.

| claim | designer | mine | method |
|---|---|---|---|
| lane == golden model | 0 mismatches | **0 / 48,000 ticks (T and r26), V294 and A**; harness `Lane` vs mine: 0 / 3,000 | `as1_repro.py` |
| K_α (T per deg/s²) | 0.21 → 0.41 | **0.2097 → 0.4091 (×1.9506)**, closed form = numeric | `as1` |
| opposing T/ω at 2 / 5 / 20 Hz | 3.41 / 3.44 / 1.26 | **3.41 @+23° / 3.44 @−25° / 1.26 @−81°** | my z-transfer |
| \|P/x\| at 20 Hz | V294 2.079, A 4.055, V282 44.90 | **2.079 / 4.055 / 44.90** | my transfer (V282 incl. Kd 128) |
| restart pulse at 10/30/100/300 deg/s | 28/84/283/561 (V294 14/43/144/419) | **29/86/284/563** (V294 15/44/146/420); b 1134 → 291 | integer march, bail then restart |
| int32 margin at a·s | 2.08 | **2.081** (integer march at x = 12000: 1,031,999,481) | `as1` |
| retrodiction row (V294 nominal lp 5–10 tracking) | 0.865 | **0.865** | harness simulate, `as5` |
| outer light_b at 26.9 m/s | GM 1.67 → 2.78, Ms 3.06 → 1.91 | **1.69 → 2.80, 3.09 → 1.92** | **my** outer linearisation from the fork source. It matches the harness `outer_frf` to 0.3 % (`as4`) |
| stress ζ: mode20 / mode13 at 5 m/s | 0.076 → 0.077 / 0.145 → 0.152 | 0.0753 → 0.0758 / 0.1431 → 0.1496 (exact ZOH); harness 0.0764 → 0.0773 / 0.1452 → 0.1522 | my exact-ZOH eigenvalues vs the harness semi-implicit Euler |

---

## 3. (a) The inner acceleration loop [E for the model, B for the car]

Two methods:
- my frequency-domain return ratio (`advlib.inner_L`): margins, Ms, min Re L;
- my exact-ZOH state-space eigenvalues (`advlib.closed_poles`).

`as2_inner.py`, `as3c_consistent_all.py`, `as2b_circle_out.txt`.

- **Family proper** (12 members incl. light_b, 5 speeds, transport delay 0–18 ms):
  - stable everywhere;
  - Ms max: 1.252 at 2 ms, 1.281 at 6 ms, 1.341 at 9 ms, 1.555 at 18 ms (V294 1.136 / 1.138 / 1.163 / 1.242);
  - GM min: 14.8 / 7.73 / 5.82 / 3.54 (V294 28.9 / 15.1 / 11.4 / 6.91).
- **Corners** (J × 0.5–2.5 and b × 0.56–1.5 on nominal and light_b): stable everywhere (ρ max 0.9994).
  - The F-IN-2 hits are all light_b × J 0.5 at 12–18 ms, and V282 is unstable on each (§1).
  - Record-consistent corners (1,010 of 1,360): Ms ≤ 1.43, GM ≥ 9.18, PM ≥ 58°. Every A-vs-V294 damping loss there
    leaves ζ ≥ 0.24.
- **Two-mass scan: 3,768 plants.**
  - Grid: f2 8–60 Hz × ζ2 0.02/0.05/0.1 × r2 0.2/0.5/0.8 × delay 2/6/9/18 ms × 4 base members × 3 speeds.
  - 0 unstable for A or V294.
  - 1,702 plants are record-consistent. On those:
    - **F-IN-3 hits: 0**;
    - A < 0.8·min(V294, open) on 3 plants, all at ζ_A ≥ 0.33;
    - lightly damped class (ζ_open < 0.10, n 484): worst A/open 0.829 (J_lo, 8 Hz, r2 0.5, 2 ms: 0.092 → V294 0.084 → A 0.076).
- **The on-car record bounds the delay** [B, model-structure dependent]. V282 turns linearly unstable on the rigid family at:
  - 6 ms: light_b, b_lo, J_lo at 3.1 m/s;
  - 9 ms: nominal.

  So the delays that bite A (≥ 12 ms rigid, ≥ 6 ms at r2 0.8) are the ones the V282 flight excludes.
- **Circle criterion** (the C and P clamps as sector-[0,1] saturations): min Re L = −0.29 (family, ≤ 6 ms) and −0.55
  (all corners, ≤ 6 ms), both > −1. Absolute stability holds.
- **Where the design under-covered**:
  - its stress scan stopped at r2 0.5 and delay ×1.5;
  - a designer-like sub-scan without the record filter already gives worst ζ_A / min = 0.720 (light_b, 16 Hz, ζ2 0.02, r2 0.5, 9 ms), not ×0.895;
  - r2 0.8 at 6–18 ms gives ζ_A as low as 0.003.

  Its conclusion survives only because of the record filter. The design should say so.

---

## 4. (b) The 20 Hz question against the on-car record [E for the model, B for the car]

`as3_hf20.py`, `as3d_absolute.py`, `as7_modeA.py`.

**Gain.** |P/x| is 4.03–4.06 at 13–25 Hz: **9.0–10.0 % of V282's** (40.2–46.9) and ×1.95 of V294's.

**Phase.** b is a pure gain, so A's T/ω phase is V294's at every frequency. A lags V282's T/ω by 1–5° at 13–25 Hz.

**The sign does NOT survive the delay uncertainty.** A's damping component crosses zero at these frequencies:

| transport delay | 0 ms | 2 ms | 4 ms | 6 ms | 9 ms | 12 ms | 18 ms |
|---|---|---|---|---|---|---|---|
| zero crossing | 27.3 Hz | **17.8 Hz** | 14.1 Hz | 12.0 Hz | 10.1 Hz | 8.8 Hz | 7.2 Hz |

So at the identified 2 ms, A is already anti-damping at 20 Hz. The design's *"turns anti-damping only past ~28 Hz"* is
true only at zero transport delay. The magnitude is small:

| delay | A at 20 Hz, T/(deg/s) | V282 at 20 Hz, T/(deg/s) | A / V282 |
|---|---|---|---|
| 2 ms | −0.12 | −0.04 | — (V282 near its own zero) |
| 4 ms | −0.43 | −3.52 | 12 % |
| 6 ms | −0.71 | −6.78 | 10.5 % |
| 9 ms | −1.04 | −10.81 | 9.6 % |

**The harness stress members are not anchored.** V282's lane on mode20 gives ζ 0.073–0.147, not the on-car 0.016.
They cannot carry an argument about closeness to the grinder.

**Calibration to the flight.**
- 30,240 two-mass plants × delays were scanned. **147 reproduce V282's grind**: ζ_open ≥ 0.05 → V282 ζ 0.010–0.035 at 19–21.5 Hz.
- **None of them has a delay of 0–2 ms**, so the record needs ≥ 3 ms in this model structure.
- On those plants, A versus open, and A's de-damping as a share of V282's (V294 about half of A in each):

  | delay | A / open (worst) | A's de-damping as % of V282's |
  |---|---|---|
  | 3 ms | 0.982 | 3.2 % |
  | 4 ms | 0.969 | 6.7 % |
  | 6 ms | 0.935 | 7.4 % |
  | 9 ms | 0.918 | 9.7 % |
  | 12 ms | 0.901 | 11.1 % |
  | 18 ms | 0.596 (ζ 0.66 → 0.40) | 42 % |

**Nonlinear positive control** (my replay, command held at 0, the drive's residual replayed, four calibrated plants):

| 17–23 Hz wheel rate | V282 | V294 | A |
|---|---|---|---|
| rms (deg/s) | 0.90–1.89 | 0.48–1.03 | 0.50–1.05 |
| vs V294 | **+40–120 %** | — | **+2–4 %** |

With the recorded command, A's 17–23 Hz wheel rate is +2–4 % over V294. Its delivered 17–23 Hz torque is ×1.4–1.8
(0.5 → 0.7–1.45 T rms), under the tap's 8-count quantum.

**Reading.** A sits at about a tenth of the grinder's 20 Hz anti-damping, twice V294's clean twentieth, on plants that
reproduce the grind. That is the margin, and it is BELIEF above 8 Hz because nothing there is identified.

---

## 5. (c) The outer loop, fork law unchanged

### 5.1 Margins [E for the model]

`as4_outer.py`, `as4b_summary.py`, `as8_sensitivity.py`.
- 1,836 cases: 11 members + 6 corners × 9 speeds 1.5–30 m/s × relay on/off × pipe 22/40/62 ms × sR gain 1.0/1.4. The
  1.4 is the Accord SR map's incremental gain at 100–250°, which I derived.
- **A's GM ≥ 1.037 × V294's GM in every case.**
- **No case where V294 is stable and A is unstable.** 44 of V294's 55 unstable cases become stable with A.
- Ms ratio ≤ 1.020 on V294-stable cases.
- Relay describing function (relay gain at 0 / 0.25 / 0.5 / 0.75 / 1 of its slope): A ≥ V294 at every fraction.
- The low-speed-factor region (1.5–5 m/s) is covered: GM rises, e.g. nominal 3.1 m/s 11.1 → 15.0, light_b 4.5 → 7.7.

### 5.2 🛑 The miss: the sensitivity peak moves DOWN into 0.5–1 Hz at 0–12 m/s

[E for the model, both methods; B for the car]
- **Linear.** A lowers the global Ms and raises GM and PM, but the |S| peak moves to a lower frequency. On light_b at
  3–8 m/s it goes from 1.2–1.65 Hz to 0.93–1.38 Hz.
  - Max |S| over 0.5–1 Hz rises on **90 % of 432 cases** (9 members × 3.1–11.9 m/s × relay × pipe × sR gain): median
    ×1.03, maximum ×1.98 (light_b, 5 m/s, 62 ms, large angle: 1.22 → 2.41).
  - The effect is **monotone in the trim dose**. Max |S| in 0.5–1 Hz for V293 (b 0) / V294 / B (b 850) / A:

    | member @ speed | V293 | V294 | B | A |
    |---|---|---|---|---|
    | nominal @ 5 m/s | 1.02 | 1.12 | 1.15 | 1.18 |
    | b_lo @ 5 m/s | 0.93 | 1.12 | 1.19 | 1.24 |
    | light_b @ 8 m/s | 0.52 | 0.83 | 1.05 | 1.25 |

- **Nonlinear replay** (fork in the loop, CRN). The lateral-accel error in 0.5–1 Hz at **0–5 m/s**, V293 / V294 / A:

  | member | lp | full |
  |---|---|---|
  | nominal | 0.0146 / 0.0163 / 0.0177 | 0.0161 / 0.0179 / 0.0196 |
  | light_b | 0.0126 / 0.0181 / 0.0253 | 0.0150 / 0.0184 / 0.0246 |
  | b_lo | 0.0140 / 0.0167 / 0.0194 | 0.0154 / 0.0180 / 0.0207 |
  | J_hi2 | 0.0158 / 0.0165 / 0.0171 | 0.0170 / 0.0179 / 0.0185 |

  - At 5–10 m/s it rises under lp on every member and under full on light_b and b_lo.
  - The 1–2.4 Hz error falls, which is the jerk benefit.
  - The harness's own J metric (0.15–2.4 Hz) at 0–5 m/s under lp is ×1.02–1.17 on all 9 members.
  - At 3 m/s, 0.018–0.020 m/s² of lateral error is roughly 5–6° of wheel angle, so it is not negligible at parking-lot speed.
- **Mechanism.**
  - The doubled K_α adds wheel inertia below the 2 Hz pole (J_eff 0.41 → 0.61).
  - That adds plant phase lag right where the fork's low-speed factor inflates the outer gain ×4–17.
  - The waterbed pushes the sensitivity peak down onto the planner and road content.
  - The design scored the loose complaints at 0.1–0.3 Hz and the jerk at 1.6–3 Hz, so this 0.5–1 Hz band fell between its proxies.
- **Link to his V294 report** [B]. The model says V294's trim already did this relative to V293. The operator's V294
  report includes *"Loose on straights and turns at low speed."* A doubles the same term.

### 5.3 Limit cycles and hunting [E for the model]

- **Replay** (`as5_modeB.py`): 378 chunk rows, 9 members × 2 disturbance models, CRN. **1 row** has a line more than 3 dB
  above V294: light_b, lp, 8.0 m/s, 0.59 Hz, +3.14 dB. It is a forced response to the planner's 0.59 Hz content.
  Median −0.04 dB overall; at 8–20 m/s, median −0.09 dB.
- **Synthetic hard-turn steps** at 8/12/16/20 m/s, 10 members (`as6_synth.py`):
  - hold-phase 0.5–5 Hz oscillation ×0.85–0.99;
  - no P or C clamp binding;
  - **light_b overshoot +2 to +6.5 points** (8 m/s: 6.0 → 12.4 %). This is the §5.2 mechanism in the prior world.
  - Identified family: unchanged.
- **On-centre hold** (`as6b_hunting.py`: 7 members × 7 speeds × 3 seeds × 3 crowns, noise 1.93 and 0):
  - 0.3–2 Hz rate median ≤ 1.00 and stick-slip events fewer on every member;
  - the exception is frictionless light_b at 8–14 m/s, ×1.03–1.07, the linear sensitivity rise;
  - the single +3.5 dB realisation in `as6` (light_b, 12 m/s) is not robust: median ×0.73 [0.51, 1.17].

---

## 6. (d) Nonlinear traps [E for the model]

- **C clamp**: 0.0000 % of ticks, all and hard turns, on 7 members × 2 disturbance models in my own mode-A replay
  (`as7_modeA.py`), and 0.000 % in the synthetic hard turns.
- **P clamp**: 0.000 %.
- **Peak |T|**: 1228–1264, always ≤ V294's.
- **Restart pulse** (fault path only): 284 T at 100 deg/s, 4 T under the design's own 288 cap.
  - **New:** at 30 deg/s it now exceeds 50 T for 109 ms. V294: never.
  - At 300 deg/s the C clamp binds: 563 against 420.
- **Stick-slip, slow ramp at 0.05 m/s³** (CRN):
  - events 64 → 60 at zero noise, 37 → 35 at 1.93 counts;
  - mean jump 1.02 → 0.93°.
  - The added damping shortens the jumps. **No worsening.**
- **The 100 Hz staircase**: the FF is bit-identical. Delivered 17–23 Hz torque in replay is ×1.25 (0.44 → 0.55 T rms),
  and the wheel's 13–25 Hz motion ×0.97–1.03.
- **Driver-torque taper loop** (T → bar → taper → T) [B, the sim has no driver]:
  - the trim is 0.03–0.06 of the sum on V294 and 0.06–0.12 with A;
  - the taper-loop gain is set by the FF, which is unchanged;
  - the relative gain change is ≤ ~6 %;
  - the trim's cap is unchanged at 616.

---

## 7. (e) Does it move the complaints and the goal metric in the direction claimed?

- **"Jerky on hard turns at medium speed": DOWN on every member and both disturbance models** [E for the sim].
  - Mode B, CRN: 1–3 Hz rate ×0.67–0.98, hard-turn 1.6–3 Hz ×0.67–0.97.
  - My own mode A: 1–3 Hz ×0.76–0.91, hard-turn ×0.74–0.91.
  - The design's ×1.03 at 15–22 m/s under lp was its per-row noise defect. With CRN it reads ×0.92–0.96.
  - Magnitudes are NOT FIT; only the direction is claimed.
- **"Loose at highway turns": unchanged** — tracking ±0.004, turn-hold −0.009..+0.014.
- **"Loose on straights and turns at low speed": NOT unchanged.** Tracking gain is unchanged, but the 0.5–1 Hz lateral
  error rises at 0–10 m/s (§5.2). **Direction: possibly WORSE** [B for the car].
- **Goal metric, closed form (my own)**, best single complex gain α = G·cmd:
  - 1–8 Hz R² goes up on every member: +0.005..+0.083 with linear weights, +0.006..+0.136 with log weights;
  - 1–3 Hz: +0.005..+0.115;
  - **3–8 Hz: −0.023..+0.008**, slightly worse on low-speed members;
  - |α/cmd| at 1 Hz falls, e.g. light_b at 8 m/s 1.72 → 1.26: the wheel answers a quick command less.

---

## 8. Required changes (to the design page and the flight plan, not to A's bytes)

1. **Retract "no complaint proxy gets worse on any member".** State the trade:
   - A moves the outer sensitivity peak into 0.5–1 Hz at 0–12 m/s;
   - the 0.5–1 Hz lateral error at 0–5 m/s rises ×1.04–1.40 (0–10 m/s under lp), monotone in b, the same direction V294 took from V293;
   - the operator may find *"loose on straights and turns at low speed"* a little worse.
2. **Pre-register a wire read for it.** It is already free on the log:
   - quantity: the 0.5–1 Hz rms of `controlsState` desired − actual lateral accel (or the angle error) on hands-off frames;
   - bands: 0–5 and 5–10 m/s;
   - baseline: r71b;
   - prediction: **UP**, direction only.

   Add to the null sentence: an unchanged 0.5–1 Hz error means the waterbed shift did not reach the car.
3. **Re-anchor the HF argument on the flight, not the stress members.** The harness stress members do not reproduce
   V282's ring. Say instead:
   - A's trim is anti-damping at 20 Hz for any transport delay ≥ 2 ms;
   - its magnitude is ~10 % of V282's;
   - on V282-calibrated plants its de-damping is 3–11 % of V282's for 3–12 ms, and its HF wheel motion is +2–4 % against V282's +40–120 %.
4. **Correct the stress-scan claim.** The worst ×0.895 holds only for r2 ≤ 0.5 at the designer's delays. Wider coverage
   (r2 0.8, up to 18 ms) is safe only after the record-consistency filter.
5. **Restart pulse**: add the 30 deg/s row (> 50 T for 109 ms) and state the 4 T margin to the design's own cap.
6. **light_b-world risks**: add the hard-turn overshoot increase (+2 to +6.5 points) and the 0.5–1 Hz rise (×1.16–1.40).
   Both come from the same inertia term.

(A dose-down to B, b 850, halves both A's jerk benefit and the §5.2 cost, because both are monotone in b. That is the
orchestrator's trade, not my recommendation.)

---

## 9. Files (`robust-joint/adv_stability/`)

| script | output | what |
|---|---|---|
| `ADV-stability-robust-joint-CRITERIA.md` | — | pre-registered FAIL rules and the verdict mapping |
| `advlib.py` | — | my cell reader, integer lane (+D for V282), z-transfers, plant FRF, exact-ZOH state space |
| `as1_repro.py` | `as1_repro_out.txt` | R1–R4 |
| `as2_inner.py` | `as2_inner_out.txt` (+ json) | inner loop: rigid and two-mass scans |
| `as2b_circle_out.txt` | — | circle criterion |
| `as3_hf20.py` | `as3_hf20_out.txt` (+ json) | stress members (mine vs harness), damping sign by delay, calibration to V282 |
| `as3b_record_filter.py` | `as3b_record_filter_out.txt` | V282/V294 on every F-IN hit |
| `as3c_consistent_all.py` | `as3c_consistent_all_out.txt` | record-consistent worst cases |
| `as3d_absolute.py` | `as3d_absolute_out.txt` | absolute ζ on the consistent set |
| `as4_outer.py`, `as4_outer_lib.py`, `as4b_summary.py` | `as4_outer_out.txt`, `as4b_summary_out.txt` | my outer linearisation, 1,836 cases |
| `as5_modeB.py` | `as5_modeB_out.txt` | fork-in-loop replay, CRN, R5, limit-cycle read |
| `as5b_lowspeed.py` | `as5b_lowspeed_out.txt` | 0.5–1 Hz decomposition |
| `as6_synth.py` | `as6_synth_out.txt` | on-centre, hard-turn step, slow ramp |
| `as6b_hunting.py` | `as6b_hunting_out.txt` | hunting robustness |
| `as7_modeA.py` | `as7_modeA_out.txt` | my own mode-A replay, clamps, HF positive control |
| `as8_sensitivity.py` | `as8_sensitivity_out.txt` | the dose trend V293 → V294 → B → A, relay describing function, replay |
| `as8b_sens_robust.py` | `as8b_sens_robust_out.txt` | robustness of the 0.5–1 Hz rise |
| `as9_alpha.py` | `as9_alpha_out.txt` | goal metric, closed form |

The harness was used for these components only, each spot-checked:
- the fork port, bit-identical to the real code (the harness's gate);
- PlantBatch, for the as5, as6 and as8 replays;
- route data and chunks;
- `chunk_c0`, for the disturbance series.

The lane, the transfers, the eigenvalues, the outer linearisation, the mode-A plant integrator, the metrics and the
limit-cycle and stick-slip detectors are mine.
