---
name: accord-v42-permanently-deletes-hondas-state4-governor
description: "V42's 0x454FE ba->b5 turns a conditional bne into an UNCONDITIONAL br, so the jarl to FUN_00049A5A - Honda's state-4 governor routine - is NEVER called on any build from V42 onward. Not a tuning change: a permanent deletion of a control element from the torque loop, present in every build showing the 7-9 Hz excess and absent from stock. Its duty is UNMEASURED and a blind revert risks returning the macro ratchet V42 fixed. Separately, the 164-byte cave is verified GATE-1 write-clean and eliminated."
metadata:
  node_type: memory
  type: reference
---

# 🛑🛑★★★★★ `0x454FE` **PERMANENTLY DELETES** HONDA'S STATE-4 GOVERNOR CALL

2026-08-27, decoded in Ghidra (my own hand-decode of the displacement was wrong — it branches
**forward** to `0x455C4`, not backward).
```
  0x454F8  ld.bu -0x67fa,gp,r12    ; the assist-chain state
  0x454FC  cmp   0x4, r12          ; state == 4 ?
  0x454FE  bne   0x000455C4        ; STOCK: if state != 4, skip the call
  0x45500  jarl  0x00049A5A, lp    ; state == 4  ->  CALL Honda's state-4 routine
```
**V112 (and every build since V42) has `br` in place of `bne`** ⇒ the branch is **unconditional** ⇒
**`FUN_00049A5A` is NEVER CALLED.**
🛑 **This is not a tuned threshold. It is a Honda control element deleted from the torque loop.**

## WHY IT MATTERS FOR THE 7–9 Hz EXCESS
It satisfies every requirement the excess imposes, which nothing else surviving does:
- **code, inside the governor** (`FUN_0004503c`, the stage clamping the combined command) — in the loop;
- **absent from stock, present in EVERY build showing the excess** (V42 onward covers V90…V112);
- **state-gated on `gp-0x67fa`**, so engagement-conditional and **command-independent**;
- it **removes** something rather than scaling it, which is what a *new* anti-damped feature needs.

## ⚠ WHY A BLIND REVERT IS NOT THE MOVE
`0x454FE` `b5` → `ba` is a one-byte revert, but **V42's change is a validated FIX**: the state-4
substitution *"forbids command-magnitude increase, cumulatively"* and was the confirmed root cause of
the V38-era macro ratchet ([[reference-accord-state4-governor-ratchet]],
[[v42-flashed-ratchet-fixed-r26-falsified]]). Reverting very likely returns that ratchet, which the
operator would feel immediately and badly.
🛑 **AND ITS DUTY IS UNMEASURED.** `gp-0x67fa` is not on the CAN bus (`STEER_STATUS` is **not**
`gp-0x67fa`) and no cached build telemeters it, so **how often state 4 occurs is unknown.** If state 4
is rare the deletion cannot explain a pervasive 7–9 Hz feature; if it is common it is the best
candidate on the table. **Measure before reverting.**
✅ **The cheap next step is a PROBE, not a revert**: one cave rung on `gp-0x67fa == 4`, which the
164-byte cave has room for and which costs no dynamics change at all.

## ✅ AND THE CAVE IS ELIMINATED — verified byte-by-byte
The 164-byte cave at `0xC4B34` was the other code-class candidate. Decoded with the correct V850
opcode map (`0x38` ld.b, `0x39` ld.h|ld.w, `0x3A` st.b, `0x3B` st.h|st.w — an earlier naive scan had
`0x39` as a store and was wrong):
```
  READS : gp-0x6B94, gp-0x4F64, gp-0x6AE2, gp-0x6B26, gp-0x6B4C, gp-0x6ADA, gp-0x3680
  STORES: gp-0x1514 (x3), gp-0x1512   -- the CAN 0x14A TX buffer, and NOTHING else
```
🛑 **No store outside the CAN buffer ⇒ GATE 1 clean ⇒ the cave cannot perturb control.**
**Eliminated as a cause of the 7–9 Hz excess.**

## THE INTERSECTION NOW
Edits common to every affected build, after eliminations: **`0x454FE`** (this note), the **V57 gain
repoint** (`0x2A1F0`, 891 → 5346 — inseparable from "being modified at all"), the **LKAS ceiling
raise ×1.067**, and ~20 cal cells. ~~the cave~~ ~~the biquad~~ are out.
