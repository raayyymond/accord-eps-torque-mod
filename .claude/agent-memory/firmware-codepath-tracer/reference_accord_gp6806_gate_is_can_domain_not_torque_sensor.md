---
name: reference_accord_gp6806_gate_is_can_domain_not_torque_sensor
description: FUN_00052676 (producer of gp-0x6803/6804/6805, which the ramp SM gates gp-0x6806 from) contains NO reference to gp-0x4f60 (torque sensor) anywhere -- gp-0x1426 (zero CPU-instruction writers, narrows but does not close the open producer question) is read in the SAME breath as the CAN-derived LKAS setpoint decode, structurally CAN-command domain not torque-sensor domain. Also: cal 0xC64A3=1 is the single-byte arm for BOTH the arb's deadband AND its sign-guard relay together (never separately gated, never touched by any build V42-V47); 0xC61B8=102 sign-guard has no cal of its own.
metadata:
  type: reference
---

# `gp-0x6806`'s gate traced to CAN-command domain, not the torque sensor (2026-08-12, `lane-weights-6bf`)

Dispatched for team-lead's driver-override/ratchet hypothesis: does driver torque opposing the LKAS
command drive `gp-0x6806` (hence the arb's deadband+sign-guard relay, see
[[reference-accord-deadband-signgate-eliminated-on-car]]) to 0?

## [EVIDENCE, fresh decompile] `FUN_00052676` — no torque-sensor input anywhere

Producer of `gp-0x6803`(direction)/`gp-0x6804`/`gp-0x6805`(request), which
[[reference_accord_fun28ea6_ramp_statemachine_gp6806_gp69b0_decoded]]'s ramp SM consumes to gate
`gp-0x6806`. Full decompile:
```c
// normal path (param_1==0, no fault bit):
sVar1 = FUN_00021724();
gp-0x69ae = clamp(sVar1 * -4, ±0x4000);     // established LKAS setpoint, CAN 0xE4-sourced
bVar4 = *(byte *)(gp-0x1426);                // <<< everything below derives from this byte
gp-0x6803 = bits[3:2] of bVar4;
gp-0x6804 = bit[6] of bVar4;
gp-0x6805 = bit[7] of bVar4;
```
`gp-0x4f60` (torque sensor) does not appear anywhere in this function. `search_instructions("1426")`
whole-image: 2 hits, both READS inside this function, **zero writers** (confirms the prior session's
finding; narrows but does not close the producer question — `gp-0x1426` is read in the same breath as
the CAN-derived setpoint decode, structurally consistent with a second byte of the same openpilot
steer-command message, or a DMA-populated CAN RX field bypassing normal `st.b`/`st.h` instructions — the
zero-writers result is consistent with either, neither independently proven this session).

**Consequence**: no firmware-internal path exists from the torque sensor to `gp-0x6803`/`gp-0x6805`/hence
`gp-0x6806`. If driver override correlates with this gate closing, the causal chain runs through
openpilot's own CAN behavior (its own driver-override detection reducing/cancelling the steer request),
not through anything inside this EPS firmware — a claim about openpilot, not verifiable from `code.bin`.

## [EVIDENCE, fresh `read_memory` + grep] `0xC64A3`=1, single-byte arm for BOTH halves

`read_memory(0xC64A3)` on `code.bin` = **1**. `builds/v18_v49/build_v42_tva.py` through `builds/v18_v49/build_v47_tva.py`: "pre-gain
deadband enable — deliberately LEFT ON," never edited on any build found. Confirmed from the decompiled
structure (`reference-accord-deadband-signgate-eliminated-on-car`): both the ±102 deadband AND the
sign-guard relay sit inside the SAME `if (cal_0xC64A3==1 && gp-0x6806==0)` — one byte arms both halves
together; there is no way to disable only the sign-guard via cal.

`0xC61B8`=102 across every build checked, V42-V86 — "deliberately LEFT STOCK." V84's own comment tags it
"ELIMINATED for the vibration [hypothesis]" — that elimination is against ORDINARY engaged driving
(route 24/V56, `gp-0x6806` measured 96.26% bypassed, 0.011 transitions/s), never measured in the
override regime specifically. **The sign-guard itself has no cal of its own** — hard-coded comparator
arithmetic once inside the shared-arm block; `0xC61B8` only sizes the deadband window, not the
sign-guard's reach.

## The motor path, re-confirmed (not re-derived, cross-checked against 2 prior sessions)
```
gp-0x6b30 (post deadband/sign-guard) -> gain x polarity (0xC646C) -> gp-0x6b3c (arb output)
  -> FUN_0002b422 (limit_and_pack) -> FUN_00025c32 (distribute_clamp) -> mixer
  -> gp-0x6b4c -> aggregator (FUN_0003aa2c) -> gp-0x6b98 -> motor
```
Matches [[reference_accord_patha_arb_is_live_not_inert_correction]] and
[[reference-accord-deadband-signgate-eliminated-on-car]] exactly.

## Open thread, not chased this session
`FUN_00021724()` is called immediately before the `gp-0x1426` read in `FUN_00052676` — a plausible site
for where the CAN byte actually lands, not decompiled this session.

## Related
[[reference_accord_fun28ea6_ramp_statemachine_gp6806_gp69b0_decoded]] — the ramp SM this producer feeds.
[[reference-accord-deadband-signgate-eliminated-on-car]] — the deadband+sign-guard block itself, and the
prior (different-hypothesis) elimination this file's finding does NOT extend to.
[[v54-flashed-authority-measured]] (kit `memory/`) — struck `0xC6AF0`/`gp-0x6966` as a candidate this
session; the authority clamp is permanently wide open on every V31+ build, not a lever for this question.
