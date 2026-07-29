---
name: reference-accord-gp6bbe-rate-error-speed-scheduled-lane
description: EXTENDS reference_accord_gp6b98_aggregator_full_lane_inventory.md's gp-0x6bbe ("boost") row -- FUN_00034a72 is not just a torque EMA, it uses raw steering-angle RATE (gp-0x6a56) as an unfiltered error term against an internal state machine, gated by 3+ separate speed-indexed LERP tables and a 4-state debounce FSM. Best candidate in the whole aggregator for an RTC/angle-rate-adjacent term. 🛑 CONFLICTS with reference_accord_aggregator_domain_audit_no_angle_lane_found.md's same-day "no angle/angle-rate input in any of the 11 lanes" verdict for THIS specific lane -- see Reconciliation section, disasm-verified in favor of THIS file. Sibling lane gp-0x6bd0 ("damping", FUN_00034350) does NOT read angle rate -- confirmed asymmetry, consistent with both sessions.
metadata:
  type: reference
---

# gp-0x6bbe ("boost") is a rate-error + multi-speed-LERP compound term, not a simple torque EMA (2026-07-29/30)

## 🛑 RECONCILIATION — conflicts with a same-day sibling memory, resolved in favor of this file

`reference_accord_aggregator_domain_audit_no_angle_lane_found.md` (same day, different session) traced
this SAME function (`FUN_00034a72`) and its domain table lists gp-0x6bbe's "Primary input" as `gp-0x4f60`,
TORQUE only, and its headline says **"No angle or angle-rate input found in any of the 11 lanes."** That
session's own writeup does not mention `gp-0x6a56`, the 4-state FSM (`gp-0x682e`), or the Y3/Y5
speed-indexed LERPs documented below — evidence it characterized the function's DOMINANT path (the outer
torque EMA) without unwinding this deeper tail portion of a 625-instruction function.

**This file's `gp-0x6a56` finding is independently disasm-confirmed, not a grep artifact**:
`search_instructions` attributes two real reads to `FUN_00034a72` by Ghidra's own function-boundary logic
(`0x34ab8 ld.h -0x6a56[gp],r13` and `0x34e8e ld.h -0x6a56[gp],r6` — TWO DISTINCT physical instructions, not
one hit double-counted), and the raw `decompile_function` JSON (captured directly from the tool, not
reconstructed) shows `gp-0x6a56` read at function entry (`sVar23 = *(short*)(gp-0x6a56)`) AND again deep in
the tail (`if (sVar23+12000U<0x5dc1) iVar30 = gp-0x6a56;` then `iVar13 = iVar13 - iVar30`, i.e. an explicit
subtraction of the FSM's state-machine result minus raw angle rate). `gp-0x6a56`'s identity as
steering-angle-rate is independently ground-truthed via the CAN 0x14A/0x18F packers (companion memory
`reference_accord_can_angle_producer_and_no_angle_correction.md`), so this is not a mislabeled variable.

**Verdict: the domain-audit memory's "no angle/angle-rate input" conclusion is WRONG for gp-0x6bbe
specifically** — it should be corrected to "torque-dominant, but ALSO reads raw angle rate as a
subtracted error term deep in its tail (see this file)." The domain audit's conclusions for the OTHER 10
lanes are untouched by this correction (not re-verified by this session). Flagging to team-lead/operator
for adjudication rather than silently editing the sibling file, per this kit's memory-correction
convention — but recording the correction here since the evidence is unambiguous.

Traced for team-lead's return-to-center / angle-loop investigation. Entry point: enumerating every
control-path reader of `gp-0x6a56` (steering angle rate, see companion memory
`reference_accord_can_angle_producer_and_no_angle_correction.md`). `code.bin` stock, GhidraMCP only,
gp=0xFEDF8000, tp=0xBF000.

## Why this matters
`reference_accord_gp6b98_aggregator_full_lane_inventory.md` already establishes `gp-0x6bbe` as ONE OF THE
NINE lanes summed into the final motor command `gp-0x6b98` (via aggregator `FUN_0003aa2c`), confirmed LIVE
(not gated dead), attenuation "-1.2dB @ 20Hz" from its outermost torque EMA (coeff `tp+0x7372`=`0xC6372`,
fc≈35.6Hz), and flagged in `docs/STATE.md` as **"candidate #2"** needing its own GATE-2 pass — described
there only as "base power steering." This session's full decompile of its producer, `FUN_00034a72`, adds
substantial structure the prior -1.2dB characterization didn't capture: the function also consumes RAW,
UNFILTERED angle rate as an error signal, and is scheduled by at least three independent speed-indexed
LERP tables plus a 4-state debounce FSM. **This reframes `gp-0x6bbe` from "a generic torque-based boost
gain" to "the aggregator's most speed-scheduled, rate-referencing lane" — structurally the best candidate
in this firmware for an active-damping / RTC-adjacent mechanism.**

## Confirmed structure of `FUN_00034a72` (full decompile this session)

```c
sVar23 = gp-0x6a56;                                  // ANGLE RATE, raw, no filter applied to it directly
uVar17 = mode byte (gp-0x674e-family, per-variant LERP-table selector)
torque = gp-0x4f60;                                  // Sensor-B driver column torque, already on record
iVar29 = gp-0x6df4 + ((torque*32 - gp-0x6df4) * cal(tp+0x7372) >> 10);   // 1-pole EMA on torque, state gp-0x6df4
iVar21 = polarity * (polarity valid check)
sVar7  = mode-selected cal gain (table &DAT_000ca324[mode])
iVar27 = clamp(((gp-0x6c2e * cal(tp+0x7370)) >> 5) * iVar21 + iVar29 >> 5, +-0x6400)   // combine, ±25600 clamp

// torque-magnitude-vs-existing-signal blend/select (feature flag tp+0x7499), producing a |combine| index
// -> LERP1 (table &DAT_000ca4f4[mode], indexed by |combine|) -> Y1
// Y1 blended with prior state gp-0x69bc via a per-mode EMA gain (table &PTR_DAT_000ca06c[mode])

// A SEPARATE 4-state FSM (state byte gp-0x682e, debounce counter gp-0x68c8 vs cal tp+0x74d1*10,
// gated by assist-substate gp-0x67fe in {1,2} AND converge/plausible flag gp-0x67f4==1 AND
// gp-0x6a5e(avg voted speed) < 0x7d01, AND two UNRESOLVED bound checks on gp-0x6a10/gp-0x6a02 vs
// 10000/20000 -- see Open Questions) selects among per-state LERP tables (PTR_LAB_000ca154[mode] etc.)
// and produces iVar13.

iVar30 = iVar13;
if (angle_rate in range [-12000,12000]) {   // tautological -- rate is already clamped there
    iVar30 = gp-0x6a56;                      // <-- FSM RESULT OVERRIDDEN BY RAW ANGLE RATE
}
iVar13 = clamp(iVar13 - iVar30, -12000, +12000);   // <-- an "error" = (FSM/state result) MINUS (raw rate)

// -> LERP3 (table PTR_LAB_000ca154[mode], indexed by gp-0x6a5e = AVG VOTED SPEED) -> Y3 (speed-scheduled gain)
iVar27 = (sVar7 * iVar13 >> 7) * Y3;                 // rate-error * mode-gain * SPEED-SCHEDULED gain
// combined sign-consistently with a mode cal (&PTR_DAT_000c7a58[mode]) -> uVar17

// -> LERP4 (table DAT_000ca23c[mode], indexed by |combine|) -> Y4, blended with gp-0x69ba via per-mode gain
// -> combined with gp-0x6988 (clamped 0..1024) and gp-0x6a62 (MAX VOTED SPEED, a DIFFERENT speed signal)
// -> if MAX speed < 32000: LERP5 (table PTR_DAT_000c7970[mode], indexed by gp-0x6a62) -> Y5 (2nd speed-scheduled gain)
//    else: fallback constant cal(tp+0x715a)
// FINAL: gp-0x6bbe = sign-consistent MIN(|iVar21_final|, |Y5|)   -- Y5 acts as a ceiling/limiter
```

**Key finding: the raw angle-RATE (`gp-0x6a56`) is injected UNFILTERED as one side of a subtraction
against an internal state/FSM result, and that error is then scaled by TWO independent speed-indexed LERP
tables** (one on `gp-0x6a5e` average voted speed, one on `gp-0x6a62` MAX voted speed — both already
documented as voted-vehicle-speed signals in `reference_accord_gp6a5e_is_voted_vehicle_speed.md`) before
reaching the aggregator lane. No EMA/IIR is applied to `gp-0x6a56` itself anywhere in this function — only
the TORQUE input gets the outer EMA that the prior -1.2dB bandwidth figure characterized. **The rate path's
own frequency response is therefore NOT yet characterized and could be materially wider-band than -1.2dB.**

## Asymmetry with the sibling "damping" lane (`gp-0x6bd0`)

`FUN_00034350` (the `gp-0x6bd0` "damping" lane, structurally parallel — same EMA-coefficient pattern
`tp+0x736e`=`0xC636E`, same ±2048 aggregator bound, per the existing inventory memory) does **NOT** appear
anywhere in the `gp-0x6a56` reader list (verified via `search_instructions` across all 183,429 analyzed
instructions — `FUN_00034350` is absent). **Only `gp-0x6bbe`/`FUN_00034a72` incorporates angle rate; the
"damping" lane is torque-only**, as its existing characterization already implies. Do not conflate the two
lanes' mechanisms going forward.

## What this does NOT resolve

1. **Whether this is genuinely "return-to-center"** in the sense of driving absolute ANGLE toward zero —
   it is not; the input is angle RATE, not angle. It is best described as an "active damping / rate
   compensation" term (the OTHER category the team-lead's brief asked to be reported separately from
   RTC-proportional-on-angle), not RTC proper. No proportional-on-absolute-angle term was found feeding
   any aggregator lane in this session (the raw angle accumulator `gp-0x6cc4`'s consumers are
   consistency/deadband gates per the existing `reference_accord_gp6cc4_tracking_pipeline.md` sweep, not
   torque contributors) — but that absence is corroborating, not independently re-proven exhaustive this
   session.
2. **The driver-override gate for THIS lane is unresolved.** The FSM's enable condition includes bound
   checks against `gp-0x6a10` and `gp-0x6a02` (thresholds 10000/20000) whose physical identity was not
   determined this session — both are widely read (12+ functions including the torque-sensor plausibility
   voter `FUN_00041eec`, and are WRITTEN-TO-ZERO conditionally in `FUN_0003e760`/`FUN_0003fc16`, suggesting
   sample-age/watchdog counters rather than raw torque, but this is NOT confirmed). **This is the single
   most promising next hop for the team-lead's item 5 (driver-override gate) — if either resolves to a
   driver-torque magnitude, this lane has a directly testable override mechanism.**
3. **Phase/gain at 20-25Hz for the rate path specifically** — not computed. The existing -1.2dB figure
   applies to the torque-EMA path only; the rate-error path bypasses that EMA entirely.
4. `gp-0x6c2e`, `gp-0x69bc`, `gp-0x6986`, `gp-0x69ba` — auxiliary quantities in the combine chain, not
   independently identified.

## Related
[[reference_accord_gp6b98_aggregator_full_lane_inventory]] — the ORIGINAL lane table this extends (gp-0x6bbe
row); superseded by [[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]] for the 11-lane count,
sign character (boost is SAME-SIGNED/reinforcing per that file, consistent with an "active damping" framing
being incomplete — it may be closer to a rate-tracking positive-feedback term), and the FUN_00022ca0 task-rate
open item (decisive for this lane's real dB — 1kHz vs ~100Hz assist-shaping task, unresolved by either session).
[[reference_accord_aggregator_domain_audit_no_angle_lane_found]] — the CONFLICTING same-day domain audit,
reconciled above.
[[reference_accord_can_angle_producer_and_no_angle_correction]] — the angle/rate producer chain this
consumer sits downstream of.
[[reference_accord_fun34350_damping_term_live_and_gated]] — the sibling lane, confirmed NOT to read angle rate
(consistent across both this session and the domain audit).
[[reference_accord_gp6a5e_is_voted_vehicle_speed]] — identity of the two speed signals (`gp-0x6a5e` avg,
`gp-0x6a62` max) this lane's two speed-indexed LERPs key off.
