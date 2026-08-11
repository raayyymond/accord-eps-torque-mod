---
name: reference_accord_vehicle_bus_clearance_and_aggregator_probe_reaim_2026-08-11
description: Two follow-on findings same day as the DBC clearance -- (1) openpilot-side clearance is NOT vehicle-side clearance; STEER_WHEEL_ANGLE on 0x14A is CANDIDATE-BLOCKED because no VSA-transmitted message carries any angle signal of its own (VSA likely reads it off the bus), mitigated but not cleared by VSA's own messages living on bus 0 while the EPS lives on bus 1; (2) the Kd cut was killed by a parallel PID trace (D damps 16-35Hz, only pumps 2-12Hz), re-aiming the telemetry probe at the aggregator's other 10 lanes -- r24/r26 and gp-0x6bbe (boost) are the only three genuinely unresolved for dissipative sign.
metadata:
  type: reference
---

# Vehicle-bus clearance is a different question from openpilot clearance, and the aggregator probe redirect

## Vehicle-bus (not just openpilot) clearance for the two candidate 16-bit channels

`STEER_WHEEL_ANGLE` (`0x14A` byte5-6) and 399's own `STEER_ANGLE_RATE` (`0x18F` byte2-3) were cleared
of OPENPILOT consumption ([[reference_accord_openpilot_dbc_repoint_clearance_2026-08-11]]) but that does
**not** establish they're safe from OTHER vehicle ECUs reading them off the physical bus.

**`STEER_WHEEL_ANGLE` — CANDIDATE-BLOCKED, real structural reason.** Grepped the FULL vehicle DBC (not
just EPS messages) for every VSA-transmitted message (`VSA_STATUS`/420, `WHEEL_SPEEDS`/464,
`VEHICLE_DYNAMICS`/490, `ROUGH_WHEEL_SPEED`/597, `STANDSTILL`/432) in full: **none carry an angle
signal of their own** (`VEHICLE_DYNAMICS` gives lat/long accel, no angle, no yaw rate). A stability
controller with no angle sensor of its own, on a bus where `0x14A` conspicuously carries TWO
distinctly-named angle fields (one openpilot-used, one not), is the classic shape of a signal fed to a
second consumer. **Mitigating, not exculpating**: ran `rlog-tools/_can_inventory.py` against an existing
local rlog (`analysis-2020accord/rlogs/...`) — **all of VSA's own messages are on bus 0; the EPS's
(`0x14A`/`0x18F`/`0x1AB`) are on bus 1.** Cross-bus consumption would need a gateway relay, unconfirmed
either way.

**399's own `STEER_ANGLE_RATE` — blocked too, weaker specific concern.** No comparably motivated
consumer found (VSA already has its own accel data). If this line is ever revisited, this is the more
promising of the two to de-risk further.

**Method, reproducible**: `ssh comma "grep -n 'BO_' <dbc>"` for the full message list, then `sed -n` to
pull each candidate consumer's full `SG_` list; `python rlog-tools/_can_inventory.py <existing rlog.zst>`
for bus assignment (no live capture, no flashing — genuinely read-only on data already on disk).

## The Kd cut died; the probe was re-aimed at the aggregator's other 10 lanes

A parallel PID trace extended `Re(Z)` to 35Hz: **D pumps ONLY 2-12Hz and DAMPS 16-35Hz** — cutting `Kd`
would cost real damping in the operator's own grinding bands (18-22/26-31Hz), so it's dead. The live
question became: net PID contribution is damping at 6-9Hz, but measured `Re(Z)` is strongly
anti-damped — where is the anti-damping, if not the PID?

Enumerated all 11 lanes of `FUN_0003aa2c` (citing the existing definitive table,
[[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]], not re-deriving) and filtered against
what's ALREADY established elsewhere this session: `gp-0x6bd0`(damper)/`gp-0x6b26`(friction)/`gp-0x6ad4`
(PID) are already known-sign or already-instrumented; `gp-0x6b62`/`FUN_00036682`/`gp-0x6ade` are ruled
out (slew-rate/attenuation/dead); `gp-0x6b4c` is externally commanded.

**⇒ Three lanes are genuinely unresolved: r24, r26 (0dB, unfiltered, 1kHz — the existing inventory
already flagged these as the top suspect once `gp-0x6ad4` was eliminated as a 21Hz carrier) and
`gp-0x6bbe`/boost, which the existing record ALREADY flags as *"the proportional-dominated-AND-
positive-feedback shape being hunted for"* (same-signed as raw torque sensor — reinforcing, not
opposing).** These three, not the D-term, are now the live suspects for the 6-9Hz anti-damping source.

**Allocation designed** (SPEC only): 427 = `\|gp-0x6bbe\|`, reclaimed b4 = `sign(gp-0x6bbe)`, two newly-
freed `0x14A` byte7 bits = `sign(r24)`/`sign(r26)`. Full detail:
`docs/SPEC-2026-08-11-telemetry-budget.md`.

Related: [[reference_accord_openpilot_dbc_repoint_clearance_2026-08-11]] (the openpilot-side half of the
clearance question this extends to the vehicle side).
