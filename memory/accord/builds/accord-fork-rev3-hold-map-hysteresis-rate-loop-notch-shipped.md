---
name: accord-fork-rev3-hold-map-hysteresis-rate-loop-notch-shipped
description: "FORK REV 3 SHIPPED 2026-09-14, NOT FLOWN (fork Dom e8e62f0e1 + analysis-2020accord/reference/toggle-config_V293_torque_mode_r3.json, 20 keys; revert = toggle-config_V293_torque_mode_r3_REVERT_to_r2.json). Five new Accord* params, defaults = the flight values, Safe Mode = all off: AccordHoldMap 1 (get_honda_accord_hold_torque: the measured saturating map k(v)*sat(v)*tanh(th/sat) replaces the linear hold term), AccordFrictionHyst 0.015 (hysteresis operator on the DESIRED angle, 3 deg band -- pure FF; SteerFriction -> 0.0), AccordRateLoopGain 0.0006 (the 100 Hz inner loop: Kv*(angle_des_rate - carState.steeringRateDeg through 0.03 s), tapered min(1, 12/v)), AccordErrorNotchQ 1.0 (speed-scheduled notch at get_honda_accord_mode_hz(v) on the P/I error), AccordRefFilter 0.12 (2 cascaded LPFs on the setpoint); AccordTorqueKi 0.3 -> 0.6; SteerKP 0.85 / LAF 14 / rate gain 0.5 / SteerDelay 0.2 unchanged. Simulated on the identified plant (v293r2_design.py): no limit cycle over b 0.0004-0.0008, J 6e-5-1e-4, delays x1.5, spring x0.7-1.4; 1 m/s^2 step overshoot 80-110 % -> 30-45 %; 5 s disturbance deflection halved; linear Ms 4-30 -> 1.9-2.6 at 15-28 m/s. Raising SteerKP to 1.5-2.0 FAILS at 22.8-28 m/s (Ms 5-18, rails with delays x1.5) -- do not. Order: fork, REBUILD PARAMS, config, restart. Tests NOT run on this host (openpilot runtime not importable); tune functions validated on a stubbed mirror."
metadata:
  type: project
---

# Fork rev 3 (2026-09-14): what shipped, what it should do, what would falsify it

**Falsifiers on the next drive (vs route 71):** the 2.34 Hz line on >20 m/s curves (rate +22.5 dB, 27 deg/s rms
in 0.5–3 Hz) below +6 dB / 8 deg/s; low-speed bursts 20.5/min → below r70's 18/min and no ramp-then-snap trace
of the t = 470 s type; tracking gain 0.83/0.93/0.99/1.12 → 0.95–1.05 in every band; turn-hold at 10–20 m/s 0.87
→ ≥ 0.95; dwells/min at 0.25 deg/s below r70's everywhere (the rev-2 ratchet trigger un-fired); integrator share
< 0.25. **Revert triggers:** a new 3–4 Hz line (the rate loop's own phase crossover) → `AccordRateLoopGain` 0.0003
or 0; late/darty turn-in → `AccordRefFilter` 0.08 or `SteerDelay` 0.3; over-holding into low-speed turns →
`AccordEpsSpringScale` 0.8 (scales the map); else the REVERT file.

**What rev 3 cannot do:** with a ~60 ms loop delay the rate loop damps the 2 Hz mode only ~×1.5–2 (cos(ωTd) ≈ 0.5
and it adds negative stiffness); fast transients will still ring it — the reference filter avoids exciting it.
The next rung if the ring remains is a firmware-side damper (−c·ω at 1 kHz, no delay), not a fork change.

**Why:** the operator asked for the plant to be modelled properly and for a 100 Hz inner loop if necessary; the
data (route 71) said the relay and the linear hold map were the causes and the loop delay bounds what feedback
can do. **How to apply:** score the drive with `v293_flight_read.py --config …r3.decoded.json` (it knows the five
keys and wants commit e8e62f0e1) and `v293r2_read.py`; read §7.1 dwells beside the 2.34 Hz line, not alone.
Related: [[accord-v293-rev2-flew-route71-2hz-limit-cycle-hold-map-wrong-twice]],
[[accord-steering-mode-2hz-inertia-and-loop-delay-budget]], [[feedback-fork-side-experiments-are-toggle-configs-not-code]].
