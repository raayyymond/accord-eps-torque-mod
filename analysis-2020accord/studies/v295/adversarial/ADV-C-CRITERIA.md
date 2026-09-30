# ADV-C (build-script audit) — FAIL criteria, written BEFORE any computation

Adversary C, V295. Written 2026-09-30 before re-hashing, rebuilding or diffing anything.
Target: V295 = V294 + ONE cal cell 0xC63EA (u16 LE) 567 -> 1050, + recomputed CRC trailer of its block.

Any ONE of the following makes the verdict **DO_NOT_FLASH**:

- F1  The on-disk V295 plain image does not hash to 5c044d65...0452ed, OR the on-disk V294 base does not
      hash to 3143616d...dbdd85 (the build is not what was reported / the base moved).
- F2  My OWN rebuild (V294 image + my own u16 LE write at 0xC63EA + my own CRC walker, algorithm and
      block table re-derived from the firmware/bootloader, not imported from the kit) does NOT reproduce
      the on-disk V295 image byte-for-byte.
- F3  The full-file diff V295 vs V294 over [0x13000, 0x100000) contains ANY byte other than
      0xC63EA, 0xC63EB and the 4 trailer bytes of the block that contains 0xC63EA — or any byte in the
      code region [0x13000, 0xC0000) differs.
- F4  The V295 value at 0xC63EA is not 1050 (0x041A) read LE, or the neighbours 0xC63E8 / 0xC63EC
      differ from V294.
- F5  ANY CRC block in the V295 image fails verification under my own walker (bootloader walk and the
      full chain), or the edited block's trailer is wrong.
- F6  My OWN .rwd decoder does not decode the V295 .rwd back to exactly the V295 image over the flashed
      range, or the .rwd's own checksum is invalid, or the rwd header / part number / range is not the
      same shape as the V294 rwd (a V294-vs-V295 rwd diff that is not explained by the 6 image bytes).
- F7  More than one flashable V295 .rwd (or more than one V295 plain image) exists on disk, or the V294
      revert .rwd is missing or no longer hashes to a2b418f0...9f706a.
- F8  A numeric claim in the docstring/report that is DECISION-BEARING (rail, trim cap, sub-rail slope,
      restart-pulse max vs the 288 cap, int32 margin >= 2, |P/x| at 20 Hz < x3 of V294) is false when
      re-derived from the image. (A cosmetic mismatch is a DEFECT, not a FAIL.)
- F9  The build script's mutation test does not catch a mutation it claims to catch, or one of MY two
      extra mutations (chosen by me) passes all of its assertions while producing a different image.
      (Caveat written in advance: a mutation that the build's physics gates cannot tell apart, e.g. a
      1-count dose change, being caught only by a readback is a DEFECT in the assertion set, not a
      FAIL — the hash pin still catches it.)
- F10 The cumulative non-stock delta table in the docstring/report omits a cell that differs between the
      V295 image and stock over [0x13000,0x100000) (excluding CRC trailers), or lists a wrong
      stock/current value for a cell.
- F11 Something outside the declared V295 artefacts changed in either repo (git status of the kit and of
      accord-firmwares) in a way that touches a flashable artefact (rwd/plain image of another build).

**DEFECT (reported, not blocking):** vacuous/tautological assertions over-counted as substantive; stale
hard-coded expectations; naming inconsistencies; report text that disagrees with the image on a
non-decision-bearing number; census label errors.

**What a PASS looks like:** F1–F11 all silent, with each check done by a method independent of the build
script (own write, own CRC, own rwd decoder, own diff), and the V294 revert path intact.
