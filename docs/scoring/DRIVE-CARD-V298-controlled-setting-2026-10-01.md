# DRIVE CARD — V298 first flight in a CONTROLLED SETTING (empty lot / quiet closed road) — 2026-10-01

Operator's decision 2026-10-01: fly V298 first in a controlled setting rather than confirm the polarity constant by a UDS read.
This card is the low-speed companion to `DRIVE-CARD-V296-angle-loop-2026-10-01.md` (which applies to V298 and remains the
card for the ≥ 8 m/s drive). **Nothing here licenses "fixed".** The flash is the operator's: name the file and the bus.

## 0. What this drive can and cannot decide
- CAN decide: the loop is LIVE and the right way round (the reader's structural regression and the INVERTED check), the
  engage/disengage/override/release behaviour is sane, the camera interlock and the fork's byte-2 field work (the lane runs
  at all), the 0.5 s timeout hold behaves, nothing grinds or hunts at the lowest authority the loop has.
- CANNOT decide: any goal criterion (tracking 0.95–1.05, turn-hold, the 20 Hz comparison) — those need ≥ 8 m/s bands.
- EXPECTED, not a failure: stick-slip / a dead zone of ~1.5° on small corrections below 8 m/s (declared miss M1; the
  loop's stiffness is ≈ 52 lane counts per degree at 3 m/s against ~76 counts of friction). Note it; it sizes the next step.

## 1. Before the key turns (same P1–P6 as the main card)
P1 EPS reports `39990-TVA,A16A` · P2 the car's own LKAS button OFF · P3 the fork on the angle-interface commit with
`AccordEpsAngleLoop` true (toggle config `studies/angle_loop/fork-config/toggle-config_V298_angle_loop.json`) · P4 no fork
angle integral · P5 `UseAutoSteerDelay` on · P6 the two re-headered revert `.rwd` files on the device and the REVERT toggle
config to hand. Confirm `pandaStates.safetyTxBlocked` stays 0 once engaged (the fork now packs the field on inactive frames).

## 2. Sequence (each step 10–20 s; hands hovering, not resting — a resting hand above ~300 wire counts freezes the integral)
1. Stationary, ignition on, openpilot up, NOT engaged: confirm no steering warning and the wheel is free (the lane must be
   inert: request 0).
2. Roll at 2–4 m/s on a straight, engage. Expect: a small hold at the current angle, no pull, no buzz. ABORT on any buzz,
   grind, oscillation, or pull.
3. Still engaged, let the path curve gently (a wide arc). Expect: the wheel follows with a visible lag and possibly a small
   step-and-hold texture (the declared low-speed miss). ABORT if the wheel overshoots past the arc and comes back, or
   oscillates at ~1–3 Hz.
4. Light hand: nudge the wheel 2–4° off the setpoint and hold 3 s, then let go. Expect: the wheel returns in under a
   second with no snap. ABORT on a lurch you would call a snap.
5. Firm hand: turn against it until openpilot disengages (your normal override). Expect: a clean release, the wheel
   stays where you put it. Re-engage.
6. Disengage with the stalk/brake while turning gently. Expect: the wheel is free within ~0.1–0.5 s (A2 + the 0.5 s
   ramp-out of the direction-2 arm), no steer-to-centre over 2 s (that was the pre-V298 behaviour on a 0 setpoint).
7. Only if 1–6 were clean and you have a safe stretch: 8–12 m/s straight and a gentle curve, 15–30 s each — that is the
   first band the main card can score.

## 3. Abort = disengage, stop, revert if any of
grinding/buzz; wheel oscillation or hunting you did not command; a snap on release; a pull toward straight or away from the
path; a jerk; any steering warning; `STEER_STATUS` 7 on 0x18F (the ±12000 angle bail latched — key cycle clears it; it means
the angle was invalid at engage, the interlock worked as designed).

## 4. After: hand over the route; the reader (`rlog-tools/studies/angle_loop/angle_loop_drive_read.py`) decides
LIVE / NOT LIVE / INVERTED, A2 skip timing, the freeze behaviour on your two holds, STEER_STATUS and 0x14A byte-4 census,
and reports breakaway/Coulomb friction per band — the number that sizes the low-speed friction term for the next build.
