---
name: accord-undefined-live-code-2b422-and-gp6b2c-orphan-writers
description: 0x2B422 and 0x2B57A are LIVE (jarl from 0x22530/0x22572, right after the 0x22522 call to FUN_00028ea6) yet Ghidra defines no function there; the 0x2A400-0x2B600 blob holds 11 more gp-0x6b2c touches invisible to search_instructions - plus the corrected V850 Format-V jr/jarl decode
metadata:
  type: reference
---

# Undefined-but-live code at 0x2A504 / 0x2B422 / 0x2B57A, and the corrected Format-V decode

**EVIDENCE, method: raw little-endian Format-V scan of stock `code.bin` with a passing positive
control (0x22522 -> 0x28EA6, `jarl lp`), cross-checked against Ghidra `get_function_by_address`
and `get_assembly_context` (both return empty at 0x2B124 and 0x2B41C).**

## The correct V850 Format-V (JR/JARL) decode — the recurring mask bug, settled

```
hw1 (LE halfword at addr):   bits 15-11 = reg2   (0 => jr, 31 => jarl lp)
                             bits 10-0  must equal 0x780   <-- mask 0x07FF, NOT 0x07C0
                             (bits 5-0 carry disp[21:16])
hw2 (LE halfword at addr+2): disp[15:0]
target = addr + sign_extend22( ((hw1 & 0x3F) << 16) | hw2 )
```
Masking with `0x07C0` also matches **`prepare`** (hw1 = 0x0782 at 0x28EA6) and produces garbage
targets — that is the false-positive generator behind the kit's recorded "jarl Format-V mask bug".
Always run the 0x22522 -> 0x28EA6 positive control before trusting a scan.

## What the scan found

Ghidra defines FUN_00028ea6 as 0x28EA6..0x2A30A (ends at `dispose 0x1,{...},[lp]`). Everything
from **0x2A400 to 0x2B600 is UNDEFINED in Ghidra**, yet it has live entry points:

- **0x2B422** — `jarl lp` from **0x22530**
- **0x2B57A** — `jarl lp` from **0x22572**
  (both immediately after `0x22522: jarl 0x28EA6,lp` — same caller, same task)
- **0x2A504** — `jr` from 0x2A34C, 0x2A368, 0x2A384, 0x2A3BA (inside the live FUN_0002a30e region)

The blob also contains **11 `gp-0x6b2c` touches that `search_instructions` cannot see** (Ghidra
reports 13 matches, all inside FUN_00028ea6; a raw byte scan for the 0x94D4 gp displacement finds
24). Extra sites: loads at 0x2A8FC, 0x2B1AC; stores at 0x2B124, 0x2B136, 0x2B158, 0x2B1BC,
0x2B1F2, 0x2B274, 0x2B2AA, 0x2B332, 0x2B350. The bytes at 0x2B118 are a *near*-clone of 0x297E0
(same instruction sequence, different register allocation) — a separately compiled variant, not a
byte copy, so a byte-identity search will not find it either.

**Containment result (EVIDENCE):** no Format-V branch anywhere in 0x2A400-0x2B600 targets an
address below 0x2A400 except `0x2B53E -> 0x25C32` (an outbound `jarl`). So that blob **cannot
redirect control flow into FUN_00028ea6's body**. It could still *write* gp-0x6b2c if it executes.

**OPEN:** whether the 0x2B0xx-0x2B3xx block is reachable from 0x2A504 / 0x2B422 / 0x2B57A. Next
step: `create_function` at 0x2B422 and 0x2A504 **in a scratch import, never on the shared project**,
then decompile. Do not call `disassemble_bytes` without `dry_run:true`, and never `save_program`.

See also [[accord-gp6b2c-addend-is-identically-zero]],
[[reference_accord_lkas_pid_pole_cell_gate1_census_2a508_second_reader]].
