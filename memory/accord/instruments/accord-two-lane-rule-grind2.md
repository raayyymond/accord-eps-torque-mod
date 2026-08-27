> 🛑🛑 **AMENDED TWICE — READ THIS FIRST.**
>
> **2026-08-05.** ⚠ **V72's row is r24 x1.000 / r26 x0.250, not 3.414 / 0.250** — its r24 half was mode-10 `gain_B` and therefore inert. The rule survives, but **V72's grind-#2 result is confounded with stock**. ~~What governs grind #2 is V62's `sar`.~~ ← **RETRACTED 2026-08-06, see below.**
>
> **2026-08-06 — THE RULE'S SHAPE SURVIVES, ITS NUMBERS DO NOT.**
> 1. 🛑 **"What governs grind #2 is V62's `sar`" is REFUTED.** `V71C` carries **neither** `sar` byte (`0x3AB76` = `aa32`, `0x3AC20` = `aa42`, byte-read) and produced a spectrally identical event: **44.31 Hz**, p99 **1741.9** = **12.2x** the max of any non-bursting build, same-segment non-burst floor **25.5**. V71C holds **3 of the corpus's 13 merged events in 5.28% of the exposure, P(>=3) = 0.028.** ⇒ **a `sar`-stock build is NOT safe by construction.**
> 2. ⚠ **V62/V65's DELIVERED r24 is x2.000, not x3.414** — `sar 0xa -> 0x9` is a flat doubling of BOTH lanes at every speed and rate, not the `0xC6446` arm. ⇒ **the "r24 >= 3.4x" threshold below is WRONG; V62/V65 burst at 2.000x.** Quote the shape ("both lanes elevated"), never the number.
> 3. 🛑 **The r26 cut's NECESSITY is NOT established.** The V67/V68 row's "none" is **11.5 s of engaged creep cornering at P(0) = 0.80** — and it was the operator's HEDGE, not a null. See [[feedback-never-log-a-hedge-as-a-null]] and [[accord-grind1-fix-and-grind2-are-collinear]].
> 4. ⚠ **"V71C's r24 is a cut (0.93x) at rateKey 100" is WRONG** — it is a **1.71x BOOST**. That figure came from `lib/_r58_lib.py` sweeping against `_v70_plain_image.bin` at **mode 10**. The companion **2.59x at rateKey 2000 is correct** (V70's edit did not reach that segment). Corrected model: `analysis-2020accord/lib/_grind2_delivered_lib.py`.

---

# ★★★★★ THE TWO-LANE RULE — why fixing one grind always fed the other

**Measured 2026-08-05 across six builds including the two new flights (V71B = route `54`,
V71C = route `58`).** This answers the operator's central question of the session.

## The rule — [EVIDENCE for the association]
High-rate corner of both surfaces (creep, rate index 3000), gains read from the shipped images:

| build | **r24 high-rate ×** | **r26 high-rate ×** | creep grind #2, measured |
|---|---|---|---|
| stock (V58/V59/V64) · V69 · V70 | 1.000 | 1.000 | **none** (0 / 1207.0 s non-hwy, P(0)=0.019) |
| **V71B/`r54`** | **1.000** | **2.000** | **none** (0 bursts / 835 windows, max 61) |
| V72 · V73 · V74 | **1.000** | 0.250 | **none** (0 / 1223.7 s non-hwy, P(0)=0.018) |
| V62/V65 | **2.000** ⚠ *(was 3.414)* | 2.000 | **YES — worst in corpus** |
| **V71C/`r58`** | **3.414** | 1.500 | **YES — 3 creep windows = 1 merged EVENT, max 1742** |
| **V67/V68** → **V76** | **3.414** | **0.250** | ⚠ **UNMEASURED — 11.5 s, P(0) = 0.80** |

> ~~**Creep grind #2 requires r24 high-rate ≳ 3.4× AND r26 high-rate ≳ 1.5×. Cutting EITHER kills it.**~~
> **CORRECTED:** *creep grind #2 has only ever been seen with **BOTH** lanes elevated, and each
> single-lane arm is clean — r26 = 2.000× alone (V71B) and r26 = 0.250× with r24 stock (V72/V73/V74).*
> **Do not quote a numeric r24 threshold: V62/V65 burst at a delivered 2.000×.**

**Six builds, no exceptions. Neither lane's multiplier predicts the outcome alone** — r26's ranges
0.25 → 2.00 across them.
⇒ **[BELIEF] Raising r24 to fix grind #1 feeds grind #2 UNLESS r26 is also cut.** V67/V68 moved both and
reached grind #1 = 109/111 **without an observed creep grind #2** — but 🛑 **that "without" is
UNMEASURED, not clean**: 11.5 s + 0.0 s of engaged creep cornering, P(0) = 0.80, power 19%.
⚠ **[BELIEF] on the product-of-two-lanes mechanism, and V67/V68's cell is the WEAKEST evidence in the
table.** 🛑 **Corrected 2026-08-06:** the earlier "~42 s of engaged creep" is the *plain* creep figure;
in the cell where **18 of 21 creep bursts actually live** (|ang| ≥ 100°) it is **11.5 s**, and in the
high-rate creep cell it is **0.0 s**. ⇒ **the r26 cut's necessity is not established at all**, and
[[accord-grind1-fix-and-grind2-are-collinear]] shows no build has ever separated the two symptoms.

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
🛑 **Price any future lever against the RATE axis, not just the speed axis.** V71C's r24 runs
**1.71× at rateKey 100 → 2.26× at 1400 → 2.59× at 2000 → 3.41× at 3000**, all at 0 km/h, because a flat
arm replaces a LERP that rolls off with rate. **A single-number "r24 dose" for a gated-arm build is
meaningless.** ⚠ *This line previously read "V71C's r24 is a cut (0.93×) at rateKey 100" — that came from
the `lib/_r58_lib.py` mode-10/V70-baseline defect and is corrected here; the 2.59× was always right.*

## ★ The one direct high-rate test, and it is reassuring
**V71B is the corpus's ONLY rate-axis-complete dose on either lane** (gain_A rec0/rec1 doubled across all
four Y; V69/V70 touched only the `[0,400]` plateau). It produced **ZERO grind-#2 bursts in either arm in
every regime across 835 windows**, and that null is **powered** — P(0) = 0.0002 engaged / 0.0098 manual.
⚠ One route, **r26 only** — it says nothing about r24.

🛑 **grind #1 and grind #2 are NOT the same mode.** A harmonic claim was published and retracted the same
session — see [[feedback-a-ratio-is-not-a-tracking-test]].

Related: [[accord-v62-fixed-the-grinding]] · [[accord-rate-lane-builds-were-never-single-variable]] ·
[[accord-r26-is-structurally-inert]] (whose "r24 carries the lane" framing this supersedes)
