---
name: accord-governor-zeroing-mechanisms
description: Accord 2020 EPS — confirmed mechanisms by which the combined motor-assist can transiently collapse to zero (no DTC), traced through mixer/distribute/governor cluster. Verified 2026-05-27.
metadata:
  type: reference
---

## Primary zeroing path: governor limit drop (Mechanism A)

`FUN_0007b022` is the SOLE WRITER of `gp-0x4f64` (runtime governor limit, nominal 4762 at highway speed).

It computes: `gp-0x4f64 = round(gp+0x184 * 1024)` where `gp+0x184` is a speed float.
- At low/zero vehicle speed, gp+0x184 → 0, so gp-0x4f64 → 0.
- m_motor_torque_governor then clamps its input gp-0x6b94 to ±0 → gp-0x6ace = 0.
- m_post_governor_torque_comp_add writes gp-0x6acc ≈ 0 (small correction term only).
- s_motor_torque_rate_shaper sees 0 input → zero assist output.
- **This zeroes ALL assist through the pipeline, including base power-steering assist, not just LKAS.**

FUN_0007b022 has 3 write branches, gated by `gp-0x4e5a` (mode byte, written by FUN_00071272 and FUN_00075718). All three branches are speed-proportional.

Lockstep shadow `gp-0x448a` is written atomically with `gp-0x4f64`. Shadow mismatch → `FUN_0006b9ee` fires and gp-0x4f64 is NOT updated (frozen, not zeroed).

## Secondary mechanism: rate-limiter hold accumulator (Mechanism C)

Inside m_motor_torque_governor, when `gp-0x67fa == 4`, `gp-0x138a` (hold accumulator) is substituted for the governed output if magnitude(gp-0x138a) < magnitude(governed). gp-0x138a is initialized to 0 on first run (`gp-0x5000` first-run flag). This produces designed ramp-up behavior, not a fault, but explains why after an override clear, the output ramps from 0 rather than stepping.

## LKAS contribution zero at aggregator (Mechanism E, low severity)

m_motor_torque_demand_aggregator zeroes the LKAS lane if `gp-0x6b4c` is outside ±0x2800:
```c
iVar20 = (int)*(short *)(gp-0x6b4c) * (uint)((gp-0x6b4c + 0x2800U) < 0x5001);
```
Normal LKAS values are well within ±10240, so this clamp doesn't fire under normal conditions.

## Chain of variables (in order)

gp-0x6b4c (LKAS mixer output) → m_motor_torque_demand_aggregator → gp-0x6b94 (clamp ±0x2800, lockstep gp-0x4ce0) → m_motor_torque_governor (clamp by gp-0x4f64 * speed_scale) → gp-0x6ace (lockstep gp-0x4cca) → m_post_governor_torque_comp_add → gp-0x6acc → s_motor_torque_rate_shaper → gp-0x6b98 → FOC

## Open questions

- FUN_0006b9fa (safety fault): does it zero or freeze output vars? (Mechanism B severity TBD)
- FUN_00038148 reads gp-0x6b4c — role unknown
- s_motor_torque_rate_shaper deadband/slew in Accord firmware not yet verified
- gp+0x184 identity as vehicle speed CAN signal needs confirmation

## Related memories

[[accord-governor-all-branches]] — prior Civic governor branch analysis (different firmware, similar structure)
[[accord-mixer-lkas-source-chain]] — mixer source for gp-0x6b4c
