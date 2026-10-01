---
name: project-the-goal-2026-09-30-angle-loop-cave-tight-smooth-silent
description: "THE GOAL set 2026-09-30 (operator asked for a definitive goal statement): make the Accord EPS under openpilot steer tight, smooth and silent at every speed via a 1 kHz FIRMWARE ANGLE LOOP (EPS angle gp-0x6a00, mode-3 gated; speed-scheduled P, bounded I bleeding on driver torque) fed by an angle setpoint from a minimally modified StarPilot (stock angle controller + VSR map, EPS angle frame); the edit is the SMALLEST verified cave, scored only against the goal with measured criteria (dwell-then-jump <= V282, tracking 0.95-1.05, turn-hold >= 0.90, ring <= 0.5 %, F7 = 0, 20 Hz gain <= V295); not torque mode, not V294/V295 cal values, not an unfiltered rate loop. Order: tracer -> harness -> fork spec -> instrument -> cave -> mirror -> gates -> adversarial -> page -> one drive."
metadata:
  type: project
---

The full statement lives at the top of `docs/STATE.md`'s decision box (🎯 THE GOAL, 2026-09-30). Summary:

**End state:** no looseness (straights, low-speed turns), no snap/jerk (hard turns), no understeer (highway), no
ring/grind in 5–30 Hz, ever. **Architecture:** firmware inner loop on STEERING ANGLE at 1 kHz; angle setpoint
from StarPilot's stock angle controller + the variable steer-ratio map, in the EPS's own angle frame.
**Edit class:** the fewest instructions that give the loop (a cave), nothing waived in verification (GATE 1, GATE 2
magnitude+phase, golden mirror, wire instrument before the dose, adversarial pass with "do not flash" reachable).
**Scoring:** against this goal only; measured criteria above; the operator's words on feel. **Not:** V294/V295's
cal space, torque mode, a rate loop with V282's 20 Hz tail, a fork rewrite.

**Why:** V294/V295 were named for a quantity their structure could not track and were scored as if the cal space
were the car; the operator ruled the tuning space is whatever a verified cave can afford, and asked for a
definitive goal. The 2026-09-13 design note already named angle as the right inner-loop quantity.

**How to apply:** open every session from this goal; the first step is the tracer on gp-0x6a00 (rate, units,
mode-3 gate, speed variable, a RAM home for the I state). Related: [[feedback-tuning-space-is-whatever-a-cave-can-afford-minimise-and-verify]],
[[accord-ki-on-acceleration-is-a-dc-rate-term-and-acceleration-feedback-is-virtual-inertia]].
