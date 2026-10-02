# FAIL CRITERIA — adversary (ARITHMETIC), V299 built image — written BEFORE the attack

Target: `accord-firmwares/analysis-2020accord/_v299_…A16B_plain_image.bin`, sha256 30ff05fa464e87ab7eecfcbab9cbf6dfb3afcb57ceb5c89e4a29c1f748c38f08.
Base: V298 `177abf04…`. Method: my own decode of the image bytes (Ghidra dry-run on a disasm-only scratch copy + a
Python LE byte decoder written this session) and my own integer mirror; never the build script's constants.

## DO_NOT_FLASH if ANY of these is shown (EVIDENCE from the image)

1. **Bound inversion / runaway.** Any reachable input (θ s16 full range, E′ s32, v-word u16 full range, I8 s32 within
   what the Honda integrator with ICL can hold) for which the cap regime 0 ≤ v ≤ 2880 yields a bound > 6144, or
   v ≤ 1382 yields a bound > 4096, or the same-sign bound is *lower* than the opposite-sign bound in a way that
   lets |I| grow past the cap (i.e. the cap fails to cap). Includes: shl-4/shl-6 overflow of r9 wrapping to a small
   or negative value that `cmovh` (UNSIGNED compare) then fails to clamp, or a negative r9 reaching the
   unsigned compare (negative = huge unsigned → would be replaced by the cap, check the direction).
2. **Freeze that cannot release / never fires.** The raw-1229 hard freeze reading the wrong cell, the wrong width,
   or a signed word with an unsigned load such that one SIGN of driver torque always (or never) freezes; or the
   imm16 1229 being sign-extended/zero-extended into a different value.
3. **Sign error in the asymmetric clause.** sgn(E′) taken from the wrong register (e.g. E before the GB-P multiply,
   or a register clobbered between `mul/sar 8` and the compare) such that the |θ| term is granted to the
   OPPOSING-sign case (unwinding is throttled and winding is granted) — the exact inverse of the design.
4. **Winding comparison wrong.** `t = ±(I8>>10)` vs the bound compared with the wrong signedness/direction so that
   the integrator is allowed to wind past the bound in either sign, or the sar-10 floor bias makes the negative
   side admit ≥ 1 S-count more than the positive side **in a way that compounds** (unbounded), not merely a
   1-LSB asymmetry.
5. **Edge pathology at 1382/2880.** v-word jitter across 1382 or 2880 producing a bound discontinuity that drops
   BELOW the current |I| in the winding direction and thereby latches FRZ with I held, or, across 2880, a jump
   from a capped 6144 to an uncapped 64|θ|+1250 that admits an integrator step larger than the steady-state
   design (quantify the jump; > the design's own 12.5 m/s regime with no record = defect, a reachable
   ICL-scale step at the edge with no mention in the spec = DO_NOT_FLASH candidate, adjudicated by size).
6. **Freeze/bound vs ICL.** If the Honda integrator's ICL (8192 in S units or whatever the image says) is BELOW
   the cap such that the cap is vacuous, that is a defect (not a flash block); if the ICL lets I reach a value
   whose >>10 overflows the s16/s32 compare path, DO_NOT_FLASH.
7. **Image diff not the claimed 67 bytes**, a CRC that does not recompute, a branch into the re-laid span from
   outside it, a write (`st.*`) in the cave, or a register the Honda caller needs clobbered relative to V298.

## PASS_WITH_DEFECTS
Arithmetic quirks that are bounded and do not let the integrator exceed its intended bound by more than a few
S-LSB (e.g. sar floor bias of 1 LSB, a bound discontinuity at an edge that only makes the loop more conservative),
or documentation mismatches between spec and image that do not change behaviour.

## PASS
None of the above; my mirror agrees with the image-executed behaviour on exhaustive/targeted sweeps, and every
intermediate is shown in-range for the full input domain.
