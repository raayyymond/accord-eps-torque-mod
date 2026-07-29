---
name: reference-accord-gp6a5e-is-speed-reclassifies-v44-v47
description: "gp-0x6a5e/0x6a62/0x6a64 are VOTED VEHICLE SPEED, settled. The damper Factor C LERP indexes on it, so Y[0]=0 means 'below ~35 km/h', NOT 'hands-off driver torque' — which means V44 and V47 were aimed at a mechanism that does not exist."
metadata:
  node_type: memory
  type: reference
---

**Settled 2026-07-29 by two independent traces plus a byte-verified pointer chase. This retires the
kit's "Sensor A" label and invalidates the RATIONALE behind two flashed builds.**

## 1. `gp-0x6a5e` / `-0x6a62` / `-0x6a64` are voted VEHICLE SPEED

Fresh decompile of the voter `FUN_00041eec` (`0x41eec`):

```python
# 5 channels: gp-0x6a44 / -0x6a40 / -0x6a3c / -0x6a38, plus gp-0x6a46 as a 5th reference
valid = lambda x: (x + 0x1900) < 0x9601          # i.e. -6400 <= x <= 32000
# -> a nonsensical window for a torque sensor; exactly right for a speed channel with overrange headroom
# >=2 channels agreeing within an adaptive tolerance -> output = their average
# else -> fall back to whichever raw channel is closest to the PREVIOUS cycle's own output
gp_0x6a5e = average_or_selected      # shadow-lockstepped @ gp-0x4caa
gp_0x6a62 = max_ish                  # @ gp-0x4cae
gp_0x6a64 = slew_limited_copy        # rate cal tp+0x74ee, @ gp-0x4cb0
```

Zero register / function / cal-loader overlap with `gp-0x4f60`'s producer cluster
(`gp-0x505x/506x/507x/25d4`). **There is exactly ONE torque sensor in the traced data flow: `gp-0x4f60`**
(byte-exact CAN399 producer: `STEER_TORQUE_SENSOR = -(gp-0x4f60*125/128)`).

⇒ **Retire the "Sensor A" label.** It was never a torque sensor. The genuine Main/Sub redundant pair
lives INSIDE `gp-0x4f60`'s own producer — see [[reference-accord-torque-sensor-main-sub-inside-gp4f60]].

## 2. 🛑 The damper Factor C / Factor E tables index on SPEED, not driver torque

Pointer chase byte-verified at the resolved INDEX 10 for this car (`TVAA1` → row 2 → INDEX 10):

```
0xC9E9C + 10*4 = 0xC9EC4  ->  bc 27 0d 00  =  0x000D27BC   (Factor C)
0xC9F84 + 10*4 = 0xC9FAC  ->  f8 27 0d 00  =  0x000D27F8   (Factor E)

0xD27BC:  count=4  X=(2240, 3840, 5120, 8960)  Y=(0, 235, 430, 877)
0xD27F8:  count=4  X=(  60,  400, 2500, 4000)  Y=(0, 140, 539, 927)
```

The index load in `FUN_00034350` (damping) is **`gp-0x6a5e`** — voted vehicle speed:

```
puVar11 = (uint)*(ushort *)(gp - 0x6a5e);
if (puVar11 > 0x7d00 || gp-0x67f4 != 1) uVar13 = 0x400;   # out-of-range/INVALID -> UNITY (0x400), not zero
else  { iVar22 = *(int*)(0xC9E9C + mode*4); ... LERP against puVar11 ... }
```

Using the kit's own anchor (`0xC62EA` = 320 ≈ 5 km/h ⇒ ~64 counts/km/h), Factor C's X row is
**≈ 35, 60, 80, 140 km/h**. Factor E indexes on `gp-0x6ac0` (motor resolver rate magnitude).

⇒ **`Y[0] = 0` means damping is zero BELOW ~35 km/h.** That is an ordinary speed-scheduled damper, not
a hands-off gate that stock illegitimately withheld.

⚠ Nuance worth keeping: if `gp-0x67f4` (the **speed voter's own validity flag**, written by
`FUN_00041eec` at `0x4218a`/`0x421a0`) is 0, the factor defaults to **UNITY**, not zero. The low-speed
gap only applies when the voter trusts its own reading.

## 3. 🛑 What this does to V44 and V47

Both were built on "the base-assist damping product is multiplied by ZERO below 2240 counts of DRIVER
TORQUE (hands-off)". **That premise is false.** They actually added damping in the 0-35 km/h band that
stock deliberately omits.

- Their **on-car results stand as measured** — V44 null, V47 marginally quieter at 5 mph and nothing in
  motion. Do not re-litigate the outcomes.
- Their **stated mechanism is withdrawn.** The "missing hands-off damping" hypothesis was never actually
  tested, because the thing it describes does not exist.
- ⇒ Do NOT cite V44/V47 as evidence that "hands-off damping is falsified." Cite them as evidence that
  adding low-speed damping does not fix the 20-25 Hz mode.

## 4. Where the "2240 counts driver torque" number came from — very likely a collision

The driver-override curve in `FUN_00028ea6` (`0x29a74`) is indexed by `gp-0x682f = |gp-0x4f60|>>5`, and
its first breakpoint is `X[0] = 70` ⇒ **raw torque 2240**. Factor C's speed table also starts at
**2240** — in speed counts. Two different tables, two different domains, same number. That coincidence is
the most plausible origin of the erroneous "damping is zeroed below 2240 counts of driver torque" claim.

**How to apply:** treat any `gp-0x6a5e`-indexed LERP as SPEED-scheduled. Before quoting a breakpoint in
physical units, confirm the index variable's domain rather than inheriting a label.
See [[reference-accord-driver-override-curve-kills-lkas-authority]] and
[[accord-check-build-lineage-before-proposing-lever]].
