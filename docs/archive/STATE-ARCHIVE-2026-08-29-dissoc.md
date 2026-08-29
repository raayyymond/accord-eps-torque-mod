# STATE archive

A RECORD, NOT AN INSTRUCTION.

## ✅✅ **PATH 2's COEFFICIENTS ARE LOCATED — THE FIR CANNOT RING, AND THE MODEL'S NOTE IS STALE**
The model says Path 2's loop gain *“lives in EIGHT float coefficients … **NEVER BYTE-READ BY ANY
SESSION** … => **GATE 2 CANNOT BE CERTIFIED**”*. `FUN_0003b8f6`'s decompile settles it: **only THREE
are floats.** The rest are `ushort` reads converted and scaled in code — which is why reading them
as float32 returned denormals.
```
   GENUINE float32:              u16 EMA coefficients (read as ushort, scaled in code):
     c1 tp+0x5048 = 1.0f           tp+0x50D4 = 573   a=0.1399  fc  22.3 Hz  |H|0.951 lag 16.6 deg
     c0 tp+0x504C = 0.0f           tp+0x50D8 = 3686  a=0.8999  fc 143.2 Hz  |H|1.000 lag  0.3 deg
     c2 tp+0x5050 = 0.0f           tp+0x50D0 = 408   a=0.0996  fc  15.9 Hz  |H|0.906 lag 23.7 deg
                                   tp+0x50D6 = 246   a=0.0601  fc   9.6 Hz  |H|0.784 lag 37.0 deg
   y = 1.0*x + 0.0*x[n-1] + 0.0*x[n-2]      tp+0x50D2 = 1020  = K1, a GAIN not a pole
   = IDENTITY PASSTHROUGH                   tp+0x50BC = 3000  = the relay KNEE, a divisor
```
✅ **[EVIDENCE] the 3-tap FIR is an IDENTITY PASSTHROUGH with both history taps multiplied by 0.0**
⇒ **2 zeros, 0 poles, no feedback path — IT CANNOT RING, whatever the input.** This confirms the
existing `0xC4048` memory (`c1=1.0f, c2=0.0f, c0=0.0f`) from the consuming code rather than from bytes.
✅ **[EVIDENCE] every Path-2 pole is now located and quantified.** The model's *“never byte-read”*
and *“GATE 2 CANNOT BE CERTIFIED”* notes are **superseded for the DYNAMICS**: ringing is structurally
excluded and the cascade is known.

### ⚠ BUT THIS SHARPENS V158's RISK RATHER THAN CLEARING IT
`tp+0x50D6` = **246 ⇒ corner 9.6 Hz, sitting IN the ratchet band**, and the decompile applies it
**TWICE** (`fVar15` then `fVar19`) ⇒ a double EMA: **|H| = 0.784² = 0.615, lag = 2 × 37.0 = 74° at
7.8 Hz.**
🛑 **AND f′ RUNS THE WRONG WAY FOR US**: memory records `f′` p50 **2.174 hands-off vs 0.346
hands-ON** — the observer lane is **6.3x MORE sensitive hands-off**, and **the ratchet is a hands-off
creep phenomenon.** So Path 2's pumping-signed copy of `gp-0x6bd0` is at its **LARGEST exactly where
the ratchet lives.** I had earlier cited f′ compression as reassurance; **read in the correct
direction it is the opposite.**
⊕ What is still uncertifiable is the **relative WEIGHT** of Path 1's damping and Path 2's pumping into
the final motor command — Path 2's route runs through the hop the model flags as *“AT LEAST ONE
UNRESOLVED HOP”* (`gp-0x6b94`'s 4 unchecked readers: `FUN_00036bec`, `FUN_0004503c`, `FUN_0004595a`,
`FUN_0007ff08`). **[OPEN] closing it needs those four decompiles.**
⭐ **NET POSITION ON V158, STATED HONESTLY**: Path 1 damping is the primary and by design; Path 2
pumping is real, attenuated to 0.615 by the double 9.6 Hz EMA but amplified by hands-off f′; and V74
already flew this dose without an adverse report. **It remains the right build to fly — and the
“worse” branch of the pre-registered tree now has a quantified mechanism, not a hand-wave.**

