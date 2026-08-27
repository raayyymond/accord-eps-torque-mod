---
name: reference-accord-falsifier-b-anchored-search-presupposes-answer
description: "V74's pre-registered abort criterion (5xf0 prominence, +/-4 bin search anchored to that build's OWN predicted 5xf0) cannot distinguish a genuine relay harmonic from a fixed pre-existing line the prediction happened to land near -- it presupposes the answer by construction. Confirmed on real data: V74's true 40.20 Hz peak sits 43 NFFT-2048 bins outside the anchored search's +/-4-bin reach. Retire Falsifier B and C in their anchored form; use an un-anchored wideband regression instead."
metadata:
  type: reference
---

**Found 2026-08-06, investigating why V74's pre-registered `5xf0` abort gate (`docs/STATE.md`) read
ambiguous — one method clear, one method (the K-free per-window version, the corpus MAXIMUM) with a CI
crossing the 3.0 abort threshold, and a thin creep-only reading at 5.844 against a 0.632 pooled
baseline.** Confirmed two independent ways this session (an across-build wideband regression here, and a
sibling's per-window Theil-Sen tracking test with a working positive control) — see
[[reference-accord-v74-flight-underpowered-both-symptoms-active]] for the flight-level summary this
supersedes on the gate question.

## The defect, stated generally

**Any search that is anchored to a value PREDICTED by the hypothesis under test cannot test that
hypothesis — it can only confirm or fail to confirm what the prediction already assumes.** `studies/sessions/r5d/r5d_falsifiers.py`'s
Falsifier B searches for a peak within `+/-4` bins (averaged spectrum, NFFT 2048) or `+/-2` bins
(per-window, NFFT 512) of `5 x f0`, where `f0` is that SAME build's own measured 6-9 Hz line. This can
only ever report "something near the predicted 5th-harmonic location is prominent" — it structurally
cannot distinguish:
- **a genuine relay harmonic**, whose location MOVES with `f0` build to build (or window to window), from
- **a fixed, pre-existing line** that happens to sit near `5 x f0` for THIS PARTICULAR build/window,
  purely because that build's `f0` is close to `(the fixed line's frequency) / 5`.

Both produce an identical anchored-search reading. The anchoring is not a minor approximation — it
removes the discriminating information (WHERE the peak sits relative to its OWN build's predictor)
before the statistic is even computed.

## Why this is not a theoretical concern here — the 43-bin arithmetic

This kit has a recorded, pre-existing line at **42.19 Hz = 2 x the 21.09 Hz grind-#1 mode**
([[accord-v60-null-closes-parametric-pump]] / `accord/builds/accord-v59-parametric-pump-marginal.md`). V74 has the
**highest measured `f0` (8.46 Hz) of all 11 corpus builds** in the engaged-v<12.5 arm, so its own
`5 x f0 = 42.31 Hz` sits closer to that fixed line than any other build's `5 x f0` does.

An UN-anchored wideband (33-47 Hz) search — free to find the tallest peak anywhere in that range,
independent of any build's own `f0` — locates V74's true dominant peak at **40.20 Hz**, essentially
exactly on `2 x grind-1`'s own measured frequency (40.19 Hz), and **2.11 Hz away from `5xf0`
(42.31 Hz)**. At NFFT 2048 / fs=100 Hz, the bin width is `100/2048 = 0.0488 Hz`, so `2.11 / 0.0488 ~= 43
bins` — the true peak sits **~43 bins outside the anchored search's +/-4-bin reach.** The anchored
search physically could not have found it; it necessarily reported a weaker nearby sidelobe (prominence
2.23) instead of the true dominant feature (prominence 5.27-15.70 depending on which arm/window is
checked). **This is not an edge case — it is the mechanism by which Falsifier B produced a misleading
number on the single build where it mattered most.**

## The two confirming tests, both against the anchored-search's implicit "genuine relay" reading

1. **Cross-build tracking regression** [EVIDENCE, `analysis-2020accord/studies/sessions/r5d/r5d_tracking_test.py`,
   `_scratch/out/_r5d_tracking_test.json`]. Regress the un-anchored wideband peak's location against `5 x f0` and
   against `2 x f_grind1`, across all 11 corpus builds (engaged v<12.5, larger-K arm):
   ```
   peak_f vs 5xf0     : slope 0.165 [-0.461, 0.913]   r=0.144   p=0.673   (not significant)
   peak_f vs 2xfgrind1: slope 1.478 [ 0.477, 2.255]   r=0.759   p=0.0068  (significant, CI excludes 0, includes 1)
   ```
   Confirmed independently by a sibling's per-window Theil-Sen test with its own positive control: slope
   vs `5 x f_ratchet` = `+0.046 [-0.201, +0.386]` (flat), while V72's own line tracks `2 x f_grind1` at
   `+0.833 [0.570, 1.016]`, r=0.597 (the working positive control proving the METHOD can detect real
   tracking when it is present). Different unit of analysis (across-build vs per-window), different
   anchoring, same conclusion.
2. **Odd-harmonic-series completeness** [EVIDENCE, `studies/sessions/r5d/r5d_3xf0_check.py`, `_scratch/out/_r5d_3xf0_check.json`]. A
   genuine relay excites the WHOLE odd harmonic series, not just the 5th. V74's `3 x f0` prominence =
   **1.374 [1.05, 2.56], rank 5 of 11 builds — unremarkable** (corpus range 0.47-18.34). The series is
   incomplete: elevated-looking at 5x, ordinary at 3x. That is evidence against a relay independent of
   the 42 Hz question entirely.
   🛑 **`3xf0` is not automatically clean either** — for V62 and V71B specifically, `3xf0` lands within
   0.6 Hz of THEIR OWN grind-1 fundamental (18-22 Hz), producing spuriously huge readings (15.8, 18.3):
   the identical class of artifact, one harmonic down. **V74 is the one build where `3xf0` happens to be
   clean** (5.29 Hz from its own grind-1 fundamental, the largest gap in the corpus) — the SAME property
   (V74's unusually high `f0`) that confounds it at `5xf0` is what makes it clean at `3xf0`. Check the
   gap to the nearest known fixed line before trusting ANY single anchored harmonic reading, for ANY
   build.

## The generalizable rule

> **An anchored search (any statistic computed only near a value the hypothesis itself predicts) is
> valid evidence FOR that hypothesis only if the anchor's predicted location is independently shown to
> separate from competing fixed explanations for that specific case. It is never valid evidence
> characterizing what is actually in the data**, because a coincidental predictor-target alignment
> produces an identical reading to a genuine relationship. Before trusting an anchored reading: (1) run
> an UN-anchored search over the same region and confirm the peak the anchored search claims to have
> found is the same one, at bin-level resolution, not just "in the neighbourhood"; (2) if a competing
> fixed explanation is known or suspected, compute the anchor's distance to it explicitly, in bins, not
> qualitatively; (3) prefer a cross-build or cross-window TRACKING regression (does the reading move when
> the predictor moves?) over any single-point anchored statistic — see
> [[feedback-a-ratio-is-not-a-tracking-test]] for the sibling lesson this generalizes (a ratio of two
> quantities is not a tracking test either, for the same underlying reason: a marginal-distribution
> artifact can imitate a real relationship at a single summary statistic).

## What this means for the criterion going forward

**Falsifier B and Falsifier C, as pre-registered for V74 (anchored `5xf0` prominence; raw `Δf0`), should
be RETIRED, not re-sized.** They are not simply "too strict" or "too loose" — they cannot in principle
separate the hypothesis they were written to test from its main competing explanation, on this specific
corpus (a genuinely pre-existing line near 5x the ratchet's typical frequency). For V75's flight and
beyond, use:
- the UN-anchored wideband peak search + cross-build tracking regression
  (`analysis-2020accord/studies/sessions/r5d/r5d_tracking_test.py` is the reference instrument, keep it),
- the `3 x f0` odd-harmonic-completeness check as a second, independent diagnostic (a real relay should
  show BOTH elevated; checking the gap to that build's own grind-1 fundamental/2nd-harmonic FIRST, since
  which harmonic (3x or 5x) is confound-free varies build to build.

## Related
[[reference-accord-v74-flight-underpowered-both-symptoms-active]] — the flight-level summary this
resolves the gate question for.
[[accord-v59-parametric-pump-marginal]] / [[accord-v60-null-closes-parametric-pump]] — source of the
42.19 Hz = 2x21.09 Hz fixed-line record this investigation confirmed is still live in the corpus.
[[feedback-a-ratio-is-not-a-tracking-test]] — the sibling lesson (marginal-distribution artifacts can
imitate real relationships; the fix is a tracking regression, not a summary ratio or a single anchored
point).
[[feedback-evaluate-clip-rules-on-the-observed-envelope]] — same family of lesson from the same session:
"which comparison you evaluate a statistic against" matters as much as the statistic itself.
