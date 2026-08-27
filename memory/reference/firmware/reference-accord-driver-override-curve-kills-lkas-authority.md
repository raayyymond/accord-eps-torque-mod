---
name: reference-accord-driver-override-curve-kills-lkas-authority
description: "The operator's 'significant driver torque in a direction kills the grinding' is a mapped, byte-verified authority cutoff: a curve indexed by |gp-0x4f60|>>5 with direction from sign(gp-0x4f60) drives LKAS authority 254 -> 0 between raw torque 2240 and 3584."
metadata:
  node_type: memory
  type: reference
---

**Found 2026-07-29 in `FUN_00028ea6` (arbitration), block `0x29a74`+. Byte-verified by the lead at the
pointer targets, not taken on report.** This is the firmware mechanism behind a long-standing operator
observation, and it is an off-switch, NOT an oscillator.

## The code

```
0x29a74: ld.bu -0x6803, gp, r10      ; mode flag
0x29a78: ld.bu  0x74b8, tp,  r8      ; cal 0xC64B8  (stock 112; 0xFF on every build since V37)
0x29a7c: ld.bu -0x682f, gp, r1       ; gp-0x682f = min(|gp-0x4f60| >> 5, 255)
0x29a86: cmp   r8, r1
0x29a88: bnh   0x29a8e               ; torque_byte <= cal -> continue
0x29a8a: jr    0x29cc4               ; else -> DIVERT to a frozen-value path (gp-0x6830)
0x29a90: ld.h  -0x4f60, gp, r12      ; the REAL SIGNED torque sensor
0x29a94: blt   0x29a9c               ; branch on SIGN -> selects which curve table
   r12 >= 0 -> 0x29aa0 : curve set @0xcba74, blended with @0xcb924
   r12 <  0 -> 0x29b7c : curve set @0xcba04, blended with @0xcb8b4
```

⚠ **The `0xC64B8` threshold branch is DEAD on the current lineage.** V37 set that cal to `0xFF` (for an
unrelated reason — the DTC-0x49 fail-counter gate), and `gp-0x682f` saturates at 255, so
`torque_byte <= 0xFF` is now **always true** and the `0x29cc4` frozen path is unreachable on the car as
driven. The live mechanism is the CONTINUOUS CURVE COLLAPSE below, not the threshold branch.

## The curves — byte-read from the stock image at the resolved pointer targets

```
0xCBA74 -> [0x0E4468, 0x0E447C, 0x0E4490, 0x0E44A4]
0xCBA04 -> [0x0E43F0, 0x0E4404, 0x0E4418, 0x0E442C]
0xCB8B4 -> [0x0E4270, 0x0E4284, 0x0E4298, 0x0E42AC]
0xCB924 -> [0x0E42E8, 0x0E42FC, 0x0E4310, 0x0E4324]

0xE4468 / 0xE447C / 0xE43F0 : count=4  X=[70,72,78,80]      Y=[254,234,12,0]
                              -> raw |gp-0x4f60| = 2240, 2304, 2496, 2560
0xE4270                     : count=4  X=[32,38,80,112]     Y=[255,255,255,0]
0xE42E8                     : count=4  X=[32,42,80,112]     Y=[255,255,255,0]
                              -> raw |gp-0x4f60| = 1024, 1216/1344, 2560, 3584
```

The sign<0 table `0xE43F0` is **identical** to the sign>=0 table at this mode index, so direction selects
*which memory is read*, not a different shape. (Mode index `gp-0x674e` assumed 0 — NOT independently
confirmed; a different index could carry an asymmetric curve.)

## What it means

**LKAS authority holds full weight (254/255) at light torque and collapses to EXACTLY ZERO between
roughly 2240 and 3584 raw torque counts, in whichever direction the driver pushes.** In DBC units
(`STEER_TORQUE_SENSOR = -(gp-0x4f60 * 125/128)`) that is about **±2190 to ±3500**.

Downstream this continues through the `gp-0x3d3c` EMA, the `gp-0x6b30` sign-guard, the 4x gain at
`0x2a1ee`, and out to `gp-0x6b3c` → `gp-0x6b4c` → aggregator → `gp-0x6b98` → motor. So crossing this
band gates the entire LKAS delivery.

## 🛑 It explains the KILL, not the CREATION

Measured on route 24 (V56, road), engaged frames:
```
|torque|     0- 500 : 88.74%      <- where the grinding lives; curve saturated at full authority
|torque|   500-1000 :  5.61%
|torque|  1000-2240 :  1.49%
|torque|  2240-3584 :  0.42%      <- the collapse band, genuinely reached on real drives
```
Hands-off, torque ≈ 0, the curve is flat at 254 and contributes **no gain variation** — so it cannot be
the oscillator. It is the reason applying firm directional torque makes the mode vanish.

⚠ It also explains why a naive rlog sweep looks like it CONTRADICTS the operator: in high-torque bins
LKAS authority is already zero so there is no mode to measure, while broadband power from active steering
is at its maximum. Any driver-torque sweep must use a PROMINENCE estimator (peak / local floor), never
raw band power, because the conditioning variable is the measured channel.

**How to apply:** when testing anything about driver torque and the mode, split at ~2240 raw counts and
know that above it you are measuring a disabled controller, not a quiet one.
See [[reference-accord-gp6a5e-is-speed-reclassifies-v44-v47]] (the 2240 number collides with an unrelated
speed breakpoint) and [[reference-accord-deadband-signgate-eliminated-on-car]].
