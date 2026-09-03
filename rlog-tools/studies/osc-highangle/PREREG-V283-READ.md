# PRE-REGISTRATION — reading V283 (Ki 50 on the LKAS rate PID, on V282) from ONE drive

Written **2026-09-03, BEFORE the build is finished and before any drive.** V283 = V282 (Kp flat 248 + the inert r24 comparator tap) + `0xC63E6` Ki 0 → 50, one u16,
cal-only. Instruments: the 427 T tap (the integrator is in series with it), 0x14A byte 4 bits 6/5/4 (V282's r24 comparators and sign), 0x18F, 0x14A, 0xE4.
Scripts: `strongturn_r35.py`, `v281r3_read_r35.py` (+ `_supp`), `r24_deembed.py`, `ki_sizing.py`, `rlog-tools/studies/grind/v282_prereg_duty.py`. **Do not move a threshold
after the log lands.** Record the toggle backup. **Operator's decision: SteerRatio STAYS 12.5 for this drive** (one change at a time: Ki is the variable), LAF 2.11, friction 0.03, KP 0.6 — the same tune as r35, so every r35 statistic is a like-for-like baseline. The road-level understeer from the 12.5 bias (the loop settling at ~0.62 of the request) is therefore EXPECTED to persist and is not a V283 statistic; the EPS-side stalls/deadband (a), (b), (c) are.

## Why (from `V281R3-READ-r35-2026-09-03.md`, `7HZ-STRONG-TURN-DEEP-ANALYSIS-2026-09-03.md` §10)
V281 rev 3 stopped the self-sustained 7 Hz cycle (F7 0.0 per 100 s; a damped ring at ~40 % remains, r24-driven). Its predicted cost arrived: seven 1–3 s stalled-wheel
runs at idx 54–79 (wheel 9–22 deg/s vs a 30–44 reference, tap 778–868 counts = 0.62 of V280's), a P-only loop's deadband. The controller's own error said OVER in
every one of them while the road said UNDER, so openpilot cannot fix it from outside. Ki 50: corner 0.25 Hz at Kp 248; accumulates the held error until the wheel
breaks free; costs < 3° at 7 Hz, ~0 at 20 Hz; no new instrument needed. Ki 5 (V270, unflown) cannot break a stall.

## Predictions (r35 = V281 rev 3 baseline)
| statistic | frames | r35 | V283 predicted |
|---|---|---|---|
| (a) stalled runs ≥ 1 s (|angle| ≥ 30, idx 40–240, rate/ref < 0.5, hands-light) | strong turns | 7 runs / 14.8 s | **≤ 2 runs, none > 1.5 s** |
| (b) idx 40–80 wheel rate vs reference, hands-light strong turns | | 13.6 vs 30 deg/s (45 %) | **≥ 22 deg/s (≥ 70 %)** |
| (c) prereg (k) dead fraction, idx 20–40 & |rate| < 1 & |angle| > 10, speed-matched 8–12 m/s | | 0.336 | **≤ 0.10** (r34 0.041) |
| (d) stall-release overshoot: rate above the reference after a stall breaks | | — | ≤ +12 deg/s for ≤ 2 s (BELIEF, clamp-set) |
| (e) F7 episodes per 100 s (fixed-103) and tap 6–8.5 Hz ripple/level in idx ≥ 68 runs | | 0.0 · 0.18 | **unchanged: ≤ 2 · ≤ 0.25** (Ki does not touch the r24-dominated ring) |
| (f) 18–22 Hz creep bar amplitude (hands-off, 1–3 m/s) | | r35 to be read | unchanged (Ki 1 % of D at 20 Hz) |
| (g) integrator windup signature: tap |T| in a held stall rising toward 2240 within ~1–2 s (T 1238 → ~2240 at idx 58 in the model) | | — | present; its rise time gives Ki on the wire (reconstruct acc offline from rate + cmd, validate vs T) |
| (h) hands-on override at idx 40–84: tap |T| while the driver holds | | ≤ 1281 | rises to the 2462 cap within 0.5 s (= V280's behaviour, not more) |
| (i) V282's bit-6 duty over engaged hands-off creep | | — | 0.300 at the 5244 arm / 0.065 at 1024 (PREREG-V282-READ.md) |

## Decision rule
- (a) ≤ 2 AND (b) ≥ 70 % AND (e) unchanged → **Ki is the deadband companion; the pair (Kp flat + Ki) is the new base.**
- **FAIL:** (a) ≥ 5 or (b) < 55 % with (g) showing the integrator railing at 10240 without motion → the stall is not an error-integral problem (road load above the
  rail at this Kp) — Ki up does nothing; the lever is back to the map/Kp trade or the r24 gain (after V282's read).
- **Cost FAIL:** (d) > +20 deg/s or lasting > 3 s (a lurch the operator reports), or a new 0.2–1 Hz hunt on straights (the integrator fighting the 12.5/16.1 bias) →
  Ki 50 → 20, or revert.
- (e) worse → Ki's 3° at 7 Hz mattered; revert to V282.

## Risk stated before the drive
**Added from adversary B (model, BELIEF):** the integrator is blind to a hand (only the output fade overrides): holding against the lane at idx 40–84 drives T to 1540–2191 counts within 1–3 s (Ki 0: 256–537), any grip; release after a 3 s hold → +14–18 deg/s overshoot, settling in ~2 s (91 % of the cost-FAIL line). The accumulator clears 0.1–1.0 s AFTER a disengage (gated on the engagement ramp). Standstill windup: the accumulator rails in 0.4–1.9 s of a held command; the lane's structural ceiling is ~2500 counts (below the 3072 cap). Before any Ki above 50: re-trace the governor/COMP composition (a 5066 vs 5120 boost-floor margin rests on an old memory).
A stall-release lurch of ~10 deg/s for ~1.8 s (BELIEF); more push against a held hand at idx 40–84 (restores V280's, not more); the integrator holds its value while
engaged (resets only on disengage) — a long one-sided curve could leave a residual offset for ~4 s (corner 0.25 Hz) after it ends. Peak torque unchanged; the r24
lane and the 20 Hz creep line untouched.
