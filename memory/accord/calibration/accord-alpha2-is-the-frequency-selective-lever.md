---
name: accord-alpha2-is-the-frequency-selective-lever
description: "alpha2 (0xC40DC) sets the gp-0x6b26 lane's EMA corner at alpha2/64, and because the lane is a differentiator its response RISES with frequency - so lowering alpha2 cuts high frequencies far more than low ones. Measured at 1 kHz: alpha2 14 to 8 gives 0.993x at 3 Hz (the LKAS command band, untouched), 0.957x at 7.8 Hz (the damper, -4.3 percent) and 0.783x at 23.4 Hz (grind #1's peak, -21.7 percent) - a selectivity of 5.07x toward grind #1 and away from the damper. This is the frequency-selective lever the kit had concluded does not exist. V109's already-flown 22 to 14 step was selective the same way and flew fault-free on V111 and V112, and V115 (alpha2 14 to 8) is already built."
metadata:
  node_type: memory
  type: reference
---

# ✅✅ `alpha2` **IS** THE FREQUENCY-SELECTIVE LEVER — and V115 already exists

## WHY IT IS SELECTIVE, structurally
`alpha2` = `cal(0xC40DC)` is the EMA-A coefficient in `FUN_00041464`, applied as
`state += (diff * alpha2) >> 6` ⇒ **alpha = alpha2/64**. Its input is a **first difference**
([[accord-gp6b26-is-inertia-not-damping]], pinned in assembly at `0x41602 sub r7,r9`), so the lane is
`|1 - z^-1| * |H_ema|` — **a differentiator whose response RISES with frequency.**
⇒ **lowering `alpha2` pulls the EMA corner down, which cuts HIGH frequencies far more than low ones.**
That is selectivity by construction, not by tuning.

## [EVIDENCE] The measured shape, 1 kHz task
```
   freq       a2=22      a2=14      a2=8      8/14      what lives there
    3.0 Hz   0.018831   0.018795   0.018665   0.993x    LKAS command band -- UNTOUCHED
    7.8 Hz   0.048680   0.048071   0.046008   0.957x    the oscillation / the damper  -4.3 %
   21.0 Hz   0.125913   0.116367   0.093856   0.807x    grind #1 lower
   23.4 Hz   0.138812   0.126319   0.098848   0.783x    GRIND #1 PEAK               -21.7 %
   26.0 Hz   0.152307   0.136233   0.103388   0.759x    grind #1 upper
   50.0 Hz   0.251820   0.194102   0.122891   0.633x
```
✅ **SELECTIVITY = 5.07× more cut at grind #1 than at the damper**, and **0.993× at 3 Hz** ⇒ the LKAS
command band, where steering velocity and acceleration live, is **effectively untouched**.
✅ **This satisfies the operator's standing constraint by construction**: it removes loop gain at
21-26 Hz **without adding mass, friction or inertia**, and without touching the band the LKAS command
occupies.

## ✅ THE SAFETY GATE PASSES, AGAINST THE KIT'S OWN WORST PRECEDENT
The same lane is what **V94 cut 6× (to 0.167×)**, after which the operator **aborted the drive**
(*"vibrated the entire car"*), and its delivered phase is **+137°/+139° vs wheel rate = a real 6-9 Hz
damper** ([[accord-the-added-lkas-mass-is-the-damper-that-works]]).
✅ **`alpha2` 14 → 8 costs only 4.3 % of that damper — 1/20th of the change that caused the abort.**
✅ **And the precedent is already flown**: V109's `alpha2` 22 → 14 was selective the same way
(damper −1.3 %, grind #1 −9.0 %, **selectivity 7.19×**) and flew **fault-free on V111 and V112** — the
operator's best builds. **V115 is the next step on an axis that has already flown twice.**

## ⇒ V115 IS THE RECOMMENDED FLIGHT FOR GRIND #1
`V115` = V112 base + `0xC40DC` 14 → 8. **Already built and unflown**: image `5f804a8a…`, rwd
`f1a47bb7…`, **42/42 assertions**, cal-only.
It is now supported by **four independent things**: a measured **amplitude** dose-response on the
corrected band (1.340 [1.12, 2.29]), a measured **frequency** shift (1.113 [1.06, 1.17], p 0.035), a
**structural** selectivity argument (5.07×), and a **flown precedent** (V109→V111/V112, fault-free).
🛑 **CAVEATS, unchanged:** `alpha2 = 14` exists only on V111/V112 (**3 routes**) so the empirical
half is **collinear with build era**; the selectivity arithmetic assumes the **1 kHz** task rate for
`FUN_00041464`; and `alpha2` also cuts **35-50 Hz by 30-37 %**, which is grind #2 territory — likely
helpful, **not verified**.
⇒ **Sequence: V115 first** (more selective, better gated, precedent flown), **then V121**.
Tool: `analysis-2020accord/verify/alpha2_frequency_selectivity.py`.

## ✅ THE `alpha2` DOSE LADDER, AND ITS FLOOR — so the next step is chosen, not improvised
```
   a2   EMA corner   3 Hz cmd   7.8 Hz damper   23.4 Hz grind#1   selectivity   note
   14     34.8 Hz     1.000x       1.000x           1.000x           --        CURRENT (V111/V112, flown)
   12     29.8 Hz     0.999x       -0.8 %           -5.0 %          6.47x
   10     24.9 Hz     0.997x       -2.0 %          -12.0 %          5.87x
    8     19.9 Hz     0.993x       -4.3 %          -21.7 %          5.07x      <- V115, BUILT
    6     14.9 Hz     0.985x       -8.7 %          -35.2 %          4.04x      the practical knee
    5     12.4 Hz     0.977x      -12.7 %          -43.7 %          3.44x      caution
    4      9.9 Hz     0.963x      -18.8 %          -53.2 %          2.83x      caution
    3      7.5 Hz     0.934x      -28.7 %          -63.9 %          2.23x      toward the V94 direction
```
✅ **A PRINCIPLED FLOOR:** the EMA corner falls with `alpha2`, and **at `a2 = 4` it reaches 9.9 Hz —
BELOW the 23.4 Hz target and close to the 7.8 Hz mode.** Past that the filter **eats the damper faster
than it eats the grind**, which is why selectivity collapses from 5.07× to 2.83× and then 1.27×.
⇒ **`alpha2 >= 6` is the usable range; `alpha2 <= 4` is the V94 direction.**
⇒ **FLY V115 (`a2 = 8`) FIRST, NOT a bigger dose.** It is already built (42/42), it is the smaller
step from the flown 14, and the empirical half of the `alpha2` case rests on **3 routes**. **`a2 = 6`
is the identified next step** — it nearly doubles the grind cut (−35.2 % vs −21.7 %) for a damper cost
of **−8.7 %**, still ~10× smaller than V94's −83 % — **but only after V115 shows the axis works on the
road.** 🛑 **Do not build `a2 = 6` yet**: seven unflown artifacts already exist, and a bigger dose
flown first would confound a larger effect with a larger cost.
