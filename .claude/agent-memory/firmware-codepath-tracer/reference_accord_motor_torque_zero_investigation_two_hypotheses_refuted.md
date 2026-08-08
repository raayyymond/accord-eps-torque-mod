---
name: reference_accord_motor_torque_zero_investigation_two_hypotheses_refuted
description: Investigation into why CAN 0x1AB MOTOR_TORQUE/steeringTorqueEps reads ~0 in openpilot rlogs. REFUTES DBC bit-position mismatch (the real honda_accord_2018_can_generated.dbc bit layout matches the firmware packer exactly) and REFUTES a frozen smoothing filter (rate cal is nonzero, ~8-cycle time constant). Also finds openpilot's Honda port does not consume steeringTorqueEps for any control decision. Leaves open: whether gp-0x4f74 is a genuinely-small-by-design signal (e.g. a current-loop residual) vs a gateway effect -- neither confirmed.
metadata:
  type: reference
---

# Why MOTOR_TORQUE/steeringTorqueEps reads ~0 -- 2 of 4 hypotheses closed (2026-08-07)

Operator asked directly why this always reads 0. Four hypotheses were framed by team-lead; two are now
settled against primary sources, not inference.

## REFUTED: DBC bit-position/scale mismatch

The real DBC (found at `C:/Users/dudei/Desktop/Projects/sunnypilot_eps/opendbc/honda_accord_2018_can_generated.dbc`,
lines 48-53):
```
BO_ 427 STEER_MOTOR_TORQUE: 3 EPS
 SG_ MOTOR_TORQUE : 1|10@0+ (1,0) [0|256] "" EON
```
Motorola (`@0`) bit numbering with start=1, length=10 decodes to **byte0 bits[1:0] (MSB half) + byte1
bits[7:0] (LSB half)** — an exact match to what `FUN_00021864` (the packer, confirmed via fresh disasm
this session, see [[reference_accord_can_tx_399_427_hook_sites_and_widened_telemetry_budget]]'s parent
report) actually writes: byte0 bits1:0 = top 2 bits of a 10-bit clamped value, byte1 = low 8 bits.
**openpilot is reading exactly the bits the firmware writes.** DBC declares range `[0|256]` vs the
packer's real clamp `[0,1023]` — a 4x headroom note, not a decode bug.
`selfdrive/car/honda/carstate.py:208`: `ret.steeringTorqueEps = cp.vl["STEER_MOTOR_TORQUE"]["MOTOR_TORQUE"]`.

## REFUTED: the smoothing filter is frozen

`tp+0x73c6` (== `0xC63C6`, filter B's rate cal, the `gp-0x4f74 -> gp-0x6c18` LERP inside `FUN_00056420`)
= raw LE bytes `02 00` = **2**, confirmed identical on `code.bin` and `_v81_C407E.511-FRICTION.STOCK_plain_image.bin`.
Filter: `iVar3 = ((gp-0x4f74-iVar3)*2)>>4 + iVar3` = 12.5%/cycle step, ~8-cycle time constant —
**faster** than filter A (motor command path, rate cal at `tp+0x73c8`=`0xC63C8`=10, `>>10`, ~1%/cycle).
Not stuck, not frozen at an init value.

## `gp-0x4f74` is NOT dead code — REVISES how hypothesis 1 should be read

`gp-0x4f74` is one of the last four writes of `FUN_000757a2` — a ~10 KB, 1 kHz, checksum-sandwiched
(DTC-0x16-class fault on mismatch) torque/current model, already mapped in
[[reference_accord_fun757a2_torque_model_and_lerp6_cluster]] and
[[reference_accord_fun757a2_iqid_gainschedule_bridge_resolved]] (prior session; this session re-verified
the live cal reads and re-disassembled the tail fresh rather than trusting the file). It starts from
`gp-0x6b98` (live commanded torque) as its primary working register, runs a speed-gated Iq/Id
PI+feedforward gain schedule feeding the 4kHz FOC ISR, and computes an ABC-frame instantaneous
power/torque estimate from peak-held phase currents. `gp-0x4f74` is a terminal clamp-and-round output
of this pipeline, alongside 3 still-unidentified sibling int16 writes (`gp-0x4EA4/0x4F5C/0x4F48`).

**New this session**: the tail (`0x7ac00-0x7af40`) repeats the same clamp-and-round-to-int16 idiom at
least twice for different outputs, and one of the siblings has a visible **deadband/zero-clamp**
(`cmovge r0,r7,r7` / `cmovle r0,r7,r7` near `0x7ac58-0x7ac6e` — forces the term to exactly zero outside
a bracket). Which output that gates, and `gp-0x4f74`'s own precise formula back through the full LERP
chain, were **not traced this session** (would need several more hours on a 10KB function). This raises
a real possibility that `gp-0x4f74` is a residual/error/ripple-class term that is legitimately near-zero
under normal, well-tracking operation — a "small by design" signal rather than a "dead" one. This
distinction was NOT settled and needs either the full formula trace or an empirical per-bit rlog census.

## openpilot does not consume steeringTorqueEps for Honda control

`grep -rn steeringTorqueEps` across `C:/Users/dudei/Desktop/Projects/sunnypilot_eps/selfdrive/`: assigned
in `honda/carstate.py:208`, consumed for torque-limit gating ONLY in `chrysler/carcontroller.py` and
`toyota/carcontroller.py`. **Zero occurrences in `honda/carcontroller.py`.** For Honda specifically it is
logged/exposed in `carState` but not fed into any lateral-control decision in this fork at this commit.
Does not cover other forks/versions, and does not cover other ECUs on the bus reading 0x1AB directly.

## Still open
1. Hypothesis 3 (gateway selectively zeroing MOTOR_TORQUE's specific bits while forwarding the rest of
   0x1AB) — needs a per-bit variability census of real rlogs (`r67-analyst`'s route-67 cache), not
   resolvable from firmware alone. One argument against it (belief, not evidence): a generic CAN gateway
   selectively zeroing 10 of 24 payload bits while passing the rest of the same frame intact would be an
   unusual thing for a bus-level gateway to implement.
2. `gp-0x4f74`'s exact formula and physical units — not derived. The Kx_Id creep-branch steepness noted
   in [[reference_accord_fun757a2_iqid_gainschedule_bridge_resolved]] and the deadband found this session
   are both loose threads pointing at the same unresolved terminal computation.
3. The 3 sibling outputs `gp-0x4EA4/0x4F5C/0x4F48` remain uncatalogued.

## Related
[[reference_accord_fun757a2_torque_model_and_lerp6_cluster]], [[reference_accord_fun757a2_iqid_gainschedule_bridge_resolved]]
— the prior full trace of `FUN_000757a2` this investigation builds on.
[[reference_accord_can427_source_is_gp4f74_not_gp6b98]] — the original two-filter finding (gp-0x6b98 vs
gp-0x4f74 as separate LERP targets inside FUN_00056420) this session's rate-cal reads corroborate.
[[reference_accord_can_tx_399_427_hook_sites_and_widened_telemetry_budget]] — the telemetry-channel
context this investigation was done for.
