---
name: feedback-constant-field-is-not-a-void-cave
description: A probe field that reads CONSTANT does not mean the cave never fired -- only a constant ZERO does, and only when 0 is unreachable in the probed cell's value set. The looser wording misled this kit's orchestrator directly on 2026-08-06.
metadata:
  type: feedback
---

# 🛑 A CONSTANT probe field is NOT a void cave — only a constant **ZERO** is

**This misled the orchestrator on route 5d, 2026-08-06, and nearly produced a "V74 was a void drive"
headline on the kit's first successful damper build.**

## The correct rule
V74's probe puts `bits 6:3 = gp-0x67fa & 0xF`. `gp-0x67fa`'s complete value set is
`{1,3,4,5,6,7,8,9,10,11}` — **0 is unreachable** (all 33 writers store literals). Therefore:

- `bits 6:3 == 0` **for a whole drive** ⇒ the cave never fired ⇒ **VOID**, nothing else is interpretable.
- `bits 6:3 == 5` for a whole drive ⇒ the cave **DID** fire and the cell is genuinely pinned at 5.
  **That is a measurement, not a null.**

On route 5d the field read **5 on 101,117 frames and 4 on 1** — the one state-4 frame being the last
frame of the route, at vEgo −0.0, in PARK.

## What the tool actually does — it was never wrong
`decode_v74_probe.identify()` implements the rule correctly:
```python
states = seen
if states == {0}:      # <- constant ZERO, not "constant"
```
and its docstring's HOW-TO-READ table says `bits 6:3 constant 0 => VOID`. Run on route 5d it printed
`✅ not excluded as V74: states seen [4, 5], bit7 duty 23.342%` and produced a full report.

## Where the bad wording lived — ✅ BOTH FIXED 2026-08-06
1. `rlog-tools/decode_v74_probe.py`, the comment at `STATE_SHADOW_DISP`, read *"0 IS UNREACHABLE, so a
   CONSTANT `bits 6:3` means THE CAVE NEVER FIRED"* — it **dropped the `== 0`**. Now reads
   *"a CONSTANT ZERO `bits 6:3` field"*, with the reason for the fix recorded inline.
2. `docs/STATE.md` carried the same sentence. Removed.

Both were written to guard against V64/V68's uninterpretable nulls
([[feedback-probe-the-gate-not-just-the-output]]), and **the guard was always right — the code tested
`states == {0}` correctly throughout.** Only the prose was wrong, and prose is what a human reads first.
🛑 **That is the transferable lesson: a correct implementation does not protect you if the comment above
it states a stronger rule.** When a guard's condition is subtle, the comment must restate the *exact*
predicate, not a paraphrase.

## How to apply
- **State the probed cell's value set alongside any liveness claim.** "Constant" is meaningless without
  it: constant-0 is void *only because* 0 is unreachable; constant-5 is informative *because* 5 is legal.
- **Prefer the direct inference.** `5 ≠ 0 and 0 is unreachable ⇒ the cave fired` needs no other bit. The
  orchestrator's route to the same conclusion — *"bit7 varies, so the store must be executing"* — is
  sound but weaker: it depends on a second field and on the single-store argument.
- **Design payloads so the two cases cannot be confused**, which is exactly what V74's structural
  liveness achieved and what V64/V68 lacked.

Related: [[feedback-probe-the-gate-not-just-the-output]] · [[accord-v74-flew-damper-is-in-force]] ·
[[accord-gp67fa-state-gate-on-assist-chain]] · [[accord-state671a-is-an-oscillation-detector]]
