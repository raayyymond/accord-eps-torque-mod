# ADVERSARY UNIT-SCALE on V298 — FAIL criteria, written BEFORE any check ran

Written 2026-10-01 by the unit/scale adversary, before reading the image bytes or the build script.
The verdict on the built image `_v298_...A16A_plain_image.bin` (sha256 177abf04...) is DO_NOT_FLASH if
ANY of the following is demonstrated from the image bytes (Python LE byte read + Ghidra decode):

F1 FRAME MISMATCH ON THE ERROR. The setpoint operand (E4 ld.h gp-0x69ae) and the angle operand
   (E1 ld.h gp-0x6a00) are not in the same frame (scale and sign) as each other, so E = sp - x is not
   an angle error -- e.g. sp is in 0xE4 raw counts with a different LSB, an offset, or opposite sign from
   gp-0x6a00. A factor error >= 1.25x or a sign flip is a FAIL (sign flip = positive feedback = DO_NOT_FLASH).

F2 THE FEEDBACK OPERAND IS NOT WHAT THE DESIGN SAYS. r26 after E1/E2 + the b cal (0xC63EA) and the a cal
   (0xC63E8) does not equal k*(theta[n]+theta[n-1]) with the claimed k (8 per sample, 16 DC), or the
   E computation does not scale both sp and x by the same factor (a setpoint scaled differently from its
   feedback leaves a DC error / gain error = the "scaling a setpoint does not scale its feedback" class).

F3 SATURATION / OVERFLOW BEFORE THE CLAMP. Any intermediate (r26 sum, E, P=E*Kp, I accumulator, D term,
   cave products G*x) overflows its storage width (16-bit store of a 32-bit value, sign-extension of a
   halfword that can exceed 32767) at a reachable angle/rate (|theta| <= 540 deg wheel, |rate| <= 1000 deg/s)
   such that the delivered sign flips or the output wraps. A wrap that can flip torque sign = DO_NOT_FLASH.

F4 SPEED KEY MISREAD. The GB-P table X axis is not in the speed unit the design assumes (64 counts per km/h),
   or the cave reads a RAM cell that is not the vehicle speed in that unit, so the gain schedule is applied
   at the wrong speeds by >= 