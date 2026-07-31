---
name: reference_accord_boost_amp_series_question_resolved_not_series
description: RETRACTED 2026-07-30 (same session). The original claim here (y1/0xD28DC is a dead end) was a tracing error -- y1 DOES reach the output. See reference_accord_boost_amp_series_question_corrected.md for the corrected trace.
metadata:
  type: reference
---

**🛑 RETRACTED. Kept only so the `[[link]]` from other memory files still resolves to an explanation.**

The original claim in this file — "only `0xD2888`(y4) is live; `0xD28DC`(y1) is computed, slew-limited, and
written ONLY to its own persisted state `gp-0x69bc`, never consumed" — was WRONG. The error: the trace
that produced it stopped reading the disassembly at `0x34c00` (right after the blend) and concluded "r25
never appears again" without checking the next few instructions. **`r25` (the blended y1 value) IS an
operand two instructions later, at `0x34c1c` (`mulu r25,r28,r0`).** Team lead caught this by pointing at
the specific `>> 0xe` multiply and the `gp-0x6986` cell, which the original trace had misread/confused
with `gp-0x6988` (a different, unrelated cell used later in the y4 chain).

**See `reference_accord_boost_amp_series_question_corrected.md` for the corrected trace: y1 DOES reach
`gp-0x6bbe`, through a nonlinear path (multiplied by `clamp(gp-0x6986)`, a friction LERP, and
`sign(gp-0x6a02)`, then DIFFERENCED against `gp-0x6a56` and clamped ±12000, gated by a 4-state ramp SM
that zeroes it in some but not all reachable states) — not a clean series product with y4, but both
curves are live.**

Lesson for this kit's record: a register-level trace is only as good as how far forward it's followed.
"I checked N instructions and found no further use" is a bounded negative, not a proof of absence, unless
the bound is the function's actual exit point (return/dispose) or a byte-scanned cross-function boundary.
The `gp-0x69bc`-has-no-external-readers byte-scan claim in the superseding memory is still correct and
still relevant (it rules out OTHER functions reading it) — what was wrong was concluding from that alone
that the value had no use *within* `FUN_00034a72` itself.
