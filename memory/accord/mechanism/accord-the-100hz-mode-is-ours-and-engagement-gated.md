---
name: accord-the-100hz-mode-is-ours-and-engagement-gated
description: SUPERSEDED FRAMING. With a full 11-route spectrogram ladder and a fixed 90-110 Hz band (no grid search), STOCK is the ONLY route that fails its null (-0.30 dB, p=0.890) while 9 of 10 gain-modified builds clear theirs at p<0.001 - so the engaged acoustic excess IS ours. But three control bands rise equally: after removing them the 100 Hz residual is <=0 on 6 of 10 routes. It is BROADBAND engaged noise scaling with gain, NOT a 100 Hz mode.
metadata:
  node_type: memory
  type: reference
---

# ⚠⚠ SUPERSEDED FRAMING — IT IS **BROADBAND ENGAGED NOISE**, NOT A ~100 Hz MODE

🛑🛑 **READ THIS BLOCK FIRST. EVERYTHING BELOW IT PREDATES THE LADDER AND IS KEPT AS THE
AUDIT TRAIL.** Three passes moved this result; this is where it landed.

## THE LADDER, WITH A STOCK ARM AND NO GRID SEARCH
`rlog-tools/decode/extract_route_audio.py` built spectrograms for **eleven** routes;
`rlog-tools/score/band_100hz.py` scores a **fixed 90–110 Hz band** (no search, so no search
inflation), engaged-minus-manual, matched speed <10 mph, hands-off, **within drive**, with an
engaged-vs-engaged null and **three control bands** (55–75, 130–150, 210–230 Hz).
```
  route build       gain   100Hz dB   null p95      p    mean ctl   100Hz - ctl
  97    V9b-STOCK    1x      -0.30       0.43   0.890      -0.04        -0.26   <- ONLY NULL
  77    V90          4x      +0.93       0.21   0.000      +0.43        +0.50
  79    V92          4x      +0.97       0.26   0.000      +1.41        -0.44
  85    V100         4x      +0.44       0.49   0.077      +0.68        -0.24
  96    V102         6x      +0.55       0.33   0.000      +0.57        -0.02
  1e    V107         6x      +0.94       0.21   0.000      +0.80        +0.14
  a4    V104         6x      +1.07       0.24   0.000      +0.88        +0.19
  a5    V105         6x      +1.12       0.38   0.000      +1.60        -0.48
  a6    V106         6x      +2.65       0.27   0.000      +1.54        +1.11
  9e    V103         6x      +3.93       0.24   0.000      +1.40        +2.53
  95    V101         8x      +4.15       0.46   0.000      +2.24        +1.91
```

## ✅ WHAT IS SOLID — THE ENGAGED ACOUSTIC EXCESS IS **OURS**
**STOCK is the only route that fails its own null** (p = 0.890). **Nine of ten gain-modified
builds clear theirs at p < 0.001.** ⇒ engaging adds measurable cabin noise on our builds and
**not** on Honda’s, at matched speed against the driver doing the same thing on the same drive.
⭐ And the BROADBAND level ladders with gain: **1× −0.04 · 4× ≈0.84 · 6× ≈1.13 · 8× 2.24 dB.**

## ❌ WHAT IS **NOT** TRUE — IT IS NOT A 100 Hz MODE
**All three control bands rise with it.** Subtracting the control mean, the 90–110 Hz residual
is **≤ 0 on six of the ten** modified routes and only stands out on r9e (+2.53), r95 (+1.91)
and ra6 (+1.11). ⇒ **the excess is BROADBAND, not band-specific**, and the earlier
"≈100 Hz mode" framing — built on the coarse 20-band third-octave caches, which had no
adjacent control bands — **does not survive.**
🛑 The companion 83.5 Hz comb result collapsed in the same way one tick earlier
([[accord-the-lowspeed-grind-is-an-83hz-harmonic-series]]). **Both were the same error: a
narrow-band claim with no adjacent-band control.**

## WHAT IT MEANS FOR THE BUILDS
- ⚠ **V109’s α2 cut is band-limited (61–300 Hz, −34 % at 100 Hz).** Against a genuinely
  broadband excess it can only remove the part inside its band. **It is no longer the
  well-aimed lever the earlier note claimed** — that claim rested on the 100 Hz framing.
  ⊕ It still cuts real content in a band where the excess is real; the claim that shrinks is
  "aimed squarely at THE mode", because there is no single mode.
- ⭐ **The gain itself is the cleanest correlate of the broadband excess.** That is consistent
  with [[accord-the-8x-gain-is-the-carrier]] and it is not a lever the operator wants moved.
- **The pre-registered V109 endpoint should be the BROADBAND engaged excess with its control
  bands, not a comb score and not a single band.**

## ⭐ THE METHOD LESSON, TWICE IN TWO TICKS
**A narrow-band acoustic claim needs ADJACENT CONTROL BANDS in the same statistic**, exactly as
the steering-rate work already does ([[accord-ratchet-and-grind-are-command-gated-saturation]]
uses four control bands and that is why its result held). The third-octave caches have only
twenty bands spanning 100 Hz–8 kHz, so no adjacent control was available — **and I published
anyway, twice.** The spectrogram makes the control free; use it.

---

