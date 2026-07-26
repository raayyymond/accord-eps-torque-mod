---
name: reference_accord_fun3d4a2_hardware_phase_disable_dispatcher
description: Accord TVA-A160 FUN_0003d4a2 is the FOC-mode/relay sequencer that actually disables the 3 motor phase-driver (CSIG) channels; gp-0x676e==4 is the exclusive, one-shot dispatch code; anchor at 0x3de6c (movea 0x3f,r0,r6) is a cleaner "physical cut" telemetry site than the upstream gate-firing flags (gp-0x6809, decider r12, FUN_0003c7fc bail).
metadata:
  type: reference
---

# FUN_0003d4a2 — FOC-mode/relay hardware dispatcher, THE physical motor-off site (2026-07-13)

Verified via Ghidra MCP (`program="code.bin"`, gp=0xFEDF8000, tp=0xBF000), `decompile_function` +
`disassemble_function` (full raw asm obtained, ~700 instrs) + `search_instructions` (program-wide,
185116 instrs) + `read_memory` byte confirmation. Read-only session, no writes.

## What this function is
`FUN_0003d4a2` (0x3d4a2–0x3debb) is a large state machine keyed on `gp-0x6772` (FOC-mode byte, 0–8,
the SAME byte [[reference_accord_deliver_commit_gate5_gate7_trampoline_anchors]]'s `FUN_0003d04c` sets
and [[reference_accord_fun3c7fc_trampoline_anchor]]'s bail at 0x3c93c resets to 0). Its job is to decide,
each cycle, what to do with the 3 motor phase-driver hardware channels — and it writes that decision into
`gp-0x676e` (0–8), which is consumed ONCE at the tail of the SAME function.

**Caller:** sole caller is `FUN_00022ca0` (unconditional call, 0x22dd8) — the SAME function that is the
sole caller of `FUN_00041eec` (the torque fuser, per `reference_accord_arb_input_cluster`), i.e. this runs
every control cycle. `get_xrefs_to(0x22ca0)` returned no static callers — FUN_00022ca0 is itself likely
installed via a function-pointer/periodic-task table (not statically called), consistent with being the
main per-cycle steer-control entry.

## gp-0x676e dispatch — exhaustively confirmed exclusive [V]
Program-wide scan (`search_instructions operand_pattern="676e"`) returns 33 hits total: ALL inside
`FUN_0003d4a2` except one write in sibling `FUN_0003debc`. There is no other reader of gp-0x676e anywhere
in the 1MB image — no parallel/bypass path around this dispatch.

At the tail (raw disasm, byte-confirmed via `read_memory`):
```
0003dd38  ld.bu -0x676e[gp],r7      843f9398   ; r7 = gp-0x676e
0003dd3c  cmp r0,r7
0003dd3e  bne 0x0003dd44                        ; r7==0 -> jr 0x3deb8 (no relay action this cycle)
...
0003dd44  cmp 0x1,r7 / bne 0x3dd8a               ; r7==1 branch (partial-enable sequence A)
0003dd8a  cmp 0x2,r7 / bne 0x3ddce               ; r7==2 branch (partial-enable sequence B)
0003ddce  cmp 0x3,r7 / bne 0x3de68               ; r7==3 branch (partial-enable sequence C)
0003de68  cmp 0x4,r7        643a
0003de6a  bne 0x0003deb8    fa25                  ; NOT taken = r7==4 CONFIRMED, only remaining case
0003de6c  movea 0x3f,r0,r6  20363f00              ; <-- RECOMMENDED ANCHOR (see below)
0003de70  mov 0x1,r7        013a
0003de72  mov 0x0,r8        0042
0003de74  mov 0x1,r9        014a
0003de76  jarl 0x00016de6,lp                      ; FUN_00016de6(0x3f, 1, 0, 1)  enable-arg=0
0003de7a  mov 0x1,r6 / movea 0x3f,r0,r7
0003de80  jarl 0x00046aea,lp                      ; FUN_00046aea(1, 0x3f)  (companion/commit call)
0003de84  movea 0x41,r0,r6 / mov 0x2,r7 / mov 0x0,r8 / mov 0x1,r9
0003de8e  jarl 0x00016de6,lp                      ; FUN_00016de6(0x41, 2, 0, 1)  enable-arg=0
0003de98  jarl 0x00046aea,lp                      ; FUN_00046aea(1, 0x41)
0003de9c  movea 0x40,r0,r6 / mov 0x2,r7 / mov 0x0,r8 / mov 0x1,r9
0003dea6  jarl 0x00016de6,lp                      ; FUN_00016de6(0x40, 2, 0, 1)  enable-arg=0
0003deb0  jarl 0x00046aea,lp                      ; FUN_00046aea(1, 0x40)
0003deb4  st.b r0,-0x676e[gp]                     ; clears dispatch code -> one-shot/edge-triggered
0003deb8  dispose ...
```
All THREE motor phase channels (0x3f/0x40/0x41 — same 3 channels as `reference_accord_lkas_path_wiring`'s
CSIG dispatch) get `FUN_00016de6(chan, mode, enable=0, 1)`. This all-enable=0 pattern is UNIQUE to the
r7==4 dispatch — states 1/2/3 (the other branches, not detailed here) each call at least one channel with
enable=1. `FUN_00016de6` itself: Ghidra decompile FAILS with a struct error citing `CSIG0_B1_registers_t`/
`CSIG0RX0` — independently confirms this is the CSIG motor-driver-IC serial-interface peripheral family
(matches prior-session naming in `reference_accord_lkas_path_wiring`). Raw disasm of `FUN_00016de6` (full,
0x16de6–0x16f5a) shows a heavily-gated conditional path ending in `st.h r14,0x0[r24]` at 0x16f34 (same
address prior memory already pinned) — the actual peripheral register write. Did NOT trace
`FUN_00016634`/`FUN_00016b66`/`FUN_00016dc0`/`FUN_0001611e`/`FUN_00018738` (the sub-helpers) to confirm
bit-level semantics of the enable arg — the "disables the channel" reading is [I], strongly supported by
the argument-pattern contrast (all-0 only here) and the CSIG-peripheral identity, but not verified down to
the register-bit level.

## RECOMMENDED TRAMPOLINE ANCHOR: 0x3de6c — `movea 0x3f, r0, r6`
- **Bytes:** `20 36 3f 00` (4 bytes), byte-confirmed via `read_memory(0x3de68, 16)`.
- **Not pc-relative, not a branch** — `movea` is pure immediate arithmetic (r6 = r0 + 0x3f), fully
  relocatable into a cave and re-executable verbatim.
- **4-byte aligned** (0x3de6c mod 4 == 0), exactly 4 bytes — clean 1:1 `jr <cave>` replacement slot.
- **Exclusive landing point:** reached only after the chained `cmp/bne` sequence excludes gp-0x676e ==
  0/1/2/3 and confirms ==4 — this is THE hardware-disable dispatch, downstream of every upstream gate
  (decider fire, Gate5/Gate7, angle-deadband bail, or anything else that drives gp-0x6772/gp-0x676e state
  transitions) — a ground-truth "motor commanded off" signal, not a proxy for one specific upstream cause.
- **Register liveness — unusually generous:**
  - `r6`: about to be overwritten by the anchor itself; its incoming value traces back to a stale leftover
    from an earlier `jarl FUN_0003d46c` call (0x3dd1a) with nothing reading it in between — DEAD.
  - `r7`: holds 4 (just consumed by the preceding `cmp`), overwritten at 0x3de70 before any read — DEAD.
  - `r8`, `r9`: overwritten at 0x3de72/0x3de74 before any read — DEAD.
  - `lp`: about to be clobbered by the `jarl` at 0x3de76 regardless of the stub — safe to use for the
    stub's own `jarl <cave>,lp`.
  - PSW: last set by `cmp 0x4,r7` @0x3de68, consumed only by the immediately-following `bne` — dead here.
  - **Net: r6/r7/r8/r9/lp are all free for stub scratch**, constrained only to leave r6=0x3f before falling
    through to 0x3de70. More headroom than either `reference_accord_fun3c7fc_trampoline_anchor`'s 0x3c93c
    (must preserve r28) or `reference_accord_decider_shared_epilogue_trampoline_anchors`'s 0x40e64 (must
    preserve r12, which IS the payload).
- **Return target:** fall through to `0x3de70` (`mov 0x1,r7`) after reproducing r6=0x3f.
- **CRC note:** not checked this session whether 0x3de6c falls inside the same `[0x13000,0xC4FFC)` code
  CRC block documented in `reference_accord_telemetry_ram_hook_a160` — very likely yes given the address
  range, but confirm before building.

## Open / not resolved this session
- Did not trace WHICH of gp-0x6772's many upstream writers (across ~14 functions incl. FUN_0003bd7c,
  FUN_00040884, FUN_00040906, FUN_00040e7e) is the dominant path from the ENGAGED-state gentle-EME
  scenario specifically into gp-0x676e==4. Structurally plausible link: gp-0x676e==4 transitions inside
  FUN_0003d4a2 repeatedly reference the SAME angle/torque scratch sentinel slot `gp+0x6470`
  (`0x7fff`/`-0x8000`) that [[reference_accord_fun3c7fc_trampoline_anchor]]'s angle-deadband gate writes —
  suggestive but NOT byte-traced end to end this session (inference, not proof).
- Did not connect this dispatch forward to the CAN 399 STEER_STATUS builder (`FUN_00055c42`, reads
  gp-0x6807/6806/6880/6804 per `reference_accord_can_tx_399_427_bitmap`) to prove the same cycle that
  disables the phases also flips STEER_STATUS to no_torque_alert_2. Recommended next step: either trace
  gp-0x6772's other writers to find whichever sets gp-0x6807, or simplest — add gp-0x676e==4 as a 6th V31P
  telemetry flag bit and correlate live against CAN 399 on the next drive (empirical > further static
  tracing given how deep this state machine goes).

## Related
[[reference_accord_deliver_commit_gate5_gate7_trampoline_anchors]] — FUN_0003d04c, sets gp-0x6770/gp-0x6772.
[[reference_accord_fun3c7fc_trampoline_anchor]] — angle-deadband gate, resets gp-0x6770, shares the
gp+0x6470 scratch slot with this function's transitions.
[[reference_accord_decider_shared_epilogue_trampoline_anchors]] — FUN_00040d58, the higher-level decider
whose firing causes FUN_00041222 to skip the deliver-commit that would otherwise keep this state machine
in a "deliver" mode.
[[reference_accord_lkas_path_wiring]] — original identification of FUN_00016de6/0x16f34 as the CSIG
motor-driver write; this memory confirms the SAME 3 channels (0x3f/0x40/0x41) and adds the disable-dispatch
caller.
[[reference_accord_arb_bvar1_full_enumeration]] — the gp-0x6809 arb gate, now confirmed (separately) to
reach gp-0x6b3c but likely NOT the right discriminating signal — see companion memory
`reference_accord_arb_gp6809_reaches_gp6b3c_not_deadsink`.
