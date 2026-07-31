---
name: accord-dtc18-cadence-watchdog
description: The DTC-0x18 task-overrun watchdog mechanism located - TAUA1I1 (EIIC 0x470) requires gp-0x68b7 & 0xF == 0xF; exactly 4 tasks set bits 0/1/2/3, so all four must run inside every watchdog window
metadata:
  type: reference
---

Any code cave on a control-task path must fit inside this deadline. The mechanism is now explicit.

## The checker — FUN_00014b3e, reached via EIIC 0x470 = TAUA1I1
```
00014b64  ld.bu -0x68b7[gp],r6
00014b6a  andi  0xf,r6,r8
00014b6e  cmp   0xf,r8
00014b70  be    0x00014b96        ; all four bits set -> OK
...       stsr EIPC / log / jarl 0x00014af6 with code 3   ; FAULT
00014b96  st.b  r0,-0x68b7[gp]    ; clear for the next window
```
Gated by `gp-0x4308 == 0` (an inhibit); if non-zero it just clears gp-0x4308 and skips the check.

## The four monitored tasks and their bits
A whole-image byte scan for gp-0x68b7 (disp 0x9749, gp-relative) returns **exactly 8 accesses —
one read + one write per task, four tasks**:

| task | read | write | `ori` mask | bit |
|---|---|---|---|---|
| 1 FUN_0002214a | 0x22152 | 0x22176 | `ori 0x1` | 0 |
| 2 FUN_00022a88 | 0x22a90 | 0x22aa6 | `ori 0x2` | 1 |
| 4 FUN_00022b24 | 0x22b2c | 0x22b42 | `ori 0x4` | 2 |
| 5 FUN_00022ca0 | 0x22ca8 | 0x22cbe | `ori 0x8` | 3 |

Four distinct bits, `0xF` requires all four -> **every one of tasks 1, 2, 4 and 5 must run at least
once inside each TAUA1I1 window, or the ECU raises the hard-fault-eligible DTC 0x18.**
Tasks 3, 6 and 7 are unmonitored. Task 5 is the one carrying the boost (FUN_00034a72) and damping
(FUN_00034350) producers, so the assist-shaping lane is inside the deadline.

## The budget itself is still [OPEN]
The window length = the TAUA1I1 period, and **no TAUA1 configuration write was located** in the
image (the only 0xFF809xxx touches are 0xFF809248/0xFF80924C at 0x6c4e8/0x6c4fe). Lower bound: the
window cannot be shorter than the slowest of the four tasks' periods. To close it, decode TAUA1
channel 1's CDR/prescaler — start at FUN_0006c4b0 and the TAUA1 base 0xFF809000.

Related: [[accord-rtos-task-table-and-rate-scheduler]], [[accord-dtc-0x18-hard-eligible-cadence-watchdog]].
