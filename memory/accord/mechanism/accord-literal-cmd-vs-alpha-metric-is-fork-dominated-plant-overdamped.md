---
name: accord-literal-cmd-vs-alpha-metric-is-fork-dominated-plant-overdamped
description: MEASURED 2026-09-30 on 7 routes — the operator's literal metric (LKAS command vs wheel angular acceleration) cannot score a firmware PID edit from ordinary driving (above 1 Hz it is the fork's P term reacting to the wheel; below 1 Hz the spring takes 55–95 % of the command); the V294 plant is OVERDAMPED + Coulomb (zeta_open 1.3–4), J≈0.2 T/(deg/s^2) at 0–5 m/s only; nothing above ~8 Hz identifiable; the 0x18F rate is rack-side (kappa 1.16 on centre) and the DBC factor is wrong (−0.1 vs −0.125)
metadata:
  type: project
---

**Measured 2026-09-30 (`analysis-2020accord/studies/v295/metric/`, `plant/`), EVIDENCE:**
- On every torque-map build (V293, V294) the literal "0xE4 command vs d²θ/dt²" metric above 1 Hz has M4 fired: the IV built on
  the planner disagrees with H1 at 13/24 coherent bins, the 1–8 Hz command is 0.92–0.96 R² the fork's P term, and the wheel's
  acceleration LEADS the command by 20–60 ms. Below ~1 Hz 55–95 % of the command variance is k·θ (holding angle against the
  spring) and 0–3 % is J·α. There is NO flat α = G·cmd band on any build. V282's rate servo is the positive control (H1 = IV).
- **The firmware-attributable read is a regression of the 427 tap on FF(cmd) + K·α (or on the byte-exact V294 FF and TRIM
  marches, c1/c2)** — V294's trim footprint |K| 0.193 (0.3–1 Hz) / 0.128 (1–3 Hz) T per deg/s² within 7° of design; V293 null ≤ 0.04.
- **The plant the 1 kHz loop acts on is OVERDAMPED and friction-dominated**: multiple-shooting output-error fit on r71b gives
  J ≈ 0.2 T counts/(deg/s²) [0.1–0.3] — identified ONLY at 0–5 m/s (= the prior 8e-5 u) — b 4.9/5.2/9.8/20.7/26.4 T/(deg/s),
  k 6.5/20/24/80/56 T/deg, Coulomb 76/13.5/15.8/7.9/4.4 T at 0-5/5-10/10-15/15-22/22+ m/s, ζ_open 1.3–4.0. The prior "light
  b 0.0006" world predicts held-out rate far worse above 10 m/s (R² −0.7 to −1.9). Above ~8 Hz nothing is identifiable from a
  50 Hz tap and weak HF excitation; a ~13 Hz ω→bar peak and the 20 Hz mode are stress cases, not measurements. The plant alone
  produces only 6–26 % of the drive's 1–3 Hz wheel motion — under this model the hard-turn band is mostly road/tyre disturbance.
- **κ:** the 0x18F rate is rack-side — d(angle)/dt ÷ x/8 = 1.16 on centre, 0.965 beyond 80°, on all 7 routes; per steering-wheel
  unit every trim figure is ×0.86 on centre. **The Accord DBC's 0x18F STEER_ANGLE_RATE factor −0.1 is WRONG for this EPS; the
  wire says −0.125** — decoding through the DBC scales every per-deg/s claim by 25 %. T per openpilot torque unit is 2619–2625.
- The kit's `|bar| < 400` hands-off mask is biased for any acceleration/jerk census (hands-off the torque sensor reads wheel
  inertia, ~0.5 counts per deg/s²); use steeringPressed.

**Why it matters:** "better track acceleration" cannot be scored on the literal metric without exogenous command content, and the
ceiling on the firmware loop is structural — |L| peaks ~0.3–0.6 at 2–3 Hz; |L| ≫ 1 needs a 13–20 Hz crossover, where V282
ground. **How to apply:** score firmware edits by the tap regression; treat the wheel as a damped spring with Coulomb friction,
not an inertia; design across the identified family AND the light-b prior; never quote sim dwells/min (noise-model-set).
Related: [[accord-v294-flew-r71b-v295-trim-gain-x1852-built]], [[accord-cereal-slot-137-collision-and-tap-polarity-plus]].
