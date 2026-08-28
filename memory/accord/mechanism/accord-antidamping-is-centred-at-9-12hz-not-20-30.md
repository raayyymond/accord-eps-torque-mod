---
name: accord-antidamping-is-centred-at-9-12hz-not-20-30
description: "Re(Z) across 17 route-arms: ENGAGING flips the impedance from uniformly POSITIVE in manual (+7 to +18 at every band, every route) to deeply NEGATIVE engaged, and the minimum is at 9-12 Hz (-67 on route 21), NOT at 20-30 Hz where the power lives (-3 to -5, crossing positive at f0 ~23 Hz). So a damping lever must target 6-16 Hz. gp-0x6b26 is the one lane measured to supply positive Re(Z) in exactly that band, which is why V94 (removing it) was catastrophic and V106 (tripling it) is the kit's only measured success."
metadata:
  node_type: memory
  type: reference
---

# 🛑🛑★★★★★ THE ANTI-DAMPING IS CENTRED AT **9–12 Hz**, NOT WHERE THE POWER IS

2026-08-27, `Re(Z) = Re(H1[rate → column torque])`, Welch 1024-pt @100 Hz, 17 route-arms.
**Estimator validated against the kit's published figure**: my units are per °/s, the kit's per rad/s;
route 21's 6–9 Hz **−43 × 57.3 = −2464**, and the deepest routes give **−67 × 57.3 = −3839** against
the published **−3375 / −3176 / −3073** ([[accord-rez-antidamping-replicated-three-drives]]). Same
quantity, same order.

## ⭐⭐ THE HEADLINE — ENGAGING FLIPS THE SIGN, AND MANUAL IS CLEAN EVERYWHERE
```
   Hz band      2-4   4-6   6-9  9-12 12-16 16-20 20-24 24-28 28-34 34-42
   r21  ENG       1    -7   -43   -67   -47   -15    -4     3     8     4
   r21  MAN       3     6     7     7     7     8    11    13    15    14
   r78  ENG      -4    -1   -33   -48   -39   -12    -3     5     8     8
   r78  MAN       7     8    12    12    10    12    14    15    16    15
   ra4  ENG      -2    -5   -43   -40   -22    -7    -4     2     3     2
   ra4  MAN       8    11    13    14    16    18    17    17    18    18
```
🛑 **The MANUAL arm is DAMPED at every band on every route that has one** (+3 to +19, no exceptions).
**Engaged, the 6–16 Hz region goes deeply negative.** ⇒ **the anti-damping is entirely a consequence
of engaging** — consistent with [[accord-vibration-requires-lkas-engaged]] (9,200× less power off)
and with [[accord-the-antidamping-is-hondas]] only in that the *region* exists; the **depth** is ours.

## 🛑 THE CORRECTION — 20–30 Hz HAS THE POWER, 9–12 Hz HAS THE INSTABILITY
[[accord-the-oscillation-is-not-command-driven]] measured **20–30 Hz carrying 36.0 % of all rate
power** and I concluded a damping lever should target 20–30 Hz. **That was wrong.** Re(Z) at
20–24 Hz is only **−3 to −5** and crosses positive at `f0 ≈ 23 Hz`; the minimum is at **9–12 Hz,
around −67**, i.e. **an order of magnitude deeper**.
⇒ **20–30 Hz is where a lightly-damped resonance RINGS. 6–16 Hz is where the energy is being PUT IN.**
🛑 **Target the damping at 6–16 Hz. Do not size a damping lever on the 20–30 Hz power.**

## ⭐ f0, THE CROSSING, REPRODUCED ACROSS THE CORPUS
First upward zero crossing above 10 Hz, engaged: **corpus n=17, p50 23.29 Hz**, range 10.15–24.89.
```
  r1e 22.36 | r21 22.93 | r77 24.89 | r78 23.29 | r79 23.22 | r7e 23.40 | r7f 23.42
  r85 22.50 | r95 18.33 | r96 23.98 | r97 21.24 | r9e 23.39 | ra4 24.36 | ra5 24.46 | ra6 24.06
```
⚠ `r81` 10.15 and `r82` 11.19 are outliers on the two smallest engaged samples (n = 4319 / 4613) and
their whole ENG row is shallow — treat as low-power, not as evidence of a moved crossing.
⊕ Consistent with [[accord-f0-crossover-is-the-endpoint]]'s 21.90 / 23.61 / 24.90 Hz at 1× / 4× / 6×.

## ⭐⭐ WHICH LANE SUPPLIES DAMPING IN THAT EXACT BAND — AND IT IS ALREADY KNOWN
`gp-0x6b26` was measured at **+137°/+139° vs wheel rate at 6–9 Hz ⇒ +518/+565 counts of POSITIVE
Re(Z)** ([[accord-v94-flew-and-the-lane-is-a-damper]]) — **inside the deepest anti-damped band.**
That single fact explains both ends of the record:
- **V94 removed 6/6ths of it** ⇒ *"vibrated the entire car … not safe to drive."*
- **V106 tripled it** ⇒ extinguished the 21–27 Hz mode at low speed, the kit's **only** band-power
  result to clear its own split-half null.
⇒ **If the damping class is re-opened, this is the lane, and 6–16 Hz is the target band.**
⚠ The **uniform** dose axis was declared exhausted after V106, and V107's reshape railed
([[accord-gp6b26-is-a-61hz-bandpass-and-v107-railed-it]]) — so a new dose needs a shape argument,
not just a bigger number.

## ⚠ CAVEATS
- Engaged Re(Z) is measured **hands-off** (D3), so `cs_tq` is the torsion bar reading the motor
  working against the column, not driver effort. The manual arm is a different excitation, so the
  ENG/MAN contrast is **directional evidence about the loop**, not a matched experiment.
- Route 21 (V111) at 9–12 Hz is **−67**, the second-deepest in the corpus (r1e/V107 −71). ⚠ Confounded
  by each route's own speed and excitation distribution — **not** a clean build ranking.
