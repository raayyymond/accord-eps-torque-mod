---
name: reference-accord-lerp3-gp3574-chain
description: "Full upstream chain of gp-0x3574 in Accord EPS — LERP1/2/3 tables, Y-table modulation, IIR constants, runtime RAM layout. ⚠ 2026-06-03 CORRECTIONS: (1) gp-0x3574 is ONE ARM of the shaper wall max gp-0x6af6 = max(dir_corridor[0x774e], THIS gp-0x3574 envelope, boost[0x7760 = steering ANGULAR-RATE LERP]) × polarity (see [[reference-accord-corridor-lockstep]]). (2) gp-0x3574 is NOT 'driver-column-torque' (driver torque = gp-0x69ca, a different node — that label, which leaked into other memories, is REFUTED). (3) OUTPUT RANGE [evidence, FUN_000352b4 decomp]: LERP3 result is HARD-CAPPED at 0x3000=12288, so gp-0x3574>>8 (natural arm value) ∈ [−12288,+12288]; typical ~512–2048 = the LERP1 width band when the dynamic gp-0x6444 base is small. So the IIR arm can far exceed the ±1024/±2048 corridor and dominate the wall when active; the corridor only sets the FLOOR when IIR+boost are both small. (4) ⚠ INPUT IDENTITY CONTESTED: the LERP3 index gp-0x4f60 (clamped ±gp-0x4f54 then ±0x6400) is called column/motor ANGULAR VELOCITY by this memory + override_snap[STRONG], but rate-limited LKAS COMMAND by 2 tracers (via gp-0x6b50, an INDIRECT-write buffer not yet walked). UNRESOLVED — resolve by walking gp-0x6b50's writer. Either way NOT driver torque. Boost arm gp-0x6ac2 = |IIR-smoothed angular rate gp-0x4f50| ∈[0,13000] → LERP 0xC6760 out ∈[0,2048] (saturates at rate>1100)."
metadata:
  type: reference
---

# gp-0x3574 upstream chain — Accord EPS s_motor_torque_rate_shaper (0x42af8)

`gp-0x3574` = upper envelope bound (×256 stored scale).  
Written at `0x42dcc`. Read out at `0x43136` as `sar 0x8, r11` → one arm of the wall `gp-0x6af6`.

## ⚠ 2026-06-03 corrections (role, range, contested input)

- **Role:** `gp-0x3574` is **one arm of the shaper wall** `gp-0x6af6 = max(dir_corridor[cal 0x774e, ±1024],
  THIS envelope, boost[cal 0x7760 = steering ANGULAR-RATE LERP, 0..2048]) × polarity`. The wall is
  cross-checked int↔float by both consistency monitors. Full model: [[reference-accord-corridor-lockstep]].
- **NOT driver torque:** the "driver-column-torque IIR" label that leaked into other memories is **REFUTED**.
  Driver column torque is `gp-0x69ca` (a separate node, used by the override comp term). This arm's input is
  velocity-or-command, never the torque sensor.
- **Output range [V]:** the LERP3 result is **hard-capped at `0x3000` = 12288** (`FUN_000352b4` decomp:
  `(ushort)(0x2fff < uVar26) * 0x3000`). So the natural arm value `gp-0x3574 >> 8` ∈ **[−12288, +12288]**;
  typical magnitude **~512–2048** (the LERP1 width band) when the dynamic `gp-0x6444` base is small. ⇒ the
  IIR arm can far exceed the corridor (±1024 stock / ±2048 V29) and dominate the wall when active; the
  corridor only sets the floor in the quiet regime (IIR + boost both small).
- **⚠ Input identity CONTESTED (unresolved):** the LERP3 index is `gp-0x4f60` (clamped `±gp-0x4f54`, then the
  shaper clamps to `±0x6400`). This memory + `override_snap` ([STRONG]) call it **column/motor angular
  velocity**; two 2026-06-03 tracers call it **rate-limited LKAS command** (sourced from `gp-0x6b50`, written
  by an *indirect store not yet walked*). Resolve by walking `gp-0x6b50`'s writer. (LERP1's separate input
  `gp-0x6a28` is the envelope-width signal, sets 2048↔512.)

## Chain overview

```
gp-0x6a28 → [LERP1] → r25
r22 (vel) → [LERP2] → r8 = 1024 (FLAT)

y_shift = (r8 × r25) >> 10 = r25   (LERP2 is identity)

r22 (vel) → [LERP3: X=gp-0x642e, Y=gp-0x6444+y_shift] → lerp3_out
            → [IIR α=10] → gp-0x3574
```

## LERP1 (flash, 0x42b42)

- Cal address: `tp+0x7770` = `0xC6770`
- Count: 7
- X = `[0, 576, 640, 12800, 13440, 14080, 14720]` (unsigned u16)
- Y = `[2048, 2048, 512, 512, 512, 512, 512]` (unsigned u16)
- Behavior: **step-down at input 576–640** from 2048 → 512. Flat at both ends.
- Input `gp-0x6a28`: unsigned motion/assist magnitude signal.

## LERP2 (flash, 0x42c50) — always 1024

- Cal address: `tp+0x79E8` = `0xC69E8`
- Count: 7
- X = `[-7168, -6144, -5120, 0, 5120, 6144, 7168]` (signed s16)
- Y = `[1024, 1024, 1024, 1024, 1024, 1024, 1024]` (FLAT)
- **LERP2 is a unity gain pass-through — output is always 1024.**
- Consequence: `y_shift = (1024 × LERP1) >> 10 = LERP1`. LERP2 contributes nothing.

## Y-table modulation (0x42cb8–0x42cc4)

`y_shift = lerp1_out` (after LERP2 identity simplification)  
LERP3 effective Y[i] = `gp-0x6444[i] + y_shift`  
→ LERP1 output **additively shifts the entire LERP3 Y curve** each cycle.  
→ High LERP1 (2048) = wide envelope; Low LERP1 (512) = tight envelope.

## LERP3 (runtime RAM, 0x42d38)

- Input: `r22` (column velocity, signed Q10)
- **Count halfword**: `gp-0x6430` (1 halfword = 9, for a 10-point table)
  - NOTE: `gp-0x6430` is a SINGLE count field, NOT a 10-element X array.
  - `FUN_000389ec` at `0x38fd0` zero-initializes this single halfword.
- **X breakpoints**: `gp-0x642e`..`gp-0x641c` (10 halfwords, runtime)
  - Written by `FUN_000389ec` init loop at `0x39018`..`0x390d6` (10 iterations) from `gp-0x3714` buffer.
  - Spacing calibration: `tp+0x71E4` = `0xC61E4` = 3072 (used as X step).
- **Y base values**: `gp-0x6444` (10 halfwords, runtime)
  - Computed each cycle by `FUN_000352b4` (float arithmetic from X values).
  - `FUN_000389ec` at `0x38fee` zero-initializes `gp-0x6444` as a single halfword.
- **Actual X and Y values are not readable from static flash analysis alone.**

## IIR smoother (0x42dac–0x42dc8)

- Alpha: `tp+0x7418` = `0xC6418` = **10**
- Q10 division: `state += (target×256 - state) × 10 >> 10`
- Anti-overshoot clamp: `if state > target×256: state = target×256`
- τ = 1024/10 = **102.4 cycles = 102.4 ms @ 1000 Hz**
- `gp-0x3574` stores the state at **×256 scale**; read back via `sar 8`.

## Plot

`analysis-2020accord/studies/models/_lerp3_gp3574_chain.py` (script) / `_lerp3_gp3574_chain.png` (output)  
4 panels: LERP1 curve (actual data), LERP2 flat line (actual data), LERP3 Y-modulation demo (representative X + 3 LERP1 levels), IIR step response.

## ⊕ 2026-06-03 — INPUT IDENTITY RESOLVED to COLUMN VELOCITY (by road data)

The contested LERP3 index (column velocity vs rate-limited LKAS command) is **resolved to column/motor
velocity** by the V30 road test: V30 soft-EME'd on a hard SUSTAINED HANDS-OFF turn, where the wheel is held
(column velocity ≈ 0). The fact that the IIR arm `gp-0x3574` was SMALL there (so the bound collapsed and the
2× command wound up the integrator → SM2/SM3) means the IIR tracks column velocity (→0 when the wheel is held),
NOT the LKAS command (which stays large on a hard turn). If the input were the command, the IIR would have
held the bound up and there'd have been no EME. So: **input = column velocity** ([STRONG], now corroborated by
behavior). This is the IIR arm of the soft-EME 3-way bound — full gating model + the V31 boost-floor fix that
addresses the collapse: [[reference-accord-soft-eme-bound-arm-gating]].

## See also

[[reference-accord-lerp-envelope-gating]] (T1/T2 driver-assist envelope, separate from this rate-shaper chain)  
[[reference-accord-override-snap-state-machines]] (SM2/SM3 use gp-0x3574 as integrator bound)
