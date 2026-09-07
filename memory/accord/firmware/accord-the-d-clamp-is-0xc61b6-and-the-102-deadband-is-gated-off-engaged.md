---
name: accord-the-d-clamp-is-0xc61b6-and-the-102-deadband-is-gated-off-engaged
description: 2026-09-06 (tracer census + adversaries A/D on V287). The LKAS rate PID's clamp family at 0xC61B4..0xC61BE, read from bytes. 0xC61B4 = T clamp (3072 on V282; ld.h/ld.hu MISMATCH at 0x2A20C -- never set >= 32768). 0xC61B6 = the D-TERM CLAMP 10240 (4 live ld.hu readers 0x29EE8/EF2/EF8/F02, symmetric via subr, inclusive at +/-L, memoryless because E_prev stores the UNCLAMPED error; 3 more readers sit in the unreachable duplicate PID FUN_0002a93a). 0xC61B8 = 102 post-lag deadband, GATED OFF WHEN ENGAGED (the block at 0x2A1BC is skipped when gp-0x6806 != 0), so the record's "P-only deadband = 0xC61B8" attribution of r39's engaged stall runs is WITHDRAWN. 0xC61BA = INTEGRATOR anti-windup ceiling 10240 (1 live reader, inert at Ki 0 -- the same-value trap as the P pair). 0xC61BC = P clamp 15360. 0xC61BE = sum clamp 15360 (same ld.h mismatch at 0x2A146). D and the PID sum (gp-0x6b36/0x6b34) are WRITE-ONLY, not on the wire; the clamp's binding is observable only through T. With Ki 0, on a rising command step where P rails and sign(D)=sign(P) the sum clamp masks a D-clamp edit exactly.
metadata:
  type: reference
---

# The D clamp is 0xC61B6 and the 102 deadband is gated off engaged -- 2026-09-06

```
dE = E - E_prev                # 0x29EE2; E_prev <- UNCLAMPED E at 0x2A18C
D  = (dE * Kd) >> 3            # 0x29EE4 mul, 0x29EEC sar 3 ; Kd 128 flat -> D = 16*dE
L  = u16[0xC61B6]              # 0x29EE8 ld.hu 0x71b6[tp]
D  = max(-L, min(D, L))        # 0x29EF0 ble / 0x29F00 bge -> inclusive; -L by subr r0
```
The build scripts (V270-V285) always had 0xC61B6 labelled correctly; the 2026-09-06 brief and Appendix B first named 0xC61BA. A build script MUST assert on the ADDRESS (displacement 0x71B6), because both cells hold 10240 and a value readback cannot tell them apart. Related: [[accord-grind1-cal-only-levers-on-v282-are-exhausted-the-lag-pole-is-a-waterbed-and-the-d-clamp-trades-the-ring]], [[accord-v281r3-flew-the-7hz-cycle-is-gone-the-p-only-deadband-arrived-understeer-is-mostly-sr-12-5]].
