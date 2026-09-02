---
name: accord-v276-mechanism-is-a-matter-of-degree
description: V276's x6 reference did NOT make the LKAS lane stop damping outright; frame-by-frame on the operator's log the lane still opposed the wheel in 0.57 of oscillation frames (0.94 at stock). The combined loop (EPS rate lane + openpilot's angle follower) went unstable between those. The crossover does NOT cap the oscillation's amplitude (V276's peaks overshot theirs 1.5-2x). K sets the damping FRACTION, not a threshold; K=2 restores 0.86.
metadata:
  type: project
---

# The V276 mechanism is a matter of DEGREE, not a threshold -- 2026-09-01 [EVIDENCE + BELIEF marked]

Frame-by-frame on route r2e (7 episodes, 87 half-cycle peaks), with the real command (index = |cmd|/16.2 via
`clamp(-4*cmd, +-15360)>>6`, capped 240 = the map's last knot), the real rate, the exact lag filter and the taper:

| K | osc: lane opposes wheel | normal engaged: lane opposes wheel | ceiling crossover |
|---|---|---|---|
| 1 stock | 0.94 | 0.80 | 22.3 deg/s |
| 1.5 | 0.90 | 0.75 | 33.4 |
| **2 (V278)** | **0.86** | **0.70** | **44.5** |
| 2.5 | 0.82 | 0.65 | 55.7 |
| 6 (V276) | 0.57 | 0.48 | 134 |

- **"The loop never damps" was WRONG** as stated in the first handoff. It damps LESS. [EVIDENCE]
- **The oscillation is of the COMBINED loop**: openpilot's command swings coherently (coh 1.00) but its desired
  path is flat (desired-lateral-accel swing 20x smaller than the error swing) -- it FOLLOWS the measured angle.
  Neither loop alone. [EVIDENCE from controlsState]
- **The crossover does not cap amplitude**: at the oscillation's own command the K=6 crossover is 36 deg/s, yet
  peaks ran 55-68 deg/s. No "residual settles at the crossover" prediction is licensed. [EVIDENCE]
- **The frequency (3.9 Hz) is mechanical**: firmware poles supply only 28-52 deg of the 180. [EVIDENCE]
- **Grip kills it at ~2500 raw driver torque -- where the override CLIFF begins (2240-2560)**, so the grip may act
  through the taper rather than mechanical damping; not separable on this drive. [EVIDENCE, weak: 7 episodes]
  => V277 (cliff softened, authority held to 3584) would have made the grip LESS effective. Unflown; good.
- The pre-registration's "command oscillates => outer loop => do not build" branch fires on a MEASUREMENT-driven
  signal and was rejected by both agents that ran it. A pre-reg can mis-specify its own verdict rule.

**How to apply:** size K by the damping FRACTION on the operator's own log, read the fraction back on the wire
with the comparator tap ([[accord-sign-e-alone-cannot-measure-damping]]), and expect a matter-of-degree
answer. Units: [[accord-feedback-operand-is-a-two-sample-sum-dc-30-89]].
