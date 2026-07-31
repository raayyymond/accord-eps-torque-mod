---
name: accord-rtos-task-table-and-rate-scheduler
description: A160 RTOS decoded - 7-task TCB @0xbb920 with NO period field; rates come from FUN_00014be4's mod-100 divider (/1,/2,/5,/10,/100); TAUJ1I2 (EIIC 0x340) is the SOLE tick source
metadata:
  type: reference
---

The kit's long-standing "RTOS TCB table walker not yet located / task rate UNRESOLVED" is closed.
All addresses verified in `code.bin` (stock, flat base 0).

## Task table — 7 tasks, 48-byte stride, NO period field
Pointer array of 7 TCBs at **0xbb858** (byte-verified in Python): 0xbb920, 0xbb950, 0xbb980,
0xbb9b0, 0xbb9e0, 0xbba10, 0xbba40.

TCB layout (0x30 bytes): `+0x00` RAM ctx ptr · `+0x04` packed `[07][prio][taskid][00]` ·
**`+0x08` ENTRY POINT** · `+0x0c` stack base · `+0x10` stack size · `+0x14` index · `+0x28` class ptr.

| id | entry | prio | role |
|---|---|---|---|
| 1 | FUN_0002214a | 6 | w_steer_control_task (command pipeline) |
| 2 | FUN_00022a88 | 4 | |
| 3 | FUN_00022b20 | 5 | 4-byte stub — body is just `jarl ext_tsk` |
| 4 | FUN_00022b24 | 3 | |
| 5 | FUN_00022ca0 | 2 | engage decider + **boost FUN_00034a72 / damping FUN_00034350** |
| 6 | FUN_0002351e | 1 | |
| 7 | FUN_00014c5c | 0 | background `do{}while(true)` loop; also programs OSTM0 |

**There is no period/phase field.** Tasks 1-6 are run-to-completion, each ending in `jarl 0x861f2`
(= syscall 9, ext_tsk) — 6 callers, byte-verified. Task 7 never exits.

## The rate divider — FUN_00014be4
Called at every `caxi [gp-0x42fc]` checkpoint that finds the flag set (82 checkpoint sites).
Counter `gp-0x4304` is modulo 100 and is touched **only** by this function (8 accesses, 0x14be8-0x14c50):

```
if (99 < c) c = 0;
syscall8(0);                        // every tick        /1
if (c & 1)        syscall8(1);      // every 2nd         /2
if (c % 5 == 2)   syscall8(3);      // every 5th         /5
if (c % 10 == 4)  syscall8(4,...);  // every 10th        /10
if (c == 0x10)    syscall8(5);      // once per 100      /100
c = c + 1;  syscall5();
```

So the firmware has exactly **five rate groups: /1, /2, /5, /10, /100**. Which task sits in which
group is still [OPEN] — it needs the kernel's syscall-8 handler (0xbba70[8] = 0x837c0).

## The tick — TAUJ1I2, and it is the ONLY one
`gp-0x42fc` has **exactly one writer image-wide**: `0x149dc st.w r19,-0x42fc[gp]` in the EI
trampoline's `EIIC == 0x340` arm. Channel 52 = TAUJ1I2. Verified with BOTH gp encodings
(disp16 scan = 0 hits, 6-byte disp23 scan = 1 hit) — the disp16-only scan is blind here, see
[[reference_v850e2_extended_disp23_encoding_solved]].

**OSTM0 is NOT the control tick** — see [[reference_accord_pclk_40mhz_and_ostm0_is_500hz]].

## RTOS service calls — only 5 exist image-wide
Byte-scanned whole image for the `syscall` encoding: 5 sites, all wrappers at 0x861e0-0x861f8.
`syscall 1` @0x861ec · `5` @0x861e6 · `8` @0x861e0 · `9` @0x861f2 (ext_tsk) · `0x2e` @0x861f8
(task startup shim, referenced as a pointer from the class records at 0xbb8c8/0xbb8fc).
**0xbba70 is the 64-entry syscall dispatch table** (not an interrupt vector table): default stub
0x84656, non-default exactly at indices 1, 5, 8, 9, 22, 46, 47 — matching the syscall numbers.
Leaf at **0x861fe** = `OSTM0TS = 1` (start the OS timer); one caller, 0x6168c in FUN_0006166a.

## EI trampoline FUN_0001492a — corrected dispatch map
Dispatches on EIIC = channel x 0x10. Two entries in the brief were wrong:
0x970 = **TSG21I05** (TSG2**1**, not TSG20) -> FUN_00061614, handled *before* `ei` (highest urgency).
0x600 = **CSIH1IR** (serial, not ADC) -> FUN_0006404c. Also 0x340 TAUJ1I2 (the tick),
0x470 TAUA1I1 (see [[reference_accord_dtc18_cadence_watchdog]]), 0x110 P0, 0x100 LVI0, 0x0f0 ECCCNED.
Fall-through 0x14810 logs ECR and raises a fault. **OSTM0 (0x2c0) is absent from this table.**
