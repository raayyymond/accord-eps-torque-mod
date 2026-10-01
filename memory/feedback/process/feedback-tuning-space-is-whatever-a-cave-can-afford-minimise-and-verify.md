---
name: feedback-tuning-space-is-whatever-a-cave-can-afford-minimise-and-verify
description: "Standing operator instruction 2026-09-30: the firmware tuning space is WHATEVER A CAVE CAN AFFORD — caves are in scope, minimised (fewest instructions, in-place edits first, one state word before two) and thoroughly verified (GATE 1/2, golden mirror, wire instrument before the dose, adversarial pass). Cal-only is a preference between equivalent loops, never a design constraint. A build is scored against its STATED goal: V294/V295 were designed to track angular acceleration, cannot (|L| <= 0.63 at any cal value), and FAILED. Recorded in CLAUDE.md and the firmware-iteration skill."
metadata:
  type: feedback
---

**The operator's words (2026-09-30):** *"Our tuning space is whatever we can afford in a cave. Caves are ok, but
need thorough verification and need to be minimized."* and *"V294 was designed to track angular acceleration.
If it doesn't do that, it failed. Same with V295."*

**Why:** two builds were named "acceleration tracking" and designed inside the cal space of a structure (one
operand, one filter, the setpoint sharing the integrator's input) whose loop gain on acceleration cannot exceed
0.63 at any value. The design panel's "ceiling" was a ceiling of the CAL SPACE, presented as if it were a ceiling
of the car. The operator rejects that framing: the structure is editable, so the ceiling is whatever a minimal,
verified cave can reach.

**How to apply:**
- Design the LOOP first, then find the smallest edit that gives it. If the stock structure cannot hold it, say
  so in the design report and design the cave; never search the cal space for a value that cannot exist.
- Score every build against its stated goal and record FAILED when it fails, whatever else it did well.
- Minimise: in-place operand/branch edit before a cave; one new state word before two; every cave instruction
  has a line naming the loop term it implements.
- Verify, nothing waived: GATE 1 RAM ownership · GATE 2 magnitude AND phase in every loop · byte-exact golden
  mirror · the wire instrument for every new state word before the dose · the adversarial pass with "do not
  flash" reachable · engage/disengage/bail init traced.
- The cave record is the brief: V24/V27/V48B bricked (pre-gate); V96/V112/V288/V289/V292 flew (post-gate);
  V291/V292 (loop opened above 10 Hz → 7 Hz re-armed), V289 (notch → 16 Hz pole took the margin), V283 (Ki on
  an operand holding the command → release lurch) are design constraints.

Related: [[accord-ki-on-acceleration-is-a-dc-rate-term-and-acceleration-feedback-is-virtual-inertia]],
[[accord-v294-flew-r71b-v295-trim-gain-x1852-built]], [[accord-lkas-pid-ki-integrates-the-command-and-taper-axis-is-driver-torque]].
