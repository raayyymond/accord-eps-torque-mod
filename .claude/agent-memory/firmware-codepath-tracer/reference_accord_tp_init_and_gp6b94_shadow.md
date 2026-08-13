---
name: accord-tp-init-and-gp6b94-shadow
description: tp=0xBF000 and gp=0xFEDF8000 are set by ONE idiom at 0x140C4-0x140D6 that Ghidra never analysed; gp-0x6b94 has a shadow-lockstep twin at gp-0x4ce0; CAN 427's packer applies abs() via FUN_00049a5a
metadata:
  type: reference
---

Three facts certified while building V100 (2026-08-13). All EVIDENCE, two methods each.

## 1. ⭐ `tp` AND `gp` ARE SET BY THE SAME IDIOM — and Ghidra cannot see it

```
0x140C0  ori   0x8000, r0, r1      800e0080   ; r1 = 0x00008000
0x140C4  movhi -0x121, r0, gp      4026dffe   ; gp = 0xFEDF0000
0x140C8  movea 0x0,    gp, gp      24260000
0x140CC  add   r1, gp              c121       ; gp = 0xFEDF8000   <- THE KIT'S gp
0x140CE  movhi 0xb,    r0, tp      402e0b00   ; tp = 0x000B0000
0x140D2  movea 0x7000, tp, tp      252e0070   ; tp = 0x000B7000
0x140D6  add   r1, tp              c129       ; tp = 0x000BF000   <- THE KIT'S tp
```

⇒ **`tp` is exactly as constant and as live as `gp`, everywhere, in every task context.** That is the
argument to use whenever a cave wants to read a `tp`-relative cal at runtime: the flown caves already
depend on `gp`, and `gp`/`tp` are established four instructions apart from the same `r1`. It converts
an ABI belief into an EVIDENCE claim. V100 used it to justify `ld.hu 0x7200,tp,r6` inside the cave.

🛑 **`0x140CE` IS NOT INSIDE ANY GHIDRA-DEFINED FUNCTION** (`get_function_by_address` → "No function
found"), so `search_instructions(mnemonic="movhi", operand_pattern="tp")` **misses the real tp
initialiser entirely** while happily returning five data-region false positives. A raw Python scan
for `reg2 == 5` write forms found it; `disassemble_bytes(dry_run:true)` then confirmed the decode.
Textbook case of the documented undercount — see [[reference_accord_c63ae_arm_agnostic_residual_gain_and_zxh_wrap]].

**The only OTHER write to `tp` in defined code is `0x0000008c mov r0,tp`** — the reset handler
clearing r1..r23. Every remaining raw candidate inside a defined function was adjudicated OUT and
they are ALL the hw2 half of a `jarl` disp22 or an `andi` imm16 (Format-V aliasing):
`0x38FE0` (hw2 of `jarl 0x6b9fa` @0x38FDE) · `0x19934` (hw2 of `andi 0x2a10,r14,r14` @0x19932) ·
`0x543E6` (hw2 of `jarl 0x16de6` @0x543E4) · `0x68FEE` (hw2 of `jarl 0x6b9ee` @0x68FEC) ·
`0x566CE` (hw2 of `jarl 0x5950e` @0x566CC). The rest lie in calibration/data pages.

## 2. 🛑 `gp-0x6b94` IS SHADOW-LOCKSTEP PROTECTED AT `gp-0x4ce0` — a THIRD pair

```
0x3acfa st.h r12,-0x6b94[gp]  /  0x3acfe st.h r12,-0x4ce0[gp]     (the +10240 rail)
0x3ad12 st.h r12,-0x6b94[gp]  /  0x3ad16 st.h r12,-0x4ce0[gp]     (the -10240 rail)
0x3ad20 st.h r10,-0x6b94[gp]  /  0x3ad26 st.h r12,-0x4ce0[gp]     (pass-through)
0x3ad1c cmp r15,r13 / bne 0x3ad2c  ->  0x3ad30 jarl 0x6b9fa       (hard-shutdown monitor)
```

Same class as `gp-0x6bfa`/`gp-0x4cfa` and `gp-0x6b4a`/`gp-0x4cd2`. **Reading is free — writing either
cell trips the monitor.** Binds any future build that wants to touch the aggregator output.
⊕ Confirms the aggregator clamp is `±0x2800 = ±10240` (`movea ±0x2800,r0,r12` @`0x3acf6`/`0x3ad0e`).
See [[reference_accord_request_arm_shadow_lockstep_and_no_cal_cells]].

## 3. CAN 427's packer really does rectify — `FUN_00049a5a` IS `abs()`

`decompile_function(0x49a5a)` returns the signed-negate idiom with the `-0x80000000` guard. So the
builder at `0x55DF0..0x55E12` is `clamp(abs(X) * 5 >> 6, 0, 0x3FF)`: `jarl 0x49a5a` (abs) ·
`0x55E06 mul 0x5,r6,r0` · `0x55E0A movea 0x3ff,r0,r8` · `0x55E10 sar 0x6,r6` (stock is `sar 0x3`).
⇒ **427 is a MAGNITUDE channel and needs a paired sign bit** — the 4.86× cost of omitting it is
measured in [[reference_accord_aggregator_is_unweighted_and_427_rectification_costs_4.9x]].

## Useful twins certified the same session (all byte-identical stock ↔ V99 base)

`24376c94` `ld.h -0x6b94[gp],r6` @`0x453E0` (FUN_0004503c) · `2437a0b0` `ld.h -0x4f60[gp],r6`
@`0x4E452` · `e5370172` `ld.hu 0x7200[tp],r6` @`0x382BC` · `243f2a95` `ld.h -0x6ad6[gp],r7`
@`0x3A798` · `a731` `sub r7,r6` @`0x4333E` (FUN_00042af8) · hw1 `2036` @`0x27798` · hw2 `0028`
(=+10240) @`0x3A7D6`. 🛑 `20360028` (`movea 0x2800,r0,r6`) does **not** exist whole anywhere.

⚠ The PID clamp reads are `ld.h 0x7200,tp,r6` = **`25370072`** @`0x3A7A2` (NOT an `ld.hu`), then
`ld.hu` = `e55f0172` @`0x3A7B2` (r11) and `e53f0172` @`0x3A7C4` (r7). Different encodings for the
same cal three instructions apart — do not assume one form.
