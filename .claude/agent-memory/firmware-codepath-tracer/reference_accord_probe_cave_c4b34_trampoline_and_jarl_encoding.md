---
name: reference_accord_probe_cave_c4b34_trampoline_and_jarl_encoding
description: The 0xC4B34 probe cave (in both _v76_gate_fb_arm5244_gateprobe and _v75_CY0.566-EX1.200_magprobe built images) is called via a single-instruction-steal trampoline inserted at 0x55c0e inside FUN_00055a98, the CAN 0x14A (STEER_ANGLE_RATE) periodic TX frame-builder -- entry index 10 of the confirmed 17-entry logical CAN-TX table (0xB71B8/0xB721C/0xB72AC). This sits OUTSIDE the DTC-0x18-monitored 1kHz task set (tasks 1/2/4/5); the v76 cave itself packs {gp-0x6bd0!=0, gp-0x6806!=0, gp-0x671d!=0, gp-0x671a>=5} into a nibble at gp-0x1514 and read-only taps gp-0x6bd0 (does not write it). Also derives and validates the V850E2 JARL/JR 22-bit displacement encoding from first principles (2 independent examples, one large-positive one large-negative), reusable for any future "who calls X" search where Ghidra's own xref engine returns a false null.
metadata:
  type: reference
---

# Q4 -- where the 0xC4B34 probe cave is called from -- 2026-08-06

Both `get_xrefs_to(0xC4B34)` and `search_instructions(mnemonic="jarl", operand_pattern="c4b34")` returned
**zero hits** on `_v76_gate_fb_arm5244_gateprobe_plain_image.bin` (2722 instructions scanned — this program
only has 57 functions analyzed, so the real caller is very likely outside Ghidra's analyzed set, per the
kit's documented `search_instructions` undercount trap). Resolved via a raw Python byte scan instead.

## JARL/JR 22-bit displacement encoding — derived and validated [EVIDENCE, 2 independent examples]

Two known-good calls in `code.bin`, one small positive displacement, one large negative:
- `0x34762`: `jarl 0x0006b9fa,lp`, bytes `83 ff 98 72` → hw1=0xff83, hw2=0x7298. disp = +0x37298.
- `0x46170`: `jr 0x00016de6`, bytes `bd 07 76 0c` → hw1=0x07bd, hw2=0x0c76. disp = -0x2F38A.

Both fit exactly: **`disp22 = ((hw1 & 0x3F) << 16) | hw2`, sign-extend from bit 21 (subtract 0x400000 if
≥0x200000), `target = call_site_address + disp22`.** (hw1's low 6 bits carry `disp[21:16]`, NOT just 2
bits as a hasty read of only-positive examples would suggest — the negative example was essential to
catch this; bits[15:6] of hw1 are opcode+reg2, not needed for a target-only search.) Matches this kit's
prior independent derivation in
[[reference-accord-can-tx-segmentb-scheduler-descriptor-table]]'s Method box, byte-for-byte — cross-confirms
both derivations.

## The scan and the real hit [EVIDENCE]

Scanning all 2-byte-aligned offsets of `_v76_gate_fb_arm5244_gateprobe_plain_image.bin` for `disp22` giving
target `0xC4B34` returned 2 raw candidates; **one was a false positive** (`0x41134` — Ghidra's own
disassembly there shows `mov 0x8,r6`, an unrelated instruction whose bytes coincidentally satisfy the
arithmetic — confirms the standing "verify every raw hit" rule). The other:

**`0x55c0e`: `jarl 0x000c4b34, lp`** (bytes `86 ff 26 ef`) — confirmed independently by Ghidra's own
`disassemble_bytes` (not just the hand-derived formula).

**Stock `code.bin` at the identical address `0x55c0e`**: `movea -0x1518, gp, r6` (bytes `24 36 e8 ea`).
**The cave's own epilogue replays this EXACT instruction** (`movea -0x1518,gp,r6 / jmp [lp]` at
`0xC4B6E-0xC4B72`) before returning — a clean single-instruction-steal trampoline: the original effect
(`r6 = &gp-0x1518`) is preserved for the caller, just delayed by the cave's probe work.

## The containing function: FUN_00055a98 = CAN 0x14A (STEER_ANGLE_RATE) periodic TX packer

`get_function_by_address(0x55c0e)` in `code.bin` → `FUN_00055a98`, body `0x55a98-0x55c41`. Confirmed twice:
1. The instruction immediately after the trampoline site loads the literal `0x14a` (`movea 0x14a,r0,r8`,
   `0x55c14`) — the same proof method this kit already used to identify `FUN_00055a98` as the 0x14A packer
   in [[reference_accord_gp6abe_column_degps_scale_settled]].
2. **Independent table-index confirmation**: read `0xB72C0` (offset 0x14 into the confirmed 17-entry
   builder-pointer array `0xB72AC`, per [[reference-accord-can-tx-segmentb-scheduler-descriptor-table]]'s
   Segment-C reconstruction) → `0x0005605c, 0x000562b8, 0x00055d80, 0x00055f2e, 0x00055c42, 0x00055a98` =
   entries 5-10. Entry 9 (`0x00055c42`) is that memory's already-CONFIRMED 399/0x18F packer; entry 10
   (`0x00055a98`, our function) lines up exactly with that memory's CAN-ID list position 10 = **`0x14A`**.
   Two independent methods agree exactly.

## Task rate — partially resolved

**[EVIDENCE]** `FUN_00055a98`/its dispatcher `FUN_0001d68e` is **NOT called from any of the 4 DTC-0x18-
monitored task bodies** (`FUN_0002214a`/task1, `FUN_00022a88`/task2, `FUN_00022b24`/task4,
`FUN_00022ca0`/task5 — this session's own disassembly of task 5 shows it calling
`FUN_00034350`/`FUN_000347b8`/`FUN_00034a72`/`FUN_00035154`, not `FUN_00055a98`). `get_function_callers`
on `FUN_00055a98` returns none (indirect dispatch via Table B, per
[[reference-accord-can-tx-segmentb-scheduler-descriptor-table]]).

**[BELIEF, inherited/not re-derived this session]** This kit's existing memory
([[accord-can-tx-100hz-base-tick-and-gateway]]) establishes a ~100Hz CAN-TX base tick for this same
table's sibling entries (399/0x18F, entry 9, immediately adjacent). 0x14A almost certainly shares that
cadence, but this session did not walk `FUN_0001d68e`'s caller chain up to a numbered scheduler task to
confirm the exact rate for 0x14A specifically — that memory's own "Open Questions #3" already flags this
exact gap as unresolved.

**⇒ The probe cave sits OUTSIDE the 1kHz-class DTC-0x18 timing budget** (that watchdog only monitors
tasks 1/2/4/5; the CAN-TX packer chain is architecturally separate). It is also **read-only on
`gp-0x6bd0`** (no write instruction to `gp-0x6bd0` anywhere in the 82-byte cave body, confirmed by
`disassemble_bytes(dry_run=true)`), so it cannot itself affect the Q1/Q2 hard-fault question — it only
observes.

## The cave's own logic (v76 build), for completeness [EVIDENCE]
```
r7 = 0
if gp-0x6bd0 != 0: r7 |= 8
if gp-0x6806   != 0: r7 |= 4
if gp-0x671d   != 0: r7 |= 2
if gp-0x671a  >= 5:  r7 |= 1
gp-0x1514 = (r7<<4) | (gp-0x1514 & 7)     ; packs into the high nibble, preserves low 3 bits
r6 = &(gp-0x1518)                          ; then replays the stolen `movea -0x1518,gp,r6` and returns
```
The sibling build `_v75_CY0.566-EX1.200_magprobe_plain_image.bin` uses the **SAME call site** (`0x55c0e`,
same trampoline) but a **DIFFERENT cave payload** at `0xC4B34` (confirmed by raw byte read — diverges from
byte offset 8 onward) — i.e. the trampoline insertion point is a reusable recipe across this kit's probe
builds, not build-specific.

## Related
[[reference-accord-can-tx-segmentb-scheduler-descriptor-table]] — source of Table B's structure and the
399/0x18F sibling identity this session's index-alignment argument depends on.
[[accord-can-tx-100hz-base-tick-and-gateway]] — source of the ~100Hz belief, not independently reconfirmed
for 0x14A this session. [[accord-dtc18-cadence-watchdog]] — the 4-task monitored set this cave sits outside.
