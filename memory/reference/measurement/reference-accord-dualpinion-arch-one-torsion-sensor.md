---
name: reference-accord-dualpinion-arch-one-torsion-sensor
description: 2020 Accord EPS is a DUAL-PINION rack system (assist motor on a second, off-axis rack pinion). Sensor A/B are the MAIN/SUB Hall channels of ONE torsion-bar sensor, not two separate sensors. The 21 Hz mode is a rack-coupled driveline resonance.
metadata:
  type: reference
---

# 2020 Accord EPS hardware architecture (EPSArch web research, 2026-07-21)

- **Dual-pinion variable-ratio EPS.** The assist motor drives a **second pinion** on the rack, mounted
  **off the steering axis** deliberately for vibration isolation (Showa / Hitachi-Astemo; Honda 40%
  owner). Well-sourced (Honda spec docs + Showa DPA-EPS product docs).
- **Sensor A and Sensor B = the MAIN and SUB Hall channels of ONE torsion-bar torque sensor** at the
  column input — NOT two separate physical sensors. Confirmed by Honda DTC **C1420 "Main/Sub Torque
  Sensor Incorrect Correlation"** (a correlation fault only makes sense for two channels of one sensor).
  This corroborates the firmware fact that `gp-0x4f60` (Sensor-B) is driver column torque, upstream of
  where the motor injects at the rack. Sensor A (`gp-0x6a5e`) is never on CAN.
- **Motor position = resolver** (consistent with the firmware's sin/cos ADC + atan2 decode of
  `gp-0x6ac0` = motor electrical-angle rate).
- **The ~21.4 Hz, Q≈13.6 mode is a rack-coupled driveline resonance** (motor inertia + assist-pinion +
  rack + steering-pinion + torsion bar + column), sensed at the torsion bar, felt at the wheel. Because
  the motor is mechanically isolated off-axis, the felt mode couples back through the RACK, not a direct
  motor→column path — but the torsion-bar/column end is exactly where driver grip (and the firmware
  motor-rate damper) adds damping. Consistent with "cured by rotating the wheel."
- **openpilot:** "Honda Bosch A connector" ("Bosch" = ADAS camera/radar generation, NOT the EPS
  supplier), `minSteerSpeed=0`, `minEnableSpeed=3 mph`. The 3-4 mph vibration turn-on = this engage
  threshold, not a firmware speed gate — see [[reference-accord-no-vehicle-speed-input-5mph-is-plant]].

No public Accord-specific ~20 Hz resonance TSB/spec was found; generic EPS torsion-bar/column/motor
modes in this band are a known industry NVH concern (class match, not a confirmed Accord number).
