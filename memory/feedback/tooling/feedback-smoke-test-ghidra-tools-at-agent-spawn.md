---
name: feedback-smoke-test-ghidra-tools-at-agent-spawn
description: "Dynamic GhidraMCP tool registration is scoped to the agent session at spawn time; check_tools reports \"callable\" while direct calls error, so every agent must smoke-test get_current_program_info first."
metadata:
  node_type: memory
  type: feedback
---

🛑 **DYNAMIC GHIDRA TOOL REGISTRATION IS SCOPED TO THE AGENT SESSION AT SPAWN TIME.**

**What happened, 2026-08-09:** three firmware tracers were **silently blind for an entire session**.
`mcp__ghidra__check_tools` reported the tools as **"callable"**, while direct calls to them **errored**.
The agents did not notice, and their reports read as ordinary nulls rather than as tool failures.

**Why it is dangerous:** a blind tracer produces **exactly the output shape of a genuine negative** —
"no hits", "no readers", "not found". In this kit a null is routinely load-bearing (RULE 11 monitor
searches, writer censuses, mode-record sweeps), so a silent tool failure converts directly into a wrong
decision-bearing claim.

**How to apply — put this in every subagent brief that touches firmware:**
1. **The FIRST call of the session is `mcp__ghidra__get_current_program_info`.** If it errors, stop and
   report a tool failure; do not proceed and do not fall back to another disassembler
   (GhidraMCP is the only one — [[feedback-ghidra-mcp-only-no-rizin]]).
2. **Do not trust `check_tools`.** It reported success against tools that did not work.
3. **Confirm every load-bearing null with a raw Python little-endian byte scan** — the standing second
   method — which is unaffected by MCP registration entirely.

Related: [[feedback-ghidra-mcp-only-no-rizin]], [[feedback-stale-ghidra-import-defeats-hash-check]],
[[feedback-delegate-firmware-tracing-to-subagents]],
[[feedback-a-falsifier-only-fires-if-it-could-have-fired]].
