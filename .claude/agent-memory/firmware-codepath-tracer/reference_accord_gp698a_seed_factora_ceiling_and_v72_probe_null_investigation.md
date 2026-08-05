---
name: reference_accord_gp698a_seed_factora_ceiling_and_v72_probe_null_investigation
description: V72's damper-presence probe (bit4 = |gp-0x6bd0|>=64) failed its own positive control, reading 0 in 87,940/87,940 frames including highway where stock's own damper should fire. Traced the multiply chain fresh -- FactorB/C/D/E all check out live per team-lead's own dump, but there IS a missing 5th multiplicative term, gp-0x698a ("seed"), a MIN-reduced Q10 ceiling-1024 confidence-like value from a deep generic plausibility/redundancy state machine whose physical identity was not resolved. Write mechanism and Q-format both ruled out as the cause. Recommends probing gp-0x698a directly rather than more static tracing.
metadata:
  type: reference
---

# gp-0x6bd0 reads 0 always -- is FactorA/seed the reason? 2026-08-05

Task: team-lead's V72 damper-presence probe rung (`|gp-0x6bd0|>=64`) read **0 in 0/87,940 frames**,
including 0/34,275 above 35 km/h where FactorC's own gate is open and stock damping should already be
present. Team-lead independently dumped FactorB/C/D/E from `_v72_plain_image.bin` and stock and found
all four nonzero/live (`430*927>>10=389` at V72's creep values). Contradiction: the calibration says
`gp-0x6bd0` should be nonzero, the probe says it never is. Four candidates given: (1) a factor not yet
found ("FactorA"), (2) the seed (design note: "delivered authority is FactorC×FactorE>>10 at seed<=1024"),
(3) the write itself (shadow-lockstep guard), (4) Q-format/scaling.

## THE CHAIN, RE-DECOMPILED FRESH [EVIDENCE: FUN_00034350]

```c
uVar7 = ((((uVar10*(uVar10<0x401)+(uVar10>=0x401)*0x400) * uVar7 >> 10) * uVar13 >> 10) * uVar21 >> 10) * uVar16 >> 10;
if (0 < *(short*)(gp-0x6abe)) uVar7 = -uVar7;
```
`uVar10 = clamp(*(gp-0x698a), 0, 1024)` = **seed**, `uVar7`=FactorB, `uVar13`=FactorC, `uVar21`=FactorD,
`uVar16`=FactorE. **FOUR chained `>>10`s**, one per factor. ⇒ Candidates #1 and #2 are THE SAME
QUANTITY -- team-lead's "the seed" already named in the design note (bounded `<=1024`) is exactly the
missing 5th multiplicative factor, not documented as such because it lives in RAM (min-reduced each
cycle), not a static `0xD2xxx`-block LERP table like B/C/D/E, so a factor-table dump never surfaces it.

## SEED'S MECHANISM -- confirmed, CEILING not floor [EVIDENCE]

Sole writer `FUN_00026c80` (confirmed via `search_instructions operand=698a`, 5 real hits after
excluding 1 `be`-branch-target false positive: writer @0x27384, readers @0x344d8(FUN_00034350, our
target) and @0x28650/0x28bdc(FUN_00027b0a, a monitor)). The reduce:
```c
uVar42 = uVar42*(uVar42<uVar29) + uVar29*(uVar42>=uVar29);   // seeded uVar42=0x400=1024
```
This is a **MIN-reduce** (when new sample bigger, OLD smaller value kept; when new smaller-or-equal,
taken), over 11 samples from `gp-0x61e8[0..10]`. ⇒ **seed starts at a ceiling of 1024 (Q10 unity) and
can only be pulled DOWN, never above.** Independently confirmed by monitor `FUN_00027b0a`, which faults
(DTC `0x3cea`/`0x3ce9`) if either of seed's two sibling min-reduces (`gp-0x6986`, `gp-0x6988` -- same
producer, same pattern) is EVER measured `>1024` -- i.e. 1024 is the DESIGNED ceiling by construction,
not an inference.

**What feeds the 11-sample array is generic infrastructure, not a nameable signal** -- traced 2 more
functions deep and it doesn't bottom out:
- `gp-0x61e8[i]` (the array that gets min-reduced) is written by an 8-state dispatch inside
  `FUN_00026c80` itself, keyed on a per-channel state byte `tp+0x5124+i`. States 6/7 write a flat 1024
  (reset/unity). States 0,2,3,4,5 (+ default) instead copy a PERSISTENT rolling value from
  `gp-0x6230+i`.
- `gp-0x6230[i]` is written by `FUN_00025c32` (confirmed sole non-trivial writer of the
  `-0x62e0`/`-0x6230`-family arrays, `search_instructions operand=62e0`, 6 real hits after excluding
  false positives). This is its OWN multi-state fault-confirmation/debounce machine (states 0-5, timers
  against cals `tp+0x51ac`/`tp+0x74fb`) operating on a generic `byte*` struct -- the shape of shared
  library code for sensor-redundancy/plausibility checks generally, not a signal-specific function.
  **The caller that would give the physical identity (what `param_1` points at for THIS use) was not
  found this session** -- chased 3 functions deep (`FUN_00034350`→`FUN_00026c80`→`FUN_00025c32`) and
  it is still generic infrastructure, not a nameable physical quantity.

⇒ [BELIEF, unresolved] Cannot say whether seed typically sits at 1024 (ceiling, "full confidence" --
would mean seed is NOT the explanation for the observed null) or is often well below it in ordinary
driving (would mean it IS the explanation, and both FactorC/E edits are vacuous on this signal path).

## CANDIDATE #3 (write mechanism) -- RULED OUT [EVIDENCE]

The store to `gp-0x6bd0` is a standard 3-way symmetric clamp `clamp(uVar7,-uVar10_ceiling,+uVar10_ceiling)`
gated by a shadow-lockstep check (`gp-0x6bd0`==`gp-0x4cf2` before write). On mismatch it calls
`FUN_0006b9fa`, decompiled: a generic 2-line fault stub (`FUN_0006ce7c(4)`, the kit's standard
DTC/fault-escalation entry used dozens of times elsewhere). If this fired every cycle the drive would
show hard faults; V72 flew fault-free. Not the explanation.

## CANDIDATE #4 (Q-format) -- NOT A BUG, conditional on seed=1024 [EVIDENCE]

Team-lead's assumed `FactorC×FactorE>>10` model is exactly what the 4-stage chain reduces to WHEN
seed=1024, FactorB=1024, FactorD=1024 (both confirmed flat/unity in the dump) -- the extra `>>10`s on
seed/FactorB/FactorD are no-ops at unity. No scaling bug found, but this closure is conditional on the
open item above.

## RECOMMENDED V73 RUNG

`gp-0x698a`, `ld.hu -0x698a[gp]`, unsigned halfword, Q10, ceiling 1024 by design. Thermometer pair
matching the kit's proven `a`-probe idiom (V72 bit6/bit5):
```
bit_hi = gp-0x698a >= 1024   -- "at ceiling / full confidence"; expected TRUE if seed is NOT the cause
bit_lo = gp-0x698a >= 512    -- coarse floor; bit_hi=>bit_lo is a monotone invariant (miswiring detectable)
```
If `bit_hi` reads ~always-1 including at highway: seed is refuted, look elsewhere (re-open #3/#4 more
skeptically, or check the probe's own read site independently). If `bit_hi` reads 0 with any regularity:
seed is confirmed as (at least part of) the explanation, Lever B/C are vacuous on this path, and any
ratchet-fix credit belongs to a different lever (most likely the rate lane).

## Related
[[reference_accord_factorc_e_damper_full_trace_r24r26_parallel]] -- the base trace this session
extends; corrects its "MAX-reducer" framing to MIN-reduce/ceiling in place.
