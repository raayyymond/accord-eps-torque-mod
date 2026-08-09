---
name: reference_accord_path1_path2_structural_decoupling_and_damping_dose_tables
description: FUN_00028ea6 (0xC6CD0's 4x LKAS gain home) has ZERO reads of gp-0x6b98 -- Path 1 cannot be part of Path 2's closed-loop denominator/Q, only its excitation amplitude. Full dose tables for 0xC646E/0xC63AC/0xC40D8 at 7.79Hz vs 1-4Hz driver-band cost.
metadata:
  type: reference
---

**2026-08-09, `DAMPFIX` task (team-lead brief: authority-preserving damping at 7.6-7.8Hz without lowering
LKAS gain).** Full report sent to team-lead via SendMessage; durable facts below.

## [EVIDENCE, fresh `search_instructions`] Path 1 (0xC6CD0, 4x LKAS fwd gain) cannot set Path 2's Q
`search_instructions(function="FUN_00028ea6", operand_pattern="6b98")` → **0 matches, 1874 instructions
scanned in scope**. `FUN_00028ea6` (home of `0xC6CD0` per [[reference_accord_c646c_gain_feedback_vs_forward_classification]])
never reads `gp-0x6b98` (delivered motor command) anywhere. Path 1 and Path 2 meet ONLY as additive,
exogenous inputs at the SAME summing points (`gp-0x6b4c` is one of 11 terms in `FUN_0003aa2c`'s aggregator
AND one of 6 terms in `FUN_00038148`'s stage-1 composite, weight `0xC63A2..AA`=1024=unity, byte-confirmed
unchanged on stock/V85/V86/V86B). ⇒ **Path 2's closed-loop poles (Q, frequency) are set entirely by cals
living inside Path 2 itself (`0xC40D4`/`0xC40D8`/`0xC63A0-AE`/`0xC646E`/`FUN_0003a382`'s PID) — 0xC6CD0/
0xC646C appear only as numerator/excitation terms, never in the denominator.** This means a Path-2-only
damping edit is structurally authority-preserving, not merely an acceptable trade — and reframes any prior
"4x gain inflated Q from 5 to 20" belief as unproven: the 4x scales excitation amplitude into a mode whose
Q was already set elsewhere, it doesn't set the Q itself.

## [EVIDENCE, fresh `decompile_function(0x3b8f6)`] Full FUN_0003b8f6 arithmetic, byte-exact
Confirms and refines `docs/STATE.md`'s 2026-08-09 diagram exactly. `model = cmd_branch(EMA2(gp-0x6b98·
polarity/1024, α=0xC40D4)) + clamp(FIR3(EMA2(gp-0x4f60/1024, α=0xC40D8))·0xC613A/32768, ±15)·LERP13(gp-0x6a10)/1024`.
The `±15` clamp is on the sensor branch BEFORE the final `×0xC6468(=2639)` scale — at realistic amplitudes
(gp-0x4f60 near its ±25600 validity ceiling) the sensor branch's contribution to `model` is ~0.88-0.94,
comparable in order of magnitude to the cmd branch at typical `gp-0x6b98` values (~2.0 at 2048 counts) —
**not negligible, just poorly-placed spectrally** (see dose table below). `gp-0x6bfc = clamp(0xC6468·
(model−FRICTION−INERTIA), ±20000)` — final live output tail confirmed: the SIGNED clamped value goes to
`gp-0x6bfc`; a SEPARATE `abs()` of the same value goes to the free diagnostic tap `gp-0x6c00`.

## Dose tables, fresh Python (1kHz discrete EMA, `H(z)=α/(1-(1-α)z⁻¹)`, DC=1 verified numerically for every α)

**`0xC646E` (INERTIA gain, pure magnitude knob, phase fixed by untouched `0xC40D6` α=246/4096 2-pole cascade)**:
vs rate, +14.7°@7.79Hz / −36.2°@21.09Hz / −45.6°@27.4Hz / −46.8°@28.5Hz — real part POSITIVE across the
whole 7.79-28.5Hz symptom band (genuine lagged-velocity damper, never flips sign in-band). Stock=1428 on
stock/V85/V86/V86B (byte-confirmed, never touched by any build). Currently 1-6% of its own ±10 clamp
(prior-session estimate). Illustrative 4x dose (1428→5712, `94 05`→`50 16`) lands at 4-24% of clamp, well
clear of V80's ~97% relay disaster. Single reader/0 writers, cleanest isolation in the estimator block.

**`0xC63AC` (Path-2 stage-1 EMA, single real pole, stock=102/1024, α≈0.0996, corner≈15.85Hz)** — mode-proof,
single reader confirmed 2 independent methods across 2 sessions, never touched:
| cal | α | corner | dB@7.79Hz | °@7.79Hz | °@1Hz | °@2Hz | °@3Hz | °@4Hz |
|---|---|---|---|---|---|---|---|---|
| 102 (stock) | 0.0996 | 15.85Hz | −0.85 | −23.6° | −3.3° | −6.5° | −9.7° | −12.8° |
| 51 (½×) | 0.0498 | 7.93Hz | −2.83 | −42.4° | −6.8° | −13.5° | −19.7° | −25.5° |
| 25 (¼×) | 0.0244 | 3.89Hz | −6.30 | −60.6° | −13.4° | −25.9° | −36.4° | −44.9° |
Same lever CLASS as V86's own `0xC40D4` (573→286, BUILT UNFLASHED, moves Path-2's −180° crossing 7.79→
6.2-6.9Hz per its own pre-registered sweep) — cheaper trade (½× dose costs only −3.6°/−7.0°/−10.1°/−12.7°
incremental driver-band vs V86's much larger driver-band cost at its own tested dose). ⚠ Direction (raise
vs lower) NOT certified — needs the same Q×delay loop-gain sweep V86 ran for 0xC40D4, not yet run for this
cell. Do not stack with V86 before V86's on-car result is in (same lever class, would confound the read).

**`0xC40D8` (sensor-branch EMA, 2-pole cascade, stock=3686/4096) — NOT RECOMMENDED, closes the item cleanly**:
| cal | α | corner/pole | dB@7.79Hz | °@7.79Hz | °@1Hz | °@2Hz | °@3Hz | °@4Hz |
|---|---|---|---|---|---|---|---|---|
| 3686 (stock) | 0.900 | 143.2Hz | −0.003 | −0.6° | −0.1° | −0.2° | −0.2° | −0.3° |
| 512 | 0.125 | 19.9Hz | −1.09 | −37.5° | −5.0° | −10.1° | −15.0° | −19.9° |
| 128 | 0.031 | 5.0Hz | −10.57 | −111.3° | −22.0° | −42.5° | −60.3° | −75.3° |
Reaching ~12dB (a "restore Q≈5 from Q≈20" scale target) needs cal≈100-110, costing 20-45° at 1-4Hz —
matches/exceeds the driver-band objection that already killed this cell for the 21Hz case. **This pole's
stock corner (143Hz/pole) is too far from BOTH 7.79Hz and the 1-4Hz driver band to discriminate between
them — extends the standing NO-GO to 7.6Hz specifically, doesn't just inherit it.**

## Candidate-4 trade curve verdict: flat, not sloped
Given the structural finding above, raising authority (6x, 8x) does not move Path 2's Q on this evidence —
the real gate on raising authority is headroom against Path 2's OWN internal clamps (`gp-0x6bfc` ±20000,
`gp-0x6b70` ±0xC6200=8192, FRICTION/INERTIA ±10 each, aggregator ±25600), not a Q-vs-gain relationship.
V80's own history is the cautionary case: the failure mode when a term saturates is a jump to relay
behavior (Q→∞ effectively), not a graceful Q rise. Not measured against real telemetry this session — the
actual next step is probing `gp-0x6bfc`/`gp-0x6b70` percentile headroom on-car, the same way `0xC40BC`'s
relay saturation was measured before/after its V85 dose.

## Related
[[reference_accord_c646c_gain_feedback_vs_forward_classification]] — 0xC6CD0's sole-site enumeration this
extends with the gp-0x6b98 zero-read check.
[[reference_accord_fun3b8f6_fir_not_biquad_inertia_friction_and_free_taps]],
[[reference_accord_c63ac_second_phase_lag_lever_and_estimator_phase_table]],
[[reference_accord_path2_is_a_real_closed_loop_via_gp6b98_and_0xc63a0_sizing]] — source memories this
session's dose tables and structural argument build directly on.
