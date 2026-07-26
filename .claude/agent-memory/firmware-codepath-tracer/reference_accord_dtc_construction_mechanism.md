---
name: reference-accord-dtc-construction-mechanism
description: Complete UDS 0x19 DTC code construction path for Accord TVA V850E2; 24-group DTC table at tp-0x64e0; gp-0x1056 cache; formula for 3-byte DTC assembly; all V22 DTC codes verified
metadata:
  type: reference
---

## UDS 0x19 DTC Construction Mechanism (Accord TVA-A160 V22, V850E2)

**Call chain for UDS ReadDTCByStatusMask (0x19 0x02):**
- FUN_0004d562 / FUN_0004d592 (service entry handlers)
- → FUN_0004d504 (main builder, checks gp-0x105c==1 for cache-ready)
- → FUN_0004d4a2 (iterative callback, called up to 0x18=24 times)
- → FUN_00057d96 (reads from gp-0x1056 cache, filters by status mask)
- → FUN_0002114e (writes 4 bytes to UDS response buffer)

**DTC group cache population:**
- FUN_0004c606 triggers FUN_0004c5a6 in a 24-cycle sweep
- FUN_0004c5a6 reads from **0x68-stride DTC group table at `tp-0x64e0 = 0xB8B20`**
- Group index from `gp-0xff0`, cycles 1→24→1; sets `gp-0x105c = 1` on completion
- 24 DTC groups in V22 firmware (also identical in stock V9 and V21)

**DTC code formula** from 4-byte LE table entry `[b0, b1, b2, b3]`:
- DTC_B0 (byte sent first) = `b[2]`
- DTC_B1 = `b[1]`
- DTC_B2 = `b[0]`
- STATUS byte = from gp+0x634b+fault_id status array

**V22/V9 (stock) 24 DTC group codes — CORRECTED 2026-06-01 with full fault_id membership from binary read:**

NOTE: gp-0xff0 cycles 1→24→1 (1-indexed). The task/operator references groups with 0-indexed numbering (task-group-N = firmware-group-N+1). So task-group-17 = firmware row 18 = DTC 0xC41668, task-group-20 = firmware row 21 = DTC 0xF00049.

| Group (1-idx) | Task-idx (0-idx) | DTC Code  | fault_ids in group |
|-------|------|-----------|-------|
| 1  | 0  | 0x000000  | 9,10,30,31,32,33,34,35,50,53,57,59,63,64,65,66,67,69,70,71,76,82,85,87,88,93,94,96..115,126,48 |
| 2  | 1  | 0x406396  | 80 |
| 3  | 2  | 0x540011  | 17 |
| 4  | 3  | 0x540013  | 122 |
| 5  | 4  | 0x540014  | 61,121 |
| 6  | 5  | 0x540096  | 26,54 |
| 7  | 6  | 0x540329  | 48,123,124,125 |
| 8  | 7  | 0x540362  | 49 |
| 9  | 8  | 0x542029  | 2,117,118 |
| 10 | 9  | 0x542114  | 1 |
| 11 | 10 | 0x542214  | 120 |
| 12 | 11 | 0x542229  | 119 |
| 13 | 12 | 0xC02900  | 95 |
| 14 | 13 | 0xC10000  | 74,75,77,78 |
| 15 | 14 | 0xC12200  | 79,90,91,92 |
| 16 | 15 | 0xC15100  | 84,89 |
| 17 | 16 | 0xC15500  | 86  (non-EPS-disabling; torque sensor lockstep monitor FUN_000534DA) |
| 18 | 17 | 0xC41668  | **81** (non-EPS-disabling; dispatch fn FUN_00053CCC; trigger = voltage/ADC timeout gp-0x1452 flag) |
| 19 | 18 | 0xD29C00  | 83 |
| 20 | 19 | 0xD48394  | 73 |
| 21 | 20 | 0xF00049  | **PRIMARY EPS-DISABLING DTC**: 4,5,6,7,8,11,12,13,14,15,16,18,19,20,21,22,23,24,25,27,28,29,38,40,41,42,43,44,45,46,47,51,55,56,58,60,62,68,116 |
| 22 | 21 | 0xF00055  | 72 |
| 23 | 22 | 0xF00316  | 36,38 |
| 24 | 23 | 0xF00317  | 37,39 |
| -- | -- | 0xF0031C  | 52 (NOTE: only 24 groups; this 25th entry in prior memory was wrong — verified row count = 24) |

NOTE on the old group table above: the prior memory (rows 1-24) was 1-indexed but the labels said group 1=0x406396. The CORRECTED table above (from direct binary read 2026-06-01) shows group 1 actually has DTC=0x000000 (a large non-standard group). The old "group 1=0x406396" was off by one. The DTC codes themselves were correct; only the group index labels shifted.

**Fault_id → DTC code direct map** at `tp-0x5AB8 = 0xB9548`:
- 0x7E entries × 4 bytes each = LE 4-byte value encoding same DTC code
- Example: fault_id=4 → [49,00,F0,00] → DTC=0xF00049

**EPS-disable (gp-0x685c = 1) trigger in FUN_000188c0:**
- Condition: `*(uint*)(fault_id * 0x1c + tp - 0x72bc) >> 0) & 1 = 1` (bit0)
  OR `>> 6) & 1 = 1` (bit6)
- Where `tp-0x58c0 = 0` and `tp-0x58bf = 6` (ROM constants)
- Fault_ids with descriptor.byte[0] bit0=1 (EPS-disabling): 4,6,7,8,11,12,14,15,16,18,19,20,21,22,23,24,25,26,27,28,29,40,42,43,44,45,46,47,48,49,51,54,55,58,68,69,116
- Fault_ids in group 21 (0xF00049) that are NOT EPS-disabling (bit0=0): 5,13,38,41,56,60,62
- fault_id 81 (DTC 0xC41668): byte[0]=0x00, NOT EPS-disabling — EPS stays enabled even if 0xC41668 fires

**Fault descriptor structure** at tp-0x72bc = 0xB7D44, stride 0x1c:
- byte[0]: bit0=EPS-disable, bit6=gp-0x685c-capable
- byte[1]: fault category code (0x0C=motor, 0x1C=sensor, 0x2D=angle, 0x3D=init)
- byte[0x0F]: function enable gate (0x01 = enabled in FUN_00016de6 check)
- bytes[0x14..0x15]: appears to be fault-check sub-function ID encoding (0x10B1, 0x10B5, 0x12B1, 0x14B1 patterns)

**Key fault trigger functions identified 2026-06-01:**
- fault_id=4 (EPS-dis): FUN_00019204 — motor init failure (gp-0x3c64 error bitmask != 0 AND gp-0x3c70==0)
- fault_id=6 (EPS-dis): FUN_000193f0, FUN_00019482 — ADC/sensor checksum mismatch
- fault_id=7 (EPS-dis): FUN_00018d02 — calibration flash-vs-RAM consistency check (ROM 0x13056..0x1306x vs RAM mirror at 0xFEDFE44C..)
- fault_id=24 (EPS-dis): FUN_0001cbdc — calibration table flash-vs-RAM mismatch (tp-0x5630 vs gp-0x3E80)
- fault_id=42 (EPS-dis): FUN_00042af8 (shaper) — TWO INDEPENDENT FIGHT-DETECTION STATE MACHINES; `FUN_00016de6(0x2a,...)` called at decompile L1399/asm 0x43de4; EXACT CONDITION: `(gp-0x6786 == 3) OR (gp-0x6785 == 3)`; gp-0x6786 = SM1 ROAD-fight state (written ONLY inside FUN_00042af8, 0x435f2/636/666/694/6ce); gp-0x6785 = SM2 ROAD-fight state (same function, 0x4372a/77c/7aa/7cc/830/860/882/8d6); both are exclusively written within FUN_00042af8; FUN_00016de6 called UNCONDITIONALLY every shaper cycle — it is NOT a trip; the actual EPS-disable bit is set inside FUN_00016de6 only when the internal enable-gate (gp-0x19d3), fault-enable flag, and status-bit conditions align; the fault call does NOT bypass or skip on V21 vs V18; gp-0x6786/6785 are derived from gp-0x6af8 (column angular velocity) and the LKAS command (uVar25) and are ZERO at startup (cmd=0) — state machines start at 0 and only advance when cmd×direction×velocity < 0 fight condition fires; ZERO dependency on gp-0x3574 or envelope value; fault_id=42 CANNOT fire at startup regardless of envelope width
- fault_id=81 (NON-EPS-dis): FUN_00053CCC via dispatch table entry group_idx=18 — ADC/measurement timeout; fires when gp-0x6bae(0xFEDF6BAE) bit2 set AND counter gp-0x32f4 >= 0x5DC=1500 cycles; ram_addr monitored = 0xFEDF6B88

**Diagnostic dispatch table** at tp-0x3aa0 = 0xBB560, 0x20-byte entries:
- Each entry: fn_ptr(+0), group_idx(+4), f8(+8), fC(+12), f10(+16), f14(+20), ram_addr(+24), f1C(+28)
- Entry param_1=15 → fn=0x534DA, group_idx=17 (DTC 0xC15500), ram=0xFEDF6BA8 (torque-sensor lockstep)
- Entry param_1=16 → fn=0x53CCC, group_idx=18 (DTC 0xC41668), ram=0xFEDF6B88 (measurement timeout)
- Dispatcher: FUN_000520d0(param_1) called for each diagnostic module index

**DTC codes 0x839440 and 0x00490E:**
- NOT FOUND anywhere in V22, V21, or stock V9 Accord TVA firmware binary
- V21 firmware changes only 17 bytes from stock (none in DTC table region at 0xB8B20)
- These codes likely came from EEPROM stored by a different/earlier firmware version
- 0x839440 has no matching table bytes; 0x00490E has w8.byte9=0x0E match at fault_id=116 (B1, EPS-disabling) — circumstantial only

[[reference-accord-tva-downstream-chain]]
