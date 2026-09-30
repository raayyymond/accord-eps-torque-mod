# ADV-stability CRITERIA — adversary "stability" against the dynamics lens's A1017 (0xC63E8 1011 -> 1017)

Subagent `adv-stability`, 2026-09-30 11:10 PDT. **Written BEFORE any number of mine was computed.** I had read
the design report (V295-DESIGN-dynamics.md), its CRITERIA, the harness report, the census, the plant report and
the source of `v294_plant.py`, `v295_harness.py` (lane, plant, fork port, linear tools) and `d1_linear.py`.
Design / analysis only: nothing built, flashed, sent or committed. Scripts in `adv_stability/`.

My job is to make A1017 FAIL on dynamics. Default verdict REFUTED if I cannot reproduce its central numbers.

## Independence plan
- My OWN integer lane (written from the census listing pseudocode, not imported), checked tick-for-tick against the
  golden model (`lkas_fb_lag` + `lkas_rate_pid_tick`) — the harness's own spot check, one lane tick.
- My OWN linear loop: exact ZOH discretisation of the continuous plant (matrix exponential, NOT the harness's
  semi-implicit Euler), my own z-domain lane, rate former, transport delay, sensor age; closed-loop poles by
  eigenvalues AND margins by Nyquist on the same model (two methods).
- My OWN outer-loop linearisation written from the fork port's arithmetic (r1 path), compared to the harness's
  `outer_frf` on V294 as a cross-check, then used for the candidate.
- At least one NONLINEAR byte-exact replay: my own lane open-loop on r71b's recorded 0xE4 + 1 kHz rate (clamp,
  P clamp, int32, r26 statistics), and closed-loop scenario sims (my lane + my Karnopp plant + the harness ForkPort,
  spot-checked) for hard turns at 8-20 m/s and on-centre hunting.
- One harness retrodiction row re-run (spot check), then the harness `sweep_drive` over the WHOLE family (not the
  designer's 6 members) for the direction question (e).

## Central numbers I must reproduce (else REFUTED)
- C1 trim damping part |T/w|cos at 2 / 2.5 / 3 Hz: V294 1.61 / 1.83 / 1.91, A1017 2.17 / 2.19 / 2.11 (T per deg/s),
  within +/-5 %; damping-peak frequency 3.15 -> 2.32 Hz within +/-0.15 Hz.
- C2 |T/x| ratio A1017/V294 at 9 / 13 / 20 / 25 / 30 Hz within 0.98-1.03; |P/x|(20 Hz) 2.08 +/-2 %.
- C3 K_alpha 0.210 -> 0.390 T per deg/s^2 within +/-3 %; int32 worst-case a*s margin 2.17 +/-0.02; b_max(1017) 1232 +/-2.
- C4 r71b open-loop replay: max |r26| ~790, 0 fb-clamp binds, P binds fall (461 -> 345), max a*s margin ~10.4.

## FAIL (REFUTED) — any ONE of these fires
- **F-a (inner loop).** Over the family (nominal, J_lo, J_hi, J_hi2, J_0.3, b_lo, b_hi, tau0/6/9, ms_free, light_b,
  mode13, mode20, mode20_lo) x speeds 3.1/8/12/17/26.9 m/s x corners {J x0.5, 1, 1.5, 2.5} x {total loop delay x1,
  x1.5, x3} x {b x0.5, 1} (and light_b the same): A1017 is UNSTABLE where V294 is stable; OR A1017 inner GM < 3 or
  PM < 30 deg where V294 has GM >= 6; OR any closed-loop oscillatory pair below 8 Hz with zeta_A1017 < 0.9 x
  zeta_V294 AND zeta_A1017 < 0.3 (a lightly damped mode made lighter), counted on > 5 % of grid cells or on any
  identified-member cell at nominal delay.
- **F-b (the 20 Hz question).** A1017 |T/x| or |P/x| at any of 13-25 Hz > 1.10 x V294; OR on any stress member
  (the harness's three plus my own: 16 Hz zeta 0.02, 25 Hz zeta 0.03, r2 0.2-0.8, collocated) at any delay in
  {2, 3, 6, 9, 12} ms the 8-40 Hz closed-loop zeta under A1017 < 0.9 x V294's; OR the change in the trim's
  damping component at 13-25 Hz (A1017 - V294, any delay 0-18 ms) exceeds 5 % of V282's |T/w| at the same
  frequency, in the anti-damping direction (the scale anchor: V282 de-damped the on-car 20 Hz mode to zeta 0.016).
  Sanity requirement: my stress model must show V282 de-damping mode20 hard (else the stress model is too blunt
  to be a test, and I say so).
- **F-c (outer loop, fork law unchanged).** On any member / speed / corner of F-a's grid: outer GM_A1017 <
  0.9 x GM_V294, or Ms_A1017 > 1.1 x Ms_V294, or A1017 unstable where V294 is stable; OR a friction-relay describing-
  function crossing (limit-cycle prediction) exists for A1017 where none exists for V294, or its predicted amplitude
  rises > 25 %; OR in my nonlinear closed-loop scenarios (hard turns 8-20 m/s, on-centre straight 3-27 m/s, nominal /
  light_b / F_hi / J_hi2 / b_lo) a sustained 0.3-5 Hz oscillation appears under A1017 that V294 does not show, or its
  rms rises > 25 %.
- **F-d (nonlinear traps).** An int32 overflow reachable with |x| <= 12000 at any a*s / b*x / E*Kp / la*o product;
  OR the fb clamp binds on > 0.1 % of r71b engaged ticks; OR P-clamp binds rise > 25 % vs V294 on r71b; OR a restart
  pulse above the 616 T trim cap; OR in deterministic stick-slip scenarios (slow demand ramps, identified members,
  no sensor noise) the mean dwell-then-jump amplitude (deg) or the per-jump peak wheel acceleration rises > 25 % vs
  V294; OR a driver-induced fast steer (up to 500 deg/s, 3000 deg/s^2) produces an opposing lane torque under A1017
  above 2x V294's before the taper (reported regardless; FAIL only if it also exceeds the 616 T cap, which the
  arithmetic forbids — so this part is REPORT-ONLY unless the cap arithmetic is wrong).
- **F-e (direction, the claim itself).** Under `full` or `lp`, on ANY member of the full family, hard-turn 1.6-3 Hz
  or r_mid rises > 5 % vs V294 in the 5-10 or 15-22 m/s band (the designer claims favourable-or-within-+/-4 % on
  every member); OR tracking gain / turn-hold falls by > 0.02 in any band; OR the closed-form |alpha/cmd| at 1 Hz
  falls below x0.85 on an identified member or x0.75 on light_b (worse than the design discloses).

## SURVIVES_WITH_CHANGES
No F fires, but I find a stated number wrong by more than its tolerance in a non-central place, an undisclosed risk
(e.g. driver-override feel, stick-slip jump size), or a pre-registered sentence the drive cannot license. The
required changes are then written as edits to the design report / the risk statement, not as a different lever.

## SURVIVES
No F fires, C1-C4 reproduce, and I find nothing that needs changing on the page.

## What I will NOT claim
- Anything about the car above ~8 Hz beyond "the stress model says"; the stress members are not measurements.
- Symptoms. The operator scores those.
