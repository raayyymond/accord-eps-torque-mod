---
name: feedback-phase-surrogate-is-no-null-for-a-spectral-line
description: "🛑🛑★★★★★ A PHASE-SHUFFLED SURROGATE PRESERVES THE MAGNITUDE SPECTRUM EXACTLY (verified ratio 1.000000), so it is NO NULL AT ALL for 'is there a LINE at f0' — an injected 35 % modulation scored 0.11 detection. It IS the correct null for coupling/correlation and waveform-phase tests. Use control FREQUENCIES for a spectral peak. And a control-frequency null is only valid where the controls BRACKET the target — on a red spectrum it fires at 1.00 on stock."
metadata:
  node_type: memory
  type: feedback
---

# A phase-shuffled surrogate is not a null for a spectral peak

**My own error, 2026-08-22, caught only because I built the sensitivity bound this kit demands.**

## THE DEFECT, PROVEN
Phase randomisation replaces `X(f)` with `|X(f)|·e^{iφ}`. **The magnitude spectrum is preserved
exactly**, so an injected line survives into the surrogate untouched:
```
|X| at 21.7 Hz   original 924.9376   surrogate 924.9376   ratio 1.000000
max | |X|_orig - |X|_surr | over all bins:  1.45e+01   (float noise)
```
**Symptom that exposed it:** injecting a **35 % amplitude modulation** — enormous and unmistakably
audible — gave a detection rate of **0.11**. *A detector that cannot see 35 % is not a detector.*

## WHERE IT IS RIGHT AND WHERE IT IS WRONG
- ✅ **CORRECT** for coupling / correlation / cross-spectrum tests: it destroys cross-structure while
  preserving each series' own spectrum. That is exactly what such a test needs.
- ✅ **CORRECT** for waveform-shape and phase-structure questions (bispectrum, nonlinearity).
- 🛑 **WRONG — zero power** for *"is there a LINE / peak / modulation at f0"*. Use instead:
  **CONTROL FREQUENCIES inside the same episodes** — same length, same noise, same spectral slope, no
  line — thresholded at their p97.5.

## 🛑 AND THE CONTROL-FREQUENCY NULL HAS ITS OWN PRECONDITION
**It is only valid where the controls BRACKET the target.** With controls at 15.5–58.5 Hz:
- targets **21.7 / 44 / 46 Hz** → false-positive rate **0.00–0.11** ✅ valid, results trustworthy.
- target **6–12 Hz** → false-positive rate **1.00 on stock** ❌ — the envelope spectrum is **red**, so
  6–12 Hz sits higher on the slope than the controls and a background fit extrapolated down from
  16–70 Hz under-predicts it. **That re-test was WITHDRAWN as uninterpretable, neither null nor
  positive.**

## THE STANDING RULE
> **Always report the m = 0 false-positive rate and an injected-signal detection curve alongside any
> null. If the detector cannot catch a large injected effect, the null is uninterpretable.**

This is the same lesson as [[feedback-run-the-control-before-the-measurement]] (`q_of` returned 79.00
on white noise) and [[accord-v68-detector-still-zero-no-positive-control]] — a third instance of the
kit's most expensive failure mode: **a null on a detector nobody demonstrated could fire.**
⊕ Related bug caught the same session: a bootstrap dividing by `max(denominator, 1e-300)` let a
resample with an empty speed bin produce CI upper bounds of ~**1e300**. Discard draws that fail to
populate every weighted bin, and report the usable-draw count.
