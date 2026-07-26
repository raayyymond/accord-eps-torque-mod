---
name: accord-assist-mode-eme-dropout
description: 2020 Accord EPS assist-mode state machine (gp-0x4e65) and the EME dropout trigger path — torque-sensor plausibility inhibit → state 3→1 ratchet, no DTC
metadata:
  type: reference
---

## Assist-mode byte gp-0x4e65 (abs 0xFEDF319B)

State values: 0=NORMAL, 1=STARTING/RAMP, 2=ACTIVE, 3=TRANSITION, 4=FAULT.

State machine lives in two functions:
- `FUN_00065eda` (0x65EDA) — outer manager; tests fault gates, writes mode to both gp-0x4e65 AND mirror gp-0x4458 (lockstep check via FUN_0006b9ee on mismatch)
- `FUN_0006651e` (0x6651E) — inner sequencer; handles state 0→FUN_0006634e, state 1/2→FUN_00068dfe, state 3 convergence check

Fault gates in FUN_00065eda that bypass normal assist:
1. `FUN_000197d0(0xf)` = bit 15 of gp-0x6d78 fault register
2. `FUN_0006fd42()` returning 1
3. `gp-0x4e6a == 1` (inhibit flag)

State-4 trigger: `FUN_0005b2be(4)`, `FUN_0005b2be(5)`, or `FUN_0005b2be(0x2A)` returning 3 → cVar14 forced to 4 before lockstep write.

## EME dropout path (Era-15 confirmed)

The EME fires via state 3→1 (NOT state 4 / no DTC):
1. Driver hand torque on sharp turn → dual-coil column torque sensor ADC channels (gp-0x6a44/40/3c/38/46) exceed inter-channel delta threshold in `FUN_00041eec` (plausibility voter, threshold ~0x7D00=32000)
2. Plausibility inhibit fires → gp-0x4e6b set (re-init flag) or state forced to 3
3. State machine re-runs states 3→1→2 ramp cycle
4. Shaper deadband tp+0x7424=0xC6424=29491 (~90%) + slew step tp+0x71d6=0xC61D6=0 (no ramp) → hard zero of gp-0x6b98 output
5. Re-engage through the deadband from zero takes ~10s → "heavy + jerky/ratcheting" wheel
6. 2× arb gain (V14: tp+0x746c=1782) amplifies a normally-imperceptible inhibit into a violent assist loss

The plausibility threshold in FUN_00041eec is a genuine safety detector — DO NOT widen it.

## Fix levers (ranked)

1. **Slew step 0xC61D6 → 14 (0x0E 0x00)** — enables incremental ramp; most direct fix
2. **Ramp step byte 0xC64DE byte[0] → 25–30** — faster re-engage after dropout
3. **Re-engage init-wait 0xC6288 → 150–200** — shorter mandatory wait
4. **Ramp ceiling 0xC628A → 600–700** — faster ramp to full assist
5. **Shaper deadband 0xC6424 → 20000–22000** — reduces dropout frequency; floor=50%(16384)
6. **Arb gain 0xC646C → ~1300** — reduce EME frequency, sacrifice some 2× gain

See [[reference-accord-slew-limiter]] and [[project-accord-torque-mod-v0]] for related notes.
