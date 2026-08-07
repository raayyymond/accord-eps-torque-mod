---
name: accord-c63a0-exonerated-of-the-hard-faults
description: The standing directive "do not double 0xC63A0, that is what caused the hard faults" rests on a false premise — there is NO firmware data path from 0xC63A0 to gp-0x6b26 or to any monitor. 0xC407E is the whole fault story. 0xC63A0 remains a real Path-2 loop-gain lever, which is a different question.
metadata:
  type: reference
---

# 🛑 `0xC63A0` IS **EXONERATED** OF THE HARD FAULTS — the premise is refuted on evidence

**The record must carry both halves of this.** A standing operator directive exists and is quoted
verbatim in `build_v80_tva.py`:

> *"Do not double `0xC63A0`, that is what was causing the hard faults."*

**The premise is FALSE.** [EVIDENCE, orchestrator's own Ghidra work 2026-08-07]

## The trace
- `0xC63A0` = `tp+0x73A0` has **exactly ONE reader** — `ld.hu` @`0x381AC` — **0 writers, 0 disp23 hits.**
- That reader, `FUN_00038148`, **writes exactly two cells**: `gp-0x374c` (its own accumulator) and
  `gp-0x6b70` (its output). It **never** writes `gp-0x6b26`, `gp-0x6c2c` or `gp-0x6a5e`.
- `gp-0x6c2c`'s two writers are both inside `FUN_00041464` (`0x4184E`, `0x41AC2`).

⇒ **There is NO firmware data path from `0xC63A0` to the faulting monitor.** A *physical* path exists
(aggregator → motor → plant → motor rate → `gp-0x6c2c`) and is **irrelevant**, because the clamp at
`0xC407E` acts **before** the store that the monitor reads
([[accord-friction-lane-ceiling-is-the-hard-fault]]).

★ This is the **fourth** monitor surface now shown blind to `0xC63A0`; the other three were already
established in [[accord-v77-cannot-reach-the-monitors]], which explicitly left *"a fourth surface is not
formally excluded."* **It is excluded now.**

## 🛑 Keep the two questions apart — this is NOT "0xC63A0 is inert"
| question | answer |
|---|---|
| Does `0xC63A0` move **delivered torque**? | **YES** — it is the damper's Path-2 weight into a
gain-scheduled PID ([[accord-path2-is-a-closed-firmware-loop-and-c63a0-weights-it]]) |
| Does it move what **any monitor compares**? | **NO — all four surfaces** |
| Did it cause the V74/V75 hard faults? | **NO. `0xC407E` = 850 did.** |

⇒ Raising `0xC63A0` is a **GATE 2 loop-gain decision**, to be argued on magnitude and phase — **not a
fault-safety decision**. "Do not raise it" may still be a sound *caution*; the *reason on record* is not.

⚠ **Its history could never have separated the two anyway**: V72/V73 carried 2048 with a structurally
**zero** damper (`2 × 0 = 0`), so the weight was functionally inert until V74 armed the damper. That
confound is what let a false premise survive four builds.

⊕ `build_v80_tva.assert_c63a0_block` still hard-asserts 1024 **with the old rationale in its comment**.
The assertion is harmless (V80 is a different lineage); **the comment is known-wrong and should be
corrected.** Recorded here so a future reader of that file does not re-import the premise.

📋 **DURABLE RULE: a directive that names a *cause* is a claim, and claims get verified.** This one had
been carried across six builds and into two build scripts without anyone tracing the cell to the monitor.

Related: [[accord-friction-lane-ceiling-is-the-hard-fault]] · [[accord-v77-cannot-reach-the-monitors]] ·
[[accord-v77-built-c63a0-revert]] · [[feedback-verify-the-crux-yourself-it-caught-four-errors]]
