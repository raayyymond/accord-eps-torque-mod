# SCORE-FREQ — common frequency-domain scoring of the angle-loop design panel (2026-10-01)

**Status: ANALYSIS ONLY.** Nothing built, flashed or sent; the fork was not touched. Ghidra was not needed (every
byte/cal spec was taken from the designers' own scripts and the task brief; the image cals used are the ones
`lane_mirror_v295`/`ds_model` read LE from the V295 image, sha asserted on import).

**Author:** the orchestrator's **common frequency-domain scorer** (`main`). Designers do not grade their own work: every
candidate is re-derived from its byte/cal spec and run through ONE identical pipeline — the same controller-FRF
primitives, the same plant family and credible member set, the same speed grid, the same hold ages, and the **same
metrics extractor**. Script: `analysis-2020accord/studies/angle_loop/panel/score_freq.py`
(caches `_scratch/angle_loop/panel/score_freq_*.json`). Run this session.

---

## 1. The pipeline (identical for all 16 real candidates + the 3 references)

- **Controller FRF** built here from the lane bytes/cals. The angle-kind controller (P+I on the held/fresh angle
  operand, D on held-rate / fresh-EMA-rate / fine-accumulator / held-LP / stock-E, optional forward/feedback lead) is a
  re-implementation **validated byte-for-byte equal to `ds_model._ctl_frf` (max|diff| = 0.0e0)** on a held sample, with
  one flag `ds_model` lacked — a **fresh 1 kHz P/I operand** (for CGF-1b). Cascade (D3a/D3b) and the references
  (V295/V294/V282) route through `ds_model.ctl_frf`. **Every candidate and reference then passes through the SAME
  extractor** (`metrics_from`): PM = min over every |L|=1 crossing, LTI GM at the −180° crossing, Ms, |T_c|/|T_ref|
  5–30 dB, M20, L20, Re(T/ω), |T_ref| 1.6–3 Hz, turn-hold |T_ref(0.05 Hz)|, 0.1–1 Hz tracking.
- **Plant + credible set:** `ds_gate2.member` = the brief's full factorial (`c1r2_members` damping×inertia×delay×age)
  **plus `mode13`/`mode20`** (collocated two-mass 13 Hz ζ0.1 / 20 Hz ζ0.05) and `ms_free`, exactly the single corners
  the brief enumerates. Speeds: `ds_gate2.GRID` = **1.0–35.0 m/s at 0.25 m/s incl. the plant knots** (3.1/8/11.9/17/26.9).
  Hold ages **{0, 10}** (= holds 1–10 and 11–20 ticks) on every member via `+h10`.
- **Image cals (EVIDENCE):** OA 992, OB 507, FWD 5346/32768, FADE 254/256; **gp-0x6abe EMA α = 37/128 = 54.3 Hz**
  (cal 0xC643C, FUN_00041464), gp-0x6abe −4.712 counts/deg·s, gp-0x6cc4 −278.5 counts/deg.
- **Validation (printed by the script):** angle held FRF == ds_model (0.0e0); V295 PM/M20 extractor == ds_model.metrics;
  **B1 nominal@26.9 PM 67.6° reproduces the B-designer's gate_B1 67.5°.** Exact 10-tick monodromy (stab_lin) spot-check:
  every binding point is **stable (ρ<1)** — e.g. B1 ms_free@11.9 ρ 0.992 (pole 0.81 Hz ζ0.16), b_q·J1.0+h10@26.9 ρ 0.979
  (pole 1.74 Hz ζ0.19). Low PM here means **low margin, not instability.**

### Convention notes (EVIDENCE/BELIEF — these move absolute numbers, not the ranking)
- **Rate model = the firmware EMA (α 37/128, 54.3 Hz)** for every D and for V295's own rate operand. This is the
  firmware-correct model (gp-0x6a56 = −1.698·gp-0x6abe, gp-0x6abe = EMA). Consequence: **V295's own Re(T/ω)₂₀ = −0.823**
  here (not the −0.633 the B-designer hard-coded from an ideal-differentiator convention), and **M20(V295) = 3.384**
  (record convention 3.85 / design 3.58). Because every candidate is compared to V295 **through the same engine**, the
  ratios (`×V295`) are the valid reading; absolute M20/Re differ from a designer who used a different rate model.
- **B2 was scored with the firmware EMA (54.3 Hz)**, not the 40 Hz EMA the B-designer's `b_lib` used — a correction, not
  a disagreement with the structure.
- **CGF-2 ≡ CGF-1 in the frequency domain.** Its only addition is a time-domain friction feed-forward (a dead-zone
  break); its small-signal linear effect is a near-unity proportional term swamped by Kp. The FF must be judged in the
  time domain, not here.

---

## 2. THE TABLE (one row per candidate, identical columns; full 0.25 m/s grid, ages 0 & 10)

PM in degrees. `minPMsingle` = min over tier-A single corners **incl. mode13/mode20/ms_free** (the brief's set).
`binding` = the combined (tier-B) member/speed with the least PM, and its crossover (the ring frequency it would
produce). `M20(×V295)` and `L20×` are the 20 Hz loop-gain measures vs V295 (both ≤1 = at/under V295). `ReTw13/16/20` =
controller-only Re(T/ω) at hold age 0 (T counts/deg·s, **>0 damps, <0 removes damping from a collocated mode**;
V295 = −0.47/−0.73/−0.82, V294 = −0.25/−0.39/−0.45, V282 = −3.50/−6.78/−8.88). `ReTw20@age10(×V295)` = the aged 20 Hz
anti-damping vs V295 aged. `turnhold` = |T_ref(0.05 Hz)| worst ≥8 m/s (goal ≥0.90). `DCstiff` = DC torque stiffness
(inf = integrator present). `dPM(age)` = PM loss from aging the hold 0→10 on the combined set. **GATE2 fails** = count
over the whole gated grid (tier-A PM<45, tier-B PM<30, GM<6, |T|5-30>+3 dB, M20>V295, L20>V295).

| cand | minPMnom | minPMsingle | minPMcomb | binding(member@v fc) | fcRange(nom,Hz) | peak5-30dB | M20(x V295) | L20x | ReTw13 | ReTw16 | ReTw20 | ReTw20@age10(x V295) | Tr1.6-3 | turnhold>=8 | trk0.1-1 | DCstiff | dPM(age) | GATE2 fails |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1-zero-cave | 82.9 | 44.8 | 34.1 | b_q*J1.0+h10@15.50 fc~1.59Hz | 0.16-1.80 | -4.6 | 1.81 (0.53) | 0.67 | -0.53 | -0.54 | -0.51 | -0.61 (0.69) | 0.69 | 0.88 | 0.32-0.97 | inf(I) | 5.7 | 1 |
| A2-ki-cave | 66.5 | 38.3 | 35.7 | ms_free+h10@11.90 fc~0.73Hz | 0.30-1.18 | -5.8 | 1.78 (0.53) | 0.66 | -0.48 | -0.52 | -0.49 | -0.62 (0.69) | 0.65 | 0.99 | 0.30-1.07 | inf(I) | 10.7 | 3 |
| B1-robust-gaincut | 67.6 | 34.1 | 31.3 | ms_free+h10@11.90 fc~0.78Hz | 0.38-1.73 | -3.9 | 2.24 (0.66) | 0.70 | -0.60 | -0.65 | -0.62 | -0.62 (0.69) | 0.87 | 1.00 | 0.38-1.11 | inf(I) | 9.1 | 13 |
| B2-freshD-lead | 68.2 | 30.9 | 28.1 | ms_free+h10@11.90 fc~0.82Hz | 0.43-1.91 | -4.3 | 2.73 (0.81) | 0.81 | -0.14 | -0.25 | -0.31 | -0.58 (0.65) | 0.90 | 1.00 | 0.42-1.12 | inf(I) | 10.8 | 18 |
| B3-noI-forkDC | 63.4 | 46.5 | 32.3 | b_lo*tau6+h10@1.00 fc~2.81Hz | 0.09-2.44 | -1.7 | 2.29 (0.68) | 0.73 | -0.68 | -0.70 | -0.65 | -0.61 (0.68) | 0.87 | 0.46 | 0.34-0.80 | 177 | 7.9 | 0 |
| CGF-1 | 69.0 | 21.2 | 17.8 | ms_free+h10@11.90 fc~0.92Hz | 0.52-2.12 | -2.3 | 3.19 (0.94) | 0.94 | -0.19 | -0.30 | -0.37 | -0.67 (0.75) | 0.89 | 1.00 | 0.51-1.15 | inf(I) | 15.0 | 35 |
| CGF-2 | 69.0 | 21.2 | 17.8 | ms_free+h10@11.90 fc~0.92Hz | 0.52-2.12 | -2.3 | 3.19 (0.94) | 0.94 | -0.19 | -0.30 | -0.37 | -0.67 (0.75) | 0.89 | 1.00 | 0.51-1.15 | inf(I) | 15.0 | 35 |
| CGF-1b | 70.6 | 23.0 | 23.0 | ms_free+h10@11.90 fc~0.93Hz | 0.52-2.25 | -1.7 | 3.40 (1.00) | 1.04 | -0.21 | -0.33 | -0.41 | -0.92 (1.03) | 0.85 | 1.00 | 0.50-1.14 | inf(I) | 11.7 | 4760 |
| B0r | 64.8 | 47.0 | 32.1 | b_lo*J_hi+h10@1.00 fc~1.44Hz | 0.42-1.86 | -3.7 | 2.24 (0.66) | 0.70 | -0.58 | -0.63 | -0.61 | -0.62 (0.69) | 0.96 | 1.00 | 0.38-1.11 | inf(I) | 5.2 | 0 |
| D1a | 69.9 | 48.1 | 31.6 | b_q*J1.0+h10@15.50 fc~1.63Hz | 0.37-1.89 | -1.4 | 1.33 (0.39) | 0.92 | -0.30 | -0.33 | -0.33 | -0.92 (1.03) | 0.91 | 1.00 | 0.28-1.04 | inf(I) | 5.9 | 0 |
| D1b | 64.5 | 46.3 | 32.0 | b_lo*J_hi+h10@1.00 fc~1.39Hz | 0.43-1.88 | -6.2 | 2.40 (0.71) | 0.71 | +0.08 | -0.02 | -0.09 | -0.39 (0.44) | 1.01 | 1.00 | 0.38-1.11 | inf(I) | 4.9 | 0 |
| D1c | 65.0 | 47.4 | 32.4 | b_lo*J_hi+h10@1.00 fc~1.45Hz | 0.41-1.90 | -2.5 | 1.81 (0.53) | 0.61 | -0.80 | -0.73 | -0.57 | -0.33 (0.37) | 0.94 | 1.00 | 0.38-1.11 | inf(I) | 5.2 | 0 |
| D2a | 64.9 | 46.7 | 32.6 | b_lo*J_hi+h10@1.00 fc~1.38Hz | 0.43-1.90 | -5.6 | 2.28 (0.67) | 0.68 | -0.11 | -0.20 | -0.25 | -0.49 (0.55) | 1.00 | 1.00 | 0.38-1.11 | inf(I) | 4.8 | 0 |
| D2b | 65.6 | 47.8 | 32.1 | b_lo*J_hi+h10@1.00 fc~1.62Hz | 0.45-2.40 | -1.4 | 2.29 (0.68) | 0.69 | -0.21 | -0.27 | -0.30 | -0.47 (0.53) | 1.02 | 1.00 | 0.39-1.11 | inf(I) | 5.1 | 0 |
| D2c | 65.4 | 47.2 | 32.2 | b_lo*J_hi+h10@1.00 fc~1.63Hz | 0.45-2.37 | -1.8 | 2.29 (0.68) | 0.68 | -0.21 | -0.27 | -0.30 | -0.47 (0.53) | 0.99 | 1.00 | 0.39-1.09 | inf(I) | 4.5 | 0 |
| D3a | 71.0 | 47.2 | 32.4 | b_q*J1.0+h10@15.75 fc~1.67Hz | 0.36-1.87 | -0.7 | 1.75 (0.52) | 0.61 | -1.01 | -0.80 | -0.51 | -0.11 (0.13) | 0.59 | 0.99 | 0.28-1.03 | inf(I) | 6.0 | 0 |
| D3b | 65.2 | 47.6 | 32.6 | b_q*J1.0+h10@15.50 fc~1.74Hz | 0.36-2.60 | +0.2 | 2.07 (0.61) | 0.69 | -0.89 | -0.79 | -0.62 | -0.56 (0.63) | 0.76 | 0.97 | 0.37-0.99 | inf(I) | 2.5 | 0 |
| E-none-1 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| E-none-2 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

---

## 3. The decisive finding: the member set, not the engine, decides GATE 2

**Every GATE-2 fail traces to `ms_free` (J≈2.08 at ~11.75–12.5 m/s), a tier-A single corner the brief enumerates but the
A/B/CGF designers never gated** (it is REPORT-only in their `c1r2_members` module; the D-structure module and the brief
put it in tier A at PM≥45). `mode13`/`mode20` pass for **every** candidate (≥63°) — the two-mass plant modes are a
non-issue. So the fail counts split cleanly into two readings:

| candidate | GATE2 fails **with ms_free** (brief literal) | GATE2 fails **without ms_free** | tier-A min PM excl. modes/ms_free |
|---|---|---|---|
| A1 | 1 (ms_free@11.9, 44.8°) | **0** | 65.1 (b_lo@7.75) |
| A2 | 3 (ms_free) | **0** | 56.5 (J_hi@3) |
| B1 | 13 (ms_free) | **0** | 52.1 (J_hi@3) |
| B2 | 18 (ms_free) | **0** | 54.1 (J_hi@3) |
| B3 | **0** | **0** | 46.5 (b_lo@3) |
| CGF-1 / CGF-2 | 35 | **7** (b_q·J1.0+h10, PM 28–29) | 56.0 (J_hi@3) |
| CGF-1b | 4760 | **≈full grid** (nominal L20/M20 > V295) | 58.5 (J_hi@3) |
| B0r, D1a, D1b, D1c, D2a, D2b, D2c, D3a, D3b | **0** | **0** | 46.3–48.1 |

**Why.** The A/B/CGF tables were fit under an envelope that **excludes** ms_free, so they run higher Kp_eff at ~12 m/s
(B1 G699→Kp_eff 306) than the D-structure tables fit **under** it (D2a G537→Kp_eff 235, −23 %). On the brief's literal
set, that extra 12 m/s gain fails ms_free's PM≥45. `ms_free`'s J 2.08 sits **above** the plant note's "J up to 1.3 is
not excluded" bound, so the reader may reasonably treat it as report-only — in which case **A1/A2/B1/B2 become 0-fail**
and only CGF's goal-first high-gain concession (b_q·J1.0, and CGF-1b's 20 Hz-ceiling breach) survives. **Both columns are
reported; the ranking does not depend on which you pick, except that it is the whole of A/B's GATE-2 story.**

---

## 4. Per-candidate verdict (frequency domain only)

- **B3, B0r, D1a, D1b, D1c, D2a, D2b, D2c, D3a, D3b — 0 GATE-2 fails on the brief's full set.** They were fit under the
  ms_free-inclusive envelope. Of these the turn-hold separates them: **B3 0.46 and D3a 0.59 FAIL the goal's turn-hold
  (≥0.90)** (no firmware integrator / cascade DC leak — their own designers flagged B3's 0.46); **D3b 0.76** also short;
  the rest (B0r/D1a/D1b/D1c/D2a/D2b/D2c) hold **≥0.94**.
- **Fresh-rate-D candidates (B2, CGF-1, D2a, D1b) are materially better at 13–16 Hz** than held-rate-D: ReTw13 −0.09…−0.19
  vs held −0.53…−0.80 (D1b actually **+0.08**, damping). This is the real, reproducible payoff of reading the 1 kHz rate —
  it removes the teen-Hz anti-damping that is C1 rev 2's declared miss. All candidates stay **under V295 at 20 Hz age 0**.
- **Aged 20 Hz (ReTw20@age10) exceeds V295 for two:** **D1a (×1.03)** (cal-only D-on-E′ differentiates the aged held
  error) and **CGF-1b (×1.03)** (fresh operand). A flag, not a hard fail of the written rule (which reads age 0), but it
  violates the brief's "Re(T/ω)₂₀ ≤ V295 at hold age 0 AND 10." D1b is best aged (×0.44).
- **CGF-1b breaks the 20 Hz / L20 ceiling across the whole grid** (M20 1.00×, L20 1.04× V295, 4760 fails incl. nominal).
  As specified (CGF-1's table + a fresh 1 kHz P/I operand) it is **not** at/under V295's 20 Hz gain — the fresh operand
  lifts the whole loop. It needs its own, lower table before it can be scored as a contender.
- **A1** is the smallest (0 cave) and passes everything except ms_free (44.8°, 0.2° under), but its **turn-hold 0.88 and
  0.1–1 Hz tracking 0.32–0.97** confirm the flat-Ki highway-looseness miss its designer declared. **A2** buys turn-hold
  back to 0.99.
- **Peak 5–30 Hz closed-loop |T|** is ≤ +0.2 dB for every candidate (D3b +0.2, D3a −0.7) — no candidate creates a
  5–30 Hz resonance; the +3 dB bar is met by all.

---

## 5. Disagreements with the designers' own claims (re-run, cause found)

1. **A/B/CGF "0 GATE-2 fails / comfortable tier-A" vs my fails.** Cause: **member set.** They gated `c1r2_members`
   (ms_free/mode13/mode20 excluded from gating); the brief and the D-structure module gate ms_free at PM≥45. On the
   shared members they agree (B1 nominal@26.9 = 67.6° reproduces their 67.5°). On the brief's literal set, ms_free@12
   is the binding tier-A fail for all of them. **Recorded as the headline.**
2. **B-designer min tier-B PM 31.7° vs my 31.3° (B1).** Cause: the B-designer's binding was `b_lo·J1.0·tau6+h10` (in
   their broader factorial, NOT in the brief's enumerated combined set); on the brief's combined set my binding is
   `ms_free+h10@11.9` (31.3°) and, excluding ms_free, `b_q·J1.0+h10@26.9` (34.7°). Different member, same engine.
3. **B-designer Re(T/ω)₂₀ V295 = −0.633 (0.92× etc.) vs my −0.823.** Cause: **rate model.** They used an ideal
   differentiator for V295; the firmware rate goes through the 37/128 EMA + 100 Hz hold. My numbers use the EVIDENCE EMA
   for both V295 and the candidate, so the ratios are consistent; their absolute −0.633 is a convention artifact.
4. **CGF "whole credible set gated PM≥30, only b_q·J≈1.0 conceded."** Partly confirmed, partly not: on the brief's set
   **excluding ms_free**, CGF-1 concedes exactly `b_q·J1.0+h10` (7 points, PM 28–29°, stable) — matches. **Including
   ms_free**, CGF-1 adds 28 ms_free fails (down to 17.8°) — CGF ran the highest highway Kp of the panel and did not gate
   ms_free, so it concedes far more than its page claims on the brief's literal set.
5. **CGF-1b "+15–20 % highway gain, M20 stays ≤ V295."** **Not reproduced.** With the fresh 1 kHz operand on CGF-1's
   table, M20 = 1.00× and L20 = 1.04× V295 — the 20 Hz gain is **not** held at/under V295; it fails L20/M20 across the
   grid. The designer's own note ("the higher-gain variant may push the table up") concedes the table must change; as
   written it breaches the ceiling everywhere.
6. **B2 scored at the firmware EMA (54.3 Hz), not b_lib's 40 Hz.** Minor: shifts B2's teen-Hz ReTw slightly; does not
   change its verdict (fresh-D benefit at 13 Hz holds, ms_free binds tier A).

---

## 6. Reproduce

```
cd analysis-2020accord/studies/angle_loop/panel
C1_VARIANT=r2 python score_freq.py          # full run (~7 min); writes _scratch/.../score_freq_{summary,refs,table}.{json,md}
C1_VARIANT=r2 python score_freq.py quick    # headline members only (~5 s), prints the validation block
```
The validation block must print `VALIDATE PASS` (angle FRF == ds_model 0.0e0; V295 extractor == ds_model.metrics;
B1 nominal@26.9 = 67.6°).
