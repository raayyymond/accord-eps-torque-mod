---
name: reference-accord-rate-scale-4p7121-stands
description: The column-deg/s -> gp-0x6ac0 counts scale is 4.7121 and it STANDS. An on-car fit against V74's bit7 peaks near 5.8, but that reflects the estimator's column-vs-motor-rate bias -- do NOT revise the constant from it. The 10.0 implied by "1 count = 0.1 deg/s" is disfavoured.
metadata:
  type: reference
---

# 🛑 The `4.7121` rate scale STANDS — and the on-car fit that looks higher must not be used to revise it

`FactorE`, the `0xC520C` cap table and every rate-indexed LERP are indexed on **`gp-0x6ac0`**, the
motor/resolver rate. The conversion from the 0x18F **column** rate is:

> **`gp-0x6ac0` counts = |column deg/s| × 4.7121** — equivalently `column deg/s = counts / 4.7121`.

Chain: `gp-0x6ac0` = 30 counts per Hz electrical (PWM carrier 4.000 kHz, PCLK 40 MHz). Settled three
independent ways; carried as `RATE_SCALE_CTS_PER_DEGS` in `rlog-tools/decode_v72_probe.py` and
`RATE_SCALE` in `analysis-2020accord/analyze_r59_probe.py`.

## 🛑 The error this file exists to stop
Taking the raw 0x18F int16 to *be* `gp-0x6ac0` implies **1 count = 0.1 deg/s ⇒ scale 10.0**. That is
**2.12× too high**, and it silently halves every breakpoint quoted in deg/s. It put V74's
`FactorE X[0] = 12` at "1.2 deg/s" when the correct figure is **2.55 deg/s**, and it inflated a
disengaged positive-control cell from its true 157 frames / 100.000 % to "183 frames / 99.45 %".

## The on-car arbitration — [EVIDENCE], route 5d
V74's `bit7 = (gp-0x6bd0 != 0)` is a threshold on FactorE's own index, so the drive can score candidate
scales. Predicted-vs-measured bit7 agreement, 101,118 frames:

| scale | agree ALL | agree ENGAGED |
|---|---|---|
| 4.0 | 91.04 % | 84.38 % |
| **4.7121** | **91.24 %** | **84.74 %** |
| 5.0 | 91.29 % | 84.82 % |
| 6.0 | 91.27 % | 84.78 % |
| **10.0** | **89.72 %** | **82.07 %** |

Per **episode** (9 replicates — [[feedback-episodes-not-windows-and-the-noise-floor]]): median best **5.80**, episode-level
bootstrap 95 % CI **[5.12, 8.27]**, and **8 of 9 episodes favour 4.7121 over 10.0**.

## 🛑 WHY THE FIT PEAKS HIGH, AND WHY IT IS NOT A CORRECTION
The estimator substitutes the **column** rate for the firmware's **motor** rate. The two differ by
torsion-bar wind-up and bus filtering, and the residual is **one-directional**: 5,522 frames where the
model predicts dose 0 and the damper fired, against 3,335 the other way, the former at column-rate p50
**1.7 deg/s**. Whenever the motor moves and the column does not, the fit compensates by **raising** the
scale. ⇒ the fitted 5.80 is an **upper-biased** estimate, and the CI excluding 4.7121 is exactly what
that bias predicts — not evidence against the firmware chain.

**[EVIDENCE]** 10.0 is disfavoured. **[BELIEF]** 4.7121 is correct once the bias is accounted for.
**Use 4.7121. Treat every column-rate-derived dose as a LOWER BOUND.**

⊕ A monotone trend in a rate band survives any monotone rescaling; only the **band edges** move. If a
result depends on an edge in deg/s, state the scale you used.

Related: [[accord-v74-flew-damper-is-in-force]] · [[reference-accord-two-dead-zones-speed-and-rate]] ·
[[accord-gp6c2c-is-the-detector-input]]
