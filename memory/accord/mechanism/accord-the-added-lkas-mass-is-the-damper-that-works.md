---
name: accord-the-added-lkas-mass-is-the-damper-that-works
description: "I was one step from proposing a cut to the engaged friction row to reduce apparent LKAS steering mass, on the reasoning that gp-0x6b26 is computed from acceleration and is therefore added inertia. V94 flew exactly that argument, cut the cell 6x, and the operator aborted the drive - 'vibrated the entire car, not safe to drive'. Measured afterwards on two independent drives with a shuffled control, the delivered lane sits at +137/+139 degrees vs WHEEL rate at 6-9 Hz, giving +518/+565 counts of POSITIVE Re(Z): it is a real 6-9 Hz DAMPER. So the added apparent mass the operator feels IS the thing suppressing his oscillation, the two goals are in direct tension on this lever, and the tension is measured rather than assumed."
metadata:
  node_type: memory
  type: reference
---

# 🛑🛑 THE ADDED LKAS "MASS" **IS** THE DAMPER THAT WORKS — do not cut it

## WHAT I WAS ABOUT TO PROPOSE, AND WHY IT WOULD HAVE REPEATED THE WORST DRIVE IN THE RECORD
Chain I had assembled, each link individually correct:
1. The engaged friction row `0xCBE74` m26 is the **only** engaged-vs-manual asymmetry on the car
   ([[accord-the-only-engaged-asymmetry-is-the-friction-row]]), at **3.0×** stock since V107.
2. It scales `gp-0x6b26`, and [[accord-gp6b26-is-inertia-not-damping]] pins **in assembly** that
   `gp-0x6c2c` is a **first difference of filtered motor rate = ACCELERATION**
   (`0x41602 sub r7,r9`) ⇒ `gp-0x6b26 = −K·α` is **apparent inertia**.
3. ⇒ "we add 3× engaged-only steering mass, which is exactly what the operator forbade and explains
   *'max steering wheel acceleration and velocity still seem low for what I would expect for 6×'*."
🛑 **V94 flew that argument verbatim** — `builds/v80_v107/build_v94_tva.py:106,117`: *"it is apparent
inertia, nothing is dissipated, lowering is strictly safe on both binding bounds."* It cut the cell
**6×**. **Route `7d`, 2026-08-12: the operator ABORTED.**
> *"Made the stuttering and grinding worse, by a lot. So much so that it vibrated the entire car,
> and I decided it was not safe to drive."*  **No fault of any kind.**
Measured after the flight: motor acceleration **3-7× up above 9 Hz**; column-torque ↔ wheel-rate
coherence at 18-31 Hz **the highest of any drive in the corpus.**

## ✅ THE MEASUREMENT THAT SETTLES THE SIGN — two drives, ω-partialled, shuffled control
```
   delivered lane phase vs WHEEL rate at 6-9 Hz : +137 deg / +139 deg   (two independent drives)
   |cos| = 0.73  =>  +518 / +565 counts of POSITIVE Re(Z)
   => IT IS A REAL 6-9 Hz DAMPER, and V94 removed 6/6ths of it.
```
✅ **This is the first measured `d(symptom)/dK` this lever has ever had, and the sign says UP.**

## ⭐ THE RECONCILIATION — both records are right, at different layers
[[accord-gp6b26-is-inertia-not-damping]] is correct **structurally**: the term is built from an
acceleration. But **structure is not delivered effect in a loop with filters** — by the time it
reaches the wheel it carries **+137° against wheel rate**, which is dissipative. ⇒ **keep both notes;
neither supersedes the other.** ⊕ The desk figure *"+75°, 26 % dissipative, structurally cannot damp
6-9 Hz"* is separately retired — it was the *producer's* filter phase against *motor* rate, not the
delivered phase against wheel rate.

## 🛑🛑 WHAT THIS MEANS FOR THE OPERATOR'S TWO GOALS
The operator asks for **both**: *"low apparent steering mass and friction to LKAS AND no ratcheting."*
⇒ **On THIS lever those are in direct, measured opposition.** The apparent mass he feels under LKAS
**is** the 6-9 Hz damper that keeps the oscillation down, and V107's escalation to 3.0× — **90 % of
the int16 ceiling k_max = 3.3335** — is a large part of why V112 is his best build.
⇒ **Cutting it to buy acceleration is REFUTED ON THE ROAD.** The remaining headroom is only
**1.11× at Y[0]** before int16 overflow, so "more damper" is nearly exhausted too.
✅ **The honest statement to the operator: the low LKAS acceleration is the PRICE of the fix that is
working, it is measured rather than assumed, and buying it back on this cell costs the oscillation.**
Any acceleration gain must come from a **different** lever — not this one.
