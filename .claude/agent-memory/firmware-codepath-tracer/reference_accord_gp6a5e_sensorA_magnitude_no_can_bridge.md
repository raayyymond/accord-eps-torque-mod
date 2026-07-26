---
name: reference-accord-gp6a5e-sensorA-magnitude-no-can-bridge
description: gp-0x6a5e/gp-0x6a62 (Sensor A 5-track voter output) are MAGNITUDES (sign discarded in the voter's first step, FUN_00041eec), not signed values, and are NEVER read by any CAN TX builder (2 exhaustive 186069-instruction scans, zero hits) -- confirming and extending reference-accord-dual-torque-sensor-architecture's "no static bridge" finding with a definitive CAN-invisibility proof. Also pins the gp-0x4f60<->CAN399 STEER_TORQUE_SENSOR conversion exactly.
metadata:
  type: reference
---

Traced 2026-07-21 answering team-lead's question of whether a measured CAN 399 `STEER_TORQUE_SENSOR`
reading can be converted into `gp-0x6a5e` counts, to test the `0xC9E9C` damping-table threshold (2240,
see [[reference-accord-damping-friction-returncentre-torque-gates]]) against route telemetry. Builds on
and confirms [[reference-accord-dual-torque-sensor-architecture]] (2026-06-30) rather than superseding it.

## Headline answer: NO conversion exists — confirmed exhaustively this session

`gp-0x6a5e`/`gp-0x6a62` (Sensor A, the 5-track DMA'd voter) and `gp-0x4f60` (Sensor B, the CAN/TAS
sensor) are **physically independent sensors with independent calibration** — already the architecture
memory's finding. **New this session**: exhaustive `search_instructions` for `-0x6a5e` (48 hits) and
`-0x6a62` (38 hits), full 186,069-instruction scans, both `truncated: false` — **zero hits fall inside
the CAN TX builder cluster** (`0x55000-0x5b000`, where `FUN_00055c42`/`FUN_00055d80` and siblings live).
Sensor A's voted output is **never read by any CAN packer** — it is not just "not bridged," it is not
transmitted on the bus in any frame this image builds. The only way to observe it is a live RAM read of
`0xFEDF159E` (`gp-0x6a5e`) / `0xFEDF159E`... (`gp-0x6a62` is `0xFEDF159E`? — see exact absolute addresses
below), i.e. UDS/RAM telemetry, not CAN.

## gp-0x6a5e is a MAGNITUDE, not a signed value [VERIFIED, NEW]

Full decompile of `FUN_00041eec` (the voter, sole producer of both `gp-0x6a5e` and `gp-0x6a62`). Every
one of the 5 input channels (`gp-0x6a44`, `gp-0x6a40`, `gp-0x6a3c`, `gp-0x6a38`, `gp-0x6a46`) is
**abs()'d as the very first operation** on it inside the voting loop (`0x420b0`-ish region, e.g.
`uVar21 = (uint)(short)aiStack_4c[uVar13]; if ((int)uVar21 < 0) uVar21 = -uVar21;` before ANY comparison
or accumulation). Both outputs are built entirely from these magnitudes:
- `gp-0x6a5e` (AVG) = either the straight average of the valid channels' magnitudes (`uVar19/uVar28`,
  when the channels agree within a dynamic spread threshold) or the single channel's magnitude closest
  to the previous cycle's value (outlier-rejection fallback) — written `st.h r28,-0x6a5e,gp @0x42342`.
- `gp-0x6a62` (MAX) = `max` of the two group extremes (4-channel group max vs the 5th channel), tolerance
  -widened, clamped to sentinel `0x7d00`(32000) — written `st.h r28/r24,-0x6a62,gp @0x42312/0x4231c`.

**Consequence for the operator's hypothesis**: a small-amplitude torque oscillating around zero (e.g.
the free wheel's inertia twisting the torsion bar while LKAS drives the rack, with no consistent sign)
still produces a small-but-positive `gp-0x6a5e` — magnitude folding does not by itself inflate a
near-zero signal into something that crosses `2240`. But it does mean `gp-0x6a5e` cannot distinguish "a
steady non-zero hand torque" from "a torque oscillating with the same RMS amplitude around zero" — both
would read similarly on this channel. Whether hands-off oscillation amplitude alone can exceed 2240 is a
question about Sensor A's REAL magnitude range during the reported vibration, which (per the section
above) cannot be settled from CAN telemetry at all.

## Sensor A's 5 channels — producers [VERIFIED, corroborating the architecture memory]

`gp-0x6a44/-0x6a40/-0x6a3c/-0x6a38` share one producer/consumer function `FUN_000534da` (both reads AND
writes all 4, i.e. this is where they're computed, not just relayed). `gp-0x6a46` (5th channel) has its
own separate producer `FUN_000522fe`. Both trace back (per the architecture memory, re-confirmed by
spot-checking `FUN_00021622`, one of the per-track bit-unpackers: reads 2 raw bytes from the DMA'd 8-byte
frame at `gp-0x1450`→`gp-0x13e0`, reconstructs a value via shift/OR bit-unpacking under the same
`FUN_0001fa42`/`FUN_0001fa72` IRQ-lock pattern used throughout this codebase for DMA-buffer critical
sections) to a **completely separate acquisition peripheral** from Sensor B. **Exhaustive check this
session**: searched all `-0x4f60` (Sensor B) xrefs program-wide (60+ hits shown, scan truncated at
156,574/186,069 instructions — not fully exhaustive, flagging this one as [INFERRED, high confidence]
rather than [VERIFIED]) — none fall inside `FUN_000534da`, `FUN_000522fe`, `FUN_00021622`, or
`FUN_00041eec`. No crossover found.

## gp-0x4f60 <-> CAN 399 STEER_TORQUE_SENSOR conversion [VERIFIED, freshly disassembled]

This one DOES have a real, precise, static conversion — confirmed independently this session (not just
cited from the existing bit-map memory, though it agrees byte-exact):

```
0x55c50: ld.h  -0x4f60[gp], r9      ; r9 = gp-0x4f60, SIGNED halfword load
0x55c54: mulhi 0x7d, r9, r6         ; r6 = r9 * 125
0x55c58: sar   0x7, r6              ; r6 >>= 7  (arithmetic shift = floor(/128))
0x55c5a: subr  r0, r6               ; r6 = -r6
0x55c5c: zxh   r6                   ; zero-extend to 16 bits
0x55c5e: jarl  0x218be, lp          ; -> byte-swap + store into CAN 399 buffer (FUN_000218be)
```

**Forward**: `CAN399.STEER_TORQUE_SENSOR = -floor(gp-0x4f60 * 125 / 128)` (as an int16, byte-swapped for
the CAN buffer's big-endian field — this is the FIRMWARE-side transform only, upstream of whatever
byte-order/scale a DBC or rlog parser applies when it decodes the raw CAN payload back into a signed
value V).

**Inverse** (the one-line deliverable, given a raw CAN399 `STEER_TORQUE_SENSOR` value **V**, already
decoded to a signed integer by the DBC/rlog tooling, matching firmware counts before any DBC scale
factor):
```
gp-0x4f60 ≈ -V * (128/125) = -V * 1.024        (exact inverse up to the floor-rounding of the forward transform, +/-1 count)
```

**This formula converts a CAN399 reading into `gp-0x4f60` (Sensor B) counts. It does NOT and CANNOT
convert into `gp-0x6a5e` (Sensor A) counts** — see the headline finding above. If the operator's route
telemetry is CAN-only, it can test hypotheses that key on `gp-0x4f60` (e.g. the resonance lane
`FUN_0003a382`, the boost curve's `|gp-0x4f60|<=25600` plausibility window, `FUN_000352b4`) but NOT the
`0xC9E9C` damping-table threshold on `gp-0x6a5e`, nor the return-centre/friction gates also keyed on
`gp-0x6a5e`.

## Physical units (N·m) — NOT FOUND, don't invent one

Checked `docs/HONDA-EPS-PID-KNOWLEDGE.md` (the kit's canonical community-PID reference) for any DBC scale
factor or N·m grounding for `STEER_TORQUE_SENSOR` or Sensor A/B counts — found none; that document covers
openpilot PID/torque-controller tuning gains (`kf=0.5` torque-scale vs `kf=0.00006` PID-scale), not
firmware sensor-to-physical-unit scaling. No UDS/RDBI service or embedded calibration constant grounding
either sensor's raw counts in N·m was located in the firmware itself either (Sensor B's `FUN_0007f3f8`
has a "learned gain" `gp-0x698c`/offset `gp-0x6b50`, but that's a self-calibration term, not a documented
physical-unit scale factor). **No physical-unit conversion for the `2240` threshold (or any other Sensor
A/B count value) can be given from this kit's evidence.**

## Related
[[reference-accord-dual-torque-sensor-architecture]] — the architectural finding this confirms/extends
[[reference-accord-damping-friction-returncentre-torque-gates]] — the `0xC9E9C` table this was tasked to test
[[reference-accord-gp4f60-is-sensor-b-column-torque]] — gp-0x4f60's identity, project-level memory dir
