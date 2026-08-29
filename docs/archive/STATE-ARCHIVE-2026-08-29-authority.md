# STATE archive — superseded during the authority measurement

A RECORD, NOT AN INSTRUCTION.

## ✅✅ **THE `(0, N)` KNOT-COUNT HEADER — AND THE LANES B/C ANOMALY IS CLOSED**

### ⭐ EVERY CAL LERP IS ANCHORED BY A 2-HALFWORD `(0, N)` HEADER, N = THE KNOT COUNT
```
   layout:   [0][N]  X[0]..X[N-1]   Y[0]..Y[N-1]        (inline tp-relative cals)
             [N]     X[0]..X[N-1]   Y[0]..Y[N-1]        (pointer-table records, hdr at +0)
   validated 0xC6000-0xC7000: 54 WELL-FORMED (header + N strictly ascending X) vs 8 false positives
```
✅ **[EVIDENCE] this is the general layout, not a pattern-match on one table.** It gives a
**self-validating anchor**: a correct read must have `hdr == len(X)` with **X strictly ascending**.
⭐ **PUT THIS CHECK IN EVERY BUILD SCRIPT.** It catches a wrong address, a wrong knot count and a wrong
stride *in one assertion* — all three of the failure modes that cost this session builds.

### ✅ THE "LANES B/C NON-ASCENDING X" ANOMALY IS RESOLVED — IT WAS AN OFF-BY-2-HALFWORD READ
Anchored on the header, all three PID lanes are **well-formed**:
```
   lane A  0xC6B1E   X=[  0, 300, 2000, 4000]   Y=[ 256,  256,  225,  153]
   lane B  0xC6B0A   X=[  0, 400, 1500, 3000]   Y=[  98,   98,   98,   98]     FLAT
   lane C  0xC6ADE   X=[ 50, 400, 1500, 3000]   Y=[2048, 2048, 2048, 2048]     FLAT
```
(V159 reported `[256,256,0,8]` and `[717,0,0,5]` — those are a Y-tail plus the next `(0,N)` header.)

### ⛔ V159's MECHANISM DOES NOT EXIST — THE THREAD IS CLOSED ON EVIDENCE, NOT JUST ON ITS ADDRESS BUG
V159 was built on *"an 18.2 % parametric modulation of K_p at 2f, at the symptom's own operating point"*,
from a claimed `X=[96,104,608,704] Y=[704,832,832,832]`. **That table is not lane A.** Lane A's real
schedule is `X=[0,300,2000,4000] Y=[256,256,225,153]`, and the measured operating point
**`gp-0x6ac0` = 99 [94,113] lies in segment 0, where Y is FLAT at 256.**
=> **there is NO gain swing at the operating point**, at 2f or any other frequency. Lanes B and C are
flat constants across their whole axes.
✅ **THE LANE-GAIN PARAMETRIC-PUMP HYPOTHESIS IS NOW CLOSED BY DIRECT BYTE EVIDENCE**, not merely
"flat at the operating point" — a second, independent derivation agreeing with how V158's shared-axis
GATE 2 was closed.
⊕ What V159 would actually have done: `0xC6728` is `Y[3]` of an **unrelated 8-knot** table at `0xC6712`
(`X=[64,65,67,73,80,88,96,104]`, `Y=[608,704,704,832,832,832,832,832]`) — it would have set that Y[3]
832 -> 704. **The supersede was correct**, and the blast radius is now known rather than guessed.

