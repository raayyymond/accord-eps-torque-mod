---
name: accord-the-rate-loop-is-a-bang-bang-servo-p-rails-at-e-440
description: Honda's LKAS rate PID is effectively a bang-bang RATE SERVO, not a torque interface with a slope -- its P term rails at |E| = 440 operand counts (+-1.8 deg/s of rate error), so with the wheel still STOCK delivers its full 417 at a command of ~113 counts (<3% of scale) and at the operator's median command with the wheel moving it is railed NEGATIVE. To openpilot's angle PID the plant has looked like an INTEGRATOR (cmd -> rate -> angle). "stock gain / modded gain" as a static torque ratio has NO finite value at any real operating point.
metadata:
  type: reference
---

# The rate loop is a bang-bang servo: P rails at |E| = 440 -- 2026-09-02 [EVIDENCE, from the images]

`P = clamp(32*E*Kp >> 8, +-15360)` with Kp 248..696 (slot 7): P rails when |E| > 15360*256/(32*Kp) = 440 at Kp 248
(171 at 696). E is in operand counts; 440 operand = 14 wire = **1.8 deg/s** of rate error. Delivered torque at
fixed wheel rate (fb in 0x18F wire counts, + = wheel already moving with the push), slot 7, from the images:

```
 cmd  idx |  stock fb=0/39/327 | V112 fb=0/39/327   | V279 (any fb)
   53   3 |  169 -418 -418     | 1014 -2506 -2506   |   31
  113   6 |  353 -418 -418     | 2122 -2506 -2506   |   62
  140   8 |  417 -418 -418     | 2505 -2506 -2506   |   83
  354  21 |  417  228 -418     | 2505  1368 -2506   |  219
 3886 239 |  417  417 -418     | 2505  2505 -2506   | 2495
```
- Small-signal dT/dcmd at fixed fb is ZERO at every real operating point except inside the +-14-wire linear band.
- V112 is exactly 6x stock at every (cmd, fb). What the 1/6 openpilot multiplier actually did on V112 was cut the
  RATE openpilot asked for by ~6x (map slope 2 -> 0.016 deg/s per count) -- which is why authority felt low until
  V276 raised the reference.
- **Consequence:** an openpilot retune for a build that changes the loop's SHAPE (V279) cannot be a scale factor;
  it must come from the cmd -> ANGLE loop. See [[accord-starpilot-runs-the-angle-pid-kf-unscaled-no-friction]].
