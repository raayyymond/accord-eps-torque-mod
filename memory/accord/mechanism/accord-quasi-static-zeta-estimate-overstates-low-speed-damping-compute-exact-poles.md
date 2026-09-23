---
name: accord-quasi-static-zeta-estimate-overstates-low-speed-damping-compute-exact-poles
description: "MEASURED 2026-09-23 (V294 redo): the design's quasi-static b_eff/(2√(k·J_eff)) formula OVERSTATED the acceleration trim's low-speed damping benefit by ~10 % — exact closed-loop poles give ζ× 0.89 at 5 m/s (was 1.02), crossing 1.0 at 8 m/s; a lagged virtual inertia is mostly INERTIA for modes below its own pole, so it makes a slow mode slower and less damped. Always compute the exact poles (4th-order continuous or 1 kHz discrete), never the perturbation estimate, for any in-EPS filter."
metadata:
  type: project
---

# The quasi-static ζ estimate overstates low-speed damping — compute exact poles (2026-09-23)

`v294_design.mode_analysis` evaluated b_eff/(2√(k·J_eff)) at an iterated frequency. On its own inputs the exact
4th-order roots of (J s² + b s + k)(s + ω_p)(s + ω_o) + K ω_p ω_o s² = 0 give ζ× **0.92 / 1.05 / 1.38 / 1.79 / 2.25**
at 5 / 8 / 12.5 / 19 / 26 m/s (map k: 0.89 / 1.00 / 1.29 / 1.43 / 1.73) against the estimate's 1.02 / 1.16 / 1.49 /
1.82 / 2.05. Reproduced independently by the orchestrator and by the auditor's exact 1 kHz discrete model.

**Why:** below ~8 m/s the wheel mode (0.5–1 Hz) sits UNDER the 2 Hz pole, where the trim is almost pure inertia
(J_eff/J ≈ 1.7); ζ falls as 1/√J_eff faster than the added damping grows. The trim never removes damping
(b_eff > b below the 180° crossing) and never destabilises (0 of 3,456 variants) — it makes a slow wheel
slower. The lever is the pole (0xC63E8): a 1018 (0.94 Hz) restores ×1.07 at 5 m/s at the cost of outer-loop
phase margin at 26 m/s (+34° → +18°, light world).

**How to apply:** for any in-EPS filter or trim, compute the exact closed-loop poles across the speed range
and report ζ AND the decay rate σ (a heavier mode can have the same ζ and a slower decay). BELIEF plant
(J 8e-5, light b, the hold map k); the ordering is robust across the grid.

Related: [[accord-v294-acceleration-trim-on-the-v293-torque-map-built]] · [[accord-filter-placement-decides-authority-not-the-filter]]
