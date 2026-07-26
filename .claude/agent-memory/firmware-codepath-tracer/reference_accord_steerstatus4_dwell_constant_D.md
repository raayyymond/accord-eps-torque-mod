---
name: reference-accord-steerstatus4-dwell-constant-D
description: Found D, the STEER_STATUS=4 dwell/hold count, in the inlined debounce SM in FUN_00028ea6 (m_steer_torque_arbitration). D = cal 0xC64DF = 100, loaded into the SAME counter gp-0x6757 that runs the already-known 5-cycle onset debounce (cal 0xC64E2=5, reused as the dwell's release-check floor). D=100 maps the telemetry-measured 100ms dwell to a ~1kHz control task tick, corroborating the OSTM0-based estimate independently.
metadata:
  type: reference
---

Traced 2026-07-21 for team-lead's cleanest-discriminator task: find D, the dwell/hold count for how many
cycles `STEER_STATUS` (`gp-0x6807`) remains at 4 once set, in the LIVE inlined debounce logic inside
`FUN_00028ea6` (`m_steer_torque_arbitration`) — NOT the already-known 5-cycle onset debounce
(`0xC64E2`=5). Full disassembly of `0x29140-0x29329` (the whole inlined SM block).

## D found: cal `0xC64DF` = 100 [VERIFIED, byte read]

`FUN_00028ea6`'s debounce counter `gp-0x6757` is genuinely **dual-purpose**, confirmed by tracing every
site that reads or writes it in this block:

**Onset phase** (already known, cited here only as load-bearing context): seeded to `-cal(0xC64E2)=-5`
on entry/reset (`0x29144: ld.bu 0x74e2,tp,r24` then `subr r0,r24` at several bail sites, e.g. `0x29168`,
`0x29184`, `0x2919c`), counts UP by 1 each cycle the torque/rate condition holds (`0x29276: add 0x1,r12`),
checked at `0x2923c: cmp r0,r12; bgt 0x2929c` (routes to dwell-mode once positive) and
`0x2927a: cmp r0,r12; bge 0x29288` (fires the transition once the count reaches 0, i.e. after 5 cycles).

**The transition — where D enters** [VERIFIED, `0x29288-0x2929a`]:
```
0x29288: ld.bu 0x74df,tp,r10    ; r10 = cal 0xC64DF
0x2928c: mov 0x4,r8
0x2928e: st.b r8,-0x6807,gp      ; STEER_STATUS = 4
0x29292: st.b r0,-0x6758,gp      ; DTC-0x49 counter reset (matches V37's known interlock)
0x29296: st.b r10,-0x6757,gp     ; gp-0x6757 = cal(0xC64DF) = 100   <-- RELOAD, not a fresh seed
```
The SAME thing happens at the function's second `STEER_STATUS=4` site (`0x292a8-0x292ae`, reached from
the dwell-decrement path itself — see below), confirming this is the single reload value for entering
state 4 from either the onset path or a mid-dwell re-entry.

**Dwell/countdown phase** [VERIFIED, `0x2923c` re-entry + `0x2929c-0x292b6`]: on every subsequent call
while `gp-0x6757 > 0`, the function branches to `0x2929c` instead of the onset-check block:
```
0x2929c: mov r24,r6              ; r6 = cal(0xC64E2) = 5 (the SAME cal, reused as the dwell floor)
0x292a0: cmp r6,r12 ; ble 0x292b8  ; while counter > 5: keep decrementing
0x292a4: addi -0x1,r12,r15
0x292a8: st.b r15,-0x6757,gp      ; gp-0x6757 -= 1
0x292ac: mov 0x4,r13
0x292ae: st.b r13,-0x6807,gp      ; STEER_STATUS = 4  (re-asserted every dwell cycle)
0x292b2: st.b r0,-0x6758,gp       ; DTC-0x49 counter held at 0 throughout the dwell
```
**`STEER_STATUS` is locked at 4 for every cycle the down-counter runs from 100 down to 5** — a
**guaranteed 95-cycle floor**, independent of any sensor condition, confirmed by the unconditional
decrement-and-reassert loop above.

**Release phase** [VERIFIED, `0x292b8-0x29322`]: once `gp-0x6757 <= 5`, the function switches to
checking whether torque (`gp-0x682f`) has fallen back below a release threshold (`cal 0xC64B5`) and rate
below `0xC61C0`=1600 (plus the same combined-tier checks as the onset side, `0xC64B7/0xC61C2/0xC64B6/
0xC61C4`). **If the condition is still active**, `gp-0x6757` is reset back to `cal(0xC64E2)`=5 unnegated
and `STEER_STATUS` stays 4 another cycle (`0x29314-0x2931e`) — a re-arm, not further decrement. **If the
condition has released**, it keeps decrementing (`0x292f0: add -0x1,r12`) until it reaches 0, at which
point `STEER_STATUS` finally reverts away from 4 (`0x292f8: st.b r10,-0x6807,gp`, r10 not 4) and
`gp-0x6757` is reseeded to `-cal(0xC64E2)` for the next onset cycle.

## What this means for D

**D, in the strict "guaranteed, condition-independent" sense = 100 - 5 = 95 cycles** (the unconditional
decrement-and-reassert loop, `0x292a0-0x292b6`, runs exactly this many times before ANY release check is
even possible). **D, as the raw calibration constant your formula names, is `cal 0xC64DF = 100`.**

I'd use **D=100** for your `tick = D/0.100s` formula as written — it's the literal reload value, and the
extra ~5-cycle release-check tail (variable, condition-dependent) is the natural explanation for the
telemetry's own scatter: **23/29 events landed at exactly 10 CAN frames (the dominant, condition-
independent 95-100-cycle lock), and the other 6/29 presumably ran a few cycles longer while the release
condition (torque/rate falling back below `0xC64B5`/`0xC61C0`) was still being satisfied cycle-by-cycle**
— that scatter pattern is a structural prediction of the code above, not just a coincidence, and is worth
checking against the 6 outlier events' exact frame counts if the telemetry data is handy (expect ~10-11
frames, not a wildly different number, since the tail is a handful of cycles, not a second regime).

## Resulting tick-rate answer

**D=100 cycles / measured 100.00ms dwell = 1000 Hz — the control task runs at ~1kHz, not 100Hz.**

This is my SECOND independent corroboration of ~1kHz this session (the first being the OSTM0 reload
[[reference-accord-ostm0-master-tick-rate-derivation]], which gave ~1006Hz via an 80MHz clock
plausibility argument, not a traced clock tree). This route is much cleaner: it doesn't touch the clock
tree question at all, and ties a **firmware-verified cycle count directly to a telemetry-measured wall-
clock duration** in the control path itself (not the CAN comms path), exactly as you specified. Two
independently-reasoned routes now agree on ~1kHz.

**Caveat, stated plainly**: I did not re-verify that `FUN_00028ea6`'s call rate to itself IS the "control
task tick" the phase-lag analysis assumed (i.e., that this function runs once per control-task cycle,
not decimated or state-gated the way `FUN_00041464`/`FUN_00041eec` turned out to be). Given
`m_steer_torque_arbitration` is the arbitration function itself — the thing computing the delivered LKAS
command every cycle by construction — this is very likely true, but I'm flagging it as an assumption
carried over, not independently re-confirmed this session.

## Related
[[reference-accord-ostm0-master-tick-rate-derivation]] — the other independent ~1kHz estimate this session
[[reference-accord-fun41464-sign-filter-phase-response]] — the phase analysis this rate answer resolves
[[reference-accord-gp6a5e-voter-bandwidth-insufficient-for-21hz]] — the magnitude analysis, rate-robust either way
