---
name: v54-flashed-authority-measured
description: "V54 FLASHED 2026-07-27 — the probe FIRED (first working firmware telemetry channel); gp-0x6966 is the soft-EME windup magnitude, NOT a speed-scheduled authority, and is identically 0 on V31+ because V31's boost floor makes windup unreachable; 0xC6AF0 direction is therefore MEASURED and the block is lifted."
metadata: 
  node_type: memory
  type: project
  originSessionId: 421be5bf-160c-42b6-820e-911dcec5caa9
  modified: 2026-07-28T05:18:20.431Z
---

**V54 = V38 cal + `0xC62EA` 320→0 + a 5-bit `gp-0x6966` probe on `0x14A` byte4 bits 7:3.**
Flashed 2026-07-27, driven (route `1b`, 61.5 s parking lot), **fault-free** — `steerFaultTemporary` and
`steerFaultPermanent` both 0, `canValid` true in 5,711/5,713.

## ★ The probe fired — the piggyback channel is PROVEN

A/B against the V53 drive is a **single bit**, exactly the one the cave writes:

| route | build | `0x14A` byte4 | bits 7:3 | bits 2:0 |
|---|---|---|---|---|
| `1a` | V53 (no probe) | `0x07` × 5,994 (100%) | 0 | 7 |
| `1b` | **V54** | `0x0F` × 5,989 (100%) | **1** | 7 |

After two silent new-mailbox attempts (see [[v53-flashed-v54-authority-probe]]), **this is the kit's first
working firmware telemetry channel.** Use `0x14A` byte4 bits 7:3 for all future firmware telemetry; the
hook at `0x55C0E` sits immediately before the checksum call, and openpilot reads nothing in those bits.
The `+1` liveness bias did its job — a dead probe would have decoded as a plausible "low authority".

## ★★ What `gp-0x6966` actually is — the framing was wrong

It is **not** a speed-scheduled "steering authority" gain. It is the **soft-EME wind-up integrator's
magnitude**:

```
gp-0x3570 += (command − bound), clamped ±(cal 0xC61DC = 30720)   [anti-windup integrator]
gp-0x6966  = |gp-0x3570 >> 15| × (cal 0xC61DA = 1092) >> 10      [max (1092×30720)>>10 = 32760 ≈ Q15 1.0]
```

The bound is a 3-way gated MAX/MIN of corridor (driver-override), boost (angular rate), IIR (column
velocity). **No arm is vehicle road speed** — verified by hit-count sweep of `FUN_00042af8`.

**Why it reads 0 on the flashed build (byte-verified in `_v54_plain_image.bin`, not argued):**

```
boost LERP Y   stock: 0 / 1536 / 2048      V38 & V54: 5120 / 5120 / 5120
float twin     stock: 0.0 / 1.5 / 2.0      V54:       5.0 / 5.0 / 5.0
```

On **stock** `Y[0]=0`: at low angular rate the boost arm vanishes, the bound collapses, the integrator
winds — the V30 hard-hands-off-turn EME. On **V31+ (incl. V38/V54)** the boost arm is floored and ungated
by driver input, so the bound cannot collapse and `(command − bound)` stays negative. See
[[reference-accord-soft-eme-bound-arm-gating]].

⇒ **On-car: `wire = 1` in 5,989/5,989 frames** ⇒ `gp-0x6966` ∈ [0,127] = **0.39% of saturation**, zero
variation, *including 17% of requesting frames at openpilot's ±4096 rail*. Reaching the first LERP knee
needs `|gp-0x3570>>15| ≥ 3073` vs an observed **≤ 119**.

**This converts V31's fixpoint from "argued, with a residual margin caveat" into on-car evidence under
railed command.** That is the drive's real contribution.

🛑 **Do NOT re-drive at road speed to "see if authority moves."** It will not. Provoking it needs the
documented EME pattern (sustained hands-off hard turn) that V31 exists to prevent. A subagent argued
"3277 is easily reachable, documented on-car" — true of **stock/V30**, false of the flashed build. That
is the lineage trap: always scope a reachability claim to a build.

## The consequence: `0xC6AF0` is unblocked

Authority ≡ 0 sits in the table's **first flat segment** (X = 0/3277/3604/19661/32768,
Y = 32768/32768/0/0/0), so `Y = 32768` (unity) is selected in **100% of normal operation** — the
`FUN_0003a382` residual lane runs at **full output bound** always, including throughout the vibration.

⇒ **"keep-live" is a no-op; mute (`Y[0]`,`Y[1]` → 0) is the only meaningful edit**, and it is licensed.
Zeroing them does not disable a live protection (the derate is never invoked) and would be *more*
conservative in a hypothetical wind-up.

🛑 **GATE 2 is NOT closed.** The measurement proves the lane is **live**, not that it is the **culprit**.
Its damping-vs-anti-damping sign at 20 Hz is undetermined. Unblocked ≠ cleared to flash.

## Verified chain (Python byte reads, independent of Ghidra and of any subagent)

```
0x3a632  0x5fe4 0x969b   ld.hu -0x6966[gp], r11    <- the ONE command-path reader
0x3a636  0x7e25 0x7af0   movea 0x7af0, tp, r15     <- tp=0xBF000 -> 0xC6AF0, 4 bytes later
0x432c8  0x6f64 0x969a   st.h  r13, -0x6966[gp]    <- st.h => 16-bit; the probe's ld.hu width is correct
```

## Two record corrections

- **NOT a correction:** the V31 memory's boost floor of **4096 is correct for V31**. **V38 raised
  it to 5120** (float twin 5.0); the golden model already carries both. The car runs V38+, so 5120
  is the live value. Do not "fix" the V31 memory.
- That memory's residual-margin arithmetic (*"COMP ceiling 2560 `0xC67D8` + governed clamp 1024
  `0xC61B4` = 3584 vs 4096"*) **does not reconcile** — `0xC67D8` reads 512, `0xC61B4` reads 2048 in V54.
  Possibly prose addresses naming one element of a LERP table. **Re-derive before quoting.** Not blocking:
  V54 measured the margin directly.

**Process lesson:** the meaning of this measurement was partly predictable from
[[reference-accord-soft-eme-bound-arm-gating]], which already stated V31 makes authority never climb. The
"two analysis passes reached opposite conclusions" deadlock that motivated building V54 could have been
broken by reading it. Check memory before building the instrument.

See also [[accord-vibration-moves-with-speed-and-dies-at-rail]],
[[reference_accord_fun3a382-unfiltered-residual-lane]].
