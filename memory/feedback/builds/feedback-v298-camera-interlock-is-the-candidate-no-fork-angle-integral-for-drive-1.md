---
name: feedback-v298-camera-interlock-is-the-candidate-no-fork-angle-integral-for-drive-1
description: "Operator rulings 2026-10-01 on the angle loop: V298 (C3-rev2-P + the gp-0x6803 == 2 camera interlock) is the flight candidate because the stock camera's 0xE4 on a relay close would be read as a ±70° angle setpoint and that hazard must be structurally impossible, not procedurally avoided (conditional: clean adversarial pass; the 6803==2 arm's hand-fade table 0xCBAE4 matched to the stock arm as cal; fork sends byte-2 bits 3:2 = 2). No fork angle integral for drive 1 — a second integrator in cascade rings at 0.3–0.5 Hz unless τ_o ≥ 6 s, where it is too slow to help; revisit after the drive from measured residual error and breakaway friction per band."
metadata:
  type: feedback
---

**Why:** the camera hazard is low-probability, high-consequence at speed; the interlock closes it in firmware at the cost of
Honda's direction-2 engage arm (0.10 s ramp-in, 0.5 s ramp-out, a harder hand fade unless re-written as cal). The fork
integral's benefit (dead-zone breaking) disappears at the τ that makes it safe.

**How to apply:** build/verify V298 as the candidate; the drive-1 fork config uses stock LatControlAngle with no angle
integral and bits 3:2 = 2 in 0xE4 byte 2; size any low-speed friction term from drive 1's breakaway measurement.
Related: [[project-the-goal-2026-09-30-angle-loop-cave-tight-smooth-silent]], [[feedback-design-is-a-judge-panel-never-one-agent-one-solution]].
