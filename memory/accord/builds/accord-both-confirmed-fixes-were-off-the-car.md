---
name: accord-both-confirmed-fixes-were-off-the-car
description: "🛑🛑 2026-08-04: byte-reading all 60 built images showed the car had been carrying NEITHER of the kit's two confirmed fixes since V66 — V42's 0x454FE ratchet kill was lost in a silent rebase at V53, and V62's 0x3AB76/0x3AC20 grind-#1 fix was removed as V66's control and never restored. This is what RULE 3 exists for."
metadata:
  type: reference
---

# 🛑🛑 BOTH CONFIRMED FIXES HAD FALLEN OFF THE CAR — and the record read as though they were on it

**[EVIDENCE — byte-read across all 60 `_v*_plain_image.bin` in `../accord-firmwares/analysis-2020accord/`.]**

| lever | what it did | recorded as | actually carried by | how it was lost |
|---|---|---|---|---|
| **`0x454FE`** `65BA`(`bne`) → `65B5`(`br`) | V42's **state-4 governor ratchet** kill | *"CONFIRMED ROOT CAUSE, carry forward"* | **V42–V52C only**; **stock in V53 → V70** | 🛑 **silent rebase loss** — V53+ descends from the V38/FOURFRAME branch point, which is *before* V42. **Nobody decided this** |
| **`0x3AB76` + `0x3AC20`** `sar 0xa` → `0x9` | V62's **×2 on BOTH rate lanes** — the kit's only measured grind-#1 fix (8× at creep, 42× at \|rate\| 16–32) | the reference "2×" rung of the dose ladder | **V62 and V65 only** | ⚠ removed as **V66's confirmatory control**, **never restored** |

⇒ **From V66 to V70 the car carried NEITHER**, across ten builds of reasoning.

## Why `0x454FE` is worse than bookkeeping
The argument that later retired it as a cause of the *current* ratchet — *"`STEER_STATUS == 4` fires
0/37,922"* — was **VOIDED** when bus `STEER_STATUS` was shown not to be `gp-0x67fa` (state 4 sits inside
all three gate masks; [[accord-gp67fa-state-gate-on-assist-chain]]). **It was never actually
eliminated** — it was mis-eliminated, then mis-recorded as absent-because-unnecessary.

## Why `0x3AB76`/`0x3AC20` is the more dangerous general form
A lever removed **on purpose** as an experimental control is, six builds later, **indistinguishable from
a lever that was never needed**. And the effect was then re-created twice in encodings that dose **r24
only** (V67/V68's arm; V69/V70's surface) while the ladder kept calling those "2×" —
see [[accord-r24-r26-two-selectors-one-gate]] for why those were never the same quantity.

## The two rules this leaves behind
1. 🛑 **`RULE 3`, now at the top of `docs/BUILD-LINEAGE.md`: for every lever you cite, byte-check
   whether the CURRENT build's plain image still carries it before reasoning from its result.**
   A confirmed fix that is no longer carried is not evidence about the car you are driving.
2. **When you remove a confirmed fix to run a control, write the restore into the next build's spec.**

⏳ **Both are restored in V71** (`0x454FE` `ba`→`b5`; `0x3AB76`/`0x3AC20` `aa`→`a9`), whose rate lane is
therefore **byte-identical to V62/V65** — flown twice, both flight-clean.
🛑 **State the `0x454FE` justification honestly: restored because it is a confirmed fix lost by
ACCIDENT, not because it is established to cause the current ratchet** — the substitution is
**asymmetric** while the ratchet measures **symmetric**
([[accord-state4-cadence-refuted-state-is-sticky]]).

See [[accord-check-build-lineage-before-proposing-lever]], [[accord-v62-flashed-grinding-is-fixed]],
[[accord-v70-flew-grind1-back-at-stock]].
