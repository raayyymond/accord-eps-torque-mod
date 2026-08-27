---
name: feedback-exposure-law-contiguous-blocks-not-total-seconds
description: Resampling/bootstrap block count comes from CONTIGUOUS engaged seconds per episode, not total engaged seconds summed across episodes — three primary endpoints (V89, V97, V99) died to this, and it is a drive-protocol fix, not a build fix.
metadata:
  type: feedback
---

**The block count a block-bootstrap can extract is set by the LONGEST CONTINUOUS engaged run(s), not
by total engaged time summed across fragmented episodes.** Route 82 (V99)'s 59.8 s split across four
episodes (15.9 / 31.3 / 2.5 / 10.1 s) gave only **12–14 blocks**; route 81 (V98)'s 65.9 s in three
episodes gave **21** — a smaller total exposure produced MORE usable blocks because it was less
fragmented. [EVIDENCE, `scorer-v99`, `docs/traces/TRACE-2026-08-13-v99-flight-score.md`]

**Why:** each resampling block needs a run of contiguous seconds at least as long as the block length
(typically ~5 s). A 2.5 s episode contributes ZERO full blocks no matter how many other episodes exist
elsewhere in the drive. Fragmenting engaged time into short episodes — stopping and restarting LKAS,
brief hands-on interruptions, traffic stops — silently starves the primary endpoint's statistical power
even when the drive's total engaged-seconds figure looks adequate on paper.

🛑 **Three builds in a row have had their primary endpoint die to this: V89, V97, V99.** In each case
the build itself was not the problem — the DRIVE PROTOCOL was. Roughly doubling the block count at
identical total exposure just requires ONE continuous ~60 s engaged episode instead of several short
ones.

**How to apply:** this is a standing drive-protocol requirement, not something a build's own design can
fix. When briefing the operator or writing a drive spec, ask for **one sustained engaged episode of at
least the block length × the number of blocks the endpoint needs** (typically ~60 s), rather than
"X total engaged seconds spread over the drive." If a route report gives total engaged seconds without
episode boundaries, treat the usable block count as UNKNOWN until the episode list is checked — do not
assume total-seconds ÷ block-length is achievable.

Related: [[feedback-episodes-not-windows]] (the sibling finding that WINDOW bootstraps over-claim
significance; this is the companion finding that EPISODE bootstraps are starved by fragmentation, not
by total exposure).
