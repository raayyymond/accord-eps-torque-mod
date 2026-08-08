---
name: reference_accord_mode24_mode26_stock_boost_friction_gainb_identical
description: Full byte census of every mode-indexed assist family at mode 24 (manual) vs mode 26 (engaged) on stock Honda firmware — all identical except the damper.
metadata:
  type: reference
---

[EVIDENCE, byte-level Python census, both `stock_fw_dump/code.bin` and a V81 plain image, cross-checked
against fresh `decompile_function` of `FUN_00034a72` and `FUN_0003ad74` to pin every pointer-array
address before dereferencing.] Method: decompile first to get the exact `arr + mode*4` addressing (single
vs double pointer indirection differs per table — see gotcha below), then read `arr+mode*4` as a u32
pointer and decode the record (`u16 n@0, i16 X[]@2, i16 Y[]@2+2n, u16 term@2+4n`) or scalar at the target.

**On STOCK Honda firmware, mode 24 (manual) and mode 26 (engaged) are byte-identical in EVERY family
checked**, for TVCA4 (this car, see [[reference-accord-car-is-tvca4-mode-24-26]]):

| family | function | pointer array(s) | mode24 vs mode26 |
|---|---|---|---|
| Damper FactorB | FUN_00034350 | 0xC9CCC | identical |
| Damper FactorC | FUN_00034350 | 0xC9E9C | identical (Y=[0,234,429,908]) |
| Damper FactorD | FUN_00034350 | 0xC9DB4 | identical (flat 1024, inert) |
| Damper FactorE | FUN_00034350 | 0xC9F84 | identical (X=[60,400,2500,4000] Y=[0,140,539,927]) |
| Damper ceiling | FUN_00034350 | 0xC77A0 | identical (flat 512 floor) |
| Friction | FUN_00036c12 | 0xCBE74 | identical (Y=[-9830,-5734,-1966]) |
| r24 gain_B (4 speed records) | FUN_0003ad74 | 0xCBF5C/0xCC044/0xCC12C/0xCC214 | identical, all 4 |
| Boost curve | FUN_00034a72 | 0xCA154 | identical (Y=[552,650,659,554,448,447] on TVCA4 row — differs from the mode-10 TVAA1 numbers quoted elsewhere in the golden model, as expected, different HW-ID row) |
| Boost amp1 (y1) | FUN_00034a72 | 0xCA4F4 | identical |
| Boost amp4 (y4) | FUN_00034a72 | 0xCA23C | identical |
| Boost ceiling | FUN_00034a72 | 0xC7970 | identical (flat 512) |
| Boost gain scalar A | FUN_00034a72 | 0xCA324 (single ptr → i16) | identical (43) |
| Boost byte scalar | FUN_00034a72 | 0xCA40C (single ptr → u8) | identical (128) |
| Boost blend rate Q10 | FUN_00034a72 | 0xCA06C (single ptr → i16), shared by BOTH y1 and y4 (aliases `tp+0xB06C`) | identical (102) |
| Boost output clamp | FUN_00034a72 | 0xC7A58 (single ptr → u16 — NOT double indirection, see gotcha) | identical (666) |

⇒ **Honda's own design does not differentiate manual from engaged at the table level anywhere in this
image.** Any engaged-vs-manual asymmetry on a built car comes entirely from OUR OWN mode-26-only edits
(see [[reference_accord_v81_engagement_impedance_factorce_dominant_mechanism]]).

## Gotcha: `0xC7A58` LOOKS like double indirection in the decompile, it is NOT
`FUN_00034a72`'s decompile shows `**(ushort **)((int)&PTR_DAT_000c7a58 + iVar18)` for the boost output
clamp — Ghidra's inferred type reads as double-pointer. **Reading it that way crashes / reads garbage**
(second dereference lands past the 1 MB image). The REAL semantics: `arr+mode*4` holds a u32 pointer P1,
and the clamp value is `u16 @ P1` directly — SINGLE indirection. Cross-checked against the existing
golden-model claim "`0xC7A58[10] -> 0xD2000 reads 666`" (mode 10): reproduces exactly. Trust the model's
stated value over Ghidra's inferred C type when they disagree on indirection depth.

## Corollary: three T3-style engagement-gate suspects RULED OUT by full decompile
- `gp-0x67f4` (sole writer `FUN_00041eec` @0x4218A/0x421A0): pure 5-channel vehicle-speed-voter
  plausibility flag (agree-within-65-ct debounce). Zero reference to `gp-0x6806`/`gp-0x69b0`/`gp-0x67fa`
  anywhere in the function body.
- `gp-0x67fe` (sole writer `FUN_0003bd7c`): EPS assist substate driven by `gp-0x6772`, an EPS
  self-test/readiness state (valid substates only reachable from raw states 4/5, gated on a DTC-bit-8
  check). No engagement reference.
- `FUN_00036682` (the one live reader of `0xC646C` that reaches the motor, per
  [[reference-accord-c646c-shared-gain-not-lkas-only]]): pure torque-domain hysteresis + slow IIR
  (alpha `tp+0x73d2`=6), zero reference to mode/state/engagement in its body.

`0xC63A0` (Path-2 weight) is real and doubled in recent builds, but it's a bare `tp` scalar with **no**
mode index — applies equally in manual and engaged (RULE 7 mode-proof) — so it cannot be the source of
an engagement-*specific* asymmetry, only a general loop-gain lever.
