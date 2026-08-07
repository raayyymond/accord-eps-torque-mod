---
name: reference_accord_path2_is_a_real_closed_loop_via_gp6b98_and_0xc63a0_sizing
description: FUN_00038148's stage-2 "g4" (previously unresolved) differences its composite against a reference DERIVED FROM gp-0x6b98 (the aggregator's own final output, via FUN_0003b8f6, one 1kHz-tick delayed) -- Path 2 is a REAL closed firmware loop, not "closing only through the plant" as the V77 gate2 topology note assumed. 0xC63A0 is fully sized: single reader/zero writer (2-method confirmed), no float mirror, pure real scalar (zero phase contribution), exactly -6.02dB on reverting 2048->1024, touches ONLY gp-0x6bd0's own slice of Path 2 and NOTHING else in the loop.
metadata:
  type: reference
---

# Path 2 closes through gp-0x6b98 itself, not just the plant -- and 0xC63A0 is now fully quantified

2026-08-06 session, tasked with the V75 GATE-2 design brief (`v77_gate2_loop_and_friction.py`'s open item
"g4 = FUN_00038148's stage-2, decides whether reverting 0xC63A0 increases net damping -- do not ship
blind"). Builds on [[reference_accord_gp6bd0_full_reader_enumeration_and_dual_path]] and the V77 handoff
`docs/HANDOFF-2026-08-06-v75-faulted-and-the-gate2-gain.md`.

## [EVIDENCE, fresh decompile+disasm, `FUN_00038148` @0x38148-0x382d6, code.bin] Stage 1 confirmed exactly

Six gated terms (`gp-0x6b4e,-0x6b4c,-0x6b26,-0x6b46,-0x6bd0,-0x6bbe`), each `(x * gate * weight) >> 10`,
summed, then `* polarity(gp-0x6752) * GLOBAL(tp+0x7468=0xC6468) >> 10`, fed into a first-order EMA held in
`gp-0x374c` (`state += ((target*16 - state) * alpha) >> 10`, `alpha = tp+0x73ac = 0xC63AC`), output stored
to `gp-0x6b70`. **Byte-read, all 3 flown images (stock/`_v74_engagedcols_x0_12_addonly_plain_image.bin`/
`_v75_CY0.566-EX1.200_magprobe_plain_image.bin`) agree exactly**: `0xC63A0`(6bd0 weight)=1024/**2048**/2048,
`0xC63A2..AA`(other 5 weights)=1024 unchanged everywhere, `0xC6468`(GLOBAL)=2639 everywhere,
`0xC63AC`(IIR alpha)=102 everywhere, `0xC63AE`(stage-2 index scale)=1024 everywhere, `0xC6200`(shared
clamp)=8192 everywhere. **0xC63A0 is the ONLY thing any build has ever touched in this entire chain.**
IIR corner ≈16.70 Hz (alpha=102/1024); at 1kHz: -0.85dB/-23.63° @7.79Hz, -4.11dB/-47.79° @21Hz.

## [NEW, EVIDENCE] Stage 2 is NOT a scalar "g4" -- it differences the composite against a reference DERIVED FROM gp-0x6b98

Full disasm 0x38234-0x382d2:
```
iVar6 = gp-0x6bfe + gated(gp-0x6bfa, wide range) - (stage1_state >> 4)   # composite subtracted from a reference
iVar9 = sign(iVar6) * LERP(|iVar6| * weight(tp+0x73ae) >> 10)           # RAM-resident LERP, X@gp-0x64b6.., Y@gp-0x641c..
gp-0x6b70 = clamp(iVar9, +/- cal(tp+0x7200=0xC6200=8192))               # SAME clamp cal FUN_0003a382 uses for its own bias clamp
```
`gp-0x6bfe` <- `FUN_0003bc20` (sole writer, 1kHz/task1, caller `FUN_0002214a`): a straight validity-gated
COPY of `gp-0x6bfc`. `gp-0x6bfc` <- **`FUN_0003b8f6`** (sole writer, 1kHz/task1), whose FIRST INPUT is
`(int)*(short*)(gp-0x6b98) * cVar5(gp-0x6752 polarity)`, gated by `|gp-0x6b98|<=~8192` (practically always
true: the bus->`gp-0x6b98` scale caps a rail-pinned command at 1782 counts, per
`docs/HANDOFF-2026-08-06...`). It also reads `gp-0x4f60` (torque sensor), `gp-0x6abc` (a rate), `gp-0x6a10`
(angle), runs a multi-stage float EMA cascade (`tp+0x50d4/0x50d8/0x504c/0x5050/0x50bc/0x50d0/0x50d2/0x50d6`,
NOT byte-read this session), and produces the reference `gp-0x6bfc` plus two write-only cells
`gp-0x6ae0`/`gp-0x6ae2` (1 writer, 0 readers image-wide, confirmed dead-end). `gp-0x6bfa` <-
`FUN_00026c80` (the same 11-channel mixer that also writes `gp-0x67ab`/`gp-0x67ac`/`gp-0x6b4c`/`gp-0x6b4a`).

**⇒ PATH 2 IS A REAL, CLOSED, 1kHz DIGITAL FEEDBACK LOOP THROUGH THE FIRMWARE**:
`gp-0x6b98[n-1] -> FUN_0003b8f6 -> gp-0x6bfc -> FUN_0003bc20(gate) -> gp-0x6bfe -> FUN_00038148(stage2,
differenced against the gp-0x6bd0-weighted composite) -> gp-0x6b70 -> FUN_00037fe6(unity sum) -> gp-0x6ad6
-> FUN_0003a382(bias-clamp+PID) -> gp-0x6ad4 -> FUN_0003aa2c(aggregator, ADD, confirmed sign) -> governor ->
gp-0x6b98[n]`. **Call-site ordering inside `FUN_0002214a` confirmed via `get_xrefs_to` on every hop**
(`FUN_0003b8f6`@0x2240e, `FUN_0003bc20`@0x22416, `FUN_00038148`@0x22676, `FUN_00037fe6`@0x22696,
`FUN_0003a382`@0x226a0, `FUN_0003aa2c`@0x2291e, governor `FUN_00042af8`@0x229ce) -- `FUN_0003b8f6` runs
BEFORE the governor writes `gp-0x6b98` in the SAME tick, so the loop has exactly one clean unit delay
(z^-1 at the `gp-0x6b98` sample), not a same-cycle algebraic loop.

**This CORRECTS `v77_gate2_loop_and_friction.py`'s topology comment** ("the damper reaches the motor by
TWO parallel FEED-FORWARD paths and closes only through the PHYSICAL plant") -- that is FALSE for Path 2:
it closes through the FIRMWARE, via `gp-0x6b98` itself, not only through the mechanical plant. `gp-0x6bd0`
is only ONE of several inputs to this loop's error term (one of 6 composite terms, PLUS whatever
`FUN_0003b8f6`'s cascade contributes from `gp-0x6b98`/`gp-0x4f60`/`gp-0x6abc`/`gp-0x6a10` directly) --
**`FUN_0003b8f6`'s direct read of `gp-0x6b98` at near-unity scale is structurally a MUCH LESS diluted
path into this same loop than `gp-0x6bd0`'s (1-of-6-terms, then IIR'd) contribution** -- i.e. **the loop's
dominant gain term is plausibly NOT gp-0x6bd0-attributable at all, and no build in this kit's history has
ever touched it.** [BELIEF: relative dominance argued structurally, not computed -- `FUN_0003b8f6`'s float
cascade coefficients were not byte-read this session; NOT closed.]

## [EVIDENCE] 0xC63A0 fully sized

- **Single reader, zero writers, whole-image**: 2 independent methods agree (V72 build script's own
  byte-scan claim, re-confirmed fresh this session via `search_instructions(operand_pattern="73a0")` ->
  1 real hit `0x381ac ld.hu 0x73a0[tp],r9` in `FUN_00038148`, 2 branch-target false positives in an
  unrelated function). Mode-proof (bare `tp` scalar, not table-indexed).
- **No float mirror**: `FUN_00038148`'s full decompile contains ZERO float-typed operations anywhere --
  the sole reader of `0xC63A0` cannot be doing an int/float lockstep check on it. Combined with the
  single-reader closure, this is a 2-method NULL (decompile type-scan + reader-count closure).
- **Zero phase contribution**: `0xC63A0` is a pure real Q10 scalar multiplying `gp-0x6bd0` BEFORE the
  IIR/PID; reverting it changes ONLY magnitude of `gp-0x6bd0`'s own slice of Path 2, never phase.
- **Exact effect of reverting 2048->1024**: -6.0206 dB (=20·log10(1024/2048)), frequency-independent,
  on gp-0x6bd0's own contribution to the stage-1 composite -> everything downstream scales linearly
  IF stage 2's local LERP slope and FUN_0003a382's PID stay in their present (non-saturating) regime.
  Combined stage1+PID magnitude at g4=1 (the prior session's central sweep estimate, NOT independently
  pinned this session): 1.18(7.79Hz)/1.12(21Hz) at W=2048 (both cross the `net=1-L` inversion boundary,
  i.e. `damper INVERTED at the motor` per the sweep's own verdict) vs 0.59/0.56 at W=1024 (both stay
  positive/`damper weakened`, i.e. NOT inverted).
- **Does NOT touch Path 1**: `FUN_0003aa2c`'s direct `gp-0x6bd0` read (`0x3ac78`, ±2048 gate, plain ADD,
  re-disassembled fresh this session) has no dependency on `0xC63A0` anywhere.
- **`gp-0x67ab`'s gate on the whole 7-lane sum in `FUN_00037fe6`** (which INCLUDES `gp-0x6b70`, hence
  0xC63A0's whole effect) remains OPEN -- shadow-lockstep pair `gp-0x67ab`/`gp-0x4c36`, raw source
  `gp-0x3d94` (traced one hop, not further) -- excludes the sum only when `gp-0x67ab==1` exactly (a narrow
  single-value condition, structurally more consistent with an edge/init flag than a steady-state value,
  by analogy with the confirmed-always-0 sibling `gp-0x67ac`, but NOT independently confirmed this
  session). If `gp-0x67ab==1` in normal running, 0xC63A0/Path-2's `gp-0x6bd0` slice is INERT regardless of
  cal value -- doesn't change the safety direction of reverting 0xC63A0 (reverting a possibly-inert term
  is still safe), but would mean it buys zero margin, not negative margin.

## Verdict for the operator's decoupling question

Reverting `0xC63A0` (2048->1024) is a genuine, narrowly-scoped, EVIDENCE-backed decoupling lever: it
removes exactly gp-0x6bd0's own (subtractive/cancelling) contribution to Path 2 without touching Path 1's
delivery of the measured grind-band fix at all, and without moving phase. It is NOT a general "loop gain"
fix, because the loop it sits inside (now shown closed through `gp-0x6b98` itself, not merely the plant)
has at least one other, structurally less-diluted gain path (`FUN_0003b8f6`'s direct `gp-0x6b98` read)
that no cal in this kit has ever adjusted and that this session did not characterize quantitatively.

## Related
[[reference_accord_gp6bd0_full_reader_enumeration_and_dual_path]] -- the prior 2-path census this extends.
[[reference-accord-fun3a382-resonance-lane-unfiltered-correction]], the PID/frequency-response memories --
`FUN_0003a382`'s structure, reused unchanged here.
`docs/HANDOFF-2026-08-06-v75-faulted-and-the-gate2-gain.md`, `analysis-2020accord/v77_gate2_*.py` -- the
session this extends; its g4 sweep numbers reproduced exactly (cross-validated) in this session's own
Python re-derivation.

## Open, next steps
1. `FUN_0003b8f6`'s float cascade (`tp+0x50d4/0x50d8/0x504c/0x5050/0x50bc/0x50d0/0x50d2/0x50d6/0x746e`) --
   not byte-read; needed to quantify the `gp-0x6b98`-direct loop gain and settle whether it dominates
   0xC63A0's contribution.
2. `gp-0x67ab`'s steady-state value (raw source `gp-0x3d94`, one more hop from a full trace) -- decides
   whether Path 2's `gp-0x6bd0` slice (and thus 0xC63A0) is live at all in normal running.
3. The RAM LERP table (`gp-0x64b6..`/`gp-0x641c..`) populator `FUN_000389ec` (task 5/100Hz) is a large,
   multi-purpose table-synthesis function -- its typical numeric output (hence stage 2's true local slope,
   "g4") was not reverse engineered this session; the sweep {0.25,0.5,1.0,2.0} remains a bound, not a
   measurement.
