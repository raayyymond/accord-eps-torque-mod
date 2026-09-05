---
name: accord-true-lat-accel-per-torque-is-3-3-and-laf-is-not-inert
description: The car's true lat-accel-per-torque measures 3.20/3.27/3.37 across three routes with three different assumed LAFs — and the "LAF is measurably inert" verdict was a conditioning artefact
metadata:
  type: project
---

⭐ **The Accord's true lateral-accel-per-torque is ≈3.3**, measured 2026-09-05 on r39 / r3c / r3a
(V282 firmware unchanged; `SteerLatAccel` 2.11 / 3.60 / 4.00).

| route | assumed LAF | n | median \|meas\|/\|ctrl\| | **LAF_true implied** |
|---|---|---|---|---|
| r39 | 2.11 | 19,514 | 1.515 | **3.20** |
| r3c | 3.60 | 14,427 | 0.909 | **3.27** |
| r3a | 4.00 | 13,155 | 0.841 | **3.37** |

Three assumed values spanning **1.9×**, implied truth agreeing to **5 %**. That invariance is the
check that the estimator measures the plant and not the assumption — it is why this beats the two
prior sizings (4.0 from the f/i balance and 9.5 from `car_fit`). It sits between the flown 2.11 and
torqued's own unused `latAccelFactorRaw` of 4.89–5.84. **EVIDENCE-grade for "≈3.2–3.4", not for a
third decimal.** Conditioned on `|ctrl| > 0.10` so the ratio is well-posed; frame-to-frame IQR is
wide and the cross-route agreement is what carries it.

🛑 **RETRACTION: "the LAF dose is measurably inert on the delivered surface" was an artefact of
conditioning on `|setpoint| > 0.5`**, which selects only the top amplitude decile. Unconditioned
whole-route road gain is **monotone in LAF**: 1.1215 [1.1031,1.1401] @ 2.11 → 1.1055 [1.0480,1.1580]
@ 3.6 → **1.0387** [0.9588,1.1140] @ 4.0. CIs still overlap, so it is a direction, not a resolved
effect — but the axis is **not** dead.

**The trade, priced by command amplitude** (road gain, gyro, SR-free):

| LAF | large-command (≥0.35 m/s²) | small-command (<0.10) |
|---|---|---|
| 2.11 | 1.126 [1.108,1.145] | **0.794** [0.700,0.888] |
| 3.60 | 1.117 [1.058,1.172] | 0.547 [0.411,0.699] |
| 4.00 | **1.048** [0.965,1.133] | 0.540 [0.415,0.659] |

⇒ **4.0 has overshot the plant's ≈3.3; 3.6 sits closer on both ends. Recommendation: 3.6.**
⚠ The small-command degradation is **perfectly confounded** with the `rdf43` → `tsfdo` driving-model
swap, which happened between r39 and the r3a/r3c pair. Cannot be attributed to LAF alone.

**Related:** the gain error is a function of **command amplitude, not speed** — gain vs speed is flat
(1.130 / 1.131 / 1.110 / 1.107 across 5–9 / 9–14 / 14–20 / 20–40 m/s) while gain vs |setpoint| rises
0.687 → 1.200, present in every speed column separately. Below ~0.10 m/s² the feedforward **points
the wrong way** (`f/setp` = −0.42/−0.46) because `ff = future_desired − roll·g·roll_offset_fade` and
`roll·g` ≈ 0.22–0.33 m/s² exceeds the whole bin, with the fade already at 1.0 above 2.5 m/s.

**Mechanism for why the integrator never removes it:** it cannot pre-charge against a
**direction-reversing** bias. Folded curve error −0.120 with **unfolded +0.014** on balanced L/R
counts; the unfolded integrator holds +0.19 (road crown / alignment) while the direction-reversing
part is never cancelled. See [[accord-the-residual-is-on-the-angle-axis-not-speed]] and
[[accord-backcalc-the-car-needs-friction-0025-and-laf-5-to-10-torqued-cannot-validate-on-the-modded-eps]].

**LAF is recoverable exactly per frame** as `-(p+i+d+f)/output` on unclipped engaged frames — the PID
runs in lateral-acceleration space and LAF divides once at `interfaces.py:329`. Measured
2.110000 / 4.000000 / 3.600000, sd ~3e-7. Use this to attribute the tune from the wire, never from
the label.
