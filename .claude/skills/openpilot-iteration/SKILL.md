---
name: openpilot-iteration
description: How the operator wants the openpilot/StarPilot lateral control fork developed — the architecture he's chosen, what he means by a good solution, what not to break, and how to run the work. Load before proposing, simulating, or shipping any fork-side control change.
---

# Working on the fork

## The architecture he's chosen

- The EPS firmware is a **pure torque map**. openpilot does the control.
- **Firmware changes are high-risk — keep them to an absolute minimum.**
- **Don't put the 1 kHz loop back in the EPS.** If we ever do, compare the setpoint to angular
  **velocity**, not acceleration.

## What a good solution means to him

- Eliminate **loose steering, understeer and oversteer**.
- **Elegant and efficient**, not just robust, accurate and performant.
- **Keep asking whether the changes we've already made are still necessary.** Lag we added is lag we own.
- **Fine control of the wheel is the point.** Small steering demands have to actually reach the road.

## Don't break what works

- **Don't delete a feature to fix a symptom — gate it.** He has overruled this twice.
- **Lane centering stays.** It's toggleable and it does a real job when the model sees both lines.
- **Don't pin something just to keep an instrument clean.** The car comes first.
- Any model we fit has to **account for lane centering being on**.

## Running the work

- **Sonnet for trivial tasks, Opus for nuanced ones. Never Fable.**
- **Tie subagent work together.** Feedback that arrives late still has to reach work already in flight.
- StarPilot → `Dom`. This kit → `main`.
- **Hand over the file he can actually use** — the encoded config, not just the readable copy.
- **Say what you measured and what you're guessing.** Mark it.
- **Keep it short.** Reports, docs, commit messages, this file.
