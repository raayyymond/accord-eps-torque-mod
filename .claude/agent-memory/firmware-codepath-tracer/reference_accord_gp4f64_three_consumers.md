---
name: reference-accord-gp4f64-three-consumers
description: gp-0x4f64 (torque governor) has THREE distinct consumers, not one — m_motor_torque_governor's speed-scaled clamp, FUN_00042af8's double-clamp (governor + separate static ±0x2000), and a diagnostic-override direct multiply in FUN_0006e09a/FUN_0006e140.
metadata:
  type: reference
---

# gp-0x4f64 governor — three consumers, verified 2026-07-17

Exhaustive `search_instructions("4f64")` scan of code.bin (185k instructions, V850:LE:32) found gp-0x4f64 (0xFEDF309C) read at 5 distinct sites across 4 different named/unnamed functions, plus 3 write sites in its producer `FUN_0007b022`. A prior request that assumed "gp-0x4f64 is applied as a flat ±4762 clamp in FUN_00042af8" was WRONG on two axes (see [[reference-accord-governor-gp0x184-chain]] for the "not flat" half). This file documents the "not one consumer" half.

## Consumer 1 — `m_motor_torque_governor` @ 0x453F0
```
0x453F0: ld.hu -0x4f64[gp],r8
0x453F4: mul r26,r8,r0          ; r8 = r26(speed_scale-labeled, UNVERIFIED — see governor-gp0x184-chain memory) * governor
0x453F8: sar 0xf,r8             ; bound = (governor * scale) >> 15
0x453FE: jarl 0x00049a90,lp     ; s_clamp_i32(gp-0x6b94, -bound, +bound)
```
Symmetric ±clamp on **gp-0x6b94** (a DIFFERENT variable from the shaper's), with the bound further scaled by `r26` on top of the already-adaptive governor. Feeds gp-0x6ace → m_post_governor_torque_comp_add → gp-0x6acc (shaper input). This is UPSTREAM of Consumer 2.

### ✅ RESOLVED 2026-07-19 — the r26 (and its downstream partner r28) Q15 factors are VERIFIED ≤ 0x8000 (unity), not assumed

Full decompile of `FUN_0004503c` (governor). The `r26`/`r28`-labeled Q15 multiplicands both trace to
the SAME literal seed:

```c
uVar10 = 0x8000;   // literal, right after the prologue — exactly unity Q15
```

This `uVar10` is then combined **only** via `FUN_00049a78` (= `min(a,b)`) and `FUN_00049a90` (=
`clamp`/median-of-3, see [[reference-accord-generic-math-helpers-49a5a-49a78-49a90]]) across an
unrolled 3-channel (6-element) redundant-sensor voting loop — each element either passes a sample
through a slew-limited clamp or folds it into the running `uVar10` via `min`. **No add or amplifying
multiply is ever applied to this seed on the path to either Q15 factor.** The bound-setter feeding the
`FUN_00049a90(gp-0x6b94, -bound, +bound)` clamp above, and the second-stage post-clamp scaler
(`iVar8 = (clamped_value * factor2) >> 15`, applied right after the call at `0x45402-0x4540a`), both
derive from this same MIN-only chain. After that, the result passes an asymmetric slew limiter with
sign-crossing reset (`0x45420-0x45458`) before landing in `gp-0x6ace` — a rate limiter cannot overshoot
its own target by construction.

**Consequence: `gp-0x6ace` cannot exceed the governor value (4762 nominal, lower under adaptive
reduction) through this chain.** This upgrades the prior "assumes the Q15 bank output is at most unity
— a MODEL DEFAULT, not a verified fact" caveat (raised when auditing the ±8192 sanitize-to-zero cliff
downstream in the shaper) to a verified structural fact. See
[[reference-accord-fun456a4-gate-no-hysteresis-and-index-identity]] for the full worked margin
(`4762 + 2560 = 7322 < 8192`) this enabled.

**[VERIFIED]** for the seed + MIN/clamp-only combination (every instruction on the call path was read).
**[INFERRED, high confidence]** that no branch I didn't hand-simulate individually could push a factor
above 0x8000 — I did not exhaustively symbolically execute all 6 loop iterations, but found no
add/multiply-up operator anywhere on this data path.

## Consumer 2 — `s_motor_torque_rate_shaper` (= FUN_00042af8) @ 0x43AE4
```
0x43AE4: ld.hu -0x4f64[gp],r10   ; governor read
0x43AE8-AFA: [sanity gate: governor zeroed if >=0x2801 — dead in practice, 4762<10241]
0x43AFE-0x43B0E: r14 = clamp(r12, -governor, +governor)   ; governor clamp on accumulated demand
0x43B0E-0x43B24: r21 = clamp(r14, -0x2000, +0x2000)        ; SEPARATE static hard clamp, immediately after
0x43B52: st.h r8,-0x6b98[gp]     ; DELIVERED torque write (r8=r21)
```
This IS a real symmetric ±governor clamp, confirmed down to the instruction — but it's the SECOND of two sequential clamps in the same function, not a single "±4762" operation. See [[reference-accord-shaper-fun42af8]] for the full clamp stack (7 stages) this sits inside.

## Consumer 3 — `FUN_0006e09a` @ 0x6E0F2 and `FUN_0006e140` @ 0x6E1CA (diagnostic/override path, NOT in the shaper chain)
Found only via exhaustive operand search — not reachable by following the normal shaper/governor call chain. Both are state-1 handlers of a 2-state dispatch table (function-pointer data at `0xBCB14`/`0xBCB18`; caller of that table NOT traced). Gated on a steady-state check: `delta = |gp-0x2944 - gp-0x2904| < cal(tp+0x7C22)=25` (live-read: bytes `19 00`):
```
0x6E0F2: ld.hu -0x4f64[gp],r10   ; governor
0x6E0F6: ld.h 0x7c3c[tp],r9      ; cal tp+0x7C3C = 1 (live-read: bytes 01 00)
0x6E100: mulh r9,r12             ; r12 = governor * 1
0x6E104: st.h r12,-0x6b98[gp]    ; DIRECT OVERWRITE of delivered torque = raw governor value
0x6E108: st.h r10,-0x4ce2[gp]    ; dual-path write, no cmp/bne mismatch-fault check (unlike every other lockstep pair in this codebase)
```
With cal=1, this directly writes the governor's raw value (nominal 4762) into gp-0x6b98, BYPASSING both the governor gate and the static ±0x2000 clamp from Consumer 2 entirely. State-0 of the same dispatch calls what look like DTC set/clear routines (`0x5a97c`, `0x6d026`). **INFERENCE (not confirmed):** reads like an EPS motor self-test/actuator-diagnostic routine (command a known fixed torque when the vehicle/column is still, to verify motor response), not a normal-drive path — but the caller of the `0xBCB14`/`0xBCB18` dispatch table was never traced, so reachability during normal LKAS operation is UNCONFIRMED. This is a live, unguarded (no lockstep-mismatch fault path) write to the delivered-torque variable — worth flagging if drivability anomalies ever look like a sudden fixed-torque command near-zero-motion.

## Producer recap (see [[reference-accord-governor-gp0x184-chain]] for full detail)
`FUN_0007b022`, 3 branches selected by `uVar26=*(byte*)(gp-0x4e5a)`, each write gated by a lockstep-shadow check against `gp-0x448a` (mismatch → `FUN_0006b9ee()` fault call). Branch 1 (steady-state LKAS) = `MIN(4762-fixed-cal, motor-electrical-rate LERP, energy/thermal budget)`.

## Related
[[reference-accord-governor-gp0x184-chain]] — producer chain + the speed-vs-motor-rate correction
[[reference-accord-shaper-fun42af8]] — Consumer 2's full 7-stage clamp stack
[[reference-accord-tva-downstream-chain]] — gp-0x6b98 downstream
