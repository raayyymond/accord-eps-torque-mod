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
