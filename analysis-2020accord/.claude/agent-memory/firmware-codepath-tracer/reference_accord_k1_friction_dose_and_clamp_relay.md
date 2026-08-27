---
name: reference-accord-k1-friction-dose-and-clamp-relay
description: V89's K1 (0xC40D2) runs at 0.3-0.4% of its authority and its ±10 clamp is STRUCTURALLY unreachable; K1 cannot move the relay index (post-nonlinearity gain, invariant) but a ≥25% dose manufactures a V80-class relay through the CLAMP; and 0xC40BC is NOT index-only — it is also a ~3.8x friction-GAIN knob, so the flown 600-vs-6000 result is confounded.
metadata:
  type: reference
---

Sized 2026-08-10 from the V89 image (`_v89_V88BASE-FRICTION.C40D2.204-…_plain_image.bin`).
Reproducer: `analysis-2020accord/studies/models/friction_k1_dose_model.py` (self-checking — it reproduces the kit's own
recorded relay index 7.87 before computing anything else).

## The arithmetic (`FUN_0003b8f6`)

```
@0x3BAB0  iVar20 = pol(gp-0x6752) * gp-0x6abc * 12
@0x3BAB4  ratio  = clamp(iVar20 / cal(0xC40BC), ±1)        # δ = cal/12 = 50 at cal 600
          FRIC   = |model| * ratio * K1/1024 + K0/1024 * ratio    # K0 = 0 on every build
          FRIC   = clamp(EMA(FRIC, α = 0xC40D0/4096 = 408/4096), ±10.0)
@0x3BC0E  gp-0x6ae2 = (short)(int)(FRIC * 1024.0)          # written on the SUCCESS PATH ONLY
```
⚠ The two `*0.5` factors in the decompiled divide **cancel exactly** — `ratio = gp-0x6abc·pol/δ`.
V89 byte-read: `0xC40D2`=204 (stock 102) · **`0xC4080`=0** · `0xC40BC`=600 · `0xC40D0`=408.
⊕ `0xC40D2` is the **only** cell differing from stock in all of `[0xC4000, 0xC4200)`.

## V89's dose is ~0.4% of authority, and its clamp CANNOT be reached [EVIDENCE]

At the engaged median `gp-0x6b98` ≈ 208 ⇒ `|model|` ≈ 0.203: FRICTION ≈ **41.4 counts (ratio 1) / 29.0
(ratio 0.7)** against a ±10 clamp = ±10,240 in the same ×1024 units ⇒ **0.405% / 0.283%.**
The clamp needs `|model| ≥ 10240/204 = 50.2` against a **maximum reachable ≈ 24** (command branch
≤ 8192/1024 = 8.0 because `gp-0x6b98` is hard-clamped; sensor branch ≤ 15 × LERP ≈ 15.9).
⇒ **structurally unreachable at K1 = 204.** Dose ladder: median 10% → K1 ≈ **5041 (24.7×)**,
25% → 12603 (61.8×), 50% → 25206 (123.6×).

## 🛑 K1 CANNOT MOVE THE RELAY INDEX — but the CLAMP is the real hazard

**K1 multiplies the OUTPUT of the nonlinearity, so it never enters the describing function.** Index
`N(50)/N(500)` = **7.867 at K1 = 102, 204, 5041 and 25206 — identical.** ⇒ on the Honda-1.00 /
V75-1.45 / **V80-3.27** scale, **K1 does not move at all.**

🛑 **The V80-class hazard arrives through the ±10 CLAMP instead.** The command distribution is
heavy-tailed (p90/p50 = 4.6×), so setting the *median* to 25% necessarily clamps the top decile:
```
K1= 5041 (median 10%):  p50 10.0%   p90  46.4%            p99  78.7%
K1=12603 (median 25%):  p50 25.0%   p90 116.1% CLAMPED    p99 196.8% CLAMPED
K1=25206 (median 50%):  p50 50.0%   p90 232.2% CLAMPED    p99 393.5% CLAMPED
```
A clamp binding on a large fraction of frames = an amplitude-independent sign-switching output = a relay.
⇒ **only the ~10% rung survives the relay screen.** The friction EMA (corner 16.7 Hz) does not save the
25% rung, because the p90/p99 excursions are manoeuvre-scale (~1 Hz) where it passes ≈0.99.

## 🛑🛑 THE BINDING CONSTRAINT IS MODEL INVERSION AT K1 ≈ 1024, NOT THE CLAMP

Found by the orchestrator, arithmetic verified by me. `FRICTION` is **proportional to `|model|`**, so it
is not an independent friction estimate — it is **a fraction of the applied torque**. With `g = K1/1024`:
```
out = model − |model|·ratio·g
  sign(model) == sign(ratio)  (the NORMAL case: the command drives the motion it commands)
        out = model·(1 − |ratio|·g)   -> ZERO at |ratio|·g = 1, INVERTS above
  sign(model) != sign(ratio)  (a REVERSAL: the command opposes the motion)
        out = model·(1 + |ratio|·g)   -> AMPLIFIES, never inverts
```
⇒ **HARD CEILING K1 ≈ 1024 (10× stock, 5× V89)**, set by the saturated arm (`|ratio|`=1, reached
whenever `|gp-0x6abc| ≥ 50`). Above it the model asserts the plant produces torque **opposite** to what
is applied — a *rate-conditional* inversion of the nine-link sign chain.

🛑🛑 **I FIRST CALLED THIS A RELAY AND A "SWITCHING CONTRAST `C = (1+g)/|1−g|` WITH A POLE AT THE
CEILING", AND CONCLUDED THE USABLE WINDOW WAS EMPTY. THAT WAS WRONG — WITHDRAWN 2026-08-10.**
**The element is CONTINUOUS**: both arms give 0 at `m = 0`, and at `r = 0` both give `m`. There is no
jump. It is a **two-slope (bilinear) element**, not a relay, and `C → ∞` is a *kink getting sharper*,
not a gain diverging. Comparing `C` to V80's describing-function index 3.27 was a bad comparison.

**Derive it properly.** With `m = A·sin(ωt)` and `|sin x| = 2/π − (4/π)Σ cos(2nx)/(4n²−1)`:
```
out = A·sin(ωt) − A·r·g·[ 2/π − (4/π)(cos2ωt/3 + cos4ωt/15 + …) ]
```
### ⇒ FUNDAMENTAL GAIN = 1, EXACTLY, FOR EVERY K1.
**K1 does not change the linear loop gain through this path at all** — which *relaxes* GATE 2 here,
because Path 2's unresolvable runtime-scheduled loop gain is not loaded by K1. What K1 controls is a
**DC offset and EVEN-harmonic injection** at `r·g·4/(3π)`:
```
K1      102     204(V89)  408    512    612(3×)   816    1024(ceiling)
H2 |r|=1  4.2%    8.5%    16.9%  21.2%   25.4%   33.8%     42.4%   <- half-wave rectifier
H2 |r|=0.7 3.0%   5.9%    11.8%  14.9%   17.8%   23.7%     29.7%
slope spread (1−rg .. 1+rg) at |r|=1: 0.90..1.10 → 0.80..1.20 → … → 0.00..2.00 at g=1
```
**The K1 ≈ 1024 ceiling SURVIVES and is sharper than "inversion":** at `g=1, |r|=1` the positive half of
`m` is annihilated and the negative half doubled — a **half-wave rectifier**; above it, full rectification.

⇒ **THE WINDOW IS NOT EMPTY, and it is directly measurable.** The kit's odd/even **harmonic-comb test
detects a 15 % injection** (positive control 1.204 [1.147, 1.566]; measured on-car 0.858 [0.739, 1.000]).
**V89 flew at 8.5 % H2 — below that sensitivity** ⇒ an independent second reason its null is
uninformative. **K1 ∈ [408, 816] (2–4× V89) gives 16.9–33.8 % H2**, resolvable, fundamental gain
untouched, clear of the rectifier. Better posed than the band-ratio test, which has a [0.18, 5.51] floor.

⚠ **Caveats.** (1) The Fourier result assumes `m` is **zero-mean sinusoidal**; where `m` is sign-definite
there is **no distortion at all** and the path is a plain gain `(1∓rg)` ⇒ real H2 depends on `model`'s
**zero-crossing rate**, unmeasured. (2) `|r|` ≈ 0.7 at p50, ~30 % lower throughout. (3) Rests on the
**substituted** `gp-0x6abc` p50/p90 = 35/228 — **`gp-0x6abc`'s physical scale is the highest-value open
item in this lane** (TorquePath: `r15`'s provenance in `FUN_00041464`); it separates *justifying* the
dose from *sizing* it.
📋 **LESSON: I shipped a kill verdict on a metric I had not derived. The Fourier decomposition took ten
minutes. Derive the nonlinearity before ranking it against a recorded hazard.**

## 🛑 THE BIASED DF SAYS IT IS NOT A RELAY AT THE REAL OPERATING POINT

| bias B | span vs δ=50 (ring A≈5) | behaviour |
|---|---|---|
| 35 (p50) | [30,40] inside | **FULLY LINEAR, index 1.00 — not a relay** |
| 228 (p90) | [223,233] outside | **FULLY SATURATED — ring sees ~zero incremental gain** |
| 50 (=δ) | straddles | the only place relay behaviour lives |

⇒ **corrects the golden model:** *"pinned at ±1 across 99.62%"* is over the **±13000 VALID range**, not
the **observed** distribution. ⚠ Contingent on the recorded B/A (p50 35 / p90 228, ring 4–7) — settle it
with measured `gp-0x6abc` percentiles.

## 🛑 `0xC40BC` IS NOT AN INDEX-ONLY KNOB — the corpus result is CONFOUNDED

In the linear region `ratio = x/δ`, so raising δ 50 → 500 **divides the friction gain**: 10.0× at p50,
2.19× at p90; distribution-weighted mean ratio **0.632 @600 vs 0.165 @6000 = a ~3.8× FRICTION-GAIN
contrast** (saturated fraction 40.5% → 3.8%). ⇒ **K1 = pure gain at constant index; `0xC40BC` = gain AND
index together.** The flown *"600 beats 6000 by 2.3× on 6–9 Hz"* is therefore **directionally supportive
of more friction gain but CONFOUNDED — suggestive, not corroborating.**

⊕ **AND IT REFRAMES V89's NULL:** a 3.8× gain contrast produced a measurable 2.3× band effect, but the
kit's cross-build 6–9 Hz floor is **[0.18, 5.51]** ⇒ it cannot resolve under ~3–5×. **V89's 2.0× null is
UNINFORMATIVE, not negative.** The problem is instrument resolution, not a 50× dose shortfall.

## 🛑🛑 FINAL (2026-08-10): K1 IS STRUCTURALLY THE WRONG LEVER — ceiling and effect bind in DIFFERENT RATE REGIMES

**`gp-0x6abc`'s scale IS settled** and is NOT an open item, contrary to two agents' reports:
`memory/accord/builds/accord-v85-flew-lever-delivered-bands-are-null.md` line 35 — **4.923 and 4.697 ct/(°/s) bracket
the inherited 4.7121; envelope ±1,930 ct = ±409.6 °/s** (wheel/column-referred, not motor-shaft).
⇒ **δ = `0xC40BC`/12 = 50 ct = 10.61 °/s.**
★ **Confirmed by flown data**: FlightV89's b6 duty steps 0.104 → 0.312 (r76) and 0.042 → 0.148 (r75)
across the 6–12 / 12–25 °/s bins — the saturation knee lands exactly at 10.61 °/s.

**The conflict, distribution-free:** across the symptom regime (1–13 °/s) `r = rate/10.61` runs
0.094 → 1.0, median ≈ 0.3.
```
rectifier ceiling  binds at r→1 (rate ≥ 10.6 °/s)  =>  g < 1     => K1 < 1024
measurable H2 (r·g·4/3π ≥ 15%) at r ≈ 0.3          =>  g ≥ 1.18  => K1 ≥ 1207
```
🛑 **CORRECTED: the margin is 1.4–3.8×, NOT the "~3.3×" first written** (1206/1024 = 1.18× at r=0.3;
the 3.3 was the *rate-regime* mismatch 1/0.3 mislabelled as the K1 margin). Measured exposure
(FlightV89, r75, 585 s engaged) puts the real operating point LOWER, which widens it:
```
|rate| >= 10.61 deg/s -> 13.3% of engaged frames (|r|=1, saturated); median bin 0.75-1.5 deg/s
   r=1.00 -> K1 362 (fine) | r=0.30 -> 1206 (1.18x) | r=0.245 -> 1477 (1.44x) | r=0.094 -> 3850 (3.76x)
```
⇒ **The conflict is real at 1.4–3.8×. The ceiling binds where the term is SATURATED (13 % of frames);
the effect is wanted where it is on the RAMP (the other 87 %); one scalar gain serves both.**
⚠ **`|r| = 1` is the MINORITY case (13 %), not the typical one.** TorquePath computed 0.385 % by
dividing the 50-ct knee by the **validity window** (13000 = the fault sentinel) instead of the
**reachable envelope** (±1,930 ct) — 2.6 % of reachable, and the distribution, not the range, is the
question. Its saturation *threshold* is confirmed (b6 duty steps across exactly 10.61 °/s).

🛑🛑 **AXIS IDENTITY IS BELIEF, NOT EVIDENCE — everything above rests on it.** TorquePath closed
**`gp-0x6abc` ≡ `gp-0x4f50`** (identity on stock; the scaling path needs magic word `0x49d6b173` AND a
byte cal = `0xE9`; all four sibling cals `0xC40EB/EC/ED/EE` read `0x00`). But `gp-0x6abc` carries a
**RATE** scale while [[reference-accord-state671a-is-oscillation-reversal-counter]] records
`gp-0x4f50` as most likely an **ANGLE** (sin/cos pair, π/180, 2^-20) and has `gp-0x6c2c`'s producer
*differentiating* it. **Both cannot stand.** My read is that the angle call is the weaker one — that
memory flags it as "an INFERENCE from usage context, not a labeled confirmation", and a sin/cos pair
suits a rate feeding a rotating-frame transform equally well. **If `gp-0x4f50` is an angle, this
ladder's axis is wrong and the whole conclusion needs redoing.**
⊕ `gp-0x6c38 = |gp-0x4f50|` is written live in `FUN_00041464` ⇒ if a flown cache carries it, `|r|`'s
distribution becomes a MEASUREMENT instead of an exposure-table inference.

⊕ **The cell that DOES decouple them is `0xC40BC` (δ)** — lowering it raises `r` at low rate while high
rate is already saturated at 1, i.e. it moves the dose without moving the ceiling. 1 reader (`0x3BAB4`);
the flown 600-vs-6000 comparison favours that direction (600 beat 6000 by 2.3×) and the standing
"FREEZE at 6000" is contradicted. 🛑 It is the INDEX knob, so it moves relay-ness directly — flagged as
the structurally correct place to look, NOT proposed.

⊕ **`gp-0x6bf6` SEPARATES `|model|` FROM `ratio` FOR FREE** — `= clamp(2639 × model, ±20000)`, written
BEFORE friction/inertia are subtracted, **1-writer / 0-reader**. With `gp-0x6ae2` already probed:
`ratio = (gp-0x6ae2/1024) / (|gp-0x6bf6|/2639) × (1024/K1)`. Better than a `gp-0x6ae0` rung, which gives
only d/dt of the rate.

⚠ **MEASURED (FlightV89, routes 75/76): `|model|·ratio ≥ 0.3137` on 3.7 % / 6.9 % of engaged frames and
0.9 % of the micro-ratcheting regime.** The term is small exactly where the symptom is.
🛑 **My clamp-binding table above is WITHDRAWN as route-mismatched** — I sized `|model|` off V87 route 71
(median cmd 208); routes 75/76 run 74/77, so `|model|` was 2.8× too high. The 427 channel also **rails at
1638**, so the 2080-count threshold was never measurable. And the p50=35 / p90=228 I used for
`gp-0x6abc` are **band-filtered bias figures from the V85 biased-DF analysis, not whole-distribution
percentiles** — a category slip, withdrawn.

📋 **THREE POSITIONS ON ONE LEVER IN ONE SESSION** — "only the 10 % rung survives" (wrong, past
inversion) → "empty window via a contrast metric" (wrong, category error) → this. **Only this one is
distribution-free.** Derive the nonlinearity and confirm the axis scale BEFORE ranking a dose.

## GATE 2 — NOT statically closable
`FRICTION → model → gp-0x6bfc → resid → gp-0x6b70` is Path 2, whose loop gain is runtime gain-scheduled
— see [[reference-accord-residual-lerp-gp3714-runtime-adaptive]]. Any loop-gain figure for a K1 raise is
an invention. What IS statically bounded: the ±10 clamp, which the 10% rung stays off.

Related: [[accord-v80-damper-relay-and-grind1-inert]], [[accord-v89-built-plant-model-friction]],
[[reference-accord-observer-gate-tautology-and-term-mismatch]].
