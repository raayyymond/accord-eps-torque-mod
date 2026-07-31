---
name: accord-0x930-masks-are-state-not-phase-settled
description: SETTLED at instruction level - the andi 0x930/0xc30/0xd30 masks are one-hot ECU-STATE masks on gp-0x67fa, NOT a 16-phase counter; the "runs on 4 of 16 phases" note is wrong and the golden model is right
metadata:
  type: reference
---

A long-standing contradiction in the kit: an older note claimed arbitration is **phase-gated**
(`andi 0x930` on a 16-phase counter -> runs on 4 of 16 phases); the golden model claimed these are
**ECU state-machine masks** on gp-0x67fa with everything in lockstep. **The golden model is right.**

## The evidence — identical prologue in all four control tasks
```
0002214e  ld.bu -0x67fa[gp],r13     ; ECU state byte
00022172  andi  0xf,r13,r15         ; state & 0x0F
0002216c  mov   0x1,r11
0002217c  shl   r15,r11,r25         ; r25 = 1 << (state & 0xF)   <-- ONE-HOT
0002219e  andi  0xc30,r25,r0        ; test state in {4,5,10,11}
```
`r25` is a **one-hot bit of the state variable**, so `andi 0xNNN,r25` is a set-membership test:
- `0xc30` = states {4,5,10,11} · `0xd30` = {4,5,8,10,11} · `0x930` = {4,5,8,11}
- `0x830` = {4,5,11} · `0xd38` = {3,4,5,8,10,11} · `0x820` = {5,11} · `0xdfa`, `0xa` likewise.

The same four instructions appear at the head of **all four** deadline-monitored tasks —
0x2214a, 0x22a88 (0x22a8c/96/9a), 0x22b24 (0x22b28/32/36), 0x22ca0 (0x22ca4/ae/b2) — each ANDing
the same one-hot with its own mask. A free-running phase counter would not be read identically by
four independent tasks, and gp-0x67fa is already established in this kit as the ECU state machine
(see [[reference_accord_state4_ratchet_and_gp67fa_state_graph]]). FUN_00014c5c also compares
gp-0x67fa against the literals 1, 6 and 8 — state values, not phases.

## Consequence
There is **no phase counter and no phase rotation anywhere in the control tasks**. Every lane runs
in lockstep at its task's full rate whenever the ECU state bit is in the mask; the only "rate"
structure in the firmware is the five scheduler groups in
[[accord-rtos-task-table-and-rate-scheduler]]. This kills the "62.5 Hz phase cycle / 3 = 20.83 Hz"
route to explaining the ~20.9 Hz grinding, and it means no cycle->millisecond conversion in the kit
needs a 4-of-16 correction factor.

Producer/consumer "rate mismatch" between mask 0xD30 and 0xC30 is likewise **not** a rate mismatch:
both run every invocation of the same task, in different ECU states. The only difference is *which
states* they are alive in, so no aliasing or beat product can arise from them.
