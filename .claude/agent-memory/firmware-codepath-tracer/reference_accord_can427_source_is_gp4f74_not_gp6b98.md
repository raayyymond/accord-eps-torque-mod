---
name: reference_accord_can427_source_is_gp4f74_not_gp6b98
description: Accord TVA-A160 CAN 427/0x1AB (STEER_MOTOR_TORQUE) source gp-0x6c18 is NOT a copy/derivative of the live motor-command gp-0x6b98 -- FUN_00056420 runs two independent LERP filters, one for each. CAN 427 may not reliably reflect an LKAS-only physical torque cut.
metadata:
  type: reference
---

# CAN 427/0x1AB source gp-0x6c18 != delivered motor command gp-0x6b98 (2026-07-13)

Verified via full `decompile_function` of `FUN_00056420` (program="code.bin", gp=0xFEDF8000, tp=0xBF000).
Corrects an assumption in a mission brief this session that CAN 427 = "the delivered motor torque the EPS
reports out" derived from the same signal as the motor command.

## The function actually runs TWO independent LERP filters
```c
void FUN_00056420(void)
{
  iVar3 = TSG21.field_0xa0;                 // persistent state B (CAN-427 filter)
  sVar1 = *(short *)(gp - 0x4f74);           // filter-B TARGET: gp-0x4f74, NOT gp-0x6b98
  uVar2 = *(ushort *)(tp + 0x73c6);          // filter-B rate cal
  // filter A: target = gp-0x6b98 (confirmed live motor-command demand), state = TSG21.field_0x9c
  iVar4 = ((gp-0x6b98 - TSG21.field_0x9c) * cal(tp+0x73c8)) >> 10 + TSG21.field_0x9c;
  TSG21.field_0x9c = iVar4;
  gp-0x6b54 = (short)iVar4;                  // MOTOR COMMAND REGISTER — filter A output
  // filter B: target = gp-0x4f74, state = TSG21.field_0xa0
  iVar3 = ((sVar1 - iVar3) * uVar2) >> 4 + iVar3;
  TSG21.field_0xa0 = iVar3;
  gp-0x6c18 = (short)iVar3;                  // CAN-427 SOURCE — filter B output
}
```
Filter A (gp-0x6b98 -> gp-0x6b54) is the confirmed live motor-command path (per
`reference_accord_lkas_path_wiring`/`reference_accord_shaper_fun42af8`). Filter B (gp-0x4f74 -> gp-0x6c18)
is a SEPARATE first-order LERP with its own persistent state (`TSG21.field_0xa0`, a different struct field
than filter A's `field_0x9c`) and its own rate cal (tp+0x73c6, adjacent to but distinct from filter A's
tp+0x73c8). They happen to live in the same function and share the "TSG21" struct label, but there is no
data dependency between them within this function.

## gp-0x4f74 provenance — partially traced, NOT closed
Sole writer: `FUN_000757a2` at `0x7af40` (`st.h r16,-0x4f74,gp`), confirmed via exhaustive
`search_instructions operand_pattern="4f74"` (14 hits total, only one is a store). That SAME function
`FUN_000757a2` also reads gp-0x6b98 elsewhere (0x7580c, per `reference_accord_lkas_path_wiring`'s reader
table, tagged "TBD" there) — but a data-flow dependency between that read and the 0x7af40 write was NOT
established this session (the function spans ~0x5000+ bytes, too large to decompile in one call; would
need the same file-dump-and-slice technique used for `m_steer_torque_arbitration` in this session, or a
narrower disassemble_bytes window around 0x7580c-0x7af40).

## Practical implication
**CAN 427/0x1AB (STEER_MOTOR_TORQUE) is at least one hop removed from the actual delivered LKAS command**
and may not move in lockstep with an LKAS-only physical cut (e.g. the gp-0x676e==4 phase-disable in
`reference_accord_fun3d4a2_hardware_phase_disable_dispatcher`) unless `FUN_000757a2` genuinely derives
gp-0x4f74 from gp-0x6b98 (unconfirmed) or from some other torque-domain signal that also collapses on a
cut. This is CONSISTENT with the existing memory `honda-op-steeringtorqueeps-always-zero`'s advice to not
trust 427 as a delivered-torque proxy, and reinforces preferring a direct RAM-level telemetry tap (V31P
style) over CAN-427 decode for confirming a physical LKAS cut.

## Related
[[reference_accord_lkas_path_wiring]] — establishes gp-0x6b98 as the live motor-command signal and
FUN_00056420 as one of its 3 confirmed consumers (this memory refines that entry: FUN_00056420 does MORE
than just consume gp-0x6b98, it also independently produces the CAN-427 value from an unrelated input).
[[reference_accord_fun3d4a2_hardware_phase_disable_dispatcher]] — the actual physical-cut site this session
identified; use that, not CAN 427, as the ground-truth signal.
[[reference_accord_can_tx_399_427_bitmap]] — the original byte/bit map of the 427 buffer this memory's
gp-0x6c18 tracing feeds into (byte0 bits1:0 + byte1, per that memory's derivation chain).
