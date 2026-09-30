# Operator's report — V294 drive, route `75604b0a432fdc89_00000071--a7b8ba5d9d` (recorded 2026-09-30)

Verbatim, the operator's words. He scores symptoms; the kit scores bands.

- "No grinding or stuttering!"
- "Jerky on hard turns at medium speed"
- "Loose on straights and turns at low speed."
- "Loose/understeer at highway turns."

Scope for this session, verbatim: "My general feeling about the current StarPilot fork state is that we have a
lot of unnecessary bloat from our current work. But for this session, I just want to focus on the firmware
internal PID loop tuning alone."

Session goal, verbatim: "Adjust the firmware LKAS PID loop values to better track desired steering angular
acceleration (comma LKAS command output vs second derivative of steering angle sensor output)."

Setup he describes: "a near end-game setup: acceleration LKAS P(ID+F) tracking and minimal StarPilot edits
(variable steer ratio, default lateral logic but with custom tuning values)."

Consequences for the session (orchestrator's reading, not his words):
- No fork change is in scope. The firmware values are the only lever; the fork bloat is a later session.
- The three complaints map onto speed/demand regimes the design must be scored in separately:
  hard turns at medium speed (jerk), low speed straights + turns (loose), highway turns (loose / understeer).
- "No grinding or stuttering" is the property a stronger loop must not lose: any design that adds 5–30 Hz
  torque content or re-creates a 7 Hz / 20 Hz object is a regression on the one symptom he has called absent.
