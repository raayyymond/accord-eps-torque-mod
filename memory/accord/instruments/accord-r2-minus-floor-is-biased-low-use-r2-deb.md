---
name: accord-r2-minus-floor-is-biased-low-use-r2-deb
description: "🛑🛑⭐⭐⭐⭐⭐ `R2 − floor` is BIASED LOW by 0.12-0.22 and degrades with sample size. Three agents published camera-lock fractions differing 4x; ALL THREE datasets were correct and TWO estimators were biased. Use `R2_deb = sqrt(max(R2^2 - mean(R2^2_detuned), 0))`, validated against a known-p synthetic to +/-0.04."
metadata:
  node_type: memory
  type: reference
---

🛑🛑 **`R2 − floor` IS A BIASED ESTIMATOR. NEVER QUOTE IT AS AN ESTIMATE.** Settled 2026-09-11 after three
agents published camera-lock fractions for the same quantity on overlapping routes that differed **4×**.
**All three datasets were correct. Two of the three estimators were biased.**

## The adjudication method — this is the transferable part

**Reproduce every disputed published number on ONE loader, then vary ONE FACTOR AT A TIME.** r39, bar,
18–22 Hz:

| windowing | estimator | quantity | value | whose published cell |
|---|---|---|---|---|
| 20 s blocks | `R2 − maxfloor` | excess | **0.1309** | `cyclekind` (published 0.131) ✓ |
| 20 s blocks | `R2_deb` | excess | 0.5356 | |
| 20 s blocks | `R2_deb` | grind total | 0.5154 | |
| whole | `R2 − maxfloor` | excess | **0.3956** | `combsize` (published 0.357, own strata) |
| whole | `R2_deb` | excess | 0.5110 | |
| whole | `R2_deb` | grind total | **0.4948** | `modelrate` (published 0.501) ✓ |

**Factor decomposition: estimator ×4.09 · windowing ×3.02 · total-vs-excess ×0.98.**

**Then settle the estimator against GROUND TRUTH, not against authority** — build a signal with a *known*
locked fraction *p* and run both:
- **`R2 − maxfloor` is biased LOW by ~0.12 whole-stratum and ~0.22 in 20 s blocks**, at every p ≥ 0.1.
- **`R2_deb = √(max(R2² − mean(R2²_detuned), 0))` recovers *p* to ±0.04.**

🛑 **The reason is dimensional, and it generalises to any floor-subtraction: NOISE ADDS IN POWER, so
subtracting a floor in AMPLITUDE over-subtracts — and the over-subtraction worsens as power falls.**
⇒ `R2 − floor` is a **conservative lower bound that degrades with sample size**, not an estimate.

## The corollary that cost two published findings

**The bias scales with N_eff, so it is NOT uniform across strata — and that manufactures fake contrasts
whenever the strata differ in length.** `combsize`'s quiet strata were **5–7× longer** than its grinding
strata, so quiet was penalised less, looked larger, and produced *"the comb does not grow when the car
grinds"*. **Debiased, the comb grows ×0.94–1.81 and r39's CI excludes 1 in the OPPOSITE direction
(1.29 [1.08, 1.59]).** A second finding died the same way: *"bar is 34 % camera-locked, the angle only
2 %"* — **debiased the angle is ~40 % locked** (command 0.624 · bar 0.534 · angle 0.401), and the
"a torque comb barely moves the column's inertia" explanation went with it.

⇒ **Before comparing any floor-subtracted statistic across strata, check the strata are the same length —
or debias.**

## Two more traps in the same family

- **A low lock/coherence statistic on a SHORT stratum is a NON-DETECTION, not a zero.** `modelrate`
  retracted a V288 falsification for exactly this: 98.9 s stratum, floor 0.455, reading 0.333 — *below its
  own floor*. **State N_eff per stratum.**
- **A detuned-frequency null does not decorrelate unless |Δf|·T ≫ 1.** At 3 s windows and Δf 0.37 Hz that
  is 1.1 cycles of slip and the "null" sits at **84 % of signal**. Use **12 s+**, ideally 20 s.
- **The detector itself: the plain circular mean FAILS its own positive control.** A staircase's 20 Hz
  component is a sawtooth whose amplitude flips sign with the plan's slope, so the phase hops by π and the
  mean cancels — a signal generated *on* the model clock scored **below** its own null. **Use the square
  law, R2 = |Σ z²e^(−2iθ)|/Σ|z|², which locks modulo π and equals the locked fraction of in-band energy.**

## The proximity control, which makes the lock real rather than mere nearness

A **free** mode 0.08 Hz from the clock — where r39's ring actually sits (19.92 vs 19.9997 Hz) — reads
`R2_deb` = **0.018** over 182 s. ⇒ Nearness alone does not manufacture a lock.

## ⭐ And the reconciliation that is not a contradiction

**A 50 % locked OUTPUT coexists with a 20 % command-side DRIVE share** because a **phase-locked** drive
accumulates **coherently** (amplitudes add) while random-phase drive accumulates **incoherently** (powers
add). **The comb is a minority of the drive, over-represented in the response because it is the only
coherent part of it.** Both measurements stand.

Related: [[accord-the-20hz-forcing-comb-is-real-and-half-the-rings-energy-is-locked-to-it]] ·
[[accord-episodes-of-hardcodes-the-18-22hz-gate]] ·
[[feedback-convert-the-symptom-into-the-levers-own-units-before-reading-a-null]] ·
[[accord-grinding-is-an-excited-resonance-no-excitation-to-remove]]
