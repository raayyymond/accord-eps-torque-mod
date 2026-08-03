---
name: accord-mic-two-weightings-are-a-filter-bank
description: soundPressure + soundPressureWeighted are a TWO-POINT FILTER BANK; inverting them shows the grind #2 acoustic excess is NOT all at 40-49 Hz — effective centroid 63.5 Hz [54.2, 79.6], the first data placing grind #2 energy above the 50 Hz ceiling
metadata:
  type: reference
---

★★★ **THE MICROPHONE CAN NAME A FREQUENCY AFTER ALL — not from one channel, from the RATIO of two.**

`soundPressure` and `soundPressureWeighted` are the same 100 ms RMS through two different filters.
A-weighting is **−32.41 dB at 44.6 Hz** but **−19.14 dB at 100 Hz** (IEC 61672, verified against the
standard table: my −30.27 at 50 Hz and −19.14 at 100 Hz vs the published −30.2 / −19.1). So their
**ratio reports where the energy sits**, even though neither channel alone can resolve anything.
Verified the channel is real before using it: `soundPressureWeightedDb = 20·log10(spw / 2.0000e-05)`
with sd **1.7e-12** ⇒ `spw` is a genuine A-weighted RMS pressure in Pa; and the ambient mean A-weight
**rises with speed on every route** (r3b 2.5e-3→6.5e-3, r2b 5.2e-3→1.2e-2, r47 1.2e-2→1.7e-2,
creep→highway) as wind/road noise must.

## Measured, 10 demonstrated creep grind #2 bursts (r3a LKAS ON ×8, r3b seg 2 LKAS OFF ×2)

| quantity | point | 95 % CI (event bootstrap) |
|---|---|---|
| un-weighted burst/control amplitude | **4.591** | [2.946, 8.313] |
| A-weighted burst/control amplitude | **6.514** | [3.609, 8.294] |
| **excess mean A-weight / w(44.6 Hz)** | **4.28** | **[2.28, 9.86]** |
| ⇒ **effective spectral centroid** | **63.5 Hz** | **[54.2, 79.6] Hz** |
| energy fraction above the band if f_h = 100 Hz | 16.2 % | [6.3, 43.8] |
| energy fraction above the band if f_h = 250 Hz | 1.4 % | [0.5, 3.8] |

**The A-weighted channel rose MORE than the un-weighted one.** ⇒ **the grind #2 acoustic excess is
NOT all at 40–49 Hz.** A pure 44.6 Hz excess would give 1.00× by construction and is excluded — the
CI's lower bound is 2.28. **The whole centroid interval sits above the 50 Hz ceiling**, and 63.5 Hz
lands essentially on `gp-0x6c2c`'s band-pass peak (61 Hz, >90 % sensitivity to ~180 Hz) — see
[[accord-gp6c2c-is-the-detector-input]]. That is independent corroboration of the V68 probe
threshold, reached from acoustics with **no shared assumption** with the firmware arithmetic.

Robust to the burst statistic: we/w(44.6) = **5.64** (p90) / **3.07** (median) / **3.31** (max). Not
one loud event: the mic fires on **8 of 10** bursts and tracks torsion-bar magnitude (per-event
un-weighted 8.58, 8.35, 8.31, 7.15, 4.98, 4.20, 4.02, 3.57, then 1.87 / 1.39 for the two weak ones).

## 🛑 THE LIMIT, AT FULL STRENGTH
**This is a MEAN-WEIGHT inversion. It proves the excess is not all sub-50 Hz; it does NOT locate the
energy.** Any mixture with the same mean weight fits — 16 % at 100 Hz, 1.4 % at 250 Hz and 0.27 % at
1 kHz are all identical to this test. Quote the centroid as an *effective* one, never as a line.

⚠ **Tyre scrub is NOT excluded.** Controls are matched on the exact (speed, effort, |rate|) cell and
the partial correlation survives it (**+0.507 [+0.297, +0.634]**, n = 2956 creep blocks, sound vs the
40–49 Hz bar envelope controlling |rate|/effort/speed), but scrub intensity is driven by rack force,
which is not among the controlled covariates.

**BELIEF, NOT MEASUREMENT:** the likeliest home is **harmonics of the 44.6 Hz contact nonlinearity —
89.2 / 133.8 / 178.4 Hz** — all inside the detector's band-pass. Nothing here measures that.

🛑 **THIS INVERTS THE RULE IN [[accord-both-instruments-blind-above-50hz]].** That file says *"un-weighted
up with A-weighted flat is itself the low-frequency signature"* — the rule is correct, but **the
outcome did not obtain**: A-weighted rose *harder*, which is the HIGH-frequency signature. Do not
carry the expected direction forward as if it were the finding.

🛑 **THE RATIO IS A POWER RATIO. INVERT IT IN POWER, NOT AMPLITUDE — this is the reusable trap.**
A centroid of **95.5 Hz [66.8, 170.5] was published in review and is RETRACTED**: it came from
inverting 4.28× against the **amplitude** weight `w(f)` instead of the **power** weight `w(f)²`.
`W(95.5)/W(44.6)` = **18.29×**, not 4.28×. The correct inversion is **63.5 Hz [54.2, 79.6]**.
**Root cause identified and confirmed two ways**, so it cannot recur silently:
- the same run's *"16.2% of energy at 100 Hz"* decomposition gives a mean **power** weight of
  `0.838·W(44.6) + 0.162·W(100) = 4.277×` — reproducing 4.28 exactly;
- that identical mixture is only **2.068×** in amplitude terms, and `√4.28 = 2.069` — the amplitude
  reading is precisely the square root of the right answer.
The conclusion **survives and tightens**: the interval is still entirely above 50 Hz (margin
**54.2 Hz**, not 66.8), and **63.5 Hz sits essentially ON `gp-0x6c2c`'s 61 Hz band-pass peak** — closer
corroboration of V68's target than the wrong number gave. ⚠ A-weighting is defined in **dB on power**;
any `w = 10**(A_db/20)` is an **amplitude** weight and must be squared before mixing energies.

⇒ `analysis-2020accord/grind2_trichannel.py` §5(a)/(d) · `_grind2_trichannel.json`. See
[[accord-grind1-is-torsional-grind2-reaches-the-chassis]] and
[[accord-mic-negative-carries-almost-nothing]].
