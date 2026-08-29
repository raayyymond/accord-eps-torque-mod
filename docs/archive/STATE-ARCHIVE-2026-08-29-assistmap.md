# STATE archive — superseded during the base-assist-map work

A RECORD, NOT AN INSTRUCTION.

## ⭐⭐⭐ **THE PARAMETRIC PUMP IS LOCATED — LANE GAIN A's KNEE STRADDLES THE OPERATING POINT**
Mining the golden model for levers (the V158 lesson) surfaced a warning I had not acted on, and
acting on it located a mechanism the kit has hypothesised since V59.

### ⚠ FIRST, A CORRECTION: V158's GATE 2 IS NOT FULLY CLOSED
The model says, of any FactorE edit:
> 🛑🛑 *"**ALL THREE LANE GAINS ARE LERPs INDEXED ON `gp-0x6ac0`** (tp+0x7b1e / tp+0x7b0a /
> tp+0x7ade) — **the SAME rectified motor rate that indexes FactorE.** So a FactorE slope change and
> this PID's own gain schedule move on ONE axis; **they are NOT independent** … **[GATE 2 — size any
> FactorE edit against this, not just dose.]**"*

⇒ **V158 changes FactorE's slope and I priced it by DOSE ALONE.** I have been describing its gate as
*"closed by the model"* — **that was overstated.** The dose is the model's own priced figure; the
**shared-axis requirement was not met.** Meeting it now.

### ⭐ SIZING IT — AND THE RESULT IS A FINDING IN ITS OWN RIGHT
```
   lane gain A  tp+0x7b1e (0xC671E)  X=[96, 104, 608, 704]  Y=[704, 832, 832, 832]
      at gp-0x6ac0 = 94 / 99 / 113  ->  704 / 752 / 832     local slope 6.74 per count
   lane gain B  tp+0x7b0a (0xC670A)  FLAT at the operating point (slope 0.000)
   lane gain C  tp+0x7ade (0xC66DE)  FLAT at the operating point (slope 0.000)
```
🛑🛑 **Lane gain A's FIRST SEGMENT spans X 96 -> 104, and the model's MEASURED operating point is
`gp-0x6ac0` = 99 [94, 113] — DEAD CENTRE.** An **18 % gain swing across 8 counts.**
⇒ and `gp-0x6ac0` is a **RECTIFIED** rate, so during a 7.8 Hz oscillation it **sweeps at 2f =
15.6 Hz** back and forth across that exact window.
⇒ **[EVIDENCE] the PID's lane gain A is PARAMETRICALLY MODULATED at 2f, by ~18 %, at the symptom's
own operating point — and this is STRUCTURAL, present on STOCK.**
⊕ This is precisely what the model predicted qualitatively: *"a rate-scheduled gain on a RECTIFIED
index (which sweeps at 2f) interacts with the parametric pump"* — **now located and quantified.**
⊕ It is also a candidate mechanism for [[accord-v59-parametric-pump-marginal]] (*"the pump is real
but MARGINAL"*), which has never had a named source.

### ✅ THE LEVER THIS IMPLIES — FLATTEN THE KNEE, DOWNWARD
```
   stock   0xC671E  Y = [704, 832, 832, 832]  over X = [96, 104, 608, 704]
   lever            Y = [704, 704, 832, 832]  -- Y[1] := Y[0]
```
⇒ the 96–104 segment becomes **FLAT at 704**, so the 2f sweep sees **no gain change** ⇒ **the
parametric modulation at the operating point is REMOVED.**
⇒ **DOWNWARD is the safe direction**: it **lowers** PID gain between 96 and 104 rather than raising
it, and the ramp simply moves to 104–608, a **far gentler slope over a 6x wider span.**
⇒ **MONOTONE preserved** ([704, 704, 832, 832] is non-decreasing) — the shape rule that V157 broke.
⚠ **[BELIEF] that removing an 18 % parametric modulation is audible.** The mechanism is EVIDENCE;
the magnitude of its contribution is not measured.
⚠ **[UNVERIFIED] `0xC671E`'s reader count, mode-indexing and blast radius** — **RULE 7 is NOT yet
satisfied**, and the three tables' record layout was inferred from a 4-knot pattern that fits lane A
cleanly but produces implausible values for B and C (X=[256,256,0,8] and X=[717,0,0,5]), **so the
layout is probably NOT uniform across the three.** **Verify before building.**

⇒ **NEXT: verify `0xC671E`'s layout, readers and mode-indexing, then build it.** This is the first
new lever since V158 and the first with a named parametric mechanism behind it.

