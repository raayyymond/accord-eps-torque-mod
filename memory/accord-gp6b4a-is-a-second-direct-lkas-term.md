---
name: accord-gp6b4a-is-a-second-direct-lkas-term
description: "gp-0x6ad6 (the PID's driver-torque tracking reference) has TWO LKAS-command-descended terms, not one. Term 0 is gp-0x6b4a — direct, unconditional, NEGATED, with NO calibration weight anywhere on its path and a gate window (+/-25600) equal to the cell's own final clamp, so it can drive the reference to its full rail alone. It is structurally REINFORCING. The golden model's [VERIFIED] block at eps_lkas_chain_model.py:2318-2344 documented only the sibling gp-0x6b4c."
metadata:
  type: reference
---

# `gp-0x6b4a` — the SECOND, direct LKAS term into `gp-0x6ad6`. Traced 2026-08-10/11.

`FUN_00037fe6` (`0x37fe6`), the assist-reference-model aggregator that produces `gp-0x6ad6`:

```python
iVar4 = 0
if abs(gp_6b4a) <= 0x6400:      # 25600 — UNCONDITIONAL, negated, NO cal weight
    iVar4 = -gp_6b4a
if gp_67ab != 1:                # gates the OTHER SEVEN terms as a block
    iVar4 += sum(gated(term_i, window_i) * cal_weight_i for i in 1..7)
gp_6ad6 = clamp(iVar4 * speedLERP(gp_69aa) / 1024, ±25600)
```

**Two LKAS-descended terms, not one:**

| | signal | gate window | cal weight | ceiling as % of `gp-0x6ad6`'s rail |
|---|---|---|---|---|
| **term 0** | **`gp-0x6b4a`** | **±25600** | **none — implicit ×1, negated** | **100 %** |
| term 7 | `gp-0x6b70` (observer residual) | ±10240, own clamp ±8192 (`0xC6200`) | `0xC64B0` = 1 | **32 %** |

**A2 CONFIRMED by red-team, at instruction level:** every instruction from `gp-0x6b4a`'s load
(`0x37fea`) to its use in the final `add r13,r10` (`0x380b4`) is
`ld.h → addi → cmp → mov → bnc → sub → sxh → add`. **No `mulh` — no multiply of any kind — ever
executes on that path.** Contrast terms 1–7, each of which is `mulh`'d by its own cal byte
(`tp+0x74ac..0x74b3`).
**A3 CONFIRMED:** the `addi 0x6400 / ori 0xc801 / cmp / bnc` idiom is the standard `|x| ≤ K` test with
K = 25600, i.e. **term 0's own gate window is identical to the cell's own output rail** ⇒ term 0
alone, unweighted, can drive the reference to its rail.
**A5 CONFIRMED, byte-level:** `be 0x380b6` at `0x380b2` is bytes `A2 05`, low nibble `0x2` = **BE**,
distinct from `0xA` = BNE ⇒ the `gp-0x67ab == 1` gate really skips the 7-term add on **equality**. The
`be`/`bne` inversion class that has bitten this kit before **did not occur here.**

## Sign: term 0 is REINFORCING, not cancelling

`bias = clamp(gp-0x6ad6, ±8192)` → `err = clamp(gp-0x4f60 − bias, ±0x2800)` → P/I/D (all positive
gains) → `× authorityLERP(≥0) × polarity(gp-0x6752, boot-static +1)` → **ADDED** into the aggregator
(`mov`, `add`×8, no negation). Raising `gp-0x6b4a` makes term 0 more negative ⇒ bias more negative ⇒
`err` **rises** ⇒ PID rises ⇒ **more assist in the same direction as LKAS's own contribution.**
Same qualitative shape as the K1/friction mechanism. **The two negations (term 0's, and `error`'s
subtraction) cancel exactly.**

## What it corrects

- 🛑 **The golden model's `[VERIFIED]` tag was covering an incomplete picture.**
  `analysis-2020accord/eps_lkas_chain_model.py:2318-2344` documents `FUN_00026c80` as `[VERIFIED]` —
  "~11 LKAS-internal distribute sources summed into `gp-0x6b4c`, the LKAS lane into the aggregator."
  True, and it **missed `gp-0x6b4a`**, the wider **pre-combine sibling** from the same internal
  aggregate `iVar13` (`gp-0x6b4a = clamp(iVar13, ±0x6400)` @`0x277be`;
  `gp-0x6b4c = clamp(… + polarity × ((iVar13 × cal(0xC63CC)) >> 10), ±0x2800)` @`0x27722`).
  📋 **A `[VERIFIED]` tag certifies what was checked, not that nothing else is there.**
- 🛑 **`build_v41_tva.py` / `BUILD-LINEAGE.md`'s "`0xC6194` architecturally inert" claim** is true only
  for the **sibling** `gp-0x6b4c`, not for `gp-0x6b4a`.

## Open / caveats

- ⚠ **`gp-0x67ab`'s exact trigger is still unresolved** (one writer, `0x2775c`, inside the same mixer).
  **If it is usually 1, term 7 never fires and term 0 is the ENTIRE reference-model story.**
- ⚠ **`gp-0x6b4a`'s typical magnitude in real driving is UNMEASURED** — no telemetry on it exists.
- 🛑 **A4 REFUTED**: `gp-0x6b4a` is *not* "all LKAS-internal". Lane 2 is resolver-descended and
  torque-gated — **but it is also structurally inert** ([[accord-c616c-never-raise-driver-torque-relay]]),
  and **what actually drives `gp-0x6b4a` off zero is an OPEN question**: nine of ten lanes write a
  literal 0 on the traced path, lane 2 is severed, and the two remaining contributors (the rate-limited
  `Σ gp-0x625c[i]` and a `gp-0x6a62`-indexed LERP term) were not traced.

Source: `docs/TRACE-2026-08-10-driver-reference-vs-lkas.md` · `docs/REDTEAM-2026-08-11-term0-verdict.md`
Related: [[accord-gp6afe-gp6b4e-are-always-zero]] · [[accord-c616c-never-raise-driver-torque-relay]] ·
[[feedback_eps_lkas_chain_model_golden_reference]] · [[accord-friction-polarity-more-friction-is-more-assist]]
