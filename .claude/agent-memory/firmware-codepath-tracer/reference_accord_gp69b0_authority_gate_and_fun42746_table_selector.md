---
name: reference_accord_gp69b0_authority_gate_and_fun42746_table_selector
description: "gp-0x69b0 (the LKAS engage-ramp AUTHORITY value, 0..0x8000 Q15) directly zero-gates FUN_0002a93a's entire arb-curve computation (the function immediately following the old 'dead code gap' 0x2a507-0x2a93a -- that gap conclusion was about FUN_0002a30e specifically, NOT this function, which is very much live and writes gp-0x6b2e/6b32/6b34/6b36, the curve-clamped LKAS demand chain). Separately, FUN_00042746 reads gp-0x6806 transitions paired with gp-0x69b0 settling at an endpoint (0 or full-scale) to select between coefficient-table sets (DAT_0000e012..e018, stride 0x24, indexed by gp-0x67e2) -- a genuine, NEW, unresolved (b)-class engagement-linked table-selection candidate, not previously in kit memory."
metadata:
  type: reference
---

# gp-0x69b0 AUTHORITY gate + a new (b)-class lead (FUN_00042746) — 2026-08-04

Dispatched while enumerating LKAS-engagement routes for team-lead. Builds on
[[reference_accord_fun28ea6_ramp_statemachine_gp6806_gp69b0_decoded]] (the ramp SM itself, and its
open `gp-0x1426` producer question).

## `gp-0x69b0` zero-gates FUN_0002a93a's entire computation [EVIDENCE, fresh decompile]

`search_instructions(operand_pattern="69b0")`: 45 hits, 43 inside `FUN_00028ea6` (the ramp SM itself,
already documented), 2 outside (`0x2a942` in `FUN_0002a93a`, `0x42846` in `FUN_00042746`); the remaining
2 raw hits are `br 0x669b0` branch-target-text collisions, excluded (standard false-positive class).

`FUN_0002a93a` (body starts immediately after the address range `[0x2a507,0x2a93a)` that
[[reference_accord_gp6806_phase_flag_and_dead_writer_split]] established as dead code for a DIFFERENT
function, `FUN_0002a30e` — that "dead" finding does not extend to `FUN_0002a93a`, which is a distinct,
large, live function): its opening gate is
```c
if (((*(short *)(gp-0x69b0) == 0) && (*(char *)(gp-0x6805) != '\x01')) || (param_1 == 0)) {
    // whole curve computation short-circuited: outputs zeroed / sentinel (iVar13=0x7fffffff)
    goto LAB_0002b054;
}
```
i.e. when the AUTHORITY ramp is at zero AND there is no active engage request pending
(`gp-0x6805`, the ramp SM's own trigger bit, sourced from `gp-0x1426` — producer still unresolved), the
ENTIRE function is bypassed and its outputs zeroed/sentineled. This function's outputs
(`gp-0x6b2e`/`gp-0x6b32`/`gp-0x6b34`/`gp-0x6b36`) are exactly the "curve-clamped LKAS demand /
integrator chain" [[accord-lkas-path-wiring]] already traced into the arb's final output `gp-0x6b3c`
(PATH-A) — now confirmed LIVE, not inert, per
[[reference_accord_patha_arb_is_live_not_inert_correction]]. **This is a genuine (a)/(c)-class
engagement gate**: while un-ramped (LKAS not engaged, no pending request), this whole arb sub-computation
is held at a defined zero/sentinel state; once the ramp is nonzero (engaging or engaged), the full curve
computation runs (not scaled proportionally to ramp magnitude within this function — it's a binary
gate, not a continuous multiply, at least within this function's own body).

## `FUN_00042746` — a NEW (b)-class lead: table selection on engagement-ramp transitions [EVIDENCE, partial]

```c
cVar2 = gp-0x6806;             // FSM phase / ~latActive proxy (99.98% correlated w/ LKAS engaged, per V67 on-car probe)
sVar4 = gp-0x69b0;              // AUTHORITY ramp, signed read (0x8000 reads as -0x8000)
if ((cVar2 != gp-0x67e1) && (sVar4 == -0x8000 || sVar4 == 0)) {
    // gp-0x6806 CHANGED since last check, AND ramp has settled at an endpoint (full-scale or zero)
    gp-0x68ac = 1;
    gp-0x67e1 = cVar2;   // latch new value
}
```
Earlier in the SAME function, `gp-0x67e2` (a small state byte) selects between coefficient/constant
records from 6 distinct tables (`DAT_0000e012..e018`, stride `0x24`, indexed further by
`FUN_00057f8e()`'s return value), writing results to `gp-0x674f` and `gp-0x63fd`(byte, offset from a
different base). **This has the shape of a filter-coefficient-set or mode-record selector that changes
specifically on a settled LKAS-engagement transition** — a genuine, NEW (b)-class candidate not
previously in kit memory. **NOT fully characterized this session**: `gp-0x67f6`/`gp-0x67e2`'s own
identity/consumers, what `DAT_0000e012..e018` physically represent, and `gp-0x674f`/`gp-0x63fd`'s
downstream consumers were not traced. Flagged as the single most promising next hop for a genuine
(b)-class ("engagement selects a different table") mechanism in this firmware.

## Related
[[reference_accord_fun28ea6_ramp_statemachine_gp6806_gp69b0_decoded]] — the ramp SM producing both
gp-0x6806 and gp-0x69b0, including the still-open `gp-0x1426` (CAN?) producer question.
[[reference_accord_patha_arb_is_live_not_inert_correction]] — confirms FUN_0002a93a's output chain is
live, raising the stakes on this gate.
[[reference_accord_gp6806_phase_flag_and_dead_writer_split]] — source of the gp-0x6806 phase semantics
and the (unrelated) dead-code gap this entry clarifies does not include FUN_0002a93a.
