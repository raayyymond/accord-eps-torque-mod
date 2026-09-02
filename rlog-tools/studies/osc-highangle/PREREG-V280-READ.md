# PRE-REGISTRATION — reading V280 from ONE drive

Written **2026-09-02, BEFORE the drive.** Build: V280 (map ×2 to idx 96, rising to ×6 at 240; `0xC62E6` = 46080; the
V278 rev 3 delivered-torque tap unchanged). Instruments already on the wire: CAN 427 = `(sign(T)<<9) | (|T|>>3)`,
field = `((b0&3)<<8)|b1`, T = `gp-0x6b38`; 0x18F rate (raw, 8 counts/deg/s) and signed driver torque; 0x14A angle;
0xE4 command. Scripts: `highangle_stutter.py`, `servo_at_reference.py` (this folder), `read_v278r3_route.py` and
`v280_map_profiles.py` (studies/v280). **Do not move a threshold after the log lands.**

## What V280 is for, in the operator's words
"Stuttering and oscillations at high angles far from center — the firmware's largest issue" and "not quite yet at 6x max
angular velocity relative to stock". Measured on rev 3: the stutter is a 7.0–7.6 Hz line, 10 episodes at |angle| ≥ 30°,
3–9 m/s, command railed; in 7 of 10 the wheel is STALLED at 10–20 deg/s against a 36–45 deg/s reference with P railing
~50 % of ticks, the 7 Hz rate ripple passing through P wherever it desaturates. Max sustained hands-light rate at full
demand: 42.3 deg/s p50 / 56.4 p90 against a 44.5 reference (1.9× the ×1 builds; 32 % of the ×6 target).

## Predictions (EVIDENCE = open-loop chain simulation on rev 3's own frames; BELIEF where marked)

| statistic | frames | rev 3 (measured) | V280 predicted |
|---|---|---|---|
| (i) T ripple/level: T 6–8.5 Hz amplitude ÷ \|T\| p50 | \|angle\| ≥ 30°, idx ≥ 200, runs ≥ 1 s | 0.55–0.70 (470–620 on 820–1010) | **≤ 0.25**, with \|T\| p50 ≥ 1000 |
| (ii) signed driver-torque 6–8.5 Hz amplitude (0x18F, raw) | same | 1470–1960 | falls with (i) — BELIEF, closed-loop |
| (iii) 7 Hz episodes per 100 s of high-angle engaged time | \|angle\| ≥ 30° | 10 / 102 s | fewer; a count ≥ 8/100 s is a FAIL |
| (iv) sustained full-demand hands-light rate p50 / p90 (deg/s) | idx = 240 ≥ 0.3 s, driver tq < 400 raw | 42.3 / 56.4 | p50 **> 56**; ceiling reference now 133.6 |
| (v) tap \|T\| p50 at idx = 240 | same | 539 | ≥ 700 (lane no longer braking at its reference) |
| (vi) low-command damping fraction P(sign(T) ≠ sign(raw rate)) | \|cmd\| < 1300, engaged | 0.40 | **unchanged, 0.35–0.45** (map identical there) |
| (vii) 2–4 Hz band excess, MID stratum | whole route | 0.76 | < 1.39 (corpus p95); V276 read 4.58 |
| (viii) saturation P(\|field\| ≥ 309) | engaged | 0.000 | ≤ 0.01 |

## The decision rule

- (i) ≤ 0.25 AND (iv) > 56 AND (vii) < 1.39 → **V280 did what it was built to do**: the map top was the lever for both
  complaints. The operator scores the symptoms; these are the instruments.
- (i) ≥ 0.45 or (ii) ≥ 1200 raw while \|T\| sits at its low-speed rail (~1000–1300) → the 7 Hz is D- or plant-fed; the map
  top is NOT the lever. Next: Kd (D is the remaining 7 Hz path, 16·ΔE), or the override cliff the ring's peaks graze.
- (iv) ≤ 56 with (v) unchanged → road load / the low-speed post-sum multiplier limits, not the map.
- (vii) ≥ 1.39 or a 3.9 Hz return on straight roads → the knee must move DOWN (idx 64), not the top: the low-command
  region is byte-identical to rev 3, so a return there means the clamp (46080 vs 15360) matters at low idx after all.
- (vi) outside 0.30–0.50 → the low-region invariance failed; read the map bytes and the clamp before anything else.

## Risk stated before the drive
On frames where the driver spins the wheel faster than the OLD reference (52–73 deg/s on rev 3's log, 3 episodes) the
lane BRAKED on rev 3 and will PUSH WITH the driver on V280 (brake fraction 0.63–0.83 → ~0.01, open-loop). Steady push at
high-angle full demand ~1.3× rev 3's. Peak torque unchanged (2481 at the rail). Override taper byte-stock; the 7 Hz
torque-sensor ring grazes the 2240 cliff on 3–12 % of stutter frames on rev 3 and is not addressed by this build.

## What refutes this pre-registration
Any field reading of 313; (vi) moving while the map bytes at idx ≤ 96 are byte-identical to rev 3 (the comparator model
is wrong); (i) rising while (v) rises (the ripple scales with the push — plant-fed, not P-fed).
