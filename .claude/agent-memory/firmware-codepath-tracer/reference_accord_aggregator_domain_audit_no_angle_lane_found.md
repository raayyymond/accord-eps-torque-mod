---
name: reference_accord_aggregator_domain_audit_no_angle_lane_found
description: Per-lane INPUT DOMAIN audit of all 11 gp-0x6b98 aggregator summands for the operator's "is one of these secretly a return-to-center angle lane" hypothesis. No angle/angle-rate input found in return-centre (gp-0x6b62)'s producer chain after tracing 5 functions deep; the chain instead roots in the EPS assist-state machine (FUN_0003bd7c). gp-0x67f4 newly identified as the speed voter's own validity flag. No driver-torque-above-threshold override gate found among the 11 lanes either -- negative result, not exhaustive (only checked paths that surfaced while tracing the lanes).
metadata:
  type: reference
---

# Angle-domain / torque-threshold-override audit -- traced 2026-07-29, same session as the definitive lane table

Dispatched after the operator raised: this kit has traced torque lanes for ~50 builds and never mapped a
position/angle feedback path, and a Honda EPS must have return-to-center logic somewhere. Task: determine
each of the 11 summands' (see [[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]]) INPUT
DOMAIN from evidence, not the kit's inherited functional labels ("friction"/"boost"/"damping"/"return-
centre" are inferences from a prior session, not verified domains).

## Domain table (evidence-based, not inherited labels)

| Lane | Primary input | Domain | Evidence |
|---|---|---|---|
| gp-0x6ad4 (resonance/PID) | gp-0x4f60 | TORQUE | ERR=clamp(gp-0x4f60-bias); established, unchanged this session |
| gp-0x6bbe (boost) | gp-0x4f60 | TORQUE | primary EMA input, this session's fresh trace |
| gp-0x6bd0 (damping) | gp-0x4f60 primary, gp-0x6abe sign | TORQUE + MOTOR-RATE sign | same EMA, sign from filtered gp-0x4f50 |
| gp-0x6b26 (friction) | gp-0x4f50 (via gp-0x6c2c cascade) | MOTOR RATE | traced full 3-stage cascade this session, NOT gp-0x4f60 |
| gp-0x6b86 (magnitude) | gp-0x4f60 (peak-hold) | TORQUE | fresh decompile this session; only conditional zero is a saturation-rail guard (\|gp-0x4f60\|>=25600, the sensor's own full-scale rail), not a driver-effort threshold |
| gp-0x6b4c (LKAS) | CAN setpoint | COMMAND (forward path) | established, unchanged |
| r24 / r26 | gp-0x4f62 (d/dt of gp-0x4f60) | TORQUE-RATE | established, unchanged |
| gp-0x6ade (feedforward) | none (dead) | N/A | corroborated dead 2 ways this session |
| gp-0x6b62 (return-centre) | gp-0x6a5e, gp-0x6ac0, gp-0x67fe, gp-0x6bda/gp-0x6b5e | SPEED + MOTOR-RATE + STATE-TIMING | full producer trace, this session, see below |
| FUN_00036682 | gp-0x4f60 (closed loop) | TORQUE | established, unchanged |

**No angle or angle-rate input found in any of the 11 lanes.** This is the headline negative result for
the operator's hypothesis, and it rests on real evidence for the two lanes that most needed checking
(return-centre and the shared "tracking error" gp-0x6a10), not on silence.

## `gp-0x6b62` (return-centre, `FUN_00036388`) -- full producer trace, no angle found

Traced every one of its non-obvious inputs to a producer:
- `gp-0x6a5e` = voted SPEED (confirmed, [[reference_accord_gp6a5e_is_voted_vehicle_speed]]).
- `gp-0x6ac0` = motor resolver rate MAGNITUDE (confirmed elsewhere in this kit).
- `gp-0x67fe`/`gp-0x671a` = EPS assist-state / mode bytes.
- `gp-0x698a` = LKAS-mixer-sourced scale (command domain, not sensor).
- **`gp-0x6bda`** (return-centre's ceiling input, ALSO feeds `FUN_0003a382`/resonance's ceiling per
  [[reference_accord_gp6ad4_engagement_gate_and_36682_closed_loop_math]]): producer `FUN_00036022`:
  `gp-0x6bda = (gp-0x6bf0<1 ? gp-0x6bf0-gp-0x6bd6 : gp-0x6bd8-gp-0x6bf0) - sVar5` -- a MARGIN-TO-BAND-EDGE
  computation. Traced `gp-0x6bf0`'s writer: **`FUN_0003bd7c`** (`0x3c0cc`/`0x3c184`) -- this is the
  **already-established EPS assist state-machine function** ([[eps-gp67fe-trump-engaged-holding-substate]],
  the function that derives `gp-0x67fe` from `gp-0x6772`). So `gp-0x6bf0` is a state-machine-internal
  value (timer/counter/transition artifact tied to assist-state transitions), NOT a sensor reading.
  `gp-0x6bd6`/`gp-0x6bd8` (the band edges) are both written inside `FUN_00035d38`, part of the same small
  cluster (`FUN_00035ce6`/`FUN_00035d38`/`FUN_00035e00`/`FUN_00036022`/`FUN_000361c8`) -- did NOT fully
  decompile this cluster (budget), so the band edges' own root domain is not 100% closed, but given the
  producer chain rooting in the assist-state machine, working conclusion is this is a state-transition
  ramp/dwell margin, not a position signal. **Flagged OPEN, not asserted as fully certified.**
- **`gp-0x6b5e`** (return-centre's sign-branch selector, ALSO r26's "hard zero-force gate" input per
  [[reference-accord-r26-adaptive-lane-full-trace-and-sign]]): producer `FUN_000361c8`: LERP-
  interpolates against a table indexed by `gp-0x6bda` (the margin above), times cal `tp+0x73c2`, times
  polarity, sign-flipped on `gp-0x6bf0<1` -- a shaped/re-signed copy of the SAME margin quantity, not an
  independent sensor. So r26's gate and return-centre's branch selector are driven by the SAME
  state-transition-timing signal, not by torque or angle.

**Verdict: return-centre's producer chain, traced 5 functions deep, contains speed + motor-rate +
assist-state-timing inputs. No angle/angle-rate input found.**

## `gp-0x6a10` ("tracking error", read by boost/damping's Factor D index + 15 other functions) -- NOT closed

Producer `FUN_0003fc16`: `gp-0x6a10 = clamp_helpers(gp-0x69ca - slew_limited(gp-0x69e0 + offset))`
(the clamp helpers are the kit's already-known `FUN_00049a5a`/`FUN_00049a78` pair), gated on
`gp-0x67fe∈{1,2}` (assist up), else zeroed. **A sibling output of the SAME function, `gp-0x6a0a`, IS
torque-domain** (`(gp-0x4f60*10)/gp-0x4ebc`, clamped ±14 via `tp+0x7356`=`0xC7356`=14 freshly read) --
but `gp-0x6a10` itself does not derive from that torque path; it derives from `gp-0x69ca`/`gp-0x69e0`,
whose domain was NOT resolved this session (budget). Given the "difference of two signals with a rate
limit" shape and the "tracking error" label, this is a real, NOT-ruled-out candidate for an angle/angle-
rate tracking signal -- explicitly flagged for whoever owns the angle-CAN-packer anchor to cross-check,
rather than guessed at here.

## `gp-0x67f4` -- NEW: identified as the speed voter's own validity flag

Recurs as a gate in damping (Factor C), boost, friction, and `FUN_0003a382`. Writer traced to
`FUN_00041eec` (`0x4218a: st.b r12,-0x67f4,gp` / `0x421a0: st.b r0,-0x67f4,gp`) -- **the same voter
function already established as producing `gp-0x6a5e`/`gp-0x6a62`/`gp-0x6a64` (voted speed)**. So
`gp-0x67f4` = "voted speed reading is valid," not an angle signal, not a torque threshold. Every place
it gates a speed-indexed factor (e.g. damping's Factor C), the gated branch defaults to a DIFFERENT
fallback (often unity, not zero -- see [[reference_accord_gp6a5e_is_voted_vehicle_speed]]'s addendum) when
`gp-0x67f4==0`, i.e. when the voted speed can't be trusted.

## Driver-torque-above-threshold override gate -- NEGATIVE RESULT (not exhaustive)

Checked every gate surfaced while tracing the 11 lanes for "torque magnitude crosses a threshold -> lane
forced off." None found:
- `gp-0x67f4` = speed-validity (above), not torque.
- Boost's internal 4-state machine (`gp-0x682e`) is gated by a TIME/dwell counter
  (`gp-0x68c8 < cal 0xC74D1(=3760, fresh read)*10`) and assist-state, not a torque-magnitude compare.
- `gp-0x6ac0`-keyed gates (damping's compute-vs-skip, Factor E's LERP range) are MOTOR-RATE magnitude
  thresholds.
- r26's "hard zero-force gate" traces to the state-transition-timing cluster above, not torque.
- `gp-0x6b86`'s only conditional zero is a saturation-RAIL guard (`|gp-0x4f60|>=25600`, the sensor's own
  full-scale limit) -- an extreme edge case, not an ordinary "driver pushes noticeably" threshold.

**Did not find the described mechanism inside the 11 aggregator summands.** If it exists, most likely
sits upstream of the aggregator (arbitration `FUN_00028ea6`, the engage state machine, or the LKAS mixer
`FUN_00026c80`) -- none of those were in this session's scope. This is a real negative result over what
was traced, not a claim that no such gate exists anywhere in the firmware.

## Related
[[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]] -- the 11-lane table this audit classifies by domain.
[[reference_accord_gp6a5e_is_voted_vehicle_speed]] -- source of the speed identity this audit relies on, and where the gp-0x67f4/Factor-C-unity-not-zero addendum from this session now lives.
[[reference-accord-r26-adaptive-lane-full-trace-and-sign]] -- r26's zero-force gate, now traced one hop further to the state-transition-timing cluster.
[[eps-gp67fe-trump-engaged-holding-substate]] -- FUN_0003bd7c, now also identified as gp-0x6bf0's writer.
