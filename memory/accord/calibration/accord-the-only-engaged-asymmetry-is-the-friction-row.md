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

## ✅ THE FLAG IS **RETRACTED** — V107..V121's 3.0× row is fine, and the kit had already shown why
2026-08-28, same session. I flagged that the engaged friction row at **3.00×** sits past a stated
**"int32 wraparound at 1.6005×"**. **Verified it. The flag was wrong on three counts.**

1. 🛑 **I cited the wrong clamp as reassurance.** `FUN_00034350` reads FactorB/C/D/E and the
   ceiling and clamps *their* product to `|gp-0x6bd0| <= 1024`. **It never reads `0xCBE74`.** The
   friction row's consumer is **`FUN_00036c12`**, whose output `gp-0x6b26` has **its own clamp at
   ±`0xC407E` = ±511**.
2. 🛑 **My saturation arithmetic used a MAX, not a distribution.** I took route 77's engaged
   **max** |gp-0x6b26| = 319.1 at the stock row, scaled it 3.0× to 957, and concluded the clamp
   binds. **`build_v107_tva.py` has a section titled "THE TERM IS NOT SATURATING"** with the
   reconstructed duty on route a6's own engaged distribution (r77-calibrated law, **held-out
   validated on r78 to ±20 % and conservative on the tail**):
```
      stratum          n eng     p50     p99    duty>=511
      engaged all     123802    15.1   268.5    0.00121
      <8 km/h (S1)      3173    16.2   221.1    0.00047
      <16 km/h         10186    30.2   333.3    0.00185
      40-95 (S3)       34593    13.3   208.1    0.00056
```
   ⇒ **p99 = 268.5 against a 511 clamp; duty 0.12 %. The term is NOT a relay.**
3. ✅ **The real arithmetic bound is documented and different.** `Y` is **signed int16**, so with
   `Y[0]` stock = -9830 the ceiling is **k_max = 32768/9830 = 3.3335**, and **V106/V107 sit at
   3.00× = 90.00 % of the int16 floor — deliberately.** The "90.0 %" column I first read as clamp
   duty is **percent of the int16 floor.** ×4/×5/×6 are int16 **overflow**, and the builder says so.
   ⇒ whatever the **1.6005×** figure in [[accord-six-levers-closed-on-arithmetic]] refers to, it is
   **not** this row's headroom; that note and this one should be reconciled, but **V107..V121 are
   inside the bound that actually governs.**

### ✅ WHAT SURVIVES, AND IT IS DELIBERATE DESIGN, NOT DRIFT
The V107 step is a **reshape at constant `Y[0]`**, chosen from five candidates:
`RESHAPE_B = (-29490, -24000, -16000)`. It holds `Y[0]` **exactly** at V106's so *"creep-speed clamp
duty and the relay index are UNCHANGED BY CONSTRUCTION"*, and raises only the high-speed knots —
Honda's own taper made the dose **4.2× weaker at highway**, which is where the residual was.
V108 then reverted `Y[1]` (-24000 → -17202), which the build name records as `GP6B26.Y1REVERT`.
⇒ **The escalation was reasoned, bounded, and its saturation risk was measured before flight.**

### ⇒ NET
✅ **No defect in the build on the car.** The only engaged-vs-manual asymmetry is still this row —
that part of the finding stands — but **it is not saturating, not wrapping, and not a hidden relay.**
🛑 **My "shape change was never analysed" claim is also withdrawn**: `build_v107_tva.py` analyses
exactly that, with a delivered-coefficient table at four speeds and an int16-headroom column.
