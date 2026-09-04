---
name: feedback_check_kit_memory_before_calling_a_function_dead
description: Before reporting any "function X is dead / unreachable / has no callers" verdict, grep this agent-memory directory and memory/ for the address first — this kit has documented live-with-zero-discoverable-callers functions, and a passing scanner control does not license a dead-code claim.
metadata:
  type: feedback
---

Never ship a "dead code / unreachable / no callers" verdict until you have grepped
`.claude/agent-memory/firmware-codepath-tracer/` and the kit's `memory/` for the address. A passing
positive control proves your **scanner** works; it does not prove the **claim**.

**Why:** on 2026-09-03 I reported to `loopshape` that the region holding a second reader of the LKAS
output-lag poles was "probably dead," on three passing jarl controls plus agreeing Ghidra nulls. Both
methods were sound and both nulls were real. But `FUN_0002a30e`, at the same addresses, had produced
the *identical* null on 2026-07-13 for a function that is demonstrably LIVE — it writes STEER_STATUS=4,
observed on CAN 399 with ~99 ms durations, and is reached by an indirect call nobody has found yet.
The fact was already written down in this very directory. I had to retract inside the same session, and
a build sized on "that reader is dead" would have been sized wrong. In the same pass I also asserted a
per-0x1000-page CRC model that an existing memory explicitly records as having "nearly caused a brick"
(the blocks are a linked list; `[0x13000, 0xC4FFC)` is one block covering all app code).

**How to apply:** the moment a null becomes load-bearing — before writing it into a report, not after —
run `ls`/`grep` over the memory directory for the function address, the cell address, and the
neighbouring 0x1000. Two cheap greps. Then state the verdict as UNRESOLVED with the specific untested
call form named (`jarl [reg]` / `jmp [reg]` dispatch was the gap here), rather than as a belief about
liveness. Report an uncontrolled test as DISCARDED, never as a null: my disp32 and function-pointer-dword
tests both returned NONE for the known-live control too, so neither carried information.

Corollary that did work and is worth repeating: pairing every scan with a positive control, and running
Ghidra and a raw Python byte scan as two independent methods and set-differencing them. That is what
surfaced the two reader sites `search_instructions` was blind to. Keep doing that — just do not let a
controlled scanner talk you into an uncontrolled conclusion.

Related: [[reference_accord_lkas_pid_pole_cell_gate1_census_2a508_second_reader]],
[[reference_accord_fun2a30e_steerstatus_debounce_statemachine]],
[[reference_accord_crc_block_lookup_and_cave_hook_template]],
[[feedback_audit_your_own_claims_before_others_act_on_them]]
