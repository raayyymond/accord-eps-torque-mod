# PRE-REGISTRATION — reading V281 from ONE strong-turn drive

Written **2026-09-03, BEFORE the build is finished and before any drive.** Build: **V281 rev 3** = V280 rev 2 with the LKAS rate-PID Kp LERP table COMPLETELY FLAT at each record's index-0 value (operator's instruction 2026-09-03: "Kp completely flat, flattened to demand index 0's value"; live slot 7: Y 248,512,645,696,696 → 248×5, X untouched). Rev 2 (flat 341 from idx 24) and rev 1 (knot cap) are SUPERSEDED. Kd (128 flat), the ×6 line map, the feedback clamp 46080 and the CAN-427 delivered-torque tap are byte-identical to
V280 rev 2. Instruments on the wire: the tap (field `((b0&3)<<8)|b1`, T = ±(field&0x1ff)<<3), 0x18F rate and driver torque, 0x14A angle, 0xE4 command.
Scripts: `strongturn_r34.py` / `strongturn_r32_r33.py` (this folder; fixed detector threshold 103 wire; same edges), `highangle_stutter.py`,
`servo_at_reference.py`. **Do not move a threshold after the log lands.** StarPilot tune must be recorded from a toggle backup for the drive.

## Sizing behind it (`analysis-2020accord/studies/v280/KPFLAT-SIZING-2026-09-03.md`)
The 6–8 Hz strong-turn ripple ("a small oscillation on top of large steering commands", operator) is the inner rate loop's crossover limit
cycle: on the tap-identified high-angle plant (v ≤ 10 m/s, |angle| ≥ 30°) the as-is Kp 512–696 (idx 68–173) has GM 0.50–0.86× at 8–9 Hz;
K_crit ≈ 425 by the linear fit and, independently, by the describing function of the P clamp on the episode frames (K_eff = N·Kp, median 439).
Flat 248 = 0.58×K_crit: PM 27°, GM 2.0× on the loaded high-angle plant; it also clears the idx-26 episode class (K_eff 225) that 341 did not. Cost (chain DC arithmetic): P-rail error 64 deg/s (as-is 22.9); hands-light full-demand rate ≈ −8 %; stalled-wheel push −29/−39/−48/−41/−31/−13 % at idx 26/40/58/68/80/100, full stalled push from idx ≈ 120 (as-is ≈ 58). The highway band idx 2–12 is NOT inert this time: Kp 255–294 → 248 (−3…−16 %, inner loop only; the map and the outer loop untouched). creep20: the 20 Hz creep line is D-dominated and Kp barely moves it (BELIEF). Kd, output-lag pole and feedback-sum variants do NOT stabilise the as-is Kp.


## Predictions (V280 rev 2 measured on r32/r33/r34 → V281 predicted)

| statistic | frames | V280 (measured) | V281 predicted |
|---|---|---|---|
| (a) F7 episodes per 100 s of high-angle engaged time (fdom ≥ 6 Hz, |angle| ≥ 30°, fixed threshold 103) | high-angle engaged | 8.1 / 4.3 / 6.8 (pooled 6.3) | **≤ 2** |
| (b) tap T 6–8.5 Hz ripple ÷ level, in-episode / in idx ≥ 68 frames with the wheel moving | same | 0.42–0.99 (median 0.55) | **≤ 0.25 median** |
| (c) driver-torque 7 Hz ring in-episode (raw) | same | 1590 median | falls with (b) — BELIEF |
| (d) hands-light sustained full-demand rate p50 / p90 (idx = 240 ≥ 0.3 s, tq < 400 raw) | | 123–125 / 136–150 | ≥ 105 / ≥ 120 (−8 % predicted) |
| (e) stalled-wheel class (rate/reference < 0.5 at |angle| ≥ 30°) | | 0–1 per route | may return at idx 60–120 (a 15 deg/s stall pins P at idx ≥ 79 on V280 but only ≥ ~120 at Kp 248) — count them; ≥ 3 per route is the cost signal |
| (f) new ~9 Hz mode on rough road (8.5–10 Hz rate band, straight ≥ 8 m/s) | | baseline to be read from r34 | ≤ 2× r34 |
| (g) highway lane-change ring count and 4–8 Hz rate power at matched speed/cmd | ≥ 20 m/s | 0 of 2, 29 wire² (new tune) | unchanged or better (inner Kp −3…−16 % there; the outer loop is untouched) |
| (h) saturation P(|field| ≥ 309) | engaged | 0.000 | ≤ 0.01 |

## Decision rule
- (a) ≤ 2 AND (b) ≤ 0.25 AND (d) ≥ 105 → **the strong-turn ripple was the P-gain limit cycle and a flat Kp is the lever.** The operator scores the feel.
- **FAIL sentence:** if with Kp flat 248 F7 episodes still occur at ≥ 4 per 100 s with tap ripple/level ≥ 0.4 in idx ≥ 68 frames, the ripple is NOT the
  P-gain limit cycle — K_eff and the plant fit both mis-sized it — and **no further Kp cut is licensed**; next is the outer loop or a plant-side
  resonance (V268 damper records), not Kp.
- **Cost FAIL:** (d) p50 < 105 deg/s, or (e) ≥ 3 stalled episodes with the r31 stutter signature → revert to V280 rev 2, or go to a knee (rev 2's 341 from idx 24) + the
  feedback-filter pole companion (0xC63E8/EA 16.5 → 33 Hz, DC held; reader census NOT done — a build gate).
- (g) worse → the inner-loop Kp drop at idx 2–12 mattered on the highway (it should not: PM ~50° there); check the build diff before believing anything else.

## Risk stated before the drive
Less push on a loaded wheel at mid demand (−48 % at idx 58 in a stall, full stalled push only from idx ≈ 120); the r31-class stall stutter may reappear between idx 60 and 120 where P is now weaker; hands-light full-demand rate ≈ −8 %; a lightly damped ~7.6 Hz mode (Ms ≈ 2.9) remains on the model. Peak torque unchanged; nothing else on the car changes.

## What refutes this pre-registration
Any field reading of 313; (b) unchanged while (a) falls (episodes just went below the detector floor); (g) moving.
