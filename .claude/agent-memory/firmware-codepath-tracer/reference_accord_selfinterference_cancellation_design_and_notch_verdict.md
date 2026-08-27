---
name: reference_accord_selfinterference_cancellation_design_and_notch_verdict
description: Complete buildable design for an LKAS self-interference cancellation cave at the 6-9Hz micro-ratchet (tap gp-0x6b98 one tick old, inject inside FUN_000352b4 right after the gp-0x4f60 load at 0x354d2, 2-pole resonator reusing Honda's dead-biquad state gp-0x3814/gp-0x3818, ship b0=0 first flight) -- delivered to the orchestrator 2026-08-20. Honest verdict: the design is buildable but NOT recommended next -- the parallel effort's re-centered-Honda-biquad NOTCH is cheaper (0 new RAM/cave), addresses ALL excitation sources (not just LKAS-injected ones, since the mode rings from manual steering too), needs no unmeasured k/J_c calibration, and its arming infrastructure already flew fault-free on V103. Cancellation's source-selectivity is worth little because 7.79Hz is well above human neuromuscular bandwidth (~2-5Hz) -- genuine driver content there is "almost none."
metadata:
  type: reference
---

Delivered 2026-08-20 as a subagent design task (full doc:
`docs/specs/design/DESIGN-2026-08-20-self-interference-cancellation.md`). Full chain verification underlying this
design is in [[reference_accord_fun352b4_full_chain_gp6b82_tap_and_c6200_shared_clamp]] -- this file
records the design decisions and the comparison verdict specifically, so a future session does not
re-derive or re-litigate them from scratch.

## The design, in one paragraph

Tap `gp-0x6b98` (delivered motor/FOC command) read from inside `FUN_000352b4` -- since `FUN_00042af8`
(gp-0x6b98's writer) runs LATER in the same 1kHz tick (both share caller `FUN_0002214a`), this yields a
clean, deterministic 1-tick-old (1.000ms) value, not a race (2.80 deg phase cost at 7.79Hz). Inject by
modifying a LOCAL register copy (r16) immediately after `ld.h -0x4f60[gp],r16` @`0x354d2`, before its
first use at `0x354d6` -- `gp-0x4f60` itself (35+ reader functions, several writers) is never touched.
Filter: a 2-pole resonator with NO zero (matched to the operator's own physical model, which has no
finite zero), poles placed from the measured ratchet (f0=7.79Hz, zeta=0.017-0.036) --
`a1=-1.995015, a2=0.997409` at nominal zeta=0.0265 (computed exactly via Python this session, not by
hand; full lo/hi bracket and IEEE754 LE hex encodings in the design doc). Reuses Honda's own dead-biquad
state cells `gp-0x3814`/`gp-0x3818` (GATE-1 verified 2 independent methods this session: a
`search_instructions` operand scan across all 183,569 analysed instructions once tp-relative false
positives are excluded -- see [[reference_v850_search_instructions_base_register_collision_trap]] -- plus
a fresh-decompile cross-check; 3 of the assignment's 5 required methods NOT independently re-run this
session, inherited from the prior biquad-characterization memory). Peak |H(f0)| ~7888x at unity gain (a
Q~19-29 resonator), so the subtraction gain `b0` must be tiny and is NOT analytically derivable with
confidence (needs unmeasured k/J_c AND a gp-0x6b98-to-gp-0x4f60 unit conversion neither pinned to
physical units this session) -- **recommendation: ship b0=0 on the first flight (telemetry-only,
zero GATE-2 exposure), dose from a comparator-informed ladder, never from an armchair number.**

## The honest comparison verdict -- DO NOT RE-DERIVE, this was argued carefully

**Cancellation is buildable and fully specified, but the notch (parallel effort, re-centering Honda's
own biquad at `gp-0x3814`/`0x3818`/`0xC60A8-B4` to 7.79Hz) is the better NEXT build, for four
independent reasons, not one:**

1. Zero new RAM/code/cave vs. a full new cave (this kit's ONLY bricking class -- V24/V27/V48B).
2. The notch's arming infrastructure (the gate, state r/w, clamp) already flew fault-free as V103
   (647.8s, Honda's own un-recentered coefficients) -- cancellation's cave infrastructure has flown
   nowhere.
3. A notch needs no physical-constant calibration (depth is set by its own Q, chosen by design).
   Cancellation needs `k/J_c`, unmeasured on this car.
4. **Structural, not just risk-based**: the 6-9Hz mode is a mechanical wheel/torsion-bar resonance that
   rings from ANY torque impulse -- on record, it is present (smaller) in MANUAL steering too, and
   gripping the wheel (not disengaging LKAS) is what kills it. A notch/damping-increase removes loop
   gain AT the mode for every excitation path. Cancellation only removes the LKAS-attributable
   component and leaves the loop exactly as underdamped for a driver's own hand movement or a road
   impulse through the column.

**Cancellation's one real, non-overlapping advantage** (source-selectivity -- it would leave genuine
driver torque at 7.79Hz untouched, where a notch kills everything in-band) **is judged worth little**:
human neuromuscular bandwidth for voluntary/reflexive steering torque is ~2-5Hz, well below 7.79Hz, and
combined with point 4 above (the mode is excitable by ANY impulse, not a carrier of driver intent at
that specific frequency), the honest read is that genuine driver content at 7.79Hz during a ratchet
episode is **almost none**. [BELIEF -- reasoned from general neuromuscular-bandwidth literature + this
kit's manual-steering-still-shows-the-ratchet finding, NOT from an on-car coherence measurement isolating
driver- from LKAS-sourced content in-band during a live episode, which has not been run and is the
direct way to close this if it is ever contested.]

**A THIRD alternative was ranked above pure cancellation too**: active damping (`-K*phi'`, phi'=
torsion-bar rate) shares the notch's "addresses all excitation sources" property (loop-shaping, not
disturbance-cancelling) while needing a smaller new-state footprint than a full 2-pole cancellation
filter (a 1st-difference/rate term, not a resonant biquad) AND being more forgiving of a tuning error --
a wrong-SIGNED gain is the only bad case; a wrong-MAGNITUDE gain just under/over-damps, unlike
cancellation where a FREQUENCY mistuning (not a gain error) is the dangerous direction. Full ranking
table (5 design shapes x 4 criteria) is in the design doc §8.

**A structural risk specific to cancellation, worth restating in any future pitch of it**: it requires a
NEW summing junction (`T_measured - H_hat(u)`) that does not exist in the firmware today -- a coefficient,
sign, or timing bug there creates an unintended feedback path around a Q~19-29 resonator, which is
structurally V48B's failure class. A notch, being a single filter already wired in series in one
existing path, cannot fail that way -- a wrong coefficient there just degrades to "wrong filtering."

## What would flip this verdict

Per the design doc's open items: if the notch flies and its own collateral cost (a driver's active
in-band correction during a ratchet episode measurably deadened) turns out to be real and bothersome,
cancellation (or the active-damping middle path) becomes worth the added cave risk. That measurement --
NOT re-derivable from existing telemetry, needs a dedicated on-car test -- is the actual gate on building
this design, not a re-litigation of the reasoning above.

## Related
[[reference_accord_fun352b4_full_chain_gp6b82_tap_and_c6200_shared_clamp]] -- the Ghidra verification
underlying every structural claim above. [[reference_accord_dead_biquad_fun352b4_pole_characterized_and_reversal_counter_arm]],
[[reference_accord_biquad_is_a_notch_v103_armed_and_recentering_priced_short]] -- the notch's own
characterization, produced by a sibling effort and cited, not re-derived, here.
