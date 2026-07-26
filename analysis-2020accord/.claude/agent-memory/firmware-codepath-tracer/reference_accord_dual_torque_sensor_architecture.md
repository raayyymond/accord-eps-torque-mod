---
name: reference-accord-dual-torque-sensor-architecture
description: Accord TVA-A160 has TWO independent column-torque sensors — A (gate/assist, DMA 5-track, gp-0x6a62/gp-0x6a5e) and B (CAN/TAS, gp-0x4f60). Upstream + forward paths traced; no static scale bridge between them.
metadata:
  type: reference
---

# 2020 Accord 39990-TVA-A160 — two independent column-torque sensors

Stock code.bin (/master.bin, 2113 fns). gp=0xFEDF8000, tp=0xBF000. All [V]erified by disasm/byte-read this session (2026-06-30). The EPS reads driver column torque through **two physically distinct acquisition paths** with independent calibration. This is the load-bearing fact behind "the gentle-EME gate scale can't be derived from CAN."

## Sensor A — the CONTROL/GATE sensor (gp-0x6a62 / gp-0x6a5e)
- HW: an 8-byte serial frame is **DMA'd** into RAM `gp-0x1450` (NO cpu writer exists anywhere — only `FUN_00021970` reads it [V]). Acquisition dispatched by `FUN_000520d0` (channel 0x10), TAUA0-timer paced.
- `FUN_00021970` copies the 8 bytes `gp-0x1450 → gp-0x13e0` under an IRQ-lock (`FUN_0001fa42`/`FUN_0001fa72` = nested IRQ-disable critical section, counter gp-0x163c — NOT a peripheral driver).
- 5 readers bit-unpack 5 fields = **5 coil "tracks"** from those 8 bytes, each `× 41/64` (`FUN_00053216` @0x53474 `mul 0x29` / @0x53480 `sar 0x6`): `FUN_00021622→gp-0x6a44`, `FUN_00021646→gp-0x6a40`, `FUN_00021672→gp-0x6a3c`, `FUN_0002169e→gp-0x6a38`; ch5 via `FUN_000522fe`←`FUN_00021706→gp-0x6a46`.
- Voter `FUN_00041eec` → `gp-0x6a5e` = AVG/voted, `gp-0x6a62` = **MAX** of |tracks| (rising-edge unfiltered; decay slew 16/cyc cal 0xC64ED; clamp 32000). See [[reference-accord-can399-torque-vs-voter-scale]].
- Consumers: the disengage gate (`gp-0x6a62 ≥ 0xC6312=320`, [[reference-accord-lkas-engage-sm-disengage-trigger]]), the assist boost curve (`gp-0x6a5e` → table 0xce578 `[612..1238]` increasing, ×'d in `FUN_00034a72`), and the arbitration setpoint cap (flat 15360, [[reference-accord-arbitration-limit-family]]).

## Sensor B — the CAN/TAS sensor (gp-0x4f60)
- HW: a different receive peripheral (status regs via `FUN_0005d99c`/`FUN_0005da64`) collects a nibble-tagged serial stream into raw buffer `gp-0x578`. `FUN_0007007c`→`FUN_0006ff68` **software-de-frames** it into **TWO sub-channels** `gp-0x548` (ch0) + `gp-0x544` (ch1) = main+sub, each **4-bit CRC** checked (`FUN_0006b5a2`).
- `FUN_0007df80` sequences frames; parser `FUN_000829e2` (nibble-tag state machine) → raw torque `gp-0x505c` + **absolute steering ANGLE `gp-0x25cc`** + temp + the sensor's **embedded gain cal `gp-0x25d4`**. So sensor B is a **Torque-AND-Angle Sensor (TAS)**.
- `FUN_0007f3f8` (decompile FAILS — ENCA0 struct; use disasm): 2-pt interp + per-sensor gain `gp-0x25d4` + phase corr `FUN_0007f300` + **LEARNED gain `gp-0x698c`/offset `gp-0x6b50`** + clamp `gp-0x4f54` → `gp-0x4f60` (store @0x7f9c8).
- Packed to CAN 399: `FUN_00055c42`: `STEER_TORQUE_SENSOR = -(gp-0x4f60 × 125/128)`. Sensor B is the ONLY one carrying absolute angle → it is the CAN-reported sensor (also packs STEER_ANGLE_RATE = -(gp-0x6a56)).

## Why two sources (observed, not assumed)
Two distinct receive peripherals + protocols + framing + calibration. Sensor B is independently dual-channel (main+sub) and CRC'd; sensor A is independently 5-track voted. Both feed the same control law (A = assist-curve axis + gate; B = sign + fault-guard ±25600 + CAN). This is **diverse redundant torque sensing**; B doubles as the angle (TAS) source, which is why it's the CAN sensor. They measure the same torsion bar but are **independent measurements with independent (learned/embedded) calibration**.

## THE consequence (load-bearing)
**No static numeric bridge exists between `gp-0x6a62` (gate units) and CAN `STEER_TORQUE_SENSOR` (sensor B units).** The old "~1:1" assumption was unfounded. Road data (CAN) cannot be used to set the gate threshold `0xC6312`. → a **live RAM read of `gp-0x6a62` (0xFEDF159E)** is the only way to pin the gate scale. The plausibility/vote checks are intra-A only (the 5 tracks agree + temporal continuity), NOT an A-vs-B comparison.

## Forward to motor (both sensors land here)
`gp-0x6b3c` (arb final) → `m_steer_torque_limit_and_pack` (ENABLE byte `gp-0x67a4`∈{2,3}) → `m_motor_cmd_distribute_clamp` (clamps ±16384/±10240/±900/±20000; writes per-phase setpoints `gp-0x62e0[phase]` + siblings) → `m_motor_cmd_mixer` (reads `gp-0x62e0` @0x26dd8/e74/fce) → TAUJ0/TAUJ1 PWM timers → motor. (distribute_clamp / mixer-cluster fail to decompile precisely on TAUJ0RSF/TAUJ1RSF = the PWM stage fingerprint.)
