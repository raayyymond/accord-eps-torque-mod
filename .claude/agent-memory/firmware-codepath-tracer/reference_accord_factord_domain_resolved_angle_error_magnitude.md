---
name: reference_accord_factord_domain_resolved_angle_error_magnitude
description: FactorD's index gp-0x6a10 is an unsigned angle-tracking-error magnitude (0.1deg/count), not torque; corrects a stale "driver torque" mislabel and clarifies gp-0x67fe's gate status is disputed, not settled.
metadata:
  type: reference
---

[EVIDENCE, disassemble_function + search_instructions this session, 2026-08-07] Full formula for the
damper's FactorD index, `gp-0x6a10` (see [[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm]]
for FactorD's own gate/LERP wiring):

```
gp-0x6a10 = FUN_00049a5a( gp-0x69ca - clamp(gp-0x69e0 + gp+0x641c, ±tp+0x733a) )   [abs(), then min(x,0xFFFF) -- a NO-OP]
```
`tp+0x733a` (0xC633A) byte-read = **130 = 13.0°**. The `min(result, 0xFFFF)` at `0x3fc90-94` is dead —
0xFFFF exceeds any real `abs()` of a 16-bit short — so **`gp-0x6a10` is a plain unclamped, unsigned
magnitude**, matching its all-non-negative LERP X-axis `[0,50,100,150,700]` → **`[0°,5°,10°,15°,70°]`** in
the confirmed 0.1°/count scale ([[reference_accord_angle_position_scale_0p1_deg_per_count_settled]]).

## Corrects a stale mislabel: `gp-0x69ca` is angle, NOT "driver torque"

`build_v30_tva.py`'s docstring calls `gp-0x69ca` "driver torque" in the context of a DIFFERENT function
(`FUN_000456a4`'s comp-term gate). That label is wrong. [EVIDENCE] `gp-0x69ca`'s only writers, full-image
`search_instructions`, are `FUN_0003bd7c`@0x3c09a (`= gp-0x6CC4 + wrap-corrected delta`, the established
angle accumulator) and a zero-reset. Neither reads `gp-0x4f60` (torque) to produce `gp-0x69ca`'s OWN
value. The V30 comment almost certainly predates the 2026-08-04 decompile that pinned this chain
([[reference_accord_near_centre_structure_hunt_angle_tracking_chain_found]]) and was never re-verified.
**Torque does enter one hop upstream**: inside `FUN_0003f884` (gp-0x69e0's sole writer), `gp-0x4f60`
forms an additive term on a sibling cell `gp-0x69c8 = gp-0x69ca + f(torque)`, which feeds `gp-0x69e0`'s
own next-cycle update — so the chain is torque-*modulated* angle-tracking error, not pure torque error
and not untouched pure angle error either.

## `gp-0x67fe ∈ {1,2}` gate reliability: DISPUTED, not settled — don't cite it as closed

`docs/HANDOFF-2026-07-28-v55-drive-oscillation-is-internal-and-v56-mute.md` §6.3 cites **V31P's on-car
measurement: `gp-0x67fe`==1 in 100% of frames including disengaged.** But
`docs/HANDOFF-2026-08-01-grind2-is-v62s-own-fix-at-high-frequency.md` (4 days later) explicitly re-opens
it: *"`gp-0x67fe`'s semantics are DISPUTED... Unresolved, and unmeasured by V66... Close it with a probe,
not an argument."* V66's own 3-bit gate probe dropped `gp-0x67fe` for cave-byte budget and it was never
re-measured. [EVIDENCE, this session, `FUN_0003bd7c` decompile] substate ∈{1,2} requires the underlying
EPS-readiness state `gp-0x6772` ∈ {4,5} (states 0-3/6-8 force substate=0) plus 3 more gates. `gp-0x6772`'s
writer `FUN_0003d4a2` is a large multi-state dispatcher (≥15 states) — structurally similar in shape to
`gp-0x67fa`'s own SM (which DOES sit at 4/5/11 near-universally on-car per multiple prior measurements),
but NOT decompiled fully this session, so this is [BELIEF] corroboration, not independent confirmation.
**Do not treat "gp-0x67fe reads 1 essentially always" as settled EVIDENCE — it rests on one 2026-mid
measurement a later session explicitly disputed and never re-closed.**

## FactorD candidate shape and the relay-risk gap

Since `gp-0x6a10` is an unsigned magnitude (not signed error), a useful `Y` shape is monotonically
NON-INCREASING over `X=[0,5,10,15,70]°`: e.g. `Y=[1024,1024,700,400,200]` — unity while tracking is tight,
tapering above ~10°. **Open, load-bearing gap before building this**: `gp-0x6a10`'s actual value during a
live grinding/ratchet episode is unmeasured. If it stays under the taper's onset during the bad
frequencies (plausible by analogy to the one on-record angular p-p figure for a 27.4 Hz limit-cycle event,
1.92° — a DIFFERENT cell, not gp-0x6a10 itself), the shape is safe by construction; if it swings into the
taper zone, D and E would co-modulate at the oscillation frequency, risking a new relay axis (V80's
"does not clip ≠ is not a relay" lesson applies identically here). Recommend a telemetry-only probe on
`gp-0x6a10` before any live edit.

## Build lineage: FactorD genuinely UNTESTED
[EVIDENCE, grep] `0xC9DB4`/`gp-0x6a10`/`gp-0x69ca`/`gp-0x69e0`/`gp-0x67fe`: zero hits as edit targets
across `build_v*_tva.py`. `FACTOR_D_PTRS` (V73-V77) appears only inside assert/print loops confirming it
unchanged, never as a write target.

## Related
[[reference_accord_near_centre_structure_hunt_angle_tracking_chain_found]] — source of the gp-0x6CC4 ->
gp-0x69ca -> gp-0x6a10 producer chain this file adds the exact disasm-confirmed formula to.
[[reference_accord_angle_position_scale_0p1_deg_per_count_settled]] — source of the 0.1°/count anchor.
[[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm]] — FactorD's own LERP/gate
wiring inside the damper evaluator.
[[reference_accord_v81_engagement_impedance_factorce_dominant_mechanism]] — the FactorC/E dose this
session's FactorD work is trying to find a non-rate-axis alternative to.
