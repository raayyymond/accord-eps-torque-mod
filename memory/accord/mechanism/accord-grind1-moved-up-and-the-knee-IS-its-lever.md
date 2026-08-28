---
name: accord-grind1-moved-up-and-the-knee-IS-its-lever
description: "The operator reported that grind #1 moved to a higher frequency a few firmware versions ago. He is right, and it invalidated every grind-#1 measurement in this session, all of which used 18-22 Hz. The engaged-minus-manual spectral excess peaks at 15.0 Hz on stock and at 20.3-32.8 Hz on every mod, median about 23 Hz on recent builds - so the kit's two bands, 18-22 and 26-31, STRADDLE the real peak and both miss it. Re-run on 21-26 Hz the knee shows a monotone dose-response: knee 300 gives 0.631, 600 gives 0.246, 1800 gives 0.213, ratio 300/1800 = 2.956 with CI [1.164, 4.079] excluding 1.0. This OVERTURNS commit c91a1ba5 and gives V121 a measured grind-#1 rationale."
metadata:
  node_type: memory
  type: reference
---

# 🛑🛑 GRIND #1 **MOVED UP**, THE KIT'S BANDS MISS IT, AND THE KNEE **IS** ITS LEVER

## THE OPERATOR'S CORRECTION, AND WHY IT MATTERED
> *"grind #1 has moved to a new, higher frequency since a few firmware versions ago."*

**Every grind-#1 measurement in this session used 18-22 Hz** — grind #1's band in the V62 era. If it
moved, all of those results were aimed at a band the symptom had left. **It moved.**

## [EVIDENCE] Where the engaged-specific excess actually is
Engaged-minus-manual median log power, **within each route** so road and exposure cancel; peak
location over 5-48 Hz:
```
   STOCK        15.0 Hz  (+4.4 dB)
   V90..V96     28.1 / 20.3 / 32.8 / 28.3 / 20.5 Hz
   V100..V107   22.9 / 22.7 / 23.4 / 24.6 / 27.0 / 21.1 Hz
   V111, V112   20.9 / 23.2 / 23.4 Hz          <- recent builds cluster 21-23.4
```
🛑 **Stock peaks at 15.0 Hz; EVERY mod peaks at 20.3-32.8 Hz.** ⇒ the mod line sits **well above
stock**, median about **23 Hz** on recent builds.
🛑🛑 **The kit's two grind bands — 18-22 and 26-31 — STRADDLE ~23 Hz and BOTH MISS THE PEAK.**

## ✅ RE-RUN ON THE CORRECTED BAND: THE KNEE IS A MEASURED GRIND-#1 LEVER
Band power as a share of each window's own 1-45 Hz power, p90, engaged:
```
   band                       knee 300   knee 600   knee 1800    ratio 300/1800   CI
   18-22 Hz  (what I used)     0.26082    0.23104    0.33799        0.772      [0.575, 1.169]
   21-26 Hz  (the real peak)   0.63080    0.24591    0.21341        2.956      [1.164, 4.079]  <== EXCLUDES 1
   26-31 Hz  (kit's other)     0.19954    0.17920    0.10255        1.946      [0.986, 7.375]
   21-26 Hz, knee 300 vs 600 (n=8 vs 7, the well-powered arm): 2.565  CI [1.010, 4.664]
```
✅ **Monotone across all three knee levels, and the CI excludes 1.0.** Raising the knee 300 → 1800
cuts the grind band about **3×**. ✅ On the old band the same data gives **0.772, pointing the WRONG
WAY and not resolved** — which is exactly what I reported.

## 🛑 WHAT THIS OVERTURNS
**Commit `c91a1ba5`, "The knee has NO measured dose-response on grind #1", is WITHDRAWN.** It was a
band error, not a null. ⊕ It also explains the operator's own dose-response report — grind #1 going
from constant to *"rare… a few moments"* exactly when the knee went 600 → 1800 — which I could not
reproduce and wrongly treated as unsupported. **His report was right and my instrument was
mis-aimed.**
⊕ It probably also explains the earlier "four predictors at p < 0.10 that contradict the operator"
result, which used the same wrong band.

## ✅ CONSEQUENCE FOR V121
V121 raises the knee **1800 → 3000**, continuing the axis that measurably cuts this band.
⇒ **V121's scoring card must be corrected: grind #1 is NO LONGER excluded as an endpoint**, and the
grind band must be **21-26 Hz**, not 18-22.
⇒ **V121 now has a MEASURED dose-response behind it on grind #1**, which is more than its
oscillation rationale ever had.
⚠ Still: `n = 2` routes at knee 1800, and knee is **perfectly confounded with K1**
([[accord-k1-and-knee-are-perfectly-confounded]]) — so *"the knee or K1 cuts grind #1"* is what is
established, not which of the two.
Tool: `rlog-tools/studies/peakturn/grind_band_location_survey.py`.
