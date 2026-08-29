# STATE archive — superseded when V168 was cut

A RECORD, NOT AN INSTRUCTION.

## ✅✅ **V158 ADDRESS-VERIFIED INDEPENDENTLY — AND WHY IT WAS IMMUNE TO V159's ERROR**
After the off-by-0x400 that killed V159, the lead build's addresses were re-derived **independently
and explicitly**, walking the pointer tables rather than trusting the builder.
```
   FactorC (L2 speed), pointer table 0xC9E9C -> records 0xD77BC / 0xD77D0 / 0xD77E4   (m25/26/27)
       m26 base 0xD77D0  X[0]@0xD77D2  Y[0]@0xD77DA  Y[1]@0xD77DC
       m27 base 0xD77E4  X[0]@0xD77E6  Y[0]@0xD77EE  Y[1]@0xD77F0
   FactorE (L4 rate),  pointer table 0xC9F84 -> records 0xD77F8 / 0xD780C / 0xD7820
       m26 base 0xD780C  X[0]@0xD780E  Y[0]@0xD7816  Y[1]@0xD7818
       m27 base 0xD7820  X[0]@0xD7822  Y[0]@0xD782A  Y[1]@0xD782C

   V158's six edits, each against its RE-DERIVED role:
       0xD77DA  FactorC m26 Y[0]    0 -> 429      0xD780E  FactorE m26 X[0]   60 -> 12
       0xD77EE  FactorC m27 Y[0]    0 -> 426      0xD7822  FactorE m27 X[0]   60 -> 12
                                                  0xD7818  FactorE m26 Y[1]  140 -> 539
                                                  0xD782C  FactorE m27 Y[1]  140 -> 539
   image diff V122 -> V158: 14 bytes = 10 payload + 4 CRC (0xD7FFC..0xD7FFF).  ZERO unattributed.
```
✅ **[EVIDENCE] all six cells match their independently re-derived roles exactly.**

### ⭐ THE STRUCTURAL REASON V158 COULD NOT SUFFER V159's BUG
```
   V159's addresses   computed as  tp + offset      -> one wrong digit = a wrong cell, silently
   V158's addresses   READ as ABSOLUTE POINTERS out of the image, then walked by a known layout
```
=> **no offset was ever added for V158**, so the **off-by-0x400 / off-by-0x1000 class cannot occur**
there. The pointer table *is* the ground truth, and a wrong pointer would land outside the image and
be caught by the `0x10000 < p < 0x100000` filter.
⭐ **RULE, generalised: PREFER POINTER-DERIVED ADDRESSES OVER OFFSET-DERIVED ONES.** When a table is
reachable through an in-image pointer array, walk the array — it is self-validating. Reserve
`tp + offset` arithmetic for scalars that have no pointer, and when you must use it, **add the offset
to `tp` explicitly and print BOTH** (the check that finally caught V159).
⊕ This also explains, retrospectively, why the **damper** work survived the audit while the
**lane-gain** work did not: the damper's records are pointer-reachable; the PID's lane gains are not.

### ✅ V158's STANDING
```
   addresses      VERIFIED independently, zero unattributed bytes
   dose           50 at the model's MEASURED operating point, inside its own [30,60] requirement
   shape          MONOTONE; dead zone opened by the AXIS, not by flattening Y[0]
   ceiling        9.8 % of the 512 creep ceiling -- a 10.2x margin to V80's bang-bang
   RULE 7         engaged modes 26/27, read from V106B, not assumed
   shared-axis    the PID schedule is FLAT at the operating point => the coupling does not bite
```
=> **every gate the golden model raised for this lever is now addressed.** V158 is the recommended
build.

## 🛑🛑🛑 **V159 SUPERSEDED — AN OFF-BY-0x400 ADDRESS ERROR, AND THE LANE GAINS ARE FLAT**
**V159 edits an unrelated cal on a false premise. It is superseded and must never be flown.**
```
   tp = 0xBF000
   tp + 0x7B1E  =  0xC6B1E     <- the REAL K_p X table
   V159 edited     0xC6728  =  tp + 0x7728   <- AN UNRELATED CAL
```
🛑 **I confused `0x7B1E` with `0x771E`** — an **off-by-0x400** address error, the same family as
the off-by-0x1000 trap `CLAUDE.md` records **six** times.

### 🛑 THE REAL TABLES KILL THE FINDING OUTRIGHT
```
   K_p  tp+0x7b1e = 0xC6B1E   X=[  0, 300, 2000, 4000]   Y=[ 256,  256,  225,  153]
   K_i  tp+0x7b0a = 0xC6B0A   X=[  0, 400, 1500, 3000]   Y=[  98,   98,   98,   98]
   K_d  tp+0x7ade = 0xC6ADE   X=[ 50, 400, 1500, 3000]   Y=[2048, 2048, 2048, 2048]
```
⇒ the operating point **`gp-0x6ac0` = 99 [94, 113]** lies in **segment 0 of every one of them**:
K_p is **256 -> 256 (FLAT)** from 0 to 300; **K_i and K_d are FLAT at every knot.**
⇒ **[EVIDENCE] ALL THREE PID LANE GAINS ARE FLAT AT THE OPERATING POINT. There is NO parametric
gain modulation there — not 18 %, not any.**
⇒ **the whole "parametric pump at lane gain A" line is VOID**, and so is V159.
✅ **The hypothesis is now CLOSED properly**, on the correct tables: the lane gains cannot be the
source of a 2f parametric pump, because they do not vary at the rate the symptom lives at.

### 🛑🛑 THE PROCESS FAILURE IS WORSE THAN THE ARITHMETIC
```
   1. computed tp+0x7b1e wrong (0xC671E)                  -- a digit error
   2. the garbage there happened to LOOK like a 4-knot table for lane A
   3. lanes B/C read NON-ASCENDING X                      -- the CORRECT symptom of a wrong base
   4. I RETRACTED -- right instinct, WRONG reason (blamed the LAYOUT, not the ADDRESS)
   5. I "verified" against the decompile -- and RE-DERIVED THE SAME WRONG ADDRESS
   6. UN-retracted, and built V159 on an unrelated cell
```
🛑 **The non-ascending X was the signal, and I read it twice and misdiagnosed it twice.**
⭐ **RULE: when a neighbouring record of the same family decodes as nonsense, suspect the BASE
ADDRESS before the LAYOUT.** A wrong base makes *every* record in the family garbage; a wrong layout
usually breaks them all *the same way*. **Lane A "working" while B and C were garbage was itself the
tell** — a correct base makes all three work.
⭐ **RULE: re-deriving an address the same way is not verification.** Step 5 felt like a check and
was not one. **Verify a tp offset by ADDING IT TO tp EXPLICITLY and printing both**, which is what
finally caught this.

### ✅ WHAT THIS COSTS AND WHAT IT LEAVES
⊕ **Nothing reached the car.** V159 was built and pushed but never flown.
⊕ **The lane-gain hypothesis is now closed on correct data** — a real result, not just a retraction.
🛑 **V158's shared-axis GATE 2 is now CLOSER to closable**: the model demanded FactorE edits be
sized against the PID's schedule on the same axis, and **that schedule is FLAT at the operating
point**, so **the coupling the model worried about does not bite at 99 counts.** That is the sizing
it asked for — done, on the right tables.
⇒ **V158 becomes the lead build again**, with its shared-axis gate substantially addressed.

