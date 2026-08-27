# 🛑🛑 A CAVEAT EXPLAINING WHY A NULL IS WEAK CAN MUTATE INTO A POSITIVE RESULT

**Discovered 2026-07-31, three handoffs after the mutation happened. It had already become the leading
hypothesis's single best piece of supporting evidence, and it was never a measurement at all.**

## What happened

V52C low-passed the torsion-bar torque sensor `gp-0x4f60` (EMA, α = 74/1024, fc ≈ 12 Hz) and was
flashed. The operator reported: *"V52C did not fix the vibration; it clearly changed manual feel."*
**A null.**

A later handoff wrote a caveat explaining why that null was weak evidence:

> ⚠ **V52C's null is weak** — `alpha = 74/1024` ⇒ fc ≈ 12 Hz ⇒ only −6.1 dB at 21 Hz *while adding 61°
> of lag*. **It halved the mode's content; it did not remove it.**

Two handoffs later that had become:

> V52C … **halved the mode** — the largest single effect any build has had on the grinding, and the
> **only** lever that sat on the **feedback** path.

The word *null* was gone. The sentence had inverted from "this test was too weak to trust its null" to
"this build produced our biggest positive result," and it propagated into `STATE.md`, `BUILD-LINEAGE.md`
and `memory/reference/firmware/reference_accord_loop_through_torque_sensor_uncompensated.md` as the retrodiction that made
the loop hypothesis compelling. It then generated a "re-derive V52C's number" task that **could not be
executed, because there is no V52C rlog and never was.**

## The arithmetic that settles it

`−6.1 dB at 21 Hz` and `halved the mode` **are the same statement written twice.**

```python
# V52C's EMA:  y[n] = y[n-1] + ((74 * (x[n] - y[n-1])) >> 10)
# |H(f)| = a / |1 - (1-a)*exp(-j*2*pi*f/fs)|,  a = 74/1024,  fs = 1000 Hz
#   f = 20.9 Hz  ->  |H| = 0.4963  ->  20*log10(0.4963) = -6.08 dB
```

**0.496× IS "halved". It is the filter's designed attenuation — a number computed from the build
script, not from a drive.**

## Why this is a distinct failure mode worth its own memory

It is the **inverse** of [[accord-check-build-lineage-before-proposing-lever]]'s lesson. That one says
*a withdrawn RATIONALE is not a withdrawn RESULT* — don't treat a falsified address as reopened because
its reasoning changed. **This one is the opposite direction: a design figure quoted inside a caveat got
promoted into a result.** Both are the same underlying error — **losing track of whether a number came
from the bytes or from the car** — and both bite hardest when a new mechanism makes the old number look
freshly meaningful.

## The rules that follow

1. **Every quantitative claim about an on-car outcome must carry its provenance inline** — route ID,
   segment, frame count, statistic. If it cannot, it is a design figure until proven otherwise.
2. **Before building on any "build X did Y" claim, confirm the rlog exists.** `STATE.md` asserted *"The
   rlogs exist; this is analysis, not a drive"* for a route that was never logged. Check
   `analysis-2020accord/rlogs/` first — it costs one `ls`.
3. **A number that exactly equals a filter's transfer function at the mode frequency is a transfer
   function**, not a coincidence. Recompute the design figure and compare before quoting it.
4. **When compressing a caveat, keep the polarity word.** The mutation happened at a summarisation step
   where "null, and here's why the null is weak" was shortened to its subordinate clause.

Related: [[accord-check-build-lineage-before-proposing-lever]],
[[reference_accord_loop_through_torque_sensor_uncompensated]],
[[accord-telemetry-conventions-that-produced-wrong-answers]].
