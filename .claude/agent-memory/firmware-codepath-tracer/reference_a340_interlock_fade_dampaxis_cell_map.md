---
name: reference-a340-interlock-fade-dampaxis-cell-map
description: 39990-TVA-A340 stock (2026-11-01): gp/tp same as A160; EME ladder +0x50; STEER_STATUS SM cals 0xC61D0/D2/D4 = 12800/8960/11520 (x8-10 A160, #1 can never trip); low-speed lockout 0xC62FC already 0; dir-0 post-PID fades are RAM tables built by FUN_0002a740; angle K 1157 vs 1159
metadata:
  type: reference
---

A340 stock image `other bins/39990-TVA-A340.bin`, Ghidra program `/A340_stock.bin`. Method: Python tp-ref
stream sequence-aligned A160→A340, every hit confirmed by A340 decompile.

- gp = 0xFEDF8000, tp = 0xBF000 (app entry 0x14084, ori 0x8000 + movhi/movea).
- Lane FUN_00029230 (jarl @0x22618); uncalled twin FUN_0002ae74/FUN_0002b4a0 + unanalysed 0x2BC2C..
- Most app code 0x36000–0x42000 = A160 + 0xB82; RAM words often A160 gp offset + 0x30..0x38.
- EME int ladder 0xC6798..0xC67BC (A160 +0x50), floats 0xC65E0..0xC661C; shaper FUN_0004367a, float model FUN_000449c6 (fault 0x3F1B).
- STEER_STATUS SM: 0xC61D0/D2/D4 = 12800/8960/11520 (A160 1600/896/1280); bytes 0xC6504..07 = 112/96/54/64; DTC-0x49 gate 0xC6508 = 112. r28 clamped to 12800 and test is `bh`, so threshold #1 never trips on A340 stock.
- Low-speed lockout 0xC62FC = 0 (A160 0xC62EA = 320). EME ramp/knot count 0xC652E = 17. Engage ramp 0xC640C/0E/10/12 = 16/33/66/328.
- Post-PID fade: dir-2 = byte tables 0xC6C10 (A) / 0xC6C00 (B); dir-0 = RAM gp-0x62d8/-0x62cc (A) and gp-0x62f0/-0x62e4 (B), built by FUN_0002a740 from speed-interpolated variant records (ptr tables 0xC7814/44, 0xC7904/34, 0xC79F4/A24) — all records identical, A Y 255,255,212,185,154,51; B X 16..112 Y 255×5,154.
- DampAxis: FUN_00041fe6 → gp-0x6bfc; alpha2 0xC40D4 = 22; ptr table 0xCBE40 → same records 0xD7A54/0xD7A64 (Y −9830,−5734,−1966); clamp 0xC407E = 511.
- Angle: gp-0x69c8 via FUN_0003f25a/FUN_0003f182; 0xC6450 = 900, 0xC6142 = 1157 (A160 1159), 0xC6542 = 128, 0xC636A = 2; C-LERP X 0xC68E2 (top 12160), Y 0xC68F2.
- PN strings same layout at 0x13100/0x9011/0x14109; SA key bytes 0x92C0 identical.

Related: [[reference_accord_variant_record_table_0xcd012_full_dump]] (A160 only).
