---
name: accord-the-r24-arm-magnitude-decides-the-sign-of-the-kd-axis
description: 2026-09-04, subagent zn39 (docs/research/ZN-BACKWARDS-NO-OVERSHOOT-2026-09-04.md Part III), measurement by grind39/orchestrator on route r39. The 7.3 Hz strong-turn ring is a SUM OF TWO ARMS - the LKAS servo arm (carries Kp and Kd) and the r24 rate-lane arm (carries NEITHER; FUN_0003aa2c has no Kp/Kd reference). A sustained ring requires Ls + Lr ~ +1 in MAGNITUDE AND PHASE, so fixing that measured complex sum (1.0028 angle +0.38 deg) and scaling |Lr| FORCES Ls with no free parameter. Result: at the published arm (Lr 1.19 angle -27 deg) the servo sits at 0.550 angle +96 deg, 123 deg from Lr, and a Kd RAISE damps the ring (|L| 0.909 at Kd 160). If r24 is 3-5x SMALLER, Ls is forced to +8..+16 deg, the arms become nearly CO-PHASED, the servo becomes dominant, and the SAME Kd raise DRIVES |L(7.3)| ABOVE 1 (1.017 at Kd 160, 1.066 at Kd 192) - i.e. it RE-ARMS the cycle V281 rev 3 removed. The r39 measurement lands in the inverted branch: prereg bit-6 duty 0.0908 against a ladder RENORMALISED on r39's own |T| predicting 0.1957 at the flown 5244 arm, i.e. an arm scale ~0.46. The Kp-cut direction is robust across the entire range (0.900 -> 0.769, always sub-unity, BETTER as r24 shrinks). Do not size any Kd move without pinning |r24| first.
metadata:
  type: reference
---

# The r24 arm's MAGNITUDE decides the SIGN of the Kd axis, not just its size - 2026-09-04

## The structure

The 7.3 Hz strong-turn ring is a **sum of two arms**:
- **`Ls`, the LKAS servo arm** - carries `Kp` and `Kd`, so the controller moves it.
- **`Lr`, the r24 rate-lane arm** - carries **neither**. `FUN_0003aa2c` contains no `Kp`/`Kd`
  reference (`gp-0x6ada` 4 hits image-wide; zero matches for `0xCB7D4` across 280 instructions).
  **The controller cannot shrink it.**

## 🛑 THE TEST WITH NO FREE PARAMETER

A naive sensitivity - scale `|Lr|` and leave `Ls` alone - is **REFUTED BY THE MEASUREMENT**: it
predicts `|L_today| = 0.46` against a measured **0.976**. A *renormalised* version (preserve
`|Ls| + |Lr|`) is equally wrong in the other direction: it FORCES the servo arm up when r24 goes
down and hides the sensitivity entirely.

**The correct test:** a sustained ring requires `Ls + Lr ~ +1` in **magnitude AND phase**. The
published arms give exactly `1.0028 ∠ +0.38°`. **Fix that complex sum, fix `Lr`'s phase at −27°,
scale `|Lr|` - and `Ls = SUM − Lr` is FORCED.** No free parameter.

| `Lr` scale | forced `Ls` | angle apart | `\|L\|` Kd 160 | `\|L\|` Kd 192 | `\|L\|` Kp 148 |
|---|---|---|---|---|---|
| 1.000 | 0.550 ∠ +96.0° | 123° | 0.909 | 0.845 | 0.900 |
| 0.600 | 0.494 ∠ +42.1° | 69° | 0.974 | 0.977 | 0.824 |
| **0.333** | 0.676 ∠ +16.1° | 43° | 🛑 **1.017** | 🛑 **1.066** | 0.784 |
| 0.200 | 0.799 ∠ +8.3° | 35° | 🛑 **1.039** | 🛑 **1.111** | 0.769 |

⇒ **At 3-5x smaller r24 the arms stop being anti-phased and become nearly CO-PHASED, the servo
becomes the dominant contributor, and a Kd RAISE RE-ARMS the ring instead of damping it.** That is
the same conclusion the V282 pre-registration's second branch reaches (*"the SERVO is the 7 Hz pump
after all"*), arrived at independently from the measurement constraint.

⭐ **The Kp-CUT direction is robust across the whole range** (0.900 -> 0.769, always sub-unity) and
**gets BETTER as r24 shrinks**, because it attacks the arm that then dominates.

## Where the measurement landed - r39, 2026-09-04

Prereg statistic (A), bit-6 duty `P(|r24| >= |T|)`, engaged/hands-off/creep 1-3 m/s, n = 5,916-5,959:
**observed 0.0908** (orchestrator-verified independently from the generic cache).

🛑 **The ladder MUST be renormalised on the route's own `|T|`** - bit 6 is a *comparison*, and the
published ladder embedded r32/r33/r34's `|T|`. On r39's own `|T|` (p50 71 vs r34/r35's 55, +29 %,
from the 1.70x outer-loop authority increase):

```
  0xC6446 arm            predicted bit-6 duty     |r24| p50    |T| p50
    5244 (flown)               0.1957                 36         160     <- was 0.300 unrenormalised
    2048 (stock)               0.0784                 12         160
    1024 (fault)               0.0387                  4         160
                  OBSERVED:    0.0908
```
⇒ effective arm between the 2048 and 5244 rungs, **scale ~0.46 of the modelled magnitude** - inside
the inverted branch. **Kd 160 interpolates to `|L(7.3)| ~ 0.99-1.00`: a boundary, not a margin.**

## The binding rule

🛑 **Do not size ANY Kd move without pinning `|r24|` first.** The V286 ladder was designed to bound
the floor a Kd *cut* approaches; **it does not bound the ceiling a RAISE approaches**, and the raise
is the move whose sign this number decides.

Related: [[accord-r24-pumps-at-7hz-and-damps-at-20hz-the-same-cell-pulls-the-two-symptoms-opposite-ways]],
[[accord-the-lkas-command-band-is-0-to-075hz-so-inner-loop-fidelity-is-a-dc-statement]],
[[accord-the-rate-pid-in-the-acceleration-frame-is-a-PI-our-P-is-its-integral-and-our-D-is-its-proportional]].
