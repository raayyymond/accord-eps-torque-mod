---
name: reference-accord-openpilot-two-hard-rails
description: openpilot holds TWO hard rails and they are the felt "throttle" -- amplitude 4096, matched EXACTLY to the firmware intake clamp (4096 x 4 = 0x4000), and a slew cap of 123 counts/frame. 16.07% of engaged time sits against one or the other, and raising STEER_MAX alone buys ZERO.
metadata:
  type: reference
---

# ★★★ openpilot has TWO hard rails, and they are the "throttle" the operator feels

⚠ **Provenance:** measured and traced by sibling agents this session and relayed by the orchestrator;
recorded here as the session's finding. The parts I re-derived myself are marked. **The `4096 × 4 =
0x4000` identity is arithmetic and checks out; the on-car duty figures I did not reproduce.**

## Rail 1 — AMPLITUDE, and it is exactly matched to the firmware
openpilot's `STEER_MAX = 4096`. The firmware's intake clamp is
**`FUN_00052676` = `clamp(req × -4, ±0x4000)`** [orchestrator-verified in Ghidra].

> `4096 × 4 = 16384 = 0x4000` — **the request rail and the intake clamp are the same number.**

🛑 **⇒ THERE IS ZERO UPSTREAM HEADROOM. Raising `STEER_MAX` alone buys NOTHING** — every extra count is
removed by the intake clamp on the next instruction. Any amplitude work must move **both**, and the
firmware side is the binding one.
⊕ This is the cleanest statement yet of why the LKAS lane feels throttled, and it supersedes reasoning
that treated `STEER_MAX` as a free comma-side knob. It does **not** license a comma-side edit — see
[[feedback-no-openpilot-side-modifications]]; openpilot stays a measurement instrument.

## Rail 2 — SLEW, and it dominates at highway speed
A slew cap of **123 counts/frame**, i.e. **`0.03 × STEER_MAX`**, with **zero frames exceeding it**.
✅ This **confirms exactly** the `(0.03*STEER_MAX*4*gain)>>15` term already carried in
`analysis-2020accord/model/eps_lkas_chain_model.py` (`openpilot_command_slew_invariance`) — a modelled term is
now a **measured** one.

## The combined exposure
**16.07 % of engaged time sits against one rail or the other**, the slew rail dominating at highway
speed and the amplitude rail at low speed.

## Why it matters for the damper work
The rails are **upstream** of everything the V44→V75 damper line touches. They bound how much LKAS
*command* can exist, not how much damping opposes it — so a damper result is not confounded by them, but
a "the command is too small" hypothesis must be priced against **both** rails, not just `STEER_MAX`.

⚠ **[OPEN]** I did not independently reproduce the 123 counts/frame figure, the 16.07 % duty, or the
"zero frames exceeding" claim. Anyone leaning on them for a build decision should re-derive them —
[[feedback_verify_subagent_claims]].

Related: [[reference_accord_lkas_window_ceiling]] · [[feedback-no-openpilot-side-modifications]] · [[accord-v74-flew-damper-is-in-force]]
