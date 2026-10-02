---
name: feedback-no-fork-override-in-the-angle-interface-rely-on-the-eps-fade
description: "RULING 2026-10-02: REMOVE the fork-side driver override (O1: setpoint := wheel when |bar| > 600) from the Accord angle interface — 'we should just rely on the built-in override from the EPS'; the EPS hand fade (stock Honda record, lane x0.30 at ~2289 counts) + the firmware's integral freeze above Honda's 1200-count hands-on level are the override; the fork's error clip bounds the stored error (17 deg at 3 m/s .. 4.5 deg at 27 m/s) so release returns to the path at the loop's own rate; no fork lead/debounce/takeover ramp either"
metadata:
  type: feedback
---

**Ruling (operator, 2026-10-02):** *"We should remove the fork override for our angle interface for my car."*
Earlier the same day he had asked why a fork override exists at all ("we should just rely on the built-in
override from the EPS") — it had been added with the angle interface on 2026-10-01 (V298's fork, O1 at 600/500 wire
counts with a 0.06 s lead) and route 79 showed it tripping on the hands-off reaction twist 345 times.

**Why:** fork-side simplicity and stock-openpilot behaviour for angle-steered cars — the car's EPS handles the hand.
The V299 firmware already moves the integral freeze to Honda's hands-on level (1229 = 1200 raw) and bounds the
centre-ward integral, which is what made a fork override unnecessary for the release lurch.

**Consequences, stated to the operator (BELIEF until drive 2):** with a firm hand the lane keeps a faded pull toward
the path, ≤ ~20 % of the rail at low speed and ~5 % at highway (clip × stiffness × the 0.30 fade); on release the
wheel returns to the path from at most the clip distance at the loop's own 0.5–1 s rate, no integral lurch.

**How to apply:** the V299 fork update carries NO override state: no O1 gate/lead/debounce/takeover ramp; the limiter
restarts from the wheel only at the latActive rising edge; the error clip is the only bound between setpoint and
hand; the bar fix and the cap/clip params stay. Any future override logic is a design question for the operator.
Related: [[feedback-goal-criterion-1-6-3hz-replaced-by-stutter-readouts]],
[[accord-v298-flew-route79-loop-live-freeze-and-o1-fire-on-reaction-twist]].
