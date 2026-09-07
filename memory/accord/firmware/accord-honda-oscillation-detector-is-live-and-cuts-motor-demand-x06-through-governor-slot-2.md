---
name: accord-honda-oscillation-detector-is-live-and-cuts-motor-demand-x06-through-governor-slot-2
description: 2026-09-06 (tracer, docs/traces/TRACE-2026-09-06-lag-and-fb-pole-census-v282.md addenda 2-3). Honda's oscillation-reversal detector FUN_000428d4 runs every 1 kHz tick with no engagement gate. It watches gp-0x6c2c = a doubly-filtered derivative of MOTOR ROTOR ANGLE (source gp-0x4f50, one writer in the 4 kHz FOC resolver estimator; input filter cal 0xC40DC = 14 on V282, corner 39.3 Hz; stock 22 = 67 Hz), counts alternate crossings past +/-cal(0xC620A)=12800 = 40 % of its 32000 full scale, resets the count if cal(0xC64DD)=50 ticks pass (so only >10 Hz counts), and after 15/20 reversals (375/500 ms at 20 Hz) ramps a cut via LERP 0xC694A (level 0/15/20/25 -> 32768/32768/19661/19661) that is passed BY REGISTER into governor slot 2 (FUN_00045608 -> FUN_0004503c) and MIN-folded into the Q15 motor-demand scale: x0.600 on the motor demand, slew-limited. The cut-factor RAM mirror gp-0x6994 has zero readers (dead diagnostic); the level byte gp-0x671a does nothing engaged on V282. No RAM halfword holds a usable reference for a cave comparator, so a "detector fired" bit is not buildable; the only buildable rung is |gp-0x6c2c| >= |gp-0x6c2e| (fast vs slow EMA of the same signal). The 2026-09-06 census found NO clean evidence it fires on any V282 grind episode (r39/r3a/r3c). The golden model's motor_torque_governor treats the scale as exogenous and cannot represent this cut.
metadata:
  type: reference
---

# Honda's oscillation detector is live and cuts motor demand x0.6 via governor slot 2 -- 2026-09-06

Integer mirror (EVIDENCE: FUN_00041464 producer, FUN_000428d4 FSM, FUN_0004503c governor):
```
u   = gp_0x4f50 * 0x400                 # rotor angle estimate, FOC ISR
u  += ((u - s1) * 37) >> 7              # cal 0xC643C, 54 Hz
d   = clamp((u - u_prev) * 0x20, +/-0xFA0000)
s2 += ((d - s2) * 14) >> 6              # cal 0xC40DC (V282 14, stock 22)
gp_0x6c2c = s2 >> 9                     # st.h; full scale 32000
# FSM: alternate crossings of +/-12800 within 50 ticks each; count -> level 0..25 -> LERP 0xC694A -> slot 2
scale  = min over 7 slots (seeded 0x8000)   # FUN_00049a78 = min
demand = (clamp(gp_0x6b94) * scale) >> 15  # then 512/205 slew, shaper, gp-0x6b98 -> FOC
```
**How to apply:** any lever that raises 20-40 Hz content persistently (a lag-pole raise to >=10 Hz fired it in 15 of 19 replayed windows) must be checked against this detector. A fired detector reads on the wire as a x0.6 step in motion per unit 427-tap torque 0.375-0.5 s after onset. Related: [[accord-grind1-cal-only-levers-on-v282-are-exhausted-the-lag-pole-is-a-waterbed-and-the-d-clamp-trades-the-ring]], [[accord-golden-model-does-not-implement-the-damper]].
