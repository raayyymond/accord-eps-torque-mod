---
name: feedback-no-openpilot-side-modifications
description: "Standing operator instruction 2026-07-28 -- do NOT propose openpilot/fork-side modifications as fixes. Retires the long-running 'openpilot 21 Hz notch' recommendation. openpilot stays in scope as a measurement instrument only."
metadata:
  node_type: memory
  type: feedback
---

**Operator, 2026-07-28: "I do not want openpilot side modifications."**

Do not propose, build, or recommend fork-side changes as a fix -- no notch filters, no low-pass, no
`STEER_DELTA` / rate-limit retuning, no `steerActuatorDelay` changes, no lateral-controller edits. This
**retires the "openpilot-side 21 Hz notch"** that sat at #1 in `docs/STATE.md` across several handoffs.

**Why:** the operator wants the fix in the EPS firmware, where the defect is. A fork-side workaround masks
the symptom on one vehicle/software combination and does not advance the reverse engineering.

**How to apply:** when a fix candidate is fork-side, drop it and find the firmware-side lever instead.
openpilot remains fully in scope as a *measurement instrument* -- rlogs, CAN decode, correlation -- just
not as a place to change behaviour. Re-check `docs/STATE.md`'s next-steps list whenever a fork-side item
creeps back in.
