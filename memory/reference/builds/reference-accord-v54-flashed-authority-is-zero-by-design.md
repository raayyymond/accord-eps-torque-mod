---
name: reference-accord-v54-flashed-authority-is-zero-by-design
description: "V54 FLASHED 2026-07-27 -- the piggyback probe FIRED (first working firmware telemetry channel in this kit, proven by a one-bit A/B). gp-0x6966 is the soft-EME wind-up magnitude, NOT a speed-scheduled authority, and is ~0 BY DESIGN on V31+ because the boost floor makes wind-up unreachable. 0xC6AF0 therefore selects unity always: mute is the only meaningful edit, but GATE 2 stays open."
metadata:
  node_type: memory
  type: reference
---

# V54 flashed: the probe fired, and authority is ~0 by design

**A/B proof the cave ran** (one bit, exactly the one we wrote), route `1a` (V53) vs `1b` (V54):

| build | `0x14A` byte4 | bits 7:3 | bits 2:0 |
|---|---|---|---|
| V53 (no probe) | `0x07` x 5,994 (100%) | 0 | 7 |
| **V54** | `0x0F` x 5,989 (100%) | **1** | 7 |

Fault-free: `steerFaultTemporary`/`Permanent` both 0, `canValid` 5,711/5,713. **The `0x14A` byte4
bits 7:3 piggyback is now proven end to end. Use it for all future firmware telemetry.**

## What `gp-0x6966` actually is

```
gp-0x3570 += (command - bound), clamped +-(cal 0xC61DC = 30720)
gp-0x6966  = |gp-0x3570 >> 15| * (cal 0xC61DA = 1092) >> 10     [max 32760 ~ Q15 1.0]
```

The bound is a 3-way gated MAX/MIN of corridor (driver-override), boost (angular rate), IIR (column
velocity). **No arm is vehicle road speed.** On **stock** the boost arm's `Y[0] = 0`, so at low angular
rate the bound collapses and the integrator winds (the V30 hands-off-hard-turn EME). **V31 floored boost
to 4096 and V38 raised it to 5120**, so the bound cannot collapse and the integrator sits pinned.

**Measured: wire == 1 in 5,989/5,989 frames** => `gp-0x6966` in [0,127] = **0.39% of saturation**, zero
variation, *including 17% of requesting frames at openpilot's +-4096 rail*. Reaching the first knee needs
`|gp-0x3570>>15| >= 3073` vs an observed **<= 119**.

=> This converts V31's fixpoint from "argued, with a residual margin caveat" into **on-car evidence under
railed command**. That is the drive's real contribution.

**Do NOT re-drive faster to move it.** It is wind-up-driven, not speed-driven. A reachability claim must
always be scoped to a build: "3277 is easily reachable, documented on-car" is true of **stock/V30** and
false of the flashed image.

## Consequence: `0xC6AF0` unblocked

Authority ~0 sits in the table's first flat segment (X = 0/3277/3604/19661/32768,
Y = 32768/32768/0/0/0), so **Y = 32768 (unity) is selected in 100% of normal operation** -- the
`FUN_0003a382` residual lane runs at **full output bound** always, including throughout the vibration.
=> "keep-live" is a no-op; **mute (`Y[0]`,`Y[1]` -> 0) is the only meaningful edit.**
Zeroing them disables no live protection (the derate is never invoked).

**GATE 2 IS NOT CLOSED.** The measurement proves the lane is **live**, not that it is the **culprit**.

Chain re-verified in Python, independent of Ghidra: `0x3a632 ld.hu -0x6966[gp],r11`;
`0x3a636 movea 0x7af0,tp,r15` (tp=0xBF000 -> `0xC6AF0`); `0x432c8 st.h r13,-0x6966[gp]` (16-bit).

**Process lesson:** this was partly predictable from [[reference-accord-soft-eme-bound-arm-gating]],
which already said V31 makes authority never climb. Check memory before building the instrument.
