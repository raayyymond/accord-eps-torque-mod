---
name: accord-lever-b-is-on-the-car-grind1-needs-something-new
description: "Byte-verified across 25 images plus stock: V112 (on the car) and V121 both CARRY Lever B, the kit's best measured grind-#1 fix (0x3AA96 = FB, 0xC6446 = 5244). The 'V81 carries neither fix' memory is specific to V81; Lever B was restored at V88 and is continuous from V90 except a real gap at V101/V102/V103 that V104 closed. Lever A is absent from all 25 builds, correctly, because its r24 half raised 40-49 Hz x11.7 and caused grind #2. So the remaining grind #1 is NOT a silently-lost fix - the best measured fix is deployed and the symptom persists, which means it needs something NEW."
metadata:
  node_type: memory
  type: reference
---

# ✅ LEVER B **IS** ON THE CAR — so the remaining grind #1 needs something NEW

## [EVIDENCE] Byte scan, 25 built images + stock, 2026-08-28
```
   build         0x3AA96       0xC6446      LEVER B?   |  0x3AB76  0x3AC20  LEVER A?
   STOCK         C5 stock      512  stock     no       |   AA       AA        no
   V90..V100     FB LKAS gate  5244 ARMED     YES      |   AA       AA        no
   V101,V102,V103  C5 stock    512  stock     NO  <-- a real gap
   V104..V121    FB LKAS gate  5244 ARMED     YES      |   AA       AA        no

   carrying LEVER B: 22 of 25      carrying LEVER A: 0 of 25
```
✅ **V112 (ON THE CAR) and V121 both carry Lever B** — the kit's **best measured grind-#1 fix**:
grind #1 **0.40 [0.27, 0.58]**, *and* creep grind #2 → **0 bursts** (P(0) = 0.0005), **mode-proof**.
🛑 **This corrects an alarm I raised from [[accord-v81-carries-neither-grind1-fix]].** That memory
is **specific to V81**. Lever B was restored at V88 ([[accord-v88-lever-b-restored]]) and has been
carried continuously since — the only later loss was **V101/V102/V103**, closed at V104.

## ✅ LEVER A IS ABSENT, AND THAT IS CORRECT
Lever A (V62's `sar` ×2, `0x3AB76` + `0x3AC20` `AA`→`A9`) measured grind #1 **0.39 [0.32, 0.48]** with
the operator reporting it *"gone"* — but **its r24 half raised 40-49 Hz ×11.7 and CAUSED grind #2.**
Lever B is equal-or-better on grind #1 **and** fixes grind #2. ⇒ **do not restore Lever A whole.**
⊕ Ghidra confirms the site: `0x3AC20` is `sar 0xa, r8`, bytes `aa42` (V850 is LE — the halfword
`0x42AA` is bytes `AA 42`; I got that backwards on the first pass).

## ⇒ THE ONE UNTESTED PIECE, AND ITS HONEST EXPECTED VALUE
**Lever A's r26 half alone — `0x3AB76` `AA`→`A9`, ONE byte — has never flown in isolation.** It is the
half that did **not** cause grind #2.
⚠ But [[accord-r26-is-structurally-inert]] records that claim as **SPLIT**: leg 1 (gate) REVERSED,
leg 2 (magnitude) **downgraded to BELIEF**. The kit leans toward r26 being inert, which would make
this a **no-op**. ⇒ **modest expected value; NOT proposed as a build on this evidence alone.**

## 🛑 THE CONCLUSION THAT MATTERS
**The remaining grind #1 is NOT a silently-lost fix.** The best measured fix is **deployed**, and the
operator still reports grind #1 *"rare, but still has its few moments in each drive."*
⇒ **Grind #1 needs a NEW lever, not a restoration.** ⊕ And it will not come from the relay knee:
[[accord-knee-has-no-measured-dose-response-on-grind1]]. ⊕ Nor from the base-assist damper:
[[accord-v80-damper-relay-and-grind1-inert]] shows grind #1 inert across k = 0.58 → 4.16.
Tool: `analysis-2020accord/verify/check_grind1_levers_across_builds.py`.
