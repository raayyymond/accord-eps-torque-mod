---
name: reference_accord_can_tx_399_427_bitmap
description: 2020 Accord TVA-A160 V850E2 (master.bin/code.bin) — exhaustive per-bit map of what builders FUN_00055c42 (399/0x18F STEER_STATUS) and FUN_00055d80 (427/0x1AB MOTOR_TORQUE) write into their CAN TX buffers, whole-program-verified via search_instructions (185116 instructions scanned). Identifies every spare/never-written bit as a piggyback candidate.
metadata:
  type: reference
---

# 399/0x18F STEER_STATUS and 427/0x1AB MOTOR_TORQUE — full bit-level buffer map

Builds on `reference_accord_can_tx_segmentD_known_frame_provenance.md` (which located these builders and
their table-A/table-B indices but did not map payload bytes). This document closes that gap.

Method: `mcp__ghidra__disassemble_function`/`disassemble_bytes` (program=master.bin) for the two builders and
every callee reached via `jarl` inside them, then `mcp__ghidra__search_instructions` with `operand_pattern`
substring (e.g. `"0x141c, gp"`) run **program-wide** (185116 instructions scanned each call) to confirm NO
other function anywhere in the 1MB image touches a given buffer byte. `get_xrefs_to` on the absolute RAM
address returns nothing for plain gp-relative accesses (Ghidra doesn't data-xref register+disp forms here) —
`search_instructions` operand-substring search is the reliable tool for this binary, confirmed working at
program scope. ⚠ substring collision trap: searching `"0x6c34"` alone also matches the UNRELATED variable
`gp-0x6c34` (=0xFEDF13CC, a different address, coincidental digit reversal) — always include the base
register text (`", gp"` or `", r18"`) in the pattern to disambiguate.

## Frame 399 / 0x18F STEER_STATUS — builder `FUN_00055c42`, buffer `0xFEDF6BE0` (gp-0x1420), DLC 7

| Offset | Addr | Bits 7..0 | Content | Store instr (addr: bytes) |
|---|---|---|---|---|
| 0 | 0xFEDF6BE0 | 15:8 of V1 (BE hi byte) | REAL: V1 = `-(ld.h gp-0x4f60 * 125 >> 7) & 0xffff` (STEER_TORQUE_SENSOR-class, signed src, matches task's own worked example) via setter `FUN_000218be` | `0x218d2: 64e7e0eb` (`st.h r28,-0x1420,gp`, byte-swapped V1) |
| 1 | 0xFEDF6BE1 | 7:0 of V1 (BE lo byte) | REAL (same V1, low byte) | same instr (halfword store) |
| 2 | 0xFEDF6BE2 | 15:8 of V2 (BE hi byte) | REAL: V2 = `-(ld.h gp-0x6a56) & 0xffff`. gp-0x6a56 has 25 program-wide readers incl. NAMED fns `m_steer_torque_arbitration` and `w_lkas_setpoint_consumer2`; sole writer `FUN_0003f776` (3 stores + 1 zero-reset at 0x3f81e) — semantic name not fully chased this session, but structurally an arbitration/setpoint-class value, NOT a raw sensor. Via setter `FUN_000218de` | `0x218f2: 64e7e2eb` (`st.h r28,-0x141e,gp`) |
| 3 | 0xFEDF6BE3 | 7:0 of V2 (BE lo byte) | REAL (same V2, low byte) | same instr |
| 4 | 0xFEDF6BE4 | 7:4 | REAL: low nibble of `gp-0x6807` (byte, effectively 4-bit field) `<<4` | `0x55ca2: 4447e4eb` |
| 4 | 0xFEDF6BE4 | 3 | REAL: `gp-0x6806 & 1` | `0x55c86: 4457e4eb` |
| 4 | 0xFEDF6BE4 | 2:0 | **SPARE — never written anywhere in the whole image** (confirmed: exhaustive `"0x141c, gp"` scan = exactly these 2 read/write pairs, no others). Boot-zeroed (buffer sits in the bss-clear range `0xFEDEC000-0xFEDFFFFF`, see `reference_accord_telemetry_ram_hook_a160.md`) and never touched after — reads as 0 forever. | none |
| 5 | 0xFEDF6BE5 | 5:4 | REAL: `gp-0x6880 & 3` (explicit 2-bit mask) | `0x55cc2: 4437e5eb` |
| 5 | 0xFEDF6BE5 | 3:0 | **SPARE — explicit constant 0, re-cleared every cycle** (`andi 0xf0,r9,r9` then store, no OR term) | `0x55cd6: 444fe5eb` (the clearing write itself) |
| 5 | 0xFEDF6BE5 | 7:6 | **SPARE — never written anywhere** (same exhaustive confirmation) | none |
| 6 | 0xFEDF6BE6 | 7 | REAL: `gp-0x6804 & 1` | `0x55cf2: 447fe6eb` |
| 6 | 0xFEDF6BE6 | 6 | **SPARE — never written anywhere** (exhaustive `"0x141a, gp"` scan = exactly 3 read/write pairs: bit7, bits5:4, bits3:0 — none touch bit6) | none |
| 6 | 0xFEDF6BE6 | 5:4 | PROTOCOL (not free): 2-bit rolling counter, own persistent var `gp-0xf48` (incremented mod-4 each call) | `0x55d44: 4447e6eb` |
| 6 | 0xFEDF6BE6 | 3:0 | PROTOCOL (not free): checksum/counter nibble from `FUN_00057b24(buf,7,399)` return value | `0x55d6c: 4437e6eb` |

**399 spare total: 10 bits** (byte4 bits2:0 = 3, byte5 bits7:6+bits3:0 = 6, byte6 bit6 = 1). All read as 0
today (boot-zero-and-never-touched, or explicit-clear-every-cycle for byte5 low nibble).

## Frame 427 / 0x1AB MOTOR_TORQUE — builder `FUN_00055d80`, buffer `0xFEDF6C34` (gp-0x13CC), DLC 3

Torque value derivation (feeds bits1:0 of byte0 + all of byte1): `ld.h gp-0x6c18` (raw torque, sole writer
`FUN_00056420` at `0x56458`) → `FUN_00049a5a` (signed clamp/negate helper) → `FUN_00049a78` (min vs 0xffff) →
`*5, >>3` (scale 5/8) → `FUN_00049a90(lo=0,hi=0x3ff)` (clamp to unsigned 10-bit) → `FUN_00021864` (packs
10-bit value into byte0 bits1:0 + byte1 full byte, sole caller = this builder).

| Offset | Addr | Bits 7..0 | Content | Store instr (addr: bytes) |
|---|---|---|---|---|
| 0 | 0xFEDF6C34 | 7 | REAL, one-time-latched + live-override: boot-once (latch `gp-0x2f67`) compares config byte at **`gp+0x6409`** (positive gp offset, addr `0xFEDFE409`) to ASCII `'0'` → bit=0 if equal else bit=1; every cycle thereafter, forced to 1 if `gp-0x683a`!=0 (no path forces it back to 0 after init) | init: `0x55e74: 443734ec` (set) / `0x55e7e: d2bf346c` (`clr1 7,0x6c34,r18`, clear) — override: `0x55e9c: d23f346c` (`set1 7,0x6c34,r18`) |
| 0 | 0xFEDF6C34 | 6:5 | **SPARE — never written anywhere** (exhaustive scan: 8 hits on `"0x13cc, gp"` + 4 hits on `"0x6c34"`+`r18` form + 2 ep-relative in `FUN_00021864`, all accounted for, none touch bits6:5). Boot-zeroed (buffer in bss-clear range), never touched after. | none |
| 0 | 0xFEDF6C34 | 4 | REAL: `gp-0x685a & 1` | `0x55dc8: 445734ec` |
| 0 | 0xFEDF6C34 | 3 | REAL: `gp-0x685b & 1` | `0x55de8: 444734ec` |
| 0 | 0xFEDF6C34 | 2 | REAL: fault/DTC-active flag = NOT(`FUN_00046ea6(3)==0 && FUN_00046ea6(4)==0 && FUN_00046ea6(10)==0`) | `0x55e44: d217346c` (set1) / `0x55e4e: d297346c` (clr1) |
| 0 | 0xFEDF6C34 | 1:0 | REAL: top 2 bits of the clamped 10-bit torque value (see derivation above) | `0x21882: 8073` (`sst.b r14,0x0,ep`, inside `FUN_00021864`) |
| 1 | 0xFEDF6C35 | 7:0 | REAL: full byte, low 8 bits of the clamped 10-bit torque value (full overwrite, no mask — 0 spare bits possible here by construction) | `0x21874: 81e3` (`sst.b r28,0x1,ep`) |
| 2 | 0xFEDF6C36 | 7 | **SPARE — never written anywhere** (exhaustive `"0x13ca, gp"` scan = exactly 3 read/write pairs: bit6, bits5:4, bits3:0 — none touch bit7) | none |
| 2 | 0xFEDF6C36 | 6 | REAL: `FUN_0004d0ac()&1` — returns 1 iff `gp-0x675a` (raw byte) is 1 or 2 (`(raw-1) <=_unsigned 1`) | `0x55da8: 446736ec` |
| 2 | 0xFEDF6C36 | 5:4 | PROTOCOL (not free): 2-bit rolling counter, own persistent var `gp-0xf47` (separate counter from 399's `gp-0xf48`) | `0x55eee: 445f36ec` |
| 2 | 0xFEDF6C36 | 3:0 | PROTOCOL (not free): checksum/counter nibble from `FUN_00057b24(buf,3,0x1ab)` return value | `0x55f16: 444f36ec` |

**427 spare total: 3 bits** (byte0 bits6:5 = 2, byte2 bit7 = 1). All boot-zero-and-never-touched (no
explicit-clear-every-cycle pattern found in this builder, unlike 399's byte5 low nibble).

## Combined spare bit budget

| Frame | Total payload bits | Spare bits | Location |
|---|---|---|---|
| 399/0x18F | 56 (7B) | 10 | byte4[2:0], byte5[7:6]+[3:0], byte6[6] |
| 427/0x1AB | 24 (3B) | 3 | byte0[6:5], byte2[7] |

**Patch-planning note (not executed, read-only session):** the "never written" bits (6 of 399's 10, all 3 of
427's) need a NEW store instruction added (e.g. code-cave + branch, matching the `0x4141E` hook pattern in
`reference_accord_telemetry_ram_hook_a160.md`) since nothing currently touches them. The "explicit constant-0"
bits (399 byte5 bits3:0, 4 bits) instead need an EXISTING mask constant changed (e.g. `andi 0xf0,r9,r9` at
`0x55cd2` → a narrower mask that preserves some low bits) — a same-length immediate-only edit, structurally
different from a store-insertion patch and carries the (unconfirmed) risk that the firmware author zeroed
that nibble deliberately for a reason (reserved/future field) rather than it being inert.

## Cross-reference
- `reference_accord_can_tx_segmentD_known_frame_provenance.md` — builder/table-index provenance this document assumes.
- `reference_accord_telemetry_ram_hook_a160.md` — bss-clear range `0xFEDEC000-0xFEDFFFFF` (both buffers fall inside it, explaining why "never touched" bits are boot-zeroed not garbage) and the `0x4141E` per-cycle hook site (reusable pattern for adding a store to the "never written" spare bits).
- `reference/tooling/reference_rizin_ghidra_v850_quirks.md` — V850E2 tooling gotchas; NOT hit this session (Ghidra MCP decoded both builders and all callees cleanly, no invalid/unaligned markers observed).
