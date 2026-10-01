---
name: feedback-design-is-a-judge-panel-never-one-agent-one-solution
description: "Operator instruction 2026-10-01: a firmware design round must evaluate MULTIPLE potential designs AND multiple implementations per design — 'I don't want a single agent to come up with a singular solution.' Pattern: independent designers from distinct angles (fewest bytes / robust margins / goal-first / loop structure / integral-and-handover) each delivering >= 2 implementations, COMMON scorers that re-score every candidate with one pipeline (designers never grade their own work), independent judges with distinct lenses, one synthesis with grafts (primary + fallback implementation), then refuters; revisions after a refutation are themselves a 2-reviser mini-panel with a judge pick."
metadata:
  type: feedback
---

**Why:** the first angle-loop design round (2026-09-30) produced C0 from one reconciler and C1 from one reviser; each
was refuted on something a different angle would have gated (combined plant members, integer blindness, I policy).
The operator ruled that a single agent producing a single solution is not acceptable for a firmware design.

**How to apply:** when a design or build is called for, author a Workflow with a judge-panel shape (see
`angle-loop-design-panel` script in the session workflows dir, 2026-10-01): ≥ 4 designers × ≥ 2 implementations,
common frequency + time scorers, ≥ 3 judges, synthesis, refuters, bounded revision panel. Also: refuter briefs carry
the kit's safety priming and are phrased as fail-safe VERIFICATION (one Opus refuter was stopped by a safety classifier
when asked to "find any way the design delivers torque the operator did not command").

Related: [[feedback-tuning-space-is-whatever-a-cave-can-afford-minimise-and-verify]], [[project-the-goal-2026-09-30-angle-loop-cave-tight-smooth-silent]].
