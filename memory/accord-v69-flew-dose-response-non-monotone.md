---
name: accord-v69-flew-dose-response-non-monotone
description: "★★★★ V69 flew route 4f 2026-08-04. Grind #1 is BACK at creep, the dose was fully delivered, and the rate-lane dose-response is NON-MONOTONE with a minimum near 2x — so V70 keeps V69's gateless speed-shaped topology at HALF the dose (x2)."
metadata:
  type: project
---

# ★★★★ V69 FLEW — GRIND #1 IS BACK AT CREEP, AND THE DOSE–RESPONSE IS NON-MONOTONE

Route **`4f--61171e660d`**, 8 segs, **481.7 s**, 47,990–47,996 frames.
✅ **FLIGHT-CLEAN two ways** — `ST==4` **0**, `ST==3` **0**, gridded *and* raw un-gridded `0x18F`;
watchlist absent; `steerSaturated` 2 / `steerOverride` 667 ordinary.
✅ **Build identity FROM THE PROBE:** byte4 = `0x87` on 100% of frames, bit7 set, **bit3 = 0 ⇒ V68
excluded absolutely**. ★ V66/V67 excluded **empirically** — their bit6 ≈ `latActive` at 99.98%, and `4f`
is **345.7 s engaged with bit6 = 0 in every frame**. V69-×2 excluded **structurally** (`0xC4B54`
`61`→`60` makes bit4 constant 1).

## ★★ THE DOSE WAS FULLY DELIVERED — saturation eliminated
Transfer-corrected `|dtorque|` max **633.9**, **0.0000%** above V69's 683 rail ⇒ **≥ 99.9% of engaged
time got the full 4.000×.** The pre-flight 0.81× margin worry did not bite ⇒ **the result below cannot
be explained as clipping.**

## 🛑 GRIND #1 IS BACK — EVIDENCE
Engaged pooled 18–22 Hz **f0 20.42 Hz, prominence 13.47** (criterion > 4), f0 identical across all 8
search bands, manual arm **1.25 = no line**, present in **6 of 8** segments (absent only on the pure-
highway seg 6). **Order veto cleared by a contrast a tyre cannot fake** — engaged-vs-manual, within
route, speed-matched: **4.726 [1.082, 18.20]** vs null [0.36, 3.24], with the 24–28 Hz negative control
and 1–4 Hz validity both inside.

| contrast | ratio | null |
|---|---|---|
| V69 / Kd2 (V62+V65) | **1.381 [1.026, 1.724]** | [0.83, 1.16] |
| V69 / Kd2-gated (V67+V68) | **1.654 [1.244, 2.167]** | [0.88, 1.13] |
| **creep <20 km/h vs V62/r37 — block** | **2.244 [1.438, 3.191]** | — |
| **creep <20 km/h vs V62/r37 — episode** | **2.235 [1.533, 3.429]** | — |

⚠ **The ALL-SPEEDS headline loses its CI under the conservative episode unit ([0.870, 2.598]); the
CREEP result does not** — it holds under both units. Quote the creep number.
★ **"Lands on stock at ≥ 50 km/h" CONFIRMED** — 1.066 [0.690, 1.677] vs the Kd1 pool and
0.789 [0.515, 1.252] vs V59/r2c, both inside null. ⚠ the *"elevated vs V67/V68 at highway"* half is
**WEAK** — its 24–28 Hz negative control moves as much as the subject band.

## ★★★ NON-MONOTONE, minimum near 2×
Median `e_18-22`, engaged creep: **0× (V61) 2501 · 1× stock 879 · 2× (V62/V65) 168 · 2× gated
(V67/V68) 109 · 4× (V69) 746.**
⚠ Cross-route medians **without covariate matching** — read beside the matched contrasts above.

## ★★ ENGAGEMENT-CONDITIONAL THOUGH THE DOSE IS NOT
V69's 4× applies **identically in both arms** (the gate is reverted). Yet **manual at 4× is
indistinguishable from stock — 1.070 [0.383, 1.396], inside null** — while engaged is **2.244×**.
⇒ **the mechanism is inside the CLOSED LKAS LOOP, not open-loop damping quality.**

## 🛑 MECHANISM — BELIEF, with the dose–response as the EVIDENCE
**(a)** a plain derivative-feedback optimum overshot; **(b)** a **parametric gain collapse** —
`gp-0x6ac0` is loaded **`ld.hu` (UNSIGNED) @`0x3AAC4`**, so the gain index sweeps **0→peak→0 twice per
cycle**, and V69 turned Honda's 2.0× rate rolloff into **8.0×**, making the damper **weakest at peak
velocity**. Modulation depth at `A_rk` 1927: **1.00×** (V67 flat) / **1.49×** (V62) / **5.96×** (V69);
effective-gain crossover `A_rk` ≈ **1300** and **1200–1330** by two methods.
**Neither is established. Do not build as if (b) were settled.**

## Grind #2 — a replication, not a result
Creep 0 bursts, engaged P(0) = 0.0042 — but **V67 already gave 0 bursts in 158.7 s at P(0) = 0.0005**.
Corner cell under-powered on `4f` (engaged 26.9 s, manual 42.2 s). ★ Genuine non-regressions: 4× did
**not** re-introduce creep grind #2 (max 142.2 vs V62/V65's 1830.7), and V69's manual creep is the
**first dosed manual arm since V65** — 0 bursts in 69.1 s, max **50.5**, P(0) = 0.0512 (*just short*).
🛑 **The "P-A" hypothesis is REFUTED**: premise confirmed (all 24 Kd=2 bursts at p90-rate ≥ 400, 19/24
≥ 1126, 0/96 windows in the lowest stratum) but in the `[1400,∞)` stratum carrying 10 of 18 engaged
bursts **V67 ran 99.8 s at 2.719× — more than V62's flat 2.000× — and produced ZERO**, expected 12.00,
**P(0) = 6e-6** ⇒ **r24 dose at the operating point is NOT sufficient to cause grind #2.** ⚠ Not a
clean single-variable contrast (V67 also carries `0xC646C` decouple, `0xC6CD0`=3564, mss0) — fine for
refuting sufficiency, not fine for a positive claim.

⇒ ★★★ **V70 KEEPS V69's GATELESS SPEED-SHAPED TOPOLOGY AND HALVES THE DOSE TO ×2**, with a repaired
probe. 🛑 **Restoring V67/V68's scalar arm was tried, BUILT, and OVERRIDDEN by the operator** — that arm
**replaces** a surface Honda rolls off, so `arm/LERP` peaks at highway (**2.44×**) and re-introduces the
high-speed grind. **An instrument null in 30–49.5 Hz was never evidence about a >50 Hz mode** — both
vibration instruments are blind above 50 Hz; see [[feedback_operator_lived_experience_overrides_analyst_recs]]. The two unknowns worth probe
bits: **`gp-0x67fa`'s runtime state** ([[accord-gp67fa-state-gate-on-assist-chain]]) and
**`a = gp-0x69a4/1024`** ([[accord-r26-is-structurally-inert]] — reversed).
🛑 **Do not aim V70's rate lane at the lane-change transient** —
[[accord-lane-change-transient-is-dose-independent]].

See [[accord-v69-built-speed-shaped-rate-lane]], [[accord-v69-ratchet-probe]],
[[feedback-size-probe-rungs-against-lane-reachable-output]], [[feedback-episodes-not-windows-and-the-noise-floor]].
