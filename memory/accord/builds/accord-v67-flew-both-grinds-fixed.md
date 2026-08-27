---
name: accord-v67-flew-both-grinds-fixed
description: V67's on-car result — grind #1 fixed, creep grind #2 eliminated, gate confirmed, and the highway symptom shows NO rate-lane dose response
metadata:
  type: project
---

★★★★ **V67 FLASHED AND DRIVEN 2026-08-02, route `47--3e0b6134c0` — the best build this kit has
measured.** 26 segments, **150,327 frames**, 1,495 s, an ordinary street → highway → street →
parking-lot commute (not a provoked route).

## The probe — decoded FIRST, per the V64 lesson
byte4 takes exactly two values `{0x87, 0xC7}`. **bit6 (`gp-0x6806`, the gate) == `carControl.latActive`
in 150,302/150,327 = 99.983%**; the 25 disagreements are single-frame transition edges. **bit5
(`gp-0x671d`, the masking risk that would pin the gain to 1024 *below* stock) = 0 in every frame**, as
is bit4 (`gp-0x671a`). ⇒ the arm was a **clean binary**: stock mode-10 LERP vs cal `0xC6446` = 5244.
⚠ bit4 is a **wasted rung** — V64 already closed the oscillation-detector approach.
✅ FLIGHT-CLEAN: `ST == 4` **0/150,327**, `ST == 3` = 12, zero `steerUnavailable`/`steerTempUnavailable`/
`canError`/`controlsMismatch`/`immediateDisable`/`steerSaturated`.

## ★★ Grind #1 fixed — and route 47 is the first route containing BOTH doses
The arm state is recorded per frame, so the dose contrast is **within-route** with no cross-route
confound. 18–22 Hz engaged creep, envelope p99, cell-stratified, episode-clustered:

| arm | vs Kd = 1.00× pool | vs Kd = 2.00× pool |
|---|---|---|
| **ENGAGED** (gate open) | **0.524 [0.337, 0.804]** | 1.183 [0.773, 1.617] |
| **DISENGAGED** (gate closed) | **1.055 [0.669, 1.354]** | — |

**Suppression in ONE arm only** — V67's conditional design, measured. It is also the first evidence ever
to separate V66 from V67 (their probe payloads cannot). Independent orchestrator pass: 0.55 [0.35, 0.65]
on a monotone four-point ladder **1.50 (Kd=0) / 1.00 / 0.55 (V67) / 0.39 (Kd=2)**, split-half null
[0.90, 1.12]. 🛑 28 engaged-creep windows / 11 episodes — strong, not proof. Confirm the `.rwd` name.

## ★★ Creep grind #2 ELIMINATED
40–49 Hz bursts (2.56 s window, envelope p99 > 500; the V62/V65 bursts ran **2000–4000**):

| dose | LKAS ON | LKAS OFF |
|---|---|---|
| Kd = 1.00× | 173 s / max 110.6 / **0** | 137 s / max 89.8 / **0** |
| Kd = 2.00× | 375 s / max **1830.7** / **18** | 140 s / max **1469.6** / **6** |
| **V67** | 22 s / max **83.5** / **0** | 91 s / max **48.8** / **0** |

🛑 **The two arms are NOT equally supported.** Manual expects 3.91 bursts ⇒ **P(0) = 0.020**, solid.
**Engaged expects only 1.04 ⇒ P(0) = 0.35 — UNRESOLVED**, matching the operator's own uncertainty.
**Closing it needs a parking lot, not a build.**

## 🛑🛑 The highway symptom is NOT the rate lane, and a confident prediction was withdrawn
The operator reported a resonance during highway lane changes, LKAS-engaged only. The arithmetic
predicted it: V67 delivers **2.44×** at highway — its maximum, 22% above V62's flat 2.00× — because a
scalar arm replaces a surface Honda rolls off with speed. **The data refuted it.**

With route **`2b` (V58, Kd = 1.00×, 227 s of highway** — a baseline three sessions had assumed did not
exist) brought in, the three-dose highway comparison is **NULL**: 40–49 Hz ratios **0.970
[0.787, 1.154]** and **0.938 [0.764, 1.184]** against a split-half null of **[0.73, 1.37]**;
manoeuvre-conditioned **0.999 [0.79, 1.31]** and **0.884 [0.67, 1.28]**. No dose ordering, and the
**corpus-maximum highway envelope (851.5 counts) is on V58/`r2b` at Kd = 1.00× — the STOCK lane.**
✅ **Positive control proves the estimator is live: 18–22 Hz IS suppressed at highway on the Kd = 2
arms**, manoeuvre-conditioned median **0.509 [0.39, 0.92]**, outside the null.
⚠ The one band outside the null, **10–16 Hz (1.55/1.50), is WHEEL ORDER 1** (order 0.996–0.999 on all
five routes) — tyre balance between drives months apart, not a dose effect.
🛑 My own first pass said *"max 341/155/267, zero windows above 500"* — **both halves wrong**; my
estimator ran 1.4–1.9× low by skipping the detrend + Hann taper `_grind2_lib.win_env` applies.

Identity settled by amplitude: creep grind #2 runs f0 43–45 Hz at prominence **48–1062×** and envelope
**2000–4000**; the highway population runs f0 45–47 Hz at prominence **~6×** and envelope **155–370**.
⇒ **Not grind #2** — the operator's *"maybe a grind #3 or #2.5"* stands.

What IS real at highway is **broadband**: 21 maneuvers vs 21 **matched** straight-line controls give
1–4 **1.21** · **6–9 2.78** · 10–16 **1.41** · 18–22 **1.86** · 24–28 **1.88** · 30–40 **1.58** ·
**40–49 2.13** (nulls ~[0.6, 1.5]) — 6–9 Hz rises *more* than 40–49, at levels ~50× below the creep
bursts. A maneuver loads the wheel and everything gets noisier.

## ✅✅ FOUR INSTRUMENTS AGREE, and the microphone null is quantitative
The comma's **microphone** (`soundPressure`) has **no ~50 Hz ceiling** — at the time, the only
measurement here that could speak to a >50 Hz event.
⚠ **CORRECTED 2026-08-03:** this line read *"computed from **16–48 kHz** audio at 10.000 Hz"*. It is one
RMS over 1600 samples of **16 kHz** PCM ⇒ **0–8000 Hz analysed**, published at 10.000 Hz. **The
correction weakens this section**: the 26.4 dB bandwidth-penalty argument that downgrades the mic null
depends on the band being 0–8 kHz, so anyone reading "16–48 kHz" will **over-weight** the null below.
★★ And it is no longer the only above-50 Hz instrument — `gp-0x671a`'s input is a band-pass **peaking at
~61 Hz**. See [[accord-both-instruments-blind-above-50hz]] and
[[accord-state671a-is-an-oscillation-detector]].
- **Positive control: it HEARS the creep grind #2** — burst vs quiet **4.14×** un-weighted p95,
  **5.88×** max, **+9.7 dB(A)**. The operator's *"like a subwoofer"* is confirmed acoustically.
- **Highway: nothing.** Un-weighted **1.067×** (my independent run 1.069 [0.960, 1.184], null
  [0.793, 1.264]); A-weighted **−0.59 dB(A)**. The low-frequency signature (un-weighted up,
  A-weighted flat) is **absent**.
- **Kd = 1.00 control kills it:** `r2b`/V58 gives **1.071× [0.824, 1.559]** vs `r47`/V67's **0.976×
  [0.814, 1.126]** — the *stock* rate lane shows a manoeuvre rise at least as large.
- **Sensitivity bound:** highway is 4.0× louder broadband, so a grind-#2-sized *absolute* excess would
  read **1.78×**. We measure ~1.0× ⇒ **the highway event is at most ~9% of grind #2's absolute
  acoustic amplitude.**
⚠ Bounds *absolute* amplitude only, and a narrow tone could be audible while barely moving a broadband
10 Hz level.

## 🛑 CORRECTION 2026-08-03 — the wheel-order-3 reading of this route is RETIRED
`MEMORY.md` carried, against this file, *"at highway 40–49 Hz is **wheel order 3**, per-window order
p50 **2.994**; anyone peak-finding there will find grind #2 and it will be a tyre."* **The order-3 half
is an estimator tautology and is superseded** — `order = f0·CIRC/v` returns ≈3.00 whenever a
band-limited argmax sits near the centre of 30–49.5 Hz at ~28 m/s. What replaces it:
**there is no line at all in 30–49.5 Hz at highway** on any route, build or channel (averaged-periodogram
prominence **1.23–3.83** vs the kit's **>4** criterion), while the 8–30 Hz positive control returns
wheel order 1 at prominence up to **79**. ⚠ **The 10–16 Hz order-1 reading above STANDS**, and so does
the general warning about mistaking a wheel order for a firmware effect.
The three-dose highway null recorded above also **survives an independent event-rate re-test**
(1.152 [0.496, 2.690], min detectable **1.61×**). See [[accord-highway-30-49hz-has-no-line]],
[[accord-highway-event-rate-null-with-power]], [[feedback-average-periodograms-before-peak-finding]].

⇒ **KEEP V67. No control-path change is supported.** Reproduce with
`analysis-2020accord/studies/sessions/r47/r47_orchestrator_checks.py` and `analysis-2020accord/studies/acoustic/r47_microphone_test.py`. See [[accord-r24-gain-is-a-speed-rate-surface]] and
[[accord-both-instruments-blind-above-50hz]]. Related: [[accord-gp6806-is-the-lkas-gate-validated-on-car]],
[[feedback-mean-and-tail-must-be-reported-together]], [[accord-v62-fixed-the-grinding]].
