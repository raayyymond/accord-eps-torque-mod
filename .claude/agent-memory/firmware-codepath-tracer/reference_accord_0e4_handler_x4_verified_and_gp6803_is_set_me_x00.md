---
name: reference-accord-0e4-handler-x4-verified-and-gp6803-is-set-me-x00
description: BYTE-VERIFIED (2026-09-09) that gp-0x69ae = clamp(-4 * signed wire 0xE4 STEER_TORQUE, +-0x4000) -- the -4 is shl 0x2 + subr r0, NOT a mul, so a mul-operand search misses it; this pins the demand-index scale at 16.125736 wire counts per LSB EXACTLY. Also resolves gp-0x6803 as 0xE4 byte2 bits 3:2 = SET_ME_X00, which openpilot packs 0.
metadata:
  type: reference
---

Stock `code.bin` (39990-TVA-A160); **every code span below is byte-identical in the V289 image**
(`0x526C6-0x526F6`, `FUN_00049a90`, `FUN_00021724`, `0x29020-0x29060`, `0x29CA8-0x29D20`).
Verified by agent `scalecheck` closing [[reference-accord-kp-kd-schedule-axis-is-the-demand-index]]'s
own open question ("the x4 came from memory and was never re-disassembled").

## The producer of `gp-0x69ae` — `FUN_00052676` (the 0xE4 RX handler) — EVIDENCE

```
000526c6: jarl 0x00021724,lp     r10 = raw 16-bit STEER_TORQUE
000526ca: mov r10,r6
000526cc: sxh r6                 SIGN-EXTEND 16 -> 32     <- the field is SIGNED
000526ce: movea -0x4000,r0,r7    lo = -16384
000526d2: shl 0x2,r6             r6 = raw << 2            <- the "4"
000526d4: subr r0,r6             r6 = 0 - r6  => -4*raw   <- the "-"
000526d6: movea 0x4000,r0,r8     hi = +16384
000526da: jarl 0x00049a90,lp     r10 = clamp(r6, lo, hi)
000526f2: st.h r10,-0x69ae[gp]
```

🛑 **The `-4` is `shl 0x2` + `subr r0`, NOT a multiply.** Any operand-text search for a `mul`/`mulh`
near the handler returns a false zero on it. This is the same class of trap as
[[reference-accord-operand-text-search-false-positive-wrong-base-register]].

`FUN_00049a90` is a genuine 3-arg clamp — `cmp r8,r7` + three `cmovgt` order `(r7,r8)` into
`(min,max)`, then `cmp r7,r6 / cmovlt / blt / cmp r6,r8 / cmovge` returns `clamp(r6,min,max)`. The
`in_r10` Ghidra shows as a 4th parameter is a cmov staging artefact, always overwritten
([[reference-accord-clamp-helpers-and-packer-scratch]]).

`FUN_00021724` assembles the value **BIG-ENDIAN from two `ld.bu`**:
`(u8[gp-0x1428] << 8) | u8[gp-0x1427]`, inside a `FUN_0001fa42`/`FUN_0001fa72` critical section.
Matches the DBC exactly: `SG_ STEER_TORQUE : 7|16@0- [-3840|3840]` in
`honda_accord_2017_can_ext_generated.dbc`. Buffer→ID mapping independently corroborated by the RX
descriptor at `0x0BB640` ([[reference-accord-op-0e4-steer-command-full-path]]).

## Consequence: the demand-index scale is EXACT

Total right shift after the handler is 22 (`sar 0x10` @`0x29CC0` + `sar 0x6` @`0x29CD6`), and
`floor(floor(x/2^16)/2^6) == floor(x/2^22)` holds for negative x too:

> **1 demand-index LSB = 2^22 / G / 4 = 4194304/65025/4 = `16.125736` wire 0xE4 counts** at
> `G = 255*255 = 65025` (hands-off; measured p10/p50/p90 = 65025 on r62/r63/r5e).

**No overflow anywhere:** `|G*S| <= 65025*16384 = 1 065 369 600 < 2^31`, so the V850 `mul`'s discarded
high word at `0x29CBC` is sign-only.

**Two constants confirm the factor independently:** the handler clamp `0x4000 = 4 x 4096` (the field's
12-bit range) and the **stock** `LIM` cal `0xCB844[7]->0xE51A8` = `15360 = 4 x 3840` (the DBC's own
declared limit) — whose X axis even contains `X[3] = 3840`. On V280r2+ that cal is 16384. Empirical
counts-per-LSB measured off r62/r63/r5e: 16.10-16.15.

⚠ `grind_incident_r35.demand_live` hard-codes the same `-4.0`, so agreeing with it can NEVER falsify
the factor — it only checks the clamps/shifts/masks. Also `v280_map_profiles.LIMIT` is the module
constant 16384 for every build, but **stock/pre-V280 LIM is 15360**; harmless only because openpilot
never sends `|raw| > 3840`.

## `gp-0x6803` RESOLVED — it is 0xE4 byte 2, `SET_ME_X00` bits 3:2

Same handler block, from `u8[gp-0x1426]` (= 0xE4 byte 2):

| cell | expression | 0xE4 field |
|---|---|---|
| `gp-0x6805` | `byte2 >> 7` | `STEER_TORQUE_REQUEST` (bit 23) |
| `gp-0x6804` | bit 6 | `SET_ME_X00` bit 6 |
| **`gp-0x6803`** | **bits 3:2** | **`SET_ME_X00` bits 3:2** |
| `gp-0x6802` | `byte2 & 3` | `SET_ME_X00` bits 1:0 |

`create_steering_control` (`opendbc/car/honda/hondacan.py`) packs only `STEER_TORQUE` and
`STEER_TORQUE_REQUEST`, so `SET_ME_X00` = 0 ⇒ **`gp-0x6803` is 0 on every openpilot frame** and the
cliff taper arms `0xCBA04`/`0xCBA74` (selected on `gp-0x6803 == 2`) are unreachable under openpilot.
Both halves now EVIDENCE, not memory.

Full write-up: `docs/traces/TRACE-2026-09-09-kp-kd-schedule-axis.md` §V.
Script: `rlog-tools/studies/grind/scalecheck_x4_r62_r63.py`.
