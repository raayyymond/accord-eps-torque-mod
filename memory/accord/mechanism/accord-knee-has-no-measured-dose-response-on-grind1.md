---
name: accord-knee-has-no-measured-dose-response-on-grind1
description: "The operator's qualitative report - grind #1 went from constant to rare exactly when the knee went 600 to 1800 - is the kit's strongest on-car evidence for a grind #1 lever, and it does NOT reproduce quantitatively. Across 17 routes the 18-22 Hz band share rises with knee (rho +0.356) rather than falling, and 26-31 Hz is flat (rho -0.158, p 0.546). So V121's rationale rests on the harmonic result for the 7-9 Hz oscillation only; its claim on grind #1 stays as originally written, which is that it does not address it. Also records that band SHARE is normalised by broadband power and is therefore not a severity measure."
metadata:
  node_type: memory
  type: reference
---

# 🛑 THE KNEE HAS **NO MEASURED** DOSE-RESPONSE ON GRIND #1

## WHY I TESTED IT
V121 raises the knee 1800→3000. Its rationale is the **harmonic** result, which bears on the 7-9 Hz
oscillation, and I wrote that it *"does not address grind #1."* I then noticed the operator's own
dose-response — grind #1 went from a constant feature to *"rare… a few moments in each drive"*
**exactly when the knee went 600→1800** — and started to upgrade V121's claim on that basis.
**I tested it first. It does not reproduce.**

## [EVIDENCE, negative] 17 routes, band power as a SHARE of each window's own 1-40 Hz power
```
   knee   n_routes   18-22 Hz    26-31 Hz    6-9 Hz
    300       8        0.0718      0.0658     0.0427
    600       7        0.0930      0.0616     0.0659
   1800       2        0.0924      0.0532     0.0663

   Spearman(knee, share)      [prediction: NEGATIVE for the grind bands]
     18-22   rho +0.356  p 0.161    knee300/knee1800 = 0.78x  CI [0.64, 1.08]
     26-31   rho -0.158  p 0.546    knee300/knee1800 = 1.24x  CI [0.56, 2.98]
```
🛑 **18-22 Hz goes the WRONG WAY** (+0.356, i.e. more grind band at higher knee) and 26-31 Hz is
flat. Nothing supports the knee as a grind #1 lever in this corpus.
⇒ **V121's claim on grind #1 stays as originally written: it does not address it.** The upgrade is
withdrawn before it was made.

## ⚠ TWO REASONS THIS IS *NOT* A REFUTATION OF THE OPERATOR'S REPORT
1. **n = 2 routes at knee 1800.** Per [[feedback-one-route-per-build-cannot-resolve-band-ratios]] that
   cannot resolve much, and the CIs say so.
2. 🛑 **Band SHARE is not severity.** It is normalised by the window's own 1-40 Hz power, so a
   change that lowers broadband power more than it lowers the band **raises the share while the
   absolute level falls.** The 6-9 Hz reference row shows the hazard plainly: it *rises* with knee
   (rho +0.477, p 0.053) on share, which is the opposite of what the harmonic and on-road results
   say. **Share answers "what fraction of the motion is in this band", not "is the symptom worse."**
⇒ **The right statistic for severity is absolute band level with exposure controlled**, and with 2
routes at knee 1800 the corpus cannot deliver it. **OPEN.**

## ⇒ WHAT STANDS
✅ V121 is justified by the **harmonic** result on the 7-9 Hz oscillation — itself **BELIEF**
([[accord-knee-is-the-relay-shape-variable-k1-is-only-gain]]).
🛑 The operator's grind-#1 dose-response is **confounded** in any case: V112 moved `knee` **and**
`K1` together, on top of every other difference from V111. It remains a real observation and the
best on-car signal the kit has for grind #1 — **but it is not a measured dose-response, and this
corpus does not reproduce one.**
Tool: `rlog-tools/studies/peakturn/grind_band_dose_vs_knee.py`.
