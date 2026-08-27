---
name: accord-ratchet-is-a-gain-driven-line
description: "The 6-12 Hz band splits into a narrow ~8 Hz LINE that does NOT exist on stock and scales at or above proportionally with the LKAS gain (E_line +1.56 / beta +1.53), and a broadband FLOOR stock also has which is gain-blind (E_floor +0.26). Pooling them - which every 6-9 Hz number in this kit's history does - dilutes the real effect 2-3x. The ratchet is a SIBLING of the 21-27 Hz carrier, not a demodulation of it."
metadata:
  type: reference
---

# 🛑★★★★★ THE RATCHET IS A GAIN-DRIVEN ~8 Hz LINE THAT DOES NOT EXIST ON STOCK

2026-08-22. `rlog-tools/studies/hf-lf-coupling/hf_lf_09_line_vs_floor.py` (+ `hf_lf_06/07/08`). Pre-registered split, confirmed.

## THE DECOMPOSITION
LINE = **7.4–8.6 Hz** (the smallest symmetric window containing all sixteen observed 6× peaks, 7.62–8.40),
minus a local background; FLOOR = background × 31 bins. 512-sample windows (0.195 Hz bins).
```
                      median E (6x vs stock)   4-dose ladder beta (1x/4x/6x/8x, matched rate)
LINE   7.4-8.6 Hz          +1.559  (71% of cells >0.7)     +1.525  => E_line  +1.136
FLOOR  broadband residue   +0.256  (57% of cells <0.3)     +0.693  => E_floor +0.300
CARRIER 21-28 Hz                -                          +1.390
CTRL   32-38 Hz (placebo)       -                          +0.395
```
- 🛑 **On STOCK the line power is EXACTLY ZERO in 3 of 4 highway cells** — the line window carries no more
  power than its own background. **The ~8 Hz line is OURS.** (Stock's median line 6.9 vs floor 23.2;
  every 6× build sits at 0.95–1.59, the 8× at 3.44.)
- **The line is rate-gated exactly like the carrier** — LINE = 0 at 0–5 °/s even on a 6× build.
- ⭐ **`E_line` is centred ABOVE 1. A by-product cannot outgrow its source** ⇒ the line is a **SIBLING** of
  the 21–27 Hz carrier, both fed by the gain, not a demodulation of it.
- ⚠ `beta_CTRL = +0.395` is itself well above zero: **the gain lifts the whole spectrum.** That broadband
  lift is what the floor is made of, and it is why the placebo correction is load-bearing.

## 🛑 THE CONSEQUENCE FOR EVERY PAST 6–9 Hz NUMBER
**`E = 0.406` "partial coupling" was a MIXING ARTEFACT** — one part gain-driven line, two parts gain-blind
floor. **Any statistic that pools them into a 6–12 Hz band RMS dilutes a real effect by ~2–3×, including
every 6–9 Hz number in this kit's history.** Score the LINE separately.

## WHY IT IS NOT AN AMPLITUDE MODULATION OF THE CARRIER — five independent lines
1. **AM depth bounded at m < 0.05** on every 6× arm, by a **calibrated injection ladder** (the surrogate
   nulls were broken — see below — so the ladder replaced them).
2. Measured 6–12 Hz RMS is a **median 2.39×** the carrier across 78 matched cells ⇒ **~75× the entire
   demodulation budget** at m < 0.05. And linear AM puts **zero** energy at `f_m`.
3. The line is **sharper and more prominent than the carrier** on several arms.
4. **Beating excluded** — every candidate partner peak has prominence ≤ 2.2 against a 3–24 dominant line;
   8 of 24 cells have no candidate at all.
5. **Frequency tracking:** within one build the carrier swings **7.03 Hz** across speed arms (26.76 hwy →
   20.12 micro) while the ratchet moves **0.78 Hz** (8.01 → 7.62), staying inside 7.62–8.40 on all 16 arms.

## 🛑 THE ONLY LIVE ESCAPE ROUTE, NAMED
A **strongly nonlinear demodulator** in the mechanical path (dry friction at the rack, a lash-limited
contact) could in principle turn a 5 % modulation into a low-frequency line 2.4× larger than its carrier.
**This cannot be excluded from `tq` alone. It needs a MECHANISM, not a statistic — a statistical re-run
will not close it and should not be commissioned.**

## ⚠ INSTRUMENT DEFECTS FOUND WHILE DOING THIS — all general, all retractions
- 🛑 **SURROGATE NULLS ABSORB THE SIGNAL.** Phase-randomising a carrier-centred band leaves the carrier and
  its sidebands **still spaced `f_m` apart**, and three tones spaced `f_m` apart beat at `f_m` whatever
  their phases. Measured: a known **35 %** AM raised the observation to 4.84 **and its own null's p95 to
  5.13**; a known **100 %** modulation scores 16.84 against a null p95 of **22.18** = "miss".
  ⇒ **voids every `hf_lf_04`/`hf_lf_06` p-value on the envelope-line and sideband tests.**
- 🛑 **A BANDWIDTH-BLIND ENVELOPE TEST.** The analytic envelope of a band of width W carries envelope
  content only to ~W Hz. Searching 3–9 Hz with 4-Hz-wide bands **cannot show a line above ~4 Hz by
  construction** — which is why the peak landed on the bottom bin in every arm. **A blind instrument, not
  a null.**
- 🛑 **THE PARTIAL-REGRESSION FAMILY IS NON-DIAGNOSTIC.** Calibrated against synthetics and then run on
  **STOCK**, where the carrier is ~1/16 the 6× level: **stock matched the ONE-mechanism synthetic too**,
  and stock's `b_car` (+0.42 to +0.66) is **as large as every 6× build's**. That is the statistic's null
  level, manufactured by a shared driver.
- **H3 (rate-scheduled governor-ceiling dropout) RETIRED** by two independent channels: `v105_b6` =
  **0.000000 across 65,959 frames**, and a reconstructed peak-follower never reaching the 223 °/s knee on
  five routes. They fail in different directions and agree.

Related: [[accord-three-grinds-are-one-frequency]] · [[accord-the-antidamping-is-hondas]] ·
[[accord-ratchet-is-a-lightly-damped-resonance]] · [[feedback-run-the-control-before-the-measurement]]
