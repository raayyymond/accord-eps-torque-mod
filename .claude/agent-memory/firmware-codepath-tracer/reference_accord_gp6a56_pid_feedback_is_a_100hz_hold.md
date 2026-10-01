---
name: reference_accord_gp6a56_pid_feedback_is_a_100hz_hold
description: The LKAS rate PID's feedback operand gp-0x6a56 (read at 0x28F4C) is produced by FUN_0003f776, whose ONLY call site 0x22de2 is in the 100 Hz slot-4 task FUN_00022ca0 -- the "1 kHz rate loop" closes on a 10 ms hold. Corrects TRACE-2026-09-10's "no staleness" (phase masks compared, task rate never checked). Fresh 1 kHz source exists: gp-0x6abe (FUN_00041464 @0x22200, slot 0).
metadata:
  type: reference
---

# The rate PID's feedback `gp-0x6a56` is a 100 Hz hold (2026-09-30)

**[EVIDENCE]** `FUN_0003f776` has one call site, `0x22de2`. That is a raw `jarl` byte scan,
positive-controlled on `0x22522`, with zero pointer-table hits; Ghidra agrees. The site is inside
`FUN_00022ca0`, RTOS slot 4, which `FUN_00014be4` activates only when `gp-0x4304 % 10 == 4`. All 4
writers of `gp-0x6a56` are in `FUN_0003f776`. `FUN_00028ea6` (slot 0, every tick) reads it at
`0x28F4C`. ⇒ the PID sees a 10-tick staircase: 9 ticks of no change, then a jump.

**Corrects** `TRACE-2026-09-10-command-intersample-zoh.md` §"No staleness". That trace showed the slot-4
phase mask `0xd38` ⊇ the PID's `0x930`, but `FUN_00022ca0` is a different TASK at one tenth of the rate.
**Not yet re-derived:** what a 10-tick ZOH on the feedback does to the two-sample-sum filter, the D term
and the 20 Hz "crossover resonance". About 40° of phase at 20 Hz is a first-order estimate only.

**Fresh alternative:** `gp-0x6abe` is the raw electrical rate, written by `FUN_00041464` at `0x22200`
in slot 0. `gp-0x6a56 = clamp(pol*((gp-0x6abe*0x30*cal 0xC613A)>>15), ±12000)` per
[[reference-accord-can-angle-producer-and-no-angle-correction]]. That formula was not re-verified this
session.

Related: [[reference_accord_gp6a00_angle_is_a_100hz_hold_inputs_fresh_at_1khz]],
[[reference_accord_0x28f4c_rate_operand_hook_runs_every_tick]].
