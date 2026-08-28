---
name: accord-the-rate-deficit-is-upstream-of-the-firmware
description: "Transfer functions over 15 routes split the LKAS path in two: demandRate->CMD rolls off -16.0 dB by 1-2 Hz while CMD->rate RISES +1.2 dB, so the steering-rate deficit is created upstream in openpilot's controller and the firmware over-delivers relative to the command it receives. No firmware calibration can recover motion that was never commanded. The same measurement shows CMD->rate at +7.5 dB by 12-20 Hz, which IS the firmware-side oscillation mechanism."
metadata:
  node_type: memory
  type: reference
---

# 🛑🛑★★★★★ THE RATE DEFICIT IS **UPSTREAM OF THE FIRMWARE** — AND THE SAME DATA LOCATES THE OSCILLATION

2026-08-27. Follows [[accord-the-rate-deficit-is-real-universal-and-not-v111]], which established the
deficit is real (ach/dem 0.73 -> 0.30) and universal. **This locates it.**

## THE MEASUREMENT [EVIDENCE]
Welch H1 = |Pxy|/Pxx, 1024-pt (10.24 s) @100 Hz, 50 % overlap, pooled over **15 routes** weighted by
n, engaged & hands-off (D3) & moving. Normalised to each path's own 0.1-0.3 Hz value.

```
  band        demandRate->CMD      demandRate->rate       CMD->rate        drvTorque->rate
  0.1-0.3 Hz   1.000  coh 0.317     1.000  coh 0.428     1.000 coh 0.704    1.000 coh 0.682
  1.0-2.0 Hz   0.158  (-16.0 dB)    0.248  (-12.1 dB)    1.152 (+1.2 dB)    0.765 (-2.3 dB)
  3.5-5.0 Hz   0.069  (-23.2 dB)    0.134  (-17.4 dB)    1.363 (+2.7 dB)    0.369 (-8.7 dB)
  5.0-8.0 Hz   0.075  (-22.5 dB)    0.201  (-13.9 dB)    2.019 (+6.1 dB)    0.208 (-13.6 dB)
 12.0-20.0 Hz     --                0.478   (-6.4 dB)    2.376 (+7.5 dB)    0.302 (-10.4 dB)
```

## 🛑 CONCLUSION 1 — THE DEFICIT IS OPENPILOT-SIDE, NOT FIRMWARE
**`demandRate->CMD` is attenuated MORE than `demandRate->rate`** (-16.0 vs -12.1 dB at 1-2 Hz).
Both estimates share the same input, so the *comparison* is robust even where coherence is low.
⇒ **openpilot does not convert its own fast rate demand into a fast command**, and the firmware then
delivers **more** motion than the command asks for (`CMD->rate` = +1.2 dB at 1-2 Hz, coh **0.51**).
🛑 **NO FIRMWARE CALIBRATION CAN RECOVER MOTION THAT WAS NEVER COMMANDED.**
⊕ Corroborated by two independent numbers:
- **Demand episodes are ultra-short.** Above 15 °/s the median excursion lasts **0.030 s** (p90 0.090 s).
  The arbitration IIR's tau is **0.0315 s**, so a 30 ms pulse reaches `1-e^(-0.952)` = **61 %** —
  against a measured `ach/dem` of **0.63** in the 15-30 °/s band.
- **openpilot's own slew limiter** is `STEER_DELTA 3.0/s x DT 0.01 x STEER_MAX 4096` = **122.88
  ct/frame** ⇒ full scale in **0.33 s**. In a 30 ms episode the command can move at most **369 counts
  = 9.0 % of scale.** Measured duty at >=90 % of the limiter **5.0 %**, at 100 % **2.1 %**
  (p50 16.2, p90 85.5, p99 125.1 ct/frame; the 254.4 max is the known two-frame row artifact).
🛑 **`STEER_MAX` and `STEER_DELTA` are openpilot-side and off-limits**
([[feedback-no-openpilot-side-modifications]]). ⇒ **"higher max steering angular velocity" is NOT
deliverable by firmware.** State this plainly rather than continuing to hunt for a cal.

## ⭐⭐ CONCLUSION 2 — THE SAME MEASUREMENT LOCATES THE OSCILLATION, AND THAT **IS** OURS
`CMD->rate` **RISES** monotonically: **+1.2 dB at 1-2 Hz, +6.1 dB at 5-8 Hz, +7.5 dB at 12-20 Hz**,
while the driver's own path through the same plant **FALLS** (-2.3 / -13.6 / -10.4 dB).
🛑 **Same plant, two inputs, opposite slopes ⇒ the high-frequency emphasis is in the LKAS path, not
the mechanics.** That is the grinding / oscillation / ratchet mechanism, it is firmware-side, and it
is consistent with the lightly-damped resonance of
[[accord-ratchet-is-a-lightly-damped-resonance]] (Q 14-29) being *excited* by the LKAS path.
⇒ **The tractable half of the operator's goal is HF de-emphasis in the LKAS path, without adding
impedance** — exactly [[feedback-do-not-buy-ratchet-with-mass-and-friction]].

## ⭐ HOW THIS SPLITS THE STANDING GOAL
| the operator asked for | verdict |
|---|---|
| eliminate grinding / oscillation / ratcheting | **firmware-tractable** — `CMD->rate` is +6 to +7.5 dB above 5 Hz and that is ours |
| higher max steering angular velocity under 6x | 🛑 **NOT firmware-tractable** — the command never carries the motion; the firmware already over-delivers |

## ⚠ CONFIDENCE
[EVIDENCE] for `CMD->rate` rising (coh 0.70 at DC, **0.51** at 1-2 Hz, 0.28 at 5-8 Hz) and for the
driver-path contrast. [EVIDENCE] for the slew and episode-duration arithmetic.
⚠ [BELIEF, direction only] for the exact `demandRate->CMD` numbers — coherence there is **0.06-0.32**,
so the absolute dB values are noise-biased downward. The load-bearing claim is the **ordering**
(CMD attenuated more than rate), which shares an input and survives that bias.
