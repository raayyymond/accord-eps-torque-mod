---
name: reference_accord_gp6dac_producer_closed_driver_torque_not_relay
description: Closes the previously-unresolved gp-0x6dac producer (flagged OPEN in reference-accord-fun43e44-no-assist-chain-float-twin.md). gp-0x6dac is a driver hand-torque-sensor redundancy/consistency-vote byproduct, clamped to +/-10.0, with exactly one writer and one reader confirmed by both search_instructions and a raw whole-image byte scan. Structurally unrelated to gp-0x6bd0/the LKAS-damper chain.
metadata:
  type: reference
---

Built 2026-08-06, V75 incident follow-up. Program: stock `code.bin`.

## Full chain [EVIDENCE]

```
gp-0x6dac  <-writer- FUN_00042adc (0x42adc-0x42af7)  <-sole caller- FUN_00027b0a  <-sole caller- FUN_0002214a (1 kHz task)
gp-0x6dac  -reader-> FUN_00043e44 @0x4487a (Monitor 2's weight-32 fVar23 construction, see
           reference_accord_monitor1_monitor2_full_accumulator_mechanics_v75.md)
```

**Exactly 1 writer, 1 reader** — confirmed by BOTH `search_instructions` (183,429/~185,693 instructions
analyzed, operand `-0x6dac`) AND an independent raw whole-1MB-image byte scan (PowerShell) for the two
exact 4-byte LE instruction patterns (`64 37 55 92` write @0x42af2, `24 47 55 92` read @0x4487a) —
zero additional hits either way. This is a genuinely closed cell, not a tool undercount.

`FUN_00042adc(param_1)`: `if (param_1 outside ±10.0) param_1 = 0x7f7fffff (FLT_MAX sentinel); gp-0x6dac
= param_1;`. The caller (`FUN_00027b0a`) already clamps its own value to ±10.0 before the call, so this
inner clamp/sentinel branch is effectively defensive/redundant, not normally reachable.

## `FUN_00027b0a` — a torque-sensor redundancy/consistency-vote subsystem, NOT the LKAS chain [EVIDENCE, structural]

~800-line decompile. Sums/votes over what reads as dual/triple-redundant driver hand-torque-sensor
channels: 5-iteration loops over arrays at `gp-0x61e8` through `gp-0x6338`, per-channel status-code
branches (values 1-7), many `FUN_0004613e` fault-report calls (codes `0x3cfb`-`0x3d04`, `0x4157`,
`0x4158`, `0x3ce6`-`0x3ced` — a distinct, self-contained fault-code range from the hard-shutdown
monitors). **Does not reference `gp-0x6bd0`, `gp-0x6ac0`, `gp-0x6abe`, or any cell recognized from the
LKAS/aggregator/governor chain** (checked structurally over the whole function; not an exhaustive
line-by-line audit of all ~800 lines — residual uncertainty flagged).

The value passed to `FUN_00042adc` is `gp-0x3d58`, itself `driver_torque_channel_B/1024 +
sum_of_driver_torque_channel_A_samples` (already clamped ±10.0 by the caller) — a driver hand-torque
consensus quantity, physically unrelated to the commanded/delivered LKAS motor torque.

## Consequence for Monitor 2's weight-32 flag

`fVar23 = clamp( min(governor_float(gp-0x4f64), gp-0x6b04_float + gp-0x6dac), ±governor ), clamped
±8.0` — one of its three additive terms (`gp-0x6dac`) is now confirmed structurally disconnected from
`gp-0x6bd0`/the relay. **The relay cannot reach `fVar23` through `gp-0x6dac`.** The remaining open
question is whether it reaches `fVar23` through `gp-0x6b04` (the pre-feed-forward/pre-clamp shaper
snapshot that `FUN_00042af8` also uses to produce `gp-0x6b98`) diverging from `gp-0x6b98` by more than
±5/1024 counts when the governor or final ±8192 clamp binds during a fast transient — this was framed
but NOT numerically closed this session; needs either telemetry of aggregate-command headroom-to-clamp
during the incident, or `gp-0x6afe` (feed-forward)'s producer and typical magnitude.

## Related
[[reference_accord_monitor1_monitor2_full_accumulator_mechanics_v75]] — the full Monitor 1/Monitor 2
mechanics this closes one input for. [[reference-accord-fun43e44-no-assist-chain-float-twin]] — where
`gp-0x6dac` was originally flagged OPEN.
