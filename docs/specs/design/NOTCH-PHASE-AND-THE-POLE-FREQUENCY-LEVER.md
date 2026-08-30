# The notch is a PHASE device, and its pole frequency is an unswept lever

**2026-08-30.** Status: **EVIDENCE** for items 1–4, **UNRESOLVED** for the sign. Nothing here is flown.

## 1. The kit has treated the biquad as a magnitude device for 40+ builds

`0xC60A8/AC/B0/B4` is a float32 direct-form II section at 1 kHz. Every build note, every design sweep
and every drive card discusses it as a **notch** — how deep, how wide, centred where. Its **phase** has
never appeared in the record. But a 2nd-order section moves phase over a far wider span than it moves
magnitude, and the spillover lands in exactly the bands the kit cares about.

Read from the **encoded float32 in each image** (`resp()` in `build_v222_tva.py`):

| build | a8 | ac | 7.79 Hz | 10.5 Hz | 18.5 Hz |
|---|---|---|---|---|---|
| car (V122) | −1.5372 | 0.6346 | 0.9829 / −10.6° | 0.9686 / −14.4° | 0.8978 / −26.1° |
| V105–V107 | −1.8819 | 0.9025 | 0.9863 / −14.6° | 0.9676 / −21.3° | 0.7107 / −55.5° |
| **V208–V228** | −1.9059 | 0.9168 | 0.9796 / **−25.4°** | 0.9257 / **−39.3°** | 0.2045 / −102.0° |

## 2. The whole notch arc is UNFLOWN

Grouping all 199 images by biquad and intersecting with the route→build map: every cached route flew
either −14.4° (V90–V104, V111–V122) or −21.3° (V105–V107) at 10.5 Hz. **V172→V228 — 40+ builds,
including every one of V202–V228 — has never produced a flown route.** So the 9–12 Hz behaviour of the
current geometry is not merely unmeasured, it is unobserved.

This matters because 9–12 Hz is the band the kit's own instrument calls the most energetic:
Re(Z) −65.4 [−69.2, −61.4], a CI overlapping no other band, P(most anti-damped) = 1.000.

## 3. The lag comes from the POLE FREQUENCY, not the width

V208's `ac` = 0.9168 ⇒ r = 0.9575; `a8` = −1.9059 ⇒ cosθp = 1.9059/(2·0.9575) ⇒ **poles at 15.52 Hz,
zeros at 20.50 Hz**. Poles *below* zeros is what drags lag down into 9–12 Hz. A first sweep over pole
**radius** at fixed angle found only a weak trade; the pole **frequency** is the real free parameter and
has never been swept.

## 🛑 CORRECTION (same day) — SECTION 4'S ALTERNATIVE IS WITHDRAWN AS AN IMPROVEMENT

Section 4 below proposes poles at 18.00 Hz as a "ready alternative". **It was sized on two axes and
there are three.** On the third it is worse than V228 and over a line the record already drew:

```
                        V228 (poles 15.52)   ALT (poles 18.00)
  grind 15-22 vs car     0.17x (-15.4 dB)     0.24x (-12.4 dB)    ALT cuts LESS
  9-12 Hz phase          -24.8 deg            -12.6 deg           ALT better
  54-74.5 Hz vs car      4.23x (+12.5 dB)     5.43x (+14.7 dB)    ALT WORSE, and above the
                                                                  5.15x the lineage called unshippable
```

**V228's geometry beats it on two of three axes.** Read section 4 as a record of the sweep, not as a
recommendation.

## ⭐ THE REAL MECHANISM — Honda's biquad IS a 55 Hz notch

```
  car / Honda   zeros 55.23 Hz, poles 42.35 Hz   deepest cut 55 Hz, |H| = 0.0063  (159x)
  V228          zeros 20.50 Hz, poles 15.50 Hz   deepest cut 21 Hz, |H| = 0.0433

                |H| 18.5 Hz   |H| 55 Hz   |H| 65 Hz
  car / Honda      0.8978      0.0063      0.2472
  V228             0.2045      0.6285      0.6457    <- 100x louder at 55 Hz
```

There is **one** biquad. The kit has been **relocating** it since V172, not adding one. The 54-74.5 Hz
lift is not the new notch adding noise -- it is **Honda's 55 Hz cut being vacated**. One 2nd-order
section cannot notch 18 Hz and 55 Hz; the tradeoff is structural and no choice of (fz, fp, r) escapes
it. Cutting 15-22 Hz with this cell ALWAYS costs the 55 Hz cut.

**Never flown.** The car carries Honda's 55 Hz notch intact, so V228 would be the first build driven
that gives it up. And CAN's Nyquist is 50.5 Hz, so only the audio arm can measure the cost.

## 4. A ready alternative geometry

2-D sweep over (pole freq, radius), zeros fixed at 20.50 Hz, constrained to keep the grinding cut, to
neither cut nor boost 6–9 Hz, and to have no resonant peak below the notch:

```
  poles 18.00 Hz, r 0.9625
    a8 = -1.91270177   ac = 0.92640625   b0 = -1.98343212   b4 = 0.82717146

                        V228          poles-18.0        car
    grinding cut 18.5   4.84x           3.37x           1.11x
    9-12 Hz phase       -24.8 deg       -12.6 deg        0 (ref)
    6-9 Hz  |H|         0.9796          0.9808          0.9829
    peak |H| 0.5-30 Hz  --              1.0000           --
```

**It halves the 9–12 Hz phase excess and costs 30 % of the grinding cut.**

🛑 **A one-sided constraint nearly shipped a resonance.** The first sweep ran `|H|7.79 >= 0.97`
with no upper bound, so an unbounded boost scored perfectly on phase: it returned poles at 13.25 Hz,
r = 0.9950 — a **Q≈100 resonance boosting 7.79 Hz by 1.32×**, in the ratchet band. Every magnitude
constraint on a notch design must be **two-sided**, with a peak-gain guard across the whole low band.

## 5. THE SIGN IS UNRESOLVED, and the corpus cannot resolve it

Which way to push is **not known**. `rez_spectrum.py` already flags the Re(Z) sign frame as unresolved.
I tried to settle it from the natural experiment (V105–V107's −21.3° vs everything else's −14.4°,
a 6.9° lever arm):

```
  episode-level bootstrap   -8.53  [-14.62, -0.58]   excludes zero   <- TOO NARROW
  route-level bootstrap     +1.77  [-21.87, +10.53]  SPANS ZERO      <- the honest one
```

The point estimate **flips sign** between them. 113 episodes in one arm came from 3 routes and 334 from
14; episodes inside a route are no more independent than windows inside an episode. The route is the
unit of randomisation. And even the route-level contrast is fully confounded with build order —
V105–V107 is one contiguous block.

⇒ **The sign frame needs a deliberate drive; it is not in the corpus.** Until then the conservative
reading is that **closer to the car is safer in a band nobody can reason about** — which is an argument
for the poles-18.0 geometry, not a measurement favouring it.

## What would settle it

One drive on V228 (−39.3°) against one on a poles-18.0 build (−26.9° absolute) with **everything else
byte-identical**, scored at 9–12 Hz. That is a clean 12.4° single-variable contrast — the corpus's is
6.9° and confounded with a whole build. **Not worth cutting until V228 has flown**, because if V228 is
acceptable the question is moot.
