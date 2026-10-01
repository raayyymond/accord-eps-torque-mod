---
name: reference_accord_gp6a00_angle_is_a_100hz_hold_inputs_fresh_at_1khz
description: gp-0x6a00 (steering angle, 0.1 deg, = 10x openpilot's raw angle) is written ONLY by FUN_0003e6d8 in RTOS slot 4 (FUN_00022ca0, 100 Hz) -> a 1-10 ms hold at the 1 kHz PID; its inputs gp-0x6cc4/gp-0x69ca are updated at 1 kHz by FUN_0003bd7c @0x2224a BEFORE the PID @0x22522. Formula, cals, sentinels, cave encodings.
metadata:
  type: reference
---

# `gp-0x6a00` is a 100 Hz hold; its inputs are fresh at 1 kHz (2026-09-30, stock code.bin = V295 bytes)

Trace: `docs/traces/TRACE-2026-09-30-angle-signal-gp6a00.md`. Mirror:
`analysis-2020accord/studies/angle_loop/angle_signal_mirror.py`.

**Scheduler [EVIDENCE].** Interrupt EIIC 0x340 sets `gp-0x42fc = 1` (`FUN_0001492a`). `caxi`
checkpoints call the dispatcher `FUN_00014be4`. It activates slot 0 (`FUN_0002214a`) on every pass and
slot 4 (`FUN_00022ca0`) when `gp-0x4304 % 10 == 4` (counter wraps at 100; `divq r7,r8,r10; cmp 4,r10`).
The activation syscall `FUN_000861e0` has exactly 5 callers, all in the dispatcher. The TCB table is at
`0xBB920 + i*0x30`: slot 0 attr `0x00010607`, slot 4 attr `0x00050207`. Slot 0 is activated first, so
the PID reads before the angle refresh. PID-side age is 1–10 ticks, mean 5.5 ms; the upper bound is
BELIEF because slot 4 is preemptible.

**Call sites (raw `jarl` scan, control `0x22522`):** `FUN_0003e6d8` @`0x22e32`, `FUN_0003f776`
@`0x22de2`, `FUN_000413ae` @`0x22e9c` — all slot 4. `FUN_0006bb08` @`0x221e0` (raw position snapshot
`gp-0x4ed8>>2` → `gp-0x4eea` → `gp-0x4ee8`), `FUN_0003bd7c` @`0x2224a`, `FUN_00040e7e` @`0x22426`,
`FUN_00028ea6` @`0x22522` — all slot 0.

**Formula [EVIDENCE].**
```
d = gp-0x6cc4 - gp-0x69d0
gp-0x69ca = int16(base + pol*(((d>>3)*1159>>8)*900>>14))       # base = gp+0x6470 unless 0x7FFF
gp-0x6a00 = int16(gp-0x3608 + pol*C(d) + gp-0x69ca)            # if gp-0x67fe in {1,2}, else 0
C(x) = sign(x) * LERP(int16(|x|*45>>9); X 0xC6892, Y 0xC68A2)  # FUN_0003e600
```
Linear scale is 32.168 motor counts per 0.1°, about 12.73° of wheel per motor revolution. `C` peaks at
+7.3° and has slope **1.155** of the linear term near centre. `gp-0x69d0` bleeds toward 0 by
`0xC6358` = 2 counts per tick (about 6.2°/s). The `−0x8000` baseline sentinel is **not** excluded at
`0x3C076`, so `gp-0x6a00` becomes garbage around +32700. Gate on `gp-0x679c == 3`. 0x7FFF is never
written into `gp-0x6a00`; it goes only into `gp-0x69ec/ee/ea`.

**Census of `gp-0x6a00` [EVIDENCE]:** Ghidra and the raw scan agree on 15 accesses with an empty
set-difference: 1 writer (`0x3e758`, `64 67 00 96`) and readers in `FUN_00040a50` (0x14A pack),
`FUN_0002e734` (10 Hz history) and `FUN_000557c8` (CAN 0x722). **`FUN_00028ea6` never reads it.**
Shadow is `gp-0x4c8a`.

Cave loads: `ld.h -0x6a00[gp],rX = 24 (rX<<3|7) 00 96` · `ld.h -0x69ca[gp],r26 = 24 d7 36 96` ·
`ld.w -0x6cc4[gp],r8 = 24 47 3d 93`.

Related: [[reference-accord-can-angle-producer-and-no-angle-correction]],
[[reference_accord_gp6a56_pid_feedback_is_a_100hz_hold]], [[reference_accord_gp679c_mode3_semantics_and_wire_bit]].
