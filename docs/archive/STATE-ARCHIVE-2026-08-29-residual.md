# STATE archive

A RECORD, NOT AN INSTRUCTION.

## ✅ **THE POINTER-TABLE MAP IS COMPLETE — ALL 37 ATTRIBUTED, NO NEW TORQUE-PATH LEVER**
The last large unexamined family is closed. Triaged by **what each function WRITES**, which is far
cheaper than decompiling and is decisive.
```
   FUN_000382d8  8 tables (0xCC9FC + 0xC7B40..0xC80B0)   writes gp-0x63e8..0x64a4, 0x62fc..0x630c
                 => ZERO aggregator-lane stores (strict scan).  gp-0x630c is read by FUN_000389ec,
                    the plausibility monitor that fires FUN_0004613e(0x4377) => MONITOR-SIDE.
   FUN_0003b338  0xC8198     writes gp-0x6b6e, gp-0x6a0a        not a lane
   FUN_0003b416  0xCA5DC     writes gp-0x6996                   not a lane
   FUN_0003b49a  0xCBCA4     writes gp-0x6b28 and gp-0x6b2a
                 gp-0x6b28 : **0 READERS image-wide => write-only telemetry, DEAD**
                 gp-0x6b2a : 1 reader, FUN_00037fe6 = the UNITY-weighted Path-2 term sum
                             => the plant-model / observer path. V89 already flew there and its
                                null is explained by f' COMPRESSION. Not new ground.
   FUN_00035154  0xC7888     writes gp-0x6bbe                   the boost lane, already characterised
```
✅ **[EVIDENCE] no unexamined pointer-table family reaches the torque path.**

### ✅ AND NO LOOP-WIDE LAG SOURCE AT THE SENSOR
`gp-0x4f60` (the torque sensor, feeding the PID error, r24's `dtorque` and the boost curve) has
**64 readers and 5 writers, all five in the 0x7Fxxx acquisition layer**. The model already confirmed
*“FUN_0007e74a has NO EMA/IIR anywhere, and gp-0x4f60 is a SINGLE physical measurement”* ⇒ **there is
no filter to de-lag.** The one remaining class of change that could add phase margin loop-wide does
not exist in this firmware. **CLOSED.**

### ⚠ SCANNER CORRECTION — V850 STORE OPCODES ARE 0x3A/0x3B ONLY
My triage scan treated **0x38–0x3B** as stores; **0x38/0x39 are LOADS**. That over-included, and it
briefly showed `FUN_0003b49a` “writing” `gp-0x4f60` when it only reads it.
⊕ The `FUN_000382d8` verdict is **unaffected**: an over-inclusive filter that found **no** lane
writes still finds none when tightened — the error was in the safe direction. **State which direction
a filter error runs before deciding whether a conclusion survives it.**

