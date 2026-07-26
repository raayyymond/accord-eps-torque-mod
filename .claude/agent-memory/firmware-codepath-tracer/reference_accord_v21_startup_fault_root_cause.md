---
name: reference-accord-v21-startup-fault-root-cause
description: Full trace of why V21 (shl 0x8->0x9 at 0x42DAE/0x42DCA) causes immediate EPS disable at startup; fault_id=6/CRC hypothesis definitively ruled out; float-monitor divergence (fault_id=29) is the most likely cause
metadata:
  type: reference
---

# V21 Startup Fault Root Cause Analysis (2026-06-01)

## Firmware context
- V21 = V18 + shl 0x8->0x9 at 0x42DAE and 0x42DCA in FUN_00042af8 (doubles upper envelope gp-0x3574)
- V18 = only PN patches at 0x13109/0x14120. Works fine.
- DTC 0xF00049 fires confirmed+active (status=0x0E) in V21.
- Analysis binary: `../accord-firmware/analysis-2020accord/_v22_plain_image.bin` (V22 = V21 patches + symmetric lower env + float monitor fix)

## fault_id=6 hypothesis — DEFINITIVELY RULED OUT

**Claim (prior agent):** fault_id=6 fires from code CRC mismatch at 0x42DAE.

**Verdict: WRONG.** Evidence:

1. FUN_000193f0 (fault_id=6 handler) decompile at 0x193f0: it checks **RAM CRC-16** over `[0xFEDF5A70, 0xFEDF5A80)` (= gp-0x2590 region) vs expected stored at `*(u16*)0xFEDF5A82`. Both addresses are runtime RAM. The "expected" value is not a flash address. This is a sensor/ADC data sanity check, completely unrelated to flash code bytes.

2. The RAM addresses (0xFEDF5A70, 0xFEDF5A82) are injected at startup by FUN_00018c44(4, sp) which overwrites the stack frame with these hardcoded values. Neither is in the flash image (both zero in binary = BSS-initialized RAM).

3. FUN_00046110 uses CRC-16 (hardware mode 1/3/5 = CRC-CCITT), not CRC-32. The flash walk uses CRC-32 (mode 0/2/4).

## Flash CRC walk — PASSES for V21

**FUN_0005c5fe -> FUN_0005c728 (flash block CRC walk):**

- Block descriptor at 0xC4FF0: covers main code block [0x13000, 0xC4FFC), CRC-32 at 0xC4FFC.
- This block covers BOTH V21 patches (0x42DAE) AND V18 patches (0x13109).
- V21 build script correctly computes `zlib.crc32(data[0x13000:0xC4FFC])` and updates 0xC4FFC.
- Verified on actual V21 rwd: all 49 blocks PASS (0 failures).

**Hardware algorithm confirmed:** FUN_0006b8f4 disasm shows it reads ALL 8 dwords per 32-byte chunk sequentially via sst.w to ep=0xFFFFFA00. This IS full sequential CRC-32. Python's `zlib.crc32` is the correct equivalent.

**No secondary sub-range CRC exists that covers 0x42DAE but not 0x13109.** The main block CRC is the only one covering that address range. There is no "hidden" per-page or per-function CRC in the firmware.

## fault_id=7 — NOT triggered by V21

FUN_00018d02 checks ROM bytes at 0x1304c..0x13069 vs RAM mirror. V21 patches at 0x42DAE are far outside this range.

## fault_id=42 — CANNOT fire at startup

V21's doubled gp-0x3574 does not affect gp-0x6786/6785 (fight state machines). These require cmd != 0 AND column velocity != 0. At startup: both are 0. State machines start at 0 and never advance.

## Most likely root cause: fault_id=29 via float-monitor divergence [INFERENCE]

**Evidence (inference, not confirmed):**
- fault_id=29 (0x1d) is EPS-disabling, in group 0xF00049.
- FUN_000462e6 -> FUN_00016de6(0x1d) fires when `|fVar24| >= 128.0` in FUN_00044234 (float monitor function, part of FUN_00043e44 in V21).
- V21 doubles integer upper envelope (gp-0x3574 = 2x) without matching the float monitor model.
- Float monitor reads gp-0x3554 (its own IIR state, separate from gp-0x3574). This causes integer vs float envelope divergence.
- fVar24 = sum of multiple error terms. With asymmetric envelope (upper 2x, lower 1x), some error term > 128 within a few control cycles.
- **V22 was built specifically to fix this**: V22 description says "float-monitor 2x match to prevent f1/f3/f6 do not diverge -> no 0x3f1b CAN fault". V22 adds code cave at 0xC4FC0 to double float monitor's upper/lower raw before the IIR.

**State machine gate in FUN_00044234:**
- State 0 (first call): fVar24 forced to 0 — no fault on first call
- State 1 (second call): monitoring starts, error terms computed
- State 2+ (third+ call): if |fVar24| >= 128 -> FUN_000462e6 -> fault_id=29 -> 0xF00049
- At 1ms control cycle: 3 cycles = 3ms = "immediate" from operator perspective

**Why V18 doesn't trigger it:** V18 has NO code patches. gp-0x3574 = stock 256x scale. Float monitor sees no divergence. fVar24 ≈ 0.

## Key address facts

| Address | Value | Meaning |
|---------|-------|---------|
| 0xC4FF0 | desc | Main block CRC descriptor |
| 0xC4FFC | 0x71B920BE (V21) | Main block CRC-32 [0x13000,0xC4FFC) |
| 0x42DAE | 0xC9 (V21) | shl 0x9,r9 (was 0xC8 = shl 0x8) |
| 0x42DCA | 0xC9 (V21) | shl 0x9,r11 (was 0xC8 = shl 0x8) |
| 0x42F16 | 0xC8 (V21) | shl 0x8,r10 — lower env, UNCHANGED in V21 |
| 0x44230 | ld.hu (V21) | Original instruction; V22 redirects to code cave |
| 0xC4FC0 | code cave | V22 only: mulf.s to double float monitor raw values |

## Open questions requiring live debugging

1. Which specific fault_id in group 0xF00049 actually fires? (gp-0x2d7c read was DENIED)
2. How many control cycles before fVar24 exceeds 128? (Need runtime trace)
3. Does gp-0x3540 (float monitor state) reset correctly on cold boot?
4. Does V22 (with float monitor fix but same code patches) actually work? (Not yet confirmed)

## Key fault_id reference

- fault_id=6: RAM CRC (sensor data), NOT EPS-dis from code patches. Handler: FUN_000193f0.
- fault_id=29 (0x1d): EPS-dis, in group 0xF00049. Fired by FUN_000462e6 from float monitor. Handler: called from FUN_00044234 @0x44a42.
- fault_id=42: Fight detection (EPS-dis). Cannot fire at startup. Only in FUN_00042af8 @0x43de4.

[[reference-accord-integrator-update-form]]
[[reference-accord-dtc-construction-mechanism]]
