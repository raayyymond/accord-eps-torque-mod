---
name: accord-relu-plan-inverts-at-the-ceiling
description: A literal ReLU damper factor is expressible in 4 points but rails against the output clamp and re-creates the Coulomb relay — the breakpoint count was never the obstacle.
metadata:
  type: reference
---

**The operator proposed making both FactorC and FactorE literal ReLUs, and — fearing 4 breakpoints were
too few — building larger tables in free memory and repointing every reader. Both halves of that
mechanism are wrong, for reasons that are worth keeping.** [EVIDENCE — exact integer arithmetic over the
real evaluator, see [[accord-damper-evaluator-fun34350-ceiling-clamp]].]

## "Not enough points" is FALSE, and it was never the obstacle
A ReLU is **2 DOF**; a 4-point table has 8 numbers and spends 3 of them on collinearity. Both evaluator
clamps (`Y[0]` below `X[0]`, `Y[n-1]` above `X[n-1]`) and the u16 slope cap are **independent of the
point count**. "No plateau in the used range" is a **range** requirement, not a point-count one.
**More points buy EXACTLY ZERO for a pure ReLU.** Constructive witness meeting all five stated
constraints at n=4: `C X=[0,10815,21630,32445] Y=[0,8946,17892,26838]` ·
`E X=[0,4356,8712,13068] Y=[0,21824,43648,65472]` → C(515)=426, E(99)=496, **dose 206**, true-ReLU both,
`E_Y[0]=0`, X strict, Y monotone, **add-only 0 drops over 406,500 points**.

What `n` actually buys is **n−1 slope segments; n=4 gives THREE.** ReLU, ReLU+hold, and ReLU+hold+rise
are all expressible at n=4. Only a **four-segment** shape (ReLU+hold+rise+taper) needs n=5.
📋 **RULE: ask anyone proposing a re-point which FOURTH segment they need. If they can't name it, n=4 is
enough.**

## 🛑 THE CONSTRAINT THAT BREAKS IS PARAMETER-FREE
A ReLU FactorC is speed-proportional with its knee below 515 counts (5 mph), so
```
dose(v, 99) / dose(515, 99)  ==  v / 515        EXACTLY, whatever values you pick
```
Pinning **206 counts at 5 mph** therefore forces **3,593 raw counts at 140 km/h = 7.02× the 512
ceiling**, and 3.01× at 60 km/h. It **rails above 3.2 °/s at 140 km/h, 7.0 °/s at 60, 21 °/s at 20 km/h.**
**Choosing a different `C(515)` does not move this by one count.**

★★ **A railed damper whose sign comes from a DIFFERENT cell (`gp-0x6abe`) than its index (`gp-0x6ac0`)
IS the Coulomb relay** — describing function `4·512/(πA)`, unbounded as amplitude falls.
**You would forbid the relay at `E_Y[0]` and re-create it at the ceiling clamp.**
Contrast: the same 206 dose on V76's **flat** FactorC rails no earlier than **563 °/s — 176.7× more
usable linear range.**

## ⚠ "Which factor isn't a ReLU" has two readings that indict OPPOSITE tables
- **Literal `max(0, k(x−x0))`** indicts **FactorC**: a nonzero 566 floor, flat across three of its four
  segments, plus a top plateau.
- **The operator's own recorded gloss**, preserved in `v76_surface.py`: *"FactorC 'FLAT — no taper down,
  like a rectified linear unit'"*, read there as a **FLOOR CLAMP** — under which FactorC **already is**
  one (the V76 filename literally says `RELU`) and **FactorE** is the offender, with three slopes:
  2.521 / 0.100 / 0.259 per count.

⇒ **Neither should be made a literal ReLU**, and the reason is the ceiling clamp, not the shape naming.
When a shape word is load-bearing for a flash decision, **check how the kit recorded the operator using
it last time** before designing to it.

## Relocation is available — it just isn't needed
[EVIDENCE] Repointing is **cal-only**: one u32 into `FACTOR_C_PTRS+26*4 = 0xC9F04` or
`FACTOR_E_PTRS+26*4 = 0xC9FEC`. **`0xD7BB8`–`0xD7FEF` is 1,080 B of virgin `0xFF` in the same page and
the same CRC block (`0xD7FFC`) the V76 build already recomputes**; the identical run exists at the same
offset in every mode-record page (`0xD0BB8`…`0xE1BB8`). Confirmed unreferenced by a byte-granular
whole-image u32 scan — 4 raw hits, all disassembled to ordinary displacement/immediate fields, zero real
pointers. **V74's "the six pointer arrays must stay byte-identical to stock" was a SELF-IMPOSED BUILD
GUARD, not a firmware requirement**: the sole reader dereferences without comparison, the only flash
writer `FUN_0000d934` has zero static callers, and the CRC verifier `FUN_0000b006` is UDS-only with no
periodic app-side re-check. 🛑 Leave `0xD7FF0`–`0xD7FFB` alone — `0xD7FF8` is the block self-descriptor
(`d7 00 01 00`).

## 🛑 2026-08-07 — CONFIRMED ON-CAR, AND THE FLAT-FactorC ESCAPE IS **NOT** A SAFEGUARD

V80 did exactly what the "flat FactorC" line above suggested — flat `[566,566,566,566]`, **0.00% clip at
both ceiling 512 and 1024** — and **still flew as a Coulomb relay**, producing the worst grinding the car
has ever made ([[accord-v80-flew-the-damper-is-a-relay]]).
**The relay did not need the ceiling.** It moved to **FactorE's own knee, 17 counts under the rail**:
V80's FactorE `Y = [0,897,912,927]` makes the slope drop ~**1200×** at `X[1]` = 119, so dose is a constant
**495** (97% of 512) over a 34× rate range.
⇒ 📋 **RULE, and it generalises past ReLUs: a no-clip guard tests `product > ceiling` and is BLIND to a
relay formed by a knee below the ceiling. Gate the SHAPE — `dose(2r)/dose(r)`, or the describing-function
ratio `N(50)/N(500)` — not just the rail.** "Does not clip" and "is not a relay" are different statements.

⊕ **New Ghidra trap:** `get_xrefs_to(0xD780C)` returned **"No references found"** although the pointer
demonstrably exists at `0xC9FEC`; the twin `0xD77D0` resolved correctly. **Do not trust Ghidra xref
completeness on pointer-array slots** — cf. [[accord-v850-scan-traps-formatv-and-storezero]].
