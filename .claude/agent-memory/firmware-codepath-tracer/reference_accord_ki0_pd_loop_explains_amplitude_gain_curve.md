---
name: reference_accord_ki0_pd_loop_explains_amplitude_gain_curve
description: The rate PID in FUN_00028ea6 (setpoint = LERP[0xC9A88](|torque req|), a CONFIRMED-LINEAR map; error = 32*setpoint - lagged column rate) runs Ki=0 on V282 (0xC63E6=0, byte-verified), so it is PD-only. A PD loop against Coulomb friction settles with a fixed absolute steady-state rate error, which is a large fraction of a small setpoint and a small fraction of a large one -- this is the first-principles mechanism for a delivered/commanded gain that RISES with command amplitude, and it is independently confirmed on-car by the V283 Ki-50 A/B (Ki cured the low-end "stalled wheel" deadband but pushed the high end into oversteer, then was rejected for other reasons).
metadata:
  type: reference
---

# Ki=0 turns the LKAS rate PID into a friction-limited PD loop -- this is a firmware-side candidate for the amplitude-dependent delivered/commanded gain (2026-09-05, `lev-firmware` session for team-lead)

## The circuit (all EVIDENCE, GhidraMCP-traced fresh 2026-08-31/09-01, cross-checked by direct
V282-image byte reads this session -- see [[reference_accord_fun28ea6_lkas_rate_pid_full_decode]])

CAN `0xE4` -> `gp-0x69ae` (clamp x -4) -> envelope LERP[`0xCB844`] -> driver-override taper x rate
gain -> torque request, clamp +-240 -> **LERP[`0xC9A88`+4*selector](|req|) = RATE SETPOINT**
-> `error = 32*setpoint - lag(gp-0x6a56 column rate)` -> PID:
  - **I: `tp+0x73E6` = `0xC63E6` = 0** on stock, V112, AND **V282 (byte-verified this session,
    `rd16(0xC63E6)==0`)** -- the integrator contributes NOTHING.
  - **P**: `clamp((32*err * Kp[0xCB994][selector](|req|))>>8, +-15360)`.
  - **D**: on the ERROR (not setpoint): `clamp(((32*err - prev_err) * Kd[0xCB7D4][selector])>>3, +-10240)`.
  - sum = P + D (no I) x two further LERP gain stages -> second lag -> sign gate (DEAD when engaged,
    see [[reference-accord-deadband-signgate-eliminated-on-car]]) -> engagement ramp -> gain (891
    stock, **5346** V282, see [[accord-the-8x-gain-is-the-carrier]]) -> `gp-0x6b38`/`6b3c` ->
    arbitration -> aggregator -> governor -> EME shaper -> motor.

## The map is CONFIRMED LINEAR, twice, at the LIVE selector

Live selector = **7** ([[accord-the-live-variant-selector-is-7-tvca4-measured-on-the-wire]]).
`0xC9A88` pointer-table record **index 7** (`0xE502C`): X=[12,20,24,32,64,96,128,160,240],
Y=[52,86,103,138,275,413,550,688,1032] -- **Y/X = 4.30 at every knot**, byte-read directly from the
V282 image this session (matches `docs/specs/V282-NONSTOCK-DELTA-2026-09-04.md`'s independent read of
record 0, which happens to carry the same values). Stock is a SATURATING curve (Y/X falls 1.33->0.72,
per that census). **⇒ the reference the loop tracks is exactly proportional to the LKAS command; the
map introduces zero nonlinearity in V282.** Kp record 7 (`0xCB994`, `0xE43A8`... `0xE5378` family) is
flat: Y=[248,248,248,248] at every knot, byte-verified -- matches the "Kp flat 248" from V281 rev 3
onward ([[accord-v281r3-flew-the-7hz-cycle-is-gone-the-p-only-deadband-arrived-understeer-is-mostly-sr-12-5]]).

## The mechanism [BELIEF, first-principles, from the verified arithmetic above -- not yet isolated on
its own instrumented drive]

A PD-only loop (Ki=0) tracking a rate reference against a plant with Coulomb (static) friction settles
with err_ss such that `P(err_ss) approx = friction_torque` -- a roughly FIXED ABSOLUTE quantity in the
error domain, independent of setpoint amplitude. Delivered rate = setpoint - err_ss. At small setpoints
err_ss is a LARGE fraction (can stall the wheel entirely -- the "P-only deadband"); at large setpoints
it is a SMALL fraction (delivered/commanded -> 1, and can overshoot past 1 if the loop is underdamped
on the way up). This is the textbook shape of the measured "gain vs |setpoint| 0.687 -> 1.200" curve in
`docs/STATE.md`'s r39/r3a/r3c study.

## Independent, on-car confirmation that this axis is real and firmware-owned

**V283 = V282 + Ki 50 at `0xC63E6`** ([[accord-v283-flew-the-integrator-cured-the-deadband-and-was-rejected-for-oversteer]]):
adding the integrator back CURED the low-end deadband (stalled runs 7->1, dead fraction 0.34->0.048)
and MOVED the high end the other way (tight-curve achieved/asked 0.996->1.278, inner DC gain 0.36->0.76).
Rejected for a NEW residual (integrator doesn't clear at disengage, 139-383 counts 0.5-1.0s late) and on
the operator's principled objection (an integrator on rate is a double-integral on torque, which he does
not want). His frontier build reverted to V282 (Ki=0), i.e. **the low end is the accepted-cost side of a
deliberately-made trade**, not an unexamined defect.

## What this does NOT explain

The r39 study ([[reference to HANDOFF-2026-09-04-R39-...]], commit 6b8bb7a) found the ANGLE-correlated
over-steer at large steering angle to be a quasi-static EQUILIBRIUM fully explained by the openpilot SR
(steer-ratio) map, with SteerKP and (implicitly) the EPS Kd/Kp axis contributing nothing to that specific
delta ("nothing earns a flash" on the r39 forced-geometry Kd/Kp study). So: amplitude-vs-gain (this note)
and angle-vs-oversteer (r39) are two different decompositions of a correlated driving style, and the
current evidence assigns them to DIFFERENT owners -- amplitude/low-end to the firmware's Ki=0 choice,
angle/high-end to the openpilot SR map -- rather than to one root cause.

**How to apply:** before proposing ANY firmware fix for the amplitude-gain shortfall, read
[[accord-v283-flew-the-integrator-cured-the-deadband-and-was-rejected-for-oversteer]] first -- the
obvious fix (Ki) has already been flown, measured, and rejected for reasons that a re-dose will not fix
without also fixing the disengage-clear race at `0x2A164`.
