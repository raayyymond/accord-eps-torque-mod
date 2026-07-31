---
name: reference_accord_task5_rate_resolved_and_feedforward_insertion_point
description: RESOLVES the long-open task-5 (boost+damping host) dispatch rate as 100 Hz via the syscall-8 handler's direct TCB-index arithmetic; confirms FUN_0003b66a's r14@0x3b846 insertion point and its ~7.5deg/tick staleness relative to gp-0x6b98/gp-0x6b3c/gp-0x6b4c; corrects FUN_0002c478/gp-0x6b12 from "dead near-miss" to "live, already-flashed-and-falsified anti-damping lane."
metadata:
  type: reference
---

**Context**: 2026-07-31 session, specifying (not building) a motor-command feedforward compensation for
the loop hypothesis (`gp-0x6b98` -> column reaction -> torque sensor -> boosted, ~21 Hz). Full trace for
the team lead; this memory records the two facts durable enough to outlive that specific spec.

## 1. TASK-5 DISPATCH RATE RESOLVED: 100 Hz, not 1 kHz — closes a gap 2 prior sessions couldn't crack

`[[accord-rtos-task-table-and-rate-scheduler]]` had the 7-task TCB table and the `FUN_00014be4` mod-100
rate divider (`syscall8(0)`=every tick, `syscall8(1)`=every 2nd, `syscall8(3)`=every 5th,
`syscall8(4,...)`=every 10th, `syscall8(5)`=once/100) but left "which task sits in which group" `[OPEN]`,
needing "the kernel's syscall-8 handler (0xbba70[8] = 0x837c0)". `[[reference_accord_task_table_and_ostm1_negative_rate_pin_attempt]]`
tried and failed to find the table's walker via gp-relative/tp-relative/LE32-literal search, closing with
"bounds unchanged: 100Hz-1000Hz, still not pinned."

**Resolved this session, EVIDENCE (Ghidra decompile + read_memory, code.bin):**
`read_memory(0xbba70,64)` gives the syscall dispatch table; index 8 = `0x000837C0`. Decompiled
`FUN_000837c0`: it computes `*(uint*)((param_1 & 0xff)*0x30 + *(int*)(tp-0x3814) + 0x2c)`.
`read_memory(0xBB7EC,4)` (= tp-0x3814, since tp=0xBF000) = bytes `20 b9 0b 00` LE = **`0x000BB920`** —
exactly TCB slot 1's address from the already-established 7-entry table. `idx*0x30 + 0xBB920` for
idx=0..6 reproduces **all 7** known TCB addresses exactly (0xBB920/950/980/9B0/9E0/A10/A40). So the
argument `FUN_00014be4` passes to `syscall8()` is a **direct 0-based task-slot index**, not an abstract
rate-group ID:

```python
TCB = {0: "FUN_0002214a (task 1, w_steer_control_task)", 1: "FUN_00022A88 (task 2)",
       2: "FUN_00022B20 (task 3, 4-byte stub)", 3: "FUN_00022B24 (task 4)",
       4: "FUN_00022CA0 (task 5, boost FUN_00034a72 + damping FUN_00034350 host)",
       5: "FUN_0002351E (task 6)", 6: "FUN_00014C5C (task 7, idle loop)"}
# FUN_00014be4: c%1==0 -> idx0 every tick => task 1 @ 1000 Hz (already-confirmed anchor)
# c%10==4 -> idx4 every 10th tick => task 5 @ 100 Hz  <-- THE ANSWER
```
Task indices 2 (stub) and 6 (idle) are never targeted by the divider — consistent (no periodic wake
needed for either). **Task 5 (boost+damping host) runs at 100 Hz, slower than either bracket
(`1kHz`/`500Hz`) the V59 parametric-pump eps table used.** The pump question is closed anyway (V60
null, 2026-07-31), so this doesn't reopen it, but it is the correct number for any future task-5 work.

## 2. FUN_0003b66a's insertion point confirmed; task-1 call order gives a clean, uniform ~7.5deg/tick staleness

Disassembled `FUN_0003b66a` fresh (`disassemble_function`, 0x3b66a-0x3b8f2). Confirms the two-branch
fold exactly: `r14` at `0x3b844-0x3b846` (`sar 0x2,r14` then `st.w r14,-0x6de4[gp]`) is the torque-EMA
branch (2-stage cascaded EMA on `4*gp-0x4f60`, alpha=512/1024=0.5 both stages, per
`[[reference_accord_tp73ba_ema_blast_radius_and_gp6bd0_damping]]`, `>>2` undoing the earlier `<<2`).
The SAME `r14` register (unreloaded between 0x3b846 and 0x3b86a) folds into `r28` (branch A, the
float/LERP angle-rate term truncated to int) at `0x3b86a: add r14,r28`. Cal `tp+0x73b6` (=`0xC63B6`,
**byte-read = `01 00` = 1**, confirmed) is loaded immediately after at `0x3b86c` and multiplies the
SUM at `0x3b870`, so a correction at `r14` (before the fold) flows through the identical downstream
scale/abs/store into **both** `gp-0x6b9a` (signed, `0x3b8b0`) and `gp-0x6ba6` (rectified, `0x3b892`).

**Task-1 call order** (disassembled `FUN_0002214a` in full, 0x2214a-0x22a84, a straight-line dispatcher
gated by one-hot masks of `gp-0x67fa`): `FUN_0003b66a` (`0x223d2`) runs **before** `FUN_00028ea6` (arb,
writes `gp-0x6b3c`, `0x22522`), `FUN_00026c80` (mixer, writes `gp-0x6b4c`, `0x225f6`), `FUN_0003aa2c`
(aggregator, `0x2291e`), and `FUN_00042af8` (**the governor, sole writer of `gp-0x6b98`**, `0x229ce`).
So **any** command-domain signal (`gp-0x6b3c`/`gp-0x6b4c`/`gp-0x6b98`) read at the `0x3b846` insertion
point is uniformly ~1 task-1-tick (~1 ms, ~7.5 deg at 20.9 Hz) stale — not signal-specific.

**State-gate subset proof** (bit arithmetic on the one-hot masks ANDed against `gp-0x67fa`):
```python
def bits_set(mask): return [b for b in range(16) if mask & (1 << b)]
bits_set(0x830)  # FUN_0003b66a's gate (r28)          -> [4, 5, 11]
bits_set(0xd30)  # FUN_00042af8's gate (r23)          -> [4, 5, 8, 10, 11]
bits_set(0xc30)  # FUN_0003aa2c aggregator gate (r22) -> [4, 5, 10, 11]
```
`{4,5,11}` (FUN_0003b66a) is a strict subset of both `{4,5,8,10,11}` (governor) and `{4,5,10,11}`
(aggregator) — there is no ECU state where the insertion point fires but the governor/aggregator don't.
The ~1-tick staleness figure is therefore general, not a best case.

**New inference (not proven, flagged as such):** the ~7.5 deg insertion staleness is dwarfed by a
pre-existing ~38-75 deg zero-order-hold lag already in the loop — task 5 (100 Hz) samples whatever
`gp-0x6b9a`/`gp-0x6ba6` task 1 (1 kHz) last wrote, average delay `Tsample/2`=5ms=37.6 deg, worst case
`Tsample`=10ms=75.2 deg at 20.9 Hz. This affects `gp-0x6bd0`'s existing velocity-proportional damping
(sign-locked to `gp-0x6abe`) TODAY, independent of any feedforward — plausible (not proven) partial
explanation for why the damping-sign question has flip-flopped across sessions. Worth a GATE-2 note for
any future task-5 change.

## 3. FUN_0002c478 / gp-0x6b12 correction: LIVE, already-flashed-and-falsified, not a dead near-miss

Re-decompiled fresh. `gp-0x6b12` is NOT one of the 5 write-only cells (`gp-0x6b10`, `gp-0x696c`,
`gp-0x696a`, `gp-0x678b`, `gp-0x678d` — those ARE genuinely write-only, triple-corroborated, per
`[[reference_accord_c646c_gain_feedback_vs_forward_classification]]`). `gp-0x6b12` itself is
self-referential (read back next cycle — confirmed, final line of the decompile is `*(gp-0x6b12) =
uVar23`) **and** externally read by `FUN_0002caa2` (called immediately after, `0x22438`, same task-1
sequence), which feeds mixer slot 8 -> `gp-0x6b4a`/`gp-0x6b4c`. V48A (**flashed**, per `BUILD-LINEAGE.md`
"all null" group) named this exact signal "an envelope-shaped cycle-DELTA of the delivered motor command
... classic anti-damping at a resonance" and muted it via mixer gate `0xC4120` — combined with an
unrelated `FUN_0003a382` mute in the same build, result null for the vibration. **Lesson for any future
"is there already something like this" search: check whether a structurally-similar site has already
been tried in the OPPOSITE direction (remove existing feedback vs. add new corrective feedforward) before
calling it a blank-slate template.**

## Related
[[reference_accord_rtos_task_table_and_rate_scheduler]] — the base table + divider this resolves.
[[reference_accord_task_table_and_ostm1_negative_rate_pin_attempt]] — the prior failed attempt this
session's method succeeded where it didn't (add a correction header there, don't delete).
[[reference_accord_tp73ba_ema_blast_radius_and_gp6bd0_damping]] — the EMA/damping-sign background this
session's ZOH inference bears on.
[[reference_accord_c646c_gain_feedback_vs_forward_classification]] — source of the 5-dead-cell /
`gp-0x6b12`-live distinction this session re-verified and re-used.
