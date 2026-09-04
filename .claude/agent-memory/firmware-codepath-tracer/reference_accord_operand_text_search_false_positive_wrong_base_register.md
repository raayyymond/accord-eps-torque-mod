---
name: reference_accord_operand_text_search_false_positive_wrong_base_register
description: search_instructions operand-text match on a displacement (e.g. "0x6b2e") can hit a DIFFERENT physical byte when a function builds its own non-gp base register with movhi/mov and uses the same displacement against it. Always check the base register, not just the displacement, before counting a hit as a real writer.
metadata:
  type: reference
---

# `search_instructions` operand-text hits must be checked against the BASE REGISTER, not just the displacement — a worked example

Worked example, 2026-09-04, V282 image (`_v282_...plain_image.bin`), GhidraMCP `search_instructions`.

## The trap

Searching for writers to `gp-0x6b2e` (part of a second-writer census on the newly-found PID
publish cells, see [[reference_accord_fun28ea6_publishes_p_d_sum_output_orphan_safe]]) returned
5 matches:

```
0002a17c  st.h  r12, -0x6b2e, gp      <- real, FUN_00028ea6 (the live PID)
0002b064  st.h  r7,  -0x6b2e, gp      <- real, FUN_0002a93a (proven-unreachable orphan)
000556dc  set1  0x6, 0x6b2e, r18      <- FALSE POSITIVE
00055704  set1  0x5, 0x6b2e, r18      <- FALSE POSITIVE
0005572c  set1  0x4, 0x6b2e, r18      <- FALSE POSITIVE
```

The first two are real gp-relative accesses (`gp = 0xFEDF8000` fixed base) and match the expected
"one live writer + one dead-orphan writer" pattern seen throughout this function's neighbourhood.

The three `set1` instructions are `FUN_00055616`'s own code, and on inspection **`r18` is NOT `gp`**:
```
0002xxxx  movhi -0x121, r0, r18      ; r18 = 0xFEDF0000  (NOT 0xFEDF8000)
0002xxxx  set1  0x6, 0x6b2e, r18     ; sets bit6 of [r18 + 0x6b2e] = 0xFEDF6B2E
```
`0xFEDF6B2E ≠ 0xFEDF8000 − 0x6B2E (= 0xFEDF14D2)`. **Two completely different physical bytes that
happen to share the literal displacement text "6b2e".** This is a bit-flag block built by the
compiler with its own private base register (a common pattern for a dense DTC/flag table too far
from `gp` for a single-instruction gp-relative access), unrelated to the PID's cell.

## The rule

**Before counting an operand-text hit as a real reader/writer of a `gp-` (or `tp-`) relative cell,
confirm the THIRD operand (the base register) is actually `gp` (or `tp`).** `search_instructions`
matches on operand text only; it does not know or care which register the displacement is applied
to. A `movhi`+register-relative form with the same literal displacement number is a same-shape,
different-target false positive, and it will not announce itself — the operand string looks
identical to a real hit.

This is a distinct trap from the ld.bu odd/even displacement parity trap and the tp-vs-gp
off-by-0x1000 trap already on record — same family (operand-text pattern matching without checking
the addressing mode/base fully), different specific mechanism. Add to the standard adjudication
checklist: **displacement match is necessary, base-register match is required.**

## Method note

Caught by inspecting each hit's full instruction line rather than trusting the match count. The
`movhi -0x121,r0,r18` pattern (constructing a non-`gp`, non-`tp` base for a dense flag/bit table) has
now been seen at least twice this session (also at `FUN_00055616`'s DTC-flag `set1`/`clr1` calls
near `0x55E44`/`0x55E7E`/`0x55E9C`) — worth recognising the pattern on sight: `movhi` immediately
followed by `set1`/`clr1` on a small literal displacement is very likely this flag-table idiom, not
a `gp`/`tp` access, even when the displacement number coincides with one you're tracking.
