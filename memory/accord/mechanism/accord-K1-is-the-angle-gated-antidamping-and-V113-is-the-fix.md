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

## 🛑🛑 DOSE CORRECTION — **V113's K1 = 204 IS LIGHTER-COMPENSATED THAN STOCK. V120 SUPERSEDES IT.**
I wrote above that *"V113 = V111's K1 with V112's knee — the combination of the two things that each
worked."* **That framing is wrong.** Because V112 raised the knee ×3 *and* K1 ×3, **V111 and V112
deliver the SAME low-rate friction compensation** — that was the gain-hold, by design. So there is
only ONE number for "what he is used to", and V113 is a third of it:
```
   build      knee    K1    comp @ 3 deg/s    vs V112
   stock       600   102       0.02816         0.500     <- HONDA'S OWN LEVEL
   V111        600   204       0.05632         1.000
   V112       1800   612       0.05632         1.000     <- ON THE CAR
   V120       1800   306       0.02816         0.500     <- == STOCK
   V113       1800   204       0.01877         0.333     <- BELOW STOCK
```
🛑 **V113 puts the low-rate compensation BELOW Honda's own**, so the wheel would feel heavier than
**stock** at low rate. That was never intended and was not computed when V113 was built.

### ⭐ V120 = V112 + K1 612 → 306 — the dose is CHOSEN, not guessed
```
builder  analysis-2020accord/builds/v108_plus/build_v120_tva.py   40/40   BASE = V112
image    a588f936e4cdfe58ece41ff4943bff532444daabc4b99a53f00c1d718950a1bb
.rwd     9d6469277a6bba995cd9d2137332d791460cc2c15f845fe00c228f13c80a67e1
0xC40D2  612 -> 306.  2 payload bytes.  knee 1800, alpha2 14, cave, biquad ALL HELD.
```
- **low-rate feel = EXACTLY stock's** (0.02816 at 3 °/s, asserted in the builder);
- **anti-damping cut to 0.500× at EVERY frequency**, no added inertia, no added phase;
- **relay corner stays at 31.8 °/s** ⇒ V112's authority win (tracking 1.37–1.62×) is kept;
- **self-targeting**: the term is linear in `|model|`, which rises 7–9× with angle.
⇒ **V120 is the recommended flight. V113 remains valid but is a heavier-than-stock variant** — keep
it as the second step if V120's cut proves insufficient.

## 🛑🛑 **THE K1 MECHANISM IS REFUTED.** V120/V113 ARE NOT MECHANISM-BACKED.
2026-08-28, tested on data already in hand. **V111 (knee 600, K1 204) and V112 (knee 1800, K1 612)
have the SAME small-signal gain**, so their friction term is identical at low rate and V112's is
**1.9× at 20 °/s and 3.0× above 31.8 °/s.** If that term drives the anti-damping, **V112 must be
2–3× WORSE than V111 at large angle.** It is not:
```
   |ang|     n111  n112   p90 ratio (V112/V111)   95% CI        verdict
    0-  5     488   424        1.27x            [1.05, 1.49]   excludes 2x
    5- 20      82   167        0.90x            [0.73, 1.22]   excludes 2x
   20- 60      25    48        0.75x            [0.48, 1.64]   excludes 2x -- V112 is BETTER
   60-400      38    19        1.53x            [0.96, 4.15]   underpowered
```
🛑 **Three of four bands EXCLUDE the predicted 2–3×, and at 20–60° — where the prediction is
strongest — V112 is BETTER.** ⊕ And at **0–5°, where the term is IDENTICAL by construction, V112 is
1.27× worse [1.05, 1.49]** — a real difference **the friction term cannot explain at all.**
⇒ **the friction term is NOT what makes the oscillation angle-gated.**

### WHAT THIS DOES AND DOES NOT KILL
**STILL SOLID:**
- the excess **is** angle-gated against **stock**, exposure-controlled and with the confound inverted
  ([[accord-the-oscillation-excess-is-ANGLE-GATED]]);
- **`|model|` rises 7–9× with angle** (measured on the cave's b5 rung, monotone, two routes);
- K1 **is** ×6 on stock, and the term **is** in phase with rate.
**REFUTED:** the causal link from that term to the angle-gated oscillation.

### ⇒ STATUS OF V120 AND V113
Both remain **valid builds** — they move the friction compensation toward Honda's level, V120 landing
exactly on it — but **they are NOT mechanism-backed fixes for the oscillation.** Anything above
claiming V113/V120 is "the targeted fix" or "evidence-backed end to end" is **withdrawn**.
🛑 **Do not present V120 as a fix.** It is a principled dose (stock-equivalent feel, half the
anti-damping, no added inertia or phase) whose effect on the symptom is **unknown**.
⚠ A residue worth keeping: the 0–5° result says **something other than the friction term differs
between V111 and V112** and shows up even where their friction is identical. The only other
differences are the knee's effect on relay *character* at low rate and route-to-route variation.
**Open.**

## 🛑🛑 SECOND-ORDER CORRECTION — **THE REFUTATION ABOVE IS ITSELF WITHDRAWN**
The section immediately above refuted the K1 mechanism on a V111-vs-V112 contrast. **That contrast
cannot support any conclusion.** `r22` and `r23` are **both V112** — identical firmware, different
drives — and they differ by:
```
   |ang|     SAME-FIRMWARE r23/r22    95% CI          cross-build V112/V111
    0-  5           1.07x           [0.81, 1.25]            1.27x
    5- 20           0.77x           [0.55, 0.97]            0.90x
   20- 60           2.74x           [0.79, 8.87]            0.75x
```
🛑 **At 20–60° the same firmware varies 2.74× between drives**, so a predicted 2–3× effect is
**below the noise floor** and the cross-build ratio sits inside the same-firmware spread. My CIs were
bootstrapped over **windows**, which ignores route-level variance and badly understated the
uncertainty.
⇒ **THE K1 MECHANISM IS UNTESTED, NOT REFUTED.** And the "0–5° residue" is **also withdrawn** —
same-firmware gives 1.07× [0.81, 1.25], so 1.27× needs no new mechanism.
✅ Rule recorded as [[feedback-one-route-per-build-cannot-resolve-band-ratios]].

### ⇒ THE HONEST STATUS OF V120 AND V113
Both are **valid, well-reasoned builds** — V120 lands low-rate feel exactly on stock's while cutting
the anti-damping term 0.500× at every frequency with no added inertia and no added phase.
**Their effect on the symptom is UNKNOWN** — neither confirmed nor refuted. **V120 is the recommended
flight on reasoning, not on demonstrated mechanism**, and it should be presented that way.
