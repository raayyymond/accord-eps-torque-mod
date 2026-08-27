---
name: accord-vibration-requires-lkas-engaged
description: "The 21.09 Hz Q~14 Accord steering resonance exists only while openpilot is commanding lateral — 9,200x less 21 Hz power with LKAS disengaged under matched conditions. Makes it a closed-loop LKAS instability, so an openpilot-side notch is a zero-risk experiment."
metadata: 
  node_type: memory
  type: project
  originSessionId: e83f5d10-c983-4d72-862d-9c17c6f2e166
  modified: 2026-07-26T21:57:30.306Z
---

Route 13 (2026-07-26, deliberate parking-lot reproduction, FOURFRAME build = V38 torque behaviour).
Matched test on raw CAN 399 torque — hands-OFF, moving (`vEgo > 0.3 m/s`), same Nfft and speed gate,
`carControl.latActive` on vs off:

- OP steering: peak **21.09 Hz**, P(21 Hz) = 7.03e7 (K=25, 23.3 s)
- OP off: peak 2.34 Hz, P(21 Hz) = **7.62e3** (K=18, 16.8 s)

**9,200x** less 21 Hz power disengaged — and the disengaged pool carries **6x MORE** low-frequency
energy, so it is not an excitation-level artifact.

**Why it matters:** this contradicts the project's standing "self-excited, command-independent
base-assist limit cycle" model and puts openpilot inside the loop. ⇒ **an openpilot-side 21 Hz notch /
lateral rolloff is a zero-brick-risk experiment that should be run before any further firmware `.rwd`**
— three code caves have already bricked this ECU, and the last two firmware candidates were nulls.

**How to apply:** when analysing this vibration, ALWAYS split hands-on vs hands-off (`steeringPressed`)
— mixed data peaks at a spurious **7.42 Hz** and buries the real mode. The "steeringPressed is circular
because it derives from the same torque channel" objection is testable and **false** (driver torque
averages 2166 hands-on vs 328 hands-off). And check your disengaged comparison cell is not a **parked**
car — the raw `latOFF & handsOFF` cell has median vEgo 0.00 m/s.

Related: [[accord-low-speed-lockout-window-c62ea]],
[[accord-can-tx-100hz-base-tick-and-gateway]].
