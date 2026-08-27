# Cluster 1: Arbitration + Input Stage — Variable Inventory
**Program:** code.bin (V850:LE:32, image_base 0x0)
**gp = 0xFEDF8000, tp = 0xBF000**
**Method:** search_instructions(operand_pattern) program-wide (185,116 instructions scanned, complete)
**Date:** 2026-05-27

---

## Variable Table

| Abs RAM Addr | gp-Offset | #R | #W | Writer Function(s) | Reader Function(s) (key) | Role | FLAGS |
|---|---|---|---|---|---|---|---|
| 0xFEDF1652 | -0x69ae | 2 | 4 | `s_lkas_process_steer_cmd` (×4) | `m_steer_torque_arbitration` (×2), `w_lkas_setpoint_consumer2` | LKAS setpoint written by CAN handler; read by arb + secondary consumer | — |
| 0xFEDF14C4 | -0x6b3c | 1 | 1 | `m_steer_torque_arbitration` | `m_steer_torque_limit_and_pack` | Arb output word; single writer (arb), single reader (limit/pack) | — |
| 0xFEDF18AE | -0x6752 | ~50 | 3 | `FUN_000490ac` (init, ×2), `FUN_000497e6` (×2) | ≥30 functions including arb, mixer, shaper, aggregator | **Assist polarity / direction byte.** Written at init by FUN_000490ac (unconditional `=1` on match, else FUN_0006b9fa fault) and by FUN_000497e6. Read by practically every torque-path function. | **FLAG: written outside normal pipeline by init/watchdog functions FUN_000490ac and FUN_000497e6.** Mismatched redundant copy at gp-0x4c2d triggers FUN_0006b9fa (fault handler). |
| 0xFEDF185C | -0x67a4 | 1 | 1 | `m_steer_torque_limit_and_pack` | `m_steer_torque_arbitration` | ENABLE byte; arb reads it, limit/pack writes it (feedback token) | — |
| 0xFEDF1859 | -0x67a7 | 1 | 1 | `m_steer_torque_arbitration` | `m_steer_torque_limit_and_pack` | Arb output status byte; single writer arb, single reader limit/pack | — |
| 0xFEDF185F | -0x67a1 | 5 | 1 | `m_steer_torque_limit_and_pack` | `m_steer_torque_limit_and_pack` (×5 reads, ×1 write, self-RMW) | Internal limit/pack state byte; entirely within limit/pack | — |
| 0xFEDF185D | -0x67a3 | 1 | 1 | `m_steer_torque_arbitration` | `m_steer_torque_limit_and_pack` | Arb output flag byte; single writer, single reader | — |
| 0xFEDF15BC | -0x6a44 | ~13 | 3 | `FUN_000534da` (×3) | arb, FUN_00041eec, FUN_00042376, FUN_0004d8f0, FUN_0004de0c, others | Column-torque channel 1; exclusively written by `FUN_000534da` (CAN torque column unpacker) | — |
| 0xFEDF15C0 | -0x6a40 | ~13 | 3 | `FUN_000534da` (×3) | arb, FUN_00041eec, FUN_00042376, FUN_0004d8f0, FUN_0004de0c | Column-torque channel 2 | — |
| 0xFEDF15C4 | -0x6a3c | ~13 | 3 | `FUN_000534da` (×3) | arb, FUN_00041eec, FUN_00042376, FUN_0004d8f0, FUN_0004de0c | Column-torque channel 3 | — |
| 0xFEDF15C8 | -0x6a38 | ~13 | 3 | `FUN_000534da` (×3) | arb, FUN_00041eec, FUN_00042376, FUN_0004d8f0, FUN_0004de0c | Column-torque channel 4 | — |
| 0xFEDF15BA | -0x6a46 | ~17 | 3 | `FUN_000522fe` (×3) | arb, FUN_00041eec, FUN_00042376, FUN_0004d8f0, FUN_0004de0c, FUN_0002ec52, FUN_0004fbde | Column-torque channel 5 (different writer: `FUN_000522fe`) | **FLAG: different writer from channels 1-4; FUN_000522fe is a separate CAN unpacker** |
| 0xFEDF179E | -0x6a5e | 1 | 1 | `FUN_00041eec` | ≥47 functions including arb (×5), shaper, aggregator, governor, many others | **Fused driver torque** (redundancy-checked; written with dual-copy at gp-0x4caa). Sole writer is the torque fusion function. | **FLAG: extremely wide reader set (47+). The fusion function FUN_00041eec also gates output based on convergence state; zero output possible when no valid torque channels.** |
| 0xFEDF180C | -0x67f4 | ~25 | 2 | `FUN_00041eec` (×2) | arb, FUN_00022016, FUN_00022034, many others | **Plausibility/convergence flag.** Written by FUN_00041eec: set to 1 when |fused - nearest_channel| < 0x41 AND gp-0x4c38 agrees; set to 0 when no valid channels. Read inside FUN_00041eec to gate further processing. | **FLAG: gating. When =0, FUN_00041eec sets gp-0x67f5=0xFF (force-disengaged?) and skips arb curve output computation. This is a zeroing path.** |
| 0xFEDF180B | -0x67f5 | ~8 | 3 | `FUN_00041eec` (×3) | `m_motor_torque_governor` (×1), FUN_00021d72, FUN_00021eee, FUN_00022034, FUN_0007e8d8 | **Convergence/engage flag.** FUN_00041eec writes: 0xFF = not-converged (when gp-0x67f4==0), 1 = converged (timer elapsed + threshold met), 0 = converged-to-zero. Read by governor. | **FLAG: gating. Governor reads this; value 0xFF may gate or zero governor output. Cross-boundary writer (FUN_00041eec is outside arb).** |
| 0xFEDF4269 | -0x3d37 | 1 | 7 | `m_steer_torque_arbitration` (×7) | `m_steer_torque_arbitration` (×1) | Arb state machine byte; entirely internal to arb | — |
| 0xFEDF426A | -0x3d36 | 1 | 6 | `m_steer_torque_arbitration` (×6) | `m_steer_torque_arbitration` (×1) | Arb state machine byte 2; entirely internal to arb | — |
| 0xFEDF4278 | -0x3d28 | 1 | 7 | `m_steer_torque_limit_and_pack` (×7) | `m_steer_torque_limit_and_pack` (×1) | Limit/pack state byte; entirely internal to limit/pack | — |
| 0xFEDF1582 | -0x6a7e | 3 | 11 | `m_steer_torque_arbitration` (×11) | `m_steer_torque_arbitration` (×3) | Re-engage counter (16-bit); entirely internal to arb | — |
| 0xFEDF18AA | -0x6756 | 2 | 10 | `m_steer_torque_arbitration` (×10) | `m_steer_torque_arbitration` (×2) | Re-engage ramp gain byte; entirely within arb | — |
| 0xFEDF18A8 | -0x6758 | 2 | 22 | `m_steer_torque_arbitration` (×12), `FUN_0002a30e` (×10) | `m_steer_torque_arbitration` (×2), `FUN_0002a30e` (×2) | **Re-engage ramp gain accumulator.** `FUN_0002a30e` independently writes this to 0 on multiple exit paths (fault, no-param, etc.). | **FLAG: FUN_0002a30e is the re-engage ramp manager and CAN ZERO this counter under several conditions: iVar7==1 (FUN_00046ea6(9) result), gp-0x67fa==8, gp-0x6807==7, param_3==0, ramp overflow, etc. This is a known zeroing source.** |
| 0xFEDF14D4 | -0x6b2c | 3 | 10 | `m_steer_torque_arbitration` (×10) | `m_steer_torque_arbitration` (×3) | Arb internal accumulator (16-bit, reset to 0 or written to r11); entirely within arb | — |
| 0xFEDF14D0 | -0x6b30 | 1 | 1 | `m_steer_torque_arbitration` | `m_steer_torque_arbitration` | Arb internal word; RMW within arb | — |
| 0xFEDF14CE | -0x6b32 | 0 | 2 | `m_steer_torque_arbitration`, `FUN_0002a93a` | (none observed) | Arb curve output word 1 (written by arb main + arb curve evaluator `FUN_0002a93a`); no observed readers in this scan | **FLAG: second writer FUN_0002a93a.** |
| 0xFEDF14CC | -0x6b34 | 0 | 2 | `m_steer_torque_arbitration`, `FUN_0002a93a` | (none observed) | Arb curve output word 2 | **FLAG: second writer FUN_0002a93a.** |
| 0xFEDF14CA | -0x6b36 | 0 | 2 | `m_steer_torque_arbitration`, `FUN_0002a93a` | (none observed) | Arb curve output word 3 | — |
| 0xFEDF14C8 | -0x6b38 | 2 | 1 | `m_steer_torque_arbitration` | `w_lkas_setpoint_consumer2` (×2) | Arb output word (16-bit); **read by the secondary LKAS consumer** | **FLAG: cross-boundary reader w_lkas_setpoint_consumer2 reads this.** |
| 0xFEDF6BD8 | (abs) | 0 | 0 | — | — | CAN buffer: no direct immediate-operand references found. Access is via base-register + computed offset (not visible to operand pattern search). | **UNRESOLVED: indirect access only.** |

---

## Discovered Variables NOT in Original List

| gp-Offset | Abs Addr | First seen in | Role inferred |
|---|---|---|---|
| -0x6757 | 0xFEDF18A9 | `m_steer_torque_arbitration`, `FUN_0002a30e` | Re-engage ramp direction/sign byte (set to -cVar2 on abort, set to cVar2 on full ramp) |
| -0x6807 | 0xFEDF17F9 | `m_steer_torque_arbitration`, `FUN_0002a30e`, `w_lkas_setpoint_consumer2`, `FUN_00055c42` | **Re-engage state machine byte** (values 3,4,6,7 seen as abort codes in FUN_0002a30e). Cross-boundary: read by w_lkas_setpoint_consumer2 and FUN_00055c42. |
| -0x6802 | 0xFEDF17FE | `s_lkas_process_steer_cmd` (W), arb (R), `FUN_0002a30e` (R), `w_lkas_setpoint_consumer2` (R) | **LKAS engagement mode byte** (values 0/2 visible). Written by LKAS CAN handler; read by arb, re-engage ramp manager, and secondary consumer. |
| -0x6a62 | 0xFEDF179E | `FUN_00041eec` (W ×2), many readers | **Fused driver torque (redundant copy / filtered)**. FUN_00041eec writes both gp-0x6a5e and gp-0x6a62. The difference between these two may be smoothed vs raw. |
| -0x6a64 | 0xFEDF179C | `FUN_00041eec` (W ×1), many readers including `m_motor_torque_governor` | **Speed-adapted torque threshold** (written by torque fuser, read by governor). |
| -0x6a32 | 0xFEDF15CE | `FUN_0002a93a` | Intermediate arb curve signed output |
| -0x697a | 0xFEDF1686 | `FUN_0002a93a` | Arb steer-rate intermediate (speed arg) |
| -0x6cf8 | 0xFEDF1308 | `FUN_0002a93a` (W), arb curve (R) | Arb integrator/history state (int32) |
| -0x6dd0 | 0xFEDF1230 | `FUN_0002a93a` (W) | Arb integrator/history state 2 (int32) |
| -0x674e | 0xFEDF18B2 | `FUN_0002a93a` (R) | Variant/mode index byte (selects arb curve set) |
| -0x674b | 0xFEDF18B5 | `FUN_0002a93a` (W) | Computed steer-rate magnitude (written mid-computation) |
| -0x680a | 0xFEDF17F6 | `FUN_0002a93a` (R) | Arb sub-mode flag (selects alternate curve path when ==1) |
| -0x6805 | 0xFEDF17FB | `FUN_0002a93a` (R) | Arb enable pre-condition byte (must be ==1 or zero-path taken) |
| -0x69b0 | 0xFEDF1650 | `FUN_0002a93a` (R) | Short near gp-0x69ae (setpoint-adjacent); zero check gates arb curve eval |
| -0x6803 | 0xFEDF17FD | `FUN_0002a93a` (R) | Sub-mode byte for arb B/A curve selection (==2 check) |
| -0x682f | 0xFEDF17D1 | `FUN_0002a93a` (R), `FUN_0002a30e` (R) | **Driver torque magnitude byte** (absolute torque, used as axis for arb curve lookup AND re-engage ramp threshold). Cross-used by both arb curve evaluator and re-engage manager. |
| -0x6830 | 0xFEDF17D0 | `FUN_0002a93a` (R) | Secondary driver torque byte (second axis for some arb curves) |
| -0x67fa | 0xFEDF1806 | heavily used (50+ hits, many writers in 0x14xxx-0x19xxx range) | **System mode / fault byte** (very wide — written by low-level CAN/power mgmt functions). Value ==8 in FUN_0002a30e causes re-engage ramp zeroing. |
| -0x4f60 | 0xFEDF3020 | `FUN_0002a93a` (R) | Signed vehicle speed or related signal (sign check gates arb direction) |

---

## Summary: Variables That Can Zero or Hard-Perturb Delivered Torque

### 1. gp-0x6758 (re-engage ramp gain accumulator) — DIRECT ZEROING
**Writer:** `FUN_0002a30e` zeros this unconditionally on ANY of these conditions:
- `FUN_00046ea6(9)` returns 1 (some system-level permission/interlock)
- `gp-0x67fa == 8` (system fault/mode byte = 8)
- `gp-0x6807 == 7` (re-engage state = abort)
- `param_3 == 0` (LKAS command = 0 or not engaged)
- Ramp overflow (counter exceeds tp+0x74e0+tp+0x74e1 threshold)

When zeroed, the re-engage ramp output is zero, meaning LKAS torque can drop to 0 even while the LKAS setpoint is nonzero. This is a **transient zero source with no DTC** — it looks like a clean ramp-to-zero.

### 2. gp-0x67f4 (plausibility flag) — GATE
Written to 0 by `FUN_00041eec` when no valid torque channels are available (all 5 channels failed range check). When 0: FUN_00041eec writes gp-0x67f5 = 0xFF and short-circuits the arb curve output calculation. Downstream effects propagate to gp-0x6a5e/6a62 (fused torque). **If driver torque channels drop (e.g., during hard override transient), this can cause a momentary zeroing of the arb input.**

### 3. gp-0x67f5 (convergence/engage flag) — GATE on governor
Read by `m_motor_torque_governor`. Value 0xFF (set when gp-0x67f4==0) may cause governor to treat LKAS as disengaged. This is the downstream consequence of gp-0x67f4==0.

### 4. gp-0x6752 (assist polarity) — FAULT on mismatch
Has a redundant copy at gp-0x4c2d. If these diverge, `FUN_000490ac` calls `FUN_0006b9fa` (fault handler). During a hard override, if the polarity byte's redundant copy is transiently inconsistent (e.g., due to timing), this fault handler could disrupt torque delivery.

### 5. gp-0x6a5e (fused driver torque) — ZERO RISK from torque fuser
Sole writer is `FUN_00041eec`. If all 5 column-torque channels (gp-0x6a44/40/3c/38/46) fail their range checks simultaneously — which can happen during a hard override with high driver torque — the function takes the "no valid channels" branch and writes zero or 0x7d00 (capped) to gp-0x6a5e. This feeds arb directly and can cause a transient torque output drop.

---

## Unexpected Writers (Outside Expected Pipeline)

| Variable | Unexpected Writer | Why Unexpected |
|---|---|---|
| gp-0x6752 (assist polarity) | `FUN_000490ac`, `FUN_000497e6` | Init/watchdog functions outside the arb/shaper pipeline |
| gp-0x6758 (ramp accumulator) | `FUN_0002a30e` | Separate re-engage ramp manager function, parallel to arb |
| gp-0x6757 (ramp direction) | `FUN_0002a30e` | Same |
| gp-0x6807 (re-engage state) | `FUN_0002a30e` | Cross-writes a byte read by arb and w_lkas_setpoint_consumer2 |
| gp-0x6b32/34/36/38 (arb internals) | `FUN_0002a93a` | Arb sub-function (curve evaluator) — expected sub-call, not truly external |
| gp-0x67f4, gp-0x67f5, gp-0x6a5e, gp-0x6a64 | `FUN_00041eec` | Torque fuser (separate function from arb) but its caller is FUN_00022ca0 |

---

## CAN Buffer (0xFEDF6BD8)
No direct immediate-operand references found anywhere in the 185,116-instruction scan. Access is exclusively via computed base+offset addressing (register load then offset). To trace the CAN buffer, the recommended next step is: decompile `FUN_000534da` (column-torque unpacker for channels 1-4) and `FUN_000522fe` (channel 5 writer) to find the base pointer chain leading to 0xFEDF6BD8.
