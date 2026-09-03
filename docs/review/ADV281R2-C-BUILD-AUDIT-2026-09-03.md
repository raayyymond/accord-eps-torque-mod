# ADV281R2-C — Build-script audit of V281 rev 2 (adversary C, 2026-09-03)

**Verdict: PASS — no defect found that would justify "do not flash". Three findings, none image-affecting.**

Target: `analysis-2020accord/builds/v108_plus/build_v281_tva.py` and its outputs
- image `_v281r2_V281R2-V280R2BASE-KP.FLAT341.FROM24.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin` sha256 `4c437e3b…250a37`
- rwd `39990-TVA,A160-V281R2-…-0x13000-0x100000.rwd` sha256 `e74a56cb…5002b`
- base V280 rev 2 `b1f19d3e…c90fa`

Audit scripts (scratch, not in the repo): `…/scratchpad/adv281c/{rebuild.py, mutate.py, census.py}`. No kit file, image or rwd was modified.

## What a FAIL would have looked like (written before running)
1. My independent rebuild from V280r2 differs from the shipped image by any byte, or the shipped image fails my own CRC walk (walker validated on STOCK and V280r2 first, with a positive control).
2. The shipped rwd decodes — via a byte map learned purely from the V280r2 rwd/image pair, not the kit's cipher constants — to anything but the shipped image; or its headers/chunking differ from V280r2's rwd; or its file checksum is wrong.
3. The assertion census diverges materially from the builder's 646/165/29, or any single-point mutation of the script passes its own assertions.
4. A docstring number is a restated constant rather than something the image supports.

## 1. Independent rebuild — PASS (EVIDENCE)
Own implementation, zero imports from the kit: walk the 28 u32 pointers at 0xCB994; per record X[1] = min idx where the record's base floor-LERP ≥ 341, X[2..4] = 68/136/208, Y[1..4] = 341, Y[0] and n untouched; re-CRC every 4 KB block touched.
- Rebuild sha256 = `4c437e3be49ccdd416f8d32c6621c640d8386c7200c6ab7c642a0136cb250a37` — **0 bytes differ from the shipped image**.
- Diff vs base: 316 bytes = 296 payload (188 u16 cells, all in 0xE4360–0xE829D, all ≥ 0xC0000) + 20 trailer bytes in exactly 5 blocks (0xE4FFC, 0xE5FFC, 0xE6FFC, 0xE7FFC, 0xE8FFC). Code region 0x13000–0xC0000 identical.
- Knees per slot: 0/4 → 37, 1/6 → 20, 2/5 → 32, 3/7 → 24, 8/9 → 23, 10–27 → 7. Matches the docstring.
- CRC scheme independently re-implemented from the walker's documented spec (linked list from the 0xFFFF8 trailer, `zlib.crc32`, bootloader bridge 0xC6000→[0x13000,0xC4FFC)): STOCK `code.bin` 50/50 and 49/49; V280r2 50/50 and 49/49; a one-bit corruption of V280r2 at 0xE5378 FAILS (positive control); shipped V281r2 50/50 and 49/49.

## 2. RWD — PASS (EVIDENCE)
- Own x31 parser. File checksum (u32 LE sum) correct. Headers byte-identical to V280r2's rwd: `#`=00, `?`=A1, `/`=39990-TVA-A110 + 39990-TVA,A160, `!`=001100121020 ×2, `&`=BF109E, `%`=30. 7584 chunks, contiguous 0x13000→0x100000, identical addresses to V280r2's.
- Byte map enc→plain learned from (V280r2 rwd, V280r2 image): bijective over all 256 values. Applying it to the V281r2 rwd yields the shipped image exactly (and my rebuild).
- V281r2 rwd vs V280r2 rwd: 318 bytes differ (316 payload-carrying + checksum), all inside the chunks carrying the Kp records.

## 3. Assertion census — re-classified (EVIDENCE) and mutation test — 36/36 caught
Non-write-mode run: 838/838 (the claimed 840 adds the two write-mode on-disk re-hash checks; consistent). Builder's own tally 644/165/29.

My re-classification of the 838 (message-level, `census.py`):

| class | count |
|---|---|
| Substantive (could fail on a wrong edit, not entailed by another assertion) | ~358 |
| Vacuous, builder-labelled V (base image only) | 165 |
| **Vacuous but labelled S** (reads base or rev-1 only: the 28 "knee N verified on the base LERP", "all 28 carried a knot above the cap", "LIVE knee is 24", the uniform-24 positive control, "rev 1 carried the BASE X axis") | 32 |
| Tautological, builder-labelled T | 29 |
| Redundant per record (X strictly increasing, Y[0] untouched, 0<Y≤341, monotone, LERP==341 from knee, LERP idx 0 — all entailed by that record's X==/Y== checks) | 168 |
| Redundant via `dec == code` (the 51 "dec:" and readback-CRC lines) and the 21 "code:" re-reads in [8] that repeat section [4] | 72 |
| Redundant other (tap window / PID inside the already-identical code region, live-map after map byte-identical, 4 live-LERP restatements, n/X[0] restated) | 9 |
| Input-integrity (sha of base / V38 rwd / rev-1, `hasattr(FF, "V38_PLAIN")`, non-circular cipher check) | 5 |

So the honest substantive count is roughly **358, not 646**: 32 of the "S" lines are entailed by the base hash, and ~250 are entailed by other assertions in the same script. This is a labelling finding, not a build defect — the substantive core (28× X==, 28× Y==, 28× LERP ≤ base, 28× shortfall ≤ 4, n untouched, cell/byte counts computed from the base, 5 CRC-moved checks, both CRC walks, full-diff attribution, payload-allowlist, `dec == code`, the rev-1 cross-image checks, and the independent rebuild) is what actually catches mutations.

Mutation test — 36 single/two-point mutations of a COPY of the script (bootstrap redirected; nothing in the kit touched). **All 36 caught, each by a substantive assertion**:

| # | mutation | caught by |
|---|---|---|
| M01 | KP_CAP 342 | LIVE knee is 24 (derived) |
| M02 | Y[0] written −1 | Kp Y == Y0, 341×4 |
| M03 | one record skipped | changed u16 cells 182 == 188 |
| M04 | X non-monotonic (136,68) | Kp X == (0,knee,68,136,208) |
| M05 | one knot 342 on a dead slot | Kp Y == |
| M06 | CRC ^1 | built image CRC chain 50/50 |
| M07 | 0xC63E6 flipped (outside family) | 0xC63E6 == base == 0 |
| M08 | rev-1 cap rule (X untouched) | Kp X == |
| M09 | writer knee +1 | Kp X == |
| M10 | knee rule `>` not `>=` | knee verified on base LERP (lerp(x1−1) < 341 fails) |
| M11 | ceil LERP instead of floor | LERP ≤ V280r2 at every idx |
| M12 | KNEE_X constant 25 | LIVE knee is 25 vs derived 24 |
| M13 | base swapped to V280 rev 1 with sha updated | live map == straight line |
| M14 | last block's CRC not rewritten | CRC chain 50/50 |
| M15 | CRC computed from base bytes (stale) | CRC actually moved |
| M16 | X[4]=209 on one record | Kp X == |
| M17 | n=4 on one record | n untouched |
| M18 | pointer-bank entry moved | pointer bank untouched |
| M19 | tap-window byte | code region byte-identical |
| M20 | hook byte | code region byte-identical |
| M21 | Kd record byte | Kd slot 7 byte-identical |
| M22 | dead slots 10–27 skipped | changed u16 cells 62 == 188 |
| M23 | rwd encoded from base | decoded .rwd == built image |
| M24 | Y[1]=340 everywhere | Kp Y == |
| M25 | X[2]=69 everywhere | Kp X == |
| M26 | independent_rebuild broken (`>`) | independent rebuild == sha |
| M27 | uniform knee 24 on all records | Kp X == (slot 0 wants 37) |
| M28 | big-endian Y write | Kp Y == |
| M29 | Y[0]=300 on dead slot 15 | Kp Y == |
| M30 | 0xC5FFC (skipped-by-BL block) flipped | CRC chain 50/50 |
| M31 | last record's Y[4] left at base | Kp Y == |
| M32 | 0xC6100 flipped and attributed | every payload byte is a Kp X/Y cell |
| M33 | two-point: cap 342 + KNEE_X 25 | LIVE X/Y == (0,24,…),(248,341,…) hard-coded |
| M35 | trailer written 4 bytes late | CRC chain 50/50 |
| M36 | Y[0] raised to 341 on slot 7 | Kp Y == |
| M37 | X[1] = knee−1 (inside the 4-count tolerance?) | Kp X == |

No uncaught mutation. Note M33: a consistent two-point change of cap and knee is caught only by the hard-coded live expectations `(0, 24, 68, 136, 208)` / `(248, 341, 341, 341, 341)` and `255 @2, 294 @12, 341 @24` — those hard-coded numbers are doing real work and should stay.

## 4. Docstring numeric claims vs the image — all read-verifiable; one omission
Verified from the shipped image (not the script): live slot 7 record @0xE5378, X 0/68/112/136/208 → 0/24/68/136/208, Y 248/512/645/696/696 → 248/341/341/341/341; LERP idx 2/12/24 = 255/294/341 on both; idx 17 = 314 vs 313 (the one off-by-one); idx 58 473→341 (ratio 0.721, "−28 %"); idx 68 512→341; idx ≥136 696→341 (0.490, "−51 %"); 112 knots at 341; Y[0] range 205–307; per-record knees as stated; worst below-knee shortfall 4 counts (slot 0); uniform-24 would exceed the base by 46 (slots 0/4) and 34 (slots 2/5); rev-1 image sha `e27f12de…` and its live idx 12 = 264; Kd slot 7 @0xE511C = 4 knots ×128; 0xC62E6 = 46080; map slot 7 = the straight line; 296 payload / 188 cells / 5 trailers / 316 total.

**Finding (cosmetic):** docstring line "X[3..4] already 136/208 on slots 0/1/3/4/6/7, differ elsewhere" omits slots 8/9, whose base X[3..4] is also 136/208 (their record changes 10 bytes, same as slots 1/3/6/7). Only slots 2/5 (160/208) and 10–27 (160/208) move X[3]. No effect on the image.

## Findings summary
1. **Census labelling** — 32 assertions marked S are entailed by the base/rev-1 hashes; ~250 more are entailed by other assertions. Honest substantive count ≈ 358, not 646. Recommend the script's `check(..., kind)` tags be corrected so the printed census is not overstated. Not a build defect.
2. **Docstring omission** — slots 8/9 also already carry X[3..4] = 136/208. Cosmetic.
3. **Housekeeping (observed, outside my brief)** — in `accord-firmwares`, the V281r2 image and rwd, the rev-1 SUPERSEDED image and the rev-1 SUPERSEDED rwd are all untracked (`git status`). Close-out must commit them.

Nothing here changes the verdict: the shipped image is exactly what the stated rule produces, its CRCs are correct under a walker proven on stock, and the rwd carries it faithfully under the same cipher and headers as the flown V280r2.
