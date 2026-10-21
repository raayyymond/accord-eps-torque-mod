---
name: accord-v300-flew-ad-b4-grind-is-hand-fight-long-is-brake-cycling-2026-10-20
description: "2026-10-20: V300 rev 2 FLEW (routes ad..b4, carFw A16C, fork accord-PTM 311c4cc0 from af on): grind-free holds; the low-speed hands-on 'grinding' = C1 the HAND FIGHT (setpoint at the error clip opposing the hand 33.6 % of hands-on creep frames; fork-side, O1 deletion); max angle is clip-bound < 6 m/s, VM only > 10 m/s, rate cap 250 binds 12–42 % > 150° — firmware PID/ICL levers do nothing, stay untouched; long 'ping-pong' = gas↔friction-brake cycling 2.7–9.9/min (Bosch brake on −0.12/off −0.02, no param) + aEgo-sign cost flip 125/375; 4-key Galaxy delta drafted, not deployed"
metadata:
  type: project
---

**State 2026-10-20 (E unless marked):** V300 rev 2 is on the car and flew 8 routes (`ad..b4`, Oct 18–20); the local
accord-PTM commits `9b7ef55826`/`311c4cc0b7` flew from af on (still not pushed). Reads: `docs/scoring/DRIVE-READ-accord-PTM-ad-b4-2026-10-20.md`,
`docs/review/LAT-RECORD-V298-TO-V300-AND-MAX-ANGLE-2026-10-20.md`, `analysis-2020accord/studies/long_control/README.md`.

- **Lat:** ring 0–0.38 %, F7 0, 18–22 Hz 0.77–1.51 (V282 3.4–3.9). Hands-on creep grinding ranks C1 = hand fight (setpoint parked at
  `ANGLE_ERROR_MAX_V` opposing the hand 33.6 % of frames; V299 19 %, V298+O1 0 %; 1.5–1.6× HF torsion-bar content at matched hand torque).
  V300's firmware reverts (notch arm, r24, damper banks) NOT supported on the wire. Fix is fork-side (gated hand-yield), B that it is what he feels.
- **Max angle:** 400° cap never binds; clip binds 47–60 % < 6 m/s; VM 3.589 binds only > 10 m/s; 250 deg/s cap binds 12–42 % > 150°. I sits at the
  4096 cap at 3–6 m/s ⇒ ICL/Ki/Kd/cap-hi inert for max angle. Lever = outward-only low-speed high-angle clip raise (+ rate cap), never symmetric.
- **Long:** no gap oscillation; brake requested 12–44 % of following at −0.12…−0.5 m/s² (coast would do) because `BOSCH_BRAKE_FORCE_ON = -0.12`
  / `RELEASE = -0.02` in honda/carcontroller.py (no param; fix = code deadband ≈ −0.35/−0.2). a-change cost flips 125↔375 on the sign of aEgo
  (JerkAcceleration 50 / JerkDeceleration 150), no hysteresis. tFollow from the profile JSON (1.25 s); AggressiveFollow*, LongitudinalActuatorDelay,
  LongSmoothSeconds INERT. Delta drafted: `studies/long_control/toggle-config_long-coast_2026-10-20.json` (Jerk Accel/Decel/SpeedDecrease/Danger → 100).
- ⚠ Route counter reuse: local `a6--78293a259e` is August; connect's a6..ac (upstream 823a5d5674 stubs) unfetched.

**How to apply:** never propose a firmware PID/ICL edit for max angle; test any fork clip/hand-yield change on the ad..b4 caches first (seconds);
read the next long drive with `long_pingpong_read.py` (gas↔brake switches/min). See [[accord-ptm-drive-notes-bar-angle-ceiling-saturation-2026-10-18]],
[[accord-v300-release-built-dom-release-fork-2026-10-15]], [[feedback-no-fork-override-in-the-angle-interface-rely-on-the-eps-fade]].
