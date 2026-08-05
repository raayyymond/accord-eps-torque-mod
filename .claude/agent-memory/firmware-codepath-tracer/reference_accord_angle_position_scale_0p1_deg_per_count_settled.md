---
name: reference_accord_angle_position_scale_0p1_deg_per_count_settled
description: Settles the internal ANGLE POSITION scale (not rate) for gp-0x69ca and its family, at 0.1 deg/count -- confirmed two independent ways (CAN-packing unity-gain chain, and a second function's own literal x0.1 float multiply). Explicitly does NOT compose with the separate 4.7121 counts/deg-s RATE scale. Applies the scale to gp-0x6a10's creep-band table (X[2]=50=exactly 5.0 deg, but that row is flat zero). Rules out FUN_0003e462 (a genuine |angle_diff|<K structure) via the wiring test. Finds one thin, multi-hop but wiring-test-surviving path from gp-0x6a10 to the aggregator via FUN_0003b8f6/FUN_00038148/gp-0x6ad6/FUN_0003a382, while confirming 4 of that function's 5 outputs are dead/write-only.
metadata:
  type: reference
---

# Internal steering-angle POSITION scale settled: 0.1 deg/count (2026-08-05)

Dispatched after D1/D3's data-side finding: grind #1 (18-22Hz) and the ratchet (6-9Hz) move in
OPPOSITE directions across a ~5-degree boundary around the sensor's own zero (measured -4.38±0.21 deg
mechanical). Team-lead's first ask: pin the internal angle-POSITION scale independently, explicitly
NOT by composing the already-settled RATE scale (4.7121 counts/deg-s, gp-0x6abe/gp-0x6ac0/gp-0x6a56) --
that composition error is exactly what produced this kit's retracted "bus = 8x deg/s" claim.

## The scale [EVIDENCE, two independent methods]

**`gp-0x69ca` = 0.1 degree per count** (10 counts/degree -- same scale as the CAN wire).

1. **CAN-packing chain** [fresh decompile `FUN_0003e6d8` + `FUN_000218fe`]: `gp-0x69ca` sums into
   `gp-0x6a00` at exact **Q7 unity gain** -- `cal(tp+0x74f2)` is read as a **BYTE**
   (`*(byte*)(tp+0x74f2)`, NOT a halfword -- a first-pass 16-bit read gave a bogus 205x factor and was
   corrected by re-decompiling), value = **128 = 128/128 = 1.0 exactly**. `gp-0x6a00` is packed into CAN
   0x14A's `STEER_ANGLE`/`STEER_WHEEL_ANGLE` fields (opendbc scale -0.1 deg/count, per
   [[reference-accord-can-angle-producer-and-no-angle-correction]]) via `FUN_000218fe`, decompiled fresh
   this session: **a pure 16-bit byte-swap, zero scaling** (`(x>>8)|(x<<8)`). Units pass through unchanged.
2. **Independent confirmation** [fresh decompile `FUN_0003fd9c`, an unrelated compass/octant-classifier
   function, likely factory self-test shaped]: contains the literal line
   `fVar7 = (float)gp-0x69ca * 0.1 - fVar10` -- the firmware's own code treats `gp-0x69ca` as
   degrees-times-10, confirming (1) independently, different function, different session-thread.

**Explicitly NOT used**: the rate-domain scale (4.7121 counts/deg-s) does not enter this derivation
anywhere. `gp-0x6CC4`/`gp-0x69d0`/`gp+0x6470` (the motor-resolver-domain family, mod-4096/±2048 wrap
idiom) are a **DIFFERENT** scale -- they need `FUN_0003e600`'s own conversion (`x*45/512` then a 5-point
LERP over `tp+0x7892-0x78a2`-ish) to enter the 0.1°/count domain. Do not treat their raw counts as
degrees directly without going through that converter (not fully characterized this session).

## Applying the scale to `gp-0x6a10`'s creep-band table

The creep-band (0-8 km/h) LERP table dumped in an earlier session
([[reference_accord_near_centre_structure_hunt_angle_tracking_chain_found]]), X-breakpoints
`[0,19,50,127,209,452,1019,2016,3607,4150]` (units of `gp-0x6a10`, assumed -- NOT independently
re-verified this session -- to share `gp-0x69ca`'s 0.1°/count scale, since `gp-0x6a10` is built as
`gp-0x69ca - slew(...)`, a difference of like-domain quantities). **X[2] = 50 = exactly 5.0 degrees** --
a striking coincidence with the D1/D3 target. But that row's Y-values are flat zero (already established),
so there is no VALUE change at that breakpoint on this calibration -- the coincidence is not yet a finding.

## `FUN_0003e462` -- a genuine `if(|angle_diff|<K)` structure, RULED OUT by the wiring test

[EVIDENCE, fresh decompile] `gp-0x69c0 = gp-0x69ca - gp-0x6a18` (difference of two angle-domain signals,
`gp-0x6a18`'s own producer `FUN_0004012e` not traced), IIR-filtered (single-pole, cal `tp+0x7490`),
clamped/abs'd, compared against `cal(0xC6352) = 1500` = **150.0 degrees** in the confirmed scale -- a
gross-implausibility fault threshold, structurally irrelevant to a 5° target regardless of wiring.
**Wiring test applied**: `gp-0x676d` (the resulting flag) has exactly 2 refs image-wide, BOTH inside
`FUN_0003e462` itself -- zero external readers. Reports via a DTC-style call (`FUN_00016de6(0x43,...)`)
but never reaches `gp-0x6b98` or any of the 11 aggregator lanes. **RULED OUT**, same pattern as the
`0xC61B8` kill.

## One thin, multi-hop path from `gp-0x6a10` DOES survive the wiring test

Enumerated all 17 readers of `gp-0x6a10` [EVIDENCE, `search_instructions`]. New finding:
`FUN_0003b8f6` -- a genuine PI-controller-shaped function (cascaded EMAs on `gp-0x6b98`/`gp-0x4f60`
feedback, angle-to-radian literal `17.453293` present, gated on `gp-0x6b98` being in-range i.e.
POST-aggregation) reads `gp-0x6a10` as an index into the SAME `tp+0x7b66-0x7b98` LERP F4 (sibling agent)
flagged as one of the two "boost-curve" tables in the `a`-array producer chain. Its five outputs:
```
gp-0x6bf6, gp-0x6c00, gp-0x6ae0, gp-0x6ae2  -- CONFIRMED write-only, zero external readers this session
  (gp-0x6bf6 matches/extends the existing [[accord-below-gp6b98-foc-delivery-path-swept]] finding)
gp-0x6bfc  -- HAS a reader: FUN_0003bc20, which forwards to gp-0x6bfe (one live output) + gp-0x695c (DEAD,
  1 ref, write-only)
gp-0x6bfe  -- read by FUN_00038148 (the already-known 6-term composite -> gp-0x6b70 -> FUN_00037fe6 ->
  gp-0x6ad6 -> FUN_0003a382's resonance lane -> gp-0x6ad4, ONE OF THE 11 CONFIRMED AGGREGATOR SUMMANDS)
```
**So `gp-0x6a10` has a path that survives the wiring test end to end** -- but it is thin: inside
`FUN_0003b8f6`, `gp-0x6a10`'s LERP output is one additive term feeding a gain dominated by `gp-0x6b98`/
`gp-0x4f60` feedback terms; then in `FUN_00038148` it is combined with a THIRD, torque-domain signal
(`gp-0x6bfa`, from the mixer `FUN_00026c80`, F4's own `gp-0x6b4a`-adjacent function) before reaching
`gp-0x6b70`. NOT sized numerically this session (no magnitude comparison against the other summed terms).
Nothing about this single-scalar-gain-modulation shape naturally produces an opposite-signed effect at
two different frequencies -- **does not explain the D1/D3 opposite-direction split as found**. Reporting
as the one survivor, not as a mechanism.

## Bottom line

The clean "~5° symmetric window with opposite-direction split across two lanes" structure was NOT found
this session. The angle-position SCALE is now solid ground for whoever continues this thread. Two
concrete leads closed (one killed, one left as a weak open thread); the core question remains open.

## Related
[[reference-accord-can-angle-producer-and-no-angle-correction]] -- source of the CAN-side ground truth
this session's scale derivation anchors to.
[[accord-below-gp6b98-foc-delivery-path-swept]] -- source of the `gp-0x6bf6` dead-end finding this
session extends to 3 sibling outputs of the same function.
[[reference_accord_near_centre_structure_hunt_angle_tracking_chain_found]] -- the earlier session this
one applies the new scale to (the creep-band table X-breakpoints).
