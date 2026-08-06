---
name: reference-accord-gp6ac2-is-a-backdrive-detector
description: gp-0x6ac2 is a SIGN-GATED back-drive detector, not a rate signal -- it is |motor rate|>>10 only when the motor rate opposes gp-0x6b98, and 0 otherwise. Consequence -- the damper ceiling 0xC77A0 is PINNED at its 512 floor in ordinary driving.
metadata:
  type: reference
---

# ★★★ `gp-0x6ac2` is a SIGN-GATED BACK-DRIVE DETECTOR — and it pins the damper ceiling at 512

**Corrects the standing description of this cell as a "steering angular rate".** It carries a rate
*magnitude*, but **only on frames where the motion opposes the command**; on every other frame it is
exactly 0. Anything that treats it as a rate axis reads a mostly-zero signal.

## The structure — [EVIDENCE], `decompile_function(0x41464)` on `code.bin`
`FUN_00041464`, the producer. `uVar16` is the filtered signed motor-rate quantity, `gp-0x6b98` the
torsion-bar / command signal ([[reference-accord-v55-flashed-oscillation-is-internal]]):

```c
uVar8 = (uVar16 < 0) ? -uVar16 : uVar16;          // |motor rate|
if ((int)uVar16 < 0) {
    if (-1 < *(short *)(gp - 0x6b98)) goto TAKE;  // motor -ve, bar +ve  -> OPPOSING
    uVar19 = 0;                                   // same sign          -> ZERO
} else {
    if (-1 < *(short *)(gp - 0x6b98)) goto ZERO;  // motor +ve, bar +ve -> ZERO
TAKE:
    uVar19 = uVar8 >> 10;                         // motor +ve, bar -ve -> OPPOSING
}
*(short *)(gp - 0x6ac2) = (short)uVar19;
```

⇒ **`gp-0x6ac2 = |motor rate| >> 10` iff `sign(motor rate) ≠ sign(gp-0x6b98)`, else 0.**
That is the definition of **back-drive / kickback**: the rack moving against what the ECU is asking for.

## ★ THE CONSEQUENCE — the damper ceiling never lifts in ordinary driving
The damper's output clamp is `ceiling = LERP(gp-0x6ac2, 0xC77A0[mode*4])`, and **all 26 modes carry the
identical record `X = [300, 800]`, `Y = [512, 1024]`** (byte-verified). In same-sign driving the index is
**0**, which clamps flat to `Y[0]` ⇒ **the ceiling sits at its 512 floor**, lifting toward 1024 only
during genuine opposing-sign kickback.

🛑 **Design consequence, and it is the load-bearing one:** any damper sizing must respect **512**, not
1024. The build-time no-clip assertion `(FactorC × FactorE[3]) >> 10 ≤ 512` is therefore the *real*
constraint, not a conservative one. See [[reference-accord-factore-x1-is-the-free-dose-lever]] for what
that permits.
⊕ On route 5d, V74's delivered dose reached the ceiling on **0 of 101,118 frames** — consistent.

## ⚠ The validity bypass writes a SENTINEL, it does not hold
```
0x41846  ld.h  -0x6b98,gp,r9
0x41852  addi  0x2000,r9,r11        \  (gp-0x6b98 + 0x2000) >u 0x4000  ->  |bar| outside +/-0x2000
0x41856  addi  -0x4001,r11,r0        }  i.e. the validity window fails
0x4185E  bc    0x000418ee           /   branch to the sentinel block
```
The target block writes **`0xFFFF`** to `gp-0x6ac2` **and** its lockstep shadow `gp-0x4cc6` (the
production path — the alternative arm needs a debug ROM signature `0x49d6b173` that is absent). It does
**not** hold the previous value.

🛑 **[OPEN] and worth closing before anyone leans on the ceiling:** whether the ceiling LERP reads
`gp-0x6ac2` as **`ld.h` (signed)** or **`ld.hu` (unsigned)** decides what the sentinel does — as s16
`0xFFFF` = −1 ⇒ ceiling clamps to the **512 floor**; as u16 it is 65535 ⇒ ceiling rails to **1024**.
One bit, opposite answers. `FUN_00041464`'s own reads at `0x41860` are `ld.hu`, but that is the lockstep
compare, **not** the ceiling's reader. Do not assume it.

## What this corrects
- **`reference_accord_corridor_lockstep.md`** describes the corridor's boost arm as
  *"boost = steering ANGULAR RATE gp-0x6ac2, out 0-2048"* (cal `0x7760`, X 700/800/1100, Y 0/1536/2048).
  The cell identity is right, **the label is not** — that arm is also fed a sign-gated quantity, so it is
  a **kickback** term, not a rate term, and it too reads 0 in ordinary same-sign driving. ⚠ I have not
  re-traced the corridor arm itself; the correction here is to the *cell's semantics*, which are shared.
- **`reference-accord-damper-two-deadzones-factorC-factorE.md`** calls the clamp
  *"DYNAMIC ±512..±1024 keyed on gp-0x6ac2"* — true, but the dynamic range is **almost never exercised**,
  which the wording does not convey.

Related: [[accord-v74-flew-damper-is-in-force]] · [[reference-accord-two-dead-zones-speed-and-rate]] ·
[[accord-gp6c2c-is-the-detector-input]] (the same function's other output, `gp-0x6c2c`, stored at
`0x4184E`)
