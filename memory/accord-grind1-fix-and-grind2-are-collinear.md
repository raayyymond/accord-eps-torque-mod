# ★★★★★ THE GRIND-#1 FIX AND GRIND #2 HAVE NEVER BEEN SEPARATED — they are perfectly collinear

**Settled 2026-08-06.** This is the fact that should stop the next agent proposing a rate-lane grind-#1
fix as if the trade were solved. **It is not solved. It has never been tested.**

## The result — [EVIDENCE]

Split-half null computed **first**, inside the stock-lane pool, with the identical estimator:
**[0.663, 1.502]**. Grind #1 = p90 of the 18–22 Hz envelope over engaged-creep windows, **episodes**
resampled. Grind #2 = merged burst events, 40–49 Hz envelope p99 > 500 counts, 2.56 s / 50% overlap
(`r47_orchestrator_checks._windows`, unchanged).

**The builds that measurably moved grind #1 are EXACTLY {V62, V65, V67, V68, V71C}.**

| moved grind #1? | build | grind-#2 events | engaged creep-CORNER s | engaged HIGH-RATE creep s |
|---|---|---|---|---|
| **YES** | V62 · V65 · V71C | **present** | 74.2 · 189.4 · 23.0 | 21.8 · 120.3 · 6.4 |
| **YES** | **V67 · V68** | not observed | **11.5 · 0.0** | **0.0 · 0.0** |
| no | V58·V59·V61·V64·V69·V70·V71B·V72·V73·V74 | none | 3.8 – 56.3 | 0.0 – 21.8 |

⇒ **Every build with adequate grind-#2 exposure failed to move grind #1, and every build that moved
grind #1 either shows grind #2 or has essentially no exposure in the burst regime.**

**18 of 21 creep burst windows sit at |ang| ≥ 100°**, so seconds of plain creep are not interchangeable
with seconds of engaged creep *cornering*. That is the cell where V67/V68 hold 11.5 s and 0.0 s.

## Why the record looked like the trade was solved

The V67/V68 cell was written **"none"**. It is **11.5 s at P(0) = 0.80** — power 19–39%. And the
operator's own V67 report hedged precisely there. See [[feedback-never-log-a-hedge-as-a-null]].

## Corpus-wide association — the phenomenon IS build-linked [EVIDENCE]

All **13** merged events fall in the **29.4%** of dosed non-highway exposure held by the two "both lanes
up" groups: **p = 1.2e-7**. V71C alone holds **3 of 13** in **5.28%** of exposure, **P(≥3) = 0.028**.
Stock lane: **0 events in 1207.0 s**, P(0) = 0.019.

## The fix, and it costs no bytes

**~90 s of deliberate ENGAGED hard cornering at creep** (< 4 m/s, |ang| ≥ 100°, openpilot engaged) takes
P(0) from ~0.61 to < 0.05 **on a single drive**. **Ship that instruction with every rate-lane build.**

## What this does NOT say

⚠ It does **not** say a rate-lane grind-#1 fix necessarily brings grind #2 — that is unproven in the
other direction too. It says the corpus **cannot distinguish** the two, so any build claiming one without
the other is asserting something no measurement supports.

Instruments: `analysis-2020accord/grind2_collinearity.py`, `grind2_delivered_verdict.py`,
`grind2_delivered_census.py`, `_grind2_delivered_lib.py`.

Related: [[accord-two-lane-rule-grind2]] (rebuilt on delivered multipliers),
[[accord-v76-rate-lane-restore-is-underisked]], [[feedback-episodes-not-windows-and-the-noise-floor]],
[[feedback-rule7-mode-proof-or-a-bet]], [[accord-v62-fixed-the-grinding]].
