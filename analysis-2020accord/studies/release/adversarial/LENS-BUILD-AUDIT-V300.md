# LENS: BUILD-SCRIPT AUDIT — V300 (2026-10-15) — verdict **PASS_WITH_DEFECTS** (no do-not-flash finding)

Study artifact; nothing flashed or sent. E = evidence (method given), B = belief. Scripts (each < 5 s) in this folder:
`audit_v300_indep.py` (diff, layout, CRC chain) · `audit_v300_sets.py` (own address sets) · `audit_v300_rwd.py` (rwd + flasher gate) · `mutate_v300.py` (16 mutations).

## What a FAIL looked like (written before running)
A byte outside the declared runs differs from stock · a kept run differs from V299 · any 4 KB-block CRC wrong · rwd payload != image ·
a page 0xCE–0xD9 byte differs · cave != V299 cave · a Kp/Kd record not 112/48 · flasher refuses an A16B ECU · a mutation passes silently. **None occurred.**

## 1. Hashes and rebuild (E: sha256 from disk; script run with no write flag, so no file touched)
| item | sha256 | claimed |
|---|---|---|
| stock `code.bin` | 3f1d55a98aac6e73… | match |
| V299 image | 30ff05fa464e87ab… | match |
| V300 image | a6a24117ba7757fde0e453215dab5264a0193633921e3fee0cd0597a730cd8a6 | match |
| V300 rwd | ed891cf36845dd47b3cf73401ff9fb26451c54f6272d55cf1eefc036122e3a8a | match |
Script rebuild in memory (2.3 s) prints the same image and rwd sha as the files on disk: **bit-identical reproduction**. 46/46 assertions pass.
V300 outside [0x13000,0x100000) == stock (the V299 image is not; irrelevant, the rwd carries only the window).

## 2. Independent full-file diff (my Python, not the script's helpers)
- V300 vs stock: **749 B**, 203 raw runs, touched pages 0x13,28,29,2A,C4,C6,E4–E8. V300 vs V299: **2123 B**.
- Own address sets typed from the census prose: **0 orphans** in both diffs; every non-keep, non-Kp/Kd, non-trailer byte == stock (0 differ).
- Kept A/B1/B2 bytes differ from V299 in exactly one place: 0x1310D (`B`→`C`). Everything else kept is byte-identical to V299.
- V300 vs V299 removals: 0x14120, 0x35A08/12/18, 0x3AA96, 0x454FE, 0x55C0E, 0x55DF2..11, 0xC40BC, 0xC40D2.., cave 0xC4B34..D7 (164 B → 0xFF), 0xC6447, 0xC649B, 0xC64DE, pages 0xCE–0xD9, E4–E8 assist-map and LIM bytes (464 B, all now == stock). All in the census removal set.
- Pages 0xCE000–0xD9FFF **identical to stock** including trailers (E). Cave 0xC4C00..0xC4D03 **identical to V299** (sha e22193b9dd2999c6…) (E).
- **Kp/Kd layout derived by hand from the image**: Kp rec0 @0xE4360 N=5, X=[0,68,112,136,208] at +2, Y at +2+2N=0xE436C; Kp rec7 @0xE5378, Y at 0xE5384. Kd rec0 @0xE4108 N=4, X=[0,11,22,32], Y at 0xE4112; Kd rec7 @0xE511C, Y at 0xE5126. These match the diff-run starts. 28 distinct pointers each table. V300: **28/28 records flat 112 (Kp) and 28/28 flat 48 (Kd)**, N and X knots == stock. V299 had 27 at 960 and 27 at 0 (the 27 non-selector records), 1 each at 112/48 — confirmed.

## 3. CRC (E: own zlib walk of the 50-block chain from the footer links at 0x100000-8; not the script's helper)
- 50 blocks, contiguous 0x13000–0x100000, sizes {4 KB, 12 KB, 16 KB, 24 KB, one 729,088 B main block 0x13000–0xC4FFC}. **0 bad CRCs on V300** (also 0 on stock and V299).
- Seven trailers differ from stock: main (0xC4FFC), 0xC6FFC, 0xE4FFC–0xE8FFC. Each recomputed by me, equals stored. Main stored 0x9DD6994A.
- `verify_bootloader_crc.walk` 49/49 PASS and `walk_all_blocks` 50/50 PASS on the disk image; negative control (flip 0x20000) returns 1.

## 4. rwd (E)
- Flasher-side parser `encode_eps.parse_x31`: 1 block, start 0x13000, length 0xED000 (970,752), x31 checksum valid. Cipher map re-derived by me from the V38 template rwd + V38 plain image (consistent 256-entry byte map, injective, 0 unseen bytes): **decoded payload == V300 image[0x13000:0x100000]**. Same method on the V299 rwd == V299 image.
- `/` header: A110, ,A160, ,A16A, ,A16B, ,A16C. Parallel `!` list has 5 identical entries; other headers identical to V299.
- Flasher gate `app_id_matches_part` (eps-update-tva.py, imported and run): ECU reporting `39990-TVA,A16B` **accepted** (also A16A, A16C, A110); `,A16D` and `TVB` refused. CAN address 0x18DA30F1.

## 5. Assertion census and mutation test
Script self-census 37 S / 3 C / 1 V / 5 T. My reclassification of the same 46:
| class | n | which |
|---|---|---|
| substantive | 15 | census ownership, TUNING==V299, no-block-in-CE–D9, block list, chain 50/50, bootloader 49/49, (1), (2), cave sha, Kp X knots, G pointer, hook, rwd readback, cipher non-circular, header list |
| constant / input hash | 8 | stock sha, V299 sha, V299 cave sha, G-table shape, u16 fit, V38 sha, source header lists, path length |
| vacuous / entailed | 16 | stock chain, assertion (4) (identical to "no stray" in (1)), the 12 "removed row back to stock" checks (code starts as stock), pages CE–D9 (entailed by construction), telemetry region 0xFF |
| tautological | 7 | F181 readback, Kp and Kd readbacks (written then read via the same table), Ki/ICL, fb-lag, authority chain, D4/D6 |
Self-census **over-counts S by about 22** (reads 37, I count 15). Not a safety defect: the real protection comes from (1), (2), CRC, cave sha and (8).

Mutation harness (build re-run in memory with a byte changed after APPLY, before CRC recompute so CRC cannot help; `collect=True`): **16/16 mutations CAUGHT, 0 silent.**
cave byte · Kp Y+1 · Kd leftover 0 · stray 0x20000 · Kp record padding · EME int · restored telemetry hook · Ki 41 · base-assist page byte · Kp X knot · F181 byte · 960 leftover record · hand-freeze imm · DTC gate · single Kp knot 111 · Kd header N.
Single-point guards: Kp/Kd value mutations (m02, m03, m12, m15) are caught only by assertion (8); kept-run edits like the EME int (m06) only by (2). Both guards are substantive, so no gap, but no redundancy.

## Defects (all low; none blocks flashing)
1. **Self-census mislabels** vacuous checks as substantive (see above). Re-label before it is quoted as "37 substantive".
2. **Hard-coded expectations** in the script: `2471` V299-vs-stock bytes and the exact 7-block start list. Fail loudly if the base changes, so safe, but they are stale-prone.
3. **Flasher gate lists `39990-TVA-A110` (hyphen) and `,A160` (comma) but not hyphen-A160.** An ECU still reporting the hyphen A160 id (B: the flasher's own docstring example of a stock id; not verified on a car) would be refused without `--force-part-mismatch`. Identical to the V299 rwd; irrelevant to the current A16B car; matters only for a rollback or bench path.
4. Gate uses prefix matching in both directions (a truncated id like `39990-TVA,A` passes); unchanged from the flasher, informational.
5. Report numbers are consistent with the image; I found no figure in the build script header contradicting the bytes.

## Verdict
**PASS_WITH_DEFECTS.** Reproduces bit-identically; every changed byte vs stock and vs V299 is accounted for by an independently typed address set; CRC chain, bootloader replay, rwd payload, headers and flasher acceptance for A16B all verified from disk; 16/16 mutations caught. Not evidence about on-car behaviour of the loop (outside this lens).

---
# REV 2 RE-AUDIT (2026-10-15) — verdict **PASS_WITH_DEFECTS** (supersedes the rev-1 verdict above; rev-1 artifacts were deleted)

Change vs rev 1: 13 DampAxis bytes kept at V299 values. Same scripts re-run on the new files (plus 7 new mutations).

| item | sha256 | claimed |
|---|---|---|
| V300 REV2 image | 7d58c823544e9e6ec369e7cc0fc0d7aa42fc8b075ad9b0005f58973d400f384e | match |
| V300 REV2 rwd | 42f562c069d39c877b66067fe56c6437c43b1609c48ffec8a83dc7303b8e7603 | match |
Rebuild (no write flag, 48/48 assertions): in-memory image and rwd sha equal the disk files — **bit-identical**. Image outside the flashed window == stock (E).

**Extents (E, own Python):** vs stock **766 B** in 207 raw runs; vs V299 **2110 B**; 8 owning blocks (main, 0xC6, 0xD7, 0xE4–0xE8); touched pages add 0xD7. Orphans against my own typed address sets: **0 / 0**. Non-keep, non-Kp/Kd, non-trailer bytes != stock: 0.
**The 13 kept bytes (E):** 0xD7A5C..61 = ce8c cebc 80c1, 0xD7A6C..71 = the same six bytes, 0xC40DC = 14. Each equals V299 and differs from stock (stock 9ad9 9ae9 52f8 twice; 22). The two rows are byte-identical to each other.
**Pages 0xCE–0xD9 vs stock:** exactly 16 bytes differ: the 12 above plus the 0xD7FFC trailer (4 B). Nothing else. Cave == V299 (sha e22193b9…). Kp/Kd 28/28 flat 112/48, N and X knots == stock (unchanged from rev 1).
**CRC (E, own zlib chain walk):** 50 blocks, 0 bad. Eight trailers differ from stock (0xC4, 0xC6, 0xD7, 0xE4–0xE8); `walk` 49/49 and `walk_all_blocks` 50/50 PASS.
**rwd (E):** my independently derived cipher map decodes the payload == image[0x13000:0x100000]; checksum valid; `/` list A110, ,A160, ,A16A, ,A16B, ,A16C; flasher gate accepts an ECU reporting `39990-TVA,A16B`; refuses ,A16D and TVB.
**Assertion census (script):** 38 S / 3 C / 1 V / 6 T of 48. My earlier reclassification applies (the 12 removed-row checks and a few others are entailed by construction), so the S count still overstates; unchanged defect.

**Mutations: 23 run; 22 CAUGHT.** All 16 prior mutations still caught. New: flip 0xD7A5C, flip 0xD7A71, flip 0xC40DC, swap words inside a row, revert row 0xD7A6C to stock, flip an unrelated 0xD7 byte — all CAUGHT (by the vs-V299 diff and the new "13 DampAxis bytes == V299" assertion). **m20 "swap the two Y rows" passes silently because it is a no-op: the rows are byte-identical, so the image does not change.** It is not a mutation and not a gap; any swap that changes bytes is caught (m21).

**Defects (low, none blocks flashing):** (1) self-census over-labels S (unchanged); (2) hard-coded count and block-list expectations now updated to 766 / 8 blocks, still stale-prone; (3) the flasher list lacks hyphen-A160 (unchanged, same as V299, irrelevant to the A16B car); (4) the two DampAxis rows are protected by one assertion plus the V299 diff; the "swap" is undetectable only because it is identical.
Whether keeping the DampAxis bytes is the right design is outside this lens (GATE 2 re-score).

**Verdict: PASS_WITH_DEFECTS — nothing in this lens says do not flash REV 2.**
