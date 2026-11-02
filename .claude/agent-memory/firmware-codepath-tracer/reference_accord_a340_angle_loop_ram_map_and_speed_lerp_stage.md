---
name: reference-accord-a340-angle-loop-ram-map-and-speed-lerp-stage
description: 39990-TVA-A340 (different compile from A160) — gp/tp unchanged but the RAM map is re-laid; A160→A340 map of every V300 angle-loop word, producers, slots, cave home 0xC4B2C free; A340 has a NEW 100 Hz speed-LERP stage FUN_0002a740 feeding the lane
metadata:
  type: reference
---

Traced 2026-11-01 on Ghidra `/A340_stock.bin` + Python census (positive-controlled, 6-byte form included).

- gp = 0xFEDF8000, tp = 0xBF000 (app entry 0x140c0–0x140d6). **No gp offset carries over; shifts are non-uniform.**
  🛑 A340 `gp-0x69b0` is a 0x14A packer field, not the ramp.
- A160 → A340: angle 6a00→**69c8** (writer FUN_0003f25a 0x3f2da, slot 4 call 0x22f28); rate fb 6a56→**6a26**
  (FUN_000402f8, 0x22ed8); setpoint 69ae→**6976** (E4 handler FUN_000533e4, RX table ptr 0xBB668); field 6803→**67c9**;
  request bit 6805→**67cb**; 6802→67c8; speed 6a5e→**6a2e** (FUN_00042a6e, slot 4); hand τ 4f60→**4eb8**, |τ| 4f68→**4ec0**
  (FUN_000804b4 via slot0 0x222d6); EMA 6abe→**6a8e** (FUN_00041fe6, slot0 0x222f6); I state 6dd0→**6da0**; ramp 69b0→**6978**;
  sentinel 6cf8→6cc8; lane out 6b38→6b08; mode 67fe→67c4; state byte 67fa→67c0; tick flag 42fc→425c.
- Lane FUN_00029230 ← 0x22618 (slot 0 entry 0x22240); uncalled twin FUN_0002ae74. Slot 4 entry 0x22D96; dispatcher FUN_00014c44.
- E4 arithmetic identical to A160 (whole-function halfword compare, only address fields differ).
- Angle cal deltas: motor-count scale 0xC6142 = 1157 (A160 1159); VGR LERP Y/X last knot differ (0xC68E2/0xC68F2).
- ⭐ **NEW on A340:** FUN_0002a740 (slot 4, 0x2332e, mask 0x930) LERPs speed into RAM records (gp-0x6e20…, -0x6110…, -0x62d8…,
  -0x635c…) that the A340 lane reads — speed-scheduled records A160 does not have.
- Cave home: 0xFF run 0xC4B2C–0xC4FF0 (main CRC block [0x13000,0xC4FFC)); unreferenced by tp/dword/imm32/movhi/jarl scans + Ghidra.

Related: [[reference-accord-gp6a00-angle-is-a-100hz-hold-inputs-fresh-at-1khz]], [[reference-accord-op-0e4-steer-command-full-path]].
