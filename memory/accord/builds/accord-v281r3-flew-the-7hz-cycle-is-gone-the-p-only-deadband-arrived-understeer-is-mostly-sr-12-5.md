---
name: accord-v281r3-flew-the-7hz-cycle-is-gone-the-p-only-deadband-arrived-understeer-is-mostly-sr-12-5
description: V281 rev 3 (Kp flat 248) FLEW 2026-09-03 as route r35 (…_00000035). The self-sustained 7 Hz strong-turn cycle is GONE (F7 0.0 per 100 s vs 6.8; 6-8.5 Hz rate power x0.19; tap ripple/level 0.18; driver ring -41 %); a damped 7 Hz ring at ~40 % remains with f0 (7.3-7.6) and bar/rate ratio (~10) UNCHANGED and the servo share down (0.82 -> 0.64) while r24's is not (1.27) -> the r24-pump reading passed, the pure-servo reading failed; no further Kp cut licensed. THE PREDICTED COST ARRIVED: seven 1-3 s stalled-wheel runs at idx 54-79 (wheel 9-22 deg/s vs ref 30-44, tap 0.62 of V280's), dead fraction x3-8 speed-matched -- the P-only deadband; the r31-type rail stutter did not return. Operator: "oversteering largely gone, prolific understeer, stuttering and rare attenuated grinding still present" + a pronounced grind at 23:48:21. The understeer is MOSTLY the SteerRatio 12.5 bias (model/pose 1.62 -> the loop settles at ~0.62 of the request; the controller's own error says OVER in every stall while the road says UNDER) with the Kp-248 deadband underneath; the oversteer's disappearance is the SR change, not the EPS. Tune on the drive: 12.5 / 2.11 / 0.03 / 0.6, ForceAutoTune off. Next: V283 = V282 + Ki 50 at 0xC63E6; SteerRatio back to 16.1.
metadata:
  type: reference
---

# V281 rev 3 flew: the 7 Hz cycle is gone, the P-only deadband arrived, the understeer is mostly SR 12.5 -- 2026-09-03

Studies: `rlog-tools/studies/osc-highangle/HIGHANGLE-r35-V281R3-2026-09-03.md` (strongturn35), `V281R3-READ-r35-2026-09-03.md` (v281read).
Prereg scorecard (r32/r33/r34/r35): (a) F7 8.1/4.3/6.8/**0.0** · (b') ripple/level 0.36/0.62/0.37/**0.18** · (d) 125/123/123/**136** (returning-dominated; winding 115) ·
(e) stall runs >= 1 s 0/0/0/**7** · (f) 8.5-10 Hz 1.1/0.97/0.69/**0.50** · (g) highway 4-8 Hz 93/121/25/**13** · (k) dead fraction 0.013/0.021/0.041/**0.114**.
Discriminators: f0 7.03/7.81/7.41/7.27; bar/rate 8.7/11.5/9.3/9.5; L_r24 1.27 at -27 deg (> 1 on 24/29 windows), L_servo 0.64; 0x14A b4.4 phase re rate -169 deg at f0
(R 0.95), +32/+62 at 15/20 Hz -> pumps at 7, damps at 20, as the deep analyses read.
Correction: the sizing's "Kp 696 at idx 26" was the wrong knot -- V280's Kp at idx 20-40 is 326-403 (cut 24-38 %), ~45 % at 40-80, 64 % at >= 136. The r34 backcalc
deadband 0.02-0.03 tq (82-123 counts of 0xE4 -> idx 5-7) is torqued's STEER_MIN, not the EPS.
Related: [[accord-r24-pumps-at-7hz-and-damps-at-20hz-the-same-cell-pulls-the-two-symptoms-opposite-ways]], [[accord-lanechange-ring-is-the-outer-loop-the-map-never-touches-the-eps-rate-feedback-gain]].
