# ADV281R3-C — Build-script audit of V281 rev 3 (adversary C, 2026-09-03)

**Verdict: PASS — no defect found that would justify "do not flash". Image, rwd and CRCs reproduce independently; 36/36 mutations caught. Three findings, none image-affecting (one labelling, two docstring nuances).**

Target: `analysis-2020accord/builds/v108_plus/build_v281r3_tva.py` and its outputs
- image `_v281r3_V281R3-V280R2BASE-KP.FLAT.Y0.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin` sha256 `98a7a5143de8fce00079f8f182bfc38c24bc59b6c4c36874015fd71292e2fc9c`
- rwd `39990-TVA,A160-V281R3-…-0x13000-0x100000.rwd` sha256 `a3e330ff29718cd4660c8ddb257fce185a82961219726ef15b992149d3598901`
- base V280 rev 2 `b1f19d3e330cd8874a857e57700ffa73b837754d6e5085be0caa33ba398c90fa`

Audit scripts (scratch, not in the repo): `…/scratchpad/adv281r3c/{rebuild.py, rwd.py, mutate.py, census.py}`. Nothing under the kit or the firmware root was modified; the build script was run in non-write mode only; mutations ran on copies in scratch with the bootstrap repointed.

## What a FAIL would have looked like (written before running)
1. My own rebuild from V280 rev 2 (walk 0xCB994, Y[1..4] := Y[0], re-CRC from the image's own linked list) differs from the shipped image by any byte; or the shipped image fails my own CRC walk, after that walker passes STOCK `code.bin` and V280 rev 2 and FAILS a one-bit corruption.
2. The shipped rwd, decoded via a byte map learned purely from the (V280 rev 2 rwd, V280 rev 2 image) pair — no kit cipher constants — yields anything but the shipped image; or its headers / chunking / file checksum differ from V280 rev 2's rwd.
3. Any single- or two-point mutation of the script passes its own assertions; or the census diverges materially from the builder's 566/198/29.
4. A docstring number that the image or the sizing doc does not support.
5. More than one non-SUPERSEDED V281 rwd on disk, or a SUPERSEDED rev 1 / rev 2 file whose hash does not match the one on record.

## 1. Independent rebuild — PASS (EVIDENCE)
Zero kit imports. Walk the 28 u32 LE pointers at 0xCB994; per record assert n = 5, write Y[0] into Y[1..4] (offsets p+14..p+20); locate the CRC block owning each touched byte by following the image's own trailer linked list from 0xFFFF8; rewrite `zlib.crc32` into each hit trailer.
- Rebuild sha256 = `98a7a514…2fc9c` — **0 bytes differ from the shipped image**.
- Diff vs base: **218 bytes = 198 payload + 20 trailer**, payload range 0xE436F–0xE829D (all ≥ 0xC0000), trailers in exactly 5 blocks (0xE4FFC, 0xE5FFC, 0xE6FFC, 0xE7FFC, 0xE8FFC). Code region 0x13000–0xC0000 identical. 112 u16 cells touched; **26 of the 224 cell bytes are byte-equal to the base**, all low-byte shares: 461→205 (slots 0/4, 1 cell each), 717→205 (slots 2/5, 3 cells each), 563→307 (dead slots 10–27, 1 cell each) = 2 + 6 + 18 = 26.
- Per-slot Y[0] read from the image: 205 on slots 0/2/4/5, 266 on 1/6, 248 on 3/7/8/9, 307 on all of 10–27. X, n and pad untouched on every record (asserted in my walker).
- CRC walker (own re-implementation of the documented BL spec, bridge at 0xC6000 for the 49-block replay, no bridge for the 50-block hygiene walk): STOCK 49/49 + 50/50; V280 rev 2 49/49 + 50/50; **positive controls: one bit flipped at 0xE5378 → 1 fail in both walks; one bit at 0x50000 → 1 fail in both**; shipped V281 rev 3 49/49 + 50/50.

## 2. RWD — PASS (EVIDENCE)
- Own x31 parser. Header block 118 bytes, byte-identical across the V280 rev 2, V281 rev 3, and both SUPERSEDED V281 rwds: `#`=00, `?`=A1, `/`=39990-TVA-A110 + 39990-TVA,A160, `!`=001100121020 ×2, `&`=BF109E, `%`=30. 7584 chunks of 130 B, contiguous 0x13000→0x100000, identical chunk addresses to V280 rev 2. File checksum (u32 LE byte sum) correct on all four files.
- Byte map enc→plain learned from (V280 rev 2 rwd, V280 rev 2 image): bijective over all 256 values. Applied to the V281 rev 3 rwd it yields the shipped image exactly; applied to the SUPERSEDED rev 1 / rev 2 rwds it yields the SUPERSEDED rev 1 / rev 2 images exactly.
- V281 rev 3 rwd vs V280 rev 2 rwd: 220 bytes differ = 218 in chunk data (mapping back to exactly the 198 payload + 20 trailer image addresses) + 2 in the file checksum.

## 3. Mutation test — 36/36 caught (EVIDENCE) and census re-classified
Non-write run: **790/790**, builder census 563 S / 198 V / 29 T (the claimed 793 / 566 adds the three write-mode on-disk checks — consistent).

Mutations of a scratch COPY (control M00 unmodified passes 790/790):

| # | mutation | caught by |
|---|---|---|
| M01 | Y[0] written −1 | Kp Y == Y0 ×5 |
| M02 | live record skipped | changed u16 cells 108 == 112 |
| M03 | dead slots 10–27 skipped | changed u16 cells 40 == 112 |
| M04 | Y := 247 (Y0−1) | Kp Y == |
| M05 | Y := 249 (Y0+1) | Kp Y == |
| M06 | X[1] +1 | Kp X == UNTOUCHED |
| M07 | n := 4 | n untouched |
| M08 | pad := 1 | pad word untouched |
| M09 | CRC ^1 | CRC chain 50/50 |
| M10 | last block's CRC stale | CRC chain 50/50 |
| M11 | 0xC63E6 := 1 (outside family) | 0xC63E6 == base == 0 |
| M12 | rev 2's rule (cap at 341, X kept) | Kp Y == |
| M13 | big-endian Y write | Kp Y == |
| M14 | rwd encoded from the base | decoded .rwd == built image |
| M15 | independent_rebuild broken (k from 2) | independent rebuild == sha |
| M16 | pointer-bank slot 7 moved +24 | pointer bank untouched |
| M17 | trailer written 4 bytes late | CRC chain 50/50 |
| M18 | Y[4] left at base | Kp Y == |
| M19 | base := V280 rev 1 (sha updated) | live map == straight line |
| M20 | flatten to Y[1] | Kp Y == |
| M21 | Kd slot 7 byte | Kd slot 7 byte-identical |
| M22 | tap-window byte | code region byte-identical |
| M23 | PID byte 0x28EA6 | code region byte-identical |
| M24 | 0xC5FFC (BL-skipped block) | CRC chain 50/50 |
| M25 | rev 2 cross-image := rev 1 (sha updated) | rev 2 live record read from its image |
| M26 | live Y[0] := 249 | Kp Y == 248 ×5 |
| M27 | cipher table entries 0/1 swapped | non-circular cipher check vs V38 plain |
| M28 | ceil LERP | [V] V280 rev 2 live LERP 255 @2 … |
| M29 | base := the rev 3 image itself (sha updated) | [V] base live Kp slot 7 Y (248, 512, …) |
| M30 | two-point: live skipped + count expectation 4×27 | changed Kp-record bytes 190 == 198 |
| M31 | write lands in X (offset −10) | Kp X == UNTOUCHED |
| M32 | N_SLOTS 27 | == 4 × 28 hard-coded |
| M33 | KP_PTR := the Kd bank | [V] base live Kp slot 7 |
| M34 | CRC computed from base bytes | CRC actually moved |
| M35 | trailer bytes not attributed | all 218 differing bytes attributed |
| M36 | two-point: Y := 247 in both writer and independent rebuild | Kp Y == (compared to the BASE's Y[0], not to the rebuild) |

No uncaught mutation. Note: M28 is not image-affecting (with every Y equal the LERP rounding form is irrelevant) — it is listed to show the [V]-labelled LERP expectations still do work against script-logic drift. M36 shows the substantive core does not rely on the two implementations agreeing with each other: every Y is checked against Y[0] read from the base.

Census re-classification of the 790 (message-level, `census.py`):

| class | count |
|---|---|
| Builder V (base-image only) | 198 |
| Builder T (`code:` Kp-slot / live-record readbacks in [8]) | 29 |
| Input integrity (base / V38 rwd / rev 1 / rev 2 sha, `hasattr`, non-circular cipher) | 6 |
| **CORE per record**: n, X, pad, Y written (4 × 28) | 112 |
| **CORE aggregate**: cell/byte counts from the base, all-28-carried, pointer bank, live X/Y, live LERP 248, rail-error arithmetic | 7 |
| **CORE CRC**: no edit on trailer, CRC moved (5 + 5), both walks | 12 |
| **CORE [6] full diff**: attributed, payload allowlist, n/X untouched, counts, span, no code, trailer count | 7 |
| **CORE [7] rwd**: decoded == built, readback walks | 2 |
| **CORE [8b] cross-image** (rev 1 / rev 2 diffs restricted to Kp cells, no code diff, Y[0] identical, LERP ≤ all three) | 8 |
| **CORE [9]** independent rebuild | 1 |
| [4] frozen-everything-else vs base — an independent implementation, but entailed by [6]'s full-diff + payload allowlist | 194 |
| Redundant per record (Y[0] untouched, LERP == Y0, LERP ≤, LERP idx 0, LERP strictly below — all entailed by that record's Y== / X==) | 140 |
| Redundant `dec:` re-reads in [8] (entailed by `decoded == built image`) | 50 |
| **Redundant `code:` re-reads in [8] labelled S** (Kd, 0xC62E6, live map, tap window, 17 FROZEN cells — verbatim repeats of section [4]) | 21 |
| **Vacuous but labelled S** ("rev 1 / rev 2 carried the 341 cap", "rev 2 live record read from its image" — read only the rev images, entailed by their sha checks) | 3 |

Honest substantive count: **149 core + 6 input-integrity = 155**, or **349** if section [4]'s 194 independent-implementation checks are counted (they are entailed by [6] but were the checks that caught M19/M21). Not 563. Labelling finding, not a build defect; the census is better than rev 2's (32 vacuous-S there, 3 here).

## 4. Docstring numeric claims vs the image and the sizing doc — all verified; two nuances
Read from the shipped image: live slot 7 @0xE5378 words `5 | 0 68 112 136 208 | 248 248 248 248 248 | 0`; base words `… | 248 512 645 696 696 | 0`; V280 rev 2 live floor-LERP 255 @2, 294 @12, 341 @24, 473 @58, 512 @68, 608 @100, 696 @136; rev 3 = 248 everywhere; ratios 0.973 / 0.844 / 0.727 / 0.524 / 0.484 / 0.408 / 0.356 (docstring's −3 % / −16 % / −64 % ✓). 112 cells / 224 bytes / 198 differ / 26 byte-equal / 5 trailers / 218 total ✓. Per-slot Y[0] table ✓. Dead slots 10–27 Y[0] = 307 ✓.
Against `studies/v280/KPFLAT-SIZING-2026-09-03.md`: flat-248 row `2.38 1.39 1.12 0.92 0.66 | −149° | PM 27° @ 7.6 | GM 2.00× @ 12.0 | Ms 2.9` ✓; K_crit 425/443/426 ✓, 248/425 = 0.58 ✓; P-rail 22.9 → 64.2 deg/s (15360·256/Kp/247 recomputed: 22.87 / 64.19) ✓; full-push 110.8 → 69.5 ✓; loaded rows 128.1/124.3/119.7/110.8 → 118.0/107.6/94.5/69.5 (−7.9/−13.4/−21.1/−37.3 %) ✓; stalled T rows 781→555, 1392→856, 2364→1239, 2462→1452/1709/2137, ≥120 rail (−28.9/−38.5/−47.6/−41.0/−30.6/−13.2 %) ✓; K_eff 225 idx-26 episode ✓; "PM 27–30, GM 2.0–2.2×" ✓; "−25…−48 % stall authority" ✓; measured 125 p50 at ~690-count load ✓.

**Nuance 1 (BELIEF correctly labelled):** the "hands-light full-demand rate … predicted ~ −8 %" is the doc's 600-count-load row (−7.9 %); the sizing doc gives no flat-248 number for that regime (it quotes ~4–6 % for 341/295). The docstring marks it BELIEF. Fine as written.

**Nuance 2 (cosmetic):** the docstring's "THE HIGHWAY BAND IS NO LONGER INERT" is true of the Kp value (255..294 → 248 at idx 2–12) but sits beside the sizing doc's own line "Highway … PM 52–59° at 13 Hz for every Kp in 248–349 — nothing to fix and nothing at risk there." Both are correct; the docstring should say the change there is a −3…−16 % inner-loop gain with no margin consequence per the sizing doc, so a reader does not take "no longer inert" as a risk flag.

## 5. On-disk state — PASS
- Exactly **one** non-SUPERSEDED V281 rwd in `flashing-2020accord/rwd/`: the V281R3 file above.
- SUPERSEDED rev 2 rwd `e74a56cbfdfea476000cb7cb8b679dfbe1609906cc0e9d4a78360fa98685002b` — matches the hash on record in the rev 2 audit. SUPERSEDED rev 1 rwd `9123b1fcece0da790fe08f6c0c5789a4592faed7df758ab33cd9dcbb455e649a` — **no prior statement of this hash exists in docs/ or memory/**; recorded here for the first time. Both decode (own cipher map) to the SUPERSEDED rev 1 / rev 2 images, whose sha256 `e27f12de…306fb` / `4c437e3b…250a37` match the build script's constants.
- `accord-firmwares` git status: the V281r2 image and rwd show as deleted (renamed to SUPERSEDED), and the rev 3 image, rev 3 rwd, SUPERSEDED rev 2 image and SUPERSEDED rev 2 rwd are all **untracked**. Close-out must commit the rename and the four new files.

## Findings summary
1. **Census labelling** — 21 `code:` re-reads in [8] and 3 rev-image-only checks in [8b] are labelled S but are entailed by other assertions; ~384 more S lines are redundant with the core. Honest substantive ≈ 155 (349 counting [4]), not 563. Not a build defect.
2. **Docstring nuance** — "highway band no longer inert" should carry the sizing doc's "no margin consequence there" beside it. Cosmetic.
3. **Housekeeping** — four untracked firmware files plus one rename pending in `accord-firmwares`.

Nothing here changes the verdict: the shipped image is exactly what the stated rule produces, its CRCs are correct under a walker proven on stock with positive controls, and the rwd carries it faithfully under the same cipher, headers and chunking as the flown V280 rev 2.
