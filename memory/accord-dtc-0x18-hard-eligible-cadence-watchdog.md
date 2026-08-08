---
name: accord-dtc-0x18-hard-eligible-cadence-watchdog
description: DTC 0x18 is the per-task cadence/overrun watchdog and IS hard-fault eligible (0x3D01) — so any code cave on the 1 kHz path has a task-timing budget to respect.
metadata: 
  node_type: memory
  type: reference
  originSessionId: ad5622d6-5208-450c-86c6-9dd849c09dd4
  modified: 2026-08-07T02:32:22.793Z
---

> 🛑🛑 **CORRECTION 2026-08-06 — THIS MEMORY IS WRONG AS WRITTEN.** DTC `0x18` is a **boot-time
> reset-cause REPORT, not a live per-task deadline monitor.** `FUN_00014b3e` (the 4-task liveness
> checker) **never calls the DTC latch chain** — it snapshots the faulting PC, writes an NVM cause-code
> and triggers a reboot. The actual `FUN_00016de6(0x18, …)` lives in a **sibling**, `FUN_00014ba0`,
> gated on **reading that NVM cause-code back**, and is reached only from **state 1** of the dispatcher
> — i.e. a **boot pass**. ⇒ **`0x18` CANNOT be tripped by a running task.**
>
> The eligibility table below is still correct *as a table* (`0x18`'s record really is `0x3D01`); what is
> wrong is the **reachability** claim, and therefore the cave-timing consequence.
>
> ⊕ **The V75 probe cave is EXONERATED on timing.** Its 45 → 68 B growth costs **+17 cycles ≈ 212 ns**
> (V74 18 cy → V75 35 cy at 80 MHz) — **4–5 orders of magnitude below any window.** Keep the standing
> "budget a cave with a loop/divide/call" hygiene rule as hygiene; it is **not** a DTC-`0x18` constraint.

**DTC index `0x18` record is `0x3D01`** — record `0xB7FDC`, `record[+8] = 0x3D01`, `& 0x41 → 1`, the
**same value as monitors 0x1C and 0x1D**. ⚠ **But see the correction banner above: the trip is
BOOT-ONLY.**

Formula (validated against 4 known ground truths): `record = 0xB7D58 + (idx-1)*0x1c`, flag at
`record[+8]`, hard-eligible iff `& 0x41`.

| idx | record | value | verdict |
|---|---|---|---|
| 0x17 | 0xB7FC0 | 0x2D01 | HARD (shadow mismatch) |
| **0x18** | **0xB7FDC** | **0x3D01** | **HARD (cadence watchdog)** |
| 0x1C | 0xB804C | 0x3D01 | HARD (monitor M1) |
| 0x1D | 0xB8068 | 0x3D01 | HARD (monitor M2) |
| 0x23 | 0xB8110 | 0x0000 | not hard |
| 0x49 | 0xB8538 | 0x0000 | not hard |

⚠ **A subagent reported 0x18 as "NOT hard-fault eligible, same class as 0x23/0x49". That is WRONG.**
It computed the record as `0xB7FDE` — a 2-byte slip — and read `0x00` from inside the next field.
Off-by-2 in this table silently flips a hard fault into a benign one. Always recompute the record
address from the formula, never accept a quoted one.

**What 0x18 actually is** ~~the per-task call-cadence / overrun watchdog, raised via
`FUN_0001cba6 → FUN_00016de6(0x18, …)`, reachable from nearly every function in the base-assist/command
chain~~ — **CORRECTED 2026-08-06: a BOOT-TIME RESET-CAUSE REPORT.** The liveness checker
`FUN_00014b3e` records a cause-code to NVM and reboots; the DTC is raised on the *next* boot by
`FUN_00014ba0` from dispatcher **state 1**, gated on reading that cause-code back. **A running task
cannot set it.**

**~~Consequence — a real constraint on code caves.~~** (Retained for the arithmetic only — the
constraint itself is withdrawn.) Budget for the
V52C EMA cave (28 instructions, once per tick at `LAB_0007feac`, no loop/divide/call):

- optimistic (1 cyc/mem): 28 cycles = 0.35 µs = **0.035%** of the 1 ms period
- pessimistic (3 cyc/mem): 50 cycles = 0.63 µs = **0.063%**

Even a 100× error in the estimate leaves >90% headroom, so V52C cannot trip it.

**★ STANDING RULE (downgraded to HYGIENE 2026-08-06):** a cave on the 1 kHz path that introduces a
LOOP, a DIVIDE or a CALL should still be budgeted — but **not against DTC `0x18`**, which is boot-only.
Real cave timing to date: **V74 18 cycles, V75 35 cycles at 80 MHz (+17 cy ≈ 212 ns)** — nothing this
kit has built is within four orders of magnitude of any window.

See [[accord-v52c-complete-broad-lowpass]], [[control-task-tick-confirmed-1khz]] and
[[reference-accord-monitor2-corridor-and-the-c64a4-trap]] (the monitors that CAN be tripped by a running
task).
