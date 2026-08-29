# STATE archive

A RECORD, NOT AN INSTRUCTION.

## ⛔⛔ **I HAD THE PID's P AND D SWAPPED — THE STANDING RECORD CAUGHT ME**
Auditing older memory for claims this session overturned turned up two entries that **contradicted my
own phase computation**, and **they are right and I was wrong.**
```
   MEMORY-PART3: "Stage A = P (gain 153-256/1024) · Stage B = I (98/1024) · Stage C = D at 2048/1024 = 2.0"
   MEMORY.md:    "net phase lag -11 to -27 deg at 6-9 Hz · P:(I+D) ~2-5:1"

   my assignment (WRONG)            the record (RIGHT)
     0xC6B1E  256  = D                0xC6B1E  256  = P     matches "153-256/1024"
     0xC6B0A   98  = I                0xC6B0A   98  = I     matches "98/1024"
     0xC6ADE 2048  = P                0xC6ADE 2048  = D     matches "2048/1024 = 2.0"
```
I assigned the three gain LERPs from **Ghidra's variable numbering** (`uVar12/16/20`) instead of from
the record. Recomputed with the correct assignment:
```
                        |P|     |I|     |D|    P:(I+D)   net phase @7.8 Hz
   mine  (P,D swapped)  64.00   1.953   0.012   33.0:1     -1.7 deg
   CORRECT               8.00   1.953   0.098    4.3:1    -13.0 deg
   the standing record                          ~2-5:1    -11 to -27 deg
```
✅ **The corrected row lands inside BOTH recorded ranges.** ⭐ **Cross-check a fresh derivation against
the standing record before publishing it** — the record is a control, and here it was the only thing
between a wrong number and the handoff.

### ✅ WHAT THE CORRECTION DOES *NOT* CHANGE
**`gp-0x6ad4` is still not a damper, and V162/V163 stay superseded — the case is STRONGER.**
−1.7° was near-zero **stiffness**; **−13.0° is a LAG**, which is strictly *worse* for stability than
0°. Raising its ceiling adds loop gain **with negative phase** into a Q 14–29 resonance.
⚠ **But my "u16-bound, ~1300x too weak" margin was WRONG and must be restated:**
```
   Kd (Q10 Y at 0xC6AE6)   2048    8192   32768   65535 (u16 MAX)
   net phase @7.8 Hz     -12.97  -10.96   -2.72   +8.28 deg
```
=> the D gain would need **Kd ~ 163 (Q10 167,170)** to reach the P term, and **the u16 ceiling delivers
only +8.3°** — not the +1.06° I claimed. **The elimination stands** (real damping needs +90°), but the
honest margin is *"the D path tops out at +8° of lead"*, not *"1300x too weak"*.

### ✅ AND IT DOES NOT MOVE THE PATH-2 BOUND — WHICH IS THE POINT WORTH KEEPING
The bound is **invariant to the PID gain**, because the same `G_pid` appears in Path 2's route *and*
in the loop whose stability supplies the bound:
```
   Path2 = 0.615 x G_pid x s          L = G_gov x G_obs x G_pid x s < 1
   => Path2 <= 0.615 / (G_gov x G_obs)     -- G_pid CANCELS
```
✅ So **V158's net remains ×1.7–×2.7** and every downstream conclusion is unaffected. A bound built
from a *structural* relation survived an 8x error in one of its factors; a bound built from the
absolute number would not have.

## ⛔ **CORRECTION — THE PATH-2 THREE-TAP GAIN IS 1.0, NOT 10.0 (a 10x error in a loop gain)**
An audit of the memory index found an earlier entry claiming the observer's three-tap structure is
*“a PURE GAIN of 10.0, both memory taps DEAD”*. The taps-dead half is right; the 10.0 is not.
```
   FUN_0003b8f6:
      fVar14 = *(float *)(tp+0x5048);                   <- 1.0f   THE COEFFICIENT
      fVar14 = 0.0*hist + fVar14*fVar19 + fVar15*0.0;   => 1.0 * fVar19  IDENTITY PASSTHROUGH
      ...
      fVar14 = 10.0;                                    <- a CLAMP constant, LATER, same variable
```
✅ **[EVIDENCE] `tp+0x5048` = `0xC4048` reads 1.0f** (byte-verified, and it matches the long-standing
`c1 = 1.0f, c2 = 0.0f, c0 = 0.0f` memory). The earlier read grabbed the **clamp** where the
**coefficient** was wanted — Ghidra reuses `fVar14` for both.
⚠ **Why it matters**: the Path-2 stability bound divides by `G_gov × G_obs`. A 10x overstatement of
the observer's forward gain would have tightened the bound on `s` by 10x and made Path 2 look far
smaller than it is. The bound as computed used the correct 1.0.
⭐ **THE TRAP**: a decompiler reuses one local for unrelated values within a function. **Read the
assignment that feeds the expression you care about, not the last assignment to that name.**

