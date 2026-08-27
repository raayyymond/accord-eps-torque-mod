---
name: control-task-tick-confirmed-1khz
description: "The EPS control task FUN_0002214a runs at ~1000 Hz — CONFIRMED two independent ways (OSTM0CMP=79999/80MHz, and the STEER_STATUS=4 dwell cal 0xC64DF=100 measured at 100.00ms). Retires the long-standing 'task rate unresolved' open item. The assist-shaping task FUN_00022ca0 is a separate task whose rate is not statically determinable (~100Hz plausible)."
metadata: 
  node_type: memory
  type: reference
  originSessionId: fa311cac-7385-4675-8851-402a261e1200
  modified: 2026-07-20T21:44:12.048Z
---

**The control-task tick is ~1000 Hz, confirmed 2026-07-20 by two independent routes:**
1. **OSTM0**: `OSTM0CMP` = 79999 auto-reload / ~80 MHz PCLK = 1000 Hz. PCLK is one of the 4 `DFLASH.DCLKWAIT` options {48,64,80,160} MHz; only 80 MHz gives a clean ~1 ms, and a 100 Hz task would need a non-existent 7.95 MHz. PCLK's absolute value is not pinnable from `code.bin` (option byte outside the image), but 100 Hz is excluded.
2. **The `STEER_STATUS=4` dwell**: cal `0xC64DF` = 100 cycles, measured on the bus at 100.00 ms (dwell counter `gp-0x6757` decrements INSIDE arbitration, so it measures that task directly). 100 cycles / 0.100 s = 1000 Hz.

**Scope:** this pins the **control task** `FUN_0002214a` — arbitration (`FUN_00028ea6`), the aggregator (`FUN_0003aa2c`), shaper, governor, and the damper's sign filter (`FUN_00041464`, single caller here, state-gated not decimated). Cycle counts in this task's tree convert to Hz at 1000 tick/s.

⚠ The **assist-shaping task** `FUN_00022ca0` (boost `FUN_00034a72`, damping producer `FUN_00034350`) is a DIFFERENT task; its own invocation rate is NOT statically determinable and ~100 Hz is architecturally normal (fast inner control + slower human-bandwidth assist shaping). This matters for V44 damper EFFICACY only, not safety.

Also: CAN 399 transmits at 99.99849 Hz (a 100.01362 Hz figure was inflated by rlog gap-reconstruction), and 399 is a **100 Hz comms cadence inside the 1000 Hz task**, not the task rate — do not read the 100 Hz CAN rate as the control rate.

The canonical elapsed-tick counter is `gp-0x3e54` (single writer, `FUN_0002214a`, read image-wide), so any dwell/timeout that reads it is provably calibrated in real 1 kHz ticks. Related: [[v44-built-handsoff-damping]]. Firmware detail in tracked agent memory `.claude/agent-memory/firmware-codepath-tracer/reference_accord_ostm0_master_tick_rate_derivation.md` and `reference_accord_steerstatus4_dwell_constant_D.md`.
