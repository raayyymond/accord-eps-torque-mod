---
name: accord-the-oscillation-excess-is-ANGLE-GATED
description: "Matched on steering angle and exposure-controlled: at |ang| 0-20 deg V112's 6-9 Hz oscillation equals stock (1.06-1.08x), but at 20-60 deg it is 1.74x at p90 with a max of 16.568 against stock's 2.111, and at 60-400 deg it is 3.16x with max 10.244 against stock's 1.909. Stock had MORE large-angle engaged exposure than V112 (13.2 percent of windows vs 4.9), so this is not an exposure artifact. The trigger for the peak-turn oscillation is LARGE STEERING ANGLE."
metadata:
  node_type: memory
  type: reference
---

# 🛑🛑★★★★★ THE OSCILLATION EXCESS IS **ANGLE-GATED** — and the exposure control INVERTS the confound

2026-08-28. 2.56 s windows, engaged & moving, 6–9 Hz rate rms.
**STOCK = route 97 (509 windows) · V112 = routes 22+23 (658 windows).**

## THE MATCHED COMPARISON
```
   |ang|      STOCK n   p90     max   |   V112 n   p90     max   |  p90 ratio
    0-  5       334    0.897   2.896  |    424    0.967   3.247  |    1.08x
    5- 20       102    1.394   3.748  |    167    1.480   4.402  |    1.06x
   20- 60        19    1.695   2.111  |     48    2.946  16.568  |    1.74x
   60-400        54    1.226   1.909  |     19    3.878  10.244  |    3.16x
```
🛑 **At |ang| < 20° we ARE stock (1.06–1.08×). At |ang| ≥ 20° we are 1.7–3.2× worse at p90 and
5–8× worse at the maximum.** ⊕ **Stock is CALMER at large angle** (max 2.111 at 20–60°, against its
own overall max of 3.748) — the blow-up is entirely ours.

## ✅ THE EXPOSURE CONTROL — it INVERTS the confound rather than merely passing it
The obvious objection is that route 97 is highway-weighted (p50 72 km/h) and never drove the regime.
**The opposite is true:**
```
   extreme regime (|ang| >= 20 AND |cmd| >= 1500, engaged)
     STOCK   67 of 509 windows (13.16 %)   |ang| p50 65.6   |cmd| p50 3631
     V112    32 of 658 windows ( 4.86 %)   |ang| p50 61.8   |cmd| p50 3266
```
**Stock drove the extreme regime MORE OFTEN, at HIGHER angle and HIGHER command — and stayed calm.**
⇒ the difference cannot be exposure. **[EVIDENCE]**

## ⭐ IT IS A TAIL PHENOMENON, NOT A SHIFTED MEAN
Pooled 6–9 Hz band power is **STOCK 0.742 vs V112 0.823 — only 1.11×.** The distributions:
```
   arm      n     p50     p90     p99   p99.9     max
   STOCK  509   0.319   1.140   2.050   3.315   3.748
   V112   658   0.477   1.364   3.730  12.413  16.568
   ratio        1.50x   1.20x   1.82x   3.74x   4.42x     (p99 CI [1.34, 2.95])
```
🛑 **Stock's ENTIRE distribution tops out at 3.748; V112 reaches 16.568**, and V112 exceeds stock's
own p99 **3.9× more often**. ⇒ the symptom is **rare extreme events** — exactly the operator's
*"it still has its few moments"*. 🛑 **The kit's "the line is 16–30× stock's" is NOT reproduced
pooled and must be quoted as a TAIL statistic, never as a mean.**

## ⊕ AND THE Q COMPARISON IS NOW EVIDENCE, NOT BELIEF
A spectral Q estimate (Welch 4096, 573 s / 809 s) independently reproduces the kit's **n = 1**
ring-down: **STOCK Q 19.65, ζ 0.0254** (ring-down 15.6–18.2 / 0.0275–0.0321) · **V112 Q 9.27,
ζ 0.0539** (ring-down 7.0–8.5 / 0.059–0.072). **Two unrelated methods, same answer** ⇒ upgrade the
ζ claim in [[accord-the-742hz-mode-is-stocks-and-our-q-is-lower]] from BELIEF to EVIDENCE.

## ⭐⭐ WHAT IS ANGLE-GATED AND OURS — the candidate this points at
**`0xC40D2` K1 = 102 → 612, ×6 ON STOCK** — the largest single multiplication in the live diff.
The friction relay is `friction = EMA(|model| · K1/1024 · sat(rate·12/knee))`, and **`|model|` grows
with steering angle** (self-aligning torque), so **K1 is angle-gated by construction**. The term sits
in phase with rate and is a *compensation*, hence **anti-damping**
([[accord-knee-and-k1-decouple-lightness-from-relayness]]).
⇒ **lowering K1 lowers the saturated magnitude without moving the relay corner** — less anti-damping,
same relay character. ⊕ **That is exactly what V113 does** (K1 held at 204 while the knee is raised),
which **rehabilitates V113's direction** after it was deprioritised on the grounds that V112 flew well.
⚠ **NOT demonstrated.** No measurement links K1 specifically to the angle gating; `|model|`'s angle
dependence is **inferred, not measured**. Do not present it as the cause.
⚠ **The plant confound is real**: large angle means large self-aligning torque and a genuinely
different operating point. Stock staying calm there argues against a *pure* plant explanation but
does not exclude a plant×firmware interaction.

## ✅ WHAT WOULD CLOSE IT
Measure `|model|` (or its proxy `gp-0x6ae2`) against steering angle on an existing route — the cave
already telemeters `gp-0x6ae2`. If `|model|` rises steeply with |ang|, the K1 link is established
without a new drive.

## ✅ CONFOUND REMOVED — matched on the denominator, it is **9 of 9**. And **ONE stock route caps p at 0.100.**
2026-08-28. Re-tested with a **within-drive** design (each route its own control, immune to the
route-offset problem in [[feedback-one-route-per-build-cannot-resolve-band-ratios]]).

**First pass, raw ratio** p90(6-9 Hz | ang>=20) / p90(| ang<20): STOCK **1.46x**, 16 mod routes median
**2.99x**, 13/16 above stock — but three mod routes fell *below* stock and stock ranked only 4th of 17
(rank p ≈ 0.24). 🛑 **That test was confounded.** The ratio's **denominator varies 10x across builds**
(1.007 → 9.388); a build already oscillating at small angle has no headroom, which compresses its
ratio. **All three mod routes below stock had small-angle p90 > 6.**

**Matched pass** — keep only mod routes whose **small-angle p90 brackets stock's** (window [0.63, 1.81]):
```
   route build   small-ang p90   LARGE-ang p90   ratio
   r97   STOCK       1.064          1.551       1.46x   <-- STOCK
   r22   V112        1.240          2.909       2.35x
   r21   V111        1.007          3.137       3.12x
   r78   V91         1.067          3.719       3.49x
   r79   V92         1.116          4.044       3.62x
   r7f   V96         1.163          4.527       3.89x
   r7e   V96         1.383          4.827       3.49x
   ra6   V106        1.155          6.227       5.39x
   r77   V90         1.703          7.353       4.32x
   r23   V112        1.060          8.320       7.85x
```
Stock's small-angle p90 ranks **3rd of 10** — exposure at small angle is **matched**, so only the
large-angle response differs. ✅ **Stock's large-angle p90 (1.551) is BELOW ALL NINE** (2.909-8.320).
⊕ The **same-firmware** V112 pair spans 2.909-8.320 and **both sit above stock by ≥ 1.88x**, so
drive-to-drive spread does not explain stock's position.

### 🛑 THE BINDING CONSTRAINT IS THE STOCK ARM, AND IT IS ARITHMETIC
Exact one-sided permutation p (stock the minimum of 10) = **1/10 = 0.100**.
🛑 **With ONE stock route the p-value FLOOR is 1/(n_mod+1) = 0.100 — no amount of analysis can
reach 0.05.** The limit is the design, not the statistics.
✅ **With TWO stock routes below all nine mods: p = 2!·9!/11! = 0.0182 — clears 0.05.**

⇒ **Status: [EVIDENCE for the direction and size, 9/9 with exposure matched; NOT significant at 0.05,
and cannot be, on n=1 stock drive].**
✅ **`docs/scoring/DRIVE-CARD-manual-at-speed.md` is the GATING ITEM for the programme** — and the ask
is now exact: **ONE more stock-configuration drive** converts the strongest surviving finding from
p=0.100 to p=0.018. **No firmware change, no flash, no build required.**
