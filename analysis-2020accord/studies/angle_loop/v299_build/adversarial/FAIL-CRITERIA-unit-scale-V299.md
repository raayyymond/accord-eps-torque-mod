# FAIL criteria — UNIT / SCALE adversary, V299 (written BEFORE the analysis, 2026-10-02)

Image under attack: `accord-firmwares/analysis-2020accord/_v299_V299-ANGLELOOP...A16B_plain_image.bin`
(sha256 to be re-hashed by me; expected `30ff05fa...`). Base for "unchanged" claims: V298 `177abf04...`.
I re-derive every unit from the IMAGE (Python LE bytes + GhidraMCP decompile), not from the spec or the build script.

## DO NOT FLASH if any of these holds (each is a unit/scale error that changes what the car does)

1. **Freeze threshold direction wrong.** If the writer of `gp-0x4f68` and the 0x18F (CAN 399) packer show that raw 1229
   corresponds to a wire value materially different from 1200 (e.g. raw = wire x 125/128, so raw 1229 = wire ~1259, or
   gp-0x4f68 is not |driver column torque| at all), so that the "hard freeze = Honda steeringPressed" equivalence the
   whole no-override ruling rests on is false by more than a couple of counts. A one-count rounding asymmetry is a
   DEFECT, not a FAIL.
2. **The I-bound is compared in a different unit than claimed.** If the quantity the cave compares against the bound
   (`I8 >> 10` with I8 = ld.w gp-0x6dd0) is not the same scale the spec calls "S", or if the cap 4096/6144 is >= the Honda
   ICL in the same unit (cap inert) or so far below it that the stated torque (6144 S ~ 983 T ~ 40 % rail) is off by
   >= x1.5 — i.e. the new upper level delivers materially more I authority than the page states.
3. **The v-word unit is wrong.** If gp-0x6a5e is not 230.4 counts per m/s (64 per km/h), such that 1382 / 2880 land at
   speeds outside ~[5, 7] / ~[11, 14] m/s (the cap switch moves into a speed band where the spec's F4 sims say the cap
   value trips overshoot), or the word is a different signal entirely.
4. **The theta unit is wrong.** If gp-0x6a00 is not 0.1 deg/count (e.g. 1/16 deg, or a rate), so that 16|theta| + 1250
   is not the bound the spec simulated by more than x1.5.
5. **Sign / width error in the cave's use of these units** that changes which regime is selected (signed vs unsigned
   compare on the v-word or the |torque| word; a 16-bit word that can exceed 32767 being sign-extended).

## PASS_WITH_DEFECTS (report, do not block)
- Spec-page arithmetic/percentage errors that do not change the image or its behaviour (e.g. a wrong derivation text
  for a correct constant), one-count rounding asymmetries, unverifiable-from-bytes claims labelled EVIDENCE.

## PASS
- Every unit above re-derived from bytes and the page's numbers agree within rounding.
