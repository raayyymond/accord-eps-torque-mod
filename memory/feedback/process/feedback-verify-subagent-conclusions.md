---
name: feedback-verify-subagent-conclusions
description: In orchestrator mode, independently double-check load-bearing subagent conclusions before acting or relaying — never blindly trust.
metadata:
  type: feedback
---

When running as an orchestrator, the lead must **independently double-check the load-bearing subagent
conclusions** — not relay them as established fact. The operator said this twice in one session
(2026-07-23/24) and asked never to have to repeat it.

**Why:** subagents can be confidently wrong, and this domain bricks an ECU when a confident-wrong claim
is trusted. The whole reason the lead orchestrates instead of just fanning out is to be the calibration
layer (belief vs evidence). Relaying an unverified subagent verdict throws that away.

**How to apply:** for the claim(s) the decision actually rests on, run a *minimal* independent
confirmation yourself — a tight script that prints only summary numbers, a paper decode of an
instruction encoding, a math-identity check — enough to confirm the crux without re-flooding context.
This is the "(b) verify final outputs + justification" carve-out to the orchestrator context-hygiene
rule: delegate the bulk, personally confirm the crux. Verify even in the SAFE direction (a
"don't-flash" / "no" still deserves confirmation so the block itself is sound). Ties to
[[feedback-orchestrator-mode-delegate-verify-at-end]] and [[feedback-delegate-firmware-tracing-to-subagents]].

This restates and extends the older [[feedback_verify_subagent_claims]] (2026-05-30: sub-agents were
confidently wrong twice, caught by direct reads) — same rule, now with the orchestrator-mode framing
(minimal confirmatory check, don't re-flood context). The operator re-emphasized it 2026-07-24.
