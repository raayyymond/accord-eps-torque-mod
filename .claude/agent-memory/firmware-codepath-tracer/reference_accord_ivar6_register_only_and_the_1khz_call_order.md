---
name: reference_accord_ivar6_register_only_and_the_1khz_call_order
description: iVar6 is register-only (FUN_00038148 has EXACTLY two stores, gp-0x374c and gp-0x6b70), so a cave must recompute it — and the fixed 1 kHz call order inside FUN_0002214a (0x22416 -> 0x225f6 -> 0x22676 -> 0x22696 -> 0x226a0) makes that recomputation ZERO-SKEW between passes and at most one-tick-skewed otherwise. Also: gp-0x6b4a has a shadow-lockstep twin at gp-0x4cd2.
metadata:
  type: reference
---

# `iVar6` is register-only — and the 1 kHz call order is what makes a cave recomputation legitimate

Traced 2026-08-13, task `tracer-6ad6`. Full trace: `docs/traces/TRACE-2026-08-13-v100-6ad6-and-ivar6.md`.

## `FUN_00038148` stores EXACTLY TWO cells [EVIDENCE — `disassemble_function(0x38148)`, whole stream]
```
00038230: st.w r6,-0x374c[gp]      the Stage-1 IIR accumulator (32-bit)
000382d2: st.h r11,-0x6b70[gp]     the Stage-2 output
```
Corroborated by a raw Python store scan (op 0x3A/0x3B, reg1==gp) over `0x38148..0x382d8`: same two.
⇒ **`iVar6` (r6 @`0x3823a`) is NEVER stored. No cave can read it directly.**

Byte-exact residual, and note the `>>4` uses the **newly committed** accumulator:
```
00038230: st.w r6,-0x374c[gp]    <- COMMIT first
00038236: sar  0x4,r6            <- ACTUAL = gp-0x374c_new >> 4   (`a432`, reusable Honda twin)
00038238: subr r15,r6            <- MODEL − ACTUAL   (subr reg1,reg2 : reg2 = reg1 − reg2)
0003823a: add  r9,r6             <- + gated REQUEST  => iVar6
```

## ⭐ THE CALL ORDER — this is the fact that licenses recomputation [EVIDENCE]
Raw decode of every `jarl disp22,lp` inside `FUN_0002214a` (the single-rate 1 kHz control task):
```
0x22416 -> FUN_0003bc20   writes gp-0x6bfe   (MODEL)
0x225f6 -> FUN_00026c80   writes gp-0x6bfa   (REQUEST) and gp-0x6b4a
0x22676 -> FUN_00038148   READS all three; writes gp-0x374c, gp-0x6b70
0x22696 -> FUN_00037fe6   writes gp-0x6ad6
0x226a0 -> FUN_0003a382   READS gp-0x6ad6 -> the PID
```
⇒ Between `0x226a0` returning and the next pass reaching `0x22416`, **all four cells are mutually
consistent** — a cave reads exactly the triple `FUN_00038148` used and exactly the reference the PID
used. **`gp-0x6ad6` therefore has ZERO skew, always** (committed cell, no recomputation).
Recomputed `iVar6`: **zero skew** unless the 100 Hz hook lands inside `[0x22416, 0x22676]`, then
**≤ one 1 kHz tick on ONE arm** = `A·2π·7.79·0.001` = **4.9 % of amplitude** at the symptom
frequency ⇒ ~150 ct against `|iVar6|` p50 **2,829 ct hands-ON** (fine) but against p50 **188 ct
hands-OFF** (fatal). 🛑 **Recomputation is valid ONLY in the hands-ON regime; mask on
`steeringPressed`.**
⚠ OPEN: whether the 100 Hz `0x14A` builder can preempt a partial 1 kHz pass at all. DI across the
cave prevents the cave being interrupted, not the cave starting mid-pass. Closing it needs the INTC
priority registers for the two vectors (SVD `UPD70F3508_V850E2Px4`).

## Cost of `|iVar6| ≥ |gp-0x6bfa|` in the cave
**40 B + 14 B pass merge** (a comparator consumes r6 AND r7 ⇒ it must SEED r7 ⇒ **one comparator per
pass** in a 2-register cave — a hard structural constraint). Net **+8 B** if it replaces V98's b5.
🛑 **FIVE new instruction encodings** (`sub r6,r7`, `add r6,r7`, `cmp 0x0,r7`, `bge` after an r7
test, `subr r0,r7`) — each needs a Ghidra-certified Honda twin, which is the real cost.

## 🛑 The cheaper route that may make it unnecessary
`gp-0x6b70 = sign(iVar6) × LERP(|iVar6|)` and the LERP is flash-derived, identity-rescaled and
monotone-by-code ⇒ **invertible**. ⇒ **`|iVar6|` is ALREADY measured at 100 Hz on CAN 427 on every
build since V96.** What is unmeasured is `|gp-0x6bfa|` (REQUEST). Cost of the in-cave comparator vs
427's `sar 0x6` quantisation + the ~10 ms CAN join is a genuine fork.

## Shadow lockstep — reading is free, writing is a hard-shutdown trip
`gp-0x6bfa` ↔ `gp-0x4cfa` (`0x273b0/b4`, `0x273c8/cc`, `0x273d6/dc`; trap `cmp r6,r14`/`bne` →
`jarl 0x6b9fa`). 🛑 **NEW: `gp-0x6b4a` ↔ `gp-0x4cd2`** (`0x27784/88`, `0x2779c/a0`, `0x277aa`; trap
at `0x2777c`). Both are **write-side** checks ⇒ a read-only cave cannot perturb them.

Related: [[reference_accord_c6200_clamps_gp6ad6_inside_the_pid]] ·
[[reference_accord_stage2_lerp_rescale_is_identity_and_ivar6_bound]] ·
[[reference_accord_request_arm_shadow_lockstep_and_no_cal_cells]]
