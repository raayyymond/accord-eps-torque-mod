---
name: reference-accord-gp6af8-fight-trigger
description: Identity of gp-0x6af8 (fight-test directional reference) and complete boolean trigger for EME fight state machine in s_motor_torque_rate_shaper (FUN_00042af8), Accord TVA-A160
metadata:
  type: reference
---

# gp-0x6af8 Identity and Full Fight-SM Trigger — Accord TVA-A160

**Verified via Ghidra decompile + disasm, 2026-05-29. Program: code.bin, V850:LE:32, 39990-TVA-A160.**

## gp-0x6af8: What It Is

**gp-0x6af8 (abs 0xFEDF1508) = gp-0x4f60, range-gated to ±0x6400 (i.e. = 0 if out of range)**

More precisely (decompile line 219-222):
```c
iVar43 = (int)*(short *)(gp - 0x4f60) *
         (uint)(&DAT_00006400 + *(short *)(gp - 0x4f60) < &DAT_0000c801);
*(short *)(gp - 0x6af8) = (short)iVar43;
```
The gate condition `(gp-0x4f60 + 0x6400) < 0xC801` passes values in the signed range ±0x6400 (±25600). Values outside this window are zeroed.

### gp-0x4f60: What It Is

**gp-0x4f60 = SIGNED MOTOR/COLUMN ANGULAR VELOCITY** (steering-column rotation rate, signed).

Evidence chain:
1. **Writer**: Primarily FUN_0007f3f8, specifically at 0x7f9c8: `st.h r26, -0x4f60, gp`
   - r26 comes from: `ld.h -0x6b50, gp, r26` (0x7f994), then slew-limited by gp-0x698c multiplied step.
   - gp-0x4f60 and its lockstep shadow gp-0x4486 are always written in tandem (dual-path safety pair via FUN_0006b9ee/FA integrity checks).

2. **FUN_00043e44 usage (0x43eda-0x43ef8)**: Reads gp-0x4f60, converts to float64 via `cvtf.ws` → `cvtf.sd`, multiplies by 0x3F500000 scale factor, then compares against 25.0 (IEEE 0x40390000) — this is a velocity-in-RPM or deg/s threshold comparison. [V: 0x43eda ld.h, 0x43ede cvtf.ws, 0x43ef6 cmpf.d against 0x40390000]

3. **m_steer_torque_arbitration usage (0x28f26, 0x29a90)**: gp-0x4f60 is sign-tested (cmp r0, r12 / blt), and used with ±0x6400 range check — signed velocity semantics. [V: 0x29a90 ld.h then blt at 0x29a94]

4. **FUN_0007f3f8 write path**: Takes input from gp-0x6b50 (which has no independent st.h writer — written via struct pointer stores not captured by search_instructions), slew-limits it using gp-0x698c as a rate cap, and stores result. The slew-limiter is the same pattern used for motor torque tracking in FUN_0007ebd6, which produces gp-0x4f54 (adjacent motor-speed-scaled output). The whole FUN_0007f3f8 cluster manages motor angular velocity tracking.

5. **Semantic relationship**: gp-0x4f60 is **signed** (readers use ld.h), gp-0x4f68 is **unsigned absolute value** (all readers use ld.hu). FUN_0007f3f8 writes gp-0x4f68 = ABS(computed_velocity) at 0x7feca. gp-0x4f60 = signed version of same quantity.

**VERDICT on gp-0x6af8**: It is the **signed motor/column angular velocity** (column rotation rate, slew-tracked from raw sensor), range-gated to zero when the velocity is implausibly large (>±0x6400 raw units).

This is NOT:
- Driver torque (gp-0x6a5e / gp-0x6abe)
- LKAS command/demand (gp-0x6acc / gp-0x6b98)
- Self-aligning torque (that would come from the torque sensor path, not the motor velocity path)

This IS: the steering column's own rate of rotation (from motor sensor feedback), which in EPS represents the ROAD/self-aligning component — when the wheel is turning on its own due to road camber or the driver's hands, the column has angular velocity. When LKAS applies torque that opposes this self-driven rotation, the fight test fires.

---

## Complete Fight-SM Trigger Boolean

The fight-detection state machine has TWO parallel SMs (gp-0x355d → gp-0x6960; gp-0x355e → gp-0x6962). The primary SM (gp-0x355d / gp-0x6960) triggers on the FIGHT condition.

### Variable Assignments (all [V] from decompile)
| Decompile var | Source | Meaning | Address |
|---|---|---|---|
| `sVar26` | `(short)uVar25` = gated gp-0x6acc | LKAS command (Q15, signed) | line 882 |
| `sVar52` | `(short)iVar18` = gp-0x6752 * bVar1 | Column torque direction sign (±1 or 0) | line 881 |
| `gp-0x6af8` | gated gp-0x4f60 | Signed column angular velocity | line 222 |
| `uVar9` | `*(ushort *)(tp + 0x71e0)` = ABS 0xC61E0 | Cal threshold: min |LKAS cmd| to arm | line 755 |
| `uVar13` | `*(ushort *)(gp - 0x4f68)` gated | Absolute column velocity magnitude | line 873 |
| `uVar19` | from gp-0x6960 (current Q15 authority gate) | Current authority gate value | line 889 |
| `uVar28` | `|uVar25|` = |LKAS command| | signed ABS | line 875-878 |
| `bVar40` | `*(byte *)(gp - 0x355d)` | State machine state (0-4 or more) | line 879 |

### State 1 (bVar40 == 1) FIGHT Trigger [V: decompile lines 883-901]
The state transitions from 1→3 (FIGHT entry) when ALL of:
1. `uVar9 < uVar13` — **SPEED gate**: column velocity magnitude > cal threshold tp+0x71e0. [V: line 884]
2. `uVar19 < uVar28` — **MAGNITUDE gate**: |LKAS command| exceeds the current authority gate value. [V: line 884]
3. `sVar26 * sVar52 * gp-0x6af8 * 4 < 0` — **SIGN/FIGHT test**: triple sign product is negative. [V: line 885]
4. `0 < uVar25` — **LKAS command must be positive** (state 1 only, not state 3). [V: line 886]

### State 3 (bVar40 == 3) FIGHT Continuation [V: decompile lines 936-941]
Transitions to state 4 when ALL of:
1. `uVar9 < uVar13` — speed gate
2. `uVar19 < uVar28` — magnitude gate  
3. `sVar26 * sVar52 * gp-0x6af8 * 4 < 0` — sign/fight test
4. `uVar25 < 0` — LKAS command must be NEGATIVE here (opposite polarity from state 1)

### State 4 (bVar40 == 4) with counter check [V: decompile lines 944-950]
Counter `gp-0x6a74` must be < uVar10 (tp+0x729a), and same fight test fires re-entry.

### The Triple-Product Sign Test Decoded
`sVar26 * sVar52 * gp-0x6af8 < 0` means:
- **sVar26** = LKAS command sign: positive = push-right, negative = push-left
- **sVar52** = column direction sign (gp-0x6752): +1 or -1 (road/driver-driven rotation direction)
- **gp-0x6af8** = column angular velocity: signed, positive = wheel turning right, negative = left

The product is negative when the three signs are not all-same. Specifically, the LKAS command is fighting the column's self-driven motion (road/driver). This fires when LKAS pushes AGAINST the direction the column is already moving AND the column is moving fast enough (uVar9 < uVar13).

### Cal threshold for the governor term (separate SM gp-0x355e)
`tp+0x7422` (ABS 0xC7422) = 16384 (0x4000): the minimum governor value below which the gp-0x355e SM inhibits the authority reduction. [V: decompile line 980]

---

## Authority Gate: How gp-0x6960 Goes to Zero

When fight state gp-0x355d reaches state 2 (after state 3→2 transition at line 923):
```c
*(undefined2 *)(gp - 0x6960) = 0;    // line 923
*(undefined1 *)(gp - 0x355d) = 2;
```
gp-0x6960 = 0 → authority gate = 0 → LKAS demand multiplied by 0 → zero torque. The recovery ramp (tp+0x71d6 slew step) is 0 in stock firmware (= EME amplifier).

---

## Related memories
[[reference-accord-shaper-fun42af8]] — input/output chain and clamp stack
[[reference-accord-slew-limiter]] — tp+0x71d6 = 0 in stock, V16 FIX = 14
[[reference-accord-shaper-deadband-dropout]] — gp-0x6960 as authority gate
[[reference-accord-assist-mode-eme-dropout]] — state machine gp-0x4e65 overview
