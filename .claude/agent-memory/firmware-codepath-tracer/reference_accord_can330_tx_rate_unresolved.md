---
name: reference_accord_can330_tx_rate_unresolved
description: Accord TVA-A160 CAN 330/0x14A builder FUN_00055a98 has ZERO statically-resolvable callers (confirmed both via get_function_callers and a direct jarl-disp22 operand scan for "55a98") and is NOT a member of the phase-scheduled "Table B" that governs 399/0x660/0x19F/0x64D (per prior Segment D/B work). Its true TX period -- and therefore the true clear-cadence of V31P-V2's gate-flag OR-latch -- is UNRESOLVED. The build script's own docstring assumption of "100 Hz / ~10 ms" is unverified, not derived.
metadata:
  type: reference
---

# CAN 330 (0x14A) TX period -- genuinely open, not just uncited (2026-07-13)

Cross-checked this session against `reference_accord_can_tx_segmentD_known_frame_provenance.md` and
`reference_accord_can_tx_segmentB_scheduler_descriptor_table.md` (both pre-existing), plus fresh Ghidra calls:

- `get_function_callers(name="FUN_00055a98")` / by address -> "No callers found."
- `search_instructions(mnemonic="jarl", operand_pattern="55a98")` -> 0 matches (185116 instructions scanned) --
  confirms no direct PC-relative call anywhere in the image, matching Segment D's independent disp22-scan finding.
- Segment D's own table explicitly lists 0x14A as "not in table-B" (the 44-byte-stride, phase-mask-gated RAM
  descriptor array that DOES govern 399/0x660/0x19F/0x64D's periods) -- so the phase-mask mechanism documented
  for those 4 messages does not apply to 330.

**Consequence:** 330 (and its builder `FUN_00055a98`, which is where V31P-V2's `pack_telemetry` hook lives, site
0x55c0e) is reached only via some other indirect/table dispatch whose period this session did not locate. The
V31P-V2 build script's docstring states "CHANNEL: CAN 330 / 0x14A (DLC8, 100 Hz...)" and "pack hook read-then-clears
every 330 frame (~10 ms)" -- this is a STATED ASSUMPTION in the build's own comments, not a traced/verified fact
(no citation of a scheduler table entry or timer register for 330 specifically exists anywhere in this session's
work or in prior memory).

## Why this matters
V31P-V2's gate flags are OR-latched (set-on-fire, never simple-overwritten) and read-then-cleared inside the 330
builder each time it runs (confirmed from `analysis-2020accord/build_v31p_v2_tva.py`'s `pack_telemetry` stub:
`ld.bu -0x1500[gp],r7` then `st.b r0,-0x1500[gp]` at the end -- a genuine read-and-clear, not a plain overwrite).
This design is ROBUST against missing a transient fire **within one 330-TX period** -- but if the true 330 period
is longer than believed (e.g. genuinely ~100 ms rather than ~10 ms), the OR-latch would accumulate ANY qualifying
gate fire across a much wider window, which for a low-threshold gate like torque-MAX>=320 (fires constantly during
normal steering) would make that bit read "fired" on nearly every frame regardless of the specific cut instant --
producing exactly the observed "steady ~100 ms cadence, statistically identical before/during/after the cut"
symptom, NOT because the hook missed the event, but because the sampling window is too coarse relative to a
320-threshold gate's true firing frequency. This is a plausible, but UNPROVEN, explanation for the field
observation -- flagged as BELIEF, not evidence.

## Next verification step
Locate `FUN_00055a98`'s indirect call site (the true 330 dispatch table/loop -- likely reached the same way
`m_steer_torque_arbitration`'s sibling ramp-manager `FUN_0002a30e` is reached, i.e. worth investigating together)
and pin the base tick rate + any phase/skip logic gating slot 10 (330's table-A index per Segment D). Until then,
treat any "100 Hz" or "10 ms" claim about CAN 330 in this codebase as an assumption carried in the V31P-V2 build
script's comments, not a Ghidra-verified fact.

## Related
[[reference_accord_decider_0x40e64_hook_confirmed_sees_real_fire]] -- the other half of why ENGAGE_SM_CUT telemetry
didn't discriminate the cut event; this memory covers the sampling-side explanation, that one covers the hook-placement side.
[[reference_accord_telemetry_ram_hook_a160]] -- source of the well-evidenced ~100 Hz claim for the DECIDER/deliver-commit
chain (w_steer_control_task -> FUN_00022ca0 -> FUN_000413ae), which is a SEPARATE, better-evidenced rate from 330's TX rate.
