---
name: reference_accord_boost_amp_blend_direction_and_d2000_block
description: The gp-0x69bc/gp-0x69ba blend in FUN_00034a72 slows RISING transitions only (falling is instant); the shared 0xD2000-0xD2013 block packs modes 10/11/12's ceiling/blend/gain scalars each in their own private slot, so editing mode 10's blend coefficient (0xD2006) in isolation is safe. Task-5 dispatch rate for FUN_00034a72/FUN_00034350 is NOT conclusively established.
metadata:
  type: reference
---

**Answers "A" and "B" from the 2026-07-30 boost-amp lever investigation; "C" (task rate) reported
unresolved with a concrete next step.**

## A — blend direction: RISING is slowed, FALLING is instant

`FUN_00034a72` (`0x34be4-0x34c02`): `cmp r25,r10` (r25=old persisted `gp-0x69bc`, r10=fresh LERP_A raw
output) computes `r10-r25` per V850 `CMP reg1,reg2` convention (= `reg2-reg1`); `ble 0x34c00` branches
when `r10-r25 <= 0` i.e. **raw <= old** — that branch does `r25 = r10` **directly, no blending** (instant
snap down). The **else** path (`0x34be8-0x34bfc`, taken when raw > old, i.e. rising) computes the
proportional step `r25 = old + ((raw-old) * cal) >> 10` — the blend. **⇒ the blend only slows RISING
transitions of the LERP output; FALLING transitions are unfiltered/instantaneous.** Same structure
confirmed for the `0xD2888`/`gp-0x69ba` pair at `0x34fc4-0x34fea` (identical `cmp`/`ble` shape). In the
requester's own "sym / slow-fall / slow-rise" framing, this is the **slow-rise** column.

## B — the 0xD2000 shared block: editing mode 10's blend coeff in isolation is SAFE

Exhaustive whole-image Python scan for every 32-bit-LE value landing in `[0xD2000,0xD2014)` (any byte
alignment), corroborated against Ghidra `get_xrefs_to` for each individual offset:
```
0xC7A80 -> 0xD2000  (0xC7A58[mode=10], ceiling)      0xC7A84 -> 0xD2002 (mode=11)   0xC7A88 -> 0xD2004 (mode=12)
0xCA094 -> 0xD2006  (0xCA06C[mode=10], blend coeff)  0xCA098 -> 0xD2008 (mode=11)   0xCA09C -> 0xD200A (mode=12)
0xCA34C -> 0xD200C  (0xCA324[mode=10], gain scalar)  0xCA350 -> 0xD200E (mode=11)   0xCA354 -> 0xD2010 (mode=12)
0xCA434 -> 0xD2012  (a 4th, 1-byte-per-mode table, mode=10)                          0xCA438 -> 0xD2013 (mode=11)
0x8AEAC -> 0xD2000  -- a table of round 0x1000-aligned addresses (0xD1000,0xEB000,0xEC000,0xD2000,0xEE000,
                        0xED000,0xF0000,0xF1000,...) -- almost certainly a CRC/block-boundary directory,
                        NOT a functional consumer (no function found at this address; it's in a data region)
0xBB3A7 -> 0xD2000  -- ODD address, doesn't fit any real table's 4-byte stride; almost certainly scan noise
                        (an unaligned coincidental byte match), not chased further
```
**⇒ The "3 identical copies" (666,666,666 / 102,102,102 / 43,43,43) are NOT one shared value read
3×** — they are **modes 10, 11, and 12's independent entries**, packed consecutively because those three
calibration variants currently carry identical numbers (consistent with mode 11 already being on record
as "our failover partner", near-duplicate of mode 10). Each of the three per-mode tables
(`0xC7A58`/`0xCA06C`/`0xCA324`) does a **single** pointer-dereference per call (`sld.w`/`sld.h`, no loop),
never an array walk — confirmed in the `FUN_00034a72` disassembly. **Mode 10's blend-coefficient cell
(`0xD2006`) has exactly ONE pointer referencing it (`0xCA094`) and sits at a different address from the
ceiling (`0xD2000`) and gain-scalar (`0xD200C`) cells for the SAME mode.** Editing only the u16 at
`0xD2006` therefore: does not touch modes 11/12 (separate cells at `0xD2008`/`0xD200A`), does not touch
the ceiling or gain-scalar tables for mode 10 itself (separate cells), and is not read as part of any
array. The only other consumer of anything in this 20-byte region is the CRC/block-directory entry, which
just needs the normal per-block CRC recompute already standard in this project's build tooling — not a new
functional side effect. **B comes back clean.**

## C — task-5 dispatch rate: NOT resolved, here is what was tried

`FUN_00034a72`/`FUN_00034350` are called from `FUN_00022ca0` (RTOS task 5, priority 2), **not**
`FUN_0002214a` (task 1, priority 6, which calls `FUN_0003b66a` and is the anchor for the established
"control task ~1000Hz" finding). Both are gated by the identical ECU-state mask `0x830` against the same
state cell `gp-0x67fa` — so they are STATE-eligible simultaneously — but that is not evidence of equal
call RATE. Tried: read the TCB "class ptr" field (`+0x28`) for tasks 1, 2, 4, 5, 7 — **all five are the
identical value `0x000BB8B8`**, so this field is a shared/common OS descriptor, not a per-task rate-class
differentiator; dead end. Partially decompiled the syscall-8 handler (`FUN_000837c0`) — it is a
wakeup-if-eligible primitiave comparing an event mask against a per-task eligibility field at
`iVar3+0x24`/a table at `tp-0x3814`, consistent with `FUN_00014be4`'s five `syscall8(0/1/3/4/5)` rate
classes from [[reference_accord_rtos_task_table_and_rate_scheduler]] — but resolving which class task 5
belongs to needs the actual per-task eligibility-mask VALUE (not yet located) cross-referenced against
which `syscall8(N)` call each task responds to. **Not completed this session.**

**Recommended next step, cheaper than the RTOS trace**: an on-car empirical measurement, the same method
already used to nail task 1 at 1kHz (STEER_STATUS dwell / CAN TX period) — e.g. observe the settle/step
cadence of `gp-0x69bc`/`gp-0x69ba` (or a diagnostic counter added to `FUN_00034a72`) against a wall-clock
CAN timestamp, which would measure the real call rate directly without needing the RTOS internals at all.

Related: [[reference_accord_boost_amp_series_question_resolved_not_series]],
[[reference_accord_rtos_task_table_and_rate_scheduler]]
