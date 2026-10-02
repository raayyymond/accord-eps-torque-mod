---
name: feedback-angle-interface-fork-code-authorised-on-raayyymond-starpilot-dom
description: "Operator instruction 2026-10-01: 'Develop the necessary StarPilot-side changes on the Dom branch on my fork' — the angle-setpoint interface for V298 is implemented as CODE in the operator's fork checkout C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot (branch Dom, remote origin git@github.com:raayyymond/StarPilot.git; opendbc vendored in-tree under opendbc_repo/, not a submodule), committed on Dom locally, NEVER pushed by an agent. The upstream checkout openpilots/StarPilot (firestar5683, branch Dom) stays read-only. All other fork-side experiments remain toggle configs."
metadata:
  type: feedback
---

**Why:** the angle interface cannot be expressed with existing params (steerControlType gate on fwVersion A16A, byte-2 bits
3:2 = 2 every frame, measured angle while inactive, packing the field when inactive, the steer-ratio fixed point, the mode-3
fault). Spec: `docs/specs/design/SPEC-angle-setpoint-interface-2026-09-30.md` §5 + the V298 addendum.
**How to apply:** code on that checkout's Dom only, surgical, invariants I1–I8 tested (torque path byte-identical when the
param is false); the push is the operator's.
