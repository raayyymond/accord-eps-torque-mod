---
name: accord-k1-and-knee-are-perfectly-confounded
description: "Every flown build holds K1/knee = 0.34 exactly - K1=204 with knee 300 or 600, and K1=612 with knee 1800 - so no knee value has ever been flown at two K1 values and the kit has never learned which of the two matters. V121 keeps the same ratio, so by construction it cannot separate them either: if it works we will not know why, and if it fails we will not know which half failed. The cause is structural, since holding the small-signal gain constant REQUIRES K1 proportional to knee. V113 (knee 1800, K1 204) is the only built artifact that breaks the confound, at the cost of dropping the small-signal gain to 0.333x V112's."
metadata:
  node_type: memory
  type: reference
---

# 🛑🛑 `K1` AND `knee` ARE **PERFECTLY CONFOUNDED** ACROSS EVERY FLOWN BUILD

## [EVIDENCE] Byte-read from every flown image
```
   K1=204  knee= 300   ->  V100 V101 V102 V103 V104 V105 V106 V107     ratio 0.68
   K1=204  knee= 600   ->  V90 V91 V92 V96 V111                        ratio 0.34
   K1=612  knee=1800   ->  V112                                        ratio 0.34
   STOCK:  K1=102 knee=600                                             ratio 0.17

   knee values flown with MORE THAN ONE K1:  NONE
```
⇒ **the kit has never learned which of the two cells matters.** Every result attributed to "the
knee" is equally attributable to `K1`, and vice versa.

## 🛑 THIS IS A DESIGN CRITIQUE OF **V121**
V121 is `knee 3000 / K1 1020` — **ratio 0.34, a fourth point on the same line.** ⇒ **by construction
it cannot separate them.** *If V121 works we will not know why; if it fails we will not know which
half failed.*
✅ **The cause is structural, not an oversight:** holding the small-signal gain
`(K1/1024)(12/knee)` constant **requires** `K1 ∝ knee`. **A gain-matched build is inherently
confounded.** ⇒ separating them **requires accepting a gain change.**

## ⇒ THE ONLY ARTIFACT THAT BREAKS IT
**V113** = `knee 1800 / K1 204` — the same knee as V112 at the same K1 as V90-V111. Flown against
V112's existing data it gives **two K1 levels at one knee, the first separation ever.**
⚠ **Cost: small-signal gain 0.0013281 = 0.333× V112's**, below stock's 0.500× ⇒ noticeably less
friction compensation, and **more modelled friction = MORE assist**
([[accord-friction-polarity-more-assist]]), so V113 means **less assist**.
⊕ The mirror experiment — `knee 600 / K1 612` — would give **3×** V112's gain and is the riskier
direction; **V113 is the safer half of the pair.**

## ⇒ THE HONEST CHOICE, STATED AS A TRADE
```
   V121   gain-matched, feel preserved, MORE assist above 31.8 deg/s   -- but CONFOUNDED
   V113   separates K1 from knee for the first time                    -- but 0.333x gain, LESS assist
```
✅ **V121 remains the right FIRST flight** — it is the only candidate that cannot make the car worse
in normal driving (bit-identical ≤ 31.8 deg/s) and it tests the pre-registered endpoint.
✅ **V113 is the right SECOND flight if V121 moves the endpoint at all** — it is the only way to learn
which cell did it. **If V121 lands in the "not resolved" band, V113 is not worth its feel cost.**
🛑 Recorded so the sequencing is deliberate rather than emergent.
