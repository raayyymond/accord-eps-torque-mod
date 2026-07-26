---
name: feedback-use-sendmessage-not-plain-text
description: "When running as a teammate agent, findings MUST be delivered via the SendMessage tool — plain-text responses are invisible to the lead. Cost three exchanges of duplicated work on the low-speed-lockout trace."
metadata:
  type: feedback
---

**When running as an agent in a team, deliver every report with the `SendMessage` tool
(`to: "team-lead"`). Plain text output is NOT visible to teammates.**

**Why:** on the 2026-07-24 low-speed-lockout trace I completed the full `gp-0x6807` writer table,
the substate map, and the DTC eligibility results, then wrote them as ordinary assistant responses —
three times. The lead saw nothing, reported me "idle without sending a report", and independently
re-derived the DTC eligibility and the RX-table mapping that I already had. Pure duplicated effort,
plus the lead nearly finalised a handoff missing the findings.

**How to apply:**
- The tool schema is deferred: `ToolSearch("select:SendMessage")` first, then call it.
- Send the substantive report through `SendMessage`. Keep the plain-text response as a short
  pointer only.
- Don't wait for a "final answer" moment. Send **partial** findings as they firm up — a lead
  assembling a handoff would rather have a scoped negative early than a perfect report late.
- Corollary that also cost time: **if my own anchor/sanity check prints a MISMATCH, surface it
  immediately** instead of proceeding because the rest is self-consistent. On this task
  `tp+0x746c` read 891 where the brief said 3564 (the brief quoted the V38 4x-gain value, stock is
  891); I walked past the mismatch silently and the lead had to correct me. A failed anchor is a
  stop-and-report event.

Related: [[accord-steerstatus3-speed-gated-but-report-only]],
[[accord-gp6a5e-is-voted-vehicle-speed]].
