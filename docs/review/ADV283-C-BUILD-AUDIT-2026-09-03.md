# ADV283-C — Build-script audit of V283 (adversary C, 2026-09-03)

**Verdict: PASS on the image — no defect that would justify "do not flash". The shipped image is exactly u16 LE 50 at `0xC63E6` on V282 with a correct CRC; my own rebuild, CRC walker and rwd decode all reproduce it. 32/38 valid mutations caught. ONE substantive script finding: the Ki VALUE is pinned to nothing outside the script's own constant — Ki 49, 51, 5, 100 and 255 each pass 325/325 with a different hash. ONE substantive docstring finding: the build's own FAIL sentence quotes a V281 rev 3 stalled-|T| baseline of "~1240–1700" that is the sizing MODEL's number, not the wire read (778–868 in the r35 read and in the prereg).**

Target: `analysis-2020accord/builds/v108_plus/build_v283_tva.py` and its outputs
- image `_v283_V283-V282BASE-KI50.KP.FLAT.Y0-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin` sha256 `fd0c321abbf933c0d846a8eaf48b594f44f5a9bd491e4396b44abc562551ef3d` ✓ (re-hashed on disk)
- rwd `39990-TVA,A160-V283-…-0x13000-0x100000.rwd` sha256 `6bd088f5e7337ae2ac4be3c65d14c58b1feaa64b247f62b6d507297488e7c85d` ✓
- base V282 `0ea98d06…5ed0fe` ✓ untouched on disk; its rwd `61836515…b7e22` ✓; V281 rev 3 `98a7a514…2fc9c` / rwd `a3e330ff…8901` ✓

Audit scripts (scratch, not in the repo): `…/scratchpad/adv283c/{rebuild.py, rwd.py, mutate.py}`. Zero kit imports in `rebuild.py`/`rwd.py`. Nothing under the kit or the firmware root was modified; the build script was run only as mutated COPIES in scratch, non-write mode, `ACCORD_V283_SCRATCH` unset.

## What a FAIL would have looked like (written before running)
1. My patch of `32 00` at 0xC63E6 onto V282, re-CRC'd from the image's own trailer list, differs from the shipped image; or the shipped image fails my walker after it passes STOCK/V280r2/V281r3/V282 and fails one-bit corruptions.
2. The rwd, decoded via a byte map learned purely from the (V282 rwd, V282 image) pair, yields anything but the shipped image; or headers/chunking/checksum differ from V282's.
3. A single-point mutation of the script passes; the Ki value is unconstrained by anything external; census diverges from the builder's 328 (273/29/26).
4. A docstring number the image, `KI-SIZING.txt`, the r35 read or the prereg does not support.
5. V282 or V281 rev 3 changed on disk; more than one non-SUPERSEDED rwd per build number; recorded hashes wrong.

## 1. Independent rebuild — PASS (EVIDENCE)
- Own walker: BL replay (bridge at 0xC6000) 49/49 and no-bridge hygiene walk 50/50 on STOCK, V280 rev 2, V281 rev 3, V282 and shipped V283. **Positive controls on V282: one bit at 0xC63E6 → 1/1 fail; 0xC63E7 → 1/1; 0x50000 → 1/1; 0xE5378 → 1/1; the trailer 0xC6FFC → 1/1; 0xC5010 (BL-skipped block) → BL 0, hygiene 1.**
- Rebuild: `img[0xC63E6]=0x32; img[0xC63E7]=0x00`; owning block from the image's own list = [0xC6000, 0xC6FFC); `zlib.crc32` rewritten. **sha256 = shipped, 0 bytes differ.**
- Diff vs V282: **5 bytes** = 0xC63E6 (`00→32`) + trailer 0xC6FFC–FF (`72dfea75 → 0cd6c440`). Code region 0x13000–0xC0000 identical. Cave sha[:8] `e9596ad9` on both; hook `86ff26ef`; 427 tap window identical.
- Read from the shipped image: Ki 50, clamp 0xC61BA 10240, deadband 0xC62E4 4, sum clamp 0xC61BE 15360. Stock Ki 0.
- V283 vs V280 rev 2: 233 B = V281 rev 3's 218 ∪ V282's 10 ∪ these 5, no overlap.

## 2. RWD — PASS (EVIDENCE)
- Own x31 parser. 118-byte header sha[:8] `4274fe0f` byte-identical across V281 rev 3, V282, V283 (`#`=00, `?`=A1, `/`=39990-TVA-A110 + 39990-TVA,A160, `!`=001100121020 ×2, `&`=BF109E, `%`=30). 7584 chunks of 130 B, contiguous 0x13000→0x100000. File checksum OK on all three.
- Byte map learned from the (V282 rwd, V282 image) pair: bijective over 256. Applied to the V283 rwd → shipped image exactly; applied to V281 rev 3's rwd → its image exactly.
- V283 rwd vs V282 rwd: **6 bytes** = chunk 5735 offset 104 (→0xC63E6) + chunk 5759 offsets 126–129 (→0xC6FFC–FF) + the file checksum byte.

## 3. Mutation test — 32/38 valid mutations caught; 6 uncaught, 5 of them ONE class (EVIDENCE)
Non-write control run: **325/325**, census 270 S / 29 V / 26 T (the claimed 328/273 adds the three write-mode on-disk checks — consistent). Control hash `fd0c321a…`.

| # | mutation | result |
|---|---|---|
| M01 | Ki := 49 | **PASSED 325/325**, hash 2c5ded6c… |
| M02 | Ki := 51 | **PASSED 325/325**, hash ba4af170… |
| M03 | Ki := 5 (V270's dose) | **PASSED 325/325**, hash 540f500b… |
| M04 | Ki := 100 (the doc's dose) | **PASSED 325/325**, hash ba55cff2… |
| M05 | Ki := 255 | **PASSED 325/325**, hash 3b1d4e1e… |
| M06 | Ki := 256 (low byte unchanged) | caught: "low byte actually moved" |
| M07 | Ki := 12800 = 0x3200 (50 in the HIGH byte) | caught: same |
| M08 | writer packs big-endian | caught: [T] readback |
| M09 | two-point: writer AND independent rebuild big-endian | caught: [T] readback (u16 reads 0x3200) |
| M10 | KI_CELL := 0xC63E4 (neighbour, base 634) | caught: base Ki == 0 |
| M11 | writer packs 4 bytes (`<I`) — zeroes 0xC63E8 | caught: no byte outside the cell |
| M12 | write lands at KI_CELL+2 | caught: [T] readback |
| M13 | neighbour 0xC63E4 ^1 | caught: no byte outside |
| M14 | neighbour 0xC63E8 ^1 | caught: no byte outside |
| M15 | anti-windup clamp 0xC61BA := 10241 | caught: clamp/deadband untouched |
| M16 | deadband 0xC62E4 := 16 | caught: same |
| M17 | CRC ^1 | caught: 50/50 walk |
| M18 | stale CRC (never written) | caught: 50/50 walk |
| M19 | CRC over the base bytes | caught: "CRC actually moved" |
| M20 | CRC written to 0xC5FFC | caught: 50/50 walk |
| M21 | stray byte 0x30000 ^1 | caught: no byte outside |
| M22b | base := V281 rev 3 (sha updated) | caught: cave site 0xC4B42 carries the V282 displacement |
| M23 | base := V280 rev 2 (sha updated) | caught: live Kp Y == 248×5 |
| M24 | V282 cave reverted (4 sites to pre-V282 displacements) | caught: no byte outside (6 stray) |
| M25 | Kp reverted (live Y[1] := 512) | caught: no byte outside |
| M26 | rwd encoded from the base | caught: decoded == built |
| M27 | independent rebuild broken (Ki+1) | caught: rebuild sha |
| M28 | rwd checksum corrupted | caught: x31 checksum |
| M29 | cipher table 0/1 swapped | caught: non-circular V38 check |
| M30 | PARENT := SUPERSEDED V281 rev 2 (sha updated) | caught: [6b] union (250 ∪ 316 ≠ 233) |
| M31 | GRANDPARENT := SUPERSEDED V280 rev 1 (sha updated) | **PASSED** (bookkeeping; image identical — same as ADV282-C M31) |
| M32 | FROZEN 0xC62E6 expectation drifted to 30720 | caught: base [V] check |
| M33 | KI_OLD := 50 | caught: base Ki == 0 |
| M34 | Ki := 306 (both bytes change) | caught: "only the LOW byte differs" |
| M35 | END := 0xC7000 (rwd truncated) | caught: encode block-length assert |
| M37 | base mutated in place AFTER [1]/[2] at non-FROZEN 0xC6900 (same CRC page) | caught: diff count 4 ≠ 5 |
| M38 | base mutated in place AFTER [1]/[2] at 0x30000 (other page) | caught: 50/50 walk |
| M39 | KI_CELL := 0xC63E2 (base 31) | caught: base Ki == 0 |
| M40 | rwd encoded from an independent rebuild carrying Ki 49 | caught: decoded == built |

(M22 as first written was my own NameError and was re-run as M22b; M36 was an inert no-op of mine and is excluded. 38 valid mutations.)

**Finding 1 (substantive, script-level, NOT image-level).** M01–M05: **the Ki value is constrained by nothing outside `KI_NEW`.** The only value-bearing checks are the [T] readbacks of the constant just written, the product-width bound (passes for any Ki ≤ ~17000), and [6]'s "only the low byte differs / low byte moved" (passes for any Ki in 1..255). The script does not read the prereg's dose, does not compute the PI corner against the live Kp read from the image, and `independent_rebuild` shares `KI_NEW`. A typo'd 5, 55, 100 or 250 ships silently with a different hash. **The brief's explicit question — "is the Ki VALUE pinned to something outside the script's own constant?" — answer: NO.** Recommended (not applied — I do not edit build scripts): (i) assert `u16(code, KI_CELL) == 50` against a literal parsed from `PREREG-V283-READ.md` ("Ki 0 → 50"), and (ii) assert the corner `1.2434 * u16(code, KI_CELL) / Y7[0]` (Y7 = the live Kp record read from the image, 248) lands in [0.24, 0.26] Hz — the docstring's own 0.25 Hz. Either pins the dose to a document outside the script; both together pin it to the physics. The shipped image reads 50 by my own u16 read, so the image is correct.

Census re-classification of the 270 S:

| class | count |
|---|---|
| [4] per-record byte-identical vs base (maps, 28 Kp, 28 Kd, tapers) — entailed by [6] full diff | 196 |
| [4] FROZEN == base == v — entailed by [1] + [6] | 18 |
| [8] `dec:` re-reads — entailed by "decoded == built image" | 25 |
| **core** | **31** |

The 31 core: base sha; clamp+deadband untouched; map ceiling; product width; no byte outside; cave/hook/tap identical; one block, block id, not on trailer, CRC moved, 50/50, 49/49; diff ⊆ attributed, low-byte-only, count 5, low byte moved; parent/grandparent sha, [6b] union, hook/tap back to V280r2, ancestors Ki 0; V38 sha, decoded == built, readback 50/50, 49/49, hasattr, non-circular cipher; independent rebuild. Honest substantive count **31** (245 with [4]); not 270. **None of the 31 constrains the Ki VALUE beyond 1..255** — Finding 1.

## 4. Docstring numbers vs the image, `KI-SIZING.txt`, the r35 read and the prereg
Verified ✓: f_i = 1.2434·50/248 = 0.2507 Hz and 0.5014 at Ki 100; ×0.9841 / −1.38° at 7 Hz (KI-SIZING sec.A, Kp 248 row); deadband 4 = ±0.52 deg/s (sec.E); sp_max 1032 = the map's top Y (read from the image at 0xE4000); |I_term| ≤ 10240 = (clampcal<<10>>3)>>7; sum clamp 15360 = 0xC61BE on the image; "t to rail" 0.99 s (Ki 50) vs 0.47 s (Ki 100); T stall 2240 at idx 58 ≥ 2100; sixteen build scripts list C63E6 (V270→V283) ✓; V270 = Ki 0→5 ✓. Bytes at 0x29D9C `e5 37 e7 73` = `ld.hu 0x73e6[tp], r6` ✓ (my own Format-VII decode). **0x59B90 gate:** bytes at 0x59B88 / 0x59B90 are `84 07 e7 83 62 ff` / `84 07 e7 73 62 ff` = 48-bit Format-XIV `ld.h disp23[gp], r16 / r14`, disp23 = (0xFF62<<7 | 0x3E) sign-extended = −0x4EC2 — my decode agrees with the docstring; the `e7 73` raw hits are exactly three: 0x29D9E (live), 0x2AC90 (dead twin), 0x59B92 (the coincidental hw2). EVIDENCE.

**Finding 2 (substantive docstring error — affects how the drive is scored).** PRE-REGISTRATION paragraph and its FAIL sentence: "tap |T| p50 — V281 rev 3 read ~1240–1700 there … leaves the idx 40-80 stalled-frame |T| p50 unmoved from V281 rev 3's ~1240-1700". The r35 read (`V281R3-READ-r35-2026-09-03.md` stall table) records tap **778 / 868** counts in the stalled runs, and the prereg file says "tap 778–868 counts = 0.62 of V280's". 1238–1281 (Ki 0) and 1568–1621 (Ki 5) are `ki_sizing.py` sec.C's **model** stall T at idx 58/60 — not a wire read. Anyone scoring V283 against the docstring's baseline would call a rise to ~1200 a null when it is a 50 % gain. The prereg file is the authority and is correct; the docstring should quote it.

**Nuance 3 (docstring).** "Ki=100 → … faster stall-release (0.83 s vs 1.77 s) but a larger overshoot on release." In sec.C idx 58 / Kp 248, 0.83 vs 1.77 s is "time above ref after release" — the overshoot DURATION, which is *shorter* at Ki 100; the release itself is t-to-rail 0.47 vs 0.99 s; peak overshoot is 10.4 vs 10.5 deg/s — equal. The cited table does not support "larger overshoot" at Ki 100; the figures are mislabelled. No image consequence; the dose choice (50, the smaller first step) stands on the corner/phase argument.

**Nuance 4 (docstring vs prereg).** The docstring's prereg is a paraphrase with no numeric PASS thresholds (prereg: (a) ≤ 2 runs, none > 1.5 s; (b) ≥ 22 deg/s / ≥ 70 %; (c) ≤ 0.10), says "0.3–1 Hz weave" where the prereg says "0.2–1 Hz hunt", and never names `PREREG-V283-READ.md`. Score the drive from the prereg file, not the docstring.

## 5. On-disk state — PASS
- Exactly one non-SUPERSEDED rwd each for V281R3 (`a3e330ff…8901`), V282 (`61836515…b7e22`), V283 (`6bd088f5…c85d`); one image each; SUPERSEDED V280 rev 1 / V281 rev 1 / V281 rev 2 rwds carry the prefix (`0357a025…`, `9123b1fc…`, `e74a56cb…`).
- `docs/BUILD-LINEAGE.md` V283 entry records `fd0c321a…` / `6bd088f5…` / 328/328 (273 S) — matches disk and my counts.

## Findings summary
1. **Script hole (substantive, does not affect the shipped image):** the Ki dose is unpinned — 49/51/5/100/255 all pass 325/325. Fix by asserting the value against the prereg's dose and the corner frequency computed from the Kp read off the image. The shipped image carries 50 (my own read and rebuild).
2. **Docstring baseline wrong:** "V281 rev 3 read ~1240–1700" is the model's stall T; the wire read is 778–868. Score against the prereg.
3. **Docstring mislabel:** 0.83/1.77 s is overshoot duration (shorter at Ki 100), not release time; "larger overshoot" at Ki 100 is unsupported by the table.
4. **Census labelling:** honest core 31 of the 270 S (245 with [4]'s independent-implementation checks).
5. **M31** (SUPERSEDED grandparent) is a bookkeeping constant with no image consequence — same class as ADV282-C.

Nothing here changes the verdict: the shipped image is u16 LE 50 at 0xC63E6 on V282 with a correct CRC under a walker proven on stock with six positive controls, and the rwd carries it faithfully under the same cipher, headers and chunking as the flown V280 rev 2 / V281 rev 3 / V282.
