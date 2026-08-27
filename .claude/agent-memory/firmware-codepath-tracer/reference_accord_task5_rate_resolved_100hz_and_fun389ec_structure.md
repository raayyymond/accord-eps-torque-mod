---
name: reference_accord_task5_rate_resolved_100hz_and_fun389ec_structure
description: "RETRACTED 2026-08-12: the 100Hz claim is CONTRADICTED by gp-0x6bbe's own flown data (route 79 freq/step/phase all point close to 1kHz). FUN_00083854/FUN_00083918 (called 'wake-related' below) turned out to be general kernel primitives on a fresh decompile, not confirmed task-wake functions -- the whole FUN_000837c0-as-task-eligibility-check reading was unverified beyond a coincidental self-consistency with task 1's ALREADY-KNOWN 1kHz. Task 1=1kHz (control-task-tick-confirmed-1khz) is UNAFFECTED. Task 5's true rate is UNRESOLVED. FUN_000389ec's RAM-LERP structural facts (9-point table, 10x-per-call commit, Y[0]=0) stand on their own but the '10Hz effective' framing inherits the retracted rate."
metadata:
  type: reference
---

## 🛑🛑 RETRACTED 2026-08-12 — see `reference/firmware/reference-accord-task5-100hz-syscall8-rate-divider.md` in the kit's `memory/` for the full writeup (mirrored there, team-lead adjudication)

Three independent measurements on `gp-0x6bbe`'s own flown telemetry (route 79) contradict 100Hz and point
close to 1kHz instead: frequency response ≈−1.2dB at 6-9Hz (100Hz predicts −6.6/−8.4/−9.5dB, 1kHz predicts
−0.2/−0.3/−0.3dB); step response +114% at 20ms (100Hz's implied τ=44.8ms caps this at 36%, a 3.8x physical
violation); phase rising monotonically to +43° by 20Hz (a 100Hz-rate pole would make phase fall, not
rise). Re-examining `FUN_00083854`/`FUN_00083918` (below, called "wake-related" without a full decompile)
shows them to be general kernel event-dispatch primitives, not confirmed RTOS task-wake functions — the
identification of `FUN_000837c0` as a task-eligibility check rests on a coincidental address match, not a
verified mechanism. **Task 1 = 1kHz stands** (two other, independent methods). **Task 5's true rate is
open.** The consequence section below (gp-0x6bbe's −5.8/−7.5/−8.6dB attenuation at 6-9Hz) does NOT survive
and should not be used for sizing.

---

# Task 5 = 100Hz [RETRACTED — kept below for the record], + FUN_000389ec's RAM-LERP construction [structural facts stand] -- 2026-08-11, `lane-weights-6bf`

Dispatched to decompile `FUN_000389ec` (populator of the RAM LERP `FUN_00038148` uses in its stage-2,
X@gp-0x64b8.., Y@gp-0x641c..) to settle Q5 (sign of raising `0xC63A2`) for team-lead. Did not fully close
Q5, but resolved a decisive prerequisite three prior sessions (2026-07-29, 2×2026-07-30) left open.

## [EVIDENCE] `FUN_00022ca0` (task 5) = 100 Hz

Method: `FUN_000837c0` (the syscall-8 eligibility handler) computes
`*(uint*)(param_1*0x30 + *(int*)(tp-0x3814) + 0x2c)`. Read `*(int*)(tp-0x3814)` (tp=0xBF000, so
`tp-0x3814=0xBB7EC`) directly: **= `0x000BB920`, which is TCB[0]'s own address** — i.e. the "table" this
indexes is the **TCB pointer array itself** (7 TCBs, 0x30-byte stride, per
[[reference_accord_rtos_task_table_and_rate_scheduler]]: `0xbb920,0xbb950,0xbb980,0xbb9b0,0xbb9e0,
0xbba10,0xbba40`). `FUN_00014be4`'s mod-100 counter calls `syscall8(0/1/3/4/5)` at rates /1,/2,/5,/10,/100
respectively — **these param values are exactly the TCB ARRAY INDICES 0,1,3,4,5** (skipping 2 and 6, which
are the 4-byte stub task and the background/no-period task 7 — consistent, neither needs a periodic wake).
Array index 0 = TCB `0xbb920` = task 1 (`FUN_0002214a`), which is independently confirmed 1 kHz — and
`syscall8(0)` is the UNCONDITIONAL every-tick call in `FUN_00014be4`, i.e. index 0 ↔ rate /1 ↔ 1 kHz,
self-consistent with the known anchor. **Task 5's TCB (`0xbb9e0`) sits at array index 4** (byte-read this
session: TCB entry #4 counting from 0 at stride 0x30 lands exactly on `0xBB9E0`, and this TCB's own bytes
confirm `[07][prio=02][taskid=05][00]` at +0x04 and entry point `0x00022ca0` at +0x08, i.e. genuinely task
5). `syscall8(4,...)` fires on `c%10==4` — the **/10** group. **⇒ task 5 = 1000Hz / 10 = 100 Hz.**

[BELIEF, minor residual]: I did not fully re-derive the exact bit-AND eligibility semantics inside
`FUN_000837c0` (what `iVar3+0x24`, the CURRENT task's own field, physically is) — the array-index↔param
correspondence and the task1=1kHz self-consistency check are what I'm resting the 100Hz conclusion on, not
a full trace of the mask bits themselves. Recommend a second method (on-car cadence measurement, as
`reference_accord_boost_amp_blend_direction_and_d2000_block.md` already proposed) before treating 100Hz as
fully certified, though I have fairly high confidence given the clean self-consistency.

## Consequence for `gp-0x6bbe`'s (boost) 6-9Hz content, RECOMPUTED at fs=100Hz (not 21Hz as prior sessions used)

Single-pole EMA alpha=205/1024=0.2002 (`FUN_00034a72`'s outer torque EMA, established prior session):
```
|H(f)| = alpha / sqrt(1 - 2*(1-alpha)*cos(2*pi*f/fs) + (1-alpha)^2),  fs=100, alpha=0.2002
f=6.0 Hz:  |H|=0.513  (-5.8 dB)
f=7.79Hz:  |H|=0.421  (-7.5 dB)
f=9.0 Hz:  |H|=0.372  (-8.6 dB)
```
Moderate attenuation, NOT the near-total (-14.9dB was computed at 21Hz, not 6-9Hz) loss a naive reuse of
the prior 21Hz number would suggest. **The rate_error tail** (raw `gp-0x6a56`, angle rate, NO EMA applied
anywhere per [[reference_accord_gp6bbe_baseline_fsm_and_lerp_struct_solved]]) is essentially untouched by
the 100Hz sample rate at 6-9Hz (Nyquist=50Hz, no aliasing risk at this band) — only its own K1/Y3
gain-scheduling terms are subject to the 100Hz update cadence, not the underlying signal.

## `FUN_000389ec` RAM LERP structure [EVIDENCE for shape, OPEN for the Y-value formula]

Fresh full decompile, `code.bin`. Confirms/extends [[reference_accord_ram_lerp_y0_zero_corrects_v86_relay_claim]]:
- **9 knots** (X0..X8, Y0..Y8), not 6/7 as some earlier framing assumed. Live cells: X-base `gp-0x64b8`
  (X0) down through ~`gp-0x64a8` (X8); Y-base `gp-0x641c` (Y0) down through ~`gp-0x640a` (Y8) — matches the
  address family the team-lead's brief already cited.
- **Y[0]=0 re-confirmed independently this session**: `*(undefined2*)(gp-0x3714) = 0;` unconditional
  staging init, every call, before the per-index loop — same conclusion as the prior session, reached via
  a fresh full decompile rather than reused.
- **Commits once per 10 calls** (`if (iVar33==9) { ...copy staging gp-0x373c/gp-0x3714 arrays into the
  live gp-0x64b8../gp-0x641c.. cells... }`, `iVar33` is a mod-10 counter incremented every call). Combined
  with task 5 = 100Hz (above): **the live RAM LERP table only refreshes at 10 Hz**, not every call. This
  is a SEPARATE, slower cadence than the 1kHz rate `FUN_00038148` itself samples it at — the table is a
  quasi-static curve that steps every 100ms, not a per-sample-updated function.
- **The X-axis is SPEED-SCALED**: the very top of the function computes `uVar46` via an LERP over
  `gp-0x6a64` (voted vehicle speed, established) against a static cal block `tp+0x769a..0x76b4`, and this
  becomes both a scaling factor and an in-range/out-of-range branch threshold inside the main population
  loop — i.e. the knot spacing/range depends on current speed, not a fixed cal table.
- **The Y-values (and the pre-scaled X source) come from an UNIDENTIFIED per-vehicle source array**
  (`gp-0x6350`/`gp-0x630c` region, read via a dense per-index loop, normalized through two calls to a
  shared subroutine `FUN_0003897a` fed by `gp-0x6984`/`gp-0x6982`-derived clamped LERP scalars). **I did
  not trace `gp-0x6350`/`gp-0x630c`'s own producer or `FUN_0003897a`'s function this session** — this is
  the piece that would be needed to determine the table's monotonicity/sign away from Y[0]=0, and it did
  not yield to a single decompile pass (the surrounding logic is ~700 lines of dense median-of-3/
  shadow-lockstep boilerplate obscuring the real per-knot formula).

## 🛑 Sign of `0xC63A2` STILL NOT CLOSED — but the open item changed shape

Found a genuine, already-recorded STRUCTURAL CONTRADICTION in this kit's own history that bears directly
on Q5, not previously connected:
- [[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]] (2026-07-29): "`FUN_00034a72`'s final
  combine only multiplies by `assist_polarity` — no motion/velocity sign flip anywhere in the function...
  **boost is SAME-SIGNED as the raw torque sensor — reinforcing, not opposing**", ranks it a top suspect
  for INJECTING energy, explicitly contrasted against the damping lane's confirmed `sign(gp-0x6abe)`
  velocity-opposing flip.
- [[reference_accord_gp6bbe_rate_error_speed_scheduled_lane]] / [[reference_accord_gp6bbe_baseline_fsm_and_lerp_struct_solved]]
  (2026-07-30, LATER, deeper trace of the SAME function): found a tail the 07-29 session didn't reach —
  `rate_error = baseline − raw_angle_rate(gp-0x6a56)`, scaled by K1/Y3, feeding the FINAL clamp — a
  genuine rate-domain term the "no velocity sign flip" claim missed. Its own conclusion: "**net damping is
  the structurally-favored read... but not provable from static analysis alone.**"
- The operator's own on-car measurement (`accord/signals/accord-gp6bbe-is-viscous-plus-dc-pedestal.md`, global memory):
  flat ≈90 ct/(rad/s), phase~0° — explicitly stated to **REFUTE** "same-signed as torque sensor ⇒
  reinforcing."

**Reading**: the 07-29 "reinforcing" claim is very likely INCOMPLETE (examined the dominant/outer path,
same pattern as the domain-audit's "no angle content" claim that the SAME later sessions also corrected),
not wrong-and-superseding — the deeper rate_error tail is real and structurally present. But neither trace
computed the NET closed-loop sign at 6-9Hz once the two paths combine, the K1 gain magnitude, the
still-partially-open LERP-table monotonicity (this file), AND the Path-2 stage-2 RAM LERP's own shape all
stack. **Three static-analysis sessions across two months have not closed this. I recommend the empirical
measurement (parallel agent, source/sink at 6-9Hz from flight data) as primary for Q5** — it directly
measures the net answer without needing every intermediate sign right.

## Related
[[reference_accord_fun38148_six_weight_v95_candidate_census]] — the Q1-Q5 census this extends/updates.
[[reference_accord_gp6bbe_baseline_fsm_and_lerp_struct_solved]] / [[reference_accord_gp6bbe_rate_error_speed_scheduled_lane]] / [[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]] / [[reference_accord_boost_amp_blend_direction_and_d2000_block]] — the four prior sessions on `gp-0x6bbe` this file reconciles.
[[reference_accord_rtos_task_table_and_rate_scheduler]] — the TCB/rate-divider structure task5=100Hz is derived from.
