---
name: accord-damper-variant-row-vs-index-trap
description: "The damper factor tables are variant-coded through THREE stages (EEPROM ID -> config ROW 0-15 -> pointer-array INDEX 0-57 -> table); conflating ROW with INDEX inverts the answer. Our car (TVA-A160 = TVAA1 = row 2 = index 10) DOES select the 0xD27xx tables V44/V47 edited, so the damping hypothesis was genuinely tested and IS falsified."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 421be5bf-160c-42b6-820e-911dcec5caa9
  modified: 2026-07-28T05:42:08.123Z
---

## The three-stage chain — collapsing it inverts the conclusion

```
5-byte coded ID (EEPROM/NVRAM — NOT in the flash dump)
  -> FUN_00057f8e()  linear match vs 16 keys @0xCD000, stride 0x24   -> ROW   (0-15)
  -> index byte      @0xCD012 + ROW*0x24                             -> INDEX (0-57)
  -> ptr_array[INDEX]                                                -> the live LERP table
```

🛑 **ROW ≠ INDEX.** A subagent read pointer-array entries 0-3 (all X0=1280), called them "rows 0-3",
and concluded our TVA-chassis car uses those — inverting the answer. The mapping is not identity:

```
row  key     idx   FactorC      X0     FactorE      X0
  0  00000     0   0xCE528    1280     0xCE550      70
  1  TVAA0     4   0xD07BC    1920     0xD07F8      60
  2  TVAA1    10   0xD27BC    2240     0xD27F8      60   <== V44 AND V47 EDITED THESE
  3  TVAC1    10   0xD27BC    2240     0xD27F8      60
  4  TVAA2     4   0xD07BC    1920     0xD07F8      60
  5  TVAA4     4   0xD07BC    1920     0xD07F8      60
  6  TVAA6    10   0xD27BC    2240     0xD27F8      60
  7  TVAC4    10   0xD27BC    2240     0xD27F8      60
  8  TVAA7    12   0xD27E4    2240     0xD2820      60
  9  TVCA0    16   0xD47BC    1920      ...
 10  TVCA3    22   0xD67BC    2240      ...
 11  TVCA4    24   0xD67E4    2240      ...
```

The 16 keys are ASCII Honda PN chassis/revision suffixes, readable directly from `0xCD000 + n*0x24`.
**`0xD27xx` is NOT another chassis's data** — the TVC rows resolve to indices 16/22/24 in the
`0xD4xxx`/`0xD6xxx` blocks.

## ⇒ The damper hypothesis was genuinely tested, and it is FALSIFIED

Our PN **39990-TVA-A160** → key `TVAA1` → row 2 → **index 10** → Factor C `0xD27BC` (X0=**2240**) and
Factor E `0xD27F8`. **Exactly the tables V44 and V47 edited.** Independent corroboration:
[[v44-built-handsoff-damping]] cites the deadzone edge as **2240 counts**, a number that exists only in
index 10's table — that session had resolved this correctly. Do not "resurrect" the damping hypothesis on
the theory that V44/V47 hit the wrong variant.

⚠ **Residual, exactly one bit wide.** The coded ID is in EEPROM and is **not** in `code.bin` or any
`_v*_plain_image.bin`, so the row cannot be byte-confirmed from the artifacts we have. The TVA family
**splits**: `{TVAA0, TVAA2, TVAA4}` → index **4** (X0=1920); `{TVAA1, TVAC1, TVAA6, TVAC4}` → index
**10** (X0=2240); `{TVAA7}` → 12. If this ECU is coded TVAA0/2/4, V44/V47 missed after all. The PN points
hard at TVAA1, but that is inference, not a read. **V55 carries one telemetry bit for it**
(`variant_index >= 10`).

## Scope — this is not just the damper

The **same** selector byte (`gp+0x63fd`, positive gp offset) indexes **all five damper factors AND the
output clamp**: Factor B `0xC9CCC`, D `0xC9DB4`, C `0xC9E9C`, E `0xC9F84`, clamp ptr `0xC77A0`. Arrays are
0xE8 (232 B) apart, 58 entries each, grouped in threes across `0xD0000`-`0xD8000` blocks.
**Assume any `0xD_xxx`-region LERP is variant-coded until proven otherwise, and resolve the pointer before
editing it.** Writers of the selector: `FUN_00042692` @`0x426ae` and `FUN_00042746`
@`0x4279e/0x427c4/0x427fc/0x42822`.

Related: [[accord-vibration-moves-with-speed-and-dies-at-rail]], [[accord-check-build-lineage-before-proposing-lever]].
