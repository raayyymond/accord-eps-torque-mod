---
name: accord-v58-boostlane-probe-built
description: "V58 BUILT 2026-07-30, unflashed: V57 with the cave payload replaced by an angle-rate/boost-lane probe. bit6 = sign(gp-0x6bbe) measures the damping phase on-car against STEER_ANGLE_RATE, which four rounds of static analysis could not settle. Zero calibration change — the CAL CRC is unchanged."
metadata:
  type: project
---

# V58 — the angle-rate/boost-lane probe (BUILT 2026-07-30, UNFLASHED)

**V58 = V57 with ONLY the cave payload replaced.** Same base `0xC4B34`, same hook `0x55C0E`, same 68-byte
extent — an envelope that has flown fault-free twice (V55, V57). A post-processor over
`_v57_plain_image.bin`; it transcribes nothing.

```
0x14A byte4:  bit7 = 1                    LIVENESS (field==0 => cave did not fire => VOID)
              bit6 = (gp-0x6bbe <  0)     THE DAMPING PHASE
              bit5 = (gp-0x6bbe == +512)  lane pinned at its ceiling (0xD20C0, flat 512)
              bit4 = (gp-0x6b9a <  0)     boost AMPLITUDE GATE sign (the FIR chain output)
              bit3 = (gp-0x6b9a == 0)     that gate dead
              bits 2:0 = stock STEER_SENSOR_STATUS, preserved
RWD   SHA 7b3cfff05116a22137c1376b78e69d955ac75397b8091e089da4b0379a5948f7
image SHA 431117459a42dc2e7906446261c7175bf2d0cc35b88290f2fdeb9b779d654c48
```

**59 bytes off V57** (cave payload + MAIN CRC only), 86 off V38. **The CAL CRC is unchanged** — machine
proof that no calibration byte moved. 50/50 bootloader CRC on the built image *and* the readback; RWD
round-trips byte-identically; the cave is re-disassembled **from the built image** and compared
instruction-by-instruction to the listing.

## Why a probe and not a lever

Every calibration lever for both symptoms is closed (see `docs/BUILD-LINEAGE.md`), and the `gp-0x6bbe`
damping sign flipped **four times** under static analysis — see
[[accord-gp6a56-is-motor-rate-not-an-angle-sensor]]. The golden model cannot simulate it. So measure it.

- **bit6** — `STEER_ANGLE_RATE` is already on the bus (`0x18F[2:4]`), so the cross-spectrum phase of bit6
  against it at 20-25 Hz gives the sign directly. ~180° ⇒ viscous damping (raising `K1` @`0xD200C`=43
  adds damping); ~0° ⇒ anti-damping (cutting is the direction); quadrature ⇒ `K1` is not a lever.
- **bit5** decides whether `K1` is a lever *at all*. The ±512 ceiling is a **SATURATING** clamp, so if the
  lane pins, the damping derivative is **zero at the peaks** and the lever becomes the ceiling
  (`0xD20C0` Y row), not `K1`. ⚠ Only the positive rail is exactly testable (`x>>9 == 1` iff `x == 512`;
  `x>>9 == -1` for **all** `x` in `[-512,-1]`) — read the negative rail from bit6+bit5 jointly.
- **bit4/bit3** test the mechanism found the same day: `gp-0x6b9a` is the FIR chain's output and indexes
  boost's **non-flat** table `0xD28DC` (Y = 16384..8187 — more motor rate, half the boost amplitude),
  landing as `blendedMagnitude` in `term3 = (term2 * blendedMagnitude) >> 14` @`0x34ffa`.

## The method was pre-validated, not hoped for

V57's bit3 is also a 1-bit sign channel, and against `STEER_ANGLE_RATE` on route 29's burst it returned
**coherence 0.958 at 21.31 Hz** (K=6). A comparator preserves zero-crossing timing, which is exactly what
phase estimation needs. Implied constant delay from the 6-27 Hz phase slope: **−1.0 ms** (~8° at 22 Hz),
so mailbox skew between `0x14A` and `0x18F` is small — an in-firmware rate reference bit was considered
and dropped as unnecessary.

## Cave discipline

Read-only, four exact single comparisons plus one arithmetic shift, no arithmetic on any signal, no new
RAM, registers **r6/r7 only** (V57's exact budget). Only condition codes **pinned to real instruction
instances** are used (`BGE` 0xE, `BNE` 0xA); `BLT` was pinned (`b6 05` @`0x1c006`) but deliberately not
needed. ⚠ Still **code in the 1 kHz TX path** — a higher risk class than cal-only, which is why the
base/hook/extent are reused rather than moved. Code caves are this kit's only bricking class.

**Not probeable, deliberately omitted:** the ±666 mid-chain clamp and the `rate_error` ±12000 clamp inside
`FUN_00034a72` are transient registers (r13/r22), never stored.

Decoder: `rlog-tools/probe/decode_v58_boostlane.py`. It enforces lateral engagement, sustained-effort hands-off,
and non-overlapping segments — see [[accord-telemetry-conventions-that-produced-wrong-answers]].
