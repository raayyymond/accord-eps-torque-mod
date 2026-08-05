# ★★★★★ THE TWO-LANE RULE — why fixing one grind always fed the other

**Measured 2026-08-05 across six builds including the two new flights (V71B = route `54`,
V71C = route `58`).** This answers the operator's central question of the session.

## The rule — [EVIDENCE for the association]
High-rate corner of both surfaces (creep, rate index 3000), gains read from the shipped images:

| build | **r24 high-rate ×** | **r26 high-rate ×** | creep grind #2, measured |
|---|---|---|---|
| stock (V58/V59/V64) · V69 · V70 | 1.000 | 1.000 | **none** |
| **V71B/`r54`** | **1.000** | **2.000** | **none** (0 bursts / 835 windows, max 61) |
| V62/V65 | **3.414** | 2.000 | **YES — worst in corpus** |
| **V71C/`r58`** | **3.414** | 1.500 | **YES — 3 creep events, max 1742** |
| **V67/V68** | **3.414** | **0.250** | **none** |

> **Creep grind #2 requires r24 high-rate ≳ 3.4× AND r26 high-rate ≳ 1.5×. Cutting EITHER kills it.**

**Six builds, no exceptions. Neither lane's multiplier predicts the outcome alone** — r26's ranges
0.25 → 2.00 across them.
⇒ **Raising r24 to fix grind #1 feeds grind #2 UNLESS r26 is also cut. Every previous attempt moved only
one lane.** V67/V68 moved both, which is why it is the only build that reached grind #1 = 109/111 with no
creep grind #2.
⚠ **[BELIEF] on the product-of-two-lanes mechanism. And V67/V68's cell is the WEAKEST evidence in the
table** — ~42 s of engaged creep, so its zero is not powered.

## The grind #1 side — [EVIDENCE, matched-exposure resampling]
Median `e_18-22`, engaged creep: V68 **70** · V65/`r3a` **94** · V67 **111** · V71C **223** · V62 **268**
· V71B **545** · V70 **729** · V69 **746** · stock pool **879** · V61 **2501**.
- **V71C excluded HIGHER than V67 at P = 0.0215** — the only functional difference is r26 (3072 vs 512)
  ⇒ **the r26 cut is load-bearing.** Cleanest single-variable result in the corpus.
- **V71B excluded higher than V62/V67/V71C, all P ≤ 1e-4** ⇒ **r26 raised ALONE does not fix grind #1.**
- **V71C better than V71B at P < 1e-4** — exactly the operator's own ranking.
⚠ Whole-axis vs plateau-only for r24 is a **3.3× point-estimate gap that does NOT clear significance**
(V71C vs V70 P = 0.35, vs V69 P = 0.15; V70's arm is 5 blocks). **Under-powered, not null.**

## ★ Grind #2 follows the GATE, not the driver's hands — [EVIDENCE]
V62/V65 (**ungated**) burst in **both** arms at equal rates — 0.0444/s engaged vs 0.0430/s manual.
V71C (**gated**) bursts **only** engaged.
⇒ caused by the rate-lane arm being **live**, not by the plant.
⚠ **This contradicts the operator's recollection that grind #2 was worse WITHOUT openpilot** — the corpus
does not carry it. Likeliest reason: on the ungated builds it was equally present hands-on with LKAS off,
which is far more salient.
⚠ **V71C's "absent on the manual arm" holds at ALL SPEEDS (p90 ratio 5.878 [3.433, 10.103], outside null)
but NOT at creep** (1.885 [0.876, 36.111], inside null; the manual zero is P(0) = 0.089, under-powered).
State it as the all-speeds contrast, where manual has no highway exposure at all.

## ★ The bursts are HIGH-RATE windows — [EVIDENCE, route 58]
Burst windows vs non-burst engaged: `|rate|` p50 **21.1 vs 2.5**, p90 **258.4 vs 21.7**, effort p50
**1689 vs 111**. ⇒ **grind #2 is a high-rate-index phenomenon**, and in the corner regime **every**
burst-producing cell in the corpus is the ≥1400 rate cell (V62/V65: 14 bursts at ≥1400 vs 1 at the knee
vs 0 at the plateau).
🛑 **Price any future lever against the RATE axis, not just the speed axis.** V71C's r24 is a *cut*
(0.93×) at rateKey 100 yet **2.59×** at rateKey 2000 — the "creep cut" does not describe a hard-cornering
window.

## ★ The one direct high-rate test, and it is reassuring
**V71B is the corpus's ONLY rate-axis-complete dose on either lane** (gain_A rec0/rec1 doubled across all
four Y; V69/V70 touched only the `[0,400]` plateau). It produced **ZERO grind-#2 bursts in either arm in
every regime across 835 windows**, and that null is **powered** — P(0) = 0.0002 engaged / 0.0098 manual.
⚠ One route, **r26 only** — it says nothing about r24.

🛑 **grind #1 and grind #2 are NOT the same mode.** A harmonic claim was published and retracted the same
session — see [[feedback-a-ratio-is-not-a-tracking-test]].

Related: [[accord-v62-fixed-the-grinding]] · [[accord-rate-lane-builds-were-never-single-variable]] ·
[[accord-r26-is-structurally-inert]] (whose "r24 carries the lane" framing this supersedes)
