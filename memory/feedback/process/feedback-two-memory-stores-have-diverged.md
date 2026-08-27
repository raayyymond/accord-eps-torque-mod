---
name: feedback-two-memory-stores-have-diverged
description: There are two distinct memory systems for this project — repo memory/ (387 files, what subagents read) and the auto-memory index (.claude/projects/.../memory/, 111 files, orchestrator-scoped) — and they have diverged. Cross-links between them dangle; a size warning about one is not a fact about the other. Cost real work three times in one session. 15 durable facts promoted 2026-08-13; specific casualties named below.
metadata:
  type: feedback
---

**Two distinct memory systems exist for this project, and they have DIVERGED.**

1. **Repo `memory/`** (this directory) — 387 files as of 2026-08-13. The kit's shared record.
   **This is the only store subagents can read.** `memory/MEMORY.md` is its flat index.
2. **Auto-memory** (`C:\Users\dudei\.claude\projects\C--Users-dudei-Desktop-Projects-accord-eps-torque-mod\memory\`)
   — 111 files. **Orchestrator-scoped** — belongs to the main conversation, not visible to subagents,
   and this session's record-repair agent was explicitly told never to write to it, only read from it.

**They are not kept in sync.** Content exists in one that the other doesn't have, under both matching
and non-matching filenames.

## 🛑 A concrete, load-bearing illustration: the conversation's OWN opening context was auto-memory
The very first system-reminder block a fresh session in this project receives — labelled "recalled
memories" — is drawn from the **auto-memory** store (explicitly, per its own system-prompt header:
*"user's auto-memory, persists across conversations"*), **not** from repo `memory/MEMORY.md`. Several
entries in that opening brief (e.g. *"V98 FLEW — the comparator ranked the observer arms"*, *"V88
FLEW — grinding FIXED"*) referenced memory files that, when actually checked against repo `memory/`
via the tools a subagent has, **did not exist there.** A session can be BRIEFED on a fact by its own
opening context and then be unable to find that fact's file when it goes looking.

## Why this recurred THREE TIMES in one session, and what each casualty cost
1. `feedback-run-the-control-before-the-measurement` — cited when writing the cabin-microphone
   memory's "how to apply" section (a genuinely relevant cross-reference: *"run the control before the
   measurement; four claims died to controls in one session"*). Link dropped rather than shipped dead.
2. `reference-accord-c520c-cap-table-axis-provenance` — cited when writing the `MEMORY_CONSTELLATION.md`
   entry about the `0xC6200` mislabelling lesson (a genuinely relevant precedent: a cap-table's INDEX
   provenance had to be separately settled once already). Link dropped rather than shipped dead.
3. `accord-4x-lkas-gain-is-the-frozen-variable` — **this one was NOT caught in time.** It is cited as a
   live `[[link]]` in `docs/archive/arc-maps/_v100_arc_map.md` (this session's own arc-map deliverable) and in
   `docs/research/RESEARCH-2026-08-10-lkas-torque-self-cancellation.md` and two other repo memory files —
   **written by multiple different sessions, over multiple days, all assuming the file existed in
   repo `memory/`, and it did not until this correction.** A size warning ("`memory/MEMORY.md` is
   24.8 KB against a 24.4 KB limit") reported early in this session about the auto-memory index was
   at one point read as if it applied to the repo `memory/MEMORY.md` (167 KB) — **a size fact about
   one store is not a fact about the other; check which store a number is about before acting on it.**

## What was done about it, 2026-08-13 (later still)
Enumerated every file present in auto-memory but absent from repo `memory/` — **24 files**. Of those:
- **15 were genuinely durable technical/reference facts with no repo coverage and were PROMOTED**
  (copied verbatim, same filename so existing `[[links]]` resolve, indexed in `MEMORY.md`): the four
  above plus `accord-869hz-line-is-wheel-order-not-v56`,
  `accord-fprime-compression-explains-v89-and-v97` (the session's own central `f′`-compression
  account — had NO repo backing despite being load-bearing throughout this session's handoff and
  `STATE.md`), `accord-ratchet-is-a-lightly-damped-resonance` (the Q 14-29 finding
  `BUILD-LINEAGE.md`'s V86 row already asserts as settled, with no memory file behind it),
  `accord-raw14-offbyone-in-every-cache`, `accord-v57-confirms-wheel-order-tyre-line`,
  `accord-v87-flew-the-probe-fired-and-6b98-is-broadband`, `accord-v88-flew-grinding-fixed-command-intact`
  (the grinding-fixed finding — arguably the kit's single best result, had NO repo memory file),
  `accord-v88-lever-b-restored`, `accord-v98-comparator-ranked-the-observer-arms` (this session's
  own central V98 finding, cited constantly, had NO repo file), and
  `reference-accord-lkas-only-rate-limiter-c6194`.
- **8 were skipped as duplicates** — a same- or similar-named repo file already covers the identical
  fact, confirmed either byte-identical (`accord-engagement-amplifies-6-9hz`,
  `accord-v89-built-plant-model-friction`) or as a clearly later/corrected version under a different
  name (`accord-friction-polarity-more-assist`, `accord-leverb-discriminator-underpowered`,
  `accord-ratchet-axis-is-wheel-rate`, `accord-takeover-beep-is-device-load`,
  `eps-telem-red-panda-same-usbc-works` — content-diffed against
  `misc/eps-telem-red-panda-cannot-poll-during-lkas.md` and confirmed the repo version is the corrected
  successor, not a conflicting claim — and `v53-fourframe2-plus-minsteerspeed0`, superseded by the
  3× larger `project-`-prefixed repo version).
- **1 was skipped as a REFUTED claim, deliberately** — `accord-damper-cannot-reach-micro-regime`
  (auto-memory's original, un-corrected version of the claim this session already found and REFUTED
  in repo `memory/accord/calibration/accord-base-assist-damper-cannot-reach-the-micro-regime.md`, a differently-named
  file). **Promoting the auto version would have reintroduced a claim already disproven from the
  images this same session.** This is the sharpest edge of the divergence problem: it is not merely
  that facts go missing, it is that a STALE, SUPERSEDED version of a fact can sit in one store while
  the CORRECTED version lives only in the other, and a naive promotion pass would silently regress
  the record. **Always check whether a same-topic fact already exists under a DIFFERENT name in the
  target store, and if it does, read both before deciding which survives.**

## 🛑 A FOURTH cost, not a casualty but a tax paid all session: briefs went inline instead of by pointer
Because the orchestrator's own opening context comes from auto-memory (§ above), **every brief this
session wrote to a subagent that relied on a fact only auto-memory held had to hand that fact inline,
in the message itself, rather than as a `[[link]]` or a "read `memory/X.md`" pointer** — the pointer
would have resolved to nothing for the subagent receiving it. This is invisible in the moment (the
subagent gets the fact either way) but it is why several briefs this session read as long inline
restatements of findings instead of short pointers to a shared file: **the shared file didn't exist
yet.** Now that the 15 promotions have landed, future briefs on those topics can go back to being
pointers.

## How to apply — the remediation, so a future session does not re-derive it
- **A dangling `[[link]]` inside repo `memory/` is not proof the fact doesn't exist** — check
  auto-memory before concluding it was never written, and check whether a differently-named repo file
  already covers the same ground before promoting.
- **Never write to auto-memory from a subagent context** — it is orchestrator-scoped. Promotion is
  **one-directional: auto → repo, copy, never the reverse.**
- **Verify a `[[link]]` actually resolves to a file in repo `memory/` before relying on it or citing
  it to a subagent** — its presence in an opening brief, in `MEMORY.md` prose, or in another memory
  file's own `[[links]]` is not evidence it exists on disk in the store subagents read. Check the
  file, every time, before treating the link as load-bearing.
- **When a fact exists in BOTH stores under the same or a related name, DIFF them — do not assume the
  newer-modified store holds the newer fact.** This session's worked example: `eps-telem-red-panda-*`
  had the CORRECTED version in repo and the superseded draft in auto-memory; `accord-damper-cannot-
  reach-micro-regime` had the REFUTED version in auto-memory and the correction already applied in
  repo under a different filename. Which store is "ahead" varies fact by fact — check content, not
  mtimes or which store you happen to be looking at first.
- **A size or count reported about one store is not a fact about the other.** State which store a
  number describes.
- This reconciliation was not exhaustive of every possible future divergence — only of the 24-file gap
  measured on 2026-08-13. Re-run the enumeration (`comm -23` on the sorted basename lists of both
  directories) at any future close-out where memory content feels inconsistent with what a session was
  briefed on at start.
