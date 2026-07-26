---
name: feedback-tight-agent-briefs
description: Agent briefs with 7+ numbered steps reliably produce "lost in the sauce" failure; single-goal tight briefs with explicit DO-NOT lists converge cleanly
metadata:
  type: feedback
source: claude
---

**Agents with 7+ numbered steps in their brief reliably produce "lost in the sauce" failure.** Validated multiple times this session:

| Pattern | Outcome |
|---|---|
| Wave 2 SA handler verifier (7 numbered steps: disasm + call graph + cross-ref + 3 candidates + dispatcher reconciliation + S-box check + iterate) | Operator reported "lost in the sauce" mid-flight; was killed early |
| Wave 3 series (3 sequential agents, single goal each: VERIFY constants / REWRITE Python / propagate DOCS) | All 3 converged cleanly with clear deliverables |
| IMPL + QA pair on eps-update-tva.py (single goal each, sequential) | Clean ship after one targeted patch |

**Why:** Multi-step briefs encourage the agent to switch between unrelated subtasks, accumulating partial work without converging on any single answer. Verbose intermediate output makes the lack of convergence visible as "floundering." Single-goal briefs with a clear "DONE WHEN..." criterion keep the agent on a converging trajectory.

**How to apply when designing agent briefs:**

1. **One goal per agent.** If you can't summarize the agent's job in a single sentence ("X verifies Y", "X builds Z", "X reviews W"), the brief is too broad. Split it.
2. **Explicit "DO NOT" list.** Tell the agent what's out of scope. Example: "DO NOT update other docs (Agent N handles that). DO NOT rewrite Python (Agent M does that)."
3. **Concrete deliverables.** Name the output files explicitly with line caps (under N lines). Tells the agent when to stop.
4. **Sequential chains for dependent work.** If A → B → C, run them as three agents with B and C taking A's output as authoritative input. Don't pile them into one brief.
5. **Parallel for independent work.** If 4 hunters can each look in a different ecosystem, parallel is right (Wave 1 of SA-key chain demonstrated this).
6. **Tighten the brief based on the failure mode you're avoiding.** If past agents lost track, add structure. If past agents over-cautious, add permission to go deep.

**Anti-pattern: the "comprehensive single agent."** Tempting because it feels efficient (one agent, one report). In practice produces unfocused work + the "lost in the sauce" failure mode. The 3-agent sequential pattern (VERIFY → REWRITE → DOCS) was the format that worked this session for the SA-key verification chain.

**Heuristic:** If the brief is longer than 1 screen, it's too long. Decompose.

Related: [[feedback-dont-kill-long-agents-early]] addresses what to do when this pattern produces a "lost" state mid-flight.
