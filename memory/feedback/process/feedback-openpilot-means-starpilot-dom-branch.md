---
name: feedback-openpilot-means-starpilot-dom-branch
description: Standing operator convention, 2026-09-02 -- "openpilot" means StarPilot, the NORMAL StarPilot on the Dom branch (checkout C:/Users/dudei/Desktop/Projects/openpilots/StarPilot), NOT the operator's own fork (openpilots/raayyymond-StarPilot). Applies until the operator says otherwise. Also: the operator is suspicious of tune recommendations (e.g. SteerFriction 0.212 -> 0.08) that are not back-calculated from route data + the controller's own math + torqued; derive, do not assert.
metadata:
  type: feedback
---

# "openpilot" = StarPilot, Dom branch -- 2026-09-02

**Why:** the car runs StarPilot (Dom branch), force-torque-controller on; earlier tune derivations shipped against the wrong
controller path and had to be retracted ([[feedback-the-operator-runs-force-torque-controller-check-toggles-not-defaults]]).

**How to apply:** read controller math, torqued and the Accord car params from `openpilots/StarPilot` on branch `Dom`
(verify with `git branch --show-current`), not from comma openpilot or the operator's fork. Any SteerFriction / latAccelFactor /
SteerKP recommendation must be back-calculated from the route data (cmd vs lateral accel), the controller's own equations and the
torqued estimator -- the operator explicitly distrusts a number that is only asserted.
