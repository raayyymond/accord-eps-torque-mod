---
name: reference_accord_fun2a30e_steerstatus_debounce_statemachine
description: Accord TVA-A160 FUN_0002a30e (0x2a30e-0x2a507, the "re-engage ramp manager") is the actual producer of STEER_STATUS=4 (gp-0x6807=4, CAN 399 no_torque_alert_2). Full decompile obtained. It is a two-phase debounce+hold state machine gated on gp-0x682f (byte, consecutive-good/bad counter, source unresolved), param_1 (u16, likely angle/rate, source unresolved), and param_2 (bool, source unresolved) -- NONE of which are wired into any of V31P-V2's 5 instrumented gate flags. This is a genuinely new, previously-un-instrumented candidate mechanism directly upstream of the observed gentle-EME symptom.
metadata:
  type: reference
---

# FUN_0002a30e -- STEER_STATUS=4 debounce+hold state machine (2026-07-13, Ghidra code.bin)

Full `decompile_function` obtained (program="code.bin"). Signature: `FUN_0002a30e(uint param_1, int param_2,
int param_3, int param_4, int param_5)`. Body 0x2a30e-0x2a507.

## Byte-exact write-site confirmation of the mission's cited anchors
`search_instructions operand_pattern="-0x6807"` shows the two STEER_STATUS=4 write sites as:
- `0x2a4ec: st.b r12,-0x6807,gp` (bytes `4467f997`), preceded by `0x2a4ea: mov 0x4,r12` (2B) -- matches the task's
  cited "0x2a4ea" anchor (that address is the `mov` immediately before the store).
- `0x2a4fc: st.b r10,-0x6807,gp` (bytes `4457f997`), preceded by `0x2a4fa: mov 0x4,r10` (2B) -- matches "0x2a4fa".

`search_instructions operand_pattern="-0x6757"` confirms the countdown byte gp-0x6757 (`0xFEDF1AA9`) is read/written
21 more times across this function, matching the task's cited anchor exactly.

## Two-phase debounce+hold mechanism, decompiled
`cVar2 = *(char*)(tp+0x74e2)` (= **cal 0xC64E2, read this session = 5**, confirmed by `read_memory` at 0xC64E0:
bytes `32 32 05` -> tp+0x74e0=50, tp+0x74e1=50, tp+0x74e2=5) is loaded once at entry and used as both a debounce
LENGTH and a reset seed throughout.

**Early unconditional bails** (any of: `param_3==0`, `FUN_00046ea6(9)==1`, `gp-0x67fa==8`, `gp-0x6807==7` already,
or STATUS_WORD bit3 set, or `param_5==0`/enable-false) immediately write a non-4 status code (7, 6, or 3) and reset
`gp-0x6757 = -cVar2` (i.e. -5) -- restarting the debounce from scratch.

**Rise phase** (`gp-0x6757 <= 0`, i.e. counting up from -5 toward 0): each call where a threshold condition holds
(`gp-0x682f` vs cal bytes 0xC64B4/0xC64B7/0xC64B6, ORed with `param_1` vs cal halfwords 0xC61C0/0xC61C2/0xC61C4,
gated by bool `param_2`) increments `gp-0x6757` by 1 and does NOT yet set status=4. Only once the increment would
cross zero does it flip: **`gp-0x6807 = 4`**, and `gp-0x6757` is RESEEDED from `cal tp+0x74df` (**=0xC64DF, read
this session = 100 (0x64)**, confirmed by `read_memory` at 0xC64DF) -- this is the transition instant.

**Hold phase** (`gp-0x6757 > 0`, counting down from 100): each subsequent call decrements `gp-0x6757` by 1 and
RE-ASSERTS `gp-0x6807 = 4`, UNLESS the quality condition (same gp-0x682f/param_1/param_2 tests, different cal
bytes 0xC64B5/0xC64B7/0xC64B6) fires, in which case the countdown is reset to the SHORT value `cVar2` (5) instead
of continuing the long decay. Once the countdown decrements to <=1, the state reverts to a different status code
(`cVar8`, a small 0-2 value) and `gp-0x6757` resets to `-cVar2` (-5), restarting the whole cycle.

## Rate/lag quantification -- PARTIAL, one link unresolved
If FUN_0002a30e runs at the same ~100 Hz cadence as `m_steer_torque_arbitration` (its sibling, confirmed this
session called directly from `w_steer_control_task` @ 0x2214a via `get_function_callers`), the rise-debounce
(cal 0xC64E2=5) would take ~50 ms, and the hold seed (cal 0xC64DF=100) would take up to ~1000 ms of full decay --
much longer than the empirically observed ~99 ms STEER_STATUS=4 duration, UNLESS the hold is cut short by the
quality-degrades-mid-hold reset branch (which reseeds to the much shorter 5-cycle value, ~50 ms -- closer to, but
not an exact match for, the observed 99 ms). **FUN_0002a30e's own caller/call-rate was NOT found this session**
(`get_function_callers` by address AND a direct `jarl` disp22 operand-substring scan for "2a30e" both returned
zero hits) -- it must be reached via an indirect call from within/near `m_steer_torque_arbitration`. This is the
single open link needed to convert the ms-lag estimate from BELIEF to EVIDENCE.

## Why this matters for telemetry design
`gp-0x682f`, `param_1`, and `param_2`'s semantic identities are UNRESOLVED this session (gp-0x682f is known only
as a byte zeroed by `m_steer_torque_arbitration`'s 3 hard-bail range checks per
`reference_accord_arb_bvar1_full_enumeration`, not what increments it). **None of V31P-V2's 5 instrumented gate
flags (decider r12, GATE5_TORQUE, VOTER_AVG, ANGLE_DB, HARD_CUT) touch these three inputs.** This function is
therefore a genuinely new candidate directly upstream of the observed symptom (STEER_STATUS=4 itself), never
tested by any build to date.

## STEER_STATUS's role in m_steer_torque_arbitration -- refines, does not overturn, "report only"
`disassemble_bytes` 0x29600-0x29820 shows `gp-0x6807` reads at 0x2963e/0x29674 feed a LOCAL bookkeeping
mini-state-machine (writes to `gp-0x3d38`, `gp-0x679f`, `gp-0x3d37`, and a duration halfword `gp-0x69b0`) that
selects WHICH of three downstream ramp-duration branches to take (targets 0x29808/0x29964/0x29a28) -- but the
actual LKAS-output zeroing gate at each of those branches is STILL independently `gp-0x6809==1` (see
[[reference_accord_gp6809_zero_writers_confirmed_dead_gate]]), which is permanently false. So gp-0x6807 selects
ramp TIMING/PARAMETERS, not a direct pass/fail gate on LKAS output -- refines the existing "REPORT only, no
gating read-back" characterization with the precise mechanism, does not contradict it.

## Related
[[reference_accord_gp6809_zero_writers_confirmed_dead_gate]] -- the E1 gate this function's output feeds into (confirmed dead).
[[reference_accord_arb_bvar1_full_enumeration]] -- original identification of FUN_0002a30e as "re-engage ramp manager."
[[reference_accord_telemetry_ram_hook_a160]] -- source of the w_steer_control_task/~100Hz chain this memory's rate estimate depends on.

## Next verification step
Find FUN_0002a30e's indirect call site (likely inside `m_steer_torque_arbitration` near the gp-0x6758/gp-0x6807
read cluster ~0x29100-0x29200) to pin its true call rate, and trace gp-0x682f's writer(s) and param_1/param_2's
sources to identify what the debounced condition physically is (angle? rate? torque?).
