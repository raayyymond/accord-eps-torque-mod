---
name: accord-path2-is-a-closed-firmware-loop-and-c63a0-weights-it
description: gp-0x6bd0 reaches the motor by two routes. Path 2 (FUN_00038148) is a CLOSED FEEDBACK LOOP inside the firmware — gp-0x6b98 re-enters it one sample later via FUN_0003b8f6. 0xC63A0 is the odd-one-out of six sibling weights, mode-proof, moved to 2048 by V72 and never reverted until V77 — but it does NOT touch the re-entry term.
metadata:
  type: reference
---

# ★★★★ PATH 2 IS A CLOSED LOOP **INSIDE THE FIRMWARE** — and `0xC63A0` weights it

`gp-0x6bd0` (the base-assist damper output) reaches the motor by **TWO** routes.

## Path 1 — `FUN_0003aa2c`, the aggregator
**Unity weight, zero phase.** This is the route that actually **delivers the damping**. Nothing here is
a lever; it is a plain summand.

## Path 2 — `FUN_00038148` stage 1
Mirrors the decompiled arithmetic exactly (V850 LE, integer `>>`):

```
# stage 1: six gated terms, plain ADD, NO subtraction anywhere
acc = 0
for (x, gate, w) in six_terms:                 # w = one of 0xC63A0 .. 0xC63AA
    acc += (x * gate * w) >> 10                # Q10

target = (acc * polarity_gp_0x6752
              * 2639) >> 10                    # 2639 = *(u16) (tp + 0x7468) = 0xC6468

# 1 kHz IIR, corner 16.70 Hz
state += ((16 * target - state) * 102) >> 10   # 102 = *(u16) (tp + 0x73ac) = 0xC63AC

# -> stage 2 -> gp-0x6b70 -> FUN_00037fe6 -> gp-0x6ad6
#            -> FUN_0003a382 (the PID) -> back into the aggregator -> gp-0x6b98
```

## ★★ AND `gp-0x6b98` RE-ENTERS PATH 2 ONE SAMPLE LATER
via **`FUN_0003b8f6`** ⇒ **Path 2 is a closed feedback loop inside the FIRMWARE, not through the plant.**

`FUN_0003b8f6` runs at **`0x2240e`**, *before* the governor at `0x229ce`, in the **same 1 kHz tick** — so
it is a **clean one-sample delay**, not an algebraic loop. That is the good news; the bad news follows.

🛑 **`0xC63A0` does not touch the `gp-0x6b98` re-entry term at all, and that term may dominate the loop
gain. This is OPEN and it is the highest-value next trace.**

## ★★ `0xC63A0` is the ODD ONE OUT of six sibling weights

`0xC63A0` = `tp + 0x73a0`, **u16, Q10**. Its five siblings `0xC63A2 .. 0xC63AA` are all stock **1024**.

- It is the **only one any build has ever moved**: **V72 set it to 2048** and **no build reverted it
  until V77** ([[accord-v77-built-c63a0-revert]]).
- **Mode-proof bare `tp` scalar** ⇒ **live in MANUAL and ENGAGED** — which is why it is a candidate for
  a manual-mode fault ([[accord-v74-hard-faulted-in-manual-over-a-bump]]) and why RULE 7 does not apply
  to it ([[feedback-rule7-mode-proof-or-a-bet]]).
- **1 reader (`0x381AC`), 0 writers, no monitor, no float mirror** — two-method null.
- **Reverting 2048 → 1024 is −6.02 dB, zero phase, and costs Path 1 nothing.**

## ⚠ Its gate is a ZEROING gate, not a clamp
`|gp-0x6bd0| > 2048` ⇒ **the whole term × 0**, not a saturation. Telemetry never exceeded ~448, so the
gate has always been open — **but it is a cliff, not a knee.** Any lever that raises `gp-0x6bd0` toward
2048 must be priced against a discontinuous drop-out, not a graceful roll-off.

🛑 `BUILD-LINEAGE.md`'s claim that this chain is *"all unity and stock, no hidden loop gain"* is **FALSE**
and was already flagged by [[reference-accord-v74-v75-damper-is-a-sampled-relay]].

Related: [[accord-v77-built-c63a0-revert]] · [[reference-accord-fun3a382-is-a-real-pid]] ·
[[accord-damper-fixes-the-grind-but-is-flat-on-the-ratchet]] ·
[[feedback-explain-with-python-mirroring-decompiled-arithmetic]]
