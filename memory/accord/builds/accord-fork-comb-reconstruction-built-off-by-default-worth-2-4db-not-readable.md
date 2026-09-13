---
name: accord-fork-comb-reconstruction-built-off-by-default-worth-2-4db-not-readable
description: "⭐⭐⭐⭐ FORK PATCH 2026-09-13 (uncommitted, raayyymond-StarPilot @ Dom): `ModelCurvatureLead` in drive_helpers.py — slope-continuous extrapolation of modelV2 desiredCurvature between 20 Hz frames, toggle `AccordCurvatureLead` default OFF, gain 0.75. Removes 63–66 % of the camera-locked leg but cuts the 0xE4 18–22 Hz content only −2.4 dB (r39) / −4.2 dB (r63) because the plan's share of the band is the limit; +0.9–2.5 dB at 5–18 Hz (lands on a 15–17 Hz ring); |H| ≥ 1 everywhere (no authority loss) but group delay vs the ideal is positive — a lead vs today's hold only below ~3.5 Hz. Design B (trajectory-shaped, 'lag-negative') FALSIFIED: orientationRate is a different head and a worse predictor than the action head's own last step."
metadata:
  node_type: memory
  type: project
---

Agent `combfix`, `docs/research/FORK-COMB-RECONSTRUCTION-2026-09-13.md`; scripts
`rlog-tools/studies/grind/fork_comb_reconstruction.py`, `fork_comb_designb_premise.py`. Patch files:
`selfdrive/controls/lib/drive_helpers.py` (class), `controlsd.py` (call before `limit_curvature_to_plan`/turn-hold/
lane-centering/`clip_curvature`; reset on `not latActive`), `starpilot/common/starpilot_variables.py`,
`common/params_keys.h` (`AccordCurvatureLead` "0", `AccordCurvatureLeadGain` "0.75"), safe_mode.py,
device_settings_layout.json (+ its test), new `selfdrive/controls/tests/test_model_curvature_lead.py`.
**Not committed; the operator's own uncommitted SR-map refit in latcontrol_vehicle_tunes.py was left untouched.**

- **Pre-registered "buys nothing" N1 TRIGGERED** (< 6 dB on the 0xE4 band); N2 triggered (the Δ² fold R
  0.197 → 0.173 only); camera-locked energy fraction of the command 0.648 → 0.387 (r39), 0.622 → 0.401 (r63)
  at gain 0.75 — the number that transfers; estimated ring benefit −18 % — exactly the ×1.22 the kit judged
  unreadable from one drive. **Ride it free on a drive spent on something else; never pre-register it as the
  thing under test.**
- **Method trap recorded:** the setpoint→wire transfer must be fitted from the quantity being perturbed
  (κ_ZOH·v²), not from the logged `desiredLateralAccel` (a +3…+7-tick delayed sample) — the wrong basis
  inverts the answer (+0.71 dB "worse").
- **Bounds:** output within [v[k]−|s[k]|, v[k]+|s[k]|] by construction; a frameId gap zeroes the slope; the
  first frame after reset reverts to the hold (an engage-jump extrapolation defect the test caught);
  clip_curvature binds LESS (0.0079 → 0.0036).
- **The fork's rate-plant FF** (sub-agent): assumes a memoryless torque→rate gain band-limited by a 0.10 s
  derivative smoother (1.59 Hz); an EPS inner-loop bandwidth drop 14 → 6 Hz is a ~2.4 % perturbation, no
  overshoot; only the integrator accumulates against a slower plant (AccordTorqueKi 0.30 → 0.15 is the
  conservative first-drive knob); `AccordRatePlantFF=False` is NOT conservative (×2.4–4.3 steady FF).
- 🛑 With V291's 9 Hz sensitivity bump, the patch's +1.5–1.9 dB at 5–10 Hz is a confound — keep the toggle
  OFF on the first V291 drive.

Related: [[accord-the-20hz-forcing-comb-is-real-and-half-the-rings-energy-is-locked-to-it]] ·
[[feedback-no-openpilot-side-modifications]] · [[accord-v291-c10-built-fb-pole-10hz-plus-r24-cut-loop-opening-class]]
