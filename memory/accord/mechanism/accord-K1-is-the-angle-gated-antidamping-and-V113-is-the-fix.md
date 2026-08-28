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
