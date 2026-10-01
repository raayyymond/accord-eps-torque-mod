# ADV-dynamics: trying to break the V295 fork config r2 / r2alt on the car's dynamics

Adversary subagent "dynamics", 2026-09-30. Analysis only.
- Nothing was sent, flashed, deployed or committed. The fork (`Dom 20d24ab79`) was read only, through `git show` and the harness's archive extract. I checked that extract against the commit: `latcontrol_torque.py`, `latcontrol_vehicle_tunes.py`, `pid.py`, `lateral.py` and `latcontrol.py` are identical once CRs are stripped.
- STATE, memory, BUILD-LINEAGE, the harness and the designer's files were not edited.
- Pre-registered FAIL criteria were written before any number of mine was computed: `ADV-dynamics-CRITERIA.md`.
- Scripts are in `adv_dynamics/` and outputs in `adv_dynamics/out/`.
- **[E]** means EVIDENCE, with the method given. **[B]** means BELIEF. Everything here is a band or a simulation; the symptoms are the operator's to score.

What I tested:
- **gated r2.** It is byte-identical to the flown r1 (sha `38ba2950…`), so drive (2) = drive (1).
- **r2alt.** This is r1 with `AccordTorqueKiHigh` 0.0 → 0.8 (sha `c428be32…`). I verified the decoded diff: 26 keys, exactly one differs.

The firmware is **V295** in both cases (sha `5c044d65…`). The image differs from V294 in 6 bytes: `0xC63EA` 567→1050, plus 4 checksum bytes at `0xC6FFC`. I read this myself [E].

---

## 0. Verdict: **SURVIVES_WITH_CHANGES**

1. **gated r2 (= r1) survives every dynamics attack.**
   - On V295 it is better than the flown state (V294 + r1) on every linear margin, every relay describing-function margin, the hard-turn 1.6–3 Hz band and the light_b weave count. No new defect. [E model]
2. **The central numbers reproduce, by independent methods.** [E]
   - The fork side is the REAL `LatControlTorque`, not the designer's port. The designer's `VecPort` with KiHigh 0.8 equals the real code in closed loop on r71b chunks at 7–29 m/s: max |Δ| 2.8e-17.
   - V294 + r1 lp retrodiction, nominal: **.840 / .865 / .586 / .764 / .917**, an exact match.
   - r2alt 8–22 m/s, nominal lp: **+0.065 tracking / +0.059 hold**. The designer has +0.065 / +0.058.
   - r2alt 8–22 m/s, light_b lp: **+0.062 / +0.097**. The designer has +0.062 / +0.096.
   - Outer-loop margins match the designer's §4 table to ≤ 0.1 GM and ≤ 1° PM.
3. **r2alt: two of my pre-registered criteria fired, and one of them stands.**
   - **X9 fired and stands** [E model, robust]. In the plant-alone (`lp`) nominal world, r2alt's hard-turn 1.6–3 Hz wheel rate at 15–22 m/s is above even the *flown* state's:
     - ×1.09–1.14 against V294 + r1, and ×1.13–1.18 against V295 + r1;
     - two seeds, and it survives a sharp 10th-order filter.
     - The designer's "could give back *part* of V295's gain" is too soft. In that world r2alt gives back *all* of it and more.
     - Mechanism [E]:
       - It is not band-pass leakage.
       - It is not stick-slip: r2alt has *fewer* stick-to-slip events.
       - About 60 % of it survives with plant friction removed.
       - It moves with a **×1.19 larger turning motion** (0.2–1.2 Hz rate) in the same frames: the wheel moves more because it now tracks.
       - Per unit of turning motion, r2alt's 1.6–3 Hz content is *lower* (×0.95).
     - Under drive-disturbance replay (`full`) r2alt keeps V295's gain: ×0.95 against the flown state on nominal, ×0.74 on light_b.
   - **X8 fired per point and is reversed as often** [E model]. This is a 2.0–2.7 Hz rate band on light_b sustained curves at ≥ 19 m/s:
     - above +3 dB against V295 + r1 at 2 of 6 points on seed 3, and 5 of 12 on replication;
     - but *below* by more than 3 dB at 6 of 12;
     - pooled: +1.2 dB against V295 + r1 and −0.9 dB against the flown state.
     - I judge my own per-point form uninformative: the light_b hold is bistable between stuck and stick-slip. This judgement is **post hoc and disclosed**.
4. **The designer's G4 statement understates r2alt's light_b weave** [E model, 3 seeds].
   - At the 22 ms pipe, r2alt weaves (≥ 0.4° p-p, 0.2–1.2 Hz) at **12 of 24** light_b crown × speed points (17–27 m/s) on every seed.
   - V295 + r1 does so at **2 / 24**, and V294 + r1 (flown) at **6–8 / 24**.
   - The amplitude is the same in all three, 0.5–0.7°. At 42–62 ms all three weave at 9–14 / 24.
   - On the **identified family** no config weaves at ≥ 8 m/s: r2alt's maximum is 0.1° p-p.
5. **A new (e) risk the page does not state** [E model].
   - A light driver correction that does **not** set `steeringPressed` (150 T for 4 s) winds r2alt's integrator ×2.3–2.5 more at ≥ 19 m/s.
   - After release the car swings ×1.6–1.8 further to the other side on the identified family: 0.09–0.14 m/s², 0.7–0.8° of wheel, decaying over ~2–4 s. On light_b it is ×1.1–1.3.
   - With `steeringPressed` set, the integrator is frozen and all configs are identical.
6. **Two revert-signature clauses cannot discriminate** [E arithmetic / model]. §7 gives the fixes.

---

## 1. Pre-registered criteria and outcome

| id | attack | outcome |
|---|---|---|
| X0 | reproduction | **PASS**: margins, retrodiction and r2alt deltas all reproduce (§0.2) |
| X1 | "r2alt = r1 below 8 m/s" | **PASS** [E]. The schedule reads `CS.vEgo` with BP (8, 18) (`latcontrol_vehicle_tunes.py` `get_honda_accord_torque_ki`). `pid.py` scales the *increment*: `i = self.i + k_i*i_dt*error`, so a speed change never steps the output. With paired noise, r2alt equals V295 + r1 bit-for-bit at every ≤ 8 m/s hunt point |
| X2 | identified-family margins, pipes 22/42/62, relay on/off | **PASS**: worst r2alt Ms 1.56, GM 5.3, PM 61° (62 ms, relay on) |
| X3 | light_b against the flown V294 + r1 | **PASS** at every speed, pipe and relay setting (§2) |
| X4 | relay DF | **PASS**: r2alt's first destabilising multiple equals V295 + r1's at every pipe |
| X5 | LSF-inflated relay at 3–5 m/s | **PASS**: margin ≥ ×8 light_b, ≥ ×16 identified (worst pipe, 62 ms) |
| X6 | nonlinear on-centre | **identified family: PASS** (no hunt ≥ 8 m/s, no 3–6 Hz chatter in any config). **light_b: confirms the designer's G4, and it is broader than stated** (§3) |
| X7 | oversteer (tracking / turn-hold > 1.05) | **PASS**: r2alt maximum tracking 0.975, maximum turn-hold 0.999 (light_b 22+ lp), over 5 members × 2 dists × 2 seeds |
| X8 | 2.34 Hz class on light_b ≥ 19 m/s | **FIRED per point, reversed as often, pooled +1.2 dB** (§4) |
| X9 | hard-turn 1.6–3 Hz above the flown state | **FIRED**: nominal lp ×1.09–1.14. Not in `full` or on light_b (§5) |
| X10 | 1–5 Hz line +3 dB | **PASS**: Δ ≤ 0.2 dB on every member, no new line |
| X11 | curve-exit wind-up | **PASS**: no exit overshoot on the identified family, and r2alt settles 2–3× *faster* (§6) |
| X12 | engage / override | **risk to state** (SURVIVES_WITH_CHANGES): the unflagged-resistance wind-up of §0.5 |

---

## 2. (a) Outer-loop margins, re-derived [E model; B car]

**Method.** The fork-side linearisation is mine, from the source:
- C(z) = (1 + lsf/Kp)·[Kp + Ki(v)·0.01/(1−z⁻¹) + k·F·LAF/0.30] / LAF
- meas = kla(v)·θ, with kla taken from the fork's own `VehicleModel` (sR 16.84)
- the 4096 wire scale, and an e^{−sτ} pipe

The EPS transfer (wire → θ) comes from two methods:
- **M1**, the harness analytic form;
- **M2**, a multisine through the byte-exact integer `H.Lane` and the `PlantBatch` stepper with friction off.

M1 and M2 agree within 4.4 % (median 3.4 %) over 0.05–8 Hz on 96 member × speed × firmware rows, with a 0.0–0.7° phase difference at 2.3 Hz. Margins use my own crossing code (`d1_outer.py`).

**Identified family** (7 linearly distinct members), worst Ms / min GM / min PM, relay slope included:

| v m/s | V294 + r1 (flew), 22 ms | V295 + r1, 22 ms | **r2alt, 22 ms** | r2alt, 42 ms | r2alt, 62 ms |
|---|---|---|---|---|---|
| 3.1 | 1.34 / 8.2 / 75 | 1.34 / 11.6 / 69 | 1.34 / 11.6 / 69 | 1.44 / 7.5 / 65 | 1.56 / 5.3 / 61 |
| 8 | 1.26 / 7.8 / 134 | 1.23 / 10.7 / 134 | 1.23 / 10.7 / 134 | 1.31 / 7.3 / 134 | 1.40 / 5.3 / 133 |
| 12 | 1.22 / 9.0 / 137 | 1.20 / 11.4 / 137 | 1.21 / 11.3 / 128 | 1.26 / 7.8 / 127 | 1.33 / 5.8 / 126 |
| 22 | 1.12 / 12.6 / 121 | 1.11 / 14.3 / 121 | 1.12 / 14.1 / 112 | 1.16 / 9.7 / 112 | 1.20 / 7.4 / 111 |
| 26.9 | 1.15 / 11.1 / 134 | 1.14 / 12.5 / 134 | 1.15 / 12.3 / 112 | 1.20 / 8.4 / 111 | 1.26 / 6.3 / 111 |

**light_b**, Ms / GM, relay on:

| v | pipe | V294 + r1 (flew) | V295 + r1 | r2alt |
|---|---|---|---|---|
| 22 | 22 ms | 2.43 / 2.07 | 1.78 / 3.29 | 1.83 / 3.23 |
| 26.9 | 22 ms | 3.07 / 1.70 | 1.96 / 2.70 | 2.01 / 2.65 |
| 22 | 42 ms | 3.74 / 1.50 | 2.30 / 2.27 | 2.39 / 2.21 |
| 26.9 | 42 ms | 6.26 / 1.25 | 2.72 / 1.89 | 2.85 / 1.84 |
| 22 | 62 ms | 7.91 / 1.19 | 3.22 / 1.68 | 3.43 / 1.62 |
| 26.9 | 62 ms | **373 / 1.00 (marginal)** | 4.43 / 1.41 | 4.83 / 1.37 |

- r2alt costs ≤ 3 % GM and ≤ 9 % Ms against V295 + r1 at every pipe. It stays far better than the flown state.
- [B] The flown state would be marginal at 2.1 Hz at 27 m/s if the car were light_b with a 62 ms pipe. r71b shows no such line (harness: 22+ straights +1.2…+2.9 dB at 2.3–2.7 Hz), so the car is not "light_b + 62 ms".
- **Linear predictor of the hard-turn band** (`d1c_sens.py`): mean |S| over 1.6–3 Hz, r2alt against V295 + r1, is ×1.000–1.005 on the identified family and ×1.003–1.026 on light_b. The integrator adds ~1.6° of lag at 2 Hz.
- **The linear loop cannot produce G8 / X9.** §5 gives the mechanism.

---

## 3. (b) The friction relay and on-centre behaviour [E code + model]

- **It is a saturation, not a relay** [E, `lateral.py` `get_friction`]. The function is `np.interp(e_lsf, [−0.30, 0.30], [−F·LAF, +F·LAF])`, which is linear inside ±0.30 m/s² of `error_with_lsf` and clamped outside.
  - Its describing function is real and ≤ the small-signal slope at every amplitude.
  - The linear loop with the relay slope ON is therefore the worst case for any relay-induced cycle.
- **LSF inflation** (`d1b_df.py`). In torque per m/s² of planner error, the relay slope is (F/0.30)(1 + lsf/Kp) = **0.570 × P at every speed**. At 3.1 m/s, P is 1.053, the relay 0.601 and Ki_eff 0.351 /s.
  - It saturates at 0.018 m/s² of planner error = **5.2° of wheel at 3–5 m/s**, 4.4° at 8 m/s.
- **First destabilising relay multiple** (× the flown slope, worst member):

  | pipe | V294 + r1 | V295 + r1 = r2alt | identified family | 3–5 m/s |
  |---|---|---|---|---|
  | 22 ms | ×3 (light_b 26.9) | ×6 | ≥ ×30 | ≥ ×20 light_b |
  | 42 ms | ×2 | ×4 | ≥ ×20 | ≥ ×13 light_b |
  | 62 ms | ×1 | ×2.5 | ≥ ×16 (V294 + r1: ×13) | ≥ ×8 light_b |

  r2alt is identical to r1 at every pipe, since the Ki change is invisible at 2–3 Hz.
- **Nonlinear on-centre** (`d5_synth.py` S1). REAL controller, byte-exact lane, Karnopp plant, 0.1° quantiser, Honda limiter, x-noise 1.93; 5 members × 8 speeds × 5 crowns; paired noise.
  - **3–6 Hz chatter (route 73's class): none in any config.** The maximum 3–6 Hz band p-p is 0.11° for r2alt, 0.13° for V295 + r1 and 0.17° for V294 + r1.
  - **Identified family at ≥ 8 m/s: no hunt.** Maximum p-p 0.1° for r2alt, 0.3° for V295 + r1, 0.2° for V294 + r1.
  - **Low-speed stick-slip wander (< 8 m/s) is pre-existing and identical** between V295 + r1 and r2alt, as it must be: up to 2.3°, 0.2–0.3 Hz, on 13/60 points. V294 + r1 reaches 3.4°.
- **light_b weave at ≥ 17 m/s** (`d8_lightb_rep.py`). 6 crowns (0–3.5 × Fs) × 4 speeds = 24 points; count of points with ≥ 0.4° p-p:

  | run | V294 + r1 (flew) | V295 + r1 | **r2alt** |
  |---|---|---|---|
  | 22 ms, seed 7 | 6 | 2 | **12** |
  | 22 ms, seed 11 | 8 | 2 | **12** |
  | 42 ms, seed 3 | 13 | 9 | 11 |
  | 62 ms, seed 3 | 11 | 13 | 14 |

  - The worst amplitude is 0.5–0.9° in every config, and r2alt's is no larger than the flown state's.
  - The designer reported a single point (22 m/s, crown 1.5, 0.6°, "r1 0.0"). That is true at that point but **understates the class**. On light_b at the measured pipe, r2alt is the most weave-prone of the three: ×6 drive (1) and ×1.5–2 the flown state.
- **A defect in the designer's G4 instrument** [E]. `f6_hunt_gate_fin_out.txt` scores C with a hit at b_lo 8.0 m/s (0.3° against r1's 0.0). At 8 m/s r2alt ≡ r1 by code (Ki = interp(8, [8, 18], …) = 0.3), so that hit is unpaired sensor-noise variation. Sub-0.3° point hits of that gate are noise. My paired runs show exact identity there.

---

## 4. (c) Oversteer and the 2.34 Hz class [E model]

- **Drive replay, REAL controller** (`d4_drive.py`: 5 members × lp/full × 2 seeds). r2alt's maximum tracking gain is 0.975 and maximum turn-hold 0.999 (light_b 22+ lp). The median ratio at |plan| ≥ 1.5 is ≤ 0.976.
  - **No band exceeds 1.0 on any member.**
  - The 1–5 Hz limit-cycle line moves ≤ 0.2 dB on every member and dist, and there is no new line.
- **Sustained curves** (S2: ramp 2 s, hold 20 s; 12–27 m/s; a = 1 and 2 m/s²).
  - Identified-family hold ratio: r2alt 0.98–1.003 against r1's 0.84–0.99. In-curve peak ≤ 1.01.
  - **On light_b, every config overshoots the curve entry**: peak 1.10 at 26.9 m/s, a = 2 for V294 + r1, V295 + r1 and r2alt alike; 1.11–1.17 across seeds and pipes. r2alt adds ≤ +0.03 at 15–22 m/s. This is pre-existing in the pessimistic world, not created by r2alt.
- **2.0–2.7 Hz in the hold, light_b ≥ 19 m/s.**
  - A 2.15–2.54 Hz stick-slip line (+2 to +9 dB prominence) is present in all three configs. It is strongest at 12 m/s, and strongest there for V295 + r1 (+9.1 dB).
  - Per point, r2alt is above V295 + r1 by more than 3 dB at 5 / 12 point-runs and below by more than 3 dB at 6 / 12.
  - Pooled rms: V294 + r1 0.125, V295 + r1 0.097, **r2alt 0.112** (deg/s). That is +1.2 dB against drive (1) and −0.9 dB against the flown state.
  - Linear check: the closed-loop |T| peak on light_b at 22 m/s is 1.28 @ 1.70 Hz for r2alt, 1.23 for V295 + r1 and 1.75 @ 2.17 Hz for V294 + r1. ζ is well above 0.10.

---

## 5. (d) Hard-turn 1.6–3 Hz: what the excess is [E model]

`d4_drive.py`, `d7_hard16.py` and `d10_leak.py` give 15–22 m/s, the harness hard-frame mask, and paired noise.

| read | V294 + r1 (flew) | V295 + r1 | r2alt | r2alt / V295 + r1 | r2alt / flown |
|---|---|---|---|---|---|
| nominal lp, harness filter (seed 0 / 5) | 0.159 / 0.168 | 0.153 / 0.162 | 0.181 / 0.186 | ×1.18 / ×1.15 | **×1.14 / ×1.11** |
| nominal lp, SHARP 10th-order 1.6–3 Hz | 0.164 | 0.160 | 0.180 | ×1.13 | **×1.09** |
| nominal lp, friction REMOVED | 0.176 | 0.165 | 0.179 | ×1.09 | ×1.02 |
| nominal lp, 0.2–1.2 Hz turning rate in the same frames | 1.70 | 1.71 | 2.03 | **×1.19** | |
| nominal lp, stick-to-slip events/s | 0.73 | 0.73 | 0.59–0.66 | fewer | |
| nominal full (drive replay) | 7.53 | 7.10 | 7.17 | ×1.01 | ×0.95 |
| light_b lp / full | 2.11 / 7.15 | 1.50 / 4.95 | 1.56 / 5.31 | ×1.04 / ×1.07 | ×0.74 / ×0.74 |

What the rows show:
- **Not leakage**: it survives the sharp filter.
- **Not stick-slip**: r2alt has fewer events.
- **Mostly linear**: ×1.09 remains with friction off.
- It moves with ×1.19 more turning motion. The ratio of 1.6–3 Hz to turning rate is 0.094 for V295 + r1 and **0.089 for r2alt**.

[B] So the plant-alone "jerky" metric rises because the wheel does more of what was asked, not because a mode is de-damped.

The plant-alone level (0.16–0.19 deg/s) is ~2 % of the drive's measured 7.6 deg/s (harness H4: NOT FIT). On the car this difference is below detection [B]. The exposure is thin: **14 s** of hard-turn frames at 15–22 m/s on r71b.

---

## 6. (e) The integrator: wind-up, override and engage

**Code** [E, `latcontrol_torque.py` @20d24ab79, `pid.py`]:
- `freeze_integrator = steer_limited_by_safety or CS.steeringPressed or vEgo < 0.3 or unwind_detected`.
  - The `unwind_detected` clause is asymmetric: it fires only on a *negative* setpoint rate below −1 m/s³ with |setpoint| < 0.3. This is generic code, the same for r1 and r2alt.
- On release (pressed → not pressed): `i *= 0.8`.
- Inactive: `pid.reset()`, so i = 0 at every engage. The request buffer is primed, so there is no setpoint step.
- Anti-windup: the clamp acts only when P + I + F would exceed ±steer_max (±LAF = ±14 m/s²). Below that, nothing bounds i but the error.

**Curve exit** (S2) [E model]:
- No opposite-side overshoot on the identified family for any config.
- The residual after exit decays **2–3× faster** with r2alt: 2–15 s against 9–31 s at 12–27 m/s. r1's slow unwinding is the "still turned after the curve" tail.
- On light_b, exit overshoots are 0.005–0.16 m/s² in all configs. r2alt's maximum is 0.09, against 0.12 for V294 + r1 and 0.16 for V295 + r1.

**Lane change** (S5: ±1.5 m/s² one sine over 4 s) [E model, `d9_traces.py`]:
- r2alt tracks more at the end of the manoeuvre (peak |la| 0.48 against 0.38 at 22 m/s).
- It returns to |la| < 0.05 in 0.46–0.51 s against 0.79–0.91 s, with **no** opposite-side overshoot on nominal; b_lo is +0.106 against +0.141.
- My first S5 metric read the end-of-manoeuvre lag as "post peak". That was my own metric error, corrected here from the traces.

**Light driver resistance not flagged `steeringPressed`** (S3: 150 T for 4 s, then released):

| member, v | integrator change during the push, r1 → r2alt (m/s²) | opposite-side swing after release, r1 → r2alt (m/s²) |
|---|---|---|
| nominal 22 | 0.19 → **0.47** | 0.053 → **0.093** (wheel −0.4° → −0.7°) |
| nominal 26.9 | 0.23 → **0.55** | 0.088 → **0.141** (−0.5° → −0.8°) |
| light_b 22 | 0.30 → 0.59 | 0.25 → 0.32 |

- With `steeringPressed` set (S3P), the integrator is frozen and all three configs are identical.
- Real light hands-on corrections below the Honda steer threshold will wind r2alt ~2.5× faster at ≥ 18 m/s [B on frequency of use].

**Engage.** i = 0 for every config. r2alt only builds it faster afterwards, so it has no engage-step risk of its own.

---

## 7. Changes the r2alt page and the pre-registration need (corrections, not a new candidate)

1. **G8 wording.**
   - Replace "could give back part of V295's firmware gain" with the following. In the plant-alone nominal world, r2alt's hard-turn 1.6–3 Hz is above even the flown state (×1.09–1.14 over two seeds; ×1.09 with the sharp filter). The cause is ×1.19 more turning motion, and per unit motion it is lower. Under replay it keeps V295's gain (×0.95 nominal, ×0.74 light_b against the flown state).
   - Add that this band has only 14 s of exposure on r71b.
2. **G4 wording.** On light_b at 22 ms, r2alt weaves at 12 / 24 points at 17–27 m/s (three seeds), against 2 / 24 for drive (1) and 6–8 / 24 for the flown state. The amplitude is 0.5–0.7°, equal to the flown state's. The identified family is clean.
3. **Revert signature, weave clause.** It must be read **relative to drive (1)**: weave incidence or rms on matched ≥ 15 m/s straights, with r2alt / drive (1) above about ×1.5. It must not be an absolute "~0.6° weave". In light_b-like worlds drive (1) and the flown state weave at that amplitude too, so the absolute clause cannot attribute a weave to r2alt.
4. **Revert signature, oversteer clause.**
   - The predicted 22+ m/s hold is 0.96–0.99 with ±0.12–0.15 one-drive scatter, so "turn-hold > 1.10" is about 1σ from the prediction and can fire on scatter.
   - Use tracking gain > 1.05 (scatter ±0.06), or require both.
5. **Add the risk.** A light driver correction that does not register as `steeringPressed` winds r2alt's integrator ~2.5× faster at ≥ 18 m/s. After release the car drifts ~1.7× further to the other side: about 0.1 m/s², under 1° of wheel, for 2–4 s.

Nothing here argues for changing gated r2. Drive (1) = drive (2) under it.

---

## 8. Files (all new; nothing else edited)

- `ADV-dynamics-CRITERIA.md`: the pre-registration.
- `adv_dynamics/` scripts:

  | script | what it does |
  |---|---|
  | `d0_setup.py` | toggles, images, real-controller timing |
  | `d1_outer.py` | M1 against M2 EPS; margins; X2 / X3 |
  | `d1b_df.py` | relay DF at 22 / 42 / 62 ms |
  | `d1c_sens.py` | linear |S| and |T| at 1.6–3 Hz |
  | `d2_engine.py` | synthetic closed loop with the REAL controller |
  | `d3_portcheck.py` | designer port against the real code at KiHigh 0.8 |
  | `d4_drive.py` | r71b replay, REAL controller, 5 members × lp/full × 2 seeds |
  | `d5_synth.py` + `d6_synth_report.py` | S1 hunt, S2 curves, S3 / S3P resistance, S5 lane change |
  | `d7_hard16.py` | friction on/off and stick-slip events |
  | `d8_lightb_rep.py` | light_b seeds and pipes |
  | `d9_traces.py` | trace reads |
  | `d10_leak.py` | sharp-filter and turning-rate decomposition |

- `adv_dynamics/out/`: every `*_out.txt`, the JSON results and the S1–S5 traces (`d5_traces_*.npz`, regenerable).
- Runtime ≈ 75 min on this PC.
