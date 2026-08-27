---
name: feedback-delegate-firmware-tracing-to-subagents
description: "Operator wants disassembly tracing/decompilation/RE pushed onto cheaper subagents, primed with exact gp/tp values and confirmed golden-model findings."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 6a579c19-b22f-4385-a786-8205eb6c7a7e
  modified: 2026-07-19T22:57:46.759Z
---

**DEFAULT, not a preference to weigh: the vast majority of reverse engineering and decompilation on this kit goes to subagents** (`firmware-codepath-tracer`, `general-purpose-sonnet`). GhidraMCP is available to them. The lead steps in **only at the end, to verify**. Restated by the operator 2026-07-19 after the lead hand-decoded V850E2 instruction encodings inline instead of dispatching — do not make them say it a third time.

Trigger: if a task involves reading firmware bytes, decoding instructions, walking xrefs, resolving a `gp-`/`tp+` operand, or decompiling a function, **dispatch it**. Do not hand-decode opcodes inline "because it's just a few instructions" — that is the exact failure the operator called out.

Every dispatch MUST include:
- **The exact register bases: `gp = 0xFEDF8000`, `tp = 0xBF000`.** A `tp+0xNNNN` operand resolves to `0xBF000 + 0xNNNN`; `gp-0xNNNN` resolves to `0xFEDF8000 - 0xNNNN`. Do not make the subagent deduce these — the historical `+0x1000` slip (`0xC6NNN` misread as `0xC7NNN`) came from exactly that.
- **All relevant confirmed findings from `analysis-2020accord/model/eps_lkas_chain_model.py`**, the golden reference — see [[eps-lkas-chain-model-is-the-live-golden-reference]].

**Why:** Tracing is high-token, low-judgment work that parallelizes well; the lead's job is verification and calibration, not byte-walking. But subagents start cold, and wrong bases silently corrupt every address they report — which in this domain can reach a flashed ECU.

**How to apply:** Fan out tracing tasks in parallel with the bases and model context inline in each prompt. Re-verify every load-bearing claim yourself in Ghidra before it enters a build or a handoff — verification is the lead's job, byte-walking is not.
