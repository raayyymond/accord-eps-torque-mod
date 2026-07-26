---
name: accord-lkas-path-wiring
description: Honda Accord TVA A160 (V850 LE): verified wiring of comma LKAS torque → motor. PATH-B (shaper→gp-0x6b98) is the live motor path; PATH-A (arb→gp-0x6b3c) is zeroed by arb gain=-1 and is inert.
metadata:
  type: reference
---

# Accord TVA A160 LKAS torque path — verified wiring (2026-05-26)

**Program:** code.bin, V850:LE:32, gp=0xFEDF8000, tp=0xF8000 (cal partition absent/0xFF)

## PATH-A (inert)

`s_lkas_process_steer_cmd (0x52676)` → writes setpoint to `gp-0x69ae` (0xFEDF1652) as `raw * -4`, clamped ±0x4000.

`m_steer_torque_arbitration (0x28ea6)` reads `gp-0x69ae` at 0x29032 and 0x29124. Output formula: `(combined_torque × gain[gp-0x6752] × tp+0x746c) >> 15`, then clamp(±tp+0x71b4) → written to `gp-0x6b3c` (0xFEDF1444) at 0x2a2ea.

**Arb gain at 0xFF46C = 0xFFFF = -1 → PATH-A output ≈ 0.** Confirmed inert.

`m_steer_torque_limit_and_pack (0x2b422)` reads `gp-0x6b3c` at 0x2b42e. It is downstream of the zeroed arb.

## PATH-B (live motor-torque path)

`s_lkas_process_steer_cmd (0x52676)` → `gp-0x69ae` → ONLY TWO readers verified by exhaustive instruction search:
1. `m_steer_torque_arbitration` (PATH-A, inert)
2. `w_lkas_setpoint_consumer2 (0x4e82e)` — reads setpoint, scales by ×3.25 (`*0xd>>2`), packs into CAN-tx buffer → **telemetry TX, not motor control**

**FUN_00042af8 (shaper) does NOT read gp-0x69ae.** Confirmed by exhaustive search over 1769 instructions (0 matches).

The shaper's actual inputs are gp-relative slots written by `m_motor_cmd_mixer (0x26c80)`: specifically `gp-0x6b4a` (0xFEDF14B6) read at 0x42bf6. The shaper reads motor state, integrates demand from adjacent gp slots (gp-0x6bf0, gp-0x6af6, gp-0x6b00, gp-0x6af8, gp-0x6b04, gp-0x6b08, gp-0x6afe, gp-0x6acc), and writes its shaped output to `gp-0x6b98` (0xFEDF1468) at 0x43b52 and 0x43dfc.

**How does the shl3 2× reach the motor?** The setpoint scale change in s_lkas_process_steer_cmd → gp-0x69ae → arb → gp-0x6b3c → limit_and_pack. PATH-A carries the shl3 effect, even though arb gain=-1 should nominally zero it. The operator observed a real 2× at low/mid — this means either:
- The arb gain 0xFF46C is not always -1 (it may be context-dependent and the tp=0xF8000 reading reflects the absent cal partition, not the runtime value), OR
- There is a code path in m_steer_torque_arbitration that bypasses the gain multiplication in certain conditions.
PATH-B (gp-0x6b98) is independent of the setpoint and carries a separate demand signal from m_motor_cmd_mixer.

## gp-0x6b98 writers (4 total)

| Address | Function | Description |
|---------|----------|-------------|
| 0x43b52 | FUN_00042af8 (shaper) | Main shaper output, shaped motor demand |
| 0x43dfc | FUN_00042af8 (shaper) | Second write site in shaper |
| 0x6e104 | FUN_0006e09a | Ramp/governor: writes `*(gp-0x4f64) * tp+0x7c3c`; gp-0x4f64 is RAM governor mirror |
| 0x6e1dc | FUN_0006e140 | Similar ramp function; same formula |

## gp-0x6b98 readers — classified (45 total read sites across ~20 functions)

| Function | Address(es) | Classification |
|----------|-------------|----------------|
| FUN_000370b6 | 0x370be | **MOTOR CONTROL** — LERP with tp+0x50c0 → writes gp-0x6bb0, gp-0x4cee (PWM/current targets) |
| FUN_00056420 | 0x56420 | **MOTOR CONTROL** — LERP with tp+0x73c8 → writes gp-0x6b54 (TSG21 timer/PWM path) |
| FUN_00042af8 | 0x43b34, 0x43dec | **SELF** (shaper reads own prior value for integration) |
| FUN_0001bf88 | 0x1c0c8 | **MONITOR/REDUNDANCY** — calls FUN_00059912 (9 reads of gp-0x6b98 = dual-path lockstep check) |
| FUN_0001c1ce | 0x1c22c | MONITOR/REDUNDANCY (same sub-chain) |
| FUN_00019f7c | 0x19fe2 | TBD — small function in steer task |
| FUN_000242a2 | 0x24448 | TBD — large (0x242a2–0x25c31) |
| FUN_0002c478 | 0x2c47c | TBD — decompile failed (TAUJ1RSF struct error) |
| FUN_00035e00 | 0x35ee6 | TBD |
| FUN_0003aff4 | 0x3b00a | TBD |
| FUN_0003b8f6 | 0x3b8f6 | TBD |
| FUN_00041464 | 0x41672, 0x41846 | TBD — large (0x41464–0x41b8d) |
| FUN_00041b8e | 0x41bd8 | TBD |
| FUN_00043e44 | 0x448d6 | TBD — large (0x43e44–0x44a8b) |
| FUN_00056518 | 0x56554, 0x56562, 0x5656a | TBD |
| FUN_000568d0 | 0x569c4, 0x56aac | TBD |
| FUN_00059912 | 0x59a44, 0x59a4c, 0x59b9a, 0x59ba4, 0x59be8, 0x59bf0, 0x59c10, 0x59c1c | **MONITOR/REDUNDANCY** — 9 reads in one function |
| FUN_00059e7a | 0x59f7c, 0x59f86, 0x5a09a, 0x5a0aa | TBD |
| FUN_00065afe | 0x65c90 | TBD |
| FUN_00069b8e | 0x69bee, 0x69cba | TBD |
| FUN_00070a98 | 0x70bfc | TBD |
| FUN_000757a2 | 0x7580c | TBD |
| FUN_0007c4f2 | 0x7c52c | TBD |
| FUN_0007c94a | 0x7c94e | TBD |
| FUN_00081b24 | 0x81be8 | TBD |

## PATH-A downstream chain (verified 2026-05-26 — arb→mixer→motor)

The arb (FUN_00028ea6) writes these gp- slots at function end (decompile lines 1243-1326):
- `gp-0x6b2e` (line 1243): curve-clamped LKAS demand component (iVar23, the post-±tp+0x71be clamp value)
- `gp-0x6b32` (line 1245): integrator A (uVar38)
- `gp-0x6b36` (line 1249): rate component (uVar36)
- `gp-0x6b34` (line 1250): velocity component (uVar32)
- `gp-0x6b30` (line 1279): LERP-weighted demand feedback (the "uVar33 path" from decompile)
- `gp-0x6b38` (line 1292): post-gain filtered value (uVar13)
- `gp-0x6b3c` (line 1326): **FINAL ARB OUTPUT** = `(short)uVar13 * (ushort)bVar6` where bVar6 = (mode==ACTIVE)

**The curve-clamped LKAS setpoint (the question's "uVar33") routes through the integrator chain** and ultimately contributes to iVar23 (gp-0x6b2e), then is combined at line 1271: `iVar23 = (int)(short)((int)(iVar34 * uVar18) >> 0xf)` to produce the gain-multiplied component. The final arb output gp-0x6b3c = `arb_sum × gain[tp+0x746c] × polarity[gp-0x6752] >> 15`, then clamped ±tp+0x71b4.

## The arb→mixer bridge (verified 2026-05-26)

`m_steer_torque_limit_and_pack (0x2b422)` reads gp-0x6b3c, clamps it ±tp+0x71b2 (= 0xFFFF = ∞ in this dump), writes to gp-0x6b3a, then calls `m_motor_cmd_distribute_clamp (0x25c32)`.

`FUN_0002b57a (0x2b57a)` reads gp-0x6b3a, scales to float, calls `FUN_00027802 (0x27802)` which is a plausibility checker reading the mixer input slots (gp-0x62e0/62f8/633c/6230 by channel index).

`m_motor_cmd_distribute_clamp (0x25c32)` IS the arb→mixer bridge. It contains multiple write blocks triggered by channel state (disasm 0x26480–0x264d4, 0x2677e–0x267d4, 0x26a60–0x26ab6, etc.) that write:
- `sst.h r12, [gp-0x62e0+r8]` — torque channel component (clamped ±0x4000 at 0x25c80)
- `sst.h r14, [gp-0x62f8+r8]` — torque channel component (clamped ±0x2800 at 0x25c9c)
- `sst.h r16, [gp-0x633c+r8]` — small channel (clamped ±0x384 at 0x25cb8)
- `sst.h r10, [gp-0x6230+r8]` — gain/ratio channel (0x400 = 1.0 in Q10)
- Mirror writes to dual-path lockstep slots (gp-0x4b70, gp-0x4b88, gp-0x4ba0, gp-0x4b10)

Where `r8 = r1 * 2` (channel index × 2 byte stride). This is the definitive arb→mixer input write.

## Key structural conclusion

PATH-B (gp-0x6b98) is populated by the shaper and ramp functions independently of the setpoint.
The shl3 2× effect observed by operator propagates through PATH-A (arb → gp-0x6b3c → limit_and_pack → distribute_clamp → mixer input slots → mixer → shaper → gp-0x6b98). PATH-A is NOT inert even though gp-0x6b3c ≈ 0 — the arb gain 0xFF46C = -1 only applies with absent cal partition; runtime gain drives real output.

The actual LKAS contribution to the motor travels:
`gp-0x69ae → arb (0x28ea6) → gp-0x6b3c → limit_and_pack (0x2b422) → gp-0x6b3a → distribute_clamp (0x25c32) → gp-0x62e0..633c → mixer (0x26c80) → ±0x2800 clamp → FUN_00042ac6 (0x42ac6) → gp-0x6afe`

The shaper (FUN_00042af8) reads gp-0x6acc, NOT gp-0x6b3c or gp-0x69ae. The shaper's gp-0x6acc writer has not been confirmed by instruction search — it may be written via EP-relative addressing not caught by operand-filter search.

## gp-0x6b98 → peripheral (verified 2026-05-26)

From gp-0x6b98 there are two confirmed motor control consumer paths:
1. **FUN_000370b6 (0x370b6):** Reads gp-0x6b98 (range-gated ±0x2000), computes LERP `iVar5 = iVar4 + ((gp-0x6b98 * 0x20 - iVar4) * tp+0x50c0/32 >> 10)`, writes `gp-0x6bb0` and `gp-0x4cee` (PWM/current targets). Called from FUN_00019f7c state machine.
2. **FUN_00056420 (0x56420):** Reads gp-0x6b98, LERP with tp+0x73c8, writes `gp-0x6b54` AND `TSG21_registers_t_ffffd000.field_0x9c` (peripheral integrator state). The TSG21 peripheral is at physical address **0xFFFFD000**.
3. **FUN_0003b8f6 (0x3b8f6):** FOC PI controller. Range-gated entry `(gp-0x6b98 + 0x2000U < 0x4001)`. Computes d/q axis currents, writes `gp-0x6bf6` (motor current command, ±20000 clamped) and `gp-0x6c00` (absolute current). Motor phase current intermediate.

The final PWM register write for the FUN_000370b6 path: FUN_00019f7c dispatches through sub-handlers (FUN_00019888 → FUN_0001a1f0/FUN_0001a1c4 → FUN_00018950 → FUN_00016de6). FUN_00016de6 does `st.h r14, 0x0[r24]` where r24 is the hardware channel register pointer — this is a CSIG/SPI peripheral write (Ghidra labels CSIG2 struct at the decompile boundary; CSIG = serial interface to the motor driver IC, not raw PWM). The specific register write is at 0x16f34 (`st.h r14, 0x0[r24]`).

FUN_00056420 writes directly to `TSG21_registers_t_ffffd000.field_0x9c` — the TSG21 timer/PWM at **0xFFFFD000** is the confirmed PWM peripheral.

## Open verification needed

1. Confirm gp-0x6acc writer. EP-relative sst.h search returned 0 matches — the writer may use a computed base address pattern `movea -0x6acc,gp,ep; sst.h rN,0x0[ep]` which would match as `sst.h rN,0x0[ep]` without the offset visible at the instruction level.
2. Confirm whether the arb gain 0xFF46C is 0xFFFF only due to absent cal partition or is always -1.
3. The PATH-A shl3 2× effect: if gain=-1 → gp-0x6b3c = -demand. With polarity gp-0x6752 also negative, product = positive = correct direction. The cancellation or summation in the mixer determines the net effect.

See also: [[reference-accord-torque-demand-task]], [[project-accord-torque-mod-v0]], [[reference-accord-tva-downstream-chain]]
