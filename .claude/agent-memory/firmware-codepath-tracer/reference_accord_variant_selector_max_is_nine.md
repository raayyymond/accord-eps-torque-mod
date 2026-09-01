---
name: reference-accord-variant-selector-max-is-nine
description: The gp-0x674E variant selector is <=9 in every coded variant, so slots 10-27 of the taper, assist-map and Kp/Kd banks are UNREACHABLE dead calibration
metadata:
  type: reference
---

🛑🛑★★★★★ **`gp-0x674E` — the one selector that indexes all the per-variant banks — is <= 9 in
EVERY coded variant. Bank slots 10-27 are DEAD CALIBRATION. A dose applied only to slots 10-27
is INERT.**

EVIDENCE (V277 image, 2026-09-01; Ghidra decompile + raw Python, agreeing):
- `FUN_00057f8e` matches a 5-byte part number and its loop is `uVar2 = 0; do {...} while (uVar2 <
  0x10);` — **only records 0..15** of the 0x24-stride table at `0xCD000` are ever searched. Index
  >15 is unreachable by construction, so the kit's older "reachable range is 0-33" figure is wrong
  for this consumer.
- `FUN_00042692` @`0x42692` writes `*(gp-0x674e) = byte at 0xCD01A + i*0x24` (tp=0xBF000; anchor
  0xBF000+0xE000 = 0xCD000). SINGLE writer: `st.b` @`0x4272A`.
- Byte +8 for i=0..15 reads {0,0,1,1,0,0,1,1,3,4,6,7,6,8,8,9}. **Max 9.** The 16 part numbers, in
  order, are `000005360Y` `TVAA05360Y` `TVAA15360Y` `TVAC15360Y` `TVAA25360Y` `TVAA45360Y`
  `TVAA65360Y` `TVAC45360Y` `TVAA75360Y` `TVCA05360Y` `TVCA35360Y` `TVCA45360Y` `TVCA65360Y`
  `TWAA05360Y` `TWAA15360Y` `TWAA25360Y`. Records 16+ are unbroken 0xFF from 0xCD240 to 0xCDFF0 and
  are never searched. **"0..27" is the BANK WIDTH, not the selector range** — the stride-vs-walk trap.
- Byte +7 (-> `gp-0x674D`) is **0 in all 16 records**, which is the only reason a 16-bit `ld.h` of the
  byte cell `gp-0x674E` returns the selector uncontaminated. Safety by luck; assert it.
- Nulls re-run through the 6-byte EXTENDED-DISPLACEMENT form (4,934 sites image-wide, positive-control
  passed): zero extra touches on gp-0x674A..0x674E. See [[reference-accord-v850-load-opcode-map-ldhu-0x3e]].
- ⚠ `FUN_00057f8e` returns **0 on NO MATCH**, so an uncoded/unknown part number silently defaults to
  record 0. Any telemetry of this selector cannot distinguish "coded to a sel-0 variant" from
  "defaulted". Nor is it injective: sel 1 <- records 2,3,6,7; sel 6 <- 10,12; sel 8 <- 13,14.
- The selector is a DIRECT, UNSCALED word index: `ld.bu -0x674e,gp,r12 / mov <bank>,r9 / shl 0x2,r12
  / add r9,ep` at `0x28FC8` (bank 0xCB844), `0x29AA0` (0xCBA74), `0x29B7C` (0xCBA04), `0x29CC4`
  (assist map 0xC9A88), and `0x2A9A6`/`0x2ABBA` in the dead twin FUN_0002a93a.
- Full disp16 census of gp-0x674E: 6 readers (those bank indexers), 1 writer, nothing else.

CONSEQUENCES
- The override-taper shape `X=(32,48,64,112) Y=(255,205,154,0)` lives ONLY on slots 10-27 — it is
  never used. The live shapes are `(70,72,78,80)/(254,234,12,0)` on banks 0xCBA04/0xCBA74 slots 0-9,
  and `(32,38,80,112)` / `(32,42,80,112)` / `(32,38,64,102)` / `(32,38,54,96)` with Y mostly
  `(255,255,255,0)` on banks 0xCB8B4/0xCB924 slots 0-9.
- This RESOLVES the long-open "record 2 (slots 10/11) vs record 11 (24/25/26/27)" question in
  [[accord-variant-selector-chain-0xcd000]]: **neither** — the live slot is always in 0..9.
- Any plot or LERP drawn from a slot >=10 record is the wrong curve. Check the lineage for doses
  that landed only there.

Related: [[accord-one-selector-indexes-all-five-banks]] · [[accord-pointer-family-size-is-the-stride]]
