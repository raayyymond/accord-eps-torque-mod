---
name: reference-accord-steeringpressed-mask-excludes-the-symptom-regime
description: "The kit's hands-off mask is |STEER_TORQUE_SENSOR| > 1200 — a threshold on the NUMERATOR of Re(Z). It does not merely contaminate Re(Z) below 6 Hz (2-4 Hz reverses sign); it EXCLUDES the regime in which the operator produces the symptom, because he produces it by OVERRIDING and override is steeringPressed == True by definition."
metadata:
  type: reference
---

# 🛑🛑★★★★★ THE `steeringPressed` MASK EXCLUDES THE SYMPTOM REGIME

Two facts, the second far more important than the first. Established 2026-08-12.

## 1. THE MASK IS A THRESHOLD ON THE MEASURED SIGNAL [EVIDENCE]

```
opendbc/car/honda/carstate.py:163
    ret.steeringPressed = abs(ret.steeringTorque) > STEER_THRESHOLD.get(fingerprint, 1200)
HONDA_ACCORD (10th gen) is NOT in the override dict  =>  T = 1200
ret.steeringTorque = cp.vl["STEER_STATUS"]["STEER_TORQUE_SENSOR"]   <- THE NUMERATOR OF Z
```
Measured: `press == (|cs_tq| > 1200)` on **99.28–99.96 %** of frames on every route, and a free
threshold fit returns **exactly 1200** every time.

Because `runs_of` requires **every** frame of a window to pass, one excursion to ±1200 in 5.12 s
kills the window. It drops **39 % of engaged and 93 % of manual** candidate windows, and the dropped
windows carry **3.91×** the 6–9 Hz torque in the engaged arm against **1.20×** in the manual arm —
**arm-asymmetric by 3.3×, so it does not cancel in a contrast.**

| band | D0 strict (the old mask) | D3 band-orthogonal | verdict |
|---|---|---|---|
| 2–4 | −1312 [−1399,−1215] | **+612** | 🛑 **SIGN REVERSES** |
| 4–6 | −1608 | −561 | 🛑 −65 % of magnitude |
| **6–9** | **−3383** | **−3394** | ✅ invariant, 16 counts |
| 9–12 / 12–16 / 18–22 | −4698 / −4457 / −697 | −5102 / −3731 / −603 | ✅ within 16 % |

⇒ **Do not quote `Re(Z)` below 6 Hz from a `steeringPressed` mask.** Fix: `D3 = window-median
|cs_tq| < 1200` — a median over 512 samples has no leverage from 2–38 Hz content. ⚠ **No
torque-independent hands-on sensor exists on this car**, so D3 is band-orthogonal, not torque-free.

## 2. 🛑🛑 THE FAR BIGGER PROBLEM: THE MASK REMOVES THE SYMPTOM

The operator, 2026-08-12: ***"Steering override is how I get the steering into such a scenario where
grinding and micro ratcheting can be observed."*** He engages LKAS, then **overrides** — turns the
wheel against the command. **Override is `steeringPressed == True` by definition.**

⇒ **Every `Re(Z)` number this kit has ever produced comes from a mask that excludes the exact
condition in which the symptom occurs.** The instrument was pointed away from the symptom, and the
exposure followed it: the corpus holds **7121.6 s of engaged hands-off against 994.9 s of engaged
hands-on.** The grip finding — that a hand on the rim changes the sign — was being treated as a
confound to exclude. **It is the target.**

**And the two regimes give different answers.** At 6–9 Hz:
- hands-OFF, rate- and speed-matched: engaged/manual `Re(Z)` ratio **1.24×**, CIs overlapping.
- **hands-ON (the symptom regime), band POWER, grip matched out on both arms: OVR/MAN-ON =
  1.43 / 1.65 / 1.74 / 1.93 / 2.22 / 2.25 / 2.35 / 2.38 / 2.55 / 2.90 — every one of 10 routes
  above 1.4, median ≈ 2.2×.**

Both are correct and they measure different things. **`Re(Z)` is LATENT** — it says energy *would*
grow if excited; hands-off there is almost no excitation (manual 6–9 Hz coherence 0.040 against a
1/n ≈ 0.014 bias floor). **Band power is the FELT quantity.** The operator's report —
*"literally every bad symptom is LKAS engaged only"* — **is confirmed by the amplitude instrument in
his own regime**, and agrees with the standing [[accord-engagement-amplifies-6-9hz]] (2.8×).

## 🛑 HOW TO APPLY
- **Score symptoms in the regime the operator drives in: ENGAGED, HANDS-ON, OVERRIDE.** Score them on
  **band power**, not impedance — amplitude is what corresponds to a felt symptom, and it does not
  inherit the mask's selection effect.
- **`Re(Z)` remains valid for what it measures** (latent loop damping, hands-off, ≥ 6 Hz) and is
  still the right tool for pricing a damping lane. It is **not** a symptom instrument.
- 🛑 **Override does not support the kit's band estimator at all.** 5013 contiguous override runs
  make up the corpus's 994.9 s: median run **0.02 s**, p90 0.55 s, and only **SEVEN** runs corpus-wide
  reach 5.12 s. Use point-process and event-triggered methods, or 1.28 s windows, and say which.

## REPRODUCE
`rlog-tools/v95_rez_polarity_and_mask.py` (§1) · `rlog-tools/v95_override_exposure.py` (exposure) ·
`rlog-tools/v95_override_onset_ringing.py` §2 (the hands-on amplitude contrast).

Links: [[reference-accord-rez-anchored-on-car-and-its-floor]] · [[accord-engagement-amplifies-6-9hz]]
· [[accord-ratchet-axis-is-wheel-rate]] · [[accord-vibration-requires-lkas-engaged]] ·
[[reference-accord-vibration-needs-applied-torque]] ·
[[accord-averaged-spectrum-needs-matched-speed-distributions]]
