---
name: accord-v278r3-high-angle-stutter-is-p-desaturating-on-a-stalled-wheel
description: V278 rev 3 FLEW 2026-09-02 (route ..._00000031). The 3.9 Hz V276 mode is GONE (band excess 0.76 vs 4.58). Max sustained hands-light rate at full demand 42.3/56.4 deg/s = 0.95 of rev 3's 44.5 REFERENCE = 1.9x the x1-map builds = 32 % of the x6 target -- the reference limits, not torque (|T| 22 % of the rail, lane braking at its setpoint). The operator's "largest issue" -- stutter at |angle| >= 30 deg -- is a 7.0-7.6 Hz line in rate AND T (coh 1.00), absent on stock/V112: in 7 of 10 episodes the wheel is STALLED by road load at 10-20 deg/s against a 36-45 deg/s reference, E = +7k..+9k, P railed ~50 % of ticks, and the +-25 deg/s 7 Hz rate ripple (+-6000 in E) crosses P's 5650 linear window every cycle -> T 100 % modulated. A x6 top (E +25k..+34k) pins P: open-loop ripple/level 0.45 -> 0.18. V280 rev 2 = the map a STRAIGHT LINE to the x6 top (operator: linearize for openpilot), clamp 46080; damping fraction in V276's ringing frames 0.840 vs rev 3's 0.863 (slope 3.8 would hold 0.863).
metadata:
  type: reference
---

# Rev 3's high-angle stutter: P desaturating on a stalled wheel -- 2026-09-02 [EVIDENCE, open-loop sim on measured rate]

`rlog-tools/studies/osc-highangle/{HIGHANGLE-V278R3-2026-09-02.md, SERVO-AT-REFERENCE-2026-09-02.md, highangle_stutter.py,
servo_at_reference.py}`, `analysis-2020accord/studies/v280/V280-MAP-DESIGN-2026-09-02.md`.

| what | rev 3 measured | mechanism |
|---|---|---|
| 7 Hz episodes | 10 of 13, all \|angle\| >= 30 deg, 3-9 m/s, cmd railed (idx 237-238), planner flat | inside the EPS loop |
| driver torque during them | a 7 Hz RING, amplitude 1470-1960 raw, mean ~0 (column twist), peaks graze the 2240 cliff 3-12 % of frames | not a hand on the wheel -- a magnitude-of-a-ringing-sensor misread was caught |
| 7 of 10 episodes | rate 10-20 deg/s vs reference 36-45 (rate/ref 0.30-0.49), \|E\| +6.9k..+9.4k, P railed 56-67 % (chain sim on measured rate) | stalled wheel; ripple crosses P's linear window (\|E\| < 15360*256/696 = 5650). The tap's "saturation 0.000" is at the FULL-SPEED rail 2472, unreachable below 10 m/s (post-sum multiplier ~0.5: T_meas/T_sim 0.42-0.51; delivered rail ~1240-1680; T max 1704). At speed nothing saturated; in stalls P railed and T sat near its low-speed rail. |
| 3 of 10 | rate 52-73 deg/s ABOVE the reference (driver spinning in), fb clamp binds 33-65 %, lane BRAKES | V280 will push WITH the driver here instead (brake 0.6-0.8 -> 0.01) |
| stock r97 / V112 r22 at high angle | same stalled structure at 1/6 torque (stock); V112 at its reference with fb ripple 2.5 deg/s | no 7 Hz line on either |

**Counterfactuals on the same frames (open loop):** x6 top + 46080 -> P railed 0.97, T ripple/level 0.11; V280 (2@96->6)
-> 0.18; rev 3 -> 0.45; stock map -> 0.94 (stock WOULD reverse the lane at 7 Hz but its 417 cap never let it matter).
P-desaturation margin at a 15 deg/s stall: rev 3 6.7 deg/s of ripple; V280 96 deg/s (adv280b). Remaining 7 Hz path is D
(16*dE, map-independent). BELIEF: the closed loop follows. V276 is NOT evidence either way: it oscillated constantly and was
barely driven laterally engaged ([[feedback-engaged-means-lateral-engaged-and-v276-is-not-a-reference]]).

**Max rate:** the REFERENCE is the limiter. Every profile keeping x2 through idx >= 64 ties rev 3's damping fraction 0.863 in
V276's ringing frames (idx <= 58) -- the comparator gate is BLIND above 58, so x6 at the top has no on-car evidence and
rests on the stall arithmetic alone.
**V280 rev 2 (built):** the map a straight line Y = 4.3*idx to 1032 (rev 1's knee at 96 superseded on the operator's instruction
to linearize). Cost (chain sim, V280-LINEAR-MAP-2026-09-02.md): damping fraction in V276's ringing frames 0.840 vs rev 3's 0.863,
all of it at idx 32-58 where stock's concave map flattens; slope 3.8 (top 912) holds 0.863. Pre-registration: `PREREG-V280-READ.md`
(ripple/level <= 0.25, rate p50 > 56, band excess < 1.39, low-cmd damping 0.30-0.40; a 3.9 Hz return -> slope 3.8).

Related: [[accord-v278r3-torque-tap-reads-310-and-damping-is-sign-t-ne-sign-rate]], [[accord-the-8hz-mode-is-the-loop-not-the-plant]],
[[accord-ratchet-is-a-gain-driven-line]], [[accord-v276-mechanism-is-a-matter-of-degree]].
