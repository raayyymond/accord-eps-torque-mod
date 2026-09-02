---
name: accord-the-rate-loop-is-a-bang-bang-servo-p-rails-at-e-440
description: RETRACTED 2026-09-02 -- "P rails at |E| = 440 (+-1.8 deg/s)" carried a SECOND x32 that the bytes do not have. The decompile of FUN_00028ea6 (lines 975/1034/1036, `sar 0x8` @0x2A0C2) is E = 32*sp - fb, P = E*Kp >> 8 -- ONE factor of 32, inside E. P rails at |E| = 15360*256/Kp = 15855 operand (64 deg/s) at Kp 248 and 5650 (22.9 deg/s) at Kp 696. Stock at full demand with the wheel still delivers P = 5504*696>>8 = 14964 < 15360: the P clamp is NOT reached anywhere in stock's fb=0 surface. The table "stock delivers 417 at cmd 113" is false. What SURVIVES: LKAS commands a RATE (the setpoint is a rate reference), and the damping-fraction analysis (sign only, independent of the 32).
metadata:
  type: reference
---

# RETRACTED -- the rate loop is NOT a bang-bang servo; P rails at |E| = 15855, not 440 -- 2026-09-02

**What was claimed (2026-09-02, morning):** `P = clamp(32*E*Kp >> 8, +-15360)`, railing at |E| = 440 at Kp 248; stock
delivers its full 417 at cmd ~113; to openpilot the plant looked like an integrator; a static torque ratio has no
finite value.

**What the bytes say [EVIDENCE -- Ghidra decompile of FUN_00028ea6 on code.bin, confirmed by the orchestrator and by
`adv278r3c` independently]:**
```
0x29d76  shl 0x5,r16 ; 0x29d78 sub r26,r16        E = 32*sp - fb            (decompile line 975: iVar31 = iVar31 * 0x20 - uVar35)
0x2a0bc/0x2a0c2 sar 0x8                           P = (E * Kp) >> 8         (lines 1034/1036: iVar26 = iVar31 * Kp; uVar33 = iVar26 >> 8)
clamp +-tp+0x71bc (0xC61BC = 15360)
```
ONE factor of 32, already inside E. The retracted memory multiplied by 32 twice. V279's build script had it right all
along (`P(idx) == 64*idx` with map Y=2X, Kp=256 needs the single 32).

**Consequences:**
- P rails at |E| = 15360*256/Kp: **15855 operand = 64 deg/s at Kp 248 (idx 0); 5650 = 22.9 deg/s at Kp 696 (idx >= 136).**
- Stock, wheel still, full demand (idx 240, Y 172): E = 5504, P = 5504*696>>8 = 14964 -- BELOW the clamp. Stock's fb=0
  surface never rails. The "linear region" covers 92-97 % of ticks on the V276 log at K=2 (PREREG-V278R3-CLAMP-READ.md).
- The "narrow linear region" premise behind the operator's clamp-widening question is gone; the pre-registered
  answer is "do not widen" (predicted saturation duty 0.000 osc / 0.004 normal at K=2).
- STATE.md's V279 "WHY THIS BUILD" paragraph and the V278 page's "stock delivers 417 at cmd 113" line were corrected.

**What survives:** [[accord-lkas-commands-rate-not-torque]] (the setpoint IS a rate; the map is its reference) and
[[accord-v276-mechanism-is-a-matter-of-degree]] (damping fraction is a sign statistic, independent of the 32).
See [[accord-v278r3-torque-tap-reads-310-and-damping-is-sign-t-ne-sign-rate]] for the corrected instrument arithmetic.
