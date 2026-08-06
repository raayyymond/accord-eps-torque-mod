---
name: accord-v70-flew-grind1-back-at-stock
description: "★★★★ V70 flew route 50 on 2026-08-04, flight-clean. Grind #1 is BACK AT THE STOCK LEVEL (median e_18-22 engaged creep 729.1; CONSISTENT with stock and V69, EXCLUDED from V62/V65 and V67/V68 at P=0.0000). Grind #2 shows 0 bursts but 'gone' is NOT established. The ratchet's Q is measured at ~40. The probe proved r26 LIVE and vindicated five detector nulls."
metadata:
  type: project
---

> 🛑 **AMENDED 2026-08-05 — READ THIS FIRST.** **Grind #1 read at stock level because V70 WAS stock** — its only edit was mode-10 `gain_B` on a mode-24/26 car. This is not a dose result; it is a replication of the stock condition.

# ★★★★ V70 FLEW — GRIND #1 IS BACK AT THE STOCK LEVEL

Route **`75604b0a432fdc89_00000050--50f2e00e8f`**, segments 0–2, **181.6 s**, **18,010 frames**.
✅ **FLIGHT-CLEAN** — `ST == 4` **0** and `ST == 3` **0**, on the gridded cache *and* the raw un-gridded
`0x18F` stream; watchlist absent. **The zero-EME streak extends.**

⚠ **THE CENSUS MATTERS MORE THAN USUAL — this is a SMALL route.** Engaged **72.4 s**, manual
**107.8 s**, **engaged creep 28.9 s**, **highway ≥50 km/h 7.9 s**, **ZERO manual highway exposure**.
**Segment 0 is PARKED — boot only.** Read every null against that census, not route `4f`'s 481.7 s.

## 🛑 GRIND #1 IS BACK AT STOCK [EVIDENCE]
Median `e_18-22` engaged creep **729.1**. Resampling **V70's exact 5-block structure** from each arm:
**CONSISTENT** with stock (P = 0.635) and with V69 (P = 0.495); **EXCLUDED** from V62/V65 and from
V67/V68 (both **P = 0.0000**). Survives **(effort, |rate|)-matching**.
★★ **METHODOLOGICAL, worth its own line: CI OVERLAP IS NOT A TEST.** This subsample-at-matched-exposure
test **excludes V62's level at P < 5e-5** where a CI comparison called the same contrast undecided.
⇒ **"V70 is not at V62's level" IS established; where it sits BETWEEN stock and V62 is NOT.**
⚠ **The 24–28 Hz negative control is NOT flat** — V70 reads **1.88× stock** there because provoked
steering raises the floor; subject-band **excess over control** vs V62 is still **2.59×**, so the
exclusion survives but the raw ratio is inflated.
⚠ **On the scale-free 18-22/24-28 ratio V70 (37.4) sits BELOW stock (76.0).** 🛑 **That view does not
rank-order the builds the way `e_18-22` does. Report both; pick neither.**
🛑 **AND GRIND #1 IS BLIND TO r24 GAIN — this retires a MEASUREMENT TOOL.** Log-log slope of median
`e_18-22` on r24 gain **−0.144 [−0.991, +0.347]**; stock/V70/V69 pairwise **P = 0.667 / 0.610 / 0.426**
⇒ **grind #1 cannot be used as an in-force check for the r24 lane on ANY future build.** Structural,
not a power limit. ⊕ It also means grind #1 **cannot adjudicate the bit6 (a)-vs-(b) question**.

## GRIND #2 — not a regression, but "gone" is NOT established
**0 bursts everywhere**, max **94.6** vs V62/V65's **1830.7**. But at V62's own burst rate:
**P(0) = 0.34** engaged-creep · **0.56** corner · **0.98** highway; power **66% / 44% / 2%**.
⇒ **the highway cell says nothing at all.** And V67 had already eliminated engaged-creep grind #2
(P(0) = 0.0005), so a clean V70 creep arm **REPLICATES an already-clean arm — it does not credit V70.**

## The ratchet, and "stiffer"
**Q ≈ 40 at f0 = 7.793 Hz** — [[accord-ratchet-q-measured-40]] (✅ it **confirms** the record's Q ≈ 36;
what it supersedes is only *"Q is not measurable at NFFT 256"*).
★★★★ **And the bigger result: the ratchet is engagement-REQUIRED and NO BUILD HAS EVER MOVED IT** —
**73/88 = 83.0% engaged hands-off vs 0/118 = 0.0% manual hands-off** across four routes/builds,
p = 3.8e-41, rate **build-independent** ([[accord-ratchet-is-engagement-required]]).
**Per-engaged-window ratchet rate is identical across V70/V69/V62 (32.1 / 34.4 / 32.8%) ⇒ V70 did not
add ratchet events**, consistent with that build-independence.
🛑 **"Stiffer" is not detected by any bus-side instrument** (effort/impedance 0.79–0.97× every
predecessor, all CIs containing 1), and **the saturation mechanism proposed for it is REFUTED
arithmetically**: the clamp at `0x3AC42` is **hard** and exactly linear below the rail, and V69 spent
**0.0000%** of engaged time at or above its 683 rail (max 633.9). **[BELIEF]** the likeliest referent is
**the ratchet itself** — 4,894 counts arriving **0.8 s** after the first engagement.

## The probe readouts
- 🛑🛑 **bit6 = 0/18,010 and NOT vacuous** (replay predicts 311 hits on route 50's own data, stock 52).
  ⚠ **But the arm-selection reading is the WEAKER one**: the same rung read **0/47,990 on V69's `4f` at
  DOUBLE the dose**, needing only 49 counts — which arm selection cannot explain, since the mask arm is
  1024 on every build. ⇒ **[BELIEF] an under-ranged / mis-reconstructed rung is better-supported; the
  corpus cannot settle it.** The durable part is the lesson —
  [[feedback-probe-the-gain-in-force-not-a-lane-output]].
- ★★ **bit5 (`gp-0x67fa == 10`) = 0.0000%** ⇒ **the five-build detector null is GENUINE** and the
  state-gate explanation is **REFUTED** — [[accord-gp67fa-state-gate-on-assist-chain]]. ⚠ licenses
  *"the call was made"*, not *"the body ran"*; `FUN_00046ea6(5)` stays OPEN.
- ★★ **bit4 tracked bit3 ⇒ r26 is LIVE** — [[accord-r24-r26-two-selectors-one-gate]].

## 🛑 The other retraction from this drive — the "peak-velocity / rateKey collapse" hypothesis
**DEAD ON SCALE B; on scale A it survives only at the ~90th-percentile worst instant.**
🛑 **Its founding number was never a burst measurement:** `A_rk = 1927` is
`v70_parametric_gain_collapse.py:132`, the **top decile of the WHOLE-DRIVE `|rate|` distribution** (hard
manoeuvres). Measured over **424 burst windows** the oscillation's own 18–22 Hz rate swing is
**p50 140 / p90 327**; raw max `|rate_c|` in-window is **p50 542**. The monotone window needs
**A_rk ≳ 1400** — **9.20%** of windows on scale A, **0.00%** on scale B.
Corroborating: grind #1 lives **97.8% (scale A) / 100% (scale B)** inside the flat `[0, 400]` rate
segment over **19,378 burst samples across 11 routes**, and re-pricing made Spearman **worse**
(−0.638 → −0.657).
⚠ **The two analysts disagreed and the orchestrator adjudicated — record the adjudication, not just the
verdict.** The outcome data (V70 excluded from V62's class at P < 5 × 10⁻⁵) is **sound**; but the
rateKey axis is the **bus angle rate converted by an assumed scale**, while `gp-0x6ac0` is the
**motor/resolver rate** — **a proxy that cannot settle the question either way.**
⇒ **the r26 explanation is preferred because it accounts for the same outcomes with no rateKey claim at
all** ([[accord-r24-r26-two-selectors-one-gate]]).

⇒ ★★★ **V71 IS BUILT AND UNFLASHED** — both lost confirmed fixes restored, the mode-10 surface reverted
to stock, and a probe that reads **the gain in force**
([[accord-both-confirmed-fixes-were-off-the-car]]). ⚠ **Known risk, disclosed: V62 is also the build
that introduced creep grind #2**; given r26 is now known live, that may have been r26's doubling rather
than r24's — **untested**.
🛑 **Deferred to V72, deliberately not stacked: FactorC/FactorE together, re-read against the RATCHET**
— **materially more compelling now**, because *engagement-required* + *hands-off-conditional* +
*Q ≈ 40* + *damping exactly zero below ~35 km/h* ⇒ **at creep the driver's hand is the only damping in
the system.**
🛑🛑 **`0xC6444` is STRUCK — a NULL BY CONSTRUCTION on any gateless build** (read only at `0x3AB5E`,
only when `lp != 0`, and `gp-0x683c` has 0 writers). Do not re-propose it.
★★ **And the build-independence buys one thing for V71:** `0x454FE` is a **genuinely untested** lever
for the ratchet — it was not on the car during any of the four measurements.

See [[accord-v69-flew-dose-response-non-monotone]], [[accord-v70-built-sign-probe]],
[[accord-aggregator-zero-gates-all-vacuous]], [[accord-state4-cadence-refuted-state-is-sticky]].
