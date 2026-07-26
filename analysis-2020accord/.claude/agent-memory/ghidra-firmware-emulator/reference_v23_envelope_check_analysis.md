---
name: reference-v23-envelope-check-analysis
description: V23 envelope check (0x43172-0x431c4) behavior at rest vs active torque — does NOT trip at rest, trips at stock_diff >= +-3 during active use
metadata:
  type: reference
---

# V23 Envelope Consistency Check Analysis

## Firmware context
- Stock: `code.bin` (2113 functions, fully analyzed)
- V23: `_v23_plain_image.bin` — stock + 3-byte patches to FUN_00042af8

## V23 Patch Points (verified from bytes)
- `0x42DAE`: stock `0xC8` (shl 0x8,r9) -> V23 `0xC9` (shl 0x9,r9) — upper IIR input 2x
- `0x42F16`: stock `0xC8` (shl 0x8,r10) -> V23 `0xC9` (shl 0x9,r10) — lower IIR input 2x
- Check region `0x43172-0x431c4`: **IDENTICAL** bytes in stock and V23 (window UNCHANGED)
- Twin stores at `0x449f4` and `0x44a30`: IDENTICAL bytes

## The Check (0x43172-0x431c4, unchanged)
- Upper: `r8 = float[gp-0x6db0]`; `r12 = trunc(r8 * 1024.0)`; `r6 = int16[gp-0x6af6]`; `diff = r12 - r6`; fault if `(diff+5)` unsigned `>= 0xb` (i.e. `|diff| > 5`)
- Lower: same for `gp-0x6db8` vs `gp-0x6b00`; fault flag written to `sp+0x18`
- Fault constant 1024.0 confirmed: `movhi 0x4480 = 0x44800000 = 1024.0f`

## At Rest / Engine Start (speed=0, steer=0, LKAS_cmd=0)

### IIR states
- LERP3 output at cmd=0: **0** (RAM tables zero at boot)
- IIR input (both stock shl 0x8 and V23 shl 0x9): `0 << 8 = 0`, `0 << 9 = 0`
- IIR convergence: target=0, state_0=0 -> state stays **0**

### Integer shadows (gp-0x6af6, gp-0x6b00)
- Stock upper/lower: `0 >> 8 = 0`
- V23 upper/lower: `0 >> 8 = 0`

### FP twins (gp-0x6db0, gp-0x6db8)
- Both stock and V23: **0.0**
- V23 code cave doubles 0.0 -> still 0.0

### Check result at rest
- `diff = trunc(0.0 * 1024) - 0 = 0`
- `diff+5 = 5` (unsigned) `< 11` -> **NO FAULT** for both stock and V23

**FINDING: The +-5 check DOES NOT TRIP at engine-start or rest for either variant.**

## Active Operation: The Real Fault Mechanism

### Mathematical relationship
- V23 integer shadow = 2 * stock shadow (shl 0x9 vs shl 0x8)
- V23 FP twin = 2 * stock FP twin (code cave doubling)
- Therefore: `V23_diff = trunc(2F*1024) - 2S = 2*trunc(F*1024) - 2S = 2 * stock_diff`

### Fault threshold
| stock_diff | stock fault? | V23_diff | V23 fault? |
|------------|-------------|----------|------------|
| 0 | No | 0 | No |
| ±1 | No | ±2 | No |
| ±2 | No | ±4 | No |
| **±3** | **No** | **±6** | **YES** |
| ±4 | No | ±8 | Yes |
| ±5 | No | ±10 | Yes |
| ±6 | Yes | ±12 | Yes |

**Critical threshold: stock_diff >= +-3 trips V23 but NOT stock.**

### Why does stock_diff reach +-3?
The FP twin (computed via float LERP in FUN_00043e44) and the integer shadow (computed via integer LERP in FUN_00042af8) are two independent paths computing the same physical quantity. Float32 LERP introduces ~1-4 LSB rounding error relative to the integer path at typical operating points. Stock tolerates +-5 LSB. V23 doubles the discrepancy, so typical +-3 becomes +-6 -> fault.

### Worked example (verified by arithmetic)
- Stock: shadow=200, FP gives trunc*1024=203, diff=+3 -> passes
- V23: shadow=400, FP gives trunc*1024=406, diff=+6 -> **FAULT**

## Conclusion
V23 DOES NOT fault at rest. It faults on the first active LKAS torque request where the FP/integer rounding discrepancy reaches +-3 LSB, which is normal for any non-trivial torque command. This explains why V23 behaves correctly at idle but faults immediately when LKAS engages.

The fix requires EITHER:
1. Widening the check window to +-10 (but the check is shared code, touching it risks other effects), OR
2. Also scaling the FP twin by the same 2x factor INSIDE the check (not just in the code cave), OR
3. A different scaling approach that keeps integer shadow and FP twin synchronized

## Addresses for future reference
- IIR upper state: `gp-0x3574` = `0xFEDF4A8C`
- IIR lower state: `gp-0x3578` = `0xFEDF4A88`
- Upper int16 shadow: `gp-0x6af6` = `0xFEDF150A`
- Lower int16 shadow: `gp-0x6b00` = `0xFEDF1500`
- Upper FP twin: `gp-0x6db0` = `0xFEDF1250`
- Lower FP twin: `gp-0x6db8` = `0xFEDF1248`
