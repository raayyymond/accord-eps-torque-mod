---
name: project-operator-starpilot-toggles-decoded-2026-09-03
description: The operator's live StarPilot (Dom) toggles, decoded 2026-09-03 from analysis-2020accord/reference/toggle-backup(2).json (XOR key "s8#pL3*Xj!aZ@dWq" + base64, per starpilot/system/the_galaxy/utilities.py; decoded copy toggle-backup(2).decoded.json, 492 keys). LATERAL: ForceTorqueController=True, ForceAutoTune=True, ForceAutoTuneOff=False -> the controller uses torqued's LIVE FILTERED latAccelFactor/friction (caps 1.182-2.196 / 0.106-0.318, tau 250-1250 s); SteerKP 0.6, SteerFriction 0.2120, SteerLatAccel 1.6893 all = stock (never moved); SteerDelay 0.2 (UseAutoSteerDelay False); HondaLateralPidKp/KiScale 0.33 (inert on the torque path); NudgelessLaneChange True, LaneChangeTime 0.4, LaneChangeSmoothing 6. The rlogs CANNOT show the toggle state -- ask for / read the backup file.
metadata:
  type: project
---

# The operator's StarPilot toggles (decoded 2026-09-03)

Source: `analysis-2020accord/reference/toggle-backup(2).json` (Galaxy toggle backup, created 2026-09-03T01:48Z). Decoder: base64 →
XOR with `"s8#pL3*Xj!aZ@dWq"` → JSON (`starpilot/system/the_galaxy/utilities.py::decode_parameters`). Decoded copy beside it.

| key | value | consequence |
|---|---|---|
| ForceTorqueController | True | torque controller (latcontrol_torque.py) |
| ForceAutoTune / ForceAutoTuneOff | True / False | controller takes torqued's live FILTERED LAF + friction (controlsd get_torque_control_params); SteerFriction/SteerLatAccel params are ignored until ForceAutoTune is turned off |
| SteerKP / SteerFriction / SteerLatAccel | 0.6 / 0.2120 / 1.6893 | all stock, never moved |
| SteerDelay / UseAutoSteerDelay | 0.2 / False | fixed lateral delay 0.2 s (stock 0.3) |
| HondaLateralPidKpScale / KiScale | 0.33 | inert (PID path only) |
| NudgelessLaneChange / LaneChangeTime / LaneChangeSmoothing / MinimumLaneChangeSpeed | True / 0.4 / 6 / 20 | the lane-change planner shape behind the 7-8 Hz ring's excitation |

**Why it matters:** the earlier assumption "ForceAutoTuneOff defaults true → params in use" was the branch default, not the operator's
state. On this car torqued's live values ARE in the loop, capped. Related: [[feedback-openpilot-means-starpilot-dom-branch]],
[[feedback-the-operator-runs-force-torque-controller-check-toggles-not-defaults]], [[accord-lanechange-ring-is-the-outer-loop-the-map-never-touches-the-eps-rate-feedback-gain]].
