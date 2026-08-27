---
name: feedback-search-the-kit-before-naming-a-cause
description: "A cause named for a null must be checked against the kit's OWN measured record before it is proposed, not after. Naming 'the wrong mode record' for the V91/V92 null took one grep to refute — and a whole build proposal had already been argued from it."
metadata:
  type: feedback
---

# 🛑 SEARCH THE KIT'S OWN RECORD BEFORE NAMING A CAUSE FOR A NULL

**Instance, 2026-08-11.** V91/V92's `0xCBE74` dose measured inert. The orchestrator proposed
*"the engaged mode record is not 26/27 — the car reads mode 24 in both states"* as the leading
explanation, wrote it into a memory, into `BUILD-LINEAGE`, into a published artifact, and built an
entire V93 discriminator around it.

**It was refuted by a memory the kit already had**, found by one grep once the operator asked
*"how do we know these are the right modes?"*: `[[reference-accord-car-is-tvca4-mode-24-26]]` records
that **V73 probed the exact index byte `gp+0x63fd` over 104,061 frames** and watched it change
**8 manual → 10 engaged**, 18 transitions, all on engagement edges, 99.09 % lag-matched.
**The mode index demonstrably tracks engagement.** The hypothesis was dead before it was written.

**Why:** a null invites a cause, and the cheapest-sounding cause gets promoted to "leading
explanation" without being run against the record. RULE 7 (*mode-proof or it is a bet*) was cited
**in support of** the wrong answer, which is the tell — a rule invoked as decoration rather than
applied.

**How to apply:**
- **Before naming any cause for a null, grep `memory/` and `docs/` for the cells and the mechanism
  involved.** Cost: one command. It is cheaper than the proposal it protects.
- **Explicitly ask whether the kit has ALREADY MEASURED the thing you are about to assume.** This
  kit's failure mode is not missing data — it is not looking for data it already owns.
- **Enumerate the alternatives and trace each**, rather than promoting the first plausible one. Doing
  that here killed the mode hypothesis *and* both fallback branches, leaving the honest answer:
  **the null is UNEXPLAINED**, which is a better statement than a confident wrong one.
- ⊕ **A hypothesis that is cheap to refute is cheap to check.** Prefer refuting your own before
  presenting it.

⊕ **The operator's question is what caught it**, as with `[[feedback-run-the-control-before-the-measurement]]`.
Related: `[[accord-cbe74-dose-measured-inert-wrong-mode-record]]`,
`[[accord-check-build-lineage-before-proposing-lever]]`.
