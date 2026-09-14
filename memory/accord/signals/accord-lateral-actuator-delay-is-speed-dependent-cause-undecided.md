---
name: accord-lateral-actuator-delay-is-speed-dependent-cause-undecided
description: "MEASURED 2026-09-13 (TAU-ACTUATOR-DELAY study, 6 routes): the closed outer loop's command→steering lag rises as speed falls — ≈0.15–0.18 s at 25+ m/s, ≈0.25 s at 3–8 m/s on the current tune; not a pure delay (lag pole 1.4–4.3 Hz = torque controller bandwidth + plant, NOT the EPS servo); the tune moved it 20–55 ms; V292 did not; small-signal is 30–50 ms slower (friction, not rate limiting); the fork's lateralDelayEstimate 0.248 is ~99 % seed; SteerDelay 0.2 is a FULL delay (vehicle part 0.0). WHETHER the speed dependence is a real physical delay is UNDECIDED (dead-time vs pole split unidentified); the operator is skeptical it is a controls issue and may implement a variable lateral/longitudinal delay if real. The V293 identification drive decides it: open-loop lane + no rate-plant FF ⇒ the 0xE4→rate pair measures the plant directly."
metadata: 
  node_type: memory
  type: reference
  originSessionId: b5512b02-211b-4c10-a2a4-db891c061b68
  modified: 2026-09-13T23:54:32.080Z
---

# The lateral actuator delay: speed-dependent, cause undecided (2026-09-13)

Study `rlog-tools/studies/grind/TAU-ACTUATOR-DELAY-2026-09-13.md` (§7 = the reading recorded at the operator's
request). Three candidate causes, none excluded: (1) the EPS firmware's speed-half fade (table D at 0xCBBC4,
axis unit OPEN; on-car ×0.42–0.69 delivered at 3–9 m/s) lowers plant gain at low speed — an apparent delay a
delay model would mis-attribute and a speed-dependent gain would fix; (2) rack Coulomb friction/deadband —
lag falls and gain rises with amplitude (physical, nonlinear; a delay cannot represent it); (3) the outer-loop
tune (LAF 6.0 cut P/I ×2.5; `low_speed_factor`; the friction compensator fed `error_with_lsf`). Evidence FOR
a physical variable dead time: r39's FOPDT fit (80 → 180 ms with falling speed); AGAINST: r6c's fit puts it
in the pole with dead time flat 160–180 ms — indistinguishable on this data.

**How to apply:** do not quote τ as one number — use `tau_eq(f)` at the crossover (§4.3); never use the
0xE4→0x18F pair on a rate-plant-FF build (anticausal); on the V293 drive re-run `tau_identify.py` with the
0xE4 pair enabled per speed band and amplitude tercile: flat dead time ⇒ servo/tune/fade; dead time growing
toward 0.18 s at creep ⇒ physical, implement the variable delay. Longitudinal: not measured this session.
Related: [[accord-v293-torque-mode-built-cleared-over-one-dissent]], [[project-starpilot-fork-lateral-state-2026-09-10]].
