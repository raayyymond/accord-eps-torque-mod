---
name: reference_accord_request_arm_shadow_lockstep_and_no_cal_cells
description: The REQUEST arm of the FUN_00038148 observer residual (gp-0x6bfa) has ZERO calibration cells -- its +-20000 bound is a movea immediate, not a cal -- AND it is protected by an ACTIVE SHADOW-LOCKSTEP MONITOR at gp-0x4cfa whose mismatch handler is FUN_0006b9fa, a GATE-1 hazard never previously recorded for this cell; by contrast gp-0x6bfe (MODEL) and gp-0x374c (ACTUAL) have NO shadow, which is exactly why V89 and V97 could touch them safely.
metadata:
  type: reference
---

# The REQUEST arm: no cal levers, and a lockstep monitor — 2026-08-13, `tracer-arms`

Task: pre-position the V99 lever set on all three arms of `iVar6 = MODEL + REQUEST − ACTUAL`
(`FUN_00038148` @ `0x38236-0x3823a`). Full write-up `docs/traces/TRACE-2026-08-13-v99-arm-levers.md`.

## 1. `gp-0x6bfa` has ZERO calibration cells [EVIDENCE — full disasm walk of `FUN_00026c80` 0x27396–0x273e6]

```
0x27396  ld.w   -0x3d90[gp],r15   ; LKAS demand, 32-bit. 1W @0x27336 / 1R @0x27396
0x2739e  addi   -0x4e20,r15,r0    ; flags vs +20000        0x4e20 = 20000
0x273a2  ld.h   -0x6bfa[gp],r14
0x273a6  ble    0x273ba
0x273ac  movea  0x4e20,r0,r14     ; ***HARDCODED IMMEDIATE — NOT a cal load***
0x273b0  st.h   r14,-0x6bfa[gp]   ; clamp HIGH = +20000
0x273c4  movea -0x4e20,r0,r14
0x273c8  st.h   r14,-0x6bfa[gp]   ; clamp LOW  = -20000
0x273d6  st.h   r15,-0x6bfa[gp]   ; in-range pass-through
```

⇒ **No tunable cell anywhere between `gp-0x3d90` and `iVar6`**, and REQUEST enters the sum with
coefficient exactly **+1** and **no cal multiply** (`add r9,r6` @ `0x3823a`, opcode `0x0E`).
**If a comparator names REQUEST as the dominant arm, there is no cal-only lever on it at all.**

⊕ This **proves at instruction level** the standing claim that REQUEST's `±20000` gate in
`FUN_00038148` is DEAD: the writer stores only values in `[-20000,+20000]` and the gate
(`addi 0x4e20,r7,r11` / `ori 0x9c41,r0,r8` / `cmp` / `cmovnc 0x0,r7,r9`) admits exactly that closed
interval. The `cmovnc` can never fire.

## 2. 🛑🛑 THE SHADOW-LOCKSTEP MONITOR — a GATE-1 hazard not previously on record

`gp-0x6bfa` has a **shadow copy at `gp-0x4cfa`**. All three writers write **both**, and **every** write
path is guarded by `cmp r6,r14 / bne 0x273e2` (r6 = shadow, r14 = live), where a mismatch reaches:

```
0x273e2  movea -0x4cfa,gp,r6
0x273e6  jarl  0x0006b9fa,lp
```

**`FUN_0006b9fa` is the generic shadow-mismatch reporter**, taking the shadow cell's address in `r6`.
Confirmed by five further pairs inside `FUN_000352b4` alone, all calling it the same way:
`gp-0x69a4`/`gp-0x4c66` · `gp-0x6b7a`/`gp-0x4cdc` · `gp-0x6458`/`gp-0x4c0c` · `gp-0x6480`/`gp-0x4c20` ·
`gp-0x6b86`/`gp-0x4cde`. The idiom is always `if (live == shadow) { write both } else { FUN_0006b9fa(&shadow) }`.

⇒ **Any cave or in-place patch writing `gp-0x6bfa` without also writing `gp-0x4cfa` trips the monitor.**
Produces an on-car fault, not a quiet null. **Add `gp-0x6bfa`/`gp-0x4cfa` to the never-touch list for
cave work.**

## 3. ⭐ THE ASYMMETRY THAT EXPLAINS THE SAFE HISTORY
`gp-0x6bfe` (MODEL) and `gp-0x374c` (ACTUAL) have **NO shadow** — censused both ways, 1W/1R each.
**The two arms that have been safely touched (V89's `0xC40D2` on MODEL, V97's `0xC63AC` on ACTUAL) are
exactly the two that are not lockstep-protected.** Not a coincidence worth relying on blindly, but it
is the structural reason neither build faulted.

## 4. ⚠ CORRECTION — the MODEL gate is NOT dead, it is the sentinel detector
`FUN_0003bc20` (sole writer of `gp-0x6bfe`, 12 lines):
```c
s = gp-0x6bfc;
if (s + 20000U < 0x9c41) { health = 0x400;  }               // gp-0x695c = OK
else                     { health = 0xffff; s = 0x7fff; }   // FAULT sentinel
gp-0x6bfe = s;  gp-0x695c = health;
```
MODEL's `±20000` test in `FUN_00038148` exists **precisely to catch the `0x7FFF` sentinel**, and it is
an `if/else` wrapping the **entire Stage 2** (`bnc 0x382ce`), whose else-branch sets
`gp-0x6b70 = 0x7FFF` — the plausibility latch, duty 0 on 87,423 frames. **REQUEST's gate is dead by
pre-clamp; MODEL's is dead only because upstream never faults.** Different mechanisms — keep distinct.

## Related
[[reference_accord_c63ae_arm_agnostic_residual_gain_and_zxh_wrap]] — the lever this trace recommends instead.
[[reference_accord_fun38148_lane_weight_map_and_c63a0_reconciliation]] — the six ACTUAL-arm weights.
[[reference_accord_fun3b8f6_cal_types_iir_phase_and_v86_gate_decode]] — the MODEL arm's ten cal cells.
[[reference_v850_ep_relative_short_format_aliasing_trap]] — the trap that fired on `gp-0x374c` here.
