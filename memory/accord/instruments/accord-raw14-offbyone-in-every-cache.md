---
name: accord-raw14-offbyone-in-every-cache
description: "🛑 INSTRUMENT DEFECT in every route cache _scratch/cache/r5e..r73: the row arrays (t, probe) are exactly ONE SAMPLE SHORTER than the raw arrays (raw14_t, raw14_b4). Pairing t with raw14_b4 reads every cave byte ~10 ms early — 28 degrees of phase at 7.79 Hz."
metadata: 
  node_type: memory
  type: reference
  originSessionId: d1d94665-4414-43cb-884d-1f27ae127561
  modified: 2026-08-10T00:03:44.836Z
---

## THE INVARIANT — confirmed on all 13 caches on disk [EVIDENCE]

```
z["t"]     == z["raw14_t"][1:]
z["probe"] == z["raw14_b4"][1:]
```

`decode_v84_probe_r6d.extract()` appends to `raw14_t` / `raw14_b4` on **every** 0x14A frame, but only
appends a **row** (`t`, `probe`, `tq`, `rate_c`, …) once a 0x18F has been seen. The first 0x14A frame
arrives before the first 0x18F, so it never gets a row ⇒ **the row family is exactly one sample
shorter, forever, in every cache.** Verified `_scratch/cache/r5e` · `r61` · `r65` · `r66` · `r66x` · `r67x` ·
`r68x` · `r6d` · `r6e` · `r6f` · `r70` · `r71` · `r73` — 13 of 13, zero exceptions.

## WHY IT BITES

Any analysis that computes indices from `z["t"]` (e.g. `np.searchsorted(t, t_other)`) and then indexes
`z["raw14_b4"]` with them takes **every byte one 0x14A frame (~10 ms) EARLY**.

**At 7.79 Hz, 10 ms is 28° of phase.** That is not a rounding error for a coherence or phase
measurement — it is a substantial fraction of a cycle.

## MEASURED COST, and the asymmetry that is itself diagnostic

The V88 identity test `b6 == (427 wire ≥ 160)`:

| | route 73 (V88) | route 71 (V87 control) |
|---|---|---|
| misaligned (`t` + `raw14_b4`) | **0.9437** | 0.4033 |
| aligned (`t` + `probe`, or `raw14_t` + `raw14_b4`) | **0.9654** | 0.4022 |
| cost of the off-by-one | **−0.0216** | **+0.0012** |

★ **The asymmetry is evidence of coupling.** On route 73 the two channels genuinely read the same cell,
so a 10 ms skew destroys real agreement; on route 71 they read different cells, so a shift merely
reshuffles an uncoupled pair and wanders by ~0.001. **The sign and size of the perturbation confirm the
coupling independently of the headline number.**

## 🛑 THE RULE

**Safe pairings are `(t, probe)` and `(raw14_t, raw14_b4)`. Never cross the two families.**
`z["probe"]` is the row-grid-aligned cave byte and is the safe one.

Audit script: `analysis-2020accord/verify/audit_raw14_offbyone.py` — re-confirms the invariant on every cache
and flags source files that mention `raw14_b4` while deriving an index from `t`. A mention alone is not
a defect: extractors legitimately *write* the array, and `(raw14_t, raw14_b4)` is correct.

⚠ **Not audited: whether any HISTORICAL result rests on the crossed pairing.** 27 files were flagged for
review; most are extractors. The defect predates route `73` by at least eight routes, so any past
phase/coherence claim built on the cave byte is exposed until checked.

Found by a subagent during V88's close-out, 2026-08-09, while reconciling two identity numbers that
differed by 0.0217. ⊕ **The reconciliation was worth more than the number** — an orchestrator hypothesis
("ZOH resampling artefact") was wrong, and chasing the discrepancy instead of averaging it away found a
kit-wide instrument bug.

Related: [[accord-v88-flew-grinding-fixed-command-intact]] ·
[[feedback-run-the-control-before-the-measurement]] · [[accord-probe-underranges-to-one-bit-comparator]]
