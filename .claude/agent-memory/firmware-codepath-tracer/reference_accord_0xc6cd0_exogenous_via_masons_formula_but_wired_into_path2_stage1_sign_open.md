---
name: reference_accord_0xc6cd0_exogenous_via_masons_formula_but_wired_into_path2_stage1_sign_open
description: Synthesis (loop-topology task, 2026-08-22) answering "is the LKAS gain 0xC6CD0 inside or outside the feedback loop". It is structurally EXOGENOUS (Mason's-gain-formula argument, confirmed by a fresh 0/1874 gp-0x6b98-read null on its home function) so it cannot move poles of a fixed-operating-point linearization -- but its single output gp-0x6b4c is unity-weighted into BOTH the aggregator AND Path 2's own Stage-1 error-forming composite (FUN_00038148), so it sets the operating point of a genuine gain-scheduled nonlinearity (the Stage-2 LERP, "f'") living inside Path 2's z^-1 loop. UPDATE (same session, round 2): the DC/mean-level sign question is RESOLVED, not open -- a fresh decompile of FUN_0003b8f6 (the plant model) plus FUN_0002b422 (the LKAS slot's own struct-populate call) shows Honda's own construction makes gp-0x6b4c's DC contribution to iVar6 cancel to ~0 (two matched +-2.578-magnitude opposite-sign pathways, REQUEST's own slot confirmed hard-zero). The original "wrong direction" claim is WITHDRAWN -- it only traced one of the two pathways.
metadata:
  type: reference
---

# 0xC6CD0: exogenous by Mason's formula, but wired into Path 2's own error stage — sign of the mechanism is OPEN

Traced 2026-08-22, task `loop-topology` (team-lead brief: is the LKAS forward gain 0xC6CD0, currently
5346=6x, applied inside or outside the feedback loop hosting the 21-28Hz mode; if outside, can it be
"moved outside" for authority at zero margin cost). Full report sent to team-lead in 2 messages (crux,
then full). This file is the durable synthesis — it connects three previously-separate memory threads
([[accord-4x-lkas-gain-is-the-frozen-variable]], [[reference-accord-c646c-shared-gain-not-lkas-only]],
[[reference_accord_path1_path2_structural_decoupling_and_damping_dose_tables]],
[[reference_accord_path2_is_a_real_closed_loop_via_gp6b98_and_0xc63a0_sizing]]) into one answer, and
adds one new result (the sign trace) none of them contains.

## [EVIDENCE, fresh decompile+search this session] The site, re-confirmed byte-exact

`FUN_00028ea6` (arbitration) @`0x2a1ee` is the SOLE reader, image-wide, of the LKAS forward gain —
stock reads `tp+0x746C`=`0xC646C` (shared with 4 feedback readers); V57+ builds repoint ONLY this
instruction's displacement field (`74 6c`→`d0 7c`) to `tp+0x7CD0`=`0xC6CD0` (private, forward-only).
Decompiled fresh:
```c
LAB_0002a1ee:
  uVar20 = gain_cal;                    // tp+0x746C stock / tp+0x7CD0 post-repoint
  uVar35 = clamp_cal;                   // tp+0x71B4 = 0xC61B4, tracks the gain 1:1
  iVar28 = (iVar28+iVar23) * polarity(gp-0x6752) * gain_cal;   // Q15
  uVar13 = iVar28 >> 15;
  ... saturate to +-uVar35 ...
  gp-0x6b38 = uVar13;  gp-0x6b3c = uVar13 * enable_flag;
```
`search_instructions(function=FUN_00028ea6, operand_pattern="6b98")` → **0/1874**, re-run fresh this
session, reproduces the 2026-08-09 `DAMPFIX` session's identical null independently. `FUN_00028ea6`
never reads the delivered motor command anywhere in its body.

## [NEW ARGUMENT — Mason's gain formula, not previously stated this way] Why the 0/1874 null actually settles the linear question

`gp-0x6b4c` (this gain's downstream target, via the 11-slot mixer, unity copy) is a pure SOURCE node
in the loop's signal-flow graph: its value is provably independent of `gp-0x6b98` anywhere upstream
(neither `FUN_00028ea6` nor `FUN_00026c80` reads it). By Mason's gain formula, a source injected into a
loop at one or more points contributes to the loop's forced OUTPUT but does not appear in the loop's
characteristic polynomial `Δ(z)=1-ΣL(z)` — **regardless of how many injection points it has.** This is
the correct, general statement of what the prior `search_instructions=0` findings were gesturing at:
**0xC6CD0 structurally cannot move poles of a FIXED-OPERATING-POINT LINEARIZATION of this system**, full
stop, confirmed by the same 0/1874 null re-run fresh.

## [EVIDENCE, fresh decompile this session, both functions] `gp-0x6b4c` is unity-weighted into TWO consumers, not one

`FUN_0003aa2c` (aggregator, 0x3aa2c) decompiled fresh — `gp-0x6b4c` is the seed of `iVar19`, later summed
unweighted (raw ADD) alongside `gp-0x6ad4`(PID output)/`gp-0x6b26`/`gp-0x6bbe`/`gp-0x6bd0`/`gp-0x6b86`/
r24/r26, all clamped together ±0x2800(10240) → `gp-0x6b94`.

`FUN_00038148` (Path 2 Stage 1+2, 0x38148) decompiled fresh — `gp-0x6b4c` is ALSO one of six gated terms
(weight `tp+0x73AA`=`0xC63AA`=1024=unity, confirmed byte-unchanged across builds per prior sessions) in
the composite that becomes `gp-0x374c` (Stage-1's persistent IIR state, `alpha=0xC63AC=102`). Stage 2
then computes `iVar6 = gp-0x6bfe(MODEL, fed from gp-0x6b98[n-1] via FUN_0003b8f6) + gp-0x6bfa(REQUEST) -
(gp-0x374c[n]>>4)`, feeds `|iVar6|` through a **gain-scheduled LERP** (the already-recorded "f′" table,
2.539→0.248 across its range — [[reference_accord_v101_v102_resonance_mechanism_and_biquad_direction]]),
clamps to `gp-0x6b70` (±`0xC6200`=8192), which re-enters the PID's reference `gp-0x6ad6` and eventually
the SAME aggregator via `gp-0x6ad4`.

**This was individually already on record** (`reference_accord_path1_path2_structural_decoupling...`:
"gp-0x6b4c is one of 11 terms in FUN_0003aa2c's aggregator AND one of 6 terms in FUN_00038148's stage-1
composite" — 2026-08-09) — this session's contribution is (a) re-confirming both halves via fresh,
independent decompile rather than relaying, and (b) the synthesis below, which was not previously stated.

## ⭐ THE SYNTHESIS: exogenous ≠ free, because the exogenous signal feeds a nonlinearity inside the loop

Mason's formula (above) says 0xC6CD0 cannot move poles AT a fixed operating point. But Stage 2's LERP is
not linear — its local slope ("f′") varies >10x across its measured range, and `gp-0x6b4c` is one of the
signals setting WHERE on that curve the loop currently sits (via its contribution to `gp-0x374c`, hence
`iVar6`). **0xC6CD0 can't move the poles of a fixed linearization, but it CAN move which operating point
gets linearized — and Path 2 contains a real nonlinearity sensitive to exactly that.** This is a
describing-function/gain-scheduling mechanism, not a contradiction of the Mason's-formula argument: both
are true simultaneously, at different levels (structural/linear vs operating-point/nonlinear).

## ✅ [EVIDENCE, RESOLVED round 2 same session] The DC/mean-level sign question — NOT "wrong direction", NEAR-EXACT CANCELLATION

**SUPERSEDES the paragraph below (kept struck-through for the record).** The first pass only traced
Stage-1's pathway and treated MODEL as fixed/negligible — an error. Redone with a fresh decompile of
`FUN_0003b8f6` (0x3b8f6, the plant-model function):

**Pathway (a), Stage-1 → gp-0x374c → iVar6**: at steady state `gp-0x374c` settles to
`SUM6 * polarity * (0xC6468/1024) * 16`; `-(gp-0x374c>>4)` undoes the ×16 exactly, giving
**d(iVar6)/d(gp-0x6b4c) = +2.578** via this path (`0xC6468=2639`, `polarity(gp-0x6752)=-1`, `0xC63AA`
weight=1024=unity).

**Pathway (b), aggregator → gp-0x6b98 → MODEL → iVar6** [fresh decompile confirms]:
`cmd_branch = 2-stage-EMA(gp-0x6b98 * polarity / 1024)` (UNITY DC gain, standard EMA property) feeds
`gp-0x6bfc = clamp(0xC6468 * (fVar18 - FRICTION - INERTIA), +-20000)`. At steady state,
**d(gp-0x6bfc)/d(gp-0x6b98) = 0xC6468*polarity/1024 = -2.578** — the EXACT SAME MAGNITUDE as pathway
(a), opposite sign (same `polarity`, same `0xC6468` scale factor in both places — Stage-1's `*16` then
`>>4` is a designed no-op on that factor, strongly suggesting deliberate scale-matching, not
coincidence). Combined with `d(gp-0x6b98)/d(gp-0x6b4c) ≈ 1` (gp-0x6b4c unweighted into the aggregator;
downstream governor/shaper/blend chain BELIEVED close to unity DC gain — the `0xC61DA≈1.066` blend-scale
caveat in [[accord-aggregator-reaches-motor-via-gp6acc-bridge]] is the one un-closed piece here):
**d(MODEL)/d(gp-0x6b4c) ≈ -2.578, canceling pathway (a) almost exactly.**

**And REQUEST is not a tiebreaker — fresh decompile of `FUN_0002b422` (the LKAS slot's own
struct-populate call, immediately upstream of `FUN_00025c32`) shows field `+8` (→ REQUEST/`gp-0x6bfa`)
is a hard-coded literal `0`** for this slot — closes the open item in
[[reference_accord_v101_v102_resonance_mechanism_and_biquad_direction]] §1 ("what param_1[8] physically
is for the LKAS slot").

**Net: d(iVar6)/d(gp-0x6b4c) = (+2.578) + 0 + (-2.578 × blend_gain) ≈ 0 to first order.** Honda's
construction near-exactly cancels the LKAS command's DC/mean contribution to `iVar6` — this is NOT
"wrong direction," it's "no first-order DC mechanism at all." The original claim below is WITHDRAWN: it
measured only one of two matched, opposite-sign, equal-magnitude pathways. Any real gain-dose effect on
`f′` must run through: (a) the un-closed `0xC61DA`/blend-fraction residual (small, BELIEF not EVIDENCE),
(b) an AC/dynamic effect at 18-28Hz specifically (a DC argument says nothing about this), or (c) one of
the other five Stage-1 terms responding indirectly to `gp-0x6b4c` through the physical plant. Reported
to team-lead in full; the practical verdict is unchanged (do not build a "flatten f′ to fix gain-dose"
lever — there is no DC operating-point effect from gain-dose to fix by that route).

~~[SUPERSEDED — kept for the record] The naive DC/mean-level direction points the WRONG WAY: `gp-0x6b4c`
enters `iVar6` via `gp-0x374c`, which is SUBTRACTED. So: more `gp-0x6b4c` → larger `gp-0x374c` magnitude
→ more negative contribution → HIGHER `|iVar6|` → LOWER f′ → LESS Path-2 amplification — the opposite
direction from the observed dose-response. This traced only pathway (a); pathway (b) was not yet
decompiled and turns out to cancel it.~~

## Independent circumstantial support that AMPLITUDE (not the gain cal specifically) is the right frame

[Relayed, `accord/mechanism/accord-f0-crossover-is-the-endpoint.md`] Pooled across gain AND command-amplitude, "the gain
term goes non-significant (ΔR²=0.0009)" once amplitude is in the model — the existing on-car record
cannot cleanly separate "0xC6CD0 the cal value" from "how hard the signal is driven." Consistent with
(not proof of) an amplitude-sensitive-nonlinearity mechanism fed by multiple sources, of which 0xC6CD0
is only one.

## Practical verdict — answers the orchestrator's build question directly

1. **"Move the gain outside the loop"** is not a coherent operation — 0xC6CD0 is ALREADY outside the
   loop's linear return ratio (Mason's argument). There is no relocation to perform.
2. **"So it's free"** does NOT follow — the same single scaled signal (`gp-0x6b4c`, one multiply, one
   source cell) is unity-weighted into BOTH the aggregator AND Path 2's own Stage-1 composite. There is
   no second cal that independently controls "authority" vs "operating-point perturbation" — splitting
   them needs a NEW frequency-selective element (a cave), not a repositioning of an existing one.
3. **Do not build a splitting cave yet** — GATE 2 cannot be signed off while the sign of the mechanism
   is open (previous section). The prerequisite is either (a) the gain-only A/B this kit has never flown
   (`ADJUDICATION-2026-08-21-r24-raise-vs-v71c`: "the kit has never flown two builds differing ONLY in
   0xC6CD0"), or (b) numerically characterizing `FUN_0003b8f6`'s float EMA cascade + the Stage-2 LERP's
   real X/Y knots (`gp-0x64b6../gp-0x641c..`, RAM-resident, populated by `FUN_000389ec` — neither is
   byte-read anywhere in the corpus as of this session) to compute a real describing-function prediction.

## Related
[[accord-4x-lkas-gain-is-the-frozen-variable]], [[reference-accord-c646c-shared-gain-not-lkas-only]],
[[accord-aggregator-reaches-motor-via-gp6acc-bridge]] — the three memory lines this file's item-1/2
synthesis draws on. [[reference_accord_path1_path2_structural_decoupling_and_damping_dose_tables]] — the
2026-08-09 session that first noted gp-0x6b4c's dual-fork wiring (this file re-confirms it fresh and adds
the Mason's-formula framing + the sign trace). [[reference_accord_path2_is_a_real_closed_loop_via_gp6b98_and_0xc63a0_sizing]]
— Stage 1/2 structure this file's loop diagram depends on. [[reference_accord_v101_v102_resonance_mechanism_and_biquad_direction]]
— the f′ table and §9b/9c retrodiction the sign trace is computed against; its §9d already flagged the
gain-vs-f0 causal question as open, which this file's sign trace now bears on directly (against the
naive DC-shift version, not for it).
