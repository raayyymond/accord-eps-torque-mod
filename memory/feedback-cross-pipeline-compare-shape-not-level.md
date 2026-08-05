---
name: feedback-cross-pipeline-compare-shape-not-level
description: Across two agents' pipelines, compare SHAPES not single-bin LEVELS — independent implementations of the same metric differed 1.16-2.40x per bin while agreeing on shape at corr 0.856.
metadata:
  type: feedback
---

**Two independent implementations of "the same" grind metric differed by 1.16x to 2.40x, bin by bin, in
both bands, while agreeing well on SHAPE (ratchet ladder shape correlation 0.856 over 0-45 deg).**

Recorded 2026-08-05, proposed independently by both agents involved (D1-near-centre-retro and
D3-microratchet) after it cost two message round-trips and one retraction from each.

**What happened.** D1 read the 6-9 Hz ratchet at **960** counts p-p in the `|mid| 0-3 deg` bin; D3 read
**2115** in their own pipeline. Compared as a single cell it looked like a hard contradiction, and two
successive explanations were floated and both failed — re-centring (D3 re-centres every route; it moves
their number 12%, not 2x) and a flat pipeline level offset (rescaling D1's 960 by the median offset from
the other ten bins gives 1507 against D3's measured 2115, and the 0-3 bin sits at *opposite* extremes of
the offset distribution in the two bands). It was closed as small-n on both sides (16 vs 65 windows,
D1's own CI already [684, 1389]) rather than by manufacturing a third hypothesis.

**Why:** `e_18-22`-style envelope metrics depend on window tapering, detrending, the `fs` estimator,
episode/segment cuts and the burst threshold. Each is defensible; together they set a pipeline's LEVEL.
Shape survives them; level does not.

> **RULE: across pipelines, SHAPE comparisons are safe and LEVEL comparisons are not. Never adjudicate a
> cross-agent disagreement on one cell.** Put the whole ladder side by side, or normalise each pipeline
> to its own mean and correlate the shapes. **Quote a bin's CI before comparing it to another agent's**
> — D1's fine ladder was originally filed with no CIs at all, and block-bootstrapping later showed every
> adjacent bin pair overlapping heavily, so no bin-level reading was supportable from either agent.

⚠ **Corollary that bit in the same session:** a shape correlation on a *flat* profile measures noise.
Grind #1's cross-pipeline shape correlation came out 0.650, and it is meaningless — grind #1 is
statistically flat over 0-45 deg. Only the ratchet's climb replicates. Do not quote the flat band's
correlation as a contrast.

⊕ Same family as [[feedback-episodes-not-windows]] and [[feedback-a-ratio-is-not-a-tracking-test]]: the
wrong thing treated as the comparable unit. This kit pools numbers across agents routinely, so the
failure mode is live every session.

⊕ One fact of record promoted from assumption in the same exchange: **the steering sensor zero is
-4.4 deg mechanical**, derived twice independently (D1 -4.12 to -5.00 over 14 routes; D3 -4.20 to -5.10
over 8), matching the operator's stated +/-4 deg. It is load-bearing for any angle bin narrower than
~10 deg and negligible at 15/45 deg edges.
