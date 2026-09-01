---
name: reference_accord_variant_record_table_0xcd012_full_dump
description: Full 16-row dump of the part-number variant record table at 0xCD012 (stride 0x24) with every field the firmware reads from it, plus the finding that V273's docstring pairs record NAMES and record VALUES from DIFFERENT rows (1-based vs 0-based) -- so its "record 2 => wire 5" may actually be wire 0, indistinguishable from a dead channel. Includes the one-byte fix (0x55E0E mov 0x0,r7 -> mov 0x1,r7) that removes the ambiguity.
metadata:
  type: reference
---

# The variant record table, dumped whole. 2026-09-01 (Python raw read of stock `code.bin`).

Base = `tp + 0xE012` = **0xCD012**, stride **0x24** (36 B), index from `FUN_00057f8e()`.
Field offsets read straight off `disassemble_function(0x42692)`:
`+0 -> gp+0x63fd` · `+4 -> gp-0x674c` · `+5 -> gp-0x674f` · `+7 -> gp-0x674d` · `+8 -> gp-0x674e`.
Layout per record is 18 numeric bytes then a 17-char ASCII name + `0x01`.

```
 row  name                 +0..+3 (gp+0x63fd base)  674c  674f  674d  674e
  0   TVAA05360YTVAA000     0, 1, 2, 3               0     0     0     0
  1   TVAA15360YTVAA100     4, 4, 5, 5               1     2     0     0
  2   TVAC15360YTVAC100    10,10,11,11               2     5     0     1
  3   TVAA25360YTVAA200    10,10,11,11               2     5     0     1
  4   TVAA45360YTVAA400     4, 4, 5, 5               1     2     0     0
  5   TVAA65360YTVAA600     4, 4, 5, 5               1     2     0     0
  6   TVAC45360YTVAC400    10,10,11,11               2     5     0     1
  7   TVAA75360YTVAA700    10,10,11,11               2     5     0     1
  8   TVCA05360YTVCA000    12,13,14,15               2     6     0     3
  9   TVCA35360YTVCA300    16,16,17,17               3     8     0     4
 10   TVCA45360YTVCA400    22,22,23,23               4    11     0     6
 11   TVCA65360YTVCA600    24,25,26,27               4    12     0     7
 12   TWAA05360YTWAA000    22,22,23,23               4    11     0     6
 13   TWAA15360YTWAA100    28,28,29,29               5    14     0     8
 14   TWAA25360YTWAA200    28,28,29,29               5    15     0     8
 15   (name = 0xFF filler) 30,31,32,33               5    15     0     9
 16+  all 0xFF
```

⭐ **Only NINE distinct numeric classes exist.** Rows {2,3,6,7} are byte-identical in every numeric
field; so are {1,4,5}, {10,12}, {13,14}. They differ only in the ASCII name. ⇒ arguing about which of
those rows is live is arguing about nothing, functionally.

✅ **`gp-0x674d` is 0 in every valid row** — so `ld.h -0x674e[gp]` returns the byte cleanly with no
masking (even offset, aligned). This is V273's key premise and it holds. `gp-0x674e` is otherwise a
BYTE cell: 4 `ld.bu` in `FUN_00028ea6`, 2 in the dead twin `FUN_0002a93a`, 1 `st.b` at `0x4272A`.
`gp-0x674f` and `gp+0x63fd` sit at **odd** gp offsets — an `ld.h` there is misaligned and the low
address bit is masked, so they cannot be tapped the same way. **`gp-0x674e` is the only even-offset,
clean-neighbour, and simultaneously most-discriminating choice** (it separates 8 of the 9 classes).

## 🛑 V273's docstring pairs names and values from DIFFERENT rows

It states *record 2 = "TVAA15360YTVAA100", gp+0x63fd ∈ {10,11}, gp-0x674e = 1* and
*record 11 = "TVCA45360YTVCA400", {24..27}, 674e = 7*. In the table above the **names** are rows 1 and
10 (**1-based** numbering) while the **values** are rows 2 and 11 (**0-based**). One is wrong, and it
decides the expected wire code:
* 0-based (values right): wire **5** vs **35** — as documented.
* 1-based (names right): wire **0** vs **30** — and **0 is indistinguishable from a dead channel.**

Four of sixteen rows have `674e = 0`. The part number is 39990-**TVA**-A160 and the row named "TVAA1…"
is row 1 with `674e = 0`, so the zero outcome is live, not hypothetical. Not resolvable from firmware
— needs whoever set the kit's record numbering, or a UDS read of the coded index.

⭐ **ONE-BYTE FIX, take it regardless.** `0x55E0E` is `mov 0x0,r7` (bytes `00 3a`), the LOW argument of
`FUN_00049a90(v,lo,hi)` in the 427 packer. Set the byte to **0x01** (`mov 0x1,r7`, Format II imm5).
The clamp floor becomes 1, so a `674e=0` row reads **1** and only a dead channel reads **0**.

## The 427 readout arithmetic, verified instruction by instruction
```
0x55DF0 ld.h -0x6c18[gp],r6   ; V273 rewrites the disp16 at 0x55DF2 -> 0x98B2 (= -0x674E)
0x55DF4 jarl FUN_00049a5a     ; abs()          (decompiled)
0x55DFE jarl FUN_00049a78     ; min(x,0xFFFF)  (decompiled, unsigned)
0x55E02 andi 0xffff,r10,r6    ; ZERO-extend
0x55E06 mul  0x5,r6,r0
0x55E0E mov  0x0,r7           ; clamp lo
0x55E10 sar  0x3,r6           ; V273 rewrites this byte 0xA3 -> 0xA0
0x55E12 jarl FUN_00049a90     ; clamp(v,0,1023)
0x55E1A jarl FUN_00021864     ; byte1 = v&0xFF ; byte0[1:0] = (v>>8)&3
```
Byte-diff of the built V273 image vs V268 over 0x55D80-0x55F30: **exactly 3 bytes changed —
0x55DF2, 0x55DF3, 0x55E10.** `sar 0x0` is architecturally legal (result unchanged, CY cleared);
that is ISA reasoning, not an observed instance in this image.

## Related
[[reference_accord_fun28ea6_lkas_rate_pid_full_decode]] — where `gp-0x674e` indexes the 28-entry banks.
[[reference_accord_fun28ea6_publishes_its_pid_internals_to_gp_cells]] — the other cells worth this tap.
