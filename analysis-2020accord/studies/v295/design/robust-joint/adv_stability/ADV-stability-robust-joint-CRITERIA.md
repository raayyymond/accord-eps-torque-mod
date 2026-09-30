# ADV "stability" vs candidate A (robust-joint: 0xC63EA b 567 -> 1106) -- FAIL criteria, written BEFORE computing

Adversary subagent "stability", 2026-09-30. Written after reading the design report, the harness report, the census,
the plant module and the harness code; BEFORE running any number of my own. Design-only: nothing built, flashed, sent.

## Default
REFUTED unless I reproduce the candidate's central numbers with MY OWN code (tolerances below).

## R -- reproduction (my own integer lane + my own linear transfer; not rj_*.py, not score())
- R1 lane: my integer lane == golden model (lkas_fb_lag + lkas_rate_pid_tick) on >= 20,000 random ticks, V294 and A
  cells, 0 mismatches. One tick of the harness Lane == mine (spot check). FAIL -> REFUTED (cannot reproduce).
- R2 K_alpha A / V294 = 1106/567 = 1.951 +- 1 %; opposing torque T/omega at 2 / 5 / 20 Hz within 3 % of 3.41 / 3.44 / 1.26.
- R3 |P/x| at 20 Hz: V294 2.079, A 4.055, V282 44.90, each within 2 %.
- R4 restart pulse at 100 deg/s: A 283 +- 5 T (V294 144 +- 5); int32 margin a*s: A 2.08 +- 0.02 (V294 4.06).
- R5 one retrodiction row via the harness (V294 nominal lp 5-10 m/s tracking gain 0.865 +- 0.01).
Any of R2-R4 off by more than its tolerance -> the design's safety numbers are not reproducible -> REFUTED unless the
discrepancy is in the SAFE direction and I can say why.

## FAIL -- dynamics (any one fires = FAIL on that surface; REFUTED if it is a stability/safety surface)
- F-IN-1 inner loop (lane x plant, my own z/s model AND my own state-space eigenvalues) UNSTABLE with A on any member of:
  identified family, light_b, mode13/mode20/mode20_lo, my own two-mass scan 8-60 Hz, transport delay 0-18 ms
  (x1.5..x3 of the 6 ms corner, x9 of the 2 ms nominal), J x0.5..x2.5 on nominal AND light_b, b_lo/b_hi -> REFUTED.
- F-IN-2 on any such member where V294 has GM >= 3: A's GM < 2 (6 dB) or PM < 45 deg at a crossover, or Ms > 2.0 -> FAIL.
- F-IN-3 any closed-loop oscillatory pole below 60 Hz with zeta_A < 0.8 x min(zeta_V294, zeta_open) AND zeta_A < 0.10
  -> FAIL.  (Less damped than V294 by any amount is REPORTED, not failed, unless it meets this rule.)
- F-HF-1 (20 Hz vs the ON-CAR record) on plants CALIBRATED so that V282's lane gives zeta 0.012-0.022 at 18-22 Hz from
  zeta_open >= 0.05 (the measured anchor): A's zeta < 0.8 x zeta_open, or A's de-damping > 25 % of V282's de-damping
  on the same plant, at ANY transport delay 0-18 ms -> FAIL (it would put A a quarter of the way to the grinder).
- F-HF-2 the sign of A's damping contribution at 13-25 Hz flips negative within the delay range AND its magnitude there
  exceeds 10 % of V282's anti-damping at the same frequency -> FAIL.  (A flip at negligible magnitude is REPORTED.)
- F-OUT-1 outer loop (MY linearisation of the flown r1 LatControlTorque code, fork unchanged), any member x speed
  (1.5..30 m/s incl. the low-speed-factor region) x relay on/off: A's GM < 0.95 x min(GM_V294, 2) or A's Ms >
  max(1.1 x Ms_V294, 1.5) -> FAIL.  Relay describing function: check at the small-signal slope (worst) AND saturated.
- F-OUT-2 closed-loop nonlinear replay with the fork in the loop (harness ForkPort = real code, spot-checked), common
  random numbers for V294 vs A: a sustained 0.5-5 Hz oscillation (limit cycle) appears or grows > +3 dB vs V294 on any
  member (nominal, light_b, F_hi, F_lo, b_lo, J_hi, mode20_lo) in (i) the r71b hard-turn chunks at 8-20 m/s or
  (ii) a synthetic on-centre hold (straight, crown disturbance) or (iii) a synthetic hard-turn step at 8/12/16/20 m/s
  -> FAIL.
## FAIL -- nonlinear traps
- F-NL-1 C clamp binds on > 1 % of engaged ticks in my own replay of r71b (any member), or the P clamp binds more than
  V294 by > x1.5 in hard turns -> FAIL (the linear analysis would be void there).
- F-NL-2 circle criterion for the trim path's saturations (C clamp, P clamp: sector [0,1]): min Re L(jw) <= -1 on any
  member where the linear loop is stable -> REPORT as "absolute stability not guaranteed"; FAIL only if a nonlinear
  replay then shows a limit cycle.
- F-NL-3 restart pulse at 100 deg/s > 288 T (the designer's own cap) in MY computation -> FAIL.
- F-NL-4 stick-slip: synthetic slow-ramp and hold tests on nominal / F_hi / F_lo with identical noise (CRN) show A
  producing more stick-slip events or larger jump amplitudes than V294 by > 20 % -> FAIL on friction.
- F-NL-5 driver-torque taper: a hands-on loop through the taper (T -> bar -> taper -> T) whose gain the trim raises above
  0.5 -> FAIL.  (Estimated, BELIEF: the sim has no driver.)
## FAIL -- the direction claims (e)
- F-DIR-1 hard-turn 1.6-3 Hz wheel rate or 1-3 Hz wheel rate goes UP with A beyond the CRN noise floor (> x1.03) on any
  member x dist in my own mode-A replay or the harness mode-B replay with CRN -> the "DOWN everywhere" claim is
  REFUTED (the candidate may still be safe: SURVIVES_WITH_CHANGES).
- F-DIR-2 the cmd -> alpha flatness (my own closed form) goes DOWN with A on any member -> "goal metric up" REFUTED.
- F-DIR-3 tracking gain / turn-hold moves by > 0.01 in either direction -> the "loose complaints unchanged" claim is wrong.

## Verdict mapping (decided now)
- REFUTED: any R fails (not safe-direction explainable), or F-IN-1, F-IN-2, F-IN-3, F-HF-1, F-HF-2, F-OUT-1, F-OUT-2,
  F-NL-1, F-NL-3 fires.
- SURVIVES_WITH_CHANGES: only F-NL-2/4/5 reports, or F-DIR-* fires, or a claim in the design needs correcting.
- SURVIVES: nothing fires and every central number reproduces.
