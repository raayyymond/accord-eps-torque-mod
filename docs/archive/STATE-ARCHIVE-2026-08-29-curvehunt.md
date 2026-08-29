# STATE archive — superseded during the assist-curve hunt

A RECORD, NOT AN INSTRUCTION.

## 🛑🛑 **RETRACTED — THE "PARAMETRIC PUMP AT LANE GAIN A" WAS A TABLE-LAYOUT ARTEFACT**
Last turn I reported that lane gain A's knee straddles the measured operating point, giving an 18 %
parametric gain modulation at 2f. **I flagged RULE 7 as unsatisfied and said “verify before
building.” Verified. The finding is WRONG and is retracted in full.**

### 🛑 WHAT THE RAW BYTES ACTUALLY SHOW
```
   halfwords around 0xC671E:
     ... 0, 8, | 64, 65, 67, 73, 80, 88, 96, 104 | 608, 704, 704, 832, 832, 832, 832, 832 | 0, 4 ...
                 \________ one ascending run of 8 ________/
```
⇒ **`0xC671E` = 96 sits in the MIDDLE of that ascending run, not at a record base.**
⇒ my 4-knot reading (`X=[96,104,608,704]`, `Y=[704,832,832,832]`) **straddled the X/Y boundary** —
it paired the tail of the X axis with the head of the Y array. **The whole “steep knee at 99” follows
from that mis-split and nothing else.**
⊕ **The tell was in my own output and I noted it without heeding it**: the same layout gave lanes B
and C the implausible axes `X=[256,256,0,8]` and `X=[717,0,0,5]`. **A layout that produces nonsense on
two of three records is not a layout.**

### ⚠ AND THE PLAUSIBLE READING REVERSES THE CONCLUSION
Read as **count = 8, then X[8] = [64,65,67,73,80,88,96,104], then Y[8] = [608,704,704,832,832,832,
832,832]**, the operating point `gp-0x6ac0` = 99 falls between **X[6]=96 and X[7]=104**, where
**Y[6] = Y[7] = 832 — FLAT.**
⇒ **the gain is FLAT at the operating point, the OPPOSITE of what I claimed**, so there is no 18 %
modulation there at all.
⚠ **This reading is ALSO unverified** — stated as the plausible alternative, not as a finding.

### 🛑 AND I CANNOT VERIFY IT BY SCANNING
The `reg1 == tp` scan returns **NO readers** for `0xC671E`, `0xC670A` or `0xC66DE`. They are reached
some other way — a pointer table, a different base register, or an index computed at runtime.
⇒ **[UNRESOLVED] the layout, the readers and the mode-indexing of all three lane-gain tables.**
⇒ **all three of last turn's lane-gain readings are VOID**, including *“lanes B and C are flat”*.

### ✅ WHAT SURVIVES, AND WHAT THIS COSTS
✅ **The golden model's warning stands**: *"ALL THREE LANE GAINS ARE LERPs INDEXED ON `gp-0x6ac0` …
they are NOT independent … [GATE 2 — size any FactorE edit against this, not just dose]"*. That is
the model's statement, not mine, and it is **unaffected by my error.**
🛑 **So V158's GATE 2 qualification STANDS**: the shared-axis sizing the model demands **has still
not been done**, because **I could not read the tables it refers to.** V158's dose is the model's own
priced figure; **its shared-axis gate remains OPEN.**
⭐ **What this cost: nothing on the car.** The verification step caught it **before** a build — which
is the whole point of having flagged RULE 7 rather than proceeding. **Contrast V156/V157/V149/V139,
where I built first and audited later.**

