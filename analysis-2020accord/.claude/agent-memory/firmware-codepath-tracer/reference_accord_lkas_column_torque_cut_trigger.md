---
name: reference-accord-lkas-column-torque-cut-trigger
description: SUPERSEDED root model. The gentle-EME LKAS cut = engage-SM disengage gp-0x6a62>=cal 0xC6312=320 (NOT the bVar1 32000 health gate, which is a railed-sensor fault). See lkas-engage-sm-disengage-trigger + dual-torque-sensor-architecture.
metadata:
  type: reference
---

2020 Accord 39990-TVA-A160, V850E2. STOCK code.bin. gp=0xFEDF8000, tp=0xBF000. [V] = disasm-verified.

## ⚠ CORRECTED ROOT MODEL (2026-06-29 → confirmed 2026-06-30)
The gentle EME (LKAS-only cut, `STEER_STATUS=no_torque_alert_2`, no DTC) is the **engage-SM disengage**:
`FUN_00040d58` param 2/3 disengages when **`gp-0x6a62 ≥ cal 0xC6312 = 320`** (no debounce). The live model + the
exact arithmetic live in [[reference-accord-lkas-engage-sm-disengage-trigger]] and
[[reference-accord-dual-torque-sensor-architecture]]. THE LEVER = raise cal `0xC6312` (lockstep-clean, cal-only).

## What in THIS file is RULED OUT (do not re-chase)
- **bVar1 / the 32000 channel ceiling** (the `0x9601`/`0x1900` raw-coil > 32000 health gate in
  `m_steer_torque_arbitration` `FUN_00028ea6`): this is a **railed-sensor FAULT** level. Real column torque tops
  out ~3400 (driver grab), so the 5 coils never approach 32000. Raising it fixes nothing and weakens fault
  detection. NOT the gentle-EME lever.
- **Voter plausibility `gp-0x67f4`**: a latch; set when `|prev gp-0x6a5e − new voted| < 0x41=65` (INTRA-sensor-A
  continuity, NOT an A-vs-B compare); cleared only on total coil loss. Does not drop on a torque transient.
- **Override-torque LERP @ tp+0x7736**: VALUES ALL ZERO → contributes no torque; not a lever.

## Still-true structural facts (kept for reference)
- `m_steer_torque_arbitration` `FUN_00028ea6`: zeroes the LKAS term `iVar28` when `(gp-0x6809 != 1) || !bVar1`.
  `gp-0x6809` (deliver flag) + `gp-0x6806` (CONTROL_ACTIVE) + `gp-0x6807` (STEER_STATUS) have **no gp-relative
  store** — written via a pointer/struct path, unresolved. The disengage SM drives them indirectly.
- The 5 voted coil tracks are sensor A (DMA serial, ×41/64); the voter `FUN_00041eec` writes `gp-0x6a62`=MAX
  (rising-edge unfiltered) and `gp-0x6a5e`=avg. Sensor A is **proven driver column torque** (indexes the assist
  boost curve 0xce578 [612..1238], fused with CAN sensor B). See the dual-sensor memory.
