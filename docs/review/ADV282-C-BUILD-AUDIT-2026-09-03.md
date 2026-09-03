# ADV282-C — Build-script audit of V282 (adversary C, 2026-09-03)

**Verdict: PASS on the image — no defect that would justify "do not flash". Image, rwd and CRCs reproduce independently from the doc's byte table; 30/37 mutations caught. ONE substantive script finding: the four NEW displacements (the entire meaning of the build) are checked against nothing outside the script's own `EDITS` table — a wrong, swapped or duplicated operand passes 354/354. The shipped image is nevertheless correct, because I re-derived it from the research doc's bytes and from the semantic anchors read in Ghidra.**

Target: `analysis-2020accord/builds/v108_plus/build_v282_tva.py` and its outputs
- image `_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin` sha256 `0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe` ✓ (re-hashed on disk)
- rwd `39990-TVA,A160-V282-…-0x13000-0x100000.rwd` sha256 `618365154e3ffdbb073c00a60173508291f0a18340d6a4f7d39cdd4b2a5b7e22` ✓
- base V281 rev 3 `98a7a5143de8fce00079f8f182bfc38c24bc59b6c4c36874015fd71292e2fc9c` ✓ untouched on disk; its rwd `a3e330ff…8901` ✓

Audit scripts (scratch, not in the repo): `…/scratchpad/adv282c/{rebuild.py, rwd.py, mutate.py}`. Zero kit imports in `rebuild.py`/`rwd.py`. Nothing under the kit or the firmware root was modified; the build script was run in non-write mode only (`ACCORD_V282_SCRATCH` was unset, so it wrote nothing); mutations ran on copies in scratch with the bootstrap repointed.

## What a FAIL would have looked like (written before running)
1. My own patch of the doc's four byte pairs (`26 95`, `c8 94`, `26 95`, `6c 94`) onto V281 rev 3, re-CRC'd from the image's own trailer list, differs from the shipped image; or the shipped image fails my CRC walker after that walker passes STOCK and V281 rev 3 and FAILS a one-bit corruption.
2. The rwd, decoded via a byte map learned purely from the (V281 rev 3 rwd, V281 rev 3 image) pair, yields anything but the shipped image; or headers / chunking / file checksum differ from V281 rev 3's rwd.
3. Any single-point mutation of the script passes; or the census diverges from the builder's 282/36/39.
4. A docstring number that the image, the research doc, or the prereg script does not support.
5. V281 rev 3 changed on disk, or more than one non-SUPERSEDED rwd per build number.

## 1. Independent rebuild — PASS (EVIDENCE)
Patch bytes `26 95` @0xC4B36, `c8 94` @0xC4B42, `26 95` @0xC4B64, `6c 94` @0xC4B70 on V281 rev 3; find the owning block from the image's own trailer linked list (one block, [0x13000, 0xC4FFC)); rewrite `zlib.crc32`.
- Rebuild sha256 `0ea98d06…5ed0fe` = shipped, **0 bytes differ**.
- Diff vs base: **10 bytes** = 6 payload (0xC4B36/37/42/43/64/70) + 4 trailer (0xC4FFC–FF). Code region 0x13000–0xC0000 identical. Cave sha256[:8] `d3bb75d8` → `e9596ad9`.
- Displacements read from the image (s16 LE): −0x6b94→−0x6ada, −0x4f64→−0x6b38, −0x6ae2→−0x6ada, −0x6b26→−0x6b94; hw1 `24 37` unchanged at all four sites.
- V282 vs V280 rev 2: 228 bytes = V281 rev 3's 218 ∪ these 10, no overlap.
- CRC walker (own re-implementation, bridge at 0xC6000 for the 49-block replay, no bridge for the 50-block hygiene walk): STOCK 49/49 + 50/50; V280 rev 2 and V281 rev 3 49/49 + 50/50; **positive controls: one bit at 0xC4B36 → 1 fail in both walks; at 0x50000 → 1/1; at 0xE5378 → 1/1; at 0xC5010 (the BL-skipped block) → BL 0, hygiene 1** (the walker distinguishes the two walks correctly); shipped V282 49/49 + 50/50.

## 1b. Semantic anchors, read in Ghidra (dry-run `disassemble_bytes` on the V280 rev 2 program; cave/hook/tap bytes are identical in V281 rev 3 and, outside the 4 sites, in V282) — EVIDENCE
- Cave rung structure confirmed: `ld.h A[gp],r6 ; cmp 0,r6 ; bge ; subr r0,r6 ; mov r6,r7 ; ld.h B[gp],r6 ; cmp 0,r6 ; bge ; subr ; cmp r6,r7 ; mov 4,r7 ; bge ; mov 0,r7 ; shl 4,r7 ; ld.bu -0x1514 ; andi 0xBF ; or ; st.b`. `cmp r6,r7` + `bge` sets the bit when **r7 ≥ r6, i.e. |A| ≥ |B|** with A the first load — so V282's bit 6 = |gp-0x6ada| ≥ |gp-0x6b38| and bit 5 = |gp-0x6ada| ≥ |gp-0x6b94|, as documented. Bit 5's rung uses `mov 2,r7` / `andi 0xDF`; the third rung writes bits 7/4/3 with `andi 0x67` (clears exactly 7,4,3 — bits 6/5 survive it).
- BEFORE operands confirmed: −0x6b94 / −0x4f64 (bit 6), −0x6ae2 / −0x6b26 (bit 5); bit 4's sign load is `ld.h -0x6ada[gp]` (so gp-0x6ada is the same cell the flown sign bit already publishes); bit 7 is `ld.h -0x6b4c`.
- `hw1 = 0x3724` (bytes `24 37`) decodes as `ld.h disp16[gp], r6` — the script's `bytes.fromhex("2437")` is the LE byte pair, correct.
- 427 tap at 0x55DF0 is `ld.h -0x6b38[gp], r6` — so bit 6's B operand IS the tap's source cell, as claimed.
- Hook + send from the V282 image bytes `86ff26ef 083a 20464a01 80ff0c1f` = `jarl 0xc4b34,lp ; mov 8,r7 ; movea 0x14a,r0,r8 ; jarl` — length 8, ID 0x14A ✓.

## 2. RWD — PASS (EVIDENCE)
- Own x31 parser. 118-byte header byte-identical across V280 rev 2, V281 rev 3 and V282 (`#`=00, `?`=A1, `/`=39990-TVA-A110 + 39990-TVA,A160, `!`=001100121020 ×2, `&`=BF109E, `%`=30). 7584 chunks of 130 B, contiguous 0x13000→0x100000. File checksum (u32 LE byte sum) correct on all three.
- Byte map learned from the (V281 rev 3 rwd, image) pair: bijective over 256. Applied to the V282 rwd it yields the shipped image exactly; applied to V280 rev 2's rwd it yields V280 rev 2's image exactly.
- V282 rwd vs V281 rev 3 rwd: **11 bytes** = 10 chunk-data bytes mapping to exactly 0xC4B36/37/42/43/64/70 + 0xC4FFC–FF, plus 1 file-checksum byte.

## 3. Mutation test — 30/37 caught; 7 uncaught, 5 of them ONE class (EVIDENCE)
Non-write run: **354/354**, census 279 S / 36 V / 39 T (the claimed 357 / 282 adds the three write-mode on-disk checks — consistent). Control M00 (unmodified copy) 354/354, same hash.

| # | mutation | result |
|---|---|---|
| M01 | bit 6 A := −0x6ADC (even, plausible, 2 bytes off r24) | **PASSED 354/354**, hash 465dc0d0… |
| M02 | hw2 written big-endian | caught: post-write readback |
| M03 | hw1 byte ^1 | caught: hw1 == 0x2437 |
| M04 | fifth cave site 0xC4B90 ^1 | caught: cave diff ⊆ touched |
| M05 | page CRC ^1 | caught: 50/50 walk |
| M06 | stale CRC (never rewritten) | caught: 50/50 walk |
| M07 | base := V280 rev 2 (sha updated) | caught: base live Kp Y == 248×5 |
| M08 | base := V281 rev 2 SUPERSEDED (sha updated) | caught: same |
| M09 | Kp live Y[1] reverted to 512 | caught: no byte outside the cave |
| M10 | 427 tap window 0x55DF2 ^1 | caught: tap window identical |
| M11 | CAVE_END += 2, no byte change | **PASSED** (bookkeeping only; image identical) |
| M11b | CAVE_END += 2 and 0xC4BD8 ^1 | caught: cave diff ⊆ touched |
| M12 | rwd encoded from the base | caught: decoded == built |
| M13 | independent rebuild skips a site | caught: rebuild sha |
| M14 | EDITS old_disp wrong | caught: base displacement == documented BEFORE |
| M15 | write lands at addr+2 | caught: post-write readback |
| M16 | hook ^1 | caught |
| M17 | 0xC6446 := 1024 | caught: no byte outside the cave |
| M18 | 0xC62E6 := 30720 | caught |
| M19 | CRC computed over base bytes | caught: "CRC actually moved" |
| M20 | CRC written to 0xC5FFC | caught: 50/50 walk |
| M21 | two-point: big-endian in writer AND independent rebuild | caught: readback `<h` == new_disp |
| M22 | **bit 6 operands SWAPPED** (A := T, B := r24) — inverts the bit's meaning | **PASSED 354/354**, hash 080c0d7f… |
| M23 | bit 6 B := gp-0x6b3c (the forward of T) | **PASSED 354/354**, hash b62105ba… |
| M24 | bit 6 mask byte 0xBF → 0xFF | caught: write-rung identical |
| M25 | stray byte at 0x30000 | caught |
| M26 | cipher table 0/1 swapped | caught: non-circular V38 check |
| M27 | new disp ODD (−0x6ADB) | caught: even check |
| M28 | one site's write skipped | caught: post-write readback |
| M29 | hw2 written onto hw1 | caught |
| M30 | CAVE_START := 0xC4B40 | caught: "6 of 8 touched bytes differ" count |
| M31 | grandparent := V280 rev 1 SUPERSEDED (sha updated) | **PASSED** (the [6b] union check is tautological in the grandparent; image identical) |
| M32 | trailer written at b1+4 | caught |
| M33 | bit 5 A edit DROPPED from EDITS (stays gp-0x6ae2) | **PASSED 344/344**, hash c179b5e6… |
| M34 | bit 6 B := gp-0x6b94 (duplicates bit 5) | **PASSED 354/354**, hash 52c55b30… |
| M35 | rwd checksum corrupted | caught: x31 checksum |
| M36 | hw1 expectation flipped to `3724` (LE confusion) | caught |

**Finding 1 (substantive, script-level, NOT image-level).** M01/M22/M23/M33/M34: the script has no external reference for the NEW displacements. `independent_rebuild` shares `EDITS`, [8] reads back `new_disp` from the same table, and nothing compares the built cave against the research doc's byte table, against the 427 tap's own `ld.h` operand (0x55DF2, which is the cell bit 6's B must equal), or against bit 4's sign-load operand (0xC4B9E, which is the cell both A operands must equal). The evenness check is the only constraint on the value. A swapped, off-by-one-cell, or dropped operand ships silently with a different hash. The predecessor's V281 rev 3 script did not have this hole because every Y was compared to Y[0] read from the base; here the intended values are pure constants. **Recommended (not applied — I do not edit build scripts):** assert `s16(code, 0xC4B42) == s16(code, 0x55DF2)` (bit 6 B ≡ the 427 tap's source) and `s16(code, 0xC4B36) == s16(code, 0xC4B64) == s16(code, 0xC4B9E)` (both A operands ≡ the flown bit-4 sign cell), and `s16(code, 0xC4B70) == −0x6B94 == the OLD bit-6 A` (the aggregator moved from bit 6 to bit 5). Those three relations pin every new operand to a byte already on the flown image and would catch all five.

Why the image is nonetheless correct (EVIDENCE): my rebuild used the research doc's byte table, not `EDITS`, and matched; and the Ghidra reads above tie 0xC4B42's new operand to the 427 tap's load (−0x6b38) and both A operands to bit 4's load (−0x6ada). Only the aggregator cell (−0x6b94 for bit 5's B) rests on the BEFORE state of bit 6, which the image confirms.

M11 and M31 are bookkeeping constants with no image consequence.

Census re-classification of the 354 (message-level):

| class | count |
|---|---|
| Builder V | 36 (incl. one literal sanity "spans are non-empty") |
| Builder T | 39 |
| **`check(True, "(b) PASS …")` in [3] — a literal `True`, labelled S** | 1 |
| CORE [1] base sha | 1 |
| CORE [2] hw1-after-write | 4 |
| CORE [3] (a)(c)(d) structure: hw1 all sites, two write-rungs, cave diff ⊆ touched, 6-of-8 count, hook, tap window | 7 |
| CORE [5] CRC: one block, trailer at 0xC4FFC, not on trailer, moved, 50/50, 49/49 | 6 |
| CORE [6] full diff ⊆ attributed, count == 10 | 2 |
| CORE [6b] grandparent sha, union, hook, tap | 4 |
| CORE [7] rwd: V38 sha, decoded == built, 50/50, 49/49, hasattr, non-circular cipher | 6 |
| CORE [9] independent rebuild | 1 |
| [4] frozen-everything-else vs base (FROZEN 18 + 0xC62E6 + maps + 28 Kp + 28 Kd + tapers + outside-cave) — independent implementation, entailed by [6] | 216 |
| [8] `dec:` re-reads labelled S — entailed by `decoded == built image` | 31 |

Honest substantive count: **31 core + 1 vacuous-S**, or **247** counting [4]'s 216 independent-implementation checks (they were the first to catch M09/M17/M18/M25). Not 279. Labelling finding, not a build defect. Note that NONE of the 31 core checks constrains the new operand VALUES — see Finding 1.

## 4. Docstring numeric claims vs the image, the doc, and the prereg script — verified; two nuances
- Cave 0xC4B34–0xC4BD7 = 164 bytes ✓ (0xA4). Cave sha[:8] `d3bb75d8` on V281 rev 3 and V280 rev 2 ✓ (also on the base per my rebuild output). Hook `86ff26ef` ✓; 0x55C12–18 = `mov 8,r7 ; movea 0x14a,r0,r8 ; jarl` ✓ read from the V282 image.
- Bit map BEFORE/AFTER ✓ against the Ghidra reads (§1b). Byte table in `GRINDING-DEEP-ANALYSIS-2026-09-03.md` §4 (`6c 94→26 95`, `9c b0→c8 94`, `1e 95→26 95`, `da 94→6c 94`) ✓ identical to the image. Trailer 0xC4FFC ✓. "6 of 8 touched bytes differ" ✓ (0xC4B65 and 0xC4B71 stay 0x95/0x94). 10 bytes total ✓.
- Predicted duties: re-ran `rlog-tools/studies/grind/v282_prereg_duty.py` (r32/r33/r34 caches): creep v 1–3 bit 6 = **0.300 / 0.188 / 0.132 / 0.065 / 0.029**, high-angle **0.199 / 0.119 / 0.076 / 0.038 / 0.019**, bit 5 creep **0.213 / 0.149 / 0.109 / 0.059 / 0.030** — docstring and doc §5 table ✓ exactly. Thresholds ≥ 0.22 / ≤ 0.10 and the FAIL / Cost-FAIL sentences ✓ match doc §5 verbatim in substance.
- Not re-derived by me (relayed from the doc as wire measurements, BELIEF here): old bit 6 duty 0.0000 on r34; old bit 5 duty 0.337 / 18.9 transitions/s; the −6 ± 25° bit-4 phase; the s16 clamp figures (±8192 / ±3072 / ±0x2800) for the three cells.

**Nuance 1 (docstring reasoning, not the build).** Docstring (a) says the odd-displacement trap "does NOT apply here — it is specific to ld.bu/st.b". That is the wrong reason. In the V850E2 Format-VII encoding used here, **hw2 bit 0 selects `ld.h` (0) vs `ld.w` (1)** — visible in this very cave: 0xC4BA8 `ld.w -0x3680[gp]` has hw2 `81 c9` = 0xC981, odd. An odd new displacement would have silently turned the 16-bit load into a 32-bit load. The script's "new displacement is EVEN" assertion is therefore load-bearing (M27 confirms it fires), but the docstring should say why. No image consequence — all four new displacements are even.

**Nuance 2 (docstring).** "verified byte-identical … cave sha256[:8] = d3bb75d8 … in this build's own [1]/[1b] steps" — [1]/[1b] check the four sites, hw1, FROZEN and the hook; the cave hash is not asserted anywhere in the script. The cave's identity to V280 rev 2 is established only by [6b]'s page-0xC4000 check. True claim, wrong pointer.

## 5. On-disk state — PASS
- V281 rev 3 image and rwd hashes unchanged (above). Exactly **two** non-SUPERSEDED rwds of these numbers in `flashing-2020accord/rwd/`: V281R3 and V282; the V281 rev 1 (`9123b1fc…`) and rev 2 (`e74a56cb…`) rwds carry the SUPERSEDED prefix and match their recorded hashes. Only one V282 image and one V282 rwd exist anywhere under the firmware root.
- SUPERSEDED images re-hashed: V281 rev 1 `e27f12de…306fb`, rev 2 `4c437e3b…250a37`, V280 rev 1 `47bdfb0d…7411`.

## Findings summary
1. **Script hole (substantive, does not affect the shipped image):** the four new displacements are unconstrained by anything outside `EDITS`; swapped/shifted/dropped operands pass 354/354 (M01, M22, M23, M33, M34). Fix by asserting the operand relations to 0x55DF2 and 0xC4B9E on the built image. The shipped bytes were independently confirmed correct from the doc's table and Ghidra.
2. **Docstring reasoning:** the even-displacement rule matters for `ld.h` because hw2 bit 0 is the ld.h/ld.w selector, not because of a ld.bu/st.b trap. Cosmetic; the assertion is present.
3. **Census labelling:** one `check(True, …)` labelled S; 216 + 31 S lines entailed by other checks. Honest core ≈ 31 (247 with [4]).
4. **Docstring pointer:** the `d3bb75d8` cave hash is not asserted by the script.

Nothing here changes the verdict: the shipped image is exactly the doc's four byte pairs on V281 rev 3 with a correct CRC under a walker proven on stock with positive controls, and the rwd carries it faithfully under the same cipher, headers and chunking as the flown V280 rev 2.
