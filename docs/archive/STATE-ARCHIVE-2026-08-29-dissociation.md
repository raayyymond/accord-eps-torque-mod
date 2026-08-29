# STATE archive — superseded during the grind/ratchet dissociation work

A RECORD, NOT AN INSTRUCTION.

## 🛑🛑 **V139 SUPERSEDED — AND THE sar PAIR IS CLOSED AT 6x GAIN, BOTH DIRECTIONS**
The audit reaches V139 (both pump arms `sar 10 -> 11`). It is wrong, **and its own builder already
said so.**

### ✅ THE STATE ON THE CAR
```
   0x3AB76 (r26 arm)  stock imm5 = 10   V122 imm5 = 10    Lever A is NOT carried
   0x3AC20 (r24 arm)  stock imm5 = 10   V122 imm5 = 10
```
⇒ **V62's sar pair — which `eps_lkas_chain_model.py` calls "the kit's ONLY measured grind-#1 fix"
(18-22 Hz down 8-42x) — is ABSENT from the flying build.** The obvious move is to restore it.
**It is not the right move.**

### 🛑 BOTH DIRECTIONS ARE WRONG ON A 6x BASE
```
   sar 9   = DOUBLE the arm   V62's measured fix -- BUT MEASURED ON A 4x-GAIN BASE
                              V133 flew sar 9 on a 6x base => "massive, violent grinding"
   sar 10  = stock, on the car
   sar 11  = HALVE the arm    V139 -- and memory records "r24 HALF CAUSED grind #2"
```
⊕ **V139's own builder contains the decisive argument**, which I should have followed rather than
promoted the build:
> *"scaling V62's 4x optimum to V122's **6x base lands BETWEEN sar 9 and sar 10**, which argues
> Honda sar 10 is already about right for a 6x base and **sar 11 OVERSHOOTS**."*

⇒ **[EVIDENCE, on-car] sar 9 at 6x produced the worst grinding the operator has reported (V133).**
⇒ **[REASONED, in the builder itself] sar 11 overshoots the other way.**
⇒ **=> stock sar 10 is approximately optimal for the 6x base, and the sar pair is CLOSED as a lever
at the current gain.** **V139 SUPERSEDED; do not restore Lever A either.**

### ⭐ THE GENERAL LESSON — THE sar OPTIMUM IS COUPLED TO THE GAIN
V62's result was obtained at **4x LKAS gain**; the car now runs **6x**. **A measured optimum does not
transfer across a gain change**, because the arm's contribution scales with the command that feeds
it.
⇒ **this is why “restore the kit's only measured fix” is the wrong instinct here** — the fix was
measured in a configuration the car no longer has.
⇒ **[RULE] before restoring ANY historical fix, check the gain base it was measured on.** The same
caution applies to every pre-V101 result, since `0xC6CD0` moved 3564 -> 5346 at V101.

### ✅ THE QUEUE AFTER A COMPLETE AUDIT
```
   1. V158   damper, the golden model's own prescription, GATE 2 closed        <-- FLY THIS
   2. V150   r26 suppression switch      premise still unverified after V149's collapse
   3. V148   deadband + probe            an instrument, not a fix
   4. V151   knee 3000 -> 3600           marginal: the relay is ~99 % unsaturated
   -  V152 / V153                        GATE-2-OPEN on 0xC40D0, demoted
   X  V139 / V149 / V154 / V155 / V156 / V157                        SUPERSEDED
```
🛑 **SIX of the builds this session recommended are now superseded.** Every one traces to the same
cause: **designed from `BUILD-LINEAGE` and fresh decompiles instead of the GOLDEN MODEL**, which held
the structure, the prescriptions, the strikes, the measured fix and its gain-dependence all along.
**V158 is the one built from the model, and it is the one that survives.**

