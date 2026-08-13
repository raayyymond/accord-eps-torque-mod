---
name: reference-accord-v850-instruction-twin-catalogue
description: Ghidra-certified whole-instruction twins in stock code.bin for cave building (mov/cmp/add/ld.h/ld.w/ld.b/sar/addi), plus the settled cmp operand direction, mov flag-transparency, and the ld.h-vs-ld.w hw2-bit0 A/B proof
metadata:
  type: reference
---

Certified 2026-08-12 against Ghidra program `code.bin` (stock `39990-TVA-A160`, 2086 functions).
Every row below is at a REAL instruction boundary inside a DEFINED function, rendered by
`disassemble_function` / `get_assembly_context`. Byte-verified identical in the V97 flown image
(`_v97_V96BASE-C63AC.102to150_plain_image.bin`) unless noted.

## Certified twins

| bytes (LE) | instruction | twin address | owning function |
|---|---|---|---|
| `0638` | `mov r6, r7` (Fmt I) | **0x00014EEE** | FUN_00014eee (entry insn) |
| `e639` | `cmp r6, r7` (Fmt I) | **0x0001BD96** | FUN_0001bd18 |
| `043a` | `mov 0x4, r7` (Fmt II) | **0x0001A79C** | FUN_0001a77a |
| `023a` | `mov 0x2, r7` (Fmt II) | **0x0001708C** | FUN_0001702c |
| `413a` | `add 0x1, r7` (Fmt II) | **0x00015404** | FUN_00015378 |
| `243f 0694` | `ld.h -0x6bfa[gp], r7` | **0x00038208** | FUN_00038148 |
| `247f 0294` | `ld.h -0x6bfe[gp], r15` | **0x00038218** | FUN_00038148 |
| `2437 b5c8` | `ld.w -0x374c[gp], r6` | **0x000381FE** | FUN_00038148 |
| `a432` | `sar 0x4, r6` | **0x00038236** | FUN_00038148 |
| `0437 ae98` | `ld.b -0x6752[gp], r6` | **0x00028F22** | FUN_00028ea6 |
| `0606 adff` | `addi -0x53, r6, r0` | **0x000498E0** | FUN_000498de |

## ld.h vs ld.w share hw1 — decided by hw2 bit 0. Proven A/B in this binary
Same hw1 `2437` (= dest r6, base gp), opposite class:
- `0x000381FE` `2437 **b5c8**` -> hw2 `0xC8B5`, **bit0 = 1** -> `ld.w -0x374c[gp], r6`
- `0x00055DF0` `2437 **e893**` -> hw2 `0x93E8`, **bit0 = 0** -> `ld.h -0x6c18[gp], r6`

Rule: `disp16` with bit0 forced to 1 selects WORD; bit0 clear selects HALF.
To build `ld.h -0xNNNN[gp], r6` use hw1 `2437` + hw2 = LE(-0xNNNN) with bit0 already 0.

## 0x55DF0 is NOT stock-displacement — it is the kit's 427-packer repoint cell
`0x55DF2` (the hw2) is the long-running CAN-427 MOTOR_TORQUE source selector, edited by many builds:
stock `e893` (gp-0x6c18) -> V87 `6894` (gp-0x6b98) -> V90 `da94` (gp-0x6b26) -> V92 `4294`
(gp-0x6bbe) -> V96/V97 `9094` (gp-0x6b70). The **hw1 `2437` is stock and unchanged**; only the
displacement moves. Never cite 0x55DF0's displacement as a stock twin.

## SETTLED: `cmp reg1,reg2` sets flags from **reg2 - reg1**
So after `cmp rA,rB`, `bge` is taken iff **rB >= rA** (signed). Three independent confirmations:
1. **Signed, decisive** - FUN_00002874: `0x2888 sld.w 0x8[ep],r15` / `0x288e cmp r7,r15` /
   `0x2890 bge 0x28ae(return)` / `0x2894 sst.w r7,0x8[ep]`. Ghidra's C writes the subtraction
   literally in the order `iVar3 - param_2` (= r15 - r7 = reg2 - reg1) and executes the store only
   when that signed-less-than expansion is true => bge taken iff r15 >= r7.
2. **Unsigned** - FUN_00038148 `0x3825e cmp r7,r8` / `0x38264 bh` -> Ghidra `if (*(gp-0x64b8) < uVar7)`
   where r7=*(gp-0x64b8), r8=uVar7 => bh taken iff reg2 > reg1.
3. **Unsigned** - FUN_00038148 `0x38270 cmp r16,r8` / `0x38272 bnc` -> Ghidra's else-arm => reg2 >= reg1.

`cmp imm5,reg2` is parallel: reg2 - imm5 (FUN_0001bd18 `0x1bd30 cmp 0x9,r8` + `bne` -> Ghidra
`*(gp-0x67fa) == '\t'`).

## `mov` does NOT touch PSW; `add`/`sar`/`addi` DO
Flags survive across a `mov` placed between a flag-setter and its branch. Compiled-code evidence:
- **Fmt II (imm5)**: FUN_0001bd18 `0x1bd30 cmp 0x9,r8` / `0x1bd32 mov 0x0,r28` / `0x1bd34 bne`.
  Also FUN_00015378 `0x15398 cmp r9,r0` / `0x1539a mov 0x0,r7` / `0x1539c bnc`.
  Also FUN_000498de `0x498e0 addi -0x53,r6,r0` / `0x498e4 mov 0x0,r10` / `0x498e6 bc`.
- **Fmt I (reg-reg)**: FUN_0001a77a `0x1a7b0 cmp r0,r10` / `0x1a7b2 st.b r0,0x4[r28]` /
  `0x1a7b6 mov r10,r20` / `0x1a7b8 be`. Ghidra still renders the test as `if (iVar2 == 0)`.
  => both the store and the Fmt-I mov are flag-transparent.
- `movea` is likewise transparent (FUN_0001a77a `0x1a786 cmp 0x9,r6` / `0x1a788 movea 0xff,r0,r10` /
  `0x1a78c bne`).
- 🛑 `add imm5,reg2` (`413a`) and `sar imm5,reg2` (`a432`) DO update PSW. Do not schedule either
  between a `cmp` and its `bge`.

## Honda's compare-and-discard idiom
`addi imm16,rN,r0` computes rN + imm16, discards the result, keeps the flags.
`addi -K,r6,r0` + `bc` == unsigned `r6 < K`; + `bge` == signed `r6 >= K`.
Clean decompiled proof at FUN_000197b8: `0x197b8 addi -0x1f,r6,r0` / `0x197bc bge` renders as
`if ((int)param_1 < 0x1f) { ... }`.

## 🛑 `search_instructions` operand_pattern needs ", " (comma-SPACE)
Reproduced this session: `mnemonic=mov, operand_pattern="r6,r7"` returned
`match_count: 0, truncated: false` over 183,570 instructions - a clean-looking FALSE NULL, while
`"r6, r7"` returned 42 real hits including the known-good 0x14EEE. `disassemble_function` renders
without the space; `search_instructions` renders WITH it. See [[reference-accord-v850-6byte-disp-decoder-corrected]].

## Raw-byte scan hits that are NOT twins
A raw LE byte scan over [0x13000,0x100000) produced hits at **0x20CB8** (`0638`), **0x1E41E**
(`e639`) and **0x1B9DA** (`023a`) where Ghidra reports *"No instruction at address"* AND *"No
function found"* - unanalysed/data regions, not instruction boundaries. Roughly 1 in 6 raw hits was
unusable. Always adjudicate a scan hit against Ghidra before using it as a twin.
