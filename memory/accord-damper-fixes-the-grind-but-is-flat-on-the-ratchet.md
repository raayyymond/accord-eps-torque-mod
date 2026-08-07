---
name: accord-damper-fixes-the-grind-but-is-flat-on-the-ratchet
description: Four-build dose-response on the damper cells (V72/V73 k=0, V74 k=0.5799, V75 k=1.5798). 18-22 Hz slope -0.599 [-0.856, -0.348] EXCLUDES zero; 6-9 Hz -0.089 [-0.350, +0.163] INCLUDES zero. k needed to fix the ratchet is 4.2-13.5 against a 1.5798 that hard-faulted ⇒ the damper alone cannot eliminate the micro-ratchet.
metadata:
  type: reference
---

# ★★★★ THE DAMPER FIXES THE GRIND AND IS **FLAT** ON THE RATCHET

> 🛑🛑 **THE GRIND HALF OF THIS TITLE IS RETRACTED, 2026-08-07 — read
> [[accord-grind1-is-inert-to-the-damper-dose]] first.** With V80's `k` = 4.16 added and all four builds
> re-scored on **one** instrument against a **split-half null of ≈ [0.63, 1.60]**, every grind-#1 point
> lies inside its own noise floor across `k` = 0.58 → 4.16. **The −0.599 [−0.856, −0.348] slope below
> does not survive**, and neither does "V75 vs V74 = 0.349 speed-matched" as a *dose* statement.
> ✅ **The RATCHET half stands** — and V80 shows the ratchet *does* respond once `k` reaches ~4.16
> (0.418 [0.33, 0.61]), which **confirms** the "`k` = 4.2–13.5 needed" arithmetic below rather than
> contradicting it. ✅ The V75-vs-V74 band DECOUPLING and the V75r 48% correction also stand.

Four builds differing **only** in the damper cells — **V72 k = 0, V73 k = 0, V74 k = 0.5799,
V75 k = 1.5798** — episode-bootstrapped ([[feedback-episodes-not-windows-and-the-noise-floor]]).

## The dose-response, `d ln(y) / dk`

| band | slope | in dB per unit k | verdict |
|---|---|---|---|
| **18–22 Hz (grind #1)** | **−0.599 [−0.856, −0.348]** | **−5.20 dB** | 🛑 **CI EXCLUDES ZERO** |
| **6–9 Hz (micro-ratchet)** | **−0.089 [−0.350, +0.163]** | — | **CI INCLUDES ZERO — FLAT** |

## V75 vs V74 on the grind
- speed-matched **0.349 [0.192, 0.784]**
- speed × rate-matched **0.378 [0.201, 0.806]**
- **limit-cycle duty 0.034 — the LOWEST of 13 builds**, ratio **0.067 [0.000, 0.283]**

Negative controls flat: 24–28 Hz **1.071**, 40–49 Hz **0.830**, 1–4 Hz **0.640**. This is a band-specific
effect, not a level shift. Consistent with [[accord-grind1-is-a-limit-cycle]] — successful builds stop
the cycle **starting**, they do not shrink it.

## The micro-ratchet
**Five of six statistics point down; NONE clears its own null.** Absolute 6–9 Hz envelope
V73 **210.1** → V74 **209.4** → V75 **205.0** — a 2.4 % move across a 1.58-unit dose.

🛑 **The `k` required to fix the ratchet is 4.2 – 13.5**, against the **1.5798 that hard-faulted**
([[accord-v75-fault-pinned-to-the-frame]]). ⇒ **the damper alone CANNOT eliminate the micro-ratchet; it
needs a different lever.** Do not propose a bigger damper dose for the ratchet — the arithmetic is
3–9× outside the demonstrated-fault boundary.

## ★ V75 is the first build where the two bands DECOUPLED
Paired ratio `(6–9 Hz) / (18–22 Hz)`:

| build | ratio |
|---|---|
| V72 | 1.18 |
| V73 | 1.38 |
| V74 | 1.40 |
| **V75** | **2.75 [2.09, 3.72]** |

Before V75 the two symptoms moved together on every lever; this is the first separation, and it is what
makes [[accord-two-ratchets-micro-is-the-779hz-line]]'s two-symptom split actionable.

## ⚠ V75's dose increase is NOT established on-car at EPISODE level
Engaged-creep bit7 duty ratio **1.347, CI [0.052, 1.833]** against a split-half null of **[0.676,
1.413]** — it does not clear. The pooled **"67.44 % → 82.85 %"** is a **window** statistic and must not
be quoted as an episode-level result.

## ⚠ CORRECTION carried here: the "V75r keeps ~99 % of V75's grind benefit" claim is WRONG
At the measured in-burst rate (**99 counts**) the re-cut delivers **66 counts vs V75's 137 = 48 %**, and
this dose-response predicts it gives back **1.63× [1.33, 2.01]** of what V75 bought — landing **inside**
the perceptual bracket. Wherever that "~99 %" appears, it is **48 %**.

Related: [[accord-v74-flew-damper-is-in-force]] · [[accord-v74-flight-underpowered-both-symptoms-active]] ·
[[reference-accord-two-dead-zones-speed-and-rate]] · [[accord-factorc-dip-is-ours-and-factore-x0-is-not-a-noop]] ·
[[reference-accord-78hz-mode-characterisation]]
