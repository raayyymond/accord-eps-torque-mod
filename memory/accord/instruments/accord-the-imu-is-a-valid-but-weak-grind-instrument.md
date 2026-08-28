---
name: accord-the-imu-is-a-valid-but-weak-grind-instrument
description: "The IMU logs at 100 Hz on every route so Nyquist is 50 Hz and the 18-22 Hz grind band is genuinely visible. Validated on the Lever B natural experiment it does discriminate - OFF/ON = 1.139 with a route bootstrap CI of [1.005, 1.338] - but it recovers only 1.139x where the steering-rate instrument recovers 2.32x for the same known effect, so it is diluted about 10x by road, tyre and drivetrain input. Its unique value is that it needs NO creep exposure, which is exactly what makes grind #1 unmeasurable on every post-V107 route. Usable only for effects larger than roughly 3x, and only a positive result is informative."
metadata:
  node_type: memory
  type: reference
---

# ✅⚠ THE IMU IS A **VALID BUT WEAK** GRIND-#1 INSTRUMENT

## Why it was worth trying
Every grind-#1 measure so far uses **steering rate**, which needs the 2-5 mph creep exposure that
**no post-V107 route has** ([[accord-grind1-is-unmeasurable-on-the-recent-routes]]). Grind #1 is
**audible and felt** — the operator's V94 report was *"it vibrated the entire car"* — so a chassis
accelerometer measures it directly and needs no steering exposure at all.
✅ **`imu_vert` / `imu_lat` log at 100 Hz on all 17 routes** (length ratio 1.00 against `cs_rate`,
checked before anything else) ⇒ **Nyquist 50 Hz, so 18-22 Hz is genuinely visible, not aliased.**

## [EVIDENCE] Validated on the Lever B natural experiment — and it is weak
Outcome: IMU-vertical 18-22 Hz as a share of 1-45 Hz, p90, **engaged vs manual within the same
drive** so road surface and speed largely cancel.
```
   Lever B OFF (2 routes)  median eng/man = 1.2020
   Lever B ON  (9 routes)  median eng/man = 1.0552
   OFF/ON = 1.139   route-bootstrap CI [1.005, 1.338]
```
✅ **It discriminates** — the CI excludes 1.0. 🛑 **But only just** (lower bound **1.005**), and it
recovers **1.139×** where the steering-rate instrument recovers **2.32×** for the *same* known effect
(true on-car value 0.40 ⇒ about 2.5×).
⇒ **dilution about 10×**: a true effect `X` appears as roughly `1 + (X-1)/10.8`. **To clear its own
noise floor the IMU needs a true effect above about 3×.**
⚠ Also `n = 2` OFF routes, and manual-arm window counts are small (28-99), so precision is
inherently limited.

## ⇒ HOW TO USE IT, AND HOW NOT TO
✅ **Use it** as the *only* grind-#1 instrument that works on routes with **no creep exposure** — i.e.
every recent drive. Complementary to, not a replacement for, the steering-rate measure.
🛑 **Do not use it to declare a null.** At about 10× dilution, *"the IMU shows nothing"* is
consistent with a real 2× change. **Only a POSITIVE IMU result is informative; a negative one is
uninformative.**
⚠ **Validated at 18-22 Hz only** — re-validate before using it at 6-9 Hz.
Tool: `rlog-tools/studies/peakturn/imu_grind_instrument.py`.
