---
name: feedback-verify-subagent-claims
description: "Personally re-derive load-bearing sub-agent claims before car-affecting / durable actions. Sub-agents were confidently WRONG twice this session; direct verification caught both."
source: claude
metadata:
  type: feedback
---

# Verify load-bearing sub-agent claims — don't relay

Reinforced 2026-05-30 (prompted by Joey's "did you run the sim or just build it, or just relay the agents?").

**Why:** Two sub-agents produced confident, load-bearing claims that were FALSE, caught only by re-deriving directly:
- A sufficiency-test agent claimed route `00000007` ran a degenerate fallback tune (kpV=[0.12]) → "v3 = route 08 only." Direct carParams read: **both 07 and 08 ran v3** (kpV=[.010,.045,.075]/kf3.0e-5, 22+10 carParams). The agent's claim would have sent Joey chasing a phantom install bug.
- The longitudinal-QA agent read the wrong *branch* (sp-modded, not joey/latlon) for the gas ceiling and concluded "v2 reverting to 750 is backwards." Direct read of joey/latlon: **gas = [0,750], the memory was right**; the agent's inversion was false.

**How to apply:** For any sub-agent claim that gates a flash, a branch push, or a durable memory, treat it as a hypothesis and re-derive it yourself (run the script, read the carParams, grep the actual branch). Especially before anything touching the car. Relaying agent output as verified fact is the failure mode.

Related: [[reference-real-plant-from-peter]], [[feedback-direct-no-hedging]].
