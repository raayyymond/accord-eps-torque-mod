---
name: accord-firmware-adds-torque-to-bar-engaged-at-low-speed
description: "★★★★★ At MATCHED column acceleration and matched speed, the engaged torsion bar carries 2.77× (6–9 Hz) and 1.66× (17–23 Hz) more torque than manual at 2–8 m/s, with the pre-declared 26–31 Hz control at 1.04. Purely inertial coupling would give 1.00 ⇒ the FIRMWARE adds torque, engaged, at low speed, in exactly the symptom bands."
metadata:
  node_type: memory
  type: reference
---

The discriminating measurement of the 2026-08-09 V85 session. A **purely inertial** reaction torque
cannot care what is driving the column, so at matched `θ̈` it must be **identical** engaged vs manual.
It is not.

Model: `log(bar) = a + b·log(θ̈) + c·1[engaged] + d·log(1+v)`, episode bootstrap, arms cut to a common
speed window first (unwindowed, the arms differ by ~9 m/s in median and are unusable).

| speed window | band | K eng | K man | b | **exp(c) = ENGAGED / MANUAL** |
|---|---|---|---|---|---|
| **2–8 m/s** | **6–9 Hz (S2)** | 15 | 27 | 0.81 | **2.77 [2.29, 3.32]** |
| **2–8 m/s** | **17–23 Hz (S1)** | 15 | 27 | 0.79 | **1.66 [1.29, 2.06]** |
| **2–8 m/s** | 26–31 Hz *(pre-declared NEGATIVE CONTROL)* | 15 | 27 | 0.81 | **1.04 [0.83, 1.23]** ✓ |
| 8–20 m/s | 6–9 / 17–23 / 26–31 | 47 | 6 | ~0.9 | 1.66 / 1.32 / **0.62** |
| 15–30 m/s | 6–9 / 17–23 / 26–31 | 29 | 10 | ~0.9 | 0.97 / 1.03 / **0.49** |

**⇒ The excess is confined to LOW SPEED and to EXACTLY the two symptom bands.** That is the symptom map,
recovered from an independent measurement.

## 🛑 Caveats, found by the orchestrator re-reading the cached numbers — do not quote this without them
1. **The negative control FAILS above 8 m/s** — it reads **0.62** and **0.49** where it must read 1.00.
   So the model is biased in those windows and *"the excess vanishes at highway"* is **NOT supported**.
   **Only the 2–8 m/s row (control 1.04) is clean**, and it is the row carrying the headline.
2. **Residual speed confound inside that window**: engaged median 5.40 m/s vs manual 2.99 m/s.
3. The manual arm is **pooled** across six caches (V80/r66 K=24, plus r5d/r54/r3b/r5a/r47 at 3–8 each).
4. The **transfer-function** contrast is separately **REFUSED** — the manual arm's γ² at 7.79/20.5 Hz is
   0.09/0.04, far below the pre-registered 0.5 floor. **What is reportable is the band-power contrast
   above, not a coupling-gain ratio.**

## What it does and does not license
✅ *"The firmware adds torque to the driver-side signal, engaged, at low speed, in the symptom bands."*
❌ *"The coupling is purely inertial."* Refuted — that is the whole point.
❌ A clean speed-matched contrast. It is not one.

## Two mechanisms consistent with it, neither isolated
- [[accord-fun3b8f6-coulomb-relay-proportional-to-command]] — `FRICTION ∝ |model| ∝ delivered command`,
  engagement-scaled with no engagement flag. Low-pass shaped (α = 408/4096 ⇒ ~16.7 Hz corner), which
  matches the falling 2.77 → 1.66 → 1.04 profile in direction though not in detail.
- **`FUN_0003a382`'s gain scheduling on `gp-0x6ac0` (rectified motor rate):** the **P** gain table
  (`0xC6B1C..2C`) *falls* 256 → 153 as motor rate rises 300 → 4000 counts, while the **D** gain table
  (`0xC6AE0..EC`) stays **flat at 2048 (=2.0)**. ⇒ the loop's weighting shifts toward the **unfiltered
  derivative** exactly when the motor is spinning fast, i.e. under aggressive commanded motion —
  engagement-correlated with no engagement flag. **[BELIEF]** — structurally coherent, never isolated
  on-car. 🛑 **The D-GAIN TABLE has never been touched by any build; only the D POLE (`0xC644A`, V43)
  and the P POLE (`0xC6450`, V46) were, and both were NULL.** "The D term is falsified" is NOT
  established — only *smoothing* it is.

## Physics context that constrains any fix
The **wheel-on-torsion-bar mode is at 12.8 Hz [12.1, 13.6]** (ζ ≈ 0.15, six route-arms, split-half
agreement <5%) — **between** the two symptom bands. Below it the bar reads **inertial** (6/6 arms
agree); above it, **stiffness** (5/5). ⇒ **a single-gain `θ̈` feedforward cancellation tuned at 7.79 Hz
arrives at 20 Hz INVERTED.** Doing it properly needs a resonant biquad ⇒ a cave ⇒ the bricking class.
⚠ Corrects `docs/FEASIBILITY-SELF-INTERFERENCE-CANCELLATION.md` twice: its `f₀ = 6.8–11.4 Hz` bracket is
**not supported** (measured 9.8–14.7, median 12.8) so **the 7.79 Hz ratchet is NOT the wheel-on-bar
mode**; and its *"~17× more lightly damped than V48B"* margin is wrong by ~10× (measured pole radius
**0.98823** vs V48B's 0.979 = **1.8×, the SAME CLASS**). **The NO-GO survives; the margin argument must
not be re-quoted.**

⊕ New structural fact, τ-free and calibration-free: **`0x14A`'s angle/rate is BELOW the torsion bar**
(motor/pinion side) — `|T/θ̇|` *falls* 2–9× from 13→27.5 Hz on every route and both conditions, where a
wheel-side sensor requires it to *rise*. ⊕ `0x14A` STEER_ANGLE and STEER_WHEEL_ANGLE are **byte-identical
on 280,598/280,598 frames** ⇒ `rlog-tools/decode_two_angles.py`'s premise is void.
⊕ `tq`'s LSB is **8**, not 1; `ang` repeats on **74%** of frames.

Tools: `rlog-tools/selfint_*.py`, cache `_cache_selfint/`.
See [[accord-loop-does-not-close-through-openpilot]].
