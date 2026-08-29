# STATE archive — superseded during the spectral-tilt work

A RECORD, NOT AN INSTRUCTION.

## 🛑🛑 **V154/V155 SUPERSEDED — `0xC63A6` IS A STRUCK CELL; AND THE EIGHT COEFFICIENTS ARE READ**
Continuing the queue audit against the golden model. Two results.

### 🛑 V154/V155 MOVE A CELL THE MODEL EXPLICITLY STRUCK
> 🛑🛑 *"**BUT NO WEIGHT MAY BE MOVED**: gp-0x6b70 is a PID **REFERENCE THAT GETS SUBTRACTED**,
> not an aggregator addend, so a weight change's SIGN is not determined by the forward path alone
> ... Path 2 **IS A REAL CLOSED LOOP** ... its loop gain lives in **EIGHT float coefficients** ...
> **NEVER BYTE-READ BY ANY SESSION** ... => **GATE 2 CANNOT BE CERTIFIED. `0xC63A6` was struck on
> exactly this.**"*

⊕ **My justification was right open-loop, and the model says so**: *"the two sign(iVar6) factors in
the chain rule SQUARE TO +1 AND CANCEL -- the unknown sign of iVar6 does NOT matter open-loop."*
🛑 **The flaw: I reasoned OPEN-LOOP about a CLOSED loop** -- precisely what GATE 2 exists to catch.
=> **V154/V155 SUPERSEDED, `.rwd` renamed.** This is the **same class of error as V156/V157**: built
from the lineage, contradicted by the golden model.

### ✅ THE EIGHT COEFFICIENTS -- BYTE-READ FOR THE FIRST TIME
```
   tp+0x504C  0xC404C   0.000000e+00  float   <-- EXACTLY ZERO
   tp+0x5050  0xC4050   0.000000e+00  float   <-- EXACTLY ZERO
   tp+0x50BC  0xC40BC   3000  the knee      tp+0x50D4  0xC40D4   573  model pre-filter (applied x2)
   tp+0x50D0  0xC40D0    408  bilinear EMA  tp+0x50D6  0xC40D6   246  rate-term EMA   (applied x2)
   tp+0x50D2  0xC40D2   1020  K1            tp+0x50D8  0xC40D8  3686  sensor pre-filter(applied x2)
```
=> **[EVIDENCE] two of the eight are EXACTLY 0.0, in stock and V122 alike -- and they are the two
multiplying the HISTORY terms.** In `FUN_0003b8f6`:
```c
   fVar14 = *(float*)(tp+0x5050) * gp-0xc9c8  +  fVar14 * fVar19  +  fVar15 * *(float*)(tp+0x504c)
          =        0.0 * gp-0xc9c8            +   10.0 * fVar19   +  fVar15 * 0.0
          =  10.0 * fVar19                                     (tp+0x5048 = 10.0)
```
=> **that three-tap structure is a PURE GAIN of 10.0 -- both memory taps are DEAD.**
=> **GATE 2 is NOT closed** (the RAM LERP's local slope is still unextracted, and `FUN_000389ec` has
defeated two attempts), **but the unknown loop gain now has TWO FEWER LIVE TERMS than the model
assumed**, and the eight values are on the record for the first time.

### ⭐ THE PATTERN ACROSS THIS AUDIT
```
   V156 / V157   mis-shaped   non-monotone FactorE, repeats V72's flatten-to-relay error
   V154 / V155   struck cell  0xC63A6, GATE 2 uncertifiable
   V158          CORRECT      built to the golden model's own measured prescription
```
=> **three of the builds I recommended this session were built from `BUILD-LINEAGE` rather than the
golden model, and two of them were wrong.** `CLAUDE.md` names the model as required reading; the cost
of skipping it was four superseded artifacts.

## ⭐⭐⭐ **THE AUTHORITY COMPLAINT HAS A SPECIFIC MECHANISM — AND THE OPERATOR DRIVES ON ITS KNEE**
Auditing the remaining queued builds against the golden model (the V158 lesson) surfaced the
authority answer, which was **already in the record** and which this session had not connected.
```
   the LKAS AUTHORITY COLLAPSE CURVE   0xE547C / 0xE5404 / 0xE52FC / 0xE5284, mode 7
   takes authority  254 -> 0  across raw driver torque  2240 -> 2560
   VIRGIN on all 90 images
   the OPERATOR's measured median override torque = 2235 = ONE COUNT BELOW the first knot
```
=> **[EVIDENCE] he drives on the knee of the authority collapse.** Any small increase in his input
takes authority from 254 toward 0 — which is exactly what *"LKAS authority"* would feel like when it
vanishes unpredictably under a push.
=> **this is a SECOND, DISTINCT mechanism from the +-4096 command rail** found earlier this session.
Both are real, both live at creep, and they are not the same thing:
```
   the +-4096 rail       the command hits its 13-bit PROTOCOL max, 6.4 % of frames at 2-8 km/h
   the collapse curve    authority is CUT BY THE FIRMWARE as driver torque crosses 2240
```

### 🛑 THE RULE THAT BLOCKS THE OBVIOUS FIX — AND IT IS A GOOD RULE
The golden model states it as a hard constraint:
> 🛑🛑 *"**Honda collapses authority BECAUSE the driver is pushing. Any change must be
> MONOTONE-NON-INCREASING: never more authority than stock at any torque.**"*

=> **moving the knee up** (so authority holds past 2240) **gives MORE than stock between 2240 and
the new knee => it violates the rule.**
=> the rule exists for a real reason: **raising this curve makes the car fight the driver harder
during an override.** That is a safety property, not a tuning preference.
=> **[DECISION] NOT proposed.** Like `0xC61BC`, this is an **operator decision about how hard the
car may resist him**, not an engineering call I should make.

### ⚠ AND IT WILL NOT HELP THE GRINDING
> 🛑 *"**NOT a 6-9 Hz lever — refuted five ways**; it drives the ~0.5-1 Hz SURGE."*

=> the collapse curve is a **surge** mechanism, not a ratchet mechanism. **Fixing it would address
LKAS authority and nothing else.**

### ☑ ALSO RE-CONFIRMED: `0xC64B8` IS DEAD, DO NOT RE-PROPOSE
The same memory records `0xC64B8` (V37's `0x70`->`0xFF`) as **structurally true, behaviourally
empty**: at mode 7 **both arms deliver 0 everywhere the branch could fire**, because all four curve
records clamp to `Y[last] = 0` above `X[last]` = 80 or 112, **below the gate's 113**. **Stock and V37
are bit-identical on this car.**
=> it *looks* compelling — non-stock for 66 builds, sitting exactly at high driver pushback — **and
it is empty.**

### ✅ WHERE THE THREE COMPLAINTS NOW STAND, MECHANISM BY MECHANISM
```
   grinding / ratchet   a mechanical resonance; firmware reaches EXCITATION and LOOP PHASE only
                        => V158, the golden model's own damper prescription, UNFLOWN
   LKAS authority       TWO mechanisms, both identified:
                          (a) the command rails at its 13-bit protocol max (6.4 % at 2-8 km/h)
                          (b) the collapse curve cuts authority above driver torque 2240,
                              and the operator's median override is 2235
                        => BOTH are barred from the obvious fix by safety rules the kit adopted
   peak command osc.    = (a) above, measured: sustained one-sided saturation
```
=> **every complaint now has a named mechanism.** Two of the three are blocked not by ignorance but
by **deliberate safety constraints**, and lifting either is **the operator's call to make
explicitly.**

