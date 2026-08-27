---
name: reference-accord-no-vehicle-speed-input-5mph-is-plant
description: There is NO vehicle-speed input anywhere in the LKAS command path or the base-assist feedback loop. The only rate-adaptive tables are keyed on MOTOR rate (gp-0x6ac0), not road speed. The ~5 mph vibration peak is openpilot minEnableSpeed=3 + plant physics, NOT a firmware speed gate.
metadata:
  type: reference
---

# No vehicle-speed lever exists; "5 mph" is not a firmware knob (SpeedPath + RlogMiner, 2026-07-21)

Retires the "speed-scheduled assist gain peaks at 5 mph" theory at the firmware level.

- **No vehicle/wheel-speed variable feeds the command chain.** All 9 aggregator lanes (`FUN_0003aa2c`
  → `gp-0x6b94`) decompiled and checked, including the boost curve's 4 previously-undumped tables. Every
  gain that varies is keyed on **driver-torque magnitude** or **motor/resolver electrical-angle rate**
  (`gp-0x6ac0`), or is a flat per-mode constant. **None reads road speed.** Honda's "most assist at
  parking speed" character falls out of *motor-rate* adaptation, not a speed table.
- The EPS *does* ingest wheel speed (CAN 0x1D0 from VSA, DTC names `KFC_WHEEL_SPEED`/`KFC_WHEELSPD_PLAUSI`)
  but only for a wheel-speed-vs-rack-position DTC plausibility check — structurally separate from torque
  arbitration, not in the command path. Live decoder/scaling never located (string trail dead-ends at
  the DTC-name table).
- **`STEER_STATUS=3` ("LOW_SPEED_LOCKOUT" in the DBC) is NOT speed-gated** — it is a fallback when the
  assist substate `gp-0x67fe` isn't "engaged" (==2). Below openpilot's `minEnableSpeed=3 mph` OP can't
  engage → `gp-0x67fe` never reaches engaged → STATUS falls to 3. Downstream artifact of OP behavior,
  not a firmware speed comparison.
- **Empirical (RlogMiner, route b9, the only post-V38 route):** vibration band power near noise floor
  <2 mph, turns on sharply at 3-4 mph (= the engage threshold), **10-25× elevated across 3-10 mph**
  (peak 19-22 Hz), a real **dip at 10-12 mph**, moderate at highway. So ~5 mph is where **excitation**
  (assist demand highest + road noise lowest at low speed) peaks — **plant physics, not a cal.**

Consequence: a vibration fix cannot be speed-conditional. Attack loop gain or damping instead. See
[[reference-accord-damper-two-deadzones-factorC-factorE]] and [[reference-accord-dualpinion-arch-one-torsion-sensor]].
