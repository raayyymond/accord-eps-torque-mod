---
name: reference-accord-damper-variant-row-vs-index-trap
description: The damper factor tables (FUN_00034350) are selected by a THREE-stage indirection, not two — conflating the EEPROM-coded variant ROW with the pointer-array INDEX gives a plausible-looking but wrong table. For this car's PN (39990-TVA-A160), the correct chain lands on the SAME tables V44/V47 edited.
metadata:
  type: reference
---

## The trap

`FUN_00034350` (base-assist damper, factors B/C/D/E) selects each factor's LERP table via a
pointer array indexed by a byte at `gp+0x63fd` (confirmed: `ld.bu 0x63fd,gp,rX` / `shl 0x2` /
`add ptr_array` / `ld.w` — e.g. `0x34470`-`0x3447e` for Factor B). It is tempting to assume that
byte equals the "variant row" that identifies this car's calibration. **It does not — there is an
extra table lookup in between.**

The real chain, confirmed by disassembly + byte reads of `stock_fw_dump/code.bin` (identical in
`_v54_plain_image.bin`):

```
5-byte EEPROM-coded ID (gp+0x6408..0x640c, UDS "write variant coding" service FUN_000508e8,
                          NOT present in the flash image — programmed at end-of-line/service)
   |
   v  FUN_00057f8e(): linear match vs 16 five-byte ASCII keys @ 0xCD000, stride 0x24
   v
  ROW (0-15)     <-- this is FUN_00057f8e()'s return value
   |
   v  gp+0x63fd = *(byte*)(tp + 0xE012 + ROW*0x24)   i.e. *(byte*)(0xCD012 + ROW*0x24)
   v  (written in FUN_00042692 / FUN_00042746: "(&DAT_000063fd)[gp] = (&DAT_0000e012)[ROW*0x24+tp]")
   |
  INDEX (0-57ish)   <-- THIS is what actually indexes the pointer arrays
   |
   v  ptr_array[INDEX] (arrays at 0xC9CCC/0xC9E9C/0xC9DB4/0xC9F84 for factors B/C/D/E)
   v
  table address
```

**ROW ≠ INDEX for 13 of the 16 rows.** Byte-read the full ROW→INDEX table at `0xCD012 + ROW*0x24`
(stock == V54, byte-identical):

| row | key | index | Factor-C table (X0) | Factor-E table (X0) |
|---|---|---:|---|---|
| 0 | `00000` | 0 | `0xCE528` (1280) | `0xCE550` (70) |
| 1 | `TVAA0` | 4 | `0xD07BC` (1920) | `0xD07F8` (60) |
| **2** | **`TVAA1`** | **10** | **`0xD27BC` (2240)** | **`0xD27F8` (60)** |
| 3 | `TVAC1` | 10 | `0xD27BC` (2240) | `0xD27F8` (60) |
| 4 | `TVAA2` | 4 | `0xD07BC` (1920) | `0xD07F8` (60) |
| 5 | `TVAA4` | 4 | `0xD07BC` (1920) | `0xD07F8` (60) |
| 6 | `TVAA6` | 10 | `0xD27BC` (2240) | `0xD27F8` (60) |
| 7 | `TVAC4` | 10 | `0xD27BC` (2240) | `0xD27F8` (60) |
| 8 | `TVAA7` | 12 | `0xD27E4` (2240) | `0xD2820` (60) |
| 9-15 | `TVCA0..TWAA2` | 16-30 | `0xD47BC..0xD87E4` | — |

## Why this matters for this car

Part number **39990-TVA-A160** → chassis `TVA`, revision `A`, spec-family digit `1` (from `160`)
→ natural key **`TVAA1` = row 2 → index 10 → `0xD27BC`/`0xD27F8`**. **This is exactly the pair of
tables V44 (`0xD27C6`/`0xD27DA`) and V47 (`0xD2802/04/06`+`0xD2816/18/1A`) edited.** So — contrary
to a first-pass reading that stopped at "row 2 through row 3 all resolve to the same *pointer-array
entries 0-3*" (an error: those were INDEX 0-3, not ROW 0-3, and the tables at index 0-3 are NOT
what row 2 actually selects) — **V44/V47 most likely DID test the live table on this car**, and
their on-car nulls are evidence against the missing-damping hypothesis, not an artifact of editing
an inert variant slot.

**Residual uncertainty, genuinely open:** the actual coded ROW is an EEPROM value (UDS variant
coding, `FUN_000508e8`), not present in the flash dump — it cannot be byte-confirmed from
`code.bin`/`_v54_plain_image.bin`. If this ECU is actually coded `TVAA0`/`TVAA2`/`TVAA4` (row
1/4/5) rather than `TVAA1` (row 2), the live table is index 4 (`0xD07BC`, X0=1920) instead —
untested by V44/V47. The part-number-derived key (`TVAA1`) is the best available inference, not a
confirmed fact. **Definitive closure needs one telemetry bit**: `gp+0x63fd` (the INDEX byte, 0-57,
fits comfortably in the existing piggyback width) or, more directly, the 5-byte ID at `gp+0x6408`.

Related: [[reference-accord-damper-two-deadzones-factorC-factorE]], [[v44-built-handsoff-damping]],
[[project_v46_falsified_v47_dampers_only]]
