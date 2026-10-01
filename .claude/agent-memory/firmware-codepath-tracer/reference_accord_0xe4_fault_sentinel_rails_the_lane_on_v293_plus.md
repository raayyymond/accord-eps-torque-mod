---
name: reference_accord_0xe4_fault_sentinel_rails_the_lane_on_v293_plus
description: 2026-09-30. On an 0xE4 RX fault gp-0x69ae = 0x7FFF; the LKAS PID keeps running through the 2.048 s ramp-down and the map path turns the sentinel into idx 240 = full rail (torque mode, V293-V295) in one fixed direction; Honda's sign-hold gate (0xC64A3, 0x2A198..0x2A1E4) passes it only if the lane was already pushing that way. Downstream delivery not traced. Also pins the I-reset rules.
metadata:
  type: reference
---

**The lane arithmetic (EVIDENCE: decompile of FUN_00052676 and FUN_00028ea6, V295 bytes, mirror
`studies/angle_loop/lane_mirror_v295.py`):**

1. A fault path writes the sentinel: `movea 0x7fff` then `st.h -0x69ae` at 0x5268C, 0x52726 or 0x527C6. The
   same paths set gp-0x6805 and gp-0x6803 to 0xFF.
2. The validity flag fails, so gp-0x6807 = 3. The SM goes 2 → 4, gp-0x6806 := 0, and the ramp falls 16/tick
   (0xC63F6), which is 2.048 s.
3. The PID still runs, because ramp != 0.
4. r22 = clamp(32767, ±LIM 16384) = 16384. That gives idx 254 → 240, sp = +Y(240) = 1032 on V295, and P = 15480,
   clamped at 15360.
5. Sign-hold gate: once gp-0x6806 == 0 and cal 0xC64A3 == 1, T := 0 if |y| ≤ 0xC61B8 (102) or y·gp-0x6b30 ≤ 0.
   After that T stays 0.
6. Mirror, lane pushing the same way: T = 38/2245/1860/1259/57 at 0/100/500/1000/2000 ms.

**Compared with stock:** stock produced the max RATE setpoint (172), not max torque.

**Cal-only mitigation:** 0xC63F6 16 → 328, a 0.1 s fade. This also shortens a normal disengage.

**NOT traced:** whether the aggregator, EME or gp-0x67a4 cuts gp-0x6b38 on the same fault.

**I-reset rules (EVIDENCE).** I := 0 and E_prev := 0x7FFFFFFF on every skip tick. A skip happens iff
(ramp == 0 && gp-0x6805 != 1) or the inputs are invalid.
- Request drop: I resets ramp/16 ms later, 2.048 s from full ramp.
- Override latch (gp-0x6807 = 4 or 7) with the request bit held: the ramp falls 328/tick, then the PID runs at
  ramp 0 and **I is never reset**. It winds up and is re-applied on re-engage.

The golden model lacks the sign-hold gate and models a skip as "T = 0" only.

Related: [[reference_accord_angle_loop_in_place_edit_set_and_8bit_setpoint]].
