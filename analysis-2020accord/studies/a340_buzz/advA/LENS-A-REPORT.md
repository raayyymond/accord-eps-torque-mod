# Lens A report - V300-A340 REV 4 - verdict PASS_WITH_DEFECTS (no DO_NOT_FLASH trigger hit)

Scripts in this dir: audit.py (CRC/diff/rwd), gate.py (flasher gate matrix), mut.py (11 mutations), dry.txt (build dry run).

## 1 Rebuild (EVIDENCE)
Dry run 13 s, 164/164, image e73278a1..., rwd 4bc63270... Disk hashes match. Independent reconstruction (REV 3 with the 13 bytes reverted to stock, letter D, own chain walk and zlib.crc32 trailers) is byte-identical to the REV 4 image.

## 2 Diffs (EVIDENCE)
[0,0x13000) identical to stock (REV 3 and REV 4). REV 4 vs REV 3 = 0x1310D, 0xC40D4, 0xD7A5C(6), 0xD7A6C(6), trailers 0xC4FFC and 0xD7FFC; nothing else. REV 4 vs stock = 825 B, 27 clusters (513 raw runs), all attributed to docstring rows (per script output; per-run attribution not independently recomputed).

## 3 CRC (EVIDENCE)
50/50 blocks pass by own zlib.crc32; kit walkers 0 fails; stock positive control 50/50; corrupted copy fails at block 0x13000.

## 4 rwd and gate (EVIDENCE)
Cipher validated non-circularly (V38 rwd -> V38 plain). REV 4 rwd payload == image; revert rwd payload == stock dump; V37A rwd == V37A image. Gate rule identical in 3 flasher copies on disk (run for real). Acceptance: REV 4 and STOCK revert accept -A340, ,A340, ,A34C, ,A34D; V37A accepts only -A340, ,A340. No stranding.

## 5 Fork (EVIDENCE)
is_accord_eps_angle_loop_fw(b"39990-TVA,A34D\0\0") True (extracted function run). Other literals: fingerprints.py:91 (stock -A340 only; no angle strings for A16C/A34C either) and tests (A34C only).

## 6 Assertion census and mutations (EVIDENCE)
Script census: 96 substantive, 9 constant-checks, 53 vacuous, 6 tautological (not independently recounted). New REV 4 assertions read `code`. 11 mutations injected before the CRC step, all caught by substantive assertions (not only the frozen sha): row0->REV3 values, alpha2=14, base-assist 0xCE100, key table 0xCD010, bootloader 0x100, row1 0xD7A6E, cave 0xC4C10, untouched 0xE0000, mask byte 0xC6D28->0, gain cell 0xC648A, DampAxis X knot 0xD7A56. Weakest: cave byte caught only by the REV3-diff assertion + sha.

## 7 Disk state (EVIDENCE)
Exactly one V300-A340 rwd (REV 4) across accord-firmwares and Downloads; REV 3 rwd gone, image kept. Output paths 100/222 chars (< 259).

## DEFECTS (none blocks flashing)
1. LOW: '/' list includes 39990-TVA-A310, so all three A340 rwds pass the gate for an A310 ECU (inherited).
2. LOW: cave-byte mutation caught only by the REV3-diff assertion, which is conditional on the REV 3 image existing (rev3 is not None), plus the sha.
3. LOW: fork tests cover A34C only; no A34D case (code is correct).
4. COSMETIC: docstring REV 2 paragraph says "13 DampAxis bytes ARE carried" (history, labelled REV 2).
5. BELIEF: ECU reads F181 from 0x13109..0x1310D rather than the dead copy at 0x14117; supported for A34C by memory, no direct evidence for A34D.
6. INFO: V37A rwd rejects A34C/A34D ECUs; going to V37A from V300 needs the stock revert first (not a strand).
