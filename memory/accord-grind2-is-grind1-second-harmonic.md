# ★★★★★ Grind #2 IS grind #1's 2nd harmonic — and the TWO-LANE rule explains every build

**Measured 2026-08-05 on routes `54` (V71B) and `58` (V71C).** This answers the operator's central
question — *"why does fixing one grind introduce the other, and why do they feel like the same thing?"*

## The frequency relation — [EVIDENCE]
Free peak-finding geometry (f_lo 15–26 Hz, f_hi 35–49 Hz, prominence ≥ 8) permits ratios **1.35–3.27**,
so 2.000 cannot be manufactured by the band choice:

| route | windows | f_lo | f_hi | **f_hi / f_lo** |
|---|---|---|---|---|
| V71B/`r54` | 156 | 21.20 | 42.91 | **2.003 [1.997, 2.008]** |
| V71C/`r58` | 58 | 21.34 | 43.79 | **2.005 [1.988, 2.255]** |
| V69/`r4f` | 78 | 20.71 | 41.86 | **2.004 [1.998, 2.030]** |

**Stress tests:** negative control (10–16 Hz fundamental, where 2.000 is unreachable) returns **3.91–3.99**
⇒ passes, **and reveals a harmonic ladder ~10.6 / 21.2 / 42.9 Hz**. Residual-fit: **2 × grind #1 beats
5 × the ratchet** on every route (5.40 vs 7.53 · 7.29 vs 9.64 · 4.20 vs 7.39).
⚠ **Two tests do NOT fully support a pure-harmonic reading:** a 35–49 line stands in **20.7–28.4%** of
windows where the 18–22 line is *absent* (enriched by, not conditional on), and amplitude locking is weak
(ρ 0.30–0.44 engaged-only).

⇒ **[EVIDENCE] the frequency relation. [BELIEF] the mechanism:** with this mode's crest factor
**2.07–2.45** (a sine gives 1.414), grind #2 is most likely **the waveform SHAPE of grind #1 — a
distortion product of a clipping nonlinearity**, not an independent resonance.

🛑 **This REVERSES the record's earlier "not a harmonic" claim** (Theil-Sen slope of grind-#2 f0 on
grind-#1 f0 = 0.173 [−0.92, +1.59]). That came from the corpus; the direct measurement wins.

## ★★★★ THE TWO-LANE RULE — 6 builds, no exceptions
High-rate corner of both surfaces (creep, rate index 3000), gains read from the shipped images:

| build | r24 high-rate × | r26 high-rate × | creep grind #2 |
|---|---|---|---|
| stock · V69 · V70 | 1.000 | 1.000 | **none** |
| **V71B/`r54`** | **1.000** | **2.000** | **none** (0 bursts, max 61) |
| V62/V65 | **3.414** | 2.000 | **YES — worst in corpus** |
| **V71C/`r58`** | **3.414** | 1.500 | **YES — 3 events** |
| **V67/V68** | **3.414** | **0.250** | **none** |

> **Creep grind #2 requires r24 high-rate ≳ 3.4× AND r26 high-rate ≳ 1.5×. Cutting EITHER kills it.**

**Neither lane's multiplier predicts the outcome alone** — r26's ranges 0.25 → 2.00 across these six.
⇒ **Raising r24 to fix grind #1 feeds grind #2 UNLESS r26 is also cut.** Every previous attempt moved
only one lane. **That is the whole answer to the operator's question.**
⚠ **[EVIDENCE] for the association; the product-of-two-lanes mechanism is [BELIEF]. V67/V68's cell is the
WEAKEST in the table** — ~42 s of engaged creep.

★ **In the corner regime every burst-producing cell in the corpus is the ≥1400 rate-index cell**
(V62/V65: 14 bursts at ≥1400 vs 1 at the knee vs 0 at the plateau) ⇒ **grind #2 is a high-rate-index
phenomenon.**

## ★ grind #2 follows the GATE, not the driver's hands — [EVIDENCE]
V62/V65 (**ungated**) burst in **both** arms at equal rates — 0.0444/s engaged vs 0.0430/s manual.
V71C (**gated**) bursts **only** engaged — 0.0478/s vs 0.0000/s.
⇒ caused by the rate-lane arm being **live**, not by the plant.
⚠ **This contradicts the operator's recollection that grind #2 was worse WITHOUT openpilot.** The corpus
does not carry it — manual rate is never higher than engaged on any build. Likeliest reason: on the
ungated builds it was equally present hands-on with LKAS off, which is far more salient and memorable.

## Consequence for any future build
**Any lever that raises r24's HIGH-RATE multiplier must cut r26 in the same build.** See
[[accord-v72-design-both-lanes-whole-axis]] and [[accord-r26-is-structurally-inert]] (whose "r24 carries
the lane" framing this supersedes).

Related: [[accord-v62-fixed-the-grinding]] · [[accord-rate-lane-builds-were-never-single-variable]] ·
[[accord-grind1-ladder-monotone-at-peak-velocity]]
