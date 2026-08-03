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

With route **`2b` (V58, Kd = 1.00×, 227 s of highway** — a baseline two sessions had assumed did not
exist) brought in, the three-dose highway comparison is **NULL**: 40–49 Hz ratios **0.98 [0.71, 1.63]**
and **0.77 [0.56, 1.44]** against a split-half null of **[0.53, 1.86]**, no dose ordering, and **zero
burst windows at any dose across ~1,400 s**.

Identity settled by amplitude: creep grind #2 runs f0 43–45 Hz at prominence **48–1062×** and envelope
**2000–4000**; the highway population runs f0 45–47 Hz at prominence **~6×** and envelope **155–370**.
⇒ **Not grind #2** — the operator's *"maybe a grind #3 or #2.5"* stands.

What IS real at highway is **broadband**: 21 maneuvers vs 21 **matched** straight-line controls give
1–4 **1.21** · **6–9 2.78** · 10–16 **1.41** · 18–22 **1.86** · 24–28 **1.88** · 30–40 **1.58** ·
**40–49 2.13** (nulls ~[0.6, 1.5]) — 6–9 Hz rises *more* than 40–49, at levels ~50× below the creep
bursts. A maneuver loads the wheel and everything gets noisier.

⇒ **KEEP V67. No control-path change is supported.** Reproduce with
`analysis-2020accord/r47_orchestrator_checks.py`. See [[accord-r24-gain-is-a-speed-rate-surface]] and
[[accord-both-instruments-blind-above-50hz]]. Related: [[accord-gp6806-is-the-lkas-gate-validated-on-car]],
[[feedback-mean-and-tail-must-be-reported-together]], [[accord-v62-fixed-the-grinding]].
