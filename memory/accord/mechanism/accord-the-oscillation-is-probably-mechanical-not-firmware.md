---
name: accord-the-oscillation-is-probably-mechanical-not-firmware
description: "Three independent measurements now converge on the peak-turn oscillation being a MECHANICAL phenomenon that firmware excites but does not create. Its f0 is invariant to a 2x forward-gain change; its harmonics track neither firmware saturation axis; and its harmonics track NO operating variable at all - flat in speed, in rate and in angle (high/low angle 1.004, CI [0.843, 1.586]) - while still being real against a non-oscillating control (1.233x, CI [1.060, 1.503]). A harmonic signature that is intrinsic to the mode and unmodulated by any operating variable is what a mechanical nonlinearity looks like. This does not mean firmware is irrelevant - the oscillation is engagement-amplified 2.8x and angle-gated, so firmware supplies the excitation - but every firmware excitation path is now closed or exhausted, and a mechanical inspection is worth more than another cal edit."
metadata:
  node_type: memory
  type: reference
---

# 🛑🛑 THE PEAK-TURN OSCILLATION IS **PROBABLY MECHANICAL** — three lines converge

## THE THIRD LINE: the harmonics track NOTHING
The generator was known to be a hard nonlinearity
([[accord-the-7to9hz-mode-is-nonlinearly-excited-harmonics]]). Three candidate amplitudes were
tested, and **all three are flat**:
```
   by SPEED   10-25 1.110 | 25-40 1.159 | 40-65 1.162 | 65+ 1.117    (refutes the +-511 clamp)
   by |RATE|  0-15  1.133 | 15-32 1.096 | 32-60 1.317 | 120+ 1.283   (fails to support the relay)
   by |ANGLE| 0-5   1.102 | 5-10  1.168 | 10-20 1.058 | 20-40 1.377 | 40-400 1.107
              high/low = 1.004   CI [0.843, 1.586]                   (refutes the |model| signum)
```
✅ **Yet the harmonics are REAL**: 1.233× against a **non-oscillating-window** control,
CI [1.060, 1.503], route-bootstrapped.
⇒ **The harmonic signature is INTRINSIC to the mode and unmodulated by any operating variable.**
That is what a **mechanical** nonlinearity looks like — whenever the mode rings, it rings nonlinearly,
in the same proportion, regardless of how the car is being driven.
🛑 It also kills the last firmware-generator hypothesis: the **`|model|`-scaled signum**. `|model|`
rises **7-9×** with angle, so if it set the generator's amplitude the harmonics would be angle-gated.
**They are not.**

## THE THREE CONVERGENT LINES
1. **`f0` is invariant to a 2× forward-gain change** (Spearman −0.015, p 0.954) ⇒ a fixed mechanical
   resonance, not a relocatable pole — [[accord-the-78hz-mode-does-not-move-with-firmware-gain]].
2. **The harmonics track neither firmware saturation axis** —
   [[accord-the-harmonics-track-neither-firmware-saturation]].
3. **The harmonics track no operating variable at all** (this note).
⊕ Consistent with the ring-down (ζ 0.017-0.036, **Q 14-29**, motor/rack-side) and with the 6-9 Hz
anti-damping being **present in stock** ([[accord-the-antidamping-is-hondas]]).

## ⚠ THIS DOES NOT MEAN FIRMWARE IS IRRELEVANT
The oscillation is **engagement-amplified 2.8×** and **angle-gated**, and the 7-9 Hz energy is
**manufactured downstream of the command** (26.5× more relative content in the response than the
command). ⇒ **firmware supplies the EXCITATION; the mechanics supply the MODE and its nonlinearity.**
🛑 But every firmware excitation path is now closed or exhausted:
```
   move the mode            REFUTED  (f0 invariant)
   damp it more             MEASURED-CLOSED  (the +-511 rail; 0xC407E faults if raised)
   relay knee               SATURATING -- 1800->3000 removes 0.25x what 600->1800 did
   model bandwidth 0xC50D8  GATE 2 BLOCKED (+63.4 deg phase, sign undetermined)
   3-tap FIR notch          ARITHMETICALLY CLOSED (a notch there kills DC)
   Coulomb floor 0xC4080    NEVER-RAISE, corroborated
   alpha2                   COSTS the damper 4.3 % -- it helps grind #1, not this
```

## ✅ WHAT IS ACTUALLY WORTH DOING NOW
🛑 **A mechanical inspection is worth more than another calibration edit.** A lightly damped
**Q 14-29** mode at **7.8 Hz** with an intrinsic nonlinearity, on the motor/rack side, is the
signature of **lash or a worn compliant element** — the usual suspects being the **intermediate-shaft
U-joints, the steering rack bushings, the tie-rod ends, and the EPS motor-to-rack coupling**.
⚠ **[BELIEF, three convergent measurements.]** Nothing here diagnoses a specific part, and the kit
has no mechanical instrumentation. **It is a direction to check, not a diagnosis.**
⊕ If a mechanical cause is found and fixed, the firmware work already done still stands — V122's
grind-#1 lever and authority gain are independent of it.
Tool: `rlog-tools/studies/peakturn/harmonic_vs_angle.py`.
