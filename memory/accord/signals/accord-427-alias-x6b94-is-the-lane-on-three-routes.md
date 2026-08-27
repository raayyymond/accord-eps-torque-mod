---
name: accord-427-alias-x6b94-is-the-lane-on-three-routes
description: "🛑🛑★★★★★ `x6b94` is a MISLABELLED ALIAS of `x6b4c` (the LANE, not the aggregator sum) in `_scratch/cache/r96`, `_scratch/cache/r97` and `_scratch/cache/r9e` — byte-identical arrays, AUDITED. Only r85/r95 carry the real sum. This is the SAME error class that produced GATE2's original notch verdict (lane quoted as sum ⇒ dose 4× too large). Guard: `analysis-2020accord/verify/check_427_alias.py`."
metadata:
  node_type: memory
  type: reference
---

# `x6b94` is the LANE, not the SUM, on r96 / r97 / r9e

**Audited 2026-08-21 with `analysis-2020accord/verify/check_427_alias.py` — EVIDENCE, byte-identity check
over every `_cache_*` directory on disk, not a spot check.**

## The trap
CAN **427 (`0x1AB`)** carries ONE firmware cell, and **which cell depends on the BUILD**:

| route | build | 427 packs |
|---|---|---|
| `0x85` | V100 | **`gp-0x6b94` — the AGGREGATOR SUM** |
| `0x95` | V101 | **`gp-0x6b94` — the AGGREGATOR SUM** |
| `0x96` | V102 | `gp-0x6b4c` — the 11-slot LANE |
| **`0x97`** | **STOCK** | `gp-0x6b4c` — the LANE |
| `0x9e` | V103 | `gp-0x6b4c` — the LANE |

**The extractors write BOTH `x6b94` and `x6b4c` keys regardless of which cell was on the wire.** So
on every lane route, **`x6b94` is a byte-identical alias of `x6b4c`.** `L.load('r9e')['x6b94']`
returns the lane and nothing warns you.

**AUDIT RESULT — three affected, not two:** `r96` (|max| 1664), **`r97` (|max| 2214.4)**, `r9e`
(|max| 1497.6). `r85`/`r95` clean (sum only, no `x6b4c` key). `r77`–`r82` and `ratio` clean.
⚠ **`r97` is the STOCK 1× baseline** — 681 s engaged, 82.8 % above 35 km/h, *the best untouched
highway reference in the kit* and therefore the one most likely to be reused. It was **not** in the
original report of this trap; the audit found it.

## 🛑 WHY IT IS DANGEROUS AND NOT A LABELLING NICETY
**At 6–9 Hz the aggregator is a 4:1 near-cancellation** — individual lanes are LARGER than their sum
(`|lane|` 0.198 vs `|sum|` 0.053). So reading a lane as the sum is a **factor of ~4 on every dose
computed from it**, in the unsafe direction.

**This is the same error class that produced GATE2's original notch verdict**: `0.2075 ∠ +39.7°` was
quoted as the sum when it was the **lane**, so the correction was being added to a baseline 4× too
large. That mistake cost a full re-derivation. It is now latent **in the data files themselves**
rather than in a document, which makes it harder to spot.

## THE GUARD
`analysis-2020accord/verify/check_427_alias.py`:
- `assert_is_sum(tag)` — raises unless the route genuinely packed `gp-0x6b94`. **Call it before
  using `x6b94` as the aggregator sum.**
- run the file directly to re-audit every cache on disk.
`SUM_ROUTES = {"r85", "r95"}` is the whole allow-list. **If a future build repoints 427, add it there
and re-run the audit** — the guard is only as current as that set.

## SIBLING TRAP IN THE SAME CACHES — `damp_nz` / `g6ac2` are STALE DECODES
Both keys are present in **every** cache, but they are decoded from a **V75/V84-era probe bit that
V102/V103's cave repurposed.** On `r9e`, `damp_nz` shows duty **0.2390** — plausible-looking and
meaningless. ⚠ It sits uncomfortably close to the genuine `|rate| > 12.7 °/s` duty of **0.2419**, so
it is possible to "confirm" the damper's duty with a bit that is measuring something else entirely.
**Do not use `damp_nz` or `g6ac2` on any V100+ route.** [Reported by an analysis agent; the numeric
duty is EVIDENCE, the "stale decode" attribution is BELIEF pending a bit-map diff against
`builds/v80_v107/build_v102_tva.py` / `builds/v80_v107/build_v103_tva.py`.]

## Related
[[accord-raw14-offbyone-in-every-cache]] — the other latent cache defect; same lesson, different
mechanism. [[feedback-run-the-control-before-the-measurement]] ·
[[accord-gp6b4c-is-an-11-slot-assist-sum]] — what the lane actually is.
