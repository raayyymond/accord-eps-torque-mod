---
name: accord-c40dc-is-the-band-limit-lever
description: 0xC40DC (alpha2, the accel cascade's second EMA pole) is virgin on all 102 images and at 14/64 holds 21.7 Hz exactly while cutting 20-35% over 61-300 Hz — but it must ship with the notch revert, and two of its three consumers are ungated.
metadata:
  node_type: memory
  type: reference
---

# `0xC40DC` (α2) — THE BAND-LIMIT LEVER. PRICED, PARTLY GATED, **V109 CANDIDATE**

★★★★ **EVIDENCE for the sweep and GATE 1; BELIEF for the sector argument.** Priced 2026-08-27,
**deliberately held out of V108.**

## WHAT IT IS
`0xC40DC` = **22** = α2, the SECOND one-pole EMA in the `gp-0x6c2c` cascade
(`FUN_00041464`: `gp-0x35a0 += ((d32 − gp-0x35a0) · cal(0xC40DC)) >> 6`, then `gp-0x6c2c = gp-0x35a0 >> 9`).
Read at `ld.hu 0x50dc,tp,r11` @`0x41626`. **`gp-0x6c2c` IS α2's own output** — α2 is UPSTREAM of it.
🛑 **Address anchored inside `FUN_00041464`, the accel cascade — NOT the observer block** where
`0xC40D2` (K1) and `0xC40BC` (the Coulomb knee, `FUN_0003b8f6` @`0x3bab4`) live. Adjacency is a trap here.

## WHY IT IS THE RIGHT LEVER
The lane peaks at 61.1 Hz (see [[accord-gp6b26-is-a-61hz-bandpass-and-v107-railed-it]]). Lowering α2
moves the peak down onto the mode and rolls off the skirt. Sweep with Y auto-scaled to hold 21.73 Hz:
```
 K2  peak_Hz  -3dB span      @3Hz  @7.79  @21.73  @61    @100   @200   @300   sector entry
 22   61.1   25.1-153.0Hz   1.000  1.000  1.000  1.000  1.000  1.000  1.000    74.1 Hz  <- today
 16   50.3   20.7-124.3Hz   1.011  1.045  1.000  0.855  0.787  0.740  0.729    58.9 Hz
 14   46.5   19.0-115.5Hz   1.021  1.074  1.000  0.796  0.714  0.660  0.648    54.0 Hz  <- pick
 11   38.5   15.3- 98.4Hz   1.062  1.181  1.000  0.668  0.572  0.515  0.503
```
⭐ **At K2 = 14 the DELIVERED response is FLAT across 18–30 Hz (1.024 → 0.966) and cuts 20–35 % over
61–300 Hz.** It de-rails **without giving back one count of mode-band damping** — which lowering the Y
row cannot do, because Y is a flat multiplier and any de-railing it buys is paid for one-for-one at
21.7 Hz.

## GATE 1 — CLEANEST POSSIBLE ON THE CELL, OPEN ON THE SIGNAL
- **The cal: exactly ONE gp/tp access image-wide, zero writers.** Ghidra + an independent Python LE scan
  agree after handling the `disp|1` trap (`hw2 = 0x50DD`, one hit at file offset `0x41628`); the 6-byte
  extended-displacement form finds zero additional candidates.
- 🛑 **THE SIGNAL IS NOT GATED.** `gp-0x6c2c` fans out to **THREE** consumers: the FOC motor-model float
  term, this friction lane, and the oscillation-detector FSM (`FUN_000428d4`, threshold
  `cal(0xC620A)` = 12800). **Two of the three were never verified against a RESHAPED rather than merely
  rescaled signal.** A cal with clean ownership feeding a signal with unverified fan-out is **not a
  cleared gate.**
- ⊕ Contrast with **α0 = `cal(0xC643C)` = 37, which IS shared**: the same `y0` EMA state feeds
  `gp-0x6abe`, `gp-0x6ac0` (the `0xC520C` cap-table index) AND the whole `gp-0x6c2c` cascade. **Never
  move α0 as part of this lever.**

## GATE 2 — CLEAN AT THE MODE, WITH ONE REAL COST
The torque phasor stays in the proven-safe **180–270°** sector at 21.73 Hz for every K2 from 22 down to
**3**; it crosses out at K2 = 2. **Floor any candidate at K2 ≥ 3.**
🛑 **The cost nobody priced: lowering α2 slides the 90–180° sector ENTRY DOWN**, 74.1 → 54.0 Hz at
K2 = 14 — *widening* the band in which the lane can structurally sustain oscillation by ~20 Hz. The
magnitude there is also cut (to 80–85 %), so the net is likely still positive, but **"an independent
second benefit" was REFUTED** — the sector boundary and the mode-band authority trade against the same
knob in the same direction.

## 🛑🛑 IT MUST SHIP WITH THE NOTCH REVERT OR NOT AT ALL
Across **54–74.5 Hz** — exactly the band K2 = 14 newly opens — V105's biquad coefficients leave the
parallel base-assist lane a geometric-mean **5.15× (+14.2 dB)** louder than Honda's, and **21.8× at the
sector's new entry point**, because Honda's own zero sits at **55.225 Hz** and V105 moved it to 25.5 Hz.
**Taking the band-limit while leaving V105's notch on the car moves the dangerous sector into the one
band where we deleted Honda's attenuation.** V108 reverts the notch (`0xC60A8`–`B7` → Honda's 16 bytes),
so the prerequisite will be on the car.

## DOSE — TAKE IT UNCOMPENSATED
Uncompensated at K2 = 14 the delivered dose is **×0.920 at creep** (below the ~9 % perceptual floor on
record), ×1.284 at 20 km/h and ×2.496 at ≥90 km/h. **Do not spend Y[0] to compensate**: the only
available buy-back is at the creep knot, which is where the relay is already worst (33.5 % at 10–25 km/h),
and it would push Y[0] to 97.8 % of the int16 floor to recover a number nobody can feel.
⭐ **The exact boundary: `29490 × 1/0.90 = 32,767` against a floor of 32,768 — a −10 % α2 cut is the LAST
one Y[0] can compensate at all.** Past that the int16 door closes permanently.

## 🛑 WHAT CANNOT BE PREDICTED
**Rail duty under a candidate α2 is NOT computable.** The only available method is the open-loop
push-through that was measured **32× wrong** on this exact lane, and α2 is upstream of `gp-0x6c2c`, so it
changes the very distribution any solve would stand on — which the 49.8 Hz, 1636.8-count-censored 427
channel cannot recover. **Size α2 from a measured drive at two α2 values, never from `|H|` alone.**
⊕ The direction (better, plausibly much better) is supported; the magnitude is not. If duty falls far
more than the ~20–35 % `|H|` cut predicts, a self-sustaining cycle broke — that is threshold behaviour
and only a drive resolves it.

## THE OLD VERDICT DOES NOT TRANSFER
`reference_accord_gp6b26_two_paths_reinforce_and_pole_fork_dead` moved **this same pole** to rotate the
21.7 Hz operating point **further INTO** 90–180° for more inertia-reduction, and found the Y cost
prohibitive. **This lever moves the same pole in the OPPOSITE direction — toward pure damping, AWAY from
that crossing at the mode.** The old "too costly" verdict was about crossing *into* 90–180° at the mode;
it does not apply to staying further away from it, which is what this does.

Related: [[accord-gp6b26-is-a-61hz-bandpass-and-v107-railed-it]] · [[accord-v80-damper-relay-and-grind1-inert]]
