---
name: accord-highway-acoustic-budget-bound
description: The creep-calibrated acoustic transfer predicts a highway signal 2-9x BELOW the microphone's own highway floor, so a highway acoustic null is uninformative — now a quantified bound rather than a hand-wave; and the joint tri-channel detector is mic-limited
metadata:
  type: reference
---

⚠ **A HIGHWAY ACOUSTIC NULL IS UNINFORMATIVE, AND THIS IS THE NUMBER THAT SAYS SO.**

Calibrated on the 10 demonstrated creep grind #2 bursts: κ = (fractional acoustic excess) /
(fractional sub-50 Hz mechanical excess, IMU `ay` 40–49 Hz, both in power) =
**0.0091 [0.0059, 0.0159]**. Log–log slope **0.72 [0.39, 0.96]**, R² **0.83**.

Transported to highway (v ≥ 25 m/s):

| route | build | Kd@hwy | measured sub-50 Hz mech excess (p99) | κ-predicted acoustic excess | mic floor | **headroom** |
|---|---|---|---|---|---|---|
| r2b | V58 | 1.00 | 941 % | 8.5 % | 52.8 % | **6×** |
| r37 | V62 | 2.00 | 1351 % | 12.3 % | 109.9 % | **9×** |
| r3b | V65 | 2.00 | 1038 % | 9.4 % | 34.1 % | **4×** |
| r47 | V67 | 2.44 | 1396 % | 12.7 % | 19.3 % | **2×** |

(mic floor = split-half null on 10 s blocks, p90 ratio, converted to excess power. My r47 19.3 % is
consistent with the 25.3 % on record; the difference is block selection.)

⇒ **The predicted signal sits 2–9× UNDER the instrument.** So the budget test **cannot bear the
weight at highway**: the residual is not small, *both terms are below the floor*. **The honest output
is the BOUND — unexplained acoustic energy up to 2–9× the sub-50 Hz-implied amount would be
invisible.** Tighter than expected, and the kit's first such bound.

## 🛑 THE THREE ASSUMPTIONS, each failing in a KNOWN direction
- **A1 — κ is creep-calibrated.** Radiation efficiency rises ~f² (raises κ at higher frequency) while
  the highway ambient is ~9.9× higher in power (divides the fractional excess). They partly cancel;
  **neither is measured here.**
- **A2 — it assumes the highway event couples to the chassis like grind #2.** If it is a **torsional
  column mode** like grind #1, the IMU sees nothing *even at creep*
  ([[accord-grind1-is-torsional-grind2-reaches-the-chassis]]) and the whole budget inherits that
  blindness.
- **A3 — the floor is a STEADY-tone floor.** A <5 Hz modulated event is ~5× easier to detect.

## ⚠ AND THE JOINT DETECTOR IS MIC-LIMITED
J = min(z_bar, z_ay, z_sound) catches **80 %** of the demonstrated creep bursts at a 0.1 %
per-block false-alarm rate — but **the microphone is the minimum channel in 97 % of burst blocks**.
⇒ **"joint" buys SPECIFICITY, not SENSITIVITY: its reach is the weakest channel's reach.** Do not
present a joint null as stronger than the strongest single channel — it is bounded by the *weakest*.

At highway the detector is a **null with LOW POWER**: exceedance counts 1 / 0 / 1 / 4 over
149.0 / 79.9 / 169.6 / 779.8 s, exact Poisson 95 % intervals **[0.6, 134.6] / [0.0, 166.2] /
[0.5, 118.3] / [5.0, 47.3]** per hour — **every interval overlaps every other**. The one clean
statement: the highest highway block on any build is **J = 1.37**, below the median creep burst
(**1.89**) and below 8 of the 10 demonstrated bursts.

⇒ `analysis-2020accord/studies/grind2/grind2_trichannel.py` §5/§6 · `_scratch/out/_grind2_trichannel.json`. See
[[accord-highway-event-rate-null-with-power]] and [[accord-mic-negative-carries-almost-nothing]].
