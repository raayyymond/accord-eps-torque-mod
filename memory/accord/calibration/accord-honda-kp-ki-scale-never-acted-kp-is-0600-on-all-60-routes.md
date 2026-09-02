---
name: accord-honda-kp-ki-scale-never-acted-kp-is-0600-on-all-60-routes
description: MEASURED ON THE WIRE, all 60 routes, 531 segments: the torque controller's effective kp = torqueState.p/error is EXACTLY 0.600 at p5/p50/p95 and in every speed bin, across the 2x->4x->8x->6x EPS gain history and V57..V27x -- so the operator's HondaLateralPidKpScale/KiScale (1.0/0.5/0.33) NEVER reached the controller. The ONLY live lateral kp knob is the SteerKP slider (default 0.6, range 0.3-0.9, never moved); it overrides even the Accord's 0.8 constant every frame. ki DID change: 0.35 -> 0.15 by StarPilot commit 50e1c1d37 on 2026-08-18 (the day before V101 flew) -- a software update, not a toggle, and the likely source of "the car felt different".
metadata:
  type: reference
---

# The Honda Kp/Ki scale never acted; kp is 0.600 on every route -- 2026-09-02 [EVIDENCE, wire]

**Method** (`rlog-tools/studies/osc-2to4/kp_scale_history.py`, JSON alongside): all 60 routes in `analysis-2020accord/rlogs`,
531 segments, decoded with StarPilot's OWN cereal (copy at `rlog-tools/_scratch/spcereal/`; the kit's lacks `starpilotPlan`).
In StarPilot `pid.p = k_p * error` and `pid_log.error` is the same `error_with_lsf` handed to the PID, so **p/error IS k_p per
frame**, no model. 2.9 M active frames (|error| > 0.05), min 1078 per route.

| quantity | every route |
|---|---|
| `lateralControlState.which()` | `torqueState` (no `pidState` frame anywhere) |
| kp_eff p5 / p50 / p95 | **0.600 / 0.600 / 0.600**, flat in <5, 5-10, 10-20, >20 m/s |
| toggles (`starpilotPlan.starpilotToggles`) | `steerKp=[[0],[0.6]]`, `force_torque_controller=True`, `nnff=False`, honda scales 1.0 (the gate's DEFAULT -- the log cannot show the UI value) |
| `liveTorqueParameters.useParams` | 1.0; `latAccelFactorFiltered` 1.65-2.52 varies by route (the live estimator) |
| EPS fw string | `39990-TVA,A160` on every route (cannot distinguish builds) |

If the scale had acted, kp would read 0.6 / 0.3 / 0.2 on the 2x / 4x / 6x routes. **It did not move by one count.**

**What DID change: ki.** 0.350 on every route from commits 8640f0605 (07-24) .. 682b4b5c9 (08-12); **0.150 on every route from
d47be8092 (08-19) onward.** Boundary = commit 50e1c1d37 (2026-08-18) adding `HONDA_ACCORD_TORQUE_KP=0.8 / KI=0.15`
(`git merge-base --is-ancestor` confirms). A 2.3x integral cut, **the day before V101 (8x) flew** -- the real cause of any
"it felt different after I changed the scale" impression around then.

**Why kp stayed 0.6 even after that commit set 0.8:** `controlsd.py:444` runs `LaC.pid._k_p = starpilot_toggles.steerKp`
EVERY frame when lateralTuning != pid, and `steerKp = [[0],[SteerKP param, default KP=0.6]]`. All 15 commits in the logs carry
the override. It also flattens stock's low-speed `KP_INTERP` (kp would be 3.5 at 10 m/s stock) -- the speed-bin flatness
confirms the override is live. **The SteerKP slider (advanced lateral tuning, 0.3-0.9) is the ONLY live lateral kp knob.**

Data notes: device wall clock bogus on ~45 routes (use the StarPilot commit date as the lower bound); the dongle route counter
restarted once (two routes each named 0x1b and 0x24); two truncated segments skipped; route 0x74 has 0 active frames.

See [[accord-starpilot-torque-controller-the-033-multiplier-was-inert]] (the source reading this confirms) and
[[feedback-the-operator-runs-force-torque-controller-check-toggles-not-defaults]].
