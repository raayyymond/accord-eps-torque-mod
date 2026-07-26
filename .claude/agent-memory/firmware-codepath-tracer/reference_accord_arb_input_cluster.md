---
name: accord-arb-input-cluster
description: 2020 Accord TVA-A160 arbitration+input cluster: all variable touchers, zeroing paths, unexpected writers for gp-0x69ae/6b3c/6752/67a4/6a44-46/6a5e/67f4/67f5/3d37/3d28/6a7e/6756/6758/6b2c-38
metadata:
  type: reference
---

Full inventory scan completed 2026-05-27. Program: code.bin (V850:LE:32, gp=0xFEDF8000, tp=0xBF000). 185,116 instructions scanned.

## Key structural facts

**gp-0x69ae (LKAS setpoint):** Written only by `s_lkas_process_steer_cmd` (4 stores). Read by `m_steer_torque_arbitration` (2 reads) and `w_lkas_setpoint_consumer2`. Clean single-producer chain.

**gp-0x6b3c (arb output):** 1 writer (arb), 1 reader (`m_steer_torque_limit_and_pack`). Clean.

**gp-0x6752 (assist polarity):** ~50 readers across almost all torque-path functions. Writers: `FUN_000490ac` (init/watchdog) and `FUN_000497e6`. Redundant copy at gp-0x4c2d; mismatch calls FUN_0006b9fa (fault). Wide impact if perturbed.

**gp-0x6a44/40/3c/38 (column-torque ch 1-4):** Written exclusively by `FUN_000534da`. Read by arb, FUN_00041eec (torque fuser), and many others.

**gp-0x6a46 (column-torque ch 5):** Written exclusively by `FUN_000522fe` (different CAN unpacker from ch 1-4).

**gp-0x6a5e (fused driver torque):** SOLE WRITER = `FUN_00041eec` (torque fuser, called from `FUN_00022ca0`). Written with redundant copy at gp-0x4caa. 47+ readers. The fuser ZEROS output (or clamps to 0x7d00) when all 5 input channels fail range check. Zero risk during hard override if driver torque overshoots range bounds.

**gp-0x67f4 (plausibility flag):** Written by `FUN_00041eec` only. Set to 0 = no valid channels. When 0: fuser sets gp-0x67f5=0xFF and bypasses arb curve output. This is a gating zero path. Redundant copy at gp-0x4c38.

**gp-0x67f5 (convergence flag):** Written by `FUN_00041eec` (3 stores). Read by `m_motor_torque_governor`. Values: 1=converged, 0=lost, 0xFF=not-yet-converged. Governor-gating flag.

**gp-0x6758 (re-engage ramp gain accumulator):** Written by `m_steer_torque_arbitration` AND by `FUN_0002a30e` (the re-engage ramp manager). FUN_0002a30e zeros it on: FUN_00046ea6(9)==1, gp-0x67fa==8, gp-0x6807==7, param_3==0, ramp overflow. DIRECT NO-DTC ZEROING SOURCE.

**gp-0x6807 (re-engage state byte):** Written by arb AND FUN_0002a30e. Read by `w_lkas_setpoint_consumer2` and `FUN_00055c42`. Values: 3=no-param, 4=ramping, 6=bit-flag abort, 7=full abort/reset. Cross-boundary.

**gp-0x6802 (LKAS engagement mode):** Written by `s_lkas_process_steer_cmd`. Read by arb, FUN_0002a30e, w_lkas_setpoint_consumer2.

**gp-0x6b38 (arb output word):** Written by arb only. Read by `w_lkas_setpoint_consumer2`.

**FUN_0002a93a:** The arb curve evaluator (inline sub-function or separately called). Reads gp-0x69b0/6a34/680a/6805/674e/682f/6830/6803/4f60. Writes gp-0x6b32/34/36 (outputs) and gp-0x6a32/697a/674b/6cf8/6dd0 (intermediates). Zero-path at start: if gp-0x69b0==0 AND gp-0x6805!=1, or param_1==0, outputs all set to 0/0x7FFFFFFF.

**FUN_00041eec:** Torque fuser. Single caller: FUN_00022ca0. Reads gp-0x6a44/40/3c/38/46 (5 channels), gp-0x6a5e (feedback), gp-0x67f4/f5, gp-0x6a62/6a64. Writes gp-0x6a5e, gp-0x6a62, gp-0x6a64, gp-0x67f4, gp-0x67f5. Uses redundancy pairs checked against gp-0x4caa/4cae/4cb0/4c38.

## Zeroing/perturbation paths (priority for "momentary power steering out" investigation)

1. **gp-0x6758=0 via FUN_0002a30e** — most likely: clean zero of re-engage ramp during hard override when gp-0x6807==7 or param_3==0. No DTC.
2. **gp-0x67f4=0 via FUN_00041eec** — triggered if all 5 driver torque channels fail range check. Hard override can push torques outside expected range.
3. **gp-0x6a5e=0 via FUN_00041eec** — consequence of #2; fused torque drops to zero.
4. **gp-0x6752 mismatch fault via FUN_0006b9fa** — if polarity byte redundancy breaks transiently.

## CAN buffer 0xFEDF6BD8

No immediate-operand references. Access is via computed base+offset. Trace via decompile of FUN_000534da (ch1-4 writer) and FUN_000522fe (ch5 writer).

## New gp-offsets discovered (not in original list)

- gp-0x6757 (ramp direction byte)
- gp-0x6807 (re-engage state machine)
- gp-0x6802 (LKAS engagement mode)
- gp-0x6a62 (fused torque, filtered copy)
- gp-0x6a64 (speed-adapted torque threshold, read by governor)
- gp-0x6a32, gp-0x697a, gp-0x6cf8, gp-0x6dd0 (arb curve intermediates)
- gp-0x674e (variant/mode index)
- gp-0x674b (steer-rate magnitude intermediate)
- gp-0x680a, gp-0x6805, gp-0x69b0, gp-0x6803, gp-0x682f, gp-0x6830 (arb curve control/input bytes)
- gp-0x67fa (system mode/fault byte, very wide)
- gp-0x4f60 (signed vehicle speed or related, used in arb direction gate)

[[accord-mixer-lkas-source-chain]]
[[accord-governor-gp0x184-chain]]
