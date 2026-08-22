---
name: reference_accord_v39_v48b_1khz_hook_precedent_correction
description: "CORRECTS today's earlier gp6c2c_gp6b26 memory claim that 'every flown cave is a read-only tap at ONE site (0x55C0E), the class has zero safe precedent.' That missed 0x3AC78 (V39, task 1/1kHz, FLOWN CLEAN, jr-trampoline into the aggregator FUN_0003aa2c itself) and mischaracterizes V48B (also task 1/1kHz -- its OWN postmortem exonerates clock rate explicitly; it bricked on a RAM collision + missing closed-loop check, not on 1kHz placement). A safe 1kHz stateless trampoline IS proven (V39); a safe 1kHz STATEFUL filter has one attempt (V48B, failed on two named, avoidable defects) not zero attempts at the class."
metadata:
  type: reference
---

# Hook-address census, kit-wide: only TWO addresses ever used, and the "zero 1kHz precedent" claim is wrong

Independent Python scan (2026-08-22, `damper-cave` subagent) of every `build_v*_tva.py` in this kit's
history for `HOOK...=0x...` assignments: **exactly two hook addresses have ever been used —
`0x3AC78` and `0x55C0E`.**

## `0x55C0E` — task 5, 100 Hz, CAN-TX chain. 49+ builds. Read-only telemetry. Never faulted.

The well-known one — `FUN_00055a98`, every probe build V49P onward.

## `0x3AC78` — task 1, 1 kHz. ONE build, V39, 2026-07-19. FLOWN CLEAN.

[EVIDENCE, `get_function_by_address(0x3AC78)` on stock `code.bin`] `0x3AC78` sits inside
**`FUN_0003aa2c` — the aggregator itself** (body `0x3aa2c-0x3ad73`), called from `FUN_0002214a` (task 1)
at mask `0xc30` = states `{4,5,10,11}`, gapless on road-reachable `{4,11}`. V39
(`build_v39_tva.py`) replaced `ld.h -0x6bd0[gp],r9` with `jr 0xC4B34` (4-byte trampoline), ran a 44-byte
cave that conditionally zeroed the live aggregator register `r24` based on driver-torque/LKAS-lane
comparisons, replicated the displaced load, jumped back via `jr 0x3AC7C`. **Flashed and road-tested —
zero faults** (`memory/v39-flashed-no-improvement.md`: "neither symptom fixed" — it falsified its own
hypothesis, not the hook mechanism). Allocated no new persistent RAM, only scratch registers.

## V48B — ALSO task 1, 1 kHz (`0x7FEAC` inside `FUN_0007f3f8`, `get_function_by_address` confirms body
`0x7f3f8-0x7ff07`; memory's claimed call chain `FUN_0002214a→FUN_0006bb08→FUN_0007f3f8` not
independently re-walked this session but the function-body/task-1 fact is). **Bricked — but its own
postmortem (`memory/reference-accord-v48b-flashed-catastrophic-ram-collision.md`) explicitly
EXONERATES the clock rate**: *"reached exactly once per call, no loop, no sub-rate divider... The
biquad is correctly clocked at fs=1000 — this was a worry and it is clean."* The two CONFIRMED root
causes were (1) a RAM collision (`gp-0x14FA`'s high byte aliased a live monitor/DTC status bitfield in a
register-indirect-dispatched I/O-mailbox array — see [[reference-accord-b7260-io-mailbox-array]]) and
(2) closed-loop stability was never checked (only single-frequency open-loop magnitude, against the
*wrong* loop). Both are GATE 1/GATE 2 failures, not sample-rate failures.

## ⇒ The correction

Today's earlier `reference_accord_gp6c2c_gp6b26_fun36c12_chain_and_v106_gate1` memory (same agent
lineage, `tq-lowpass` subagent) states: *"every flown cave is a read-only tap at ONE site (0x55C0E)...
the class has zero safe precedent."* **This is wrong on two counts**: it missed `0x3AC78` (a second
site), and it conflated "read-only tap" with the whole hook mechanism — V39's cave actively mutated a
live control-path register (r24), which is a materially bigger intervention than a telemetry tap, and it
still flew clean. **Do not repeat "zero 1kHz precedent" or "every cave is read-only" in future work on
this kit** — the correct statement is: **the trampoline mechanism at 1 kHz is proven safe (V39 stateless,
V48B's own clock-rate exoneration); what has exactly ONE attempt, not zero, is a STATEFUL FILTER at 1kHz,
and that attempt's failure is root-caused to two specific, named, avoidable defects — not to the sample
rate or the task.**

Related: [[reference_accord_fun41464_rate_signal_hub_and_fun34350_damper_hook]] (the hook this finding
supports) · [[reference_accord_gp6c2c_gp6b26_fun36c12_chain_and_v106_gate1]] (the memory being corrected —
retained, not deleted; its RAM-candidate and GATE-1 material stands, only the "zero precedent" framing is
wrong) · `memory/reference-accord-v48b-flashed-catastrophic-ram-collision.md`,
`memory/v39-flashed-no-improvement.md`.
