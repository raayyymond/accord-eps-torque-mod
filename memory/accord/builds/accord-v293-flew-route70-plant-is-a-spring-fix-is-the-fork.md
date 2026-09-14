---
name: accord-v293-flew-route70-plant-is-a-spring-fix-is-the-fork
description: "V293 torque mode FLEW 2026-09-13 (route 75604b0a432fdc89_00000070--717f5a7866, 19 segs, 858 s engaged, fork Dom 4247cb09e, rev-1 toggle config confirmed in initData + Kp 0.3000 at 100 Hz). Identity HOLDS (tap vs image surface R² 0.986) — the EPS rate loop is dead on the wire. OPERATOR: no classic grinding or stuttering; NEW symptoms: ratchety snapping between angles, sometimes loose, sometimes oversteer, overshoot-then-correct on hard transients. Bands: 18–22 Hz ring present in 1.1 % of windows (9.8–20.9 % on every earlier build), amp ×0.43 (gate ≤ 0.40: a marginal miss, not a null); F7 0.00; tap ripple ×0.10; one REVERT trigger = the outer-loop 1.2–1.8 Hz line (fork tune). THE PLANT LEFT IS A SPRING + COULOMB FRICTION (torque → angle; hold 0.00086/0.0079/0.0113/0.0154 u/deg at 5/12.5/18.5/28.5 m/s (0.00055 at ≤4; the low-speed knots bounded by route 70's own hands-off data, ADV-REV2); F 0.010–0.012 u = SteerFriction's unit, ran 0.00); the fork's model was wrong twice (no friction, one LAF: measured 3.2 → 6.4 with speed, ×2.8 with amplitude); low-speed loop PM −11°/Ms 12 from the hard-coded low-speed factor (only SteerLatAccel divides it; in the plant-FF branch LAF scales P and I alone); the command-vs-f gap is +0.41 roll compensation (a persistent +2.4° estimated roll, untouched by toggles) plus a −0.07 learned offset (restored cache) — NOT a 0.30 stale offset; the ratchet MEASURED (dwell-then-jump 6–39× V282 at th 0.25, command 3× smoother). FIX SHIPPED = FORK: plant tables re-identified in CODE (Dom 8c4051ce6, G_V [550,271,246,205], K_V [0.30,1.00,2.15,2.77,3.15] — no single SpringScale fits the shape) + rev-2 toggle config (plant FF on, friction 0.011, LAF 14, Kp 0.85, Ki 0.30, offset off). Authority vs stock: peak ×6.17, every cell exactly ×6, median ×4.35 — unchanged. τ: not a variable transport delay."
metadata:
  type: project
---

# V293 flew (route 70): the plant is a spring with Coulomb friction; the fix is the fork, not the firmware
**[EVIDENCE — `rlog-tools/studies/grind/V293-FLIGHT-READ-r70-2026-09-13.txt`, `V293-PLANT-IDENT-2026-09-13.md`,
`docs/research/FORK-LATERAL-PATH-V293-2026-09-13.md`; BELIEF where marked]**

- **Attribution:** rev-1 config in `initData` key for key; `torqueState.p/error` = 0.3000 (77,863 frames); |427 tap|
  vs the image surface R² 0.986, resid 22 counts, sign(T) = +sign(cmd). 🛑 The scorer's `f/D ≥ 0.75` gate was BROKEN:
  `f = D_current − roll·g·fade − latAccelOffset·fade`, `desiredLateralAccel = setpoint` (0.30 s delayed reference) ⇒
  f/D = 1 − c/|D|. Scorer v2 gates on `f` vs `starpilotLateralState.feedforward` instead.
- **Operator's score, verbatim:** *"I did not experience any classic grinding or stuttering."* · *"steering felt
  ratchety, like the wheel did not move smoothly but only snapped between angles"* · *"sometimes loose … sometimes
  oversteer … on hard transients, it would overshoot then correct slightly"*. Bands = instrument; nothing "fixed".
- **Plant:** `u = a(v)·θ + b·θ' + F·sign θ' + u0`; IV torque→angle FLAT 0.15–1.2 Hz (an integrator falls at −1);
  no inertia below 1.5 Hz; τ_eq 0.19–0.34 s total, split unidentifiable, NOT a transport delay; SR/VM within 1 % of
  the gyro — not a cause. Loop as flown: crossover 0.034–0.25 Hz, PM 110–136° above 8 m/s, **PM −11° at 4.5 m/s**.
- **Ratchet:** dwells/min at th 0.25: 15.2/7.7/4.6/1.2 (r70) vs 0.39/0.64/0.44/0.20 (r6c); p90 dwell 1.3–2.6× longer;
  snap ≈ 2F/k(v); concentration 0.468 vs 0.325–0.351; three nulls on integrator stick-slip; the command exonerated.
  Mechanism: a friction band with nothing fast to linearise it (V282 had the 1 kHz rate servo + the fork's dither).
- **Loose** = loop stiffness only 1.1–1.5× the car's spring (wander is a null); **oversteer** = the lat-accel FF
  ×1.9–2.1 over above 15 m/s; **overshoot** = a fixed 0.4–0.5 m/s² excursion, not an under-damped linear loop.
- **Rev 2 (shipped):** fork `8c4051ce6` tables (hold ratio ~0.5/0.94/0.99/0.84 after the adversary's low-speed re-bound vs 3.20/1.52/1.54/1.29 for old ×3.3;
  replay residual 0.042/0.042/0.007/0.010) + `toggle-config_V293_torque_mode_r2.json`. Predicted Ms 1.78/≈1.9 at
  speed, PM 68°/Ms 2.16 at 4.5 m/s, step overshoot ÷3–4, hold stiffness ≈ as flown; every config fails at 3 m/s
  (the low-speed factor; direction only). DF check: no friction-relay cycle at 0.011 (first at 0.0235). ORDER:
  fork first, config second, restart. Falsifiers: tracking gain → 1.00, integrator share ≪ 0.38, dwells/min ≤ 3× r6c,
  concentration ≤ 0.40, 1–4 Hz prominence < 3 dB. Next rungs if not: 100 Hz fork rate feedback → firmware angle
  loop; never angular acceleration (electronic inertia) — `docs/research/DESIGN-NOTE-INNER-LOOP-QUANTITY-2026-09-13.md`.
- **Authority (operator's question):** V293 peak ×6.17 of stock's delivered peak (2461 vs 399 lane counts, stalled),
  every authority cell exactly ×6.000, surplus = flat Kp 120 against the unchanged stock P clamp, median ×4.35,
  min ×3.79; V282 was above ×6 everywhere. Nothing changed.
- **Dongle route counter RESET 2026-09-13** (6c–70 newer than a6; 00000070 reused) — key on `counter--hash`.

Related: `accord-v293-torque-mode-built-the-model-independent-test`, `accord-cereal-slot-137-collision-and-tap-polarity-plus`,
`feedback-fork-side-experiments-are-toggle-configs-not-code`, `accord-lateral-actuator-delay-speed-dependent`.
