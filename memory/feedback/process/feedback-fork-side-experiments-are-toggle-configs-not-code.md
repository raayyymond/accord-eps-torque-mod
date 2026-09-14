---
name: feedback-fork-side-experiments-are-toggle-configs-not-code
description: "The operator wants a fork-side experiment shipped as a plain Galaxy TOGGLE CONFIG (a .json toggle backup, a DELTA of the keys that change) whenever the existing params can express it — NOT a preset-applying param (rejected 2026-09-13, morning) and NOT a Testing Ground slot either (rejected 2026-09-13, evening: 'way too complicated for what should just be a toggle config file'). The Accord EPS torque mode is analysis-2020accord/reference/toggle-config_V293_torque_mode.json; the fork (Dom 4247cb09e) carries no torque-mode code."
metadata:
  type: feedback
---

# Fork-side experiments are toggle configs, not code (2026-09-13)

**Why:** the fork already had sliders for everything the torque-mode code branch changed
(`AccordRatePlantFF`, `SteerKP`, `AccordTorqueKi`, `SteerFriction`, `SteerLatAccel`), and Galaxy's toggle
backup/restore (`/api/toggles/restore`) applies exactly the keys present in a file and leaves the rest
alone. Code — a preset param, then a Testing Ground slot, a compiled `params_keys.h` change, a cereal
field — was three mechanisms in one day for what one small JSON does, and each had to be undone: fork
commit `3d1a3d0c7` was force-removed, `starpilotLateralState.epsTorqueMode @8` never shipped.

**How to apply:**
1. Ask whether the experiment is expressible with existing params. If yes, write a **delta** toggle config
   with `tools/make_galaxy_toggle_config.py` (Galaxy format; XOR key from the fork's `utilities.py`; the
   codec is positive-controlled against the operator's own 2026-09-10 backup) **and the revert delta**, both
   under `analysis-2020accord/reference/`. Never a full backup — a full one drags back every setting he has
   changed since (route 6f showed `SteerRatio` 16.88 and `LaneChangeSmoothing` 4 against the backup's
   16.33 / 6).
2. Attribute the drive from the wire, not from a code flag: `initData.params` (an `Accord*` key at its
   default is ABSENT — read absence as the default) and **`torqueState.p / torqueState.error` = `SteerKP`
   at 100 Hz** (the fork logs `error_with_lsf` and feeds the same number to the PID; r6f reads 0.9000
   exactly over 42,905 frames). `v293_flight_read.py` §0 does both, plus the f/D branch read.
3. Only when new code is genuinely needed does a Testing Ground slot come into it — and ask first.
4. Never commit his dirty working tree wholesale. `3d1a3d0c7` swept in the `ModelCurvatureLead` patch, an
   SR-map refit and two binary deletions he had not asked about; committing only the files the task
   touched, or asking, was the right call.

Related: [[feedback-openpilot-means-starpilot-dom-branch]],
[[accord-v293-torque-mode-built-the-model-independent-test]],
[[feedback-the-operator-runs-force-torque-controller-check-toggles-not-defaults]].
