---
name: reference-accord-factorc-lockstep-gate-clear-ceiling-only
description: FactorC (0xC9E9C[mode], the damper's speed-keyed gain) is NOT mirrored on the float-lockstep side; FUN_000347b8/FUN_00034350's cross-tick checks are ceiling-only (gp-0x6ac2-keyed) and numerically identical int/float — a FactorC edit is clear of both hard-shutdown DTC 0x1c/0x1d monitors on this lane
metadata:
  type: reference
---

**2026-07-30, safety-gate question from team-lead before a build editing FactorC `0xC9E9C[mode]` →
mode 10 `0xD27BC` (raising Y[0] from 0 so the damper isn't arithmetically zero at creep).** Extends
[[reference_accord_gp6ac2_ceiling_only_and_no_motor_command_feedforward]] and
[[reference_accord_v48b_monitor1_dtc1c_notch_safety_closed]]. Full instruction-level trace, byte-scan
corroborated. Program: stock `code.bin`.

## The verdict: FactorC is not mirrored anywhere. Clear to edit w.r.t. these two monitors.

`FUN_000347b8` (0x347b8-0x348dc, 45 instructions, fully disassembled) is the float-lockstep twin of
`FUN_00034350` (the damper). It reads ONLY `gp-0x6bd0` (the already-clamped int output) and `gp-0x6ac2`
(the ceiling index). It recomputes the CEILING via a float LERP at cal **0xC6554/0xC655C/0xC6560+**
(global, not mode-indexed — 4-byte float entries, no count header, unlike the int-domain struct), then
checks `gp-0x6bd0/1024 <= ceiling` within **±0.0048828125 (= exactly ±5 raw counts at Q10)** tolerance.
**Zero instructions reference gp-0x698a/gp-0x69bc/gp-0x6a5e/gp-0x6a10/gp-0x67fe/gp-0x6abe/gp-0x6ac0 (the
seven raw-product inputs) or any of the four factor tables.**

**FactorC (0xC9E9C) confirmed referenced EXACTLY ONCE in the entire 1,048,576-byte image — inside
`FUN_00034350`@0x34506/0x34508, nowhere else — by 4 independent methods:** `search_instructions`
("c9e9c", 1 hit), raw full-image byte scan for the literal LE 32-bit sequence (1 hit, same offset),
`get_xrefs_to(0xC9E9C)` (2 hits, both dereferences within FUN_00034350), and a `movhi`+`movea` split-
encoding check (only 2 `movhi 0xd,r0,rX` instructions exist program-wide — `FUN_0001c4bc`@0x1c4f2,
`FUN_000508e8`@0x50b3c — both disassembled and resolve to unrelated addresses 0xCEFF4/0xCD01B, not
0xC9E9C-0xC9ECC). **Same result (exactly 1 hit, in FUN_00034350) for FactorB (0xC9CCC), factor3
(0xC9DB4), factor4 (0xC9F84), and the int ceiling (0xC77A0).**

## Bonus: the two ceilings are numerically identical (closes an indirect-risk angle)

Int ceiling mode 10 (`0xD209C`, struct format `[count,X0..Xn,Y0..Yn]` cross-validated against
FactorC's own known bytes at `0xD27BC` which decoded exactly to X=(2240,3840,5120,8960)/
Y=(0,235,430,877)): **X=(300,800), Y=(512,1024)**. Float ceiling (`0xC6554`): **X=(300.0,800.0),
Y=(0.5,1.0)** — same breakpoints, Y consistently /1024. Modes 8 (`0xD109C`) and 11 (`0xD20A8`) byte-
identical to mode 10 (mode 0's pointer `0xC0E068` failed to read — unbacked in Ghidra's map, not
chased). Since `FUN_00034350`'s clamp to ±int-ceiling is unconditional, FactorC can only change *how
often* the raw product saturates — it cannot push gp-0x6bd0 past either ceiling, so no NEW int/float
divergence is possible even indirectly via increased saturation frequency.

## Exhaustive gp-0x6bd0 reader sweep (11 raw hits, all adjudicated)

`FUN_0001bf88`@0x1c114 (CAN/UDS diagnostic packer, case 0xb of 16, telemetry only) ·
`FUN_00034350` (producer + entry shadow-check) · `FUN_000347b8` (ceiling lockstep, above) ·
**`FUN_00038148`@0x38150 — a SECOND, different aggregator feeding `gp-0x6b70`**, sums gp-0x6bd0 with
gp-0x6b4e/6b4c/6b26/6b46/6bbe, cal-weighted 0xC73A0-0xC73AC, own history/rate-limit chain, no fault
call — not a watchdog, an undocumented second consumer worth flagging for future work · `FUN_0003aa2c`
(main aggregator, already known) · `FUN_0006bcb2`@0x6bcf8 and `FUN_000757a2`@0x76bb6/0x76bc8 —
**FALSE POSITIVES**, `operand_pattern="6bd0"` substring-collided with branch target address
`0x00076bd0`; confirmed by full decompile text search of FUN_000757a2 (208,469 chars, zero literal
"6bd0" matches) and by disassembling FUN_0006bcb2 (a phase-mask dispatcher, unrelated). **Adds a
concrete instance to the "operand_pattern substring collision" trap class — a branch target ending in
the same 4 hex digits as a cal displacement gives a false xref.**

## Escalation path traced (what a trip actually means)

`FUN_000347b8` fault → `FUN_000462e6(0x417a,...)` → `FUN_00016de6(0x1d,...)` (hard-shutdown DTC 0x1d).
`FUN_00034350`'s OWN entry-time re-check of the same ±5-count window (`0x34358-0x3438a`, reading the
`gp-0x6bc4/6bc6/6bc8/6bca` shadow cells `FUN_000347b8` populates) → `FUN_0004613e(0x4179,...)` →
`FUN_00016de6(0x1c,...)` — the SAME hard-shutdown chain as
[[reference_accord_consistency_monitor_hardshutdown]] (Monitor 1, motor-off). Confirmed these are ONE
tolerance cross-verified twice (0.0048828125 × 1024 = 5.0 exactly), not two independently-thresholded
gates.

## Naming reconciliation
Team-lead's "table 0xD2018" is not an instruction reference (search_instructions finds 0) — it is
**data**, one resolved per-mode pointer inside `FUN_00035154`'s ceiling table array (`0xC7888[mode]`).
`FUN_00035154` is the `gp-0x6bbe` (boost shaper) analog of `FUN_000347b8` — decompiled in full,
structurally identical (ceiling-only, same tolerance, same `FUN_000462e6` escalation), keyed on
`gp-0x6a62` instead of `gp-0x6ac2`. Not a stronger/different mechanism than the damper's lane.

## Open items
- `FUN_00038148`/`gp-0x6b70`'s downstream role uncharacterized.
- Mode 0's ceiling table address unreadable this session.
- Session worked stock `code.bin` only; team-lead reports V59 cal bytes match stock for cells in
  question, but the function bodies/escalation chain here weren't cross-opened against V59.
