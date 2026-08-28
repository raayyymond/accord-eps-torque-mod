---
name: accord-K1-is-the-angle-gated-antidamping-and-V113-is-the-fix
description: "The chain is now closed end to end with measurements: the oscillation excess is angle-gated (exposure-controlled); |model| measured via the cave's b5 rung rises 7-9x monotonically with steering angle on two independent routes; the friction term is |model| x K1/1024 x sat(rate), in phase with rate and therefore anti-damping; and K1 is x6 on stock. V113 is exactly V112 with K1 612 -> 204, cutting that term to 0.333x. V113 was wrongly deprioritised and is now the recommended flight."
metadata:
  node_type: memory
  type: project
---

# 🛑🛑★★★★★ K1 IS THE **ANGLE-GATED ANTI-DAMPING** — AND **V113 IS ALREADY THE FIX**

2026-08-28. Every link below is measured, not inferred.

## THE CHAIN
**1. The oscillation excess is ANGLE-GATED** — matched on angle and exposure-controlled
([[accord-the-oscillation-excess-is-ANGLE-GATED]]): at |ang| < 20° V112 **is** stock (1.06–1.08×);
at 20–60° p90 **1.74×** with max **16.568** against stock's **2.111**; at 60–400° p90 **3.16×**.
Stock drove that regime **more** often (13.2 % vs 4.9 %) at higher angle and command **and stayed
calm**, so it is not exposure.

**2. `|model|` RISES 7–9× WITH ANGLE** — measured, not assumed. The cave's **`0x14A` byte4 bit 5** is
the kit's own `gp-0x6AE2` comparator rung (V106's b5, recorded pooled duty 0.2533; measured here
0.2021 / 0.1695). Its duty against |ang|, engaged:
```
   |ang|        <5      5-20    20-60   60-400     rise
   route 22   0.1184   0.2268   0.3813   0.8372    7.1x
   route 23   0.1040   0.2460   0.4883   0.9339    9.0x
```
**Monotone across all four bins on two independent routes.** [EVIDENCE]

**3. THE TERM SCALES WITH BOTH `|model|` AND K1** —
`friction = EMA(|model| · K1/1024 · sat(POL·rate·12/knee))`, and it sits **in phase with rate** (the
EMA at `0xC40D0` = 408 adds only −1.1° at 2 Hz to −11.1° at 21 Hz). It is a friction *compensation*,
so **more of it is ANTI-DAMPING** ([[accord-knee-and-k1-decouple-lightness-from-relayness]]).

**4. K1 IS ×6 ON STOCK** — `0xC40D2` **102 → 612**, the largest single multiplication in the
29-run live V112-vs-stock diff.

⇒ **At large angle our anti-damping term is 6× stock's coefficient multiplied by a 7–9× larger
`|model|`. That is the angle gating, and it is ours.**

## ⭐⭐ V113 IS THE TARGETED FIX, AND IT IS ALREADY BUILT
```
   build    knee   K1    small-signal gain      K1 vs stock
   stock     600   102      0.0019922             1.0x
   v111      600   204      0.0039844             2.0x
   v112     1800   612      0.0039844             6.0x     <- ON THE CAR
   v113     1800   204      0.0013281             2.0x     <- THE FIX
```
**V113 vs V112 is 6 bytes in 2 runs: `0xC40D2` 612→204 plus the CRC trailer.** Nothing else moves —
same knee, same gain cell, same cave, same biquad.
⇒ **it cuts the anti-damping term to 0.333× of V112's, and because the term carries `|model|`, the
cut lands hardest exactly where `|model|` is 7–9× larger: at large steering angle.**
⊕ V113 = **V111's K1 with V112's knee**. V111 was the build the operator reported as *"oscillations
gone, ratcheting reduced"* (at the cost of rate); V112's raised knee is what restored the authority
(tracking 1.37–1.62× better). **V113 is the combination of the two things that each worked.**

## 🛑 I DEPRIORITISED V113, AND THAT WAS WRONG
It was shelved on the grounds that it had been built to be "strictly safer" than V112 against an
anti-damping risk that V112's flight appeared to refute. **The refutation was of the *magnitude* of
that risk at V112's operating point, not of the mechanism** — and the angle-gated measurement now
shows the mechanism is real and concentrated where V112 was least tested.

## ⚠ THE COST, AND WHAT WOULD FALSIFY THIS
**Less friction compensation ⇒ the wheel feels HEAVIER below ~30 °/s**, and `FUN_0003b8f6` is not
LKAS-gated so manual feel changes too. That is V113's own stated trade.
⚠ **The plant confound is still open**: large angle also means large self-aligning torque, a
genuinely different operating point. Stock staying calm there argues against a *pure* plant story but
does not exclude a plant×firmware interaction.
🛑 **Falsifier**: if V113 flies and the large-angle oscillation is unchanged, K1 is not the mechanism
and the angle gating is plant-side. That is a clean, single-variable read.

## ⭐⭐ V113 ADDRESSES **BOTH** SYMPTOMS — and it SELF-TARGETS
```
   rate        V112 (K1 612)   V113 (K1 204)   ratio    saturated?
     3.0 d/s      0.05632         0.01877      0.333
    31.8 d/s      0.59704         0.19901      0.333     <- the corner
   100.0 d/s      0.59766         0.19922      0.333     SATURATED
```
**0.333× at EVERY rate** — the linear region *and* the saturated plateau both scale with K1. So one
two-byte change cuts:
- the **ANTI-DAMPING** (the component in phase with rate) ⇒ **the 7.42 Hz peak-turn oscillation**;
- the **RELAY KICK magnitude** at saturation ⇒ **grind #1**;
while the relay **CORNER stays at 31.8 °/s**, so **V112's authority win is preserved** (the corner,
not K1, is what bought the 1.37–1.62× tracking improvement).
⭐ **And it self-targets.** The term is **linear in `|model|`**, and `|model|` rises **7–9×** from
<5° to >60° (measured), so the **absolute** cut is 7–9× larger at large angle — concentrated exactly
where the symptom lives, with least effect where the car already matches stock.

## 🛑 V113 SUPERSEDES V119 AS THE RECOMMENDED FLIGHT
| | V113 | V119 |
|---|---|---|
| payload | **2 bytes** | 8 bytes |
| dynamics levers | **1** | 2 |
| mechanism | **evidence-backed end to end** | knee on a validated prediction; biquad weak (P = 0.722) |
| symptoms addressed | **both** | grind #1 (knee) + a weak oscillation candidate |
⇒ **fly V113.** V119 remains built and valid, but its biquad arm rests on a comparison that is not
statistically separable, and its knee arm targets grind #1 only.
⚠ V113 carries **no state-4 probe**; that diagnostic can wait, since `0x454FE` is now a lower
priority than a mechanism with a closed chain.

## 🛑 THE OBVIOUS ALTERNATIVE — "make it FREQUENCY-SELECTIVE" — TESTED AND **REJECTED**
K1 cuts the term at *all* frequencies, so it trades the oscillation against steering feel. The
tempting fix is the friction **EMA pole `0xC40D0` = 408**: its DC gain is 1 for any α, so lowering α
should keep the low-frequency term (feel) while attenuating 7.42 Hz (oscillation). **It does — and it
pays for it in INERTIA:**
```
   alpha | anti-damping vs V112 | INERTIA vs V112 | DC feel kept
    408  |        1.000         |      1.00x      |   1.0000
    100  |        0.843         |      5.12x      |   0.9995
     56  |        0.608         |      6.84x      |   0.9984
     28  |        0.273         |      6.21x      |   0.9936
     14  |        0.087         |      3.86x      |   0.9749
```
Lag rotates the term off the rate axis: the damping component falls as `cos φ` but the **quadrature
(inertia) component rises as `sin φ`**. Every useful setting multiplies apparent inertia **5–7×**.
🛑 **That is precisely what [[feedback-do-not-buy-ratchet-with-mass-and-friction]] forbids**, and it
is the same failure mode as V111's α2 change, which the operator felt as lost rate and acceleration.
⊕ `0xC40D0` is separately flagged in V113's own header as **"the only cell in this lane that adds
PHASE — MUST NOT MOVE."**
⇒ **REJECTED.** **V113's K1 cut is strictly cleaner: 0.333× anti-damping at EVERY frequency, with NO
added inertia and NO added phase.** Recorded so the frequency-selective idea is not re-proposed.
