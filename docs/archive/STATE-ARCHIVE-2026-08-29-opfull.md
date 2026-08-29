# STATE archive

A RECORD, NOT AN INSTRUCTION.

## ⛔ **THE PATH-2 WEIGHTS ARE NOT A LEVER FAMILY — AND WHY `0xC63A0` IS THE ONE EXCEPTION**
Having found that `FUN_00038148` weights every Path-2 term, the obvious next move is to lower the
others. **It is wrong, and the reason sharpens V167's own justification.**

### THE TEMPTING READING
Every term gets the **extra `pol` multiply**, so a Path-1 **damper** arrives as a Path-2 **pumper**.
`gp-0x6bbe` is a **measured** viscous damper (1.571 ct/(deg/s), phase ~0° vs rate) and, unlike the
base damper, it is **LIVE ON STOCK at creep**. Its Path-2 weight `0xC63A2` is **VIRGIN on all 142
images**. So it reads as a standalone ratchet lever that needs no V158 base.

### ⛔ WHY IT IS NOT ONE
**Path 2 is a DISTURBANCE OBSERVER.** It sums the assist lanes to predict what the motor is doing and
compares that prediction against a measurement. Lowering a term's weight does **not** simply remove
pumping — **it makes the observer's model WRONG**, biasing the residual by exactly the amount removed.
The pumping-signed arrival is not a defect to be trimmed; it is **what an observer subtracting a
predicted contribution is supposed to look like.**
=> lowering `0xC63A2`, `0xC63A4`, `0xC63A6`, `0xC63A8` or `0xC63AA` corrupts a model of a term the
firmware has always included. **Not built. Not proposed.**
⊕ This also retro-justifies the **strike on `0xC63A6`** (the `gp-0x6b26` weight, moved on the
superseded V154/V155): the objection is not only that GATE 2 was uncertifiable, it is that the edit
**de-tunes an observer**.

### ⭐ WHY `0xC63A0` IS DIFFERENT — THE ARGUMENT V167 ACTUALLY RESTS ON
```
   on V122 the base damper gp-0x6bd0 is EXACTLY ZERO at creep (FactorC Y[0] = 0)
   => the observer's creep-band sum has NEVER contained a damper term
   => V158 introduces, at FULL weight, a term the observer was never tuned to see
```
✅ **V167's 512 is therefore CLOSER to the observer's pre-V158 behaviour than V158's 1024 is.** It is
not "de-tuning a working observer" — it is **partially withholding a term the observer has no history
with**, on the one lane where that argument holds. **On every other weight the argument fails**,
because those terms have always been in the sum.
⚠ It still cuts both ways: if the motor really does produce the damper torque, the observer *should*
see it, and halving it biases the residual. **That is why V167 is a DISCRIMINATOR for the “worse”
branch and NOT a predicted improvement** — exactly how it is filed.

⭐ **THE GENERAL RULE**: **before lowering a weight, ask what the sum is FOR.** In a torque
aggregator a weight is a gain and lowering it reduces a contribution. In an **observer** the same
edit changes a *model*, and "less of the bad-signed thing" is the wrong frame entirely.

