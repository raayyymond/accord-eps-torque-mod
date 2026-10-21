# HANDOFF 2026-10-20 — V300 first flights read (routes ad..b4); long-control "ping-pong"; grind = the hand fight; max-angle levers

Previous: `HANDOFF-2026-10-17-v37a-reference-map.md`. No build cut, nothing flashed, nothing deployed, nothing pushed to the fork.

## 0. Where things stand
- **ON THE CAR: V300 rev 2** (`39990-TVA,A16C`) + fork `accord-PTM` `311c4cc0b7` (the two local 10-18 commits flew from route af on; ad/ae ran `83fa2e68c8`). EVIDENCE: carFw on all 8 routes. First V300 flights in the record.
- Routes fetched (comma connect → `analysis-2020accord/rlogs/`): `75604b0a432fdc89_0000{ad--5909e7772a, ae--74557c6b94, af--a4e305dfc5, b0--26515d54d1, b1--9038570540, b2--b41c6320f8, b3--7449208c37, b4--008b967c94}`. ⚠ Counter reuse: the local `a6--78293a259e` is an AUGUST route; connect's a6..ac (Oct 18 morning, upstream `823a5d5674`, mostly stubs) were not fetched.

## 1. Operator's notes this session (his words)
1. "long control feels off — following a static car it ping-pongs forwards and backwards; we should be coasting more → suggest updated long settings in Galaxy."
2. "lat control, what changed since V298? rare instances of grinding at low speed while manually turning the wheel while LKAS is engaged."
3. "firmware PID settings can be updated (Kp/Ki/Kd or max integral) → goal: increase the max turning angle WITHOUT affecting LKAS performance and the current lack of grinding."

## 2. Long control — `analysis-2020accord/studies/long_control/` (README, reader, config)
- **Code (E, verified by the orchestrator at 311c4cc0):** `starpilot_following.py` picks the MPC cost set by the SIGN of measured `aEgo`, no hysteresis; his Aggressive tune (personality 0) = JerkAcceleration 50 / JerkDeceleration 150 ⇒ a-change cost 125 ↔ 375, a 3× flip at every zero crossing (33–215 flips/min on the wire). tFollow comes from the profile JSON "close" preset (1.25 s; AggressiveFollow keys inert). LongitudinalActuatorDelay 0.3 and LongSmoothSeconds are inert (no caller / DeveloperUI off). `honda/carcontroller.py`: `BOSCH_BRAKE_FORCE_ON = -0.12`, `RELEASE = -0.02` — no coast band, no param.
- **Wire (E, 7 routes, ~21 min following, 68 s stopped-lead):** NO gap oscillation (2–8 s band 0.35–0.7 m; ego speed wobble < lead's); stopped-lead episodes are one monotone stop + brisk launch, no oscillation; what cycles is **gas ↔ friction brake, 2.7–9.9 /min, brake 12–44 % of following, pulses 4–7 s at only −0.12…−0.5 m/s²** — braking where coasting would do. Mode flipping and gas-factor drift NOT supported.
- **Deliverable:** `toggle-config_long-coast_2026-10-20.json` (+ `_REVERT`, `.decoded.json`): Aggressive Jerk Acceleration 50→100, Deceleration 150→100, SpeedDecrease 150→100, Danger 30→100 (= one symmetric cost set 250/5.5/100, same as his Standard). Import in Galaxy while parked/off-road. Optional in the profile editor: following close→medium, acceleration sport→standard.
- **The real coast fix is CODE** (not implemented): a brake deadband in the Bosch carcontroller (on ≈ −0.35, off ≈ −0.2, gas 0 between), optionally hysteresis on the aEgo-sign switch. Readout for the next drive: gas↔brake switches/min and brake duty from `long_pingpong_read.py <route>` (≤ 8 s).

## 3. Lat control — what changed since V298, and the grinding
- Delta (E, image diffs `studies/release/lat_record_2026_10_20/diff3.py`): V298→V299 67 B (freeze 512→1229, asymmetric A3, two-level cap 4096/6144); V299→V300 2110 B (telemetry, ×6 map, LIM, r24 gate/arm, biquad arm, Coulomb relay, damper banks, 0x454FE, 0x14120 all back to stock; Kp/Kd on all 28 records; DampAxis kept). Fork: O1 override deleted (Dom c6452361), clip a pure bound + turn lead gated + 250 deg/s (accord-PTM), saturation rule + bar normaliser (311c4cc0).
- **Grind-free holds (E):** ring 0–0.38 %, F7 0, no new 5–30 Hz line, 18–22 Hz 0.77–1.51 vs V282 3.4–3.9.
- **The hands-on low-speed grinding ranks as C1, the HAND FIGHT (E for the mechanism, B that it is what he feels):** hands-on creep < 6 m/s, the sent setpoint opposes the hand AT the error clip on 33.6 % of frames (V299 19 %, V298+O1 0 %); P-only lane demand ≤ 870–930 T (35–38 % of rail); at matched hand torque the at-clip windows carry 1.5–1.6× the 15–25 / 35–50 Hz torsion-bar content, wheel rate unchanged. V300's firmware reverts (55 Hz notch arm, r24, damper banks) are NOT supported (HF ratios ≤ V299's). C2 delayed-feedback refuted (setpoint follows the wheel at ~1 frame). Top-10 episode table in the drive read (b0 t690, ae t745, b3 t141, b2 t375–381, …) for the operator to match.
- **Implication:** the fix is fork-side (a hand-yield: fade/soft-release of the setpoint toward the wheel when the driver torque is high at low speed — the O1 class, gated, per the 2026-10-02 ruling "rely on the EPS hand fade" the firmware fade alone is not enough on the wire). Not implemented; needs the operator's ruling.

## 4. Max turning angle
- E: 400° cap never bound; VM 3.589 limit binds only > 10 m/s (21 % of short frames); < 6 m/s the fork error clip (`ANGLE_ERROR_MAX_V` 17/15.5/19.5/17°) binds 47–60 %, the loop itself 36–47 %; 6–10 m/s clip 44 % / loop 53 %; the 250 deg/s rate cap binds 12–42 % of |θ| > 150° frames. All high-angle turns were hands-on; hands-off ceiling untested.
- E (integer mirror vs r9d hold 1136 vs 1144 T): at 3–6 m/s I sits at the 4096 cap and P is clip-limited ⇒ **ICL, Ki, Kd, cap-hi do nothing for max angle**; cap-lo 5120 or Kp ×1.25 move it but with recorded costs (F4 overshoot 7.6° at 3 m/s; PM −10°) and V300 has no tap to observe a dose. **Firmware stays untouched.**
- **Fork lever:** raise the error clip only outward, low speed, high angle (×1.3 ⇒ ≈ 314° at 3 m/s, lock from 4 m/s, B ±30 %); a symmetric raise would raise C1. Second lever: the 250 deg/s rate cap at high angle. Both are constants in `opendbc/car/honda/values.py`; not implemented.

## 5. NEXT
1. Operator: import the long toggle config (parked), drive, read `long_pingpong_read.py`; if switches/min do not drop, the brake deadband code change.
2. Operator ruling on the hand-yield (C1) — then a fork change with the outward-only clip gate in the same commit, verified on the ad..b4 caches first (seconds).
3. Match the top-10 episodes to what he felt.
