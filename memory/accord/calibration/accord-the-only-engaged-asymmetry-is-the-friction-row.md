---
name: accord-the-only-engaged-asymmetry-is-the-friction-row
description: "Byte-verified by dereferencing each pointer array at arr+mode*4: of fourteen mode-indexed families, exactly ONE differs between mode 24 (manual) and mode 26 (engaged) on V112 and V121 - the friction row at 0xCBE74. Everything else, including the FactorC/E damper that V74-V81 armed, is byte-stock and symmetric. The engaged row escalated x1.5 at V91 and x3.0 at V107, and the V107 step also changed its SHAPE: Y[2] is 8.14x stock against 3.0x at Y[0], flattening a curve that stock decays 5.0x across. Flags that 3.0x exceeds the int32 wraparound point of 1.6005x on which the kit CLOSED this lever - unverified, and worth checking on the build that is on the car."
metadata:
  node_type: memory
  type: reference
---

# ⭐⭐ THE **ONLY** ENGAGED-VS-MANUAL ASYMMETRY LEFT IS THE FRICTION ROW

## [EVIDENCE] Fourteen mode-indexed families, dereferenced at `arr + mode*4`
```
   family        STOCK m24!=m26   V112 m24!=m26   V112 vs STOCK
   FactorB/C/D/E     same             same          byte-stock
   ceiling           same             same          byte-stock
   r24 gainB a-d     same             same          byte-stock
   boost curve/amp/ceil same          same          byte-stock
   friction 0xCBE74  same          ** DIFFERS **    EDITED      <-- the ONLY one
```
✅ **The V74-V81 engaged-only FactorC/E damper is GONE** — V90 onward is byte-stock and symmetric,
`Y[0] = 0`, Honda's own ramp. [[accord-v80-damper-relay-and-grind1-inert]]'s standing recommendation
*"restore the RAMP, don't merely lower k"* **is already satisfied** and needs no build.
⇒ **Every engaged-vs-manual asymmetry on the current car is either the friction row or a CODE gate**
(Lever B's LKAS gate). That is a short list, and it matters because
[[accord-engagement-amplifies-6-9hz]] measures engagement multiplying the 6-9 Hz band **2.8×**.

## ⭐ THE ROW ESCALATED TWICE — and V107 changed its SHAPE, not just its scale
```
   build         m24 (MANUAL)              m26 (ENGAGED)               Y[0] ratio
   STOCK, V90    [-9830,-5734,-1966]       [-9830,-5734,-1966]           1.00
   V91..V104     [-9830,-5734,-1966]       [-14745,-8601,-2949]          1.50   uniform
   V107..V121    [-9830,-5734,-1966]       [-29490,-17202,-16000]        3.00   NOT uniform
                                            Y[0] 3.00x  Y[1] 3.00x  Y[2] 8.14x
   X = [0, 1280, 5760] in every build and both modes.
```
🛑 **Stock's |Y| decays 5.0× across the axis (9830 → 1966); ours decays only 1.84×
(29490 → 16000).** We tripled the row **and flattened it.** Manual stays byte-stock throughout.
⊕ **All prior analysis of this cell was of UNIFORM scaling** — the ×1.5 dose. A shape change alters
the **slope** d|f|/dx, which is a different physical quantity from the magnitude, and no measurement
in the kit's record addresses it.

## 🛑 A FLAG ON THE BUILD THAT IS ON THE CAR — unverified, and it should be checked
[[accord-six-levers-closed-on-arithmetic]] closed this lever partly on **"int32 wraparound at
1.6005× ⇒ ×1.5 is 94 % of the lever's ENTIRE range"**. **V107 through V121 carry 3.00× — nearly
double that point.**
⚠ **I have NOT verified the wraparound claim**, and two things argue it is not catastrophic: the row
values (-29490) fit `i16` comfortably, and
[[accord-damper-evaluator-fun34350-ceiling-clamp]] shows the output is **hard-clamped**
(`gp-0x6bd0 = clamp(product, ±ceiling)`, `|gp-0x6bd0| <= 1024`), so an oversized input should
**saturate, not wrap**. V107-V112 also flew fault-free and V112 is the operator's best build.
🛑 **But "should saturate" is a belief, not a check.** ⇒ **OPEN, and the highest-value verification
available: does the V107+ 3.0× row overflow anywhere between the LERP and the clamp?** It is pure
arithmetic on a decompile — no drive, no flash.

## ⚠ WHAT THIS IS *NOT*
🛑 **Not a build proposal.** The ×1.5 dose **measured INERT** at its own output over two flights
([[accord-cbe74-dose-measured-inert-wrong-mode-record]]) — filed as a candidate **T10, "the
instrument is invariant to the lever"**, NOT falsified, since V94 cut the same cell 6× and the
operator **aborted the drive**, proving it reaches the car. And the kit judged delivered damping
**5-69× below the resolvability floor**.
⇒ **The new content here is (a) it is the ONLY engaged asymmetry, (b) the V107 SHAPE change was
never analysed, and (c) 3.0× sits past the stated wraparound point.** Verify (c) before anything else.
Tool: `analysis-2020accord/verify/mode24_vs_mode26_asymmetry.py`.
