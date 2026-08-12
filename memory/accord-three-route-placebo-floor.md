---
name: accord-three-route-placebo-floor
description: "Routes 77/78/79 are three drives on the SAME functional car (the V91/V92 cal edit was measured inert) — the kit's largest same-firmware placebo set. Column-torque band spread 1.09x-1.99x is the floor any future band claim must beat."
metadata:
  type: reference
---

# ★★★★ THE THREE-ROUTE PLACEBO FLOOR — what any future band claim has to beat

Because the V91/V92 ×1.5 edit was **measured inert** at its own single output
(`[[accord-cbe74-dose-measured-inert-wrong-mode-record]]`), routes **77 (V90), 78 (V91) and 79
(V92)** are **three independent drives of the same functional car**. That accident produces the
kit's **largest same-firmware placebo set**. Tool: `rlog-tools/v92_symptom_bands.py`.

Method: window on the physical mask (engaged, hands-off, moving), classify each window by its **own
median |wheel rate|**, then take column-torque (`tq`, `0x18F`) band **density normalised within each
window** by that window's own 1–38 Hz total — so a window that merely saw more road cannot inflate a
band.

## MICRO regime (1–13 °/s) — median band density [95 % CI]

| band | r77 (V90) | r78 (V91) | r79 (V92) | **spread** |
|---|---|---|---|---|
| 6–9 (micro-ratchet) | 0.0838 [.0650,.0962] | 0.0696 [.0515,.0949] | 0.0954 [.0572,.1272] | **1.37×** |
| 9–12 | 0.0842 | 0.0702 | 0.0771 | 1.20× |
| 18–22 (grind #1) | 0.0090 | 0.0069 | 0.0090 | **1.31×** |
| 26–31 (grind #2) | 0.0028 | 0.0034 | 0.0017 | **1.99×** |
| 32–38 (control) | 0.0009 | 0.0006 | 0.0006 | 1.54× |
| windows | 95 | 36 | 36 | |

## static regime (<1 °/s) — tighter, because there are far more windows

| band | r77 | r78 | r79 | spread |
|---|---|---|---|---|
| 6–9 | 0.0464 | 0.0301 | 0.0429 | 1.54× |
| 18–22 | 0.0064 | 0.0059 | 0.0064 | **1.09×** |
| 26–31 | 0.0035 | 0.0034 | 0.0027 | 1.30× |
| 32–38 (control) | 0.0014 | 0.0014 | 0.0013 | 1.13× |
| windows | 122 | 152 | 183 | |

## 🛑 HOW TO USE IT

- **A build that moves a band by less than its own row here has not been shown to do anything.**
  Grind #2 (26–31 Hz) in the micro regime carries a **1.99× same-firmware spread** — nearly a factor
  of two of pure drive variation. **No grind-#2 claim below 2× is supportable.**
- **The 32–38 Hz control band moves too** (1.13×–1.54×), which is the point: it has no hypothesis
  attached, so its spread *is* the noise.
- This supersedes the older single-pair placebo estimates (`e_18-22` r77÷r75 = 1.504) with a
  three-route version on a matched, regime-classified estimator.
- ⚠ The MICRO rows rest on **36 windows** for r78/r79 against 95 for r77. Treat the micro spread as
  an **upper bound on precision**, not a settled floor.

Related: `[[feedback-episodes-not-windows]]`, `[[accord-averaged-spectrum-needs-matched-speed-distributions]]`,
`[[feedback-run-the-control-before-the-measurement]]`.
