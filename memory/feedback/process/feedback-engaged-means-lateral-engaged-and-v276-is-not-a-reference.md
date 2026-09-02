---
name: feedback-engaged-means-lateral-engaged-and-v276-is-not-a-reference
description: Operator, 2026-09-02 -- (1) "V276 carried x6 at every index for 73 s with no turn stutter" is NOT evidence: V276 oscillated constantly so he barely drove it laterally engaged; do not cite V276 as a reference for anything except the oscillation it produced. (2) CONFOUND: openpilot can run LONGITUDINAL control with lateral OFF. "Engaged" in every analysis must mean LATERAL engaged -- 0xE4 STEER_REQUEST and 0x18F STEER_CONTROL_ACTIVE (the bits the kit's decoders gate on), never carState.enabled / cruise state. State which flag a script used.
metadata:
  type: feedback
---

# "Engaged" means LATERAL engaged; V276 is not a reference build -- 2026-09-02

**What the operator said:** *"not sure why we are using V276 as a reference. It was a bad firmware which made LKAS engagement
unusable due to the constant oscillation ... stutter didn't appear because it was constantly oscillating and I didn't drive it
engaged much! Looks like we have a confound here: I can engage longitudinal control without activating lateral control on
openpilot. We need to make sure not to get confused by this moving forward."*

**Why:** the V280 handoff and page leaned on "V276 flew x6 at every index for 73 s, no turn stutter reported" to support raising
the map top. That 73 s is lateral-engaged time on a build he could not use; an absence of a symptom on a build that was not
driven in the regime is not evidence (the kit's own rule: an absence of a complaint is not a report of improvement).

**How to apply:**
- Never cite V276 as an on-car reference for a cell value, a knot, or "no symptom". It is evidence for ONE thing: the 3.9 Hz
  combined-loop oscillation at small commands.
- Every route statistic must gate on LATERAL engagement: `0xE4` byte 2 bit 7 (STEER_REQUEST) AND `0x18F` byte 4 bit 3
  (STEER_CONTROL_ACTIVE) -- what `decode_v278r3_torque_tap.py`, `highangle_stutter.py`, `read_v278r3_route.py` use. A script
  that gates on `carState.enabled`, cruise state or `controlsState.active` alone is counting longitudinal-only time as engaged.
  Say which flag was used in every report.
- Comparison routes ("stock r97", "V112 r22") must be checked the same way before "did it exist before" is answered.
