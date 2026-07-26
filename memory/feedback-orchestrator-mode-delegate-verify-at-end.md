---
name: feedback-orchestrator-mode-delegate-verify-at-end
description: Operator wants the lead to run as a pure orchestrator — subagents do all the digging; lead only touches Ghidra/fine-detail to finalize or arbitrate.
metadata:
  type: feedback
---

For substantive sessions the operator wants the lead agent to act as an **orchestrator +
synthesis/reasoner**, delegating to subagents "as much as possible," and to **only look into Ghidra and
the fine details when confirming the final picture or resolving a dispute between subagent findings.**

**Why:** the operator is paying for lead-model tokens/time; hands-on tracing at the lead level is the
expensive, slow path when a `firmware-codepath-tracer` / `general-purpose-sonnet` can do it. The lead's
value is in framing the questions, splitting the work, reconciling conflicting evidence, and keeping the
belief-vs-evidence calibration — not in decoding opcodes.

**How to apply:** default to spawning subagents for enumeration, disassembly, xref walking, string
sweeps, decode, and candidate hunts. Prime each with `gp=0xFEDF8000`, `tp=0xBF000`, GhidraMCP-only, the
target program name, and the relevant golden-model facts (see
[[feedback-delegate-firmware-tracing-to-subagents]] and [[feedback-ghidra-mcp-only-no-rizin]]). Step in
with your own GhidraMCP calls **only** to (a) verify the assembled final answer before delivering, or
(b) break a tie when two subagents disagree. This strengthens the pre-existing "delegate RE to subagents"
rule into "delegate by default, verify at the end." Keep [[feedback_rigorous_validation]] — the
end-of-session verification is still mandatory; it just happens at the synthesis step, done by the lead.
