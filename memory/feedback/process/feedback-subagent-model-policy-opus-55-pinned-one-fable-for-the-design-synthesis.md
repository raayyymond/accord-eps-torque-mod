---
name: feedback-subagent-model-policy-opus-55-pinned-one-fable-for-the-design-synthesis
description: "Subagent model policy (2026-09-12, amended 2026-10-01/02): pin `claude-opus-5-5` for hard tasks (the `opus` alias once resolved to 4.8), `claude-sonnet-5-5` for trivial; set EFFORT per task (medium..xhigh) through the Workflow `effort` option — prompting does not set it; ONE Fable 5.1 subagent per design round for the single role that determines the design (the design synthesis / architect), nothing else on Fable"
metadata:
  type: feedback
---

**Rules, in order given:**
- 2026-09-12: never a Fable subagent; Opus for hard tasks, Sonnet for trivial; set the model explicitly every time.
- 2026-10-01: *"All opus agents should use 5.5"* — the `opus` alias had resolved to 4.8 mid-run; pin `claude-opus-5-5`.
- 2026-10-02: *"Be sure to have adequate control over their effort settings. Prompting them alone won't suffice"* —
  use the Workflow `agent()` `effort` option ('medium' | 'high' | 'xhigh'); the Agent tool has no effort control.
- 2026-10-02: *"for key subagents who solely determine the design (synthesis or architect or designer) use a Fable
  subagent. This should be limited to a single use."* — exactly one `claude-fable-5-1` call per design round, the
  design-synthesis judge whose output IS the spec; designers, scorers, judges, refuters, measurement syntheses
  stay Opus 5.5.

**Why:** cost and capability tiering is the operator's call; Fable is reserved for the orchestrator and for the one
decision that most needs it.

**How to apply:** every Workflow `agent()` carries `model` and `effort`; label the Fable call as the design synthesis;
brief grandchildren-spawning agents to pin models too. The 2026-10-02 V299 design round is the template
(`_scratch`-side script `wf_v299_design.js`: 5 designers xhigh → 3 scorers high → 3 judges xhigh → 1 Fable synthesis
xhigh → 3 refuters high).
Related: [[feedback-design-is-a-judge-panel-never-one-agent-one-solution]],
[[feedback-analysis-scripts-must-run-in-seconds-not-minutes]].
