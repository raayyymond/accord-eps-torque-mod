---
name: reference_accord_deadband_signgate_c61b8_c64a3_routes_to_diagnostics_not_motor
description: The FUN_00028ea6 deadband+sign-consistency gate (cals 0xC61B8/0xC64A3, gp-0x6806-gated) is inert on V53+ (STEER_STATUS 3/4/7 all structurally unreachable) AND its entire output (gp-0x6b30/gp-0x6b38/gp-0x697e/gp-0x697c) routes exclusively to diagnostic/voter functions, never gp-0x6b98. Two independent reasons it cannot be the ~20-25Hz vibration mechanism.
metadata:
  type: reference
---

# Deadband/sign-gate at FUN_00028ea6 0x2a1ae-0x2a206: re-derived 2026-07-29, both premises now closed

Full re-derivation on stock `code.bin` (GhidraMCP only, `disassemble_bytes dry_run:true` + `search_instructions`,
cross-checked with byte-level Python reads of stock/V53/V54/V55/V56 plain images). Supersedes the 2026-07-20
"pregain deadband" note's open items (A)/(B)/(C) — resolved as (A), and adds a second, independent kill.

## Finding 1 — gp-0x6806 is 1 throughout normal engaged driving on V53+ (structural, not measured)

8 writers found (`search_instructions -0x6806`, 183,429 instrs, all 4-byte disp16, all in `FUN_00028ea6`):
- **Writes 1** (0x293a6, 0x293e4, 0x2948c, 0x2958c): each fires when STEER_STATUS (`gp-0x6807`) `<= 2`, or
  when the engage ramp (`gp-0x69b0`) saturates to full scale (0x8000) — i.e. ordinary engagement.
- **Writes 0** (0x29696, 0x296d2, 0x2970e, 0x29724): each requires STEER_STATUS `== 3`, `== 4`, `== 7`, or an
  internal ramp-arithmetic overflow/underflow reset.

All writers execute earlier in the same `FUN_00028ea6` pass (same ~1kHz `w_steer_control_task` cycle) than
the gate at 0x2a1ae — no cross-cycle lag.

**On the current build (V53-V56): STATUS=3 is unreachable** (`0xC62EA`=0, byte-verified in stock/V53/V54/V55/V56
— see [[accord-low-speed-lockout-window-c62ea]] for the V53 edit), **STATUS=4/7 were already unreachable on
V37+** (torque/rate cals saturated to max, DTC-0x49 counter permanently disabled). So none of the zero-writers
can fire under healthy engaged driving ⇒ **gp-0x6806 == 1 essentially always**, confirmed by exhausting every
writer's guard condition, not by inference. This settles the 2026-07-20 note's option (A) definitively —
resolves the self-latch worry too: the gate never activates, so the sign-rule's self-latch scenario never arises.

## Finding 2 — even if the gate DID fire, its output never reaches gp-0x6b98 (new this session)

`gp-0x6b30` (the gate's own output, `iVar34` post deadband+sign-test+ramp-gain) has **exactly 2 refs
image-wide** (0x2a1d4 read, 0x2a206 write, both inside the gate) — confirmed via fresh `search_instructions`,
matches the prior memory's count independently.

But the same register also feeds `r11` (`add r9,r11` @0x2a1fc, r11 = iVar34 + some other earlier term), which
is clamped (±cal `0xC61B4`) and splits two ways, **both diagnostic**:
- **gp-0x6b38** (3 refs total: this write + 2 reads in `FUN_0004e82e`, the known UDS/diagnostic record builder
  — see [[reference_accord_steerstatus3_speed_gated_but_report_only]], which already IDs this function as
  packing `gp-0x69ae`/`gp-0x4f60`/`gp-0x6a56`/`gp-0x6b38` into a 56-byte diagnostic record).
- **gp-0x697e / gp-0x697c**, gated by **gp-0x67a4** (2 refs: our read + one writer in `FUN_0002b422`). Full
  decompile of `FUN_0002b422` this session: it is a **sensor-plausibility voter/monitor** — packs gp-0x697e/
  gp-0x697c plus other clamped channels into a local struct, calls `FUN_00025c32` (a generic N-channel
  redundant-sensor voter — clamps 10 inputs to fixed ranges, tracks per-channel agreement in a persistent
  state array, returns a 0-5 status), and conditionally calls `FUN_0001cba6()` on mismatch (uninspected,
  shape implies a DTC/fault report — BELIEF not evidence). Writes `gp-0x67a4` back for next cycle. Sole
  caller of `FUN_0002b422` is `FUN_0002214a` = `w_steer_control_task`, same task as `FUN_00028ea6`.

Cross-checked against [[reference_accord_gp6b98_aggregator_full_lane_inventory]] (full decompile of
`FUN_0003aa2c`, the ONLY function that sums into gp-0x6b98): its 9 named lanes are gp-0x6ad4, -0x6bbe,
-0x6bd0, -0x6b86, -0x6b4c, two inline friction terms, -0x6b62, -0x6b46/`FUN_00036682`, -0x6b26, -0x6ade.
**None of gp-0x6b30/-0x6b38/-0x697e/-0x697c/-0x67a4 appear in that list.**

⇒ **This entire computation (one-pole IIR `gp-0x3d3c` → deadband/sign-gate → ramp-gain → polarity-scale →
symmetric clamp) is a self-contained diagnostic/monitor side-channel. It cannot shape torque under any
gp-0x6806 state.** Even a live, misbehaving relay here would only corrupt a UDS telemetry field and a
plausibility-voter input — not the motor command.

## Corrected block pseudocode (byte-exact, corrects two control-flow details in the 2026-07-20 note)

```python
# entering: r9=iVar34 (IIR state >>5), r16=cal 0xC64A3 (loaded 0x2a198)
if cal_0xC64A3 == 1:                                    # 0x2a1ae/0x2a1b4
    if gp_0x6806 == 0:                                  # 0x2a1b6-0x2a1bc
        L_signed = read_i16_LE(0xC61B8)                 # 0x2a1be  ld.h SIGNED
        if sign_extend_16(iVar34) > L_signed:           # 0x2a1c6/0x2a1c8
            pass  # -> SIGN_TEST
        else:
            L_unsigned = read_u16_LE(0xC61B8)            # 0x2a1ca  ld.hu UNSIGNED (mixed-signedness trap)
            if iVar34 >= -L_unsigned:                    # 0x2a1ce-0x2a1d2  (covers full |iVar34|<=L)
                iVar34 = 0
                goto RAMP_GAIN_SKIP_MUL                  # 0x2a1e4
        # SIGN_TEST @0x2a1d4
        prev = read_i16(gp_0x6b30)
        if iVar34 * prev > 0:                            # 0x2a1da-0x2a1e0, 16x16->32, no overflow
            pass  # PASS -> RAMP_GAIN
        else:
            iVar34 = 0
            goto RAMP_GAIN_SKIP_MUL
    # else: gp-0x6806 != 0 -> SKIP to RAMP_GAIN, iVar34 UNCHANGED (not zeroed!)
# else: cal != 1 -> SKIP to RAMP_GAIN, iVar34 UNCHANGED (not zeroed!)
RAMP_GAIN:                                                # 0x2a1e6
    iVar34 = sign_extend_16((iVar34 * ramp_gain_gp0x69b0) >> 15)
RAMP_GAIN_SKIP_MUL:                                       # 0x2a1ee (numerically identical since 0*x=0)
    ...
gp_0x6b30 = iVar34                                        # 0x2a206 — ONLY store to gp-0x6b30 in the image
```
Correction vs 2026-07-20 note: the SKIP path (cal!=1 or gp-0x6806!=0) leaves iVar34 **unmodified**, it does
not zero it — only the deadband/sign FAIL path zeroes. No behavioral difference (skipping the ramp-gain mul
on an already-zero value is a no-op), just a control-flow correction.

## Byte-read of both cals, LE, both premises for the flash-lineage check
`0xC61B8` (u16): stock/V53/V54/V55/V56 all `66 00` = 102. `0xC64A3` (u8): all `01` = 1. Neither has moved off
stock through V56. (`0xC62EA` read alongside as an offset-mapping sanity check: stock `40 01`=320, V53-V56
`00 00`=0 — matches the known V53 edit exactly, confirming plain-image file-offset == firmware address.)

## How to apply
Do not propose `0xC64A3->0` or `0xC61B8->0` for the vibration/damping investigation — retract if seen again.
Both are true no-ops for that purpose: Finding 1 says the gate doesn't fire; Finding 2 says it wouldn't matter
to the motor even if it did. If ever revisited, it would only be relevant to gp-0x6b38's UDS telemetry field
(same diagnostic record as gp-0x69ae/gp-0x4f60/gp-0x6a56, useful for [[v54-flashed-authority-measured]]-style
telemetry work) or to suppressing a plausibility DTC via the `FUN_0002b422`/`FUN_00025c32` voter chain — not
for steering feel.

## Related
[[reference_accord_steerstatus3_speed_gated_but_report_only]] — source of the FUN_0004e82e UDS-record ID.
[[reference_accord_gp6b98_aggregator_full_lane_inventory]] — the complete 9-lane list this finding checks against.
[[accord-low-speed-lockout-window-c62ea]] — the V53 cal edit (0xC62EA) that makes STATUS=3 unreachable.
[[reference_accord_fun2a30e_steerstatus_debounce_statemachine]] — the DEAD twin of this engage-ramp SM.

## Open / not chased this session
- `FUN_0001cba6` not decompiled (DTC-report inference is belief, not evidence).
- The IIR's raw-input physical identity: LERP indexed by `gp-0x6a34` over cal axis `tp+0x7710-0x7736`
  (0x2a080-0x2a174) — a different table from the `tp+0x7736-0x773e` one in the steerstatus3 memory despite
  overlapping addresses. Not needed for the routing conclusion.
- 6-byte extended-disp form not independently byte-scanned for gp-0x6806/-0x6b30/-0x6b38 (relied on
  search_instructions' positive counts, which is lower-risk than trusting a null result, but not full
  corroboration per kit policy).
