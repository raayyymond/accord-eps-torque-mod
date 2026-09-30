# Adversary "stability" on V295 trim-ratio (b 0xC63EA 567 -> 964): FAIL criteria, written BEFORE computing

Subagent `adv-stability`, 2026-09-30 11:03 PDT. Written after reading only the candidate report
(`V295-DESIGN-trim-ratio.md`), its own criteria, and the harness report. No number of mine exists yet.
Anything added later is marked ADDED-LATER.

Default verdict: **REFUTED** unless the central numbers reproduce from my own code.

## R. Reproduction gate (any miss -> REFUTED, "cannot reproduce")
My own code (not `v295_harness.lane_ctf`, not the designer's scripts), cells read by me from the V294 image bytes:
- R1 |P/x| at 20 Hz: V294 2.079, b964 3.535, V282 44.90 -- each within 1 %.
- R2 K_alpha (low-frequency inertia of the trim) 0.210 -> 0.356 T per deg/s^2 within 3 %; HF |T/x| ratio 1.70 within 1 %.
- R3 byte-exact integer lane on r71b recorded (cmd, 0x18F rate): V294 march vs the 427 tap within ~4 counts rms
  (the harness reads 3.64); b964 march identical to V294 at x = 0 (FF identity).
- R4 int32 a*s margin 2.39 within 2 %; restart-pulse peaks 24/73/246/542 T within 5 %.
- R5 inner-loop worst Ms at delay x1.5 about 1.23 (within 0.05) and stress-mode zeta table within 0.005 --
  reproduced by my own linear closed-loop code on the same plant parameters (v294_plant family is data, used as data).

## D. Dynamics FAIL (any one -> REFUTED on dynamics)
- D1 (inner loop) any member x speed x delay (x1 ... x3 of the member's delay) x J (x0.5 ... x2.5) x b/Fc corner where
  V294 is stable and b964 is unstable; or b964 Ms > 2.0 anywhere V294 Ms <= 1.5; or a closed-loop pole with zeta < 0.15
  on b964 that is more than 0.02 LESS damped than the matching V294 pole.
- D2 (20 Hz vs the on-car record) at any EPS-internal delay in the plausible range (2 ... 15 ms total loop delay),
  the trim's contribution to a 13-25 Hz stress mode is ANTI-damping (Delta zeta vs open < -0.005) AND that anti-damping is
  larger on b964 than on V294 by more than the V294 -> open difference, i.e. the candidate moves a flexible mode toward
  V282's de-damped state. A mere phase flip with |Delta zeta| < 0.005 is a WARNING, reported, not a FAIL.
  Also FAIL if the candidate's |P/x| at 13-25 Hz exceeds 10 % of V282's at the same frequency anywhere (V282 is the only
  on-car ground truth for "grinds"; 3.54/44.9 = 7.9 % at 20 Hz is the claim).
- D3 (outer loop, fork law unchanged) any speed band / member where the b964 outer GM falls > 10 % below V294's, or below
  1.5, or outer Ms rises > 10 % above V294's; or a closed-loop replay (fork in the loop) shows a sustained oscillation
  (1-5 Hz line or on-centre hunting) on b964 that is > 1 dB above V294's on any member of {nominal, light_b, one
  stress-J corner}.
- D4 (nonlinear) the fb clamp C binds on > 1 % of ticks in a plausible hard-turn scenario (not just r71b); a relay / stick-
  slip limit cycle appears or grows > 20 % in amplitude on b964 vs V294; restart pulse > 615 T; any int32 margin < 2 on a
  bounded input set the firmware can actually see (|x| <= 12000).
- D5 (claims) the direction of the jerk claim (hard-turn 1.6-3 Hz wheel rate down at 5-10 m/s) does not hold on every member
  I test; or the low-speed worsening exceeds x1.20 on any member (the design's own worst is x1.19 / x1.12); or the
  cmd -> alpha metric moves the wrong way on any member.

## Outcomes
- SURVIVES: R1-R5 reproduce, no D fires.
- SURVIVES_WITH_CHANGES: R reproduces, no D fires, but a claim on the page is overstated or a margin statement is wrong in
  a way that must be corrected before the page goes to the operator (e.g. the damping sign at 13-25 Hz flips inside the
  plausible delay range but stays below 0.005 in zeta; a quoted number is off by more than the tolerance but not decision-
  bearing).
- REFUTED: any R miss, or any D fires.
