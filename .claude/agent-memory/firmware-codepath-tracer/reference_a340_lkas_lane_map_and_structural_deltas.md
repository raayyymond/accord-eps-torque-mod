---
name: a340-lkas-lane-map-and-structural-deltas
description: 39990-TVA-A340 LKAS rate PID = FUN_00029230 (caller 0x22618); NOT a re-addressed A160 lane — speed-scheduled RAM gain/map tables (FUN_0002a740, 36 records/table), P>>3 not >>8, 8-bit gains, ICL 0, r6 live across hook, 0xC6CD0 occupied
metadata:
  type: reference
---

A340 (sha 01a53539…, build C30_802_D_12_00) vs A160 lane `FUN_00028ea6`, traced 2026-11-01 (T1a).
gp/tp identical (0xFEDF8000 / 0xBF000; startup 0x140C0..DF byte-identical). .data = flash [0x87320,0x8BC6C) → RAM 0xFEDF11C0.

- Lane `FUN_00029230` 0x29230–0x2A73F, sole caller jarl 0x22618 (slot-0 FUN_00022240, task ptr 0xBB950).
  Twin island 0x2AE74 + FUN_0002b4a0 uncalled. Limit&pack = FUN_0002bfa4 (0xC61C0).
- Site map: E1 0x292EE · B2 0x29E68 (eligibility reg = **r25**, not r27) · A2 0x29E6E · E4 0x2A334 · HOOK 0x2A340 ·
  HOOK_RET 0x2A344 · FRZ_RET 0x2A348 · SKIP 0x2A596 · OPH = 0x2A3D4 `subr r9,r10` · fwd gain ld.h 0x748a[tp] @0x2A620.
- gp map: 6a56→6a26, 6a5e→6a2e, 69ae→6976, 69b0→6978, 6803→67c9, 6805→67cb, 6a00→69c8, 4f68→4ec0, 6abe→6a8e,
  6dd0→6da0, 6b38→6b08, 674e→6714, 674b→6711. Offsets are NOT uniform — re-derive every cell.
- **Kp/Kd/Ki/map/dir-0 fades are RAM tables** filled at 100 Hz by FUN_0002a740 from 3 speed records × 12 variants
  (ptr tables 0xC77E4/0xC7784/0xC77B4/0xC72A4/0xC7844/0xC7814 + 0xF0/0x1E0 for mid/high). Stock: all identical.
- P = (E·Kp)>>3 (A160 >>8); I inc has extra shl 2; gains 8-bit truncated. ICL 0xC61C8 = 0 stock. Low-speed lockout 0xC62FC = 0 stock.
- r6 (engage state gp-0x6764) and r8 (DB) are live at the hook → the A160 cave cannot be relocated unchanged.
- 0xC6CD0 is occupied on A340 (read 0x6E5C0). Free 0xFF run [0xC4B2C,0xC4FF0).
- ⚠ Address reuse trap: A340 0xC64B8 is the Kd speed-knot array, not A160's DTC-0x49 gate (that is 0xC6508 on A340).

Full table: the T1a report in that session's scratchpad (not in repo). Related: [[accord-fun28ea6-lkas-rate-pid-full-decode]].
