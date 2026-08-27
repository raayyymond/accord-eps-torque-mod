---
name: feedback-ground-every-session-in-golden-model-and-post-v38-arc
description: "Standing instruction — every EPS investigation or firmware-fix session must be grounded in the full model/eps_lkas_chain_model.py and the whole post-V38 build arc, and every subagent primed with both."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 5f77a420-7409-45d5-9449-a5d3307671b6
  modified: 2026-08-03T05:43:52.194Z
---

Operator instruction, 2026-08-03: **every** investigation or firmware-fix session on the Accord EPS kit
must take into account **(a)** the entire EPS LKAS chain model
(`analysis-2020accord/model/eps_lkas_chain_model.py`, the golden reference) and **(b)** all recent effort
**since V38** — read as one arc, not as the latest session's slice. This applies to me *and* to every
subagent I brief. Recorded in the kit's `CLAUDE.md` under "READ FIRST".

**Why:** a lever is only understood once you can say where it sits in the chain, what feeds it, and what
it feeds — the kit's strongest evidence form is a **dose-response across four or more builds**
(e.g. Kd = 0 / 1 / gated / 2 on grind #1), which is invisible if you read one handoff. Reading a slice
has repeatedly produced levers that were already flashed, already falsified, or pushed the wrong *way*
(V39/V42/V61 all tested the rate lane **downward**; the gradient pointed up).

**How to apply:** before proposing or evaluating any lever — and in every subagent prompt — require the
golden model plus `docs/BUILD-LINEAGE.md` and the `HANDOFF-*.md` chain back to V38. Pair it with the
existing mandatory grep of `analysis-2020accord/build_v*_tva.py` for any calibration address
([[accord-check-build-lineage-before-proposing-lever]]) and with
[[feedback-delegate-firmware-tracing-to-subagents]] for the standard priming block
(GhidraMCP only, gp=0xFEDF8000, tp=0xBF000).
