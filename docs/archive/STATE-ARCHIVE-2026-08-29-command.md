# STATE archive — superseded during the command-oscillation work

A RECORD, NOT AN INSTRUCTION.

## ✅✅ **V158 VERIFIED FROM THE SHIPPED BYTES — AND THE POINTER-TABLE FAMILY IS CLOSED**

### ✅ THE DAMPER FUNCTION IS `FUN_00034350`, AND IT CARRIES **FIVE** TABLES, NOT FOUR
Decompiled 2026-08-28. The cascade the golden model describes is confirmed instruction-by-instruction,
and the **fifth table is the OUTPUT CEILING** — previously known only from the model's prose.
```
   L1 torque  0xC9CCC  4-knot   X[0]@+2  Y[0]@+0xA     axis |torque|      flat unity 1024
   L2 speed   0xC9E9C  4-knot   X[0]@+2  Y[0]@+0xA     axis gp-0x6a5e     Y[0]=0  <- creep dead zone
   L3 angle   0xC9DB4  5-knot   X[0]@+2  Y[0]@+0xC     axis gp-0x6a10     flat unity 1024
   L4 rate    0xC9F84  4-knot   X[0]@+2  Y[0]@+0xA     axis gp-0x6ac0     Y[0]=0  <- rate dead zone
   ceiling    0xC77A0  2-knot   X[0]@+2  Y[0]@+6       axis gp-0x6ac2     X=[300,800] Y=[512,1024]
```
⭐ **THE RECORD'S FIRST HALFWORD IS THE KNOT COUNT** (hdr=2 on the ceiling, 4 on L1/L2/L4, 5 on L3).
That is a **self-validating invariant** — any correct record read must have `hdr == len(X)` and X strictly
ascending. **It would have caught V159's off-by-0x400 instantly**, and it belongs in every build script.
✅ The ceiling's 512 floor is now **read from the image**, not taken from prose: `gp-0x6ac2` is a
sign-gated kickback detector (0 in same-sign driving) => the LERP clamps flat to Y[0] = **512**, and the
`>= 0x32c9` bypass lands on `0xC6158` = **512** too. Both paths agree.

### ✅ V158 RE-VERIFIED BY EXACT INTEGER ARITHMETIC ON ITS OWN SHIPPED IMAGE
```
   5 km/h, rate  60 ct : FactorC=429 FactorE= 66 -> dose  27      (stock 0)
   5 km/h, rate  99 ct : FactorC=429 FactorE=120 -> dose  50      (stock 0)   <- the operating point
   5 km/h, rate 200 ct : FactorC=429 FactorE=261 -> dose 109      (stock 0)
   build-time rule (FactorC x FactorE[3])>>10 <= 512 :  m26 388 PASS   m27 385 PASS
```
✅ **[EVIDENCE] dose 50 at the measured operating point** — the model's design target, and the exact
value V74 flew with **67.4 % engaged-creep liveness and 0 frames reaching the ceiling**.
✅ **[EVIDENCE] GENUINELY RATE-PROPORTIONAL, NOT A RELAY**: 27 -> 50 -> 109 across 60/99/200 counts.
That is the substantive GATE 2 test and V158 passes it.

### ⚠ CORRECTION TO THIS SESSION'S OWN RECORD — V158's FactorC ARM IS **NOT** MONOTONE
V158 leaves FactorC `Y = [429, 234, 429, 908]` (m26) / `[426, 233, 426, 875]` (m27): it **dips** between
35 and 60 km/h. I earlier certified V158 as "MONOTONE"; **that wording was wrong.**
✅ **The build is still correct.** The model prescribes `FactorC Y[0] := Y[2]` **explicitly**, knowing it
exceeds the monotone limit (it also records that `Y[0] := Y[1]` is *"the largest monotone lift of Y[0]
alone"*). The shape law exists to stop **FactorE** being flattened across the **rate** axis into a
bang-bang relay — a limit-cycle generator at a lightly-damped resonance. FactorC is **speed**-indexed and
*"costs NO rate-proportionality"*; vehicle speed varies over seconds and cannot pump a 7.8 Hz ratchet.
=> **the gate that matters is on FactorE, and V158's FactorE is monotone and rate-proportional.**
⭐ Lesson: **name the AXIS when applying a shape law.** "Monotone" is load-bearing on a fast axis and
merely cosmetic on a slow one; asserting it unqualified nearly cost the lead build.

### ✅ THE 37 POINTER TABLES ARE CLOSED — AND TWO ARE DEAD
35 of 37 are loaded by **exactly one `mov imm32` literal** in code, each now located. **`0xCC214` and
`0xCC914` have NO reference anywhere in the image** — no literal, no `movhi`+`movea` pair.
⛔ **`0xCC914` IS A DEAD TABLE.** Its double dead zone (`Y=[0,0,512,2560]`, zero below ~40 km/h) looked
like a creep lever and **is not one — nothing reads it.**
⚠ **The "single reference `movea 0xC914` at `0x3938E`" was a FALSE POSITIVE**: the instruction is
`movea 0xC914, r4, r30` with **r1 = r4 = gp**, i.e. `gp - 0x36EC` (a RAM cell that appears throughout
`FUN_000389ec`), not a table base. A raw byte scan for an immediate cannot tell a **base register** from
a **`movhi` partner**; the decompile settled it in one call. **Decompile first — again.**

