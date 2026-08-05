---
name: accord-grind1-is-a-limit-cycle
description: Grind #1 is a limit cycle — duty spans 64x across builds while in-burst amplitude spans 1.24x against a 5.62x dose ladder. Successful builds stop it starting, never shrink it.
metadata:
  type: reference
---

★★★★ **Grind #1 (18–22 Hz) is a LIMIT CYCLE, not a gain problem.** [EVIDENCE, 8 routes, D1's
decomposition of each build's median into `duty x in-burst amplitude`, engaged creep, threshold fixed
across builds]

| | range across builds |
|---|---|
| **duty** | 0.015 -> 0.958 — **64x** |
| **in-burst amplitude** | 1232 -> 1533 — **1.24x** |

against a **5.62x** rate-lane dose ladder. Amplitude is tight **within** build too (CV **0.17–0.26**,
IQR/median 0.19–0.28), and `log10 e_18-22` is **two-moded on exactly the arms that carry the cycle and
one-moded on the arms that suppress it**, with the high mode at **1073–1353** on three independent arms —
the same place as the in-burst amplitude. Latch and unlatch.

> **Successful builds stop the cycle STARTING. None of them makes it smaller.**

**The ladder floors.** Priced as excess over its own in-window 24–28 Hz control (a fully eliminated mode
reads 1.00): V61 **12.42** · stock **8.77** · V72 **6.40** · V71C **4.17** · V62+V65 **2.82** ·
V67+V68 **2.21**. **Nothing reaches 1.0 on any build**; the first factor of dose bought 4x and the last
buys almost nothing.

⊕ **Corroborated from the opposite direction:** sweeping `a` (`gp-0x69a4`) from 0 to 32.0 in **both**
summed and differential models, **no value makes the cross-build ladder monotone** (best |tau| = 0.429,
optimum at a = 0). ⇒ **grind #1 is not a scalar-gain phenomenon** — it is amplitude- or shape-dependent.

★★ **The decisive on-car datum:** at ≤10 km/h **V72's delivered gain is BIT-IDENTICAL to V67/V68's** —
the same absolute 5244 / 512 at every rate index, not merely the same ratio — **and V72 scored stock's
grind** (614 [311, 1187]; dose-matched stratum: consistent with stock **P = 0.874**, excluded higher than
V67+V68 **P < 0.0001**, effort-matching runs against V72 twice).
⇒ **the creep rate-lane gain is not what separated them, and the rate lane is exhausted as a grind-#1
lever.** Ten builds of dosing it floored at ~8x for this reason.

## RELATION TO THE 7.79 Hz RATCHET — one driver, two modes
- **Shared driver [EVIDENCE]:** partial `r(6-9, 18-22 | 24-28)` = **0.460**, circular-shift null
  [-0.102, +0.023], **p = 0.0002**, build-independent (within-episode r = 0.60–0.77 on every build).
  ⚠ The **raw** correlation would have fooled us — the 24–28 Hz control band tracks nearly as hard
  (0.606 vs 0.683). The partial is the load-bearing statistic.
- **Distinct modes [EVIDENCE]:** **opposite-signed dependence on steering position.** Over 0–45 deg the
  ratchet's amplitude grows with distance from the sensed zero while grind #1's does not (window-level
  Spearman **+0.23 / +0.32** vs **+0.05 / +0.06**, two independent pipelines, n = 117 and 437; ratio of
  ratios ~**2.0–2.3** for any inner/outer split between 3 and 20 deg — a smooth gradient, no knee; robust
  to leaving out any route or any block). **Two amplitudes of one oscillation cannot do that.**

⇒ 🛑 **Anything that moves one should be expected to move the other. Score BOTH bands on every build.**
⚠ The angle-position result is **DIAGNOSTIC, not a lever**: two rounds of firmware search found no
angle-indexed structure of adequate magnitude (the best candidate `0xC6B64` moves **3.8%** over the
measured 0–45 deg range against a **3.2x** measured effect, and is indexed by tracking *error* not
absolute position), and **nothing in the corpus separates firmware from plant** — self-aligning torque,
rack friction or assist level varying with rack position fit equally well.

Links: [[accord-damper-is-mode-table-selected]] · [[accord-two-lane-rule-grind2]] ·
[[feedback-cross-pipeline-compare-shape-not-level]]
