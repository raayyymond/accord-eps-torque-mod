---
name: reference_accord_gp6807_is_live_speed_gated_not_dead_can_status
description: CORRECTS prior framing -- gp-0x6807 (consumed by FUN_00028ea6's engage-ramp SM as "STEER_STATUS") is NOT a passively-read/dead CAN value. It is COMPUTED every 1kHz cycle INSIDE FUN_00028ea6 itself from a live speed window read directly off cal 0xC62E8 (upper bound)/0xC62EA (lower bound, the kit's known "low-speed lockout"). With 0xC62EA=0 (V53-present, confirmed through V105), the window's low half can never fail, so gp-0x6807<3 (required for gp-0x6806=1) is NOT excluded at creep speed on the current car. This is why gp-0x6806 ("LKAS is applying") is reachable/TRUE at low-speed creep, closing the crux of the 2026-08-22 Lever-B gate-reachability question.
metadata:
  type: reference
---

# `gp-0x6807`'s TRUE mechanism: a live speed-window eligibility byte computed inside `FUN_00028ea6`, not dead CAN STEER_STATUS

Traced 2026-08-22, `leverb-gate` session, team-lead's Lever-B gate-reachability brief. [EVIDENCE: fresh
`decompile_function(0x28ea6)` on `code.bin` (54KB, saved and grepped locally), `search_instructions`
whole-image census, and direct byte reads on stock/V104/V105 plain images.]

## What was wrong in the prior record

[[reference_accord_fun28ea6_ramp_statemachine_gp6806_gp69b0_decoded]] and
[[reference_accord_gp6806_phase_flag_and_dead_writer_split]] (2026-07-29) both treat `gp-0x6807` as an
externally-supplied "STEER_STATUS" value and conclude every `gp-0x6807==3/4/7` check in the ramp SM is
**dead code**, citing `0xC62EA=0` (V53) and `0xC64B8=0xFF` (V37) as reasons those VALUES are unreachable
— correct in outcome, but via the wrong mechanism, and the deadness claim is **too strong**: the checks
themselves are live and re-evaluated every cycle; only the specific LOW-SPEED path to `==3` was closed.

## The real mechanism [EVIDENCE, fresh decompile, addresses byte-exact]

`FUN_00028ea6` (~0x28ea6-0x29750, the engage-ramp SM plus a shared setup block ahead of it) computes
`gp-0x6807` itself, every call, from a speed-window plausibility check:

```c
// shared setup, runs before the gp-0x3d38 state dispatch (~0x28f0e-0x28f26):
uVar13 = *(ushort*)(tp+0x72e8);              // 0xC62E8 -- upper speed bound
uVar25 = *(ushort*)(tp+0x72ea);              // 0xC62EA -- lower speed bound = KIT'S "low-speed lockout"
uVar20 = *(ushort*)(gp-0x6a5e);              // voted vehicle speed
bVar2 = !((uVar13 < uVar20 || uVar20 < uVar25) && gp-0x68b3 == 0);   // false = outside window

// later (~0x29180-0x292f8), inside a bigger eligibility block gated on bVar3(torque-plausibility),
// FUN_00046ea6(9)!=1, gp-0x67fa!=8, and gp-0x6807!=7 (self-latch):
if (bVar2) { ... debounced counter, can still land gp-0x6807 = 4 on timeout/direction-conflict ... }
else       { gp-0x6807 = 3; }          // <<< the value that blocks STATE1->STATE3/6 (ramp begin)
// outer condition false entirely -> gp-0x6807 = 7 (persists once latched, self-referential check)
```

**Writer census confirms this is the SOLE live writer**: `search_instructions(operand_pattern="6807")`
whole-image, 32 hits — all 10 writers + 9 reads inside `FUN_00028ea6` (live, sole caller
`FUN_0002214a` the 1kHz task); the other 9 writes are inside `FUN_0002a30e`, re-confirmed DEAD this
session (`get_function_callers(0x2a30e)` = "No callers found", matching the prior session's finding
exactly); `FUN_0004e82e` and `FUN_00055c42` only READ it — `FUN_00055c42` sits in the CAN `0x14A`
packer's address range, meaning `gp-0x6807`, computed HERE, is what gets TRANSMITTED as bus
STEER_STATUS, not the reverse.

## The state dispatch itself, re-confirmed byte-for-byte against the prior trace

`gp-0x3d38` (state, read into `bVar6` at the dispatch), STATE1 (`bVar6==1`, idle) only initiates the
ramp (`gp-0x679f=1/2; gp-0x3d38=3/6; gp-0x6806=1`) when ALL of: `gp-0x6805==1`(request) AND
`gp-0x6803∈{0,2}`(direction, 1=neutral=hold) AND **`gp-0x6807<3`**. This exactly matches
[[reference_accord_fun28ea6_ramp_statemachine_gp6806_gp69b0_decoded]]'s phase-transition addresses
(0x293a6, 0x293e4/0x293fe, 0x2948c/0x29494, 0x2958c/0x29594, 0x2970e, 0x29696, 0x296d2, 0x29724) —
that part of the prior trace is fully correct and unchanged; only the SOURCE of `gp-0x6807`'s value
was mis-modeled.

## Byte-exact values, stock vs current car (V104/V105 identical)

| cal | role | stock | V104 | V105 |
|---|---|---|---|---|
| `0xC62E8` | window upper bound | 12800 (≈200 km/h-equiv) | 12800 | 12800 |
| `0xC62EA` | window lower bound | 320 (≈5 km/h, the known "low-speed lockout") | **0** | **0** |
| `0xC64B8` | unrelated DTC-0x49 counter gate | 112 | 255 | 255 |

⇒ **Pre-V53, creep speed (< 320 counts) would have failed the window, forcing `gp-0x6807=3` and
blocking the ramp — i.e., stock Honda's "low-speed lockout" WAS partly implemented through this exact
mechanism, inside the ramp SM's own eligibility computation, not a separate independent gate.**
Post-V53 (confirmed still true on V105, direct byte read of
`_v105_V104BASE-NOTCH25.5HZ..._plain_image.bin`), the low half is neutralized; the upper bound
(≈200 km/h-equivalent) is never binding at any real driving speed, creep included.

## What is still open — UPDATED same session, 3 of 5 now closed

Of the 5 secondary conditions gating `gp-0x6807<3`:
- **`gp-0x67fa!=8` — CLOSED, non-binding.** Kit's own retracted/corrected finding
  ([[reference_accord_leverb_v104_v105_deployment_status_and_open_diagnostics]]'s parent handoff,
  retraction table item 17): the sourced/reachable states during driving are **{4, 11}**, not 8.
- **torque-plausibility window (`0x6400+torque(gp-0x4f60) < 0xc801` unsigned) — CLOSED, non-binding.**
  Only fails above ≈25,600 counts of column torque; realistic driver torque tops out in the low
  thousands, moderate or hard steering included.
- **`FUN_00046ea6(9)` — CLOSED, non-binding.** Fresh decompile: `bit 9 of (gp-0x18d0 | gp-0x18d4)`, a
  fault/DTC bitmask (same family as this function's other indices per prior kit tracing). Every
  characterized route on this car is fault-free (0 sentinels, DTC bit2 duty 0.00000, CONFIG_VALID
  1.0) — non-binding absent an active fault.
- **`gp-0x67fe==2` and the `gp-0x69aa`/`gp-0x69ae` setpoint window — STILL OPEN, not traced.** Neither
  has shown any speed/rate dependence in anything read so far; lower priority than the other three.
  If this needs to be fully airtight, trace `gp-0x67fe`'s writer next.

## Related
[[reference_accord_fun28ea6_ramp_statemachine_gp6806_gp69b0_decoded]],
[[reference_accord_gp6806_phase_flag_and_dead_writer_split]] — the state-dispatch/phase-flag work this
session's finding refines (their dispatch-address work stands; their "gp-0x6807 is dead CAN status"
framing is superseded by this file).
[[accord-gp6806-is-the-lkas-gate-validated-on-car]] (kit `memory/`) — the on-car 99.9% latActive
correlation this structural finding is consistent with.
[[accord-gp67fa-state-gate-on-assist-chain]] (kit `memory/`) — the OUTER gate (whether `FUN_00028ea6`
runs at all), independent of this file's INNER speed-window gate.
