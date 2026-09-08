---
name: accord-disengage-skips-the-pid-hook-and-gp-0x6cf8-is-hondas-first-tick-sentinel
description: "FUN_00028ea6 (the LKAS rate PID) runs every tick in normal ECU modes, but three flag-guarded jumps (0x29A5C/0x29A64 → 0x2A164; 0x29A70 → 0x2A0C6) skip everything from the setpoint to the PID and enter a SHARED epilogue (0x2A174) with r16 = 0x7FFFFFFF, stored to gp-0x6cf8 @0x2A18C; Honda reads it @0x29E5E as a first-tick-after-gap guard (|prev|>768000 ⇒ dE:=0). Any cave state added inside this function must be re-seeded on that sentinel or it freezes across disengagement."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 4fb8c05d-08ba-46ea-96e0-19a3b1899a03
  modified: 2026-09-08T05:31:08.910Z
---

# Disengage skips the PID hook; gp-0x6cf8 is Honda's first-tick sentinel (2026-09-07)

- Guard at 0x29A48–0x29A70: the hook region runs iff (engagement ramp gp-0x69b0 ≠ 0 OR gp-0x6805 == 1) AND inputs valid (r25)
  AND gp-0x680a ≠ 1. Ordinary openpilot disengage: demand → 0 while the ramp walks down (0.10 s / 2.05 s, cals 0xC63F4/F6/F8/FC),
  so the PID still runs with sp = 0; once the ramp reaches 0 every tick skips. [EVIDENCE, adversaries B + D, Ghidra]
- **0x2A164 is NOT a private reset routine.** It is the head of a shared epilogue; the engaged route enters at 0x2A174.
  A store added at 0x2A164+ would fire every tick. The reset constants (zeros + 0x7FFFFFFF→r16) are loaded only on the
  skip routes (0x2A16C; 0x2A0EA for the gp-0x680a lane) and r16 is not rewritten before 0x2A18C on either span.
- gp-0x6cf8 is 32-bit and private to the PID (one live reader 0x29E5E, one live writer 0x2A18C; two orphans in the dead copy).
  Boots to 0 (crt0 .data copy, ROM 0x863B8); 0 reads as a VALID state, but the first engage is always preceded by skip ticks,
  so the sentinel is present at every real engage.
- **Trap that produced a FAIL:** a cave state cell written only inside the hooked region is NOT reset with the rest of the
  PID state and freezes across disengagement; on re-engage it seeds a stale setpoint (up to 11 ms railed in the wrong direction
  after an override). V288 rev 1 did exactly this. Seed on `gp-0x6cf8 == 0x7FFFFFFF` (exact 32-bit compare).
See [[accord-v288r2-setpoint-prefilter-cave-built-adversarial-pass-passed]].
