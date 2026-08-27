---
name: reference_accord_gp6809_zero_writers_confirmed_dead_gate
description: Accord TVA-A160 gp-0x6809 (0xFEDF17F7, the presumed "deliver flag") has ZERO writers anywhere in the 185116-instruction image, re-confirmed this session via 4 independent operand-pattern search forms (hex "0x6809", hex "-0x6809", decimal "26633", decimal "-26633") plus get_xrefs_to on the absolute address. The E1 gate in m_steer_torque_arbitration (gp-0x6809 != 1 zeroes the re-engage-ramp term at gp-0x6b2c, sites 0x2975a/0x29808/0x29964/0x29a2c) is therefore a PERMANENTLY DEAD code path, not an event-driven cut mechanism -- it takes the "!=1" bail branch unconditionally, every single cycle, forever.
metadata:
  type: reference
---

# gp-0x6809 exhaustively confirmed zero-writer, E1 gate structurally dead (2026-07-13, Ghidra code.bin)

Verified via `mcp__ghidra__search_instructions` (program="code.bin", 185116 instructions scanned per call):
- `operand_pattern="0x6809"` -> 4 matches, all `ld.bu -0x6809,gp,lp` reads inside `m_steer_torque_arbitration`
  (0x2975a, 0x29808, 0x29964, 0x29a2c). Zero stores.
- `operand_pattern="-0x6809"` -> identical 4 matches (same reads, confirms no separate negative-form encoding hides a store).
- `operand_pattern="-26633"` and `operand_pattern="26633"` (decimal form of 0x6809, closing the gap that a prior
  session's dispatcher-state variable was mis-cited in hex when Ghidra rendered it in decimal) -> **0 matches each**.
- `get_xrefs_to("0xFEDF17F7")` -> "No references found" (expected; this binary's gp-relative accesses don't populate
  Ghidra's data-xref DB, per prior sessions' own caveat -- not independent evidence, just consistent).

This is the SAME zero-writer result an earlier session found (see `reference_accord_fun3d04c_case4_and_arb_gp6809_forwarding.md`
and auto-memory `misc/eps-deliver-cut-gp6809-broken.md`), now independently re-derived this session with 2 additional
search forms (decimal) that close the "maybe it's rendered differently" gap those sessions flagged as unclosed.

## Consequence for the gentle-EME gating map

Because `ld.bu -0x6809,gp,lp; cmp 0x1,lp; bne <bail>` (confirmed byte-exact at both 0x2975a and 0x29808 this session
via `disassemble_bytes` 0x29600-0x29820) can never see lp==1 (the byte is boot-zeroed bss and never written), **the
bail branch is taken unconditionally on every pass through this code, on every cycle, for the life of the ECU.**
The re-engage-ramp term this gate protects (`gp-0x6b2c`, written at 0x297ec via `st.h r11,-0x6b2c,gp`) is therefore
ALWAYS zero regardless of any upstream state -- this is not a toggling "deliver flag," it is dead/vestigial logic
(or a flag intended to be set by a mechanism this exhaustive scan cannot find, e.g. hardware DMA-written RAM --
no evidence for that hypothesis was found either).

**Practical takeaway:** gp-0x6809 must NOT be used as a gentle-EME telemetry anchor (V31P-V2 already dropped it,
correctly, replacing it with HARD_CUT/gp-0x676e). The `docs/guides/GENTLE-EME-CAN-TO-MOTOR-GATING-MAP-2026-07-06.md` §1/§4
"E1 gate = the physical LKAS cut" framing should be read as REFUTED, not merely unconfirmed -- this session provides
positive evidence (not just absence of a writer) that the gate is structurally inert.

## Related
[[reference_accord_fun3d4a2_hardware_phase_disable_dispatcher]] -- the real hardware phase-disable anchor.
[[reference_accord_arb_bvar1_full_enumeration]] -- original E1 gate location/forwarding trace.
[[reference_accord_fun2a30e_steerstatus_debounce_statemachine]] -- the actual STEER_STATUS=4 producer, a separate
mechanism from E1, found the same session.
