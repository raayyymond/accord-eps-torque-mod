---
name: accord-steering-mode-2hz-inertia-and-loop-delay-budget
description: "MEASURED 2026-09-14 on V293 torque mode (routes 70+71): the steering system has a lightly damped MODE J*th'' + b*th' + hold(th) = torque with J ~8e-5 torque/(deg/s^2) (band fits 7.2e-5..9.1e-5; limit-cycle point 9e-5..1e-4), damping ratio 0.2-0.35 (b ~0.0006 at the mode -- NOT the 0.0015-0.004 low-frequency 'viscous' b of the 0.5 Hz joint fit, a different quantity), frequency sqrt(k(v)/J)/2pi = 1.0 Hz at 4.5 m/s, 1.28 at 8, 1.67 at 12, 1.87 at 18.9, 2.04 at 22.8, 2.06 at 28. The static hold torque is 0.020 (static friction) + k(v)*sat(v)*tanh(th/sat(v)), k = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0134] at v = [2,4,6,8,10,12.5,15,17.5,20,23,28], sat = 19.3 + 546*exp(-v/3.01) deg (saturates ~0.30 torque above 55 deg at 10 m/s). Kinetic Coulomb 0.012-0.015. LOOP DELAY budget from route-71 timestamps: 0x14A -> carState 3 ms, controlsState -> 0xE4 13 ms, 0xE4 -> delivered torque 30-45 ms = ~50-60 ms; the rate-loop-alone phase passes -180 deg at 3.5-4 Hz, so a fork rate feedback must have |L| < 1 there (Kv 0.0006 -> 0.5; 0.0012 would cross). The delayed P + a relay reach -180 deg AT the mode -> the 2.34 Hz limit cycle."
metadata:
  type: reference
---

# The V293 steering mode, its inertia, and the loop-delay budget (2026-09-14) [EVIDENCE — `rlog-tools/studies/grind/_scratch/r71_delay_and_2nd_order.txt`, `r70r71_hold_joint_fit.txt`, `design_notch_linear.txt`]

**Use:** any feedback design on this plant must (a) keep |L| small where phase(P) + phase(delay) = −180°, which
sits AT the mode for a P loop with 60 ms delay (hence the notch at √(k/J)/2π in rev 3), and (b) bound rate
feedback by the 3.5–4 Hz phase crossover (Kv ≤ ~0.0008 torque per deg/s with a 0.03 s filter). The hold map is
the feedforward's hold term; the 0.020 intercept is the static friction, supplied by a hysteresis operator on the
desired angle, not by an error relay. The map above 15 m/s beyond 25°, at 12–15 m/s beyond 30°, and below 8 m/s
beyond 150° is EXTRAPOLATED (BELIEF). **Why:** three of the operator's symptoms on route 71 traced to these
numbers being absent from the fork's model. **How to apply:** `v293r2_loop.py` (linear margins) and
`v293r2_simlib.py` (the transcribed fork chain on this plant) carry them; re-identify J and ζ on the rev-3 drive
from the S5/S7 spectra before trusting a higher gain. Related: [[accord-v293-rev2-flew-route71-2hz-limit-cycle-hold-map-wrong-twice]],
[[accord-lateral-actuator-delay-is-speed-dependent-cause-undecided]], [[accord-v293-flew-route70-plant-is-a-spring-ratchet-measured]].
