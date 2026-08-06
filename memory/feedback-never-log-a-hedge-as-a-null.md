# 🛑🛑 A WELL-POWERED SUBJECTIVE REPORT OUTRANKS AN UNDER-POWERED MEASUREMENT — and never log a hedge as a null

**2026-08-06. The operator challenged a build recommendation and was right. The recommendation rested on
a table cell reading "none" that had been a HEDGE when he wrote it.**

## What happened

On V67 he wrote (`docs/HANDOFF-2026-08-02-v67-flew-and-the-highway-grind-is-not-the-rate-lane.md:23`):

> *"Grind #2 seems **mostly** gone. However, and maybe this is a grind #3 or #2.5, on the way, when doing
> somewhat significant turns, there is sometimes a resonance that I can feel is similar to grind #2. …
> Grind #2 **might still be there somewhat** during LKAS-disengaged or **more so LKAS-engaged at
> low-speed, I am not sure. Might just be dampened.**"*

That was recorded in the two-lane rule table as **"none"**. A later session cited the "none" as evidence
that V67/V68's configuration is grind-#2-free, and built a recommendation on it.

**The measurement behind that "none" is 11.5 s of engaged creep cornering and 0.0 s of engaged high-rate
creep — P(0) = 0.80, power 19%.** He named *engaged low-speed* as exactly where he was unsure. His
multi-day exposure on V67/V68 vastly exceeds 11.5 s of log. **His report was the better-powered
instrument and the record converted it into its opposite.**

## The standing instruction this violated

`CLAUDE.md`: *"The operator's **lived experience overrides analyst recommendations** — if they report how
the car feels, that beats theoretical dwell-time arguments."* A null derived from 11.5 s is a
dwell-time argument.

## How to apply

1. **When logging a subjective report into a results table, keep the hedge, or record the cell as
   `UNMEASURED` / `NOT ESTABLISHED`. NEVER as a null.** "Mostly gone", "might still be there", "not sure"
   are not zeros. If the table has no room for the hedge, the table needs another column, not a rounding.
2. **Every zero in a results table carries its exposure and its P(0), in the same cell.** A zero without
   them is not a result. See [[feedback-episodes-not-windows-and-the-noise-floor]].
3. **Match exposure on the PROVOKING covariate, not on wall-clock seconds.** 18 of 21 creep grind-#2
   bursts sit at |ang| ≥ 100°; a build with 200 s of straight-line creep has *no* exposure to the effect.
4. **When the operator contradicts the record, check the record's power before defending it.** In this
   case the record had ~19% power and he had days of driving. Ask what exposure his impression rests on
   before treating a measurement as the tiebreak.
5. **A summarised claim must carry the clause that makes it true.** The same session lost
   *"Only V62/V65 **and V71C** have ever produced bursts"* when transcribing a retraction into
   `docs/STATE.md:453`, which flipped its meaning. **Quote retractions whole or not at all.**

Related: [[accord-grind1-fix-and-grind2-are-collinear]] (the finding this produced),
[[accord-a-caveat-can-mutate-into-a-result]], [[accord-two-lane-rule-grind2]],
[[feedback-mean-and-tail-must-be-reported-together]].
