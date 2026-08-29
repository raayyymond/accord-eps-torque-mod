# STATE archive

A RECORD, NOT AN INSTRUCTION.

## ✅✅✅ **V167 BUILT — THE KNOB FOR V158's ONE NAMED RISK. `0xC63A0` 1024 → 512.**
ONE HALFWORD on a V158 base, 56/56 assertions, CRC 50/50, **1 payload byte**.
```
   image 93970b6d65e10ff989b429efa1f387f52e48d7cba80938d1dd4f15dfa58ac61d
   rwd   b80180d89afdafb9579fc095dc254f7af8d7e9086c7abea35e36c81138ae53c4
```
### ⭐ `FUN_00038148` APPLIES PER-TERM WEIGHTS — AND ONE OF THEM IS THE DAMPER'S
```
   sum = (gp-0x6b4e * 0xC63A8 >>10) + (gp-0x6b4c * 0xC63AA >>10)   <- LKAS
       + (gp-0x6b26 * 0xC63A6 >>10) + (gp-0x6b46 * 0xC63A4 >>10)
       + (gp-0x6bd0 * 0xC63A0 >>10) + (gp-0x6bbe * 0xC63A2 >>10)   <- THE DAMPER
   sum = (sum * pol * cal) >> 10      <-- the EXTRA pol multiply that inverts the sign
```
✅ **[EVIDENCE] `0xC63A0` is `gp-0x6bd0`'s PATH-2 weight and nothing else.** Halving it halves the
**pumping** copy while **Path 1's damping is byte-for-byte untouched** — Path 1 reads the same cell in
a different function (`FUN_0003aa2c` @`0x3AC78`) with no such weight. The build asserts all five
sibling weights and both FactorC/FactorE records byte-identical.
✅ **[EVIDENCE] lowering is the safe direction**, in the model's own words for the sibling cell:
*“LOWERING is safe BY CONSTRUCTION — reducing a feedback magnitude cannot destabilise a stable loop
whatever its phase. RAISING is the classic destabiliser.”* History: **1024 on 137 images, 2048 on five
(V72/73/74/75/81) — raised and flown, NEVER lowered.**
✅ **[EVIDENCE] it is INERT without V158**: on V122 the damper is exactly 0 at creep, so `0xC63A0`
multiplies zero. That is why the base is V158.

### ⭐ IT REPLACES "REVERT" AS THE ANSWER TO V158's "WORSE" BRANCH
A bare revert to V122 discards **Path 1's damping along with Path 2's pumping** and tells you nothing
about which caused the regression. **V167 keeps the damping and removes half the pumping ⇒ it
DISCRIMINATES.** The decision tree is updated.

### ⚠ WHAT IS NOT ESTABLISHED
**[BELIEF]** that Path 2's pumping matters at all. Two effects push **opposite** ways and the net is
**not resolved**: Path 2 reaches the aggregator via `gp-0x6b70 → FUN_00037fe6 → gp-0x6ad6 → the PID
→ gp-0x6ad4`, whose ceiling is throttled to **170/1024 = 16.6 %** at creep by `0xC67C2` — but f′ is
**2.174 hands-off vs 0.346 hands-on**, so the observer is **6.3x MORE sensitive hands-off**, which is
where the ratchet lives.
**[NOTE]** the final linear gain also needs a **RAM LERP's local slope** (rows at `gp-0x64b8`/
`gp-0x641c`), which the model records as never successfully extracted. **512 is a HALVING, one notch
on a safe axis — NOT a computed optimum.**

