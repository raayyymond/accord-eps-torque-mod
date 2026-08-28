---
name: accord-two-symptoms-two-mechanisms-rez-spectrum
description: "The fine Re(Z) spectrum on V112 (routes 22+23, 0.5 Hz bins, coherence 0.5-0.85) shows ONE broad anti-damped feature spanning 3.0-23.5 Hz, peaked at 8-12 Hz (-81) and crossing zero at f0 = 23.28 Hz. The peak-turn oscillation at 7.42 Hz sits on its rising edge and IS this instability. Grind #1's band (18-22 Hz) measures only -1 to -10 -- nearly neutral -- so grind #1 CANNOT be an Re(Z) instability and must be a different mechanism."
metadata:
  node_type: memory
  type: reference
---

# ⭐⭐★★★★★ TWO SYMPTOMS, **TWO DIFFERENT MECHANISMS** — the fine `Re(Z)` spectrum says so

2026-08-27. V112, routes 22 + 23 pooled, engaged & low-torque & moving, Welch 2048-pt (20.5 s
windows) @100 Hz, averaged into 0.5 Hz bins. **No stock arm needed — this is within-build and
adequately powered** (coherence 0.5–0.85 through the feature).

```
   Hz    3.0    5.0    6.0    7.0    7.5    8.0    9.0   10.0   12.0   13.0
  Re(Z)   -0     -6    -15    -35    -51    -81    -67    -64    -79    -60
  coh2  .024   .074   .243   .465   .626   .756   .647   .618   .596   .486

   Hz   15.0   16.0   17.0   18.0   19.0   20.0   21.0   22.0   23.0   23.5
  Re(Z)  -31    -20    -16    -11    -10     -6     -4     -3     -1     +1
  coh2  .471   .392   .446   .500   .792   .842   .817   .535   .228   .082
```
**ONE broad anti-damped feature, 3.0 → 23.5 Hz, peak −81 at 8 Hz, zero crossing f0 = 23.28 Hz.**
⊕ f0 agrees with the corpus-wide 17-route estimate of **23.29 Hz**
([[accord-antidamping-is-centred-at-9-12hz-not-20-30]]) — two methods, same number.

## 🛑 THE SEPARATION — and it changes the search
| symptom | frequency | `Re(Z)` there | verdict |
|---|---|---|---|
| **peak-turn oscillation** | **7.42 Hz** | **−32, rising into the −81 peak at 8 Hz** | **IS this instability** |
| **grind #1** | ~18–22 Hz (V62's measured band) | **−1 to −10, essentially neutral** | **CANNOT be this instability** |

⇒ **Stop treating them as one problem.**
- The **peak-turn oscillation** is the `Re(Z)` instability. Its fix must add positive `Re(Z)` at
  **8–12 Hz**, where the deficit is deepest.
- **Grind #1 is something else** — a nonlinearity, a relay, or mechanical noise — because the linear
  loop is nearly neutral in its band. **A damping lever cannot fix grind #1**, and the fact that
  V112's relay-knee raise *did* move grind #1 while the relay tests failed to explain the 7.42 Hz
  oscillation is consistent with exactly this split.

## ⚠ WHAT THE SHAPE IS *NOT*
A pure transport delay was tested against the shape and **fails**. `Re(Z) = −K·cos(ωτ)` with
`τ = 1/(4·f0) = 10.74 ms` (suggestively ~one 100 Hz frame) predicts the zero crossing correctly but
demands `Re(Z) ≈ −0.98K` at 3 Hz, where the measurement is **≈ 0**. The feature is **band-limited**,
rising from zero at ~3 Hz — not a delay acting on a broadband rate-proportional term.
🛑 **Do not propose a delay-compensation fix on the strength of the f0 coincidence.**

## SIZING THE AVAILABLE LEVER AGAINST THIS DEFICIT
`gp-0x6b26` supplies **+518 counts/rad/s = +9.0 per °/s** at 6–9 Hz (V94 flight) against a deficit of
**−81 per °/s at 8 Hz** ⇒ the lane is worth ~**11 %** of the deficit at its peak, and α2 14→8 raises
that by 25 % ⇒ **~2.8 % of the deficit**. Consistent with the independent 5.3 % estimate in
[[accord-antidamping-is-a-state-effect-of-engaging]]. **The lane is not the fix.**

Related: [[accord-the-742hz-mode-is-stocks-and-our-q-is-lower]] ·
[[accord-v112-flew-best-yet-and-the-peak-turn-oscillation]]
