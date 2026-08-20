---
name: reference_accord_gp6abe_live_triple_confirmed_and_gp6a5e_mislabel_flag
description: CLOSES the 3-way contradiction flagged open in reference_accord_damping_friction_returncentre_torque_gates.md -- gp-0x6abe IS live in normal driving (independently re-derived from a fresh FUN_00041464 decompile, the THIRD independent trace to reach this conclusion). Also flags that the same file's "0xC9E9C keyed on gp-0x6a5e = AVG DRIVER TORQUE" label is SUPERSEDED -- gp-0x6a5e is voted VEHICLE SPEED (3-way confirmed in reference_accord_factorc_e_damper_full_trace_r24r26_parallel.md), so that table is NOT a driver-torque-keyed damping gate.
metadata:
  type: reference
---

Found 2026-08-19 while hunting for a |driver-torque|-keyed damping/authority gate (item 5 of a
V101 self-oscillation damping-lever brief). Program: stock `code.bin`.

## gp-0x6abe live-status: THREE independent traces now agree [EVIDENCE]

`reference_accord_damping_friction_returncentre_torque_gates.md` flagged a 3-way disagreement over
whether `gp-0x6abe` (the sign source gating `FUN_00034350`'s damping term) is live in normal driving
or permanently pinned to `0x7fff`. This session did a **fresh, independent** `decompile_function`
of `FUN_00041464` (not reading the resolving memory first) and confirmed: the function branches on
`bVar2 = |gp-0x4f50| > ~12936` (an "abnormal rate" flag). In the `bVar2==false` (normal) branch,
when the debug/factory CRC-magic gate fails (confirmed by byte-reading `tp+0x50ed`=`0xC40ED`=`0x00`
on both stock and the current V101 image, not the required `0xE9`), `gp-0x6abe` is set to a live
EMA-filtered copy of `gp-0x4f50` (`uVar16 = EMA(gp-0x4f50*1024, gain=tp+0x743c) >> 10`), NOT pinned.
Only in the `bVar2==true` branch does it pin to `0x7fff`.

This is the SAME conclusion `reference_accord_fun34350_damping_term_live_and_gated.md` already
reached (and additionally proved the pin branch is structurally unreachable in production, because
`gp-0x4f50` is hard-clamped to `[-13000,13000]` upstream, making `|gp-0x4f50|>13000` impossible).
**Three independent derivations (that file's first pass, its later exhaustive-sweep correction, and
this session's from-scratch re-decompile) now agree: `gp-0x6abe` is always live in production.**
Treat the contradiction in `reference_accord_damping_friction_returncentre_torque_gates.md` as
CLOSED in favor of "live." No action needed on that file beyond this pointer.

## 🛑 Flag: that same file's `gp-0x6a5e` = "driver torque" label is SUPERSEDED, not corrected in place

`reference_accord_damping_friction_returncentre_torque_gates.md` labels the `0xC9E9C` table
(Y=0,235,430,877 rising) as "keyed DIRECTLY on gp-0x6a5e (AVG voted driver column torque)" and reads
it as a driver-torque-activated damping term. **`reference_accord_factorc_e_damper_full_trace_r24r26_parallel.md`
later corrects `gp-0x6a5e`'s identity to voted VEHICLE SPEED**, confirmed three independent ways
(shared gate with the speed-domain r24/r26 cross-axis; breakpoints 2240/3840/5120/8960 divide
exactly by 64 into 35/60/80/140 km/h; onset exactly 35 km/h). **`0xC9E9C` is FactorC of the
FUN_00034350 base-assist damper — a SPEED-scheduled factor, not a torque-scheduled one.** This
kills it as a candidate for item 5 (a driver-torque-keyed gate): applying more steering torque does
not, by itself, raise this term's gain — vehicle speed does. I did not edit the original file
(not this session's memory to correct unilaterally); flagging here so nobody re-cites the "driver
torque -- one table found this session whose shape matches 'requires driver torque to activate'"
framing without the correction. [[reference_accord_factorc_e_damper_full_trace_r24r26_parallel]] is
the authoritative axis label going forward.

## Net effect on the item-5 hunt (|driver torque|-keyed damping/authority gate)

No standalone driver-torque-magnitude-keyed damping or authority-reduction gate was found anywhere
in the aggregator's 11 lanes, the governor, the shaper, or the two engagement state machines
searched this session and in the prior sessions this file draws on. `gp-0x67f4` (the "plausibility"
flag reused by nearly every lane's gate) is independently confirmed elsewhere
(`reference_accord_aggregator_domain_audit_no_angle_lane_found.md`) to be the voted-SPEED-validity
flag, not a torque or hands-on/off signal. This is a genuine negative result, not exhaustive beyond
the paths named.

## Related
[[reference_accord_fun34350_damping_term_live_and_gated]], [[reference_accord_factorc_e_damper_full_trace_r24r26_parallel]],
[[reference_accord_damping_friction_returncentre_torque_gates]] (the file this closes/flags).
