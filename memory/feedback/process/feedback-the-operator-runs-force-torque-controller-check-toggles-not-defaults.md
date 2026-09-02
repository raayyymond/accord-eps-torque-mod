---
name: feedback-the-operator-runs-force-torque-controller-check-toggles-not-defaults
description: The operator's StarPilot has force_torque_controller ENABLED -- the car runs LatControlTorque, not the Accord's default LatControlPID. An agent read the default controller selection in the source and concluded "angle PID, no friction term", and a whole tune derivation shipped on it before the operator corrected it the same day. RULE: a claim about which controller/tune/toggle the operator's car runs must come from the OPERATOR'S CONFIGURATION (his toggles, his params, his words), never from the source's default path.
metadata:
  type: feedback
---

# The operator runs `force_torque_controller` -- check HIS toggles, not the code's defaults (2026-09-02)

**What happened:** `tune279` traced StarPilot's controller selection (`controlsd.py` picks `LatControlPID` when
`lateralTuning.which() == 'pid'`, torque only if `force_torque_controller`/`nnff` are set) and reported the DEFAULT.
The operator: *"Pretty sure StarPilot is doing torque controller this entire time actually. I explicitly have force
torque controller enabled."* The derivation (Kp 0.33 = 16.7 dB, "no friction term") was void, and the "openpilot
friction relay" attribution I had withdrawn on that basis was actually RIGHT -- the torque controller HAS one.

**Why it matters:** the torque controller's structure (feedforward on lateral accel via LAT_ACCEL_FACTOR, PID on
lateral-accel error, FRICTION x sign(error) -- a relay) is a different loop from the angle PID, with different
multipliers and a relay nonlinearity that survives V279's removal of the EPS's own relay.

**How to apply:** before deriving any comma-side number, ASK or READ the operator's actual toggle state; a source
tree tells you what CAN run, not what DOES. Mark any controller identity that came from the default path as BELIEF
until the operator confirms it. See [[accord-the-rate-loop-is-a-bang-bang-servo-p-rails-at-e-440]].
