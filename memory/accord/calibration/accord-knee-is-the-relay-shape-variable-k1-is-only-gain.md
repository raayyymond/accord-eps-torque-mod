---
name: accord-knee-is-the-relay-shape-variable-k1-is-only-gain
description: "K1 (0xC40D2) multiplies AFTER the Coulomb relay, so it is pure gain and cannot change the relay's shape or its harmonic content. KNEE (0xC40BC) sets where the clamp bites and IS the shape. Harmonic ratio is monotone in knee across all three levels flown - 300 gives 1.743, 600 gives 1.412, 1800 gives 1.213 - suggestive but not significant (rho -0.291, p 0.257). This changes the recommended build from V120 (halves K1, pure gain, costs assist) to V116 (knee 1800->2400 with K1 612->816, softening the relay while holding the small-signal gain exactly at V112's)."
metadata:
  node_type: memory
  type: reference
---

# ⭐⭐ `KNEE` IS THE RELAY'S **SHAPE**; `K1` IS ONLY ITS **GAIN**

## 🛑 A MIS-CONSTRUCTED PREDICTION, CORRECTED
I first tested the relay hypothesis against
`fric_gain = (K1/1024)·(12/knee)` and got a flat result (+30 % for a 2× dose, CI [0.794, 2.241]).
**That test could not have worked.** The relay is
```
   fVar13   = clamp(POL · gp-0x6abc · 12 / knee, ±1)      <- KNEE sets where the clamp bites = SHAPE
   friction = EMA( |model| · K1/1024 · fVar13 )           <- K1 multiplies AFTER = pure GAIN
```
🛑 **A signum's harmonic content relative to its own fundamental is SCALE-INVARIANT**, so `K1`
cannot move a harmonic *ratio* by construction, and `fric_gain` conflates it with the one variable
that can. ⇒ the flat result was a property of the statistic, not of the car.

## [EVIDENCE, suggestive] RE-TESTED ON `KNEE` — MONOTONE ACROSS ALL THREE LEVELS FLOWN
```
   knee   n_routes   median harmonic ratio      relay character
    300       8            1.743                hardest signum
    600       7            1.412                stock
   1800       2            1.213                softest / most linear   <- V112

   Spearman(knee, harmonic ratio) = -0.291   p = 0.257     [predicted: NEGATIVE]
   knee 300 / knee 1800 = 1.437   CI [0.925, 2.258]
   knee 300 / knee  600 = 1.234   CI [0.693, 2.279]
```
✅ **Direction correct and monotone across three levels.** 🛑 **NOT significant** — every CI includes
1.0 and p = 0.257. A specific monotone ordering of three groups has one-sided chance ≈ 1/6, so this is
**suggestive, and it is exactly the strength the data can carry.** [BELIEF, not EVIDENCE.]
⊕ It is coherent with the road result: **V112 has the softest relay AND the lowest harmonic ratio,
and it is the operator's best build ever.**

## ✅ ⇒ THE RECOMMENDED BUILD CHANGES: **V116, NOT V120**
```
              knee    K1     small-signal gain      relay saturates at    assist change
   V112 (on car) 1800   612       0.0039844            knee/12 = 150         --
   V116          2400   816       0.0039844            knee/12 = 200        NONE
   V120          1800   306       0.0019922            knee/12 = 150        LESS
```
✅ **V116 raises `knee` 1.333× and `K1` 1.333× together, so the small-signal gain is EXACTLY V112's
while the relay saturates 1.333× later** ⇒ *"make the relay more linear without changing the
assist."* That is the mechanism-matched edit.
🛑 **V120 does the opposite of what the operator asked for.** Halving `K1` halves the modelled
friction, and [[accord-friction-polarity-more-assist]] establishes **more modelled friction = MORE
assist** ⇒ V120 **reduces assist**, against *"low effective friction and steering mass w.r.t. LKAS
command."* It is also pure gain, so on this mechanism it cannot touch the harmonics at all.
⇒ **V116 supersedes V120 as the recommendation**, on both the mechanism and the operator's own
constraint. V116 is already built, 38/38 assertions, cal-only.
🛑 **The mechanism is BELIEF, not EVIDENCE.** V116 is the best-motivated flight, not a guaranteed
fix. ⊕ Its own falsifier is clean: if the relay drives the harmonics, V116 should reduce the harmonic
ratio below V112's 1.213 **and** be no worse on assist.
Tools: `rlog-tools/studies/peakturn/harmonic_dose_vs_knee.py`,
`rlog-tools/studies/peakturn/harmonic_dose_vs_fricgain.py` (the mis-constructed one, kept as a record).

## 🛑 THE ONE QUANTITATIVE CHECK ON THIS MECHANISM **DOES NOT SUPPORT IT** — 2026-08-28
I tried to turn V121 into a prospective prediction, the way the saturation-duty model correctly
called V112 (predicted 0.2353, measured 0.3102 / 0.1071). The relay is **memoryless**, so I fed the
measured rate from the V112 drives through `clamp(rate·4.7121·12/knee, ±1)` at each knee and measured
the harmonic content of the output:
```
   knee     600     1800     2400     3000     4000     8000
   ratio   0.951   1.365    1.248    1.493    1.832    1.278
   vs 1800   --      --     0.914x   1.094x   1.342x   0.936x
   predicted factor for knee 3000: 1.094x   window-bootstrap CI [0.755, 1.335]
```
🛑 **Non-monotone, and knee 3000 comes out slightly WORSE, not better.** It also **contradicts the
cross-build trend** this note rests on (knee 600 → 1.412, knee 1800 → 1.213 on the wire; the
simulation puts 600 BELOW 1800).

### ⚠ THE SIMULATION IS INVALID AS A PREDICTION — and that is the methodological point
I fed the **measured** rate through a *different* relay, but that signal **already contains the
effect of the relay that was actually running** (knee 1800). **A memoryless nonlinearity inside a
CLOSED LOOP cannot be simulated by post-processing the loop's own output** — the loop would settle
somewhere else entirely. ⇒ the numbers above **cannot confirm** the mechanism.
🛑 **But they cannot be waved away either**: an invalid simulation that nevertheless *reproduced*
the trend would have been weak support, and this one **fails to reproduce it.** ⇒ net, **confidence
in the harmonic mechanism goes DOWN.**

### ⇒ WHERE THIS LEAVES V121 — the headline rationale is WEAKENED, the build is not withdrawn
**V121's case no longer rests on the harmonic mechanism.** What survives is independent of it:
1. ✅ **Small-signal gain held EXACTLY at V112's** ⇒ bit-identical feel at and below 31.8 deg/s, so
   the regression risk in normal driving is structurally near zero.
2. ✅ **More friction above 31.8 deg/s ⇒ MORE assist** ([[accord-friction-polarity-more-assist]]) ⇒ it
   serves the operator's stated constraint directly, whatever it does to the oscillation.
3. ✅ **`knee` is the one variable whose previous step (600→1800) coincided with the operator's
   best-ever build** — confounded, but it is the best on-car track record any lever here has.
4. ✅ Cal-only, 4 payload bytes, no cave, 40/40 assertions.
⚠ **V116 is the conservative version of the same move** (K1 at 0.797 of |model| vs V121's 0.996,
which sits just under the sign-inversion ceiling). **If the weakened mechanism argues for a smaller
step, V116 is it.**
🛑 **Stated plainly: V121 is a well-constructed build whose effect on the oscillation is UNKNOWN.**
Tool: `analysis-2020accord/verify/predict_v121_harmonic_effect.py`.
