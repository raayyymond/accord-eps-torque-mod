# redo-ghidra FAIL criteria (written BEFORE any Ghidra call, 2026-09-23)
F1 sign: operand at 0x28FA4 in V294 is s_old - s_new (or E adds r26 instead of subtracting) -> torque ASSISTS acceleration -> FAIL.
F2 scale: bytes give x != 8 counts/(deg/s) by more than +-25% (outside 6..10) -> FAIL; chain at 0x55B48 not holding -> scale is BELIEF.
F3 interlock: any governor/EME/lockstep/DTC/diagnostic reader of 0xC62E6/0xC63E8/0xC63EA/Kp bank/gp-0x3d30 outside the filter/PID -> FAIL.
F4 boundaries: any instruction boundary in FUN_00028ea6 differs V293 vs V294 -> FAIL.
F5 second consumer: r26 (or its r16 copy at 0x28FBE) read by a live path other than E formation, with a meaning that changes sign/scale unsafely -> FAIL.
F6 kick: a reachable path giving an unbounded (beyond +-1024 operand clamp) one-tick kick -> FAIL.
F7 0x14A cave reads P/I/D/S cells instead of delivered torque -> FAIL (telemetry would mis-attribute).
