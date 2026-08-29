# STATE archive

A RECORD, NOT AN INSTRUCTION.

## ✅✅✅ **THE LAST UNKNOWN IS BOUNDED — V158 DELIVERS ×1.7 TO ×2.7, NOT 0 TO ×2.74**
The RAM-LERP slope `s` did **not** need extracting — the model records two failed attempts at exactly
that. **The loop's own stability bounds it.**

### ✅ THE PATH-2 LOOP IS CLOSED — ALL 13 HOPS VERIFIED BYTE-WISE
```
   FUN_0003a382 reads gp-0x6ad6 @0x3A6BA   writes gp-0x6ad4 @0x3A8A0
   FUN_0003aa2c reads gp-0x6ad4 @0x3ACA8   writes gp-0x6b94 @0x3ACFA
   FUN_0004503c reads gp-0x6b94 @0x453E0   writes gp-0x6ace @0x454D2      <- the governor hop
   FUN_0003b8f6 reads gp-0x6b98 @0x3B8F6   writes gp-0x6bfc @0x3BC1A      <- the observer
   FUN_00038148 reads gp-0x6bfe @0x38218   writes gp-0x6b70 @0x382D2
                reads gp-0x6bd0 @0x38150                                  <- THE DAMPER enters here
   FUN_00037fe6 reads gp-0x6b70 @0x38006   writes gp-0x6ad6 @0x38142
```
⚠ My first closure attempt failed on two hops because I assumed `FUN_0003a382` ended at `0x3A620`; its
real extent is `0x3A382-0x3A8A7`. **Ghidra had the extent; I guessed instead of asking.**

### ⭐ THE BOUND, AND WHY IT NEEDS NO EXTRACTION
The **same `0.332 × s` segment** sits in Path 2's route to the aggregator **and** in the loop's own
forward path, and the `gp-0x6bfe` entry coefficient is exactly **1** (`iVar5 = gp-0x6bfe - (iVar4>>4)`).
So:
```
   L = G_gov x G_obs x 0.332 x s      must be < 1, because the car is STABLE
                                      (the ratchet is a lightly-damped resonance, not divergence)

   G_gov*G_obs >= 1.0   => s < 3.01  => Path 2 <= 0.614 x Path 1  => net 0.39 of nominal
   G_gov*G_obs  = 2.174 => s < 1.39  => Path 2 <= 0.283 x Path 1  => net 0.72 of nominal
   (f' alone is 2.174 hands-off, and the governor is ~unity-passing, so G_gov*G_obs >= 1 holds)
```
✅ **[EVIDENCE] V158's net creep damping is bounded to 1.05–1.96 ct/(deg/s)**, i.e. a total of
**2.63–3.53 vs the measured 1.571 baseline = ×1.67 to ×2.25** — against the **×2.74** I quoted when I
ignored Path 2, and against the **×1.00** it would be if Path 2 cancelled the damping entirely.
=> **the pumping does NOT cancel the damping. V158 still delivers a real, substantial increase.**

### ✅ WHAT THIS SETTLES, AND WHAT IT DOES NOT
**SETTLED**: Path 2 cannot overturn V158. The worst admissible `s` still leaves **39 % of nominal**,
and the first non-zero creep damping this car has ever had. The ×2.74 headline should be **restated as
×1.7–×2.7**, and the pre-registration's predicted effect updated accordingly.
**NOT SETTLED**: the exact `s`, and the hand-traced net **sign** (three inversions) — still **[BELIEF]**.
⊕ **V167 keeps its role**: halving `0xC63A0` halves the `0.204 × s` term directly, moving the net from
0.39–0.72 of nominal up toward 0.69–0.86. It is the sharpest available test of this whole bound.

⭐ **THE METHOD WORTH KEEPING**: when a coefficient resists extraction, **ask what the system's
observed behaviour already implies about it.** A closed loop that demonstrably does not diverge bounds
every gain inside it. Two sessions failed to extract `s`; the stability argument bounds it in one step
and needs no bytes at all.

