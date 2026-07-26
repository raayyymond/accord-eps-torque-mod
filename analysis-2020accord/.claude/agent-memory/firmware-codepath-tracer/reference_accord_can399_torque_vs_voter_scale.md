---
name: reference-accord-can399-torque-vs-voter-scale
description: CORRECTED 2026-06-30. gp-0x6a62 (gate, voter MAX of 5 coil tracks, rising-edge UNFILTERED) and CAN STEER_TORQUE_SENSOR (gp-0x4f60) are TWO DIFFERENT SENSORS. NO static scale bridge ("~1:1" was WRONG). Needs a live RAM read.
metadata:
  type: reference
---

2020 Accord 39990-TVA-A160, V850E2. STOCK code.bin. gp=0xFEDF8000, tp=0xBF000. [V] = disasm-verified.

## ⚠ CORRECTION (2026-06-30): the two are DIFFERENT SENSORS, not one signal at ~1:1
The prior version of this memory claimed `gp-0x6a62 : |CAN STEER_TORQUE_SENSOR| ≈ 1:1`. **That is wrong.** They are two physically independent torque acquisitions with independent calibration — see [[reference-accord-dual-torque-sensor-architecture]] for the full upstream trace. There is **no derivable static ratio**; the only way to pin the gate scale is a **live RAM read of `gp-0x6a62` (0xFEDF159E)**.

## gp-0x6a62 (the gate signal) = voter FUN_00041eec output [V]
- = **MAX** of the 5 column-coil track magnitudes (`gp-0x6a44/-0x6a40/-0x6a3c/-0x6a38/-0x6a46`), each = raw_ADC × 41/64 (`FUN_00053216` @0x53474 `mul 0x29`, @0x53480 `sar 0x6`).
- **Rising edge: instantaneous, NO filter.** The slew limiter is **decay-only** (16 counts/voter-cycle, cal 0xC64ED=0x10); it only governs recovery, not the peak. ⇒ the old "rate-limit lags so 320 trips while CAN reads 1633" story is FALSE — on a torque spike `gp-0x6a62` tracks the instantaneous peak coil.
- clamp 32000. RAM shadow twin `gp-0x4cae` (0xFEDF35B2). `gp-0x6a5e` = the AVG/voted twin (not the max).

## gp-0x4f60 (the CAN torque) = a SEPARATE sensor (sensor B / TAS) [V]
- Producer `FUN_0007f3f8` (decompile fails, ENCA0 struct) reads raw `gp-0x505c` ← parser `FUN_000829e2` ← dual-channel CRC'd frame `gp-0x548`/`gp-0x544` ← `FUN_0007df80`. Carries torque **+ absolute angle + temp + embedded cal** (a Torque-Angle Sensor). Applies a LEARNED gain `gp-0x698c`/offset `gp-0x6b50`.
- Packer `FUN_00055c42`: `STEER_TORQUE_SENSOR (bytes[0:1]) = -(gp-0x4f60 × 0x7d >> 7) = -(gp-0x4f60 × 125/128)`. `STEER_ANGLE_RATE (bytes[2:3]) = -(gp-0x6a56)`. Commit `FUN_00057b24(gp-0x1420, 7, 399)`.

## TO PIN THE GATE SCALE
Read `gp-0x6a62` (`0xFEDF159E`) live at held torques and during a hard hands-off turn(+bump). Optionally read `gp-0x4f60` (`0xFEDF30A0`) or the CAN `STEER_TORQUE_SENSOR` alongside to relate them — but they will NOT be 1:1; expect the gate units much smaller than CAN (road EME onset is CAN ~1239–2290 while the gate is at 320, hinting ~1:4–5, but that is empirical, not derivable). This is the blocker for choosing the gentle-EME threshold; see the 2026-06-30 handoff.
