---
name: v44-built-handsoff-damping
description: "V44 BUILT + independently verified, UNFLASHED — restores the base-assist damping term hands-off (0xD27C6 0→235, 0xD27DA 0→234) + reverts V43's falsified pole. The vibration is a MEASURED Q=13.6 mechanical resonance the firmware fails to damp hands-off because the damping product is multiplied by zero below 2240 counts of driver torque."
metadata: 
  node_type: memory
  type: project
  originSessionId: fa311cac-7385-4675-8851-402a261e1200
  modified: 2026-07-20T21:43:57.233Z
---

**V44 = V43 + 12 bytes: revert the falsified pole (`0xC644A` 32→1024) + raise the hands-off damping gate (`0xD27C6` 0→235 mode 10, `0xD27DA` 0→234 mode 11).** Cal-only, dual-verified, NOT flashed. Builder `analysis-2020accord/builds/v18_v49/build_v44_tva.py`; handoff `docs/handoffs/2026-07/HANDOFF-2026-07-20-v44-handsoff-damping.md`. Carries the confirmed ratchet fix (`0x454FE`) unchanged.

**Why:** The vibration is a **measured lightly-damped mechanical resonance** (21.4 Hz, Q≈13.6 — the "sharp 21.02 Hz clock-locked line" was an FFT artifact, see [[v42-flashed-ratchet-fixed-r26-falsified]] lineage). Its firmware enabler: the base-assist viscous **damping** lane `gp-0x6bd0` (`FUN_00034350`) is a product of four Q10 factors, and the factor keyed on voted driver torque `gp-0x6a5e` (LERP `@0xD27BC` mode10 / `@0xD27D0` mode11) has **`Y[0]=0` at `X[0]=2240`** → below 2240 counts (hands-off) the whole product = 0. No notch filter exists anywhere in the command path. So hands-off the mode rings undamped; hands-on (driver torque 8.1%FS vs 0.59% hands-off, straddling the ~7% gate) the damper engages → vibration gone = the operator's report.

**How to apply:** Safety is CLOSED — the damper's sign source `FUN_00041464` is confirmed ~1 kHz (see [[control-task-tick-confirmed-1khz]]), so its phase is −22° (cos +0.93), net-dissipative even if the producer task runs at 100 Hz (cos +0.55). Never injects. Efficacy is the ONLY open question: the term maxes at ~213 counts vs a ~139-count oscillation — "is that enough?" is a plant question the car resolves, not firmware. ⚠ Zero damping was equally true pre-V38 (which didn't vibrate), so it's an ENABLING condition; V38's 4× authority excites the mode. V44 is a MITIGATION, not a root-cause repair. Both modes patched because a failover reselects mode 11. Highest-value data to collect: a 2–10 mph hands-off log (the regime the operator reports worst, the one route b9 can't see).

Corrections of record this build carries: control tick confirmed ~1 kHz; `gp-0x6abe` is LIVE in normal driving (was recorded backwards); the V43 "half-wave damper" is wrong (`gp-0x6ac0` is abs()'d before store); `search_instructions` undercounts (use byte-pattern scans). Related: [[reference-accord-state4-governor-ratchet]], [[reference-accord-lkas-lane-is-a-lowpass]], [[v43-dirty-derivative-pole-built]].
