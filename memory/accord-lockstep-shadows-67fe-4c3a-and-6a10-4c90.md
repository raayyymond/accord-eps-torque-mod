---
name: accord-lockstep-shadows-67fe-4c3a-and-6a10-4c90
description: Two lockstep shadow pairs not previously recorded — gp-0x67fe <-> gp-0x4c3a and gp-0x6a10 <-> gp-0x4c90. Reading either cell is safe; writing one requires the matched shadow write.
metadata:
  type: reference
---

★★ **TWO LOCKSTEP SHADOW PAIRS, NOT PREVIOUSLY ON RECORD.** 2026-08-08. [EVIDENCE, writer census.]

| cell | shadow | mechanism |
|---|---|---|
| `gp-0x67fe` | **`gp-0x4c3a`** | paired `st.b` at **every** writer; mismatch escalates via `FUN_0006b9fa` @`0x3BE68` |
| `gp-0x6a10` | **`gp-0x4c90`** | maintained by `FUN_0003fc16` |

**Reading them is safe. Writing either one requires the matched shadow write** — an unmatched write is a
lockstep desync, which is the failure class that produces hard shutdowns rather than wrong numbers.
Same family as the four pairs in [[reference-accord-fun45a20-monitor-and-shadow-lockstep-pairs]].

## ⊕ `gp-0x67fe`'s value domain is exactly {0, 1, 2}

Across **all five writers**, the only values ever stored are **0, 1 and 2**. ⇒ on this image the tests
**`!= 0`** and **`∈ {1,2}`** are **equivalent**, so a one-bit probe of `!= 0` fully answers the FactorD
enable question — you do not need two rungs to distinguish 1 from 2.

That closes the cheap half of the gate on [[accord-factord-is-the-angle-error-lever]]: `gp-0x67fe ∈ {1,2}`
is settleable with a single telemetry bit, and `gp-0x6a10` itself can be read alongside it without
touching either shadow.

Related: [[accord-damper-evaluator-fun34350-ceiling-clamp]] ·
[[accord-two-cave-encoding-traps-sar-floor-and-opcode-bit]] ·
[[feedback-cave-two-gates-ram-ownership-and-closed-loop]]
