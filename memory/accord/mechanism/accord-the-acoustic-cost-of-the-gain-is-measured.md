---
name: accord-the-acoustic-cost-of-the-gain-is-measured
description: The acoustic cost of the LKAS gain is measured for the first time - 6x adds +1.158 dB [+0.475, +1.817] of steering-band cabin noise over 4x relative to a far-field control band, P(>0)=1.000, across 9 routes with 8 of 9 outside their own null. Ordering is stock ~= 4x < 6x < 8x. Supersedes three narrow-band framings that all died to adjacent-band controls.
metadata:
  node_type: memory
  type: reference
---

# THE ACOUSTIC COST OF THE GAIN IS **MEASURED** — +1.16 dB from 4× to 6×

★★★★★ **EVIDENCE**, 2026-08-27. Eleven-route audio spectrogram ladder with a **STOCK arm**, built
this session (`rlog-tools/decode/extract_route_audio.py`). This note is the **surviving** result of
the acoustic thread; three narrower framings preceded it and all three died to controls (below).

## THE STATISTIC — and why it needs two bands, not one
```
  MECH  =  engaged-minus-manual median dB over  60- 400 Hz   (where steering-mechanism noise lives)
  FAR   =  engaged-minus-manual median dB over 1200-2000 Hz  (far from any steering mechanism)
  score =  MECH - FAR
```
All within one drive, **matched speed below 10 mph, hands-off (D3)**. Absolute cabin level differs
3–12× between drives, so a raw dB never travels; an engaged-minus-manual difference does.
🛑 **FAR IS NOT OPTIONAL.** It rises too — **+0.74 dB on STOCK, +1.16 dB mean at 4×** — which proves
the engaged and manual segments differ in ways that lift the WHOLE spectrum (road, exact speed inside
the bin, HVAC). **Any single-band engaged-minus-manual claim on this corpus is confounded by that**,
which is exactly how the two earlier framings died.

## THE RESULT
```
  gain   n     MECH     FAR   MECH-FAR
   1x    1    +0.01   +0.74     -0.73
   4x    3    +0.36   +1.16     -0.80
   6x    6    +0.95   +0.58     +0.36
   8x    1    +2.01   +0.39     +1.62

  per route:  4x  V90 -0.32 · V92 -0.96 · V100 -1.11
              6x  V102 +0.24 · V103 +1.43 · V104 -0.67 · V105 +0.53 · V106 -0.22 · V107 +0.86

  6x - 4x  =  +1.158 dB   [+0.475, +1.817]   P(>0) = 1.000   (route bootstrap, both arms)
```
⭐ **The 4×→6× step is the well-powered contrast (3 vs 6 routes) and its CI excludes zero.**
⊕ **8 of 9 routes lie OUTSIDE their own engaged-vs-engaged null**, so the per-route values are real
rather than noise. (V102 is the one inside.)
⚠ **n = 1 for stock and n = 1 for 8×** — those are single points and must not be quoted as tested
levels. What is tested is 4× vs 6×.
⚠ The **absolute sign is not the finding** — 4×'s negative values mean the far field rose more than
the mechanism band on those drives, which is a property of the confound, not of the steering. **Only
the CONTRAST is interpretable.**

## \U0001f6d1 WHAT THIS MEANS FOR THE OPERATOR'S GOALS
**The 6× he asked for costs ~1.2 dB of steering-band cabin noise over 4×, measured.** That is the
first time the acoustic price of the gain has been quantified rather than asserted, and it is a
**direct trade against goal #1 (eliminate audible grinding)**:
> **goals #1 and #4 are in tension through the gain itself**, and the tension is now numeric.
⊕ Consistent with [[accord-the-8x-gain-is-the-carrier]], reached independently from the 20–26 Hz
steering-rate band. **Two unrelated instruments, same conclusion: the gain carries the noise.**
🛑 It does **not** follow that lowering the gain is the answer — the operator wants 6×, and
[[accord-4x-lkas-gain-is-the-frozen-variable]] warns against recommending a gain cut. **The finding
is a PRICE, not a prescription.**

## ✅ AND IT IS **NOT COMMAND-MODULATED** — which closes a whole search direction
The obvious follow-up: if the excess were switched on by command magnitude, the relay/knee story
would reach it and V111 would measure the acoustic symptom too. **Tested. It does not.**
**WITHIN-ENGAGED** contrast — high command (`|e4tq| >= 2048`) vs low command (`< 512`), **both arms
engaged**, hands-off, <10 mph. ⭐ **This design has no engaged-vs-manual confound at all**, which is
what made the earlier passes fragile.
```
  route  build       gain   MECH-FAR   n lo  n hi   vs own null
  97     V9b-STOCK    1x       +0.81    283   189   OUTSIDE
  77     V90          4x       +0.21    802  1305   OUTSIDE
  79     V92          4x       +2.40    833   164   OUTSIDE
  85     V100         4x       -0.72    150   190   OUTSIDE
  a4     V104         6x       -0.13   1176   239   inside
  a5     V105         6x       -0.41    556   371   OUTSIDE
  a6     V106         6x       +1.31    672   336   OUTSIDE
  1e     V107         6x       -2.42   1177   175   OUTSIDE
  96 / 9e / 95        thin -- <150 high-command frames below 10 mph

  BY GAIN:   1x +0.81 (n=1)   4x +0.63 (n=3)   6x -0.41 (n=4)
```
🛑 **Signs go BOTH WAYS, stock sits in the same range as the modified builds, and the gain means
do not order.** Seven of eight routes are outside their own null, so the scatter is **real
between-drive variation, not noise** — there is simply no command effect to find.
⇒ **The acoustic excess is a LEVEL SHIFT TIED TO THE GAIN, not something command modulates.**

## ⭐⭐ THE TWO SYMPTOM FAMILIES ARE NOW CLEANLY SEPARATED
| family | instrument | command-gated? | lever |
|---|---|---|---|
| **6–9 Hz ratchet + 20–26 Hz grind** | steering RATE | **YES — 48× at matched rate**, two control bands falling ([[accord-ratchet-and-grind-are-command-gated-saturation]]) | the Coulomb relay knee; **V111 measures whether it is reachable** |
| **60–400 Hz cabin noise** | AUDIO | **NO** — scatters both ways, stock in range | **none but the gain itself** |
⇒ 🛑 **A command-domain lever cannot reach the acoustic symptom.** V111's probe is aimed at the
ratchet family and **should not be expected to inform the acoustic one.**
⇒ 🛑 **And the acoustic cost of 6× is therefore not reducible by any lever this kit has found** —
only by moving the gain, which the operator does not want and
[[accord-4x-lkas-gain-is-the-frozen-variable]] warns against recommending.

## ❌ THREE FRAMINGS THAT DIED ON THE WAY HERE — all the same error
| framing | what killed it |
|---|---|
| *"the ~100 Hz mode is ours"* (third-octave bands) | three **adjacent control bands rise equally**; residual ≤ 0 on 6 of 10 routes |
| *"an 83.5 Hz harmonic comb is the grinding"* | **STOCK fires too**, no gain ordering, and the comb estimator has a **sub-harmonic ambiguity** (`f0` also scores at `f0/2`) |
| *"PMSM 6th/12th torque ripple"* | **decisively excluded** — an electrical order moves 40× across the tested rate span; the centroid moves 1.04× |
⭐ **THE COMMON ERROR: a narrow-band acoustic claim with no adjacent-band control.** The
steering-rate work never made it — [[accord-ratchet-and-grind-are-command-gated-saturation]] carries
four control bands and that is precisely why its result held. **The spectrogram makes controls free.
Use them, and build the STOCK arm BEFORE publishing an "it is ours" claim.**

## THE V109 ENDPOINT, RESTATED
Score V109 against V108 on **MECH − FAR**, same road, same driver, matched speed, hands-off. ⚠ **Not**
a comb score, **not** a single band. ⚠ And note V109's α2 cut is band-limited to 61–300 Hz while the
excess is broadband over 60–400 Hz, so it can only remove the part inside its band — **it is not
"aimed squarely" at this, and the earlier note claiming so has been corrected.**
🛑 **The V109 drive must capture audio**, or the endpoint is unmeasurable.

Related: [[accord-the-100hz-mode-is-ours-and-engagement-gated]] (superseded framing) ·
[[accord-the-lowspeed-grind-is-an-83hz-harmonic-series]] (qualified) ·
[[feedback-run-the-control-before-the-measurement]]
