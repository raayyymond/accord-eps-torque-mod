---
name: accord-backcalc-the-car-needs-friction-0025-and-laf-5-to-10-torqued-cannot-validate-on-the-modded-eps
description: 2026-09-03 back-calculation (studies/optune/BACKCALC-LAF-FRICTION-2026-09-02.md + STARPILOT-DOM-TORQUE-MATH-…). On r31/r32/r33 the controller ran the Accord DEFAULTS LAF 1.689 / friction 0.212 -- liveValid was 0 on every tick (orchestrator-verified: -(p+i+d+f)/output = 1.689 at p5/p50), because the modded EPS needs so little torque (engaged |torque| p90 0.06-0.12) that torqued's outer buckets (|x| 0.1-0.5) never fill; its "raw LAF 5.0" is a TLS through this build's central buckets plus a STALE cache (6653 points frozen) -- not a measurement. The CAR on V280 rev 2: deadband/hysteresis 0.013-0.030 tq (coulomb ~0), i.e. friction ~0.025 (0.212 is 7-10x too high = an 868-count kick, 1.8x the p90 command); lat-accel per torque 5 at the lane-change band, 9-10 steady -- the plant is INTEGRATOR-LIKE (|P| ~ 1/f, 0.1-1 Hz) because the EPS is a rate servo, so no single LAF makes the feedforward exact. Small-signal outer gain Gc = (kp+lsf)/LAF + friction/0.30 (friction 64 % at 25 m/s, LAF-independent): friction 0.025 -> 0.43x; + SteerLatAccel 2.53 (toggle max) -> 0.32x; the "0.08" figure was 3-4x the car. torqued's caps [1.18,2.196]/[0.106,0.318] are BOTH outside the car, so auto-tune can never get there: ForceAutoTune OFF and set the toggles.
metadata:
  type: reference
---

# Back-calculated StarPilot lateral tune for the modded EPS -- 2026-09-03

Reports: `analysis-2020accord/studies/optune/STARPILOT-DOM-TORQUE-MATH-2026-09-02.md` (Dom @3d4c625de, file:line),
`BACKCALC-LAF-FRICTION-2026-09-02.md` (+ `backcalc_extract.py`, `backcalc_laf_friction.py`). Toggles: [[project-operator-starpilot-toggles-decoded-2026-09-03]].

| build | route | lat-accel/torque IV slope (lag 0.2 s) | \|P\| 0.1/0.3/1.0 Hz | hysteresis half-width (tq) | controller used | torqued raw |
|---|---|---|---|---|---|---|
| stock | r97 | 1.13 | 1.64/1.10/0.62 | 0.116 | 2.25/0.177 (valid) | 2.42/0.181 |
| V112 | r22 | 6.0 | 5.96/2.68/1.17 | 0.054 | 2.34/0.148 (valid, old tree) | 5.35/0.123 |
| V278r3 | r31 (567 pts) | 6.9 | 6.17/3.82/1.49 | 0.028 | 1.689/0.212 (INVALID -> defaults) | 4.73/0.138 |
| V280r2 | r32 / r33 | 8.3 / 9.4 | 11.2/5.4/2.5 · 10.7/4.7/2.3 | 0.013 / 0.030 | 1.689/0.212 (INVALID) | 5.06/0.140 · 4.84/0.140 |

**The control law (EVIDENCE, source):** `T = [kp·e' + I + FF]/LAF + friction·sat((e' + 0.22·j_f)/0.30)`, e' = (setpoint − m)(1 + lsf/kp),
m from the STEERING ANGLE via the vehicle model (not the IMU); kp = SteerKP 0.6 flat, ki 0.15, kd 0; FRICTION_THRESHOLD 0.30 m/s². The friction
term is independent of LAF. Small-signal `Gc = (kp+lsf)/LAF + friction/0.30`: at 25 m/s 1.102 (friction 64 %).

| tune | Gc | ratio |
|---|---|---|
| live (defaults 1.689 / 0.212) | 1.102 | 1.00 |
| friction 0.08 (the earlier, asserted figure) | 0.662 | 0.60 |
| friction 0.025 (measured deadband) | 0.479 | 0.43 |
| LAF 2.53 (toggle max) + friction 0.025 | 0.347 | 0.32 |
| LAF 5 + friction 0.025 (needs params.toml, re-bases the toggle range) | 0.217 | 0.20 |

**Caveats:** all fits closed-loop (OLS biased low, IV consistent); above ~2 Hz the H1 estimate is the controller inverse (do not read a
7.5 Hz plant gain from it -- the wire G(f) in `studies/v280/LOWCMD-LOOPGAIN-…` A2 is the ring-band plant). That the Gc ratio equals the
|L(7.5 Hz)| ratio is BELIEF (plant term build-fixed). latAccelOffset −0.26..−0.47 on every route is road crown, frozen at 0 while invalid.
To apply: ForceAutoTune OFF (custom Steer* are ignored while it is on), then SteerFriction / SteerLatAccel.

Related: [[accord-lanechange-ring-is-the-outer-loop-the-map-never-touches-the-eps-rate-feedback-gain]],
[[accord-starpilot-torque-controller-the-033-multiplier-was-inert]] (its "raw 4.5-5.2 clipped to 2.196" is corrected here: nothing was applied),
[[accord-lkas-commands-rate-not-torque]].
