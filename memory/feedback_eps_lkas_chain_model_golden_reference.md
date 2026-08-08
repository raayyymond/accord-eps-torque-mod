---
name: eps-lkas-chain-model-is-the-live-golden-reference
description: "Treat eps_lkas_chain_model.py as the repo's most current golden reference, update it continuously, and extend it to cover the full driver-assist chain."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 6a579c19-b22f-4385-a786-8205eb6c7a7e
  modified: 2026-07-29T23:59:47.979Z
---

Use `analysis-2020accord/eps_lkas_chain_model.py` as the live, most up-to-date golden reference for the EPS command-to-motor chain. Update it throughout every relevant investigation as findings are learned and validated, rather than leaving validated knowledge only in handoffs or memory.

**Scope directive (2026-07-19):** the model must cover **the entire driver-assist chain too**, not only the LKAS lane — every aggregator sibling, the Sensor-B torque-rate lanes, base/manual assist, and their shared governor/shaper path. The two chains merge at the aggregator and share downstream stages, so modeling LKAS alone cannot predict on-car behavior.

**Why:** The model is the shared ground truth used to keep firmware conclusions, build behavior, and future reverse-engineering work consistent. Symptoms like the V38/V39 vibration and ratchet are driver-conditioned, so a LKAS-only model is structurally blind to them.

**How to apply:** Read it before EPS control-path work; reconcile new evidence against it; clearly label verified, inferred, and open behavior; and update its executable logic, self-checks, and explanatory comments in the same session when evidence changes the model. Pass its confirmed findings to subagents — see [[feedback-delegate-firmware-tracing-to-subagents]].

**Terseness constraint (2026-07-29):** the operator had this file distilled from 4,709 to 2,200 lines because comments/docstrings had ballooned into full research essays (dated changelogs, multi-hundred-line findings reports in function docstrings). Standing rule going forward: inline `#` comments ≤1 sentence, function/class docstrings ≤1 paragraph — state, address ties, Q-format/confidence tags, in as few words as possible. The full narrative belongs in `docs/HANDOFF-*.md`, `docs/STATE.md`, `docs/BUILD-LINEAGE.md`, and `memory/`, not in this file. Do not let it re-balloon; when adding a new finding, add the terse fact here and put the story in a handoff.
