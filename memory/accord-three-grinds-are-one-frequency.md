---
name: accord-three-grinds-are-one-frequency
description: "OPERATOR-CONFIRMED and then MEASURED: grind #1, #2 and #3 are ONE 21-27 Hz mode under three CONDITIONS, not three frequencies. The kit's 'grind #2 = 44.9 Hz Q=37, NOT a harmonic' and 'grind #3 = 46 Hz' are NOT REPRODUCED anywhere in the corpus under the operator's own scenario definitions. Also re-attributes 'applying torque kills the buzz' to RATE, not torque."
metadata:
  type: reference
---

# 🛑🛑★★★★★ THE THREE GRINDS ARE ONE FREQUENCY UNDER THREE CONDITIONS

2026-08-22. The operator corrected the kit; the instrument then confirmed him.

> *"I actually think all 3 grinds are the same frequencies. They just happen under different scenarios.
> Grind #1 low speed like 5 mph (LKAS engaged), grind #2 low speed but hard manual turns during LKAS
> engagement, grind #3 highway speeds (LKAS engaged)."*

## THE MEASUREMENT — peak-searched 15–48 Hz, stratified by HIS scenarios
`rate_f` (0x18F), 1 s Hann, engaged, episode-bootstrapped:
```
                  S1 (<10 km/h)    S2 (hard manual)   S3 (highway)
STOCK 1x            17.02 (no line)  17.02 (no line)   15.02 (no line)
V102 6x             22.03            22.03             25.04
V103 6x             21.03            21.03             24.04
V104 6x             23.03            23.03             27.04
V101 8x             23.03            23.03             25.04
V105 NOTCH          22.03            21.03             27.04
```
**38–48 Hz prominence: 0.3–4.9, median ~1.0 — indistinguishable from the local baseline in ALL 21
build×scenario cells.** RMS 18–26 vs 38–48 runs **5–15×** in every scenario. A per-window burst detector
(the record describes grind #2 as a rare EVENT a pooled spectrum would wash out) **never puts a 38–48 Hz
window above an 18–26 Hz one** — range 0.09–0.91.
**Harmonic PLV: NULL** where runnable. 🛑 **NOT RUNNABLE at highway** — 2 × 25–27 Hz = 50–54 Hz, at or
above `0x18F`'s **50.57 Hz Nyquist**. The only scenario where a 44–46 Hz label was plausible is the one
where this channel is structurally blind to the harmonic.

⇒ **RESTATE THE TAXONOMY AS THREE CONDITIONS OF ONE 21–27 Hz MODE.** The recorded
*"grind #2 ≈ 44.9 Hz, Q ≈ 37, NOT a harmonic of grind #1"* and *"grind #3 ≈ 46 Hz"* are **not reproduced**.

## ⭐ AND A CORPUS CLAIM RE-ATTRIBUTED — it is the RATE, not the torque
The record has *"applying torque kills the buzz"* at 16.12× [5.29, 41.29]. Four S2 mask definitions on
the same drive, same channel, same window:
```
|tq|>=1000 AND |rate|>=40   PSD  0.193  prom 1.7   <- the RATE FLOOR kills it
|tq|>=1000, any rate             51.689      33.5
|tq|>=500 AND 15<=|rate|<40      97.676      58.7  <- maximal
```
⇒ **"Applying RATE kills the buzz."** At high torque with no rate condition the mode is fully present.
[EVIDENCE — only the mask differs.]

## 🛑 THE CEILING — state it wherever this is cited
`0x18F` = 101.15 Hz ⇒ **Nyquist 50.57 Hz**. `0x1AB` = 49.78 Hz ⇒ Nyquist 24.89 Hz (never use it above
~25 Hz). **Nothing above ~50 Hz is observable in the CAN corpus at all.** The only wide-band instrument
is `rawAudioData` (Nyquist 8 kHz), already measured NULL from 100 Hz to 8 kHz across six builds.
⇒ **The verdict is "one mode within 5–48 Hz", not a wide-band null.** S3 is the best-powered arm
(299–745 windows); S2 the weakest (3.2–36.6 s).

Related: [[accord-v105-relocated-the-mode-not-damped]] · [[accord-ratchet-is-a-gain-driven-line]] ·
[[feedback-design-the-statistic-inside-a-drive]]
