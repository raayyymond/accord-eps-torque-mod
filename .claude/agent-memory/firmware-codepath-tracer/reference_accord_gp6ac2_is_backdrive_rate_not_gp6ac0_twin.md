---
name: reference_accord_gp6ac2_is_backdrive_rate_not_gp6ac0_twin
description: gp-0x6ac2 (the FactorC/E damper's CEILING TABLE 0xC77A0 index) is NOT a copy of gp-0x6ac0's magnitude -- it is SIGN-GATED against gp-0x6b98 (the aggregate torque command), reading |rate| only when the motor's rate direction DISAGREES with the commanded torque direction (back-drive / being overpowered), and reading exactly 0 whenever the motor moves WITH its own command. Revises the [BELIEF] in reference_accord_v75_ceiling_c77a0_noclip_asymmetry_and_aggregator_inclusive_bound.md that gp-0x6ac2 "probably tracks gp-0x6ac0".
metadata:
  type: reference
---

Task: team-lead's crux result showed LEVER E' (V74) is IN FORCE on-car, and re-tasked "establish gp-0x6ac0's
true index scale" + "find the ceiling numerically, it's the most valuable single number." Follow-up to
[[reference_accord_v75_ceiling_c77a0_noclip_asymmetry_and_aggregator_inclusive_bound]].

## gp-0x6ac2's producer [EVIDENCE, decompile_function 0x41464, code.bin]
Same producer function as `gp-0x6abe`/`gp-0x6ac0` (`FUN_00041464`), NOT the same output. The non-diagnostic
path (`bVar2==false`, the live path -- diagnostic injection is disarmed on stock per
[[reference-accord-common-mode-rate-signal-6abe-6ac0-full-chain]]):

```c
uVar16 = state;                          // the shared EMA state (gp-0x359c, alpha=37/128)
uVar8 = abs(uVar16);
if (sign(uVar16) != sign(*(short*)(gp-0x6b98)))   // XOR of signs
    uVar19 = uVar8 >> 10;                // disagreement: pass the magnitude through
else
    uVar19 = 0;                          // agreement: ZERO
gp-0x6ac2 = (short)uVar19;               // (after a further sign-gate on gp-0x6b98's own magnitude window
                                          //  vs 0x2000/0x4000, immaterial at the small values in play here)
```

`gp-0x6b98` is the kit's established aggregate/delivered torque command (per
`reference_accord_gp6b98_aggregator_definitive_lane_table_v57.md` /
`reference_accord_can427_source_is_gp4f74_not_gp6b98.md` -- gp-0x6b98 sits at the aggregator's own output,
upstream of the final CAN-transmitted copy).

## Reading: gp-0x6ac2 IS A BACK-DRIVE RATE, not a general rate magnitude
**`gp-0x6ac2` = |motor rate| ONLY when the motor is turning OPPOSITE to what is currently commanded**
(driver overpowering the assist, or a fast external disturbance) — **and is exactly 0 whenever the motor
moves WITH its own commanded torque direction**, which is the ordinary case for most commanded motion.

## Consequence for the ceiling table `0xC77A0` (FactorC/E's clamp, `X=[300,800] Y=[512,1024]` on mode 26)
The ceiling sits at its **floor (512)** whenever the motor moves WITH command (the common case), and can
rise toward **1024** specifically DURING back-drive/disagreement events. This is architecturally sensible
for a safety ceiling: more damping authority is *allowed* precisely when something is fighting the motor.
**Practical effect on any V75 dose ladder built on this damper**: the conservative `floor=512` assumption
used in [[reference_accord_v75_ceiling_c77a0_noclip_asymmetry_and_aggregator_inclusive_bound]]'s Rungs A/B
is a safe WORST-CASE bound, not necessarily the value in force throughout a real oscillation burst — if a
resonance/limit-cycle involves the motor briefly reversing relative to command each cycle (plausible for a
lightly-damped mode), the ceiling could lift toward 1024 at exactly those instants, giving MORE effective
headroom than the static 512-floor analysis assumed. This weakens the case for Rung C's separate
ceiling-table edit (512->900) — the architecture may already self-relax the ceiling during the moments
that matter, without touching a second table. NOT independently confirmed against telemetry this session
(would need `gp-0x6ac2` or `gp-0x6b98` sign-disagreement duty during an actual grind-#1/ratchet burst).

## Related
[[reference_accord_v75_ceiling_c77a0_noclip_asymmetry_and_aggregator_inclusive_bound]] -- supersedes its
"gp-0x6ac2's physical identity was not resolved this session" open item.
[[reference-accord-common-mode-rate-signal-6abe-6ac0-full-chain]] -- gp-0x6abe/gp-0x6ac0 origin, same
producer function.
[[reference_accord_gp6abe_column_degps_scale_settled]] -- gp-0x6ac0's scale to column deg/s (4.7121),
unaffected by this finding (gp-0x6ac2 is a gated DERIVATIVE of the same EMA state, not FactorE's own index).
