---
name: feedback-name-superseded-hashes-dead-not-merely-omitted
description: "A VERIFIED artefact for a SUPERSEDED design is MORE dangerous than an unverified one — everything about it looks correct, including its assertion log. A hash reported in a transcript outlives the artefact it names. When a build is re-cut, the superseded hashes must be explicitly named DEAD in the record, not merely omitted from it. Stripping them from the docs is necessary and NOT sufficient: omission is invisible, a DEAD marker is not."
metadata:
  type: feedback
---

# Name superseded hashes DEAD — omitting them is not enough. 2026-08-11.

> **A VERIFIED ARTEFACT FOR A SUPERSEDED DESIGN IS *MORE* DANGEROUS THAN AN UNVERIFIED ONE, NOT LESS.**
> Everything about it looks correct — **including its assertion log.**
> **A hash reported in a transcript OUTLIVES the artefact it names.**

**Why:** a future session greps the transcript, finds a SHA256 with **every assertion passing**, and
has no way to tell the artefact is dead. Nothing about a passing log says "this design was replaced".

## The rule

**When a build is re-cut, the superseded hashes must be EXPLICITLY NAMED DEAD in the record — not
merely omitted from it.** Put a marked block in the handoff *and* the `BUILD-LINEAGE.md` row giving:
the dead hashes, what design they carried, what superseded them, and the `SUPERSEDED-DO-NOT-FLASH-…`
filenames they now live under.

🛑 **Stripping the stale hashes from the docs is NECESSARY AND NOT SUFFICIENT.** **Omission is
invisible; a DEAD marker is not.**

🛑 **AND WRITE THE DEAD HASH OUT IN FULL, next to the word DEAD.** The search that will actually be run
is a **paste of the full 64-char string out of the transcript**. A truncated or prefix-only entry
(`b092bf19…`) returns **nothing** for that search — so the marker fails at exactly the moment it is
needed. This is a real failure mode: the first pass of this very correction used truncated forms only.

⊕ **Corollary for the `SUPERSEDED-DO-NOT-FLASH-…` rename this kit already does:** the rename fixes the
**filesystem** and does nothing for the **transcript**. **Both need doing.**

## The instance

A **real, fully-verified V92 cut** — **182/182 assertions, from-disk verified**, image `b092bf19…`,
rwd `630248a5…` — carried the **OLD rung map** (`b4 = sign(gp-0x6abc)`, a 110 B cave, no 427 `sar`
fix). It was superseded before flight by the `gp-0x6bda`-in-window swap and the `0x55E10`
`a332`→`a432` no-clip fix, and **never flew.**

The collaterals correctly stripped those hashes. **But they were live in the session transcript with a
complete passing assertion log**, and **the only tell left was a `6ABC` token buried in the old
filename** — which reads as a warning only to someone who already knows a swap happened.

Files renamed on disk to
`SUPERSEDED-DO-NOT-FLASH-_v92_OLDRUNGMAP-b4.6ABC-NEVER-FLOWN_plain_image.bin` and
`SUPERSEDED-DO-NOT-FLASH-39990-TVA,A160-V92-OLDRUNGMAP-b4.6ABC-NEVER-FLOWN-0x13000-0x100000.rwd`.

⊕ **How the catch was made, because the pattern is the point:** the **BUILDER** caught it itself and
**pushed back on the orchestrator's own proposed filename, which had mischaracterised the superseded
artefacts as a "dry run".** They were not a dry run — they were a real cut, **and that distinction is
the entire hazard.** Same shape as the rest of this session's catches: the correction came from the
agent that **owned** the artefact, against the orchestrator's description of it.

Related: [[accord-recut-overwrites-the-previous-plain-image]] (the sibling filesystem hazard — a re-cut
under the same build number destroying its predecessor's image) ·
[[accord-check-build-lineage-before-proposing-lever]] ·
[[reference-accord-cbe74-friction-row-zero-clean-flights]] (the "two artefacts share a build number and
a glob answers the opposite question" case)
