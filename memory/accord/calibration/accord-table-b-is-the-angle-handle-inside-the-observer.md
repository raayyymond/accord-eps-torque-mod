---
name: accord-table-b-is-the-angle-handle-inside-the-observer
description: "Decompiling FUN_0003b8f6 traces table (b) at 0xC6B66/0xC6B80: it is LERPed on gp-0x6a10 (absolute steering angle) and multiplies a model component that is then ADDED INTO the model, so it scales |model| - the exact amplitude that multiplies the Coulomb signum. Its Y row rises 899 to 1084 (1.21x) and saturates at 2.5 degrees, so it contributes only part of the measured 7-9x rise of |model| with angle. Flattening it to 899 is a modest, angle-targeted, cal-only lever that touches nothing below 2.5 degrees and is ORTHOGONAL to the K1/knee confound. Also confirms the 12 in the relay is a hardcoded 0xc immediate, so there is no third handle to break that confound."
metadata:
  node_type: memory
  type: reference
---

# ⭐ TABLE (b) IS THE **ANGLE HANDLE INSIDE THE OBSERVER** — and it is orthogonal to the confound

## [EVIDENCE] Traced by decompiling `FUN_0003b8f6`
```
   uVar17 = gp-0x6a10                                  <- ABSOLUTE STEERING ANGLE
   if (uVar17 < 0x2711) { LERP over tp+0x7b66 (X) / tp+0x7b80 (Y) }    = 0xC6B66 / 0xC6B80
   else uVar17 = 0x400;                                <- unity above the overflow gate
   fVar18 = fVar13 * uVar17 * 0.0009765625 + fVar18;   <- scales a model component INTO the model
```
⇒ **table (b) is an ANGLE-SCHEDULED gain on a model component, and its product is added into
`fVar18` = the model.** ⊕ `|fVar18|` is then exactly what multiplies the Coulomb signum:
`friction_in = |model| * K1/1024 * fVar13 + K0/1024 * fVar13`.
✅ **So table (b) sets part of the very amplitude whose angle-dependence makes the symptom
angle-gated** ([[accord-the-oscillation-excess-is-ANGLE-GATED]]).
```
   X (deg)  0.00  0.85  1.60  2.12  2.50  3.00 ... 11.94
   Y         899   908   981  1060  1083  1084  (flat to the end)      rise 899 -> 1084 = 1.21x
```
⚠ `|model|` was measured to rise **7-9×** with angle, and table (b) supplies only **1.21×** of that
⇒ **most of the angle rise is the model itself (physically more load at more angle), not this
table.** Do not oversell it.

## ✅ WHY IT IS STILL WORTH HAVING — it is ORTHOGONAL
[[accord-k1-and-knee-are-perfectly-confounded]]: every flown mod sits on `K1/knee = 0.34`, so `K1`
and `knee` cannot be separated without a gain change. **Table (b) is on neither axis** — it changes
neither the small-signal gain nor the relay's shape. ⇒ **it is an independent lever that does not add
another point to the confounded line.**
✅ And it is **angle-targeted by construction**: flattening `Y` to its low-angle value **899** cuts
the high-angle model contribution ~**17 %** and **touches nothing below 2.5°**, where the operator has
no complaint.
🛑 **Modest.** 17 % of one contributor to a 7-9× rise is a small lever, and
[[accord-factord-is-the-angle-error-lever]] already records table (b) as *"DEAD as a shaped lever"*
on the grounds that **88.6 % of engaged driving sits in its flat first segment** — true for broadband
driving, but the **angle-gated** symptom lives in the other 11.4 %. **Not a contradiction; a
different question.** [BELIEF that it is worth a build; NOT proposed yet.]

## ✅ A CLOSED QUESTION, RECORDED SO IT IS NOT RE-ASKED
The relay is `iVar20 = POL * gp-0x6abc * 0xc` — **the `12` is a HARDCODED IMMEDIATE (`0xc`), not a
calibration cell.** ⇒ there is **no third handle** with which to hold the small-signal gain while
varying `K1` independently of `knee`. **The K1/knee confound is structural and cannot be engineered
around; separating them requires accepting a gain change (V113).**
⊕ Also confirmed at the instruction level: `knee` is read at `tp+0x50bc` = `0xC40BC`, `K1` at
`tp+0x50d2` = `0xC40D2`, `K0` at `tp+0x5080` = `0xC4080`, the friction EMA pole at `tp+0x50d0` =
`0xC40D0` — all four match the kit's documented addresses.
