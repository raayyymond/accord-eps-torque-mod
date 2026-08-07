---
name: reference_accord_ceiling_race_v74_manual_reconciliation_and_dtc_index_sharing
description: Reconciles the FUN_00034350/FUN_000347b8 gp-0x6bd0 ceiling-race monitor against "V74 also hard-faulted in manual, damper byte-stock" -- structurally CANNOT be the mechanism in mode 24 (gp-0x6bd0 forced 0). Also flags DTC indices 0x1c/0x1d are SHARED by 4 independent monitors, so "fault_id 28/29 fired" does not by itself identify this monitor. Measures the real T1/T2 race gap at ~1-3us via instruction-adjacent disasm.
metadata:
  type: reference
---

2026-08-06, dispatched by team-lead ("SlewFix") to test H: "gp-0x6bd0 slews between an int check and a
float check, opening a fault corridor." Fresh decompile+disasm of `FUN_00034350`/`FUN_000347b8`,
`code.bin`. Extends [[reference_accord_gp6bd0_damper_own_ceiling_consistency_monitor_fun347b8]],
[[reference_accord_v75_step_size_hypothesis_refuted_and_fun347b8_precise_trigger]],
[[reference_accord_v75_float_mirror_search_negative_and_ceiling_race_mathematically_unreachable]] — does
not contradict any of them, adds two new closures.

## H needs a variable substitution [EVIDENCE]
gp-0x6bd0 does not slew in the window that matters — nothing writes it between `FUN_00034350`'s write and
`FUN_000347b8`'s read of it (fresh disasm: `0x347bc ld.h -0x6bd0[gp],r7` is literally FUN_000347b8's 2nd
instruction). The race variable is **gp-0x6ac2** (the ceiling table's own index), independently sampled at
T1 (inside `FUN_00034350`'s own ceiling lookup, end of function) and T2 (`0x347c0 ld.hu -0x6ac2[gp],r14`,
FUN_000347b8's 2nd instruction). Straight-line code, no calls, in between — **the T1->T2 gap is ~1-3us at
40MHz** (rough instruction count of FUN_00034350's post-ceiling tail + jarl + FUN_000347b8 prologue), ~1000x
shorter than a 1kHz tick. Under normal (non-preempted) execution gp-0x6ac2 cannot move in that window; it
could only move if a 1kHz interrupt lands exactly inside it (architecturally plausible — no
`__disable_irq` bracket visible around the FUN_00034350/FUN_000347b8 pair in FUN_00022ca0 — but not proven
from static bytes; would need RTOS/interrupt-priority tracing not attempted).

## NEW: mode 24 (manual) structurally cannot trip this monitor [EVIDENCE]
Mode 24's FactorC Y[0]=0, byte-stock (per [[reference_accord_fun34350_purely_multiplicative_and_mode_index_debounce_chain]]),
forces gp-0x6bd0≡0 always (pure multiplicative chain, no additive rescue). At gp-0x6bd0=0:
`fVar5=0/1024=0`, `diff = 0 - clamp(0,±ceiling) = 0` identically, for ANY ceiling value on either side of
the T1/T2 race. **⇒ FUN_000347b8/FUN_00034350's own check (fault codes 0x417a/0x4179, DTC idx 0x1d/0x1c)
cannot be the mechanism behind a hard-fault that occurred in manual/mode-24 driving.** If a V74/V75-era
manual-mode fault is confirmed to have fired via THIS specific monitor, that would falsify something else
in this trace (worth a byte re-check, not assumed here) — as currently understood, it rules this monitor
out for that case.

## NEW: DTC indices 0x1c/0x1d are SHARED buckets across 4 independent monitors [EVIDENCE, cross-referencing reference_accord_hard_shutdown_full_map_v75_incident.md]
Both `FUN_000347b8` (code `0x417a`) and `FUN_00034350`'s own entry check (code `0x4179`) report through
`FUN_00016de6(0x1d,...)`/`(0x1c,...)` respectively — but so do **Monitor 1** (`FUN_00042af8`, shaper,
idx 0x1c), **Monitor 2** (`FUN_00044666`, corridor, idx 0x1d, gated by `0xC74A4`), and **`FUN_00045a20`**
(undebounced comp-bound check, code `0x3a09`, idx 0x1d, 1kHz task). **A DTC/fault-history read showing
"index 28 or 29 fired" does NOT by itself identify Trip Surface A (this damper-ceiling monitor)** — it
requires the specific inner code (`0x417a`/`0x4179` vs `0x3f1b`/`0x3a09`/whatever Monitor 1 passes) to
discriminate, which needs either `FUN_0004613e`/`FUN_000462e6`'s logged param or a source-level DTC
extended-data field, not just the top-level index.

## Standing (unchanged) design conclusion, restated for the record
The guaranteed-safe, timing-independent design rule for THIS monitor is a **magnitude** bound, not a slew
bound: keep max achievable `|gp-0x6bd0|` (full speed x rate grid, every mode) `<= ceiling floor` (512 raw
counts today, `Y[0]` of `0xC77A0[mode]`) — because the ceiling table is monotone non-decreasing with that
hard floor, so `ceiling(T2) >= floor >= gp-0x6bd0` always holds regardless of gp-0x6ac2's race timing. This
is the SAME criterion the prior full-grid sweep already used to derive `C_Y0_max=566` — that number IS
the "guaranteed safe" answer, already on record, not new this session.

## Related
[[reference_accord_gp6bd0_damper_own_ceiling_consistency_monitor_fun347b8]],
[[reference_accord_v75_step_size_hypothesis_refuted_and_fun347b8_precise_trigger]],
[[reference_accord_v75_float_mirror_search_negative_and_ceiling_race_mathematically_unreachable]],
[[reference_accord_v75_true_headroom_e_exhausted_c_max_566]] — source of the 566/zero-E-headroom numbers
restated here. [[reference_accord_fun34350_purely_multiplicative_and_mode_index_debounce_chain]] — source
of the mode24-forces-zero fact used in the new reconciliation.
[[reference_accord_hard_shutdown_full_map_v75_incident]] — source of the 4-monitor DTC-index-sharing table.
