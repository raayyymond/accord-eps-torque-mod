---
name: accord-v291-c10-built-fb-pole-10hz-plus-r24-cut-loop-opening-class
description: "🛑🛑⭐⭐⭐⭐⭐ V291 (C10) BUILT 2026-09-13, NOT FLOWN, NOT CLEARED by its adversarial pass (B4 + an ungated 9–18 Hz cost): V282 + 0xC63E8/EA 923/1560 → 962/958 (LKAS feedback lag pole 16.5 → 9.94 Hz, DC 30.89 held) + 0xC6446 5244 → 4725 (r24 engaged arm −9.9 %, a partial revert of V84's Lever B) + 0x14A b3 = sign(fb state gp-0x3d30); 15 bytes vs V282, forward path byte-identical (peak 2505, map ×6). Class: OPEN THE RATE LOOP ABOVE ~8 Hz. Passes all 8 gates with margin; predicted ring ×3.24 shorter, S@20.3 ×0.34, Ms 12–26 19.4 → 3.6 (unfolded) / 4.7–12.3 (r24-folded); 5–9 Hz bump 0.91; |T(3.9)| ×1.07; pkR_w 1.026. Image a66f9c54…, rwd 8ce8d5b7…."
metadata:
  node_type: memory
  type: project
---

Script `analysis-2020accord/builds/v108_plus/build_v291_tva.py` (DOSE C12/C10/C8 × TELEMETRY_BIT b3/b7/off;
writes only with `ACCORD_V291_WRITE=rwd`; 490/490 assertions: 380 substantive / 60 vacuous / 50 tautological).
Exactly one V291 rwd on disk: `…V291-V282BASE-FBPOLE.10HZ.962.958-R24.4725-B3.FBSTATE-…rwd`, sha256
**8ce8d5b7c7cda973a04fbe9a061090c76121b6a136d1bba18d1b67fd24530533**; plain image sha256
**a66f9c54b21031d3948cf1f60fbcadc6ac44d422c01d5a357b19aa0d23144657**. Diff vs V282: 0xC4BAA-AB (b3 rung
`ld.w −0x3680[gp],r6` → `ld.w −0x3d30[gp],r6`), 0xC4FFC CRC, 0xC63E8 (9b → c2), 0xC63EA-EB (1806 → be03),
0xC6446-47 (7c14 → 7512), 0xC6FFC CRC. Design `docs/specs/design/DESIGN-V291-FBLP-2026-09-13.md` (Addenda
B–D), prereg `docs/review/ADVERSARIAL-V291-PREREG-2026-09-13.md`.

**Why this class [EVIDENCE]:** with the loop open there is no 18–22 Hz object
([[accord-with-the-loop-open-there-is-no-18-22hz-object-zeta-open-ge-0-05]]); every in-loop lever at the mode
(notch/lead/fb-pole-UP/Kd/output-lag) returned a null under the authority gates; lowering the fb pole is the
first lever that improves ζ, Ms over the whole 12–26 Hz band, PM, GM, HF noise AND transient authority
simultaneously, and its only block was the 7.3 Hz gate, which the r24 cut removes
([[accord-fb-pole-down-class-does-everything-but-fails-the-7hz-gate-r24-arm-is-the-blocker]]).

**Why C10 and not C12/C8:** C12 (12 Hz, −6 %) cannot observe its own edit (predicted ×2.17 with a 2-SE
interval containing 1); C8 (8 Hz, −14 %) sits at the edge of the extended gates, its 5–9 Hz bump crosses
unity (1.18) and its r24-folded mode lands at 15.6–16.5 Hz — inside the band the operator rejected on V289.
C10: gate 1.0099, pkR_w 1.026, 0/121 unstable, |T(3.9)| 1.071, |ΔL|<5 Hz 18 %, overshoot 0.823 (V282 0.753),
Ms 5–9 0.91 at 9 Hz, ring ×3.24 (f −0.79 Hz), readable at ×2.98 SUB against the ×2.43 floor.

**Telemetry (the instrument for the edit):** CAN 0x14A byte 4 **b3 = 1 iff the fb state s < 0**
(int32 @gp-0x3d30, ld.w, 4-byte aligned, no tear; b7 = sign(gp-0x6b4c) kept — it IS informative; b3 was an
aliased 45–47 transitions/s coin-flip). Read the b3 TRANSITION RATE within-drive against the byte-exact
mirror at both poles: C10 predicts ×0.785 [0.762, 0.805] of the V282-pole prediction on the same 0x18F
trace (duty moves only ×1.07 — do not use it). Positive control: 45+ transitions/s = the re-point did not
land; stuck 0/1 with b5/b6 alive = wrong operand. b5/b6 (|r24| ≥ |aggregator| / |T|) are the r24 cut's own
instrument, byte-identical.

**Pre-registered read (one ~20 s hands-off creep episode):** 18–22 Hz envelope half-peak decay ≈545 →
≈183 ms; T-vs-0x18F-rate cross-spectrum phase −14° at 10 Hz (−12.5° at 7.3 Hz) — the LANDED check (16 s of
creep data). **Null:** decay not below 1.23× V282's while the phase HAS moved ⇒ the object's damping is not
set by the rate loop's return ratio and the whole in-loop class is closed; phase NOT moved ⇒ NO-READ, check
the cells and the gp-0x671d latch. **Revert signatures (whole band):** the 6–9 Hz strong-turn ripple returns
(F7 ≥ 2/100 s or ripple/level ≥ 0.25); a new 15–18 Hz line in trains (the folded mode at 17.0–17.9 Hz is
the edge of that band); a 22–30 Hz line; grinding unchanged; a darty/loose lane-centring feel.

**Risk, stated:** torque authority unchanged; capped-step overshoot ~×1.1; openpilot's outer loop sees
×1.07 at 3.9 Hz (adverse bound 0.38 → 0.41); the r24 cut removes ~10 % of the lane that supplies 73–86 % of
the electronic 20 Hz damping — the two edits are in tension there, and the r24 fold is NOT certified (its
C3(ii) control fails in the 10–14 Hz band where B(f) is unidentified); κ bracket 0.45–1.45; gate_k's
LR73 ∝ 0xC6446 is BELIEF. Under the pessimistic (flown-cal) fold C10 is still ×1.6 better than V282 on
Ms 12–26; under the wire-supported effective arm ×4.1.

**Fork side:** the comb reconstruction patch (`ModelCurvatureLead`, toggle `AccordCurvatureLead` default
OFF, gain 0.75) stays OFF for the first V291 drive — one variable. See
[[accord-fork-comb-reconstruction-built-off-by-default-worth-2-4db-not-readable]].

Related: [[accord-r24-lane-is-a-lag4-bar-difference-unit-weight-sibling-of-the-lkas-lane-damps-20hz-pumps-7hz]]

**ADVERSARIAL PASS (2026-09-13, criteria pre-registered before the image existed): A arithmetic PASS · C build audit PASS · D interlocks PASS · 🛑 B DO-NOT-FLASH — B3 re-scored PASS (r24-folded Ms 12–26 ×3.3–4.2 on the admissible effective arm κ 0.449 once `biv` closed the deadband hypothesis and identified 9.94–14 Hz), but B4 FAILS byte-exactly (steady state at sp = 3 counts ×1.34–1.80 of V282's, sub-deg/s absolute — the feedback quantum 0.66 → 1.07 raw counts opens the loop below ~0.5 deg/s; intrinsic to any cal-only fb-pole change, fixable only by a cave with error feedback) and an UNGATED cost stands (worst-fit sensitivity worse than V282 on 121/121 fits over 3.0–18.2 Hz, peak ×1.99 at 12.85 Hz, a well-damped shoulder). No instability on any fit at any scaling. **ORCHESTRATOR'S VERDICT: NOT CLEARED FOR FLASHING by the letter of the pre-registration; flying it is the operator's decision** (`docs/review/ADVERSARIAL-V291-PREREG-2026-09-13.md`).**
