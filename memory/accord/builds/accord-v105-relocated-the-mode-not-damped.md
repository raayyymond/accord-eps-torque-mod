---
name: accord-v105-relocated-the-mode-not-damped
description: "V105's 25.5 Hz notch flew (route a5) and RELOCATED the mode instead of damping it - peak 22.73->20.48 Hz at low speed, UP at highway, total 18-30 Hz power CONSERVED, and |H_V105| at each build's own peak rose 0.304->0.544. On V104 only 1.2% of low-speed band power was ever inside the stopband. Filtering is structurally the wrong tool for this mode."
metadata:
  type: reference
---

# 🛑🛑★★★★★ V105 RELOCATED THE MODE — A NOTCH SLIDES A LIMIT CYCLE, IT DOES NOT KILL IT

2026-08-22, route `a5`. `analysis-2020accord/studies/sessions/ra5/ra5_relocation.py`, `studies/sessions/ra5/ra5_pole_moved.py`.

## THE NOTCH WAS AIMED AT SPECTRUM THAT IS NOT THERE
Share of engaged <16 km/h **18–30 Hz power** inside V105's own −20 dB region (24.5–26.5 Hz):
**V104 = 0.0123.** ⇒ **a PERFECT 25.5 Hz notch could have removed at most ~1.2 % of the power in the
operator's own grinding window.** At highway it was 42–71 %, which is why the shape IS stamped there
(local minimum at 24.97 Hz) and absent at low speed.
🛑 **The two estimates that named 25.5 Hz are discredited:** `a4`'s per-window peak regression had
**R² = 0.039** (its own handoff says so), and `f0` = 24.90 Hz is a `Re(Z)` zero-crossing, never the
spectral peak. **The mode is at 21.7–22.9 Hz** — route `0x9e`'s recorded 21.73 Hz line was right.

## ⭐⭐ THE RELOCATION, AND ITS DISCRIMINATOR
```
                 peak Hz    95% CI            peak PSD    |H_V105| at its OWN peak
<16 km/h  V104    22.73   [22.48, 22.98]        51.36            0.3039
          V105    20.48   [20.23, 21.98]        17.48            0.5442   <- 1.79x
55-70 km/h V104   25.97   [24.97, 26.97]         7.74            0.0467
          V105    27.47   [26.97, 27.72]        11.42            0.1795   <- 3.84x
```
**Shift −2.25 Hz [−2.50, −0.50] low speed, +1.50 Hz [+0.50, +2.50] speed-matched highway — both CIs
exclude 0 — while total 18–30 Hz power is CONSERVED (0.769 [0.548, 1.135], spans 1).**
⭐ **`|H_V105|` at each build's OWN peak ROSE.** A stationary mode being attenuated cannot do that; a
describing-function intersection sliding along the loop does exactly it.
⊕ Corroborated on an independent channel by an independent analyst: `tq` peaks agree to **≤0.4 Hz at
highway, ≤0.5 Hz at low speed**, same signed shift in both directions.

⇒ **FILTERING IS STRUCTURALLY THE WRONG TOOL.** Damping removes the intersection; a notch moves it.
⇒ The build that follows (V106) is a **damper**, not a filter.

## 🛑 AND THE BUILD IS VERIFIED FROM THE WIRE, NOT FROM A DOC — three legs
1. 427 wire max **946** vs V103's structural ceiling **800**.
2. `b6` duty **0.0000** on `a5` vs **0.9918** on `a4` (the rung was repointed) ⇒ excludes V104.
3. ⭐ The filter's own output: CAN 427 carries `|gp-0x6b86|`; normalised (21–24)/(3–8) Hz lane ratio
   **0.4337 [0.3107, 0.6426]** vs **0.3864** predicted from the images' float bytes. **In force.**

## 🛑 THE STANDING LIMIT — no V105-vs-V104 band-power ratio resolves on `a5`
Within-drive split-half null spans **0.26–3.8**; 18–30 Hz reads 0.410 [0.240, 0.688] — **inside it.**
Two pipelines reported narrow-band "cuts" (0.348, 0.343) and **both authors withdrew them**: 18–22 Hz
goes UP 30 % while 20.5–23 goes DOWN 65 %, because the mode moved. **A window centred high sees a cut,
one centred low sees a rise, the widest sees nothing.**
**What survives is everything that is NOT a cross-drive ratio:** peak location and shift,
`|H|`-at-own-peak, the 427-lane shape (normalised within-drive), the grind-#1 centre, cave duties.

## ⚠ TWO WITHDRAWALS THAT MUST NOT BE RE-DERIVED
- 🛑 **"Lower the pole radius to widen the stopband" is WRONG.** At fixed DC unity, lowering `r` creates
  a resonant peak: `max|H|` **1.000 → 1.124 → 1.956 → 3.217** at r = 0.95/0.90/0.85/0.80, landing gain on
  grind #1's own lower shoulder. **Widen by moving the POLE DOWN at r ≈ 0.95.**
- 🛑 **All Q/linewidth numbers are VOID** — the −3 dB estimator returns **BW 0.749 Hz / Q 36.2 on WHITE
  NOISE** at 4 s, above every measured value. Only `linewidth ≲ 1.0 Hz, Q ≳ 21` survives, as a LOWER
  bound. Same family as `q_of` returning 79.00 on noise.

Related: [[accord-three-grinds-are-one-frequency]] · [[accord-v106-built-gp6b26-x3-mode-proof]] ·
[[feedback-design-the-statistic-inside-a-drive]] · [[feedback-run-the-control-before-the-measurement]]
