---
name: reference_accord_patha_arb_is_live_not_inert_correction
description: "CORRECTS the 2026-05-26 lkas-path-wiring finding that PATH-A (arb gp-0x6b3c) is inert due to gain 0xFF46C=-1. That address predates the tp=0xBF000 resolution and was reading the absent-cal-partition placeholder, not the real cal. Re-read this session: 0xC646C (tp+0x746c, the arb's real gain multiplier) = 891 (0x37B), a normal live Q-something gain. The mixer FUN_00026c80 does NOT read gp-0x69ae anywhere (0 hits in 989 instructions) -- confirming PATH-A (arb -> gp-0x6b3c -> limit_and_pack -> distribute_clamp -> mixer input slots) is the ONLY route by which the raw CAN 0xE4 torque setpoint reaches the live motor path; the other reader of gp-0x69ae is telemetry-only."
metadata:
  type: reference
---

# PATH-A (the arb) is the live conduit for CAN 0xE4, not inert — correction, 2026-08-04

## The stale claim
[[accord-lkas-path-wiring]] (2026-05-26) read cal address `0xFF46C` as the arb's gain multiplier and
found it `= 0xFFFF = -1`, concluding "PATH-A output ~ 0, confirmed inert." That same memory already
flagged the reading as suspect: *"the tp=0xF8000 reading reflects the absent cal partition, not the
runtime value."* At the time `tp` had not yet been pinned to `0xBF000`
([[reference_v850e2_extended_disp23_encoding_solved]] et al., later sessions) — `0xFF46C` is not a
tp-relative address consistent with the now-established cal block layout at all.

## Re-derivation this session [EVIDENCE]
The arb's real gain multiplier is `tp+0x746c` = **`0xC646C`**, the SAME cal this kit has extensively
documented elsewhere ([[reference_accord_c646c_gain_feedback_vs_forward_classification]],
[[reference_accord_c646c_shared_gain_not_lkas_only]]) as a live, shared, 6-reader gain. Fresh
`read_memory(0xC646C, 4)` = `7b 03 94 05` LE -> u16 **= 0x037B = 891**, a normal live gain value, not a
sentinel/absent-partition placeholder.

## The mixer does not read gp-0x69ae [EVIDENCE]
`search_instructions(function="FUN_00026c80", operand_pattern="69ae")` (the mixer, body
`0x26c80-0x27801`, 989 instructions) -> **0 hits**. So the live motor path
(mixer -> gp-0x6b4c/6b4e -> ... -> gp-0x6b94 -> gp-0x6ace -> gp-0x6b98, per
[[reference-accord-gp6b4c-lane-chain]]) does NOT read the raw CAN setpoint directly. `gp-0x69ae` has
exactly two readers image-wide (per [[accord-lkas-path-wiring]]'s own exhaustive search): the arb
(PATH-A) and the CAN-TX telemetry packer (`w_lkas_setpoint_consumer2`, ×3.25 scale, TX-only).

## Conclusion [EVIDENCE, resolves an open item]
**PATH-A is the ONLY conduit from the raw CAN `STEER_TORQUE` setpoint into the live motor path.** The
chain is: CAN 0xE4 -> `s_lkas_process_steer_cmd` (`0x52676`) -> `gp-0x69ae` (×-4, clamp ±0x4000) ->
`m_steer_torque_arbitration` (`FUN_00028ea6`, gain `0xC646C`=891 × polarity `gp-0x6752` >>15, clamp
±`tp+0x71b4`) -> `gp-0x6b3c` -> `m_steer_torque_limit_and_pack` (`FUN_0002b422`) -> `gp-0x6b3a` ->
`m_motor_cmd_distribute_clamp` (`FUN_00025c32`, the confirmed arb->mixer bridge per
[[accord-lkas-path-wiring]]) -> mixer input slots `gp-0x62e0/62f8/633c/6230` -> mixer (`FUN_00026c80`)
-> `gp-0x6b4c` et al -> aggregator -> `gp-0x6b98`. **"PATH-A inert" should be struck from any future
citation** — it was an artifact of an unresolved cal address, not a structural finding.

## What this does NOT resolve
The arb's OWN internal LKAS-integrator zeroing gates (bVar1, the 3 hard-bail checks — see
[[reference-accord-arb-bvar1-full-enumeration]]) were separately assessed as far above real driving
magnitudes (low bump-sensitivity) — that finding is UNCHANGED by this correction. Also unresolved: the
exact numeric magnitude PATH-A delivers vs PATH-B's contribution at the aggregator (both now confirmed
live, relative weighting not quantified this session).

## Related
[[accord-lkas-path-wiring]] — the memory this corrects (its writer/reader enumeration is otherwise
still accurate; only the "gain=-1/inert" conclusion is struck).
[[reference-accord-gp6b4c-lane-chain]] — the downstream chain gp-0x6b4c feeds, now confirmed reachable
from CAN 0xE4 via this corrected PATH-A route.
[[reference_accord_c646c_gain_feedback_vs_forward_classification]] — the cal `0xC646C` this session
re-read as live (891), consistent with that memory's broader "shared, live, 6-reader gain" finding.
