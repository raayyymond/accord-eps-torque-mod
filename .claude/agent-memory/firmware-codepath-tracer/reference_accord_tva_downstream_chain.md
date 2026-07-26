---
name: accord-tva-downstream-chain
description: Verified downstream path from gp-0x6b98 (LKAS torque demand) to motor output in Honda Accord 39990-TVA-A160, V850 platform
metadata:
  type: reference
---

## Entry point

`gp-0x6b98` = `0xFEDF1468` — LKAS torque demand (signed 16-bit). Read by ~20 functions from `w_steer_control_task @ 0x0002214a`.

## Verified downstream chain

### Hop 1: FUN_00041b8e (0x00041b8e) — Range guard + FOC current reference computation

Called from w_steer_control_task with `uVar4` mask (0x830).

- Reads gp-0x6b98 as Q1.0 (divide by 1024 → float), checks sign for same-side torque condition
- Inner ±8.0 float guard: `dVar8 = gp-0x6b98 * 0.0009765625; if dVar8 <= 8.0 && -8.0 <= dVar8 → pass`
  — 8.0 / 0.0009765625 = 8192 = 0x2000. This is the ±8192 range guard in floating point.
- Writes float target to gp-0x6d90, gp-0x6d88, gp-0x6d8c, gp-0x6d84 (FOC phase current reference set)
- When out of range: writes 65535.0 (fault value) to gp-0x6d90

### Hop 2: FUN_00041464 (0x00041464) — Phase current interpolation + velocity estimates

Called from w_steer_control_task (0x930 mask, before FOC path).

- Reads gp-0x6b98 as integer, has explicit `if (0x4000 < (int)*(short *)(unaff_gp + -0x6b98) + 0x2000U)` guard
  — same ±0x2000 (±8192) check in integer form
- Writes gp-0x6abc, gp-0x6abe, gp-0x6ac0, gp-0x6ac2 (phase current command set for FOC axes)
- Writes gp-0x6c2c, gp-0x6c2e (integrator state), gp-0x6c38 (feedforward term)

### Hop 3: FUN_0003b8f6 (0x0003b8f6) — FOC current controller (PI + feedforward)

Called from w_steer_control_task (0x830 mask).

- Range guard at entry: `(int)*(short *)(unaff_gp + -0x6b98) + 0x2000U < 0x4001`
- Computes full FOC PI controller in float: d-axis and q-axis current errors, integration
- Inner ±20000 clamps on intermediate motor current calculations:
  `if (iVar11 < 0x4e21) ... else iVar11 = 20000; if (iVar11 < -20000) iVar11 = -20000;`
  (20000 = 0x4E20 — motor current limit in internal units)
- Writes `gp-0x6bf6` (motor current command, short) and `gp-0x6c00` (absolute value of current)
- On invalid range: writes 0x7fff to gp-0x6bf6, 0xffff to gp-0x6c00

### Hop 4: m_steer_torque_limit_and_pack @ 0x0002b422 — Arbitration + m_motor_cmd_distribute_clamp

Called from w_steer_control_task sequence (named function).

- Reads gp-0x6b3c (arbitrated torque demand from m_steer_torque_arbitration @ 0x00028ea6)
- Applies ±tp+0x71b2 clamp to gp-0x6b3c → writes gp-0x6b3a (limit-and-pack output)
- tp+0x71b2 is a cal read — returns 0xFFFF (no effective clamp in this dump)
- Calls `m_motor_cmd_distribute_clamp @ 0x00025c32` with channel descriptor struct

### Hop 5: m_motor_cmd_distribute_clamp @ 0x00025c32 — Per-channel clamp + distribution

Key clamps visible in disassembly (code immediates):
- `0x00025c80–0x00025c98`: ±0x4000 (16384) clamp — channel 1 torque component
- `0x00025c9c–0x00025cb4`: ±0x2800 (10240) clamp — channel 2 torque component  
- `0x00025cb8–0x00025cd0`: ±0x384 (900) clamp — small channel (rate/damping?)
- `0x00025cd4–0x00025cec`: ±0x4E20 (20000) clamp — motor current (FOC units)
- `0x0000025c3c–0x00025c50`: gp-0x69aa range check → sets fault flag at gp-0x6188

Also checks gp-0x69aa vs 0x8000 (signed) at 0x00025c44 — this is a runtime condition.

### Hop 6: m_motor_cmd_mixer @ 0x00026c80 — Final mixing, arbitration, FINAL clamp

Massive function; key clamp chain at end:
- `0x000276de–0x0002772a`: ±0x2800 (10240) final clamp on mixed torque sum → gp-0x6b4c
  Code immediates: `movea 0x2800,r0,r8` at 0x000276ec and `movea -0x2800,r0,r8` at 0x00027704
- Clamp at 0x00027396–0x000273ea: ±0x4E20 on intermediate → gp-0x6bfa
- Clamp at 0x000273ee–0x0002743e: ±0x0E10 (3600) on another intermediate → gp-0x69f2
- Calls FUN_00042ac6 at very end with r26 (the ±0x2800-clamped value)

### Hop 7: FUN_00042ac6 @ 0x00042ac6 — Final saturation write to gp-0x6afe

```
if (param_1 + 0x2800 > &PTR_FUN_00005000) {  // i.e. > 0x2800 = 10240
    param_1 = 0x7fff;
}
*(short*)(gp - 0x6afe) = (short)param_1;
```

— This is the absolute final write before the motor command is consumed downstream.
gp-0x6afe = 0xFEDF1302 (motor current command register, runtime)

The 0x7fff cap here is a **fault path** (invalid input), not the normal operating ceiling.
Normal ceiling from the ±0x2800 clamp = **10240 (0x2800)**.

## Peripheral interface

The TAUJ0 struct error that prevents decompiling m_motor_cmd_mixer suggests it writes directly to TAUJ0 timer/PWM registers. From w_steer_control_task, the chain terminates via FUN_00042ac6 writing to gp-0x6afe, which is then consumed by whatever function writes TAUJ0 (not visible in budget).

The `TAUA1_registers_t_ffffc800` references visible in multiple readers (FUN_00035e00, FUN_0003aff4) show reads from TAUA1 peripheral (feedback/current sense), not writes to PWM — confirming those are ADC/sense path.

## Clamp hierarchy summary (CODE IMMEDIATES, editable)

| Clamp value | Hex | Location | Function | Role |
|---|---|---|---|---|
| ±8192 | ±0x2000 | FUN_0003b8f6 entry, FUN_00041464, FUN_000370b6 | Multiple readers | Input range guard — pass-through gating |
| ±20000 | ±0x4E20 | 0x00025cd4 (m_motor_cmd_distribute_clamp), 0x000273a6 (m_motor_cmd_mixer) | FOC current | Motor current absolute limit (CODE IMMEDIATE) |
| ±10240 | ±0x2800 | 0x00025c9c (distribute_clamp), 0x000276e2/0x000276fa (motor_cmd_mixer final) | Mixed torque | **Final torque ceiling = 10240 (CODE IMMEDIATE)** |
| ±16384 | ±0x4000 | 0x00025c80 (distribute_clamp) | Channel component | Sub-limit (CODE IMMEDIATE) |
| ±3600 | ±0x0E10 | 0x000273ee (m_motor_cmd_mixer) | Intermediate | Rate/secondary limit (CODE IMMEDIATE) |

**Key finding: there is NO 8192 (0x2000) ceiling on the output path.** The ±8192 checks are INPUT GUARDS (pass/reject the torque demand into the control path). The final output ceiling in code immediates is ±10240 (0x2800), applied in both m_motor_cmd_distribute_clamp and m_motor_cmd_mixer. Both are CODE IMMEDIATES and editable.

## Notes
- tp+ cal reads return 0xFFFF in this dump → tp+0x71b2 (the limit_and_pack clamp) is effectively ∞ 
- gp- values are runtime — not directly editable as code immediates
- The ±8192 check in FUN_000370b6 at `(int)*(short *)(unaff_gp + -0x6b98) + 0x2000U < 0x4001` is an unsigned comparison: 0 → 0x4000 range → signed -0x2000 to +0x2000 = ±8192. This is a GATE, not an output clamp.

Related: [[accord-torque-demand-task]], [[reference_c020_vs_c120_motor_power]]
