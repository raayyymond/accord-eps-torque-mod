---
name: accord-fprime-compression-explains-v89-and-v97
description: "The firmware desensitises the observer lane 6.3x exactly when the driver pushes — f' is 2.174 hands-off but 0.346 hands-on. One mechanism explains V89's flat result AND V97's felt-null, and it gives the kit its first dose-in-counts against a measured perceptual floor."
metadata: 
  node_type: memory
  type: reference
  originSessionId: fa9eb530-c732-4c40-8991-98e824e54a49
  modified: 2026-08-13T07:22:17.215Z
---

★★★★★ **THE FINDING OF 2026-08-13, and the first time this kit has had a DOSE IN COUNTS to compare
against a MEASURED PERCEPTUAL FLOOR.**

## The mechanism [EVIDENCE — deterministic, no model, no mask dependence]

`f′ = dY/dX` of the Stage-2 LERP is a **deterministic function of `|iVar6|`**:

| `\|iVar6\|` ct | 0–178 | 178–356 | 356–719 | 719–1200 | 1200–1800 | **1800–3000** | 3000–5000 |
|---|---|---|---|---|---|---|---|
| **f′** | 2.539 | **2.174** | 1.496 | 0.948 | 0.488 | **0.346** | 0.248 |

Route 81, engaged, scored under **two independent masks** (`steeringPressed`, and the D3 fix from
[[reference-accord-steeringpressed-mask-excludes-the-symptom-regime]]):

| | steeringPressed | D3 mask |
|---|---|---|
| `\|iVar6\|` p50 **hands-ON** | **2,829 ct** | **2,818 ct** |
| `\|iVar6\|` p50 hands-OFF | 188 ct | 337 ct |
| **f′ p50 hands-ON** | **0.346** | **0.346** |
| **f′ p50 hands-OFF** | **2.174** | **2.137** |
| ratio | **0.159×** | **0.162×** |

🛑 **The two masks agree to 2 %.** ⇒ **THE FIRMWARE DESENSITISES THIS LANE 6.3× EXACTLY WHEN THE
DRIVER PUSHES** — and *pushing* is how the operator provokes the symptom.

## Why it matters: it explains TWO nulls with one mechanism, and it PREDICTED V98

**Every perturbation of `iVar6` reaches the car through `f′`.** V89 and V97 both perturb `iVar6`, and
**both had their directions argued on hands-off data — the steep part of the curve — while the symptom
lives on the flat part.**

🛑 **The residual is NOT small** (V98 is right: MODEL ≈ ACTUAL, `b6` = 0.4235, 288 ct RMS at 6–9 Hz).
**What is small is the SLOPE that carries changes in it.** Unlike the arm-inequality story — which V98
killed — this account is consistent with comparable arms, a lively 427 lane, V89's flat contrast and
V97's felt-null, and **requires nothing unmeasured.**

## ⭐ PATH 2 IS AUTHORITATIVE — the "maybe it barely matters" hypothesis is REFUTED
`d(gp-0x6b94)/d(gp-0x6b70)` = **0.2529 / 0.2565 / 0.2617** at 6 / 7.79 / 9 Hz. **No dilution anywhere**
— every link is unity, an enable byte = 1, a flat LERP (`tp+0x7aca..0x7ad8` = `[1024]×8` ⇒ 1.000 at
every speed), or the PID. Positive control **passed first**: reproduces the independently-recorded
*"+41.8°…+55.0° lead at 21 Hz, |D|≈|P|"* at **|D|/|P| = 1.055, arg H = +41.81°**.
⊕ Both structural gates are **OPEN**: `gp-0x67ac` const-0, and **`gp-0x67ab` ≡ 0 STRUCTURALLY** — a
sticky-OR over roles {2,3,4} in `0xC4124` = `00 00 05 00 05 05 00 00 00 05 00`, **no 2/3/4 anywhere**,
byte-identical across 65 images. Closes an OPEN item from `HANDOFF-2026-07-27:287`.

## ⭐ THE PERCEPTUAL BRACKET — the "underivable" step is now an interpolation
| build | measured in-band delivered change | operator | felt |
|---|---|---|---|
| V88 | 15–22 Hz command **0.549 [0.407,0.844]** | *"grinding fixed"* | ✅ |
| V62 | 18–22 Hz **8–42× down** | *"grinding at 2–5 mph is gone!"* | ✅ |
| V85 | 6–9 Hz **1.088 [0.746,1.451]** | *"barely, perceptibly better (unsure)"* | ~✗ |
| V89 | **0.947 [0.827,0.979]** | *"fixed nothing"* | ✗ |

⇒ **~0.55× (−45 %) IS felt. ~1.09× (+9 %) IS NOT.**

## 🛑 THE DOSES — every 2026-08-13 candidate, scored against that floor
| lever | dose in his regime | vs +9 % floor |
|---|---|---|
| `0xC63AC` 150→102 (V99 hygiene) | 1.1–3.6 ct = **0.8–2.5 %** of Path-2's 140.6 ct | **below, ~20×** |
| **`0xC40BC` 600→300 (V99's lever)** | 0.7–1.7 ct = **0.5–1.2 %** | **below, 8–18×** |
| `0xC63AE` 1024→**2048** | ≈ **+28 %** on the lane, ≈ +177 ct | ⭐ **ABOVE** |

**`0xC40BC` is dead in his regime for a structural reason [EVIDENCE, orchestrator-verified]:
93.1 % of hands-on engaged frames sit ABOVE the 10.61 °/s knee, where 300 and 600 are ARITHMETICALLY
IDENTICAL.** Mean ramp ratio **1.050** — a ×1.05, not a ×2. ⊕ Sensitivity is one-directional: a larger
motor-referred scale puts the knee *lower*, so *more* frames are inert, never fewer.
🛑 **And the structural kill: `friction = |fVar18| · ramp · K1/1024` — `0xC40BC` and `0xC40D2` are TWO
FACTORS OF THE SAME PRODUCT, not two levers. V99's perturbation is 0.096× V89's, and V89 measured FLAT
against a well-powered placebo band (0.92 σ).**
🛑 **The direction is right but unreachable:** V85's 600→6000 moved the knee out of the regime and the
ratchet got **worse**; but reaching his p50 of 83 °/s needs `norm` ≈ 4,700–11,000 — **which IS 6000,
which flew and was worse. The dose requirement and the flight result are in direct conflict.**

## ⚠ CORRECTIONS THIS PRODUCED — all decision-bearing
1. 🛑 **"The two poles are an exact match and V97 broke it" ⇒ the CONSEQUENCE is REFUTED.** The cell
   identity is real and probably deliberate (`round(0.1·4096) = 410`, but Honda shipped **408 = 4×102**;
   `408/4096 == 102/1024` exactly) — **but it is a match between two STAGES, not the ARMS.** The arms
   **do not share an input** (a plant model vs a six-lane weighted sum), `0xC40D0` is one stage of five
   on a sub-path, and **stock is already 84° and 0.557-vs-0.906 apart.** 🛑 **Never quote the
   0.111/0.136/0.151 "phantom".** What survives: V97 moved the arms **further apart** (+7.82°, +5.4 %).
2. 🛑 **`b5` = 0.0000 does NOT license "REQUEST is minor"** — it tests REQUEST vs **ACTUAL**; the
   denominator is the **RESIDUAL** (`|iVar6|` p50 **389 ct**, 288 ct RMS at 6–9 Hz). The kit's own
   already-retracted "≤ 9 % share" error, repeated. **REQUEST is the most important unmeasured term in
   the chain** — zero cal cells, shadow-lockstep protected, and our own 4× `0xC6CD0` feeds it.
3. 🛑 **427's "broadband ⇒ no band-specific claim" verdict was an ARTEFACT.** 427 is transmitted at
   **49.835 Hz**; a ZOH images 5–15 Hz onto **35–45 Hz**, so the negative control band was outside
   Nyquist (a pure 7.79 Hz tone reads 0.163 RMS there out of nothing). With a valid **20–24 Hz**
   control, 6–9 Hz excess is **2.30× on 427 and 1.97× on column torque — they agree.**
4. 🛑 **V86's `gp-0x67ab < 2` rung could NEVER have fired** — `< 2` is true of both the open (0) and
   closed (1) states. `BUILD-LINEAGE.md` cites it as *"lever in force three ways."* **A falsifier that
   could not fire.** The gate is open; V86 is not why we know it.
5. ⚠ `0xC63A0` weights **`gp-0x6bd0`**, not `gp-0x6b26` (that is `0xC63A6`). Its four-build null is
   explained by `gp-0x6bd0` ≈ 0 on 87,940 frames — **not** by the FactorC×FactorE dead-zone product.

## ⇒ THE V100 SHAPE
1. ⭐ **`|gp-0x6ad6| ≥ 8192`** — the PID clamps its feedback at ±8192 while the reference runs to
   ±25600, and term 0 alone can rail it. **If railed, Path-2's MARGINAL authority is exactly zero with
   every gain above unchanged.** A comparator: no LSB, no ceiling, **its duty is the answer**, and a
   null retroactively explains V89 *and* V97. **This cell has never been on the wire.**
2. **`0xC63AE` 1024 → 2048** — the only candidate scored today that clears the perceptual floor.
   🛑 Direction is **UP, not down** (the scale sits in the chain **twice**: `(scale/1024) × LERP′`).
   🛑 Never 0 (flattens to a relay); **never far above 2048** — at 4096 the index pins at the ±8192
   clamp and a clamped output IS a relay, V80 class. 🛑 **RULE 7 unproven** (`decompile_function(0x382d8)`).
   ⚠ **It must FOLLOW the `gp-0x6ad6` rung, not precede it** — raising `gp-0x6b70` pushes toward that clamp.

Related: [[accord-v98-comparator-ranked-the-observer-arms]] ·
[[accord-steering-sign-convention-confirmed]] · [[accord-friction-polarity-more-assist]] ·
[[reference-accord-steeringpressed-mask-excludes-the-symptom-regime]]
