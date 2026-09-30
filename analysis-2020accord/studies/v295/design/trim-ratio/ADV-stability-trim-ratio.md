# Adversarial pass "stability" on V295 trim-ratio: b at 0xC63EA, 567 → 964

Subagent `adv-stability`, 2026-09-30. **Design review only.**
- Nothing was built, flashed or sent. Nothing was committed.
- No fork, firmware artifact, STATE, memory, lineage or golden-model file was touched.
- The FAIL criteria were written before any number of mine existed: `adv-stability/CRITERIA-ADV-stability.md` (11:03 PDT).
- Every script and output is in `adv-stability/`.
- **[E]** marks EVIDENCE, with its method. **[B]** marks BELIEF.

## 0. Verdict: SURVIVES_WITH_CHANGES

| check | result |
|---|---|
| central numbers (R1–R5) | **Reproduced**, using my own code: my own cell reader, integer lane, exact-ZOH closed loop, return ratio, outer-loop linearisation and nonlinear simulator |
| dynamics FAIL clauses D1–D5 | **None fires as intended.** One sub-clause (D3's Ms) fires literally, in rows where V294 is itself linearly unstable (§4) |

**The dynamics case holds:**
- **Stability.** The candidate is stable on every member, every stress corner, delay ×1 to ×3, J ×0.5 to ×2.5 and every b corner.
- **Outer loop.** The unchanged fork law's outer gain margin gets **better** in every row (×1.03 to ×1.73).
- **No nonlinear traps.** Nothing I tried produced a new limit cycle, clamp binding or extra stick-slip.
- **The jerk direction holds.** Hard-turn 1.6–3 Hz wheel rate at 5–10 m/s falls on every member I ran.
- **The goal metric improves.** It gets better on 65 of 65 member-speeds, though only by a little.

**One claim on the page is wrong in sign and must be rewritten before the operator reads it.**
- The page says: *"It is still a damper at 13–20 Hz. Its phase is −60° to −70°, so it adds ζ to every stress mode instead of removing it."*
- That holds only if the delay after the tap is ≤ about 2–4 ms. The stress members were evaluated at 2 ms.
- The same model reproduces V282's on-car 20 Hz de-damping (ζ 0.016) only with **5–12 ms** after the tap.
- At those delays the trim's 20 Hz contribution is **anti-damping**. V294 already pays that, and b964 pays ×1.7 of it.
- The size stays small:
  - ≤ 0.004 of ζ against the open mode, and 0.001–0.002 more than V294;
  - about 5 % of what V282 removed.
- So this is a **claim correction, not a do-not-flash**. §3 has the detail.

**Margins on the page are quoted over a narrower set than the family allows.** They are thinner than stated but still inside the designer's own limits (§2, §5):

| margin | page | wider set (mine) |
|---|---|---|
| worst inner Ms at delay ×1.5 | 1.23 | **1.35** |
| worst inner Ms at delay ×3 | – | **1.51** |
| worst F5-HF band | ×1.45 | **×1.48**, against the ×1.5 line |

## 1. Reproduction gate (R1–R5): PASS

| # | quantity | design | mine | method |
|---|---|---|---|---|
| R1 | \|P/x\| at 20 Hz: V294 / b964 / V282 | 2.079 / 3.535 / 44.90 | **2.0790 / 3.5347 / 44.900** (sinusoid march: 2.0787 / 3.5319) | [E] my FRF from the golden-model arithmetic; a time-domain IntLane march |
| R2 | K_α (T per deg/s²) | 0.210 → 0.356 | **0.2097 → 0.3566** closed form; ramp march 0.205 → 0.350 (floor bias 2 %) | [E] two methods |
| R2 | HF gain ratio | ×1.70 | **×1.7002** at 1, 2, 5, 10 and 20 Hz | [E] |
| R3 | V294 march vs the 427 tap, hands-off | 3.64 counts | **3.64 counts** (35,441 tap frames), bit-exact to plib's march (0 of 1,020,390 ticks differ) | [E] `a5_replay_out.txt` |
| R3 | FF identity at x = 0 | identical | **0 mismatches** in 30,000 ticks | [E] `a4d_out.txt` |
| R4 | int32 a·s margin at \|x\| = 12000 | 2.39 | **2.387** (b_max 2301.1) | [E] |
| R4 | restart pulse at 10 / 30 / 100 / 300 deg/s | 24 / 73 / 246 / 542 | **25 / 75 / 248 / 544** (V294 15 / 44 / 146 / 420) | [E] my scenario definition differs slightly; within 5 % |
| R5 | worst inner Ms at delay ×1.5 | 1.23 (`tau9`) | **1.226** (`tau9`, 3.1 m/s, 14 ms) | [E] exact-ZOH closed loop plus my return ratio |
| R5 | mode20 ζ at 5 / 12 / 25 m/s | .076 / .099 / .115 → .077 / .101 / .116 | `VP.linear_poles` .0764 / .0994 / .1149 → .0770 / .1010 / .1165. Mine (exact ZOH) .0753 / .0964 / .1106 → .0757 / .0977 / .1120 | [E] two discretisations agree in sign and within 0.004 |

**Controls:**
- My IntLane equals the golden model (`lkas_fb_lag` + `lkas_rate_pid_tick`) on 20,000 random ticks each for V294, b964, V282 and b2301: 0 mismatches.
- My IntLane equals the harness Lane on 20,000 ticks: 0 mismatches.
- My lane FRF equals the harness `lane_ctf` to 5 digits and 0.00°.

**Harness spot check [E].** V294, nominal, dist lp, tracking gain by band from `sweep_drive`: 0.8397 / 0.8649 / 0.5862 / 0.7636 / 0.9166. The harness report gives 0.840 / 0.865 / 0.586 / 0.764 / 0.917.

## 2. (a) The inner trim loop across the family: no D1 fire

Source: `adv-stability/a1_inner.py` and `a1_inner_out.txt`.

**Coverage:**
- 25 members:
  - the identified family;
  - `light_b`, `J_0.3`, `tau0`, `tau6`, `tau9`;
  - mode13, mode20 and mode20_lo;
  - my own corners:
    - J ×0.5 and J ×2.5 (not refitted);
    - b ×0.5, and b ×0.5 with J ×2.5;
    - flexible modes on the prior (`lb_mode20`, `lb_mode20_lo`);
    - `mode16_lo`, `mode13_lo`.
- 7 speeds.
- Delay ×1, ×1.5, ×2 and ×3.
- Rate-former window 1, 3 and 5 ms at ×1.5.

**Results:**
- **Stability [E, model].** Spectral radius is below 1 for b964 wherever V294's is. No row is unstable on b964 only.
- **Worst Ms on b964:**

  | delay | Ms (V294) | where |
  |---|---|---|
  | ×1.5 | **1.354** (1.189) | `lb_mode20_lo`, 26.9 m/s, 3 ms |
  | ×1.5, `tau9` | 1.226 (1.124) | the page's case |
  | ×3 | **1.506** (1.252) | `lb_mode20_lo`, 6 ms |
  | ×3, `tau9` | 1.356 | 27 ms |
  | ×1.5, window 5 ms | 1.40 | `lb_mode20_lo` |

  No row has Ms above 2.
- **Worst GM on b964: 3.46** (V294 5.88), on `lb_mode20_lo` at 6 ms. The page's GM_min is 9.6; over the wider set it is 3.5.
- **Poles that become less damped than on V294.** None falls below ζ 0.15 by more than 0.02. D1 is clear. In detail:
  - **The low-frequency wheel/spring mode** (inertia effect, the known low-speed cost):
    - `light_b` 0.48–1.23 Hz: ζ 0.454–0.544 → 0.427–0.490;
    - `b_lo` 0.64 Hz at 8 m/s: ζ 0.70 → 0.64;
    - `J_hi2` 0.55 Hz: ζ 0.72 → 0.69.
  - **The lane-vs-J pair** moves from 3.3–4.0 Hz to 4.4–5.2 Hz, and ζ falls from 0.74–0.77 to 0.63–0.69.
  - **The flexible stress modes at longer delay** (§3). The largest matched drop inside ×3 is −0.0057 (`lb_mode20_lo`, 26.9 m/s, 6 ms: 0.0425 → 0.0368).

## 3. (b) 13–25 Hz against the on-car record: the damping sign does NOT survive the delay uncertainty

Source: `adv-stability/a2_hf.py` and `a2_hf_out.txt`.

**Gain and phase of x → T** (tap against the wheel rate; 0° = pure damping, the kit convention):

| f (Hz) | V294 | **b964** | V282 (ground on car) | b964 / V282 |
|---|---|---|---|---|
| 13 | 0.120 ∠−59.9° | **0.204 ∠−59.9°** | 2.335 ∠−55.1° | 8.7 % |
| 16 | 0.100 ∠−65.3° | **0.170 ∠−65.3°** | 2.052 ∠−59.8° | 8.3 % |
| 20 | 0.0815 ∠−70.0° | **0.139 ∠−70.0°** | 1.761 ∠−65.0° | 7.9 % |
| 25 | 0.066 ∠−74.0° | **0.112 ∠−74.0°** | 1.488 ∠−70.2° | 7.5 % |

- [E] The candidate sits at **the same phase as the lane that ground on car**, within 5°. The kit measured that lane on the wire at ∠−69° at 20 Hz (V280r2/V282 era; `docs/research/GRINDING-DEEP-ANALYSIS-2026-09-03.md` §2).
- It is **1/12 of the gain**. D2's 10 % gain clause does not fire; the maximum is 8.7 %.

**Delay sweep** (collocated stress modes, exact ZOH, ζ open / V294 / b964):
- **At τ = 0–2 ms the trim damps**, as the page says.
- **From about 4 ms it removes damping:**

  | mode, speed | delay | open | V294 | b964 |
  |---|---|---|---|---|
  | mode20, 5 m/s | 6 ms | .075 | .073 | .072 |
  | mode20_lo, 5 m/s | 6 ms | .119 | .114 | .109 |
  | mode20_lo, 5 m/s | 12 ms | .119 | .104 | .094 |
  | mode16_lo, 5 m/s | 12 ms | .139 | .124 | .112 |
  | `lb_mode20_lo` | 8 ms | .050 | .040 | .033 |

- At 25 m/s it keeps damping at every delay.
- [E, model] b964's excess anti-damping is always 0.7 × V294's, because the dose is linear.

**Calibration to the car.**
- The on-car record: V282 engaged ζ **0.016** [0.013, 0.022] at 20 Hz, with the loop-open ζ ≥ 0.05 (memory `accord-with-the-loop-open-there-is-no-18-22hz-object`).
- The same model makes V282 de-damp mode20 to 0.016–0.025 only at these delays:
  - **τ = 5 ms** at 5 m/s;
  - **τ = 10–12 ms** at 12 m/s;
  - mode20_lo at 12 m/s, **6 ms**;
  - mode16_lo at 12 m/s, **7 ms**.
- **At 2 ms, the page's stress setting, the same model leaves V282 at ζ 0.073 ≈ open.** So the 2 ms stress model contradicts the one on-car fact it can be checked against.
- At the calibrated delays [B, model calibrated to one on-car number]:

  | case | V294 Δζ vs open | b964 Δζ vs open | b964 − V294 |
  |---|---|---|---|
  | mode20 | −0.0007 … −0.0024 | −0.0014 … −0.0042 | **−0.0006 … −0.0018** |
  | mode20_lo, 12 m/s | | | +0.0003 |
  | mode16_lo, 12 m/s | | | +0.009 |

**Second method: extrapolating the on-car ζ-vs-Kp strata.**
- The strata: 0.033 / 0.030 / 0.018 at Kp 280 / 385 / 575 (MODE-NATURE recensus).
- Those strata sit at |(P+D)/x| 46.1 / 50.8 / 61.0, at nearly the trim's own pre-lag phase (+8° to −10°, against +5.8°).
- A linear fit gives ζ = 0.081 − 0.00103·|P/x|. The intercept, 0.081, is consistent with the ≥ 0.05 bound.
- Effect of the trim: **V294 −0.0021, b964 −0.0036** [B: linear-in-gain extrapolation over ×13].

**Worlds the record excludes [B].**
- In `lb_mode20_lo` and `mode20_r08`, V282's lane is linearly **unstable** at every delay ≥ 1–2 ms.
- On car V282 rang without saturating: clamp binding was 0.0 % at the measured ring amplitudes [E, record]. So those worlds are inconsistent with V282, unless the r24 lane (5244 on V282, not modelled here, damps 20 Hz) rescued them.
- In those worlds b964's 20 Hz line rises +1 to +2.2 dB (10–30 Hz rate ×1.08–1.18, `a4c_out.txt`).

**Reading.**
- The page's §6 point 2 ("adds ζ to every stress mode") is **wrong on the delay the car actually has**, as far as one on-car number can pin it.
- The honest statement is: **b964 removes about 0.001–0.004 of 20 Hz ζ, V294 about 0.001–0.002, against the ~0.03–0.06 V282 removed.** That is still a wide margin. The claim changes; the verdict does not.

## 4. (c) The outer loop with the unchanged fork law: better everywhere, a small phase-margin cost at low speed

Source: `adv-stability/a3_outer.py` and `a3_outer_out.txt`. [E, model; B, car]

The linearisation is my own:
- inner closed loop → FF path → 100 Hz ZOH → pipe 12/22/42/62 ms;
- r1 law: Kp 0.9, Ki 0.3, LAF 14, low-speed factor, relay slope friction·LAF/0.30;
- VM constants from the fork's own VehicleModel, and steerRatio 16.84.

Check: at DC, L_o has a positive real part (negative feedback).

**Anchors.** `light_b` at 26.9 m/s, 22 ms, relay on:

| | GM | Ms |
|---|---|---|
| V294 | **1.68** | 3.11 |
| b964 | **2.49** | 2.07 |

The page gives 1.68 → 2.51 and 3.07 → 2.05.

**Results:**
- **GM ratio b964/V294 is 1.027–1.73 in every one of 728 rows** (13 members × 7 speeds × 4 pipes × relay off/on).
- **Low-speed-factor region** (3.1–5 m/s), identified family:
  - PM drops **2–6.4°**, from 74.6–138° to 70.2–138°. The worst is `b_lo` at 5 m/s with a 62 ms pipe: 89.0 → 82.6.
  - Ms changes by ±0.02, and the Ms peak moves down, e.g. 1.23 → 1.07 Hz at 3.1 m/s.
  - This is the inertia cost, in the outer loop.
  - On `light_b` the same region gains PM and Ms falls.
- **The D3 "Ms +10 %" sub-clause fired literally in 4 rows:**
  - `lb_J2.5` at 22 and 26.9 m/s;
  - `lb_b0.5` at 26.9 m/s;
  - all with a 42–62 ms pipe and the relay on.

  In each of them V294 is **linearly unstable** (GM 0.68–0.85) and b964 raises the GM to 0.88–1.16. The Ms of an unstable loop is not a margin.
- **The GM < 1.5 flags** are all rows where V294 is lower still.
- **I adjudicate D3 as not fired.** It is disclosed because it fired as written.
- **Relay describing function.**
  - The worst relay factor is always the full small-signal slope (n = 1), so there is no amplitude-dependent crossing that V294 lacks.
  - A limit cycle is predicted only on `lb_J2.5` at 26.9 m/s with a 62 ms pipe, where V294 is worse (GMmin 0.68 against 0.88).

**Closed-loop replay (harness mode B)** with the bit-verified fork port, on the members **the designer did not run in mode B**: tau9, J_0.3, mode13, mode20 and mode20_lo, plus nominal, light_b, tau6 and b_lo. Source: `a6_modeB_out.txt`.
- The 1–5 Hz limit-cycle prominence **falls** on every member:
  - lp −0.5 to −1.6 dB;
  - full −0.6 to −4.7 dB.
- On `light_b` full, the line's rms rises 3.51 → 3.91, i.e. +0.95 dB, just under D3's 1 dB, as it moves from 1.27 to 1.07 Hz. This is the low-frequency inertia shift. Its prominence falls 4.7 dB.
- The 12–26 Hz line changes by −0.7 to +1.4 dB. No new line appears.
  - The +1.4 dB is `tau6` under lp, where the argmax moved to a weak 20.1 Hz line (+1.2 dB prominence; rms 0.126 → 0.127).
  - Every other member is within ±0.9 dB.

**My own nonlinear loop** (`a4_nl_out.txt`, `a4d_out.txt`):
- **Scenarios.** On-centre HOLD at 3.1–26.9 m/s, and hard turns at 8 / 12 / 17 / 20 m/s with lateral acceleration 2–3 m/s².
- **Hard turns.** b964 lowers the 1–5 Hz line everywhere.
- **The one +4.7 dB 3.61 Hz reading** was on one seed and one build per member. Over 4 seeds it shows no b964 excess: mixed sign within ±2.6 dB, all ≤ +1.7 dB on both builds.

## 5. (d) Nonlinear traps: none found

| trap | V294 | b964 | source |
|---|---|---|---|
| fb clamp C binding, r71b engaged | 0 % | 0.0029 % | [E] byte-exact replay, `a5_replay_out.txt` |
| fb clamp C binding, my hard turns and holds | 0 % | 0 % | [B] sim |
| b1701 (G3), for scale | | 0.137 % | [E] |
| P clamp binding, r71b | 0.057 % | 0.051 % | [E] |
| rail | 0 % | 0 % | [E] |
| max \|T\| on r71b | 1467 | 1311 | [E] the trim damps the peak |
| b964 − V294 torque on r71b's own inputs | | 9.9 T rms, p99 50, max 142 | [E] 17 T rms at 0–5 m/s, 2 T at 22+ |
| int32 (bounded input, \|x\| ≤ 12000) | 4.06 | 2.39 | [E]; on r71b the largest a·s is 3.6e8, a margin of 5.9 even at G3 |
| restart pulse | 420 | 544 ≤ 615 | [E]; needs a bail at \|x\| > 12000, which is unreachable [B] |
| 100 Hz staircase, no road or x noise, 5–30 Hz torque | | ×0.98–1.14; 30–120 Hz unchanged | [B] `a4d_out.txt` |
| stick-slip (dwell-then-jump), 8 paired seeds at 3.1 and 5 m/s | | fewer or equal on every member; paired mean −0.25 … −3.6 per minute, jump peaks lower | [B] `a4b_out.txt` |

Notes on the table:
- **Stick-slip.** A single-seed run had read `light_b` 2 → 9 at 3.1 m/s. With 8 seeds the mean is 12.0 → 10.0 (7 of 8 seeds lower). The single seed was noise.
- **Phantom momentum.** The torque change in the 60 ms after a stick rises 1–4 T on b964, below every member's Fs.
- The harness's rule that simulated dwell counts are set by the noise model applies. Only the paired sign is read here.

## 6. (e) Does it move the complaints and the goal metric across the family?

**"Jerky on hard turns at medium speed": yes at 5–10 m/s, on every member.** [B, sim counterfactual]

| source | members | 5–10 m/s | 15–22 m/s |
|---|---|---|---|
| mode B lp | 9 | ×0.81–0.88 (light_b 0.73) | ×0.92–**1.07** (mode20_lo 1.07, mode13 1.02, J_0.3 1.00) |
| mode B full | 9 | ×0.83–0.87 (light_b 0.75) | ×0.92–0.95 (light_b 0.74) |
| my nonlinear hard turns, 8 m/s | | ×0.73–0.90 | |
| my nonlinear hard turns, 12 / 17 / 20 m/s | | ×0.67–0.96 | |

**The page's 15–22 m/s claim is not family-robust under lp** (×0.92–1.07). Quote it for full and for the prior only.

**The two "loose" complaints: not reached, as the page says.** [B]
- Tracking gain, turn-hold, straight delivery and integrator share move by ≤ ±0.015 on every member. The ±0.015 is `light_b` straight delivery at 22+ m/s under lp.

**Low-speed cost, as the page says, and near my ×1.20 bound:**
- 0.3–1 Hz wheel rate at 0–5 m/s: ×1.18 (lp) and ×1.19 (full) on `light_b`, ×1.03–1.08 on the rest.
- J_err at 0–5 m/s (lp): ×1.04–1.12.
- Plus the outer-loop phase-margin loss of 2–6° at 3–5 m/s (§4).

**The cmd → α goal metric** [E, model closed form; B, car] (`a7_goal_out.txt`):
- Flatness over 0.5–3 Hz, phase spread and the best-flat-gain error all **improve on 65 of 65** member-speeds.
- The flat-gain error goes from 0.360–0.644 to 0.307–0.582, a median of −0.025.
- The improvement comes from lowering the 1–3 Hz response (×0.74–0.96). The 0.3–0.5 Hz response goes ×0.98–1.08.
- The direction is robust; the size is small. That matches the page.

## 7. Required changes (to the page and the wire read; the cell value can stand)

1. **Rewrite the 13–25 Hz damping claim** (§0 bottom line, §4 "the trim never reduces … ζ", §6 point 2, §6 table rows 3–5):
   - The trim's damping sign at 13–20 Hz depends on the delay after the tap.
   - Calibrated to V282's on-car ζ, it is **weakly anti-damping** at 20 Hz on low-speed modes.
   - b964 removes about 0.001–0.004 of ζ, V294 about 0.001–0.002.
   - The stress-member table at 2 ms is not validated by the record: at 2 ms the same model says V282 did not de-damp.
   - Keep the conclusion: 1/12 of V282's gain at the same phase.
2. **Restate the worst-case margins over the wider set:**
   - inner Ms 1.35 at ×1.5 delay and 1.51 at ×3 (`lb_mode20_lo`);
   - inner GM_min 3.5;
   - worst F5-HF band **×1.48** (`tau9`, 13–17 Hz, dist full), not ×1.45. That is 0.02 inside the page's own pre-registered ×1.5 clause.
3. **Limit the 15–22 m/s hard-turn improvement claim to dist full and the prior.** Under lp across 9 members it spans ×0.92–1.07.
4. **Add the outer-loop phase-margin loss of 2–6° at 3–5 m/s** to the stated low-speed risk.
5. **Make the revert signature quantitative for the one thing the model cannot settle.**
   - Read the demand-gated (idx ≥ 20) 18–22 Hz and 15–17 Hz census on the 0x18F rate against r71b.
   - Predicted: no new line, and 10–30 Hz rate rms ×0.96–1.18 [B, the harshest stress world].
   - A new line, or any rise > 3 dB, means revert to V294.

## 8. Not covered, or limits

- Nothing above ~8 Hz is identified. Every HF statement rests on stress members plus one on-car calibration number.
- The r24 lane (2048 on V294 and b964; 5244 on V282) is not modelled. On the record it damps 20 Hz. My calibrated delays for V282 are therefore upper-leaning, and the true anti-damping share may be smaller.
- My fork in the nonlinear simulations is a simplified r1 law: no roll, offset, delay-compensation buffer or jerk low-pass. The mode-B replays use the harness's bit-verified port.
- Interlocks (EME, lockstep, DTC) are another adversary's surface and are not covered here.
- My pre-registered D2 second clause ("b964 − V294 exceeds V294 − open") **cannot fire for a pure linear dose of ×1.7**, since the increment is always 0.7 × V294's. That is a defect in my criterion. I report the sign finding under its first clause instead of hiding it.

## 9. Files (`analysis-2020accord/studies/v295/design/trim-ratio/adv-stability/`)

| file | contents |
|---|---|
| `CRITERIA-ADV-stability.md` | pre-registered FAIL criteria |
| `adv_lib.py` | my cell reader, IntLane, lane FRF, exact-ZOH closed loop, return ratio, margins |
| `a0_spot.py` / `_out.txt` | R1–R4, golden and harness lane controls, FRF vs harness |
| `a1_inner.py` / `_out.txt` / `.json` | (a) family × delay × J × b × window; R5 |
| `a2_hf.py` / `_out.txt` | (b) gain and phase against V282, delay sweep, V282 calibration, strata extrapolation |
| `a3_outer.py` / `_out.txt` | (c) outer loop, relay describing function |
| `a4_nl.py`, `a4_core.py` / `a4_nl_out.txt` / `.json` | (c)/(d) my nonlinear loop: holds, hard turns, creep |
| `a4b_stickslip.py` / `a4b_out.txt` | 8-seed paired stick-slip |
| `a4c_hf.py` / `a4c_out.txt` | 10–30 Hz rate lines on flexible members at 2 / 6 / 9 ms |
| `a4d_check.py` / `a4d_out.txt` | 3.61 Hz line over seeds, FF identity, staircase isolation |
| `a5_replay.py` / `_out.txt` | byte-exact r71b replay: R3, clamps, int32 |
| `a6_modeB.py` / `_out.txt` / `.json` | harness mode B on the members the designer did not run, plus the spot-check row |
| `a7_goal.py` / `_out.txt` | cmd → α closed form on 65 member-speeds |
