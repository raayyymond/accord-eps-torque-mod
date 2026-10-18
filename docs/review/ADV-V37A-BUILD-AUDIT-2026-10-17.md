# ADV-V37A build-script audit (lens 3) -- 2026-10-17

VERDICT: PASS_WITH_DEFECTS. None of the pre-written FAIL conditions fired. Defects are in the script's assertions, not in the artifacts.

## Pre-written FAIL conditions (all EVIDENCE, own code `_scratch/v37a/audit/audit.py`, `mut.py`)
| condition | result |
|---|---|
| hash not reproducible | CLEAR. Script rerun with ACCORD_V37A_WRITE=0 gives 69/69. My own ~30-line rebuild from the base (own rounding formula (2*y1*x+6)//12, own CRC) equals the on-disk image byte for byte. sha256 7cb6fd3a... and rwd c9bd3446... match the claims. |
| unexplained byte | CLEAR. Built vs V37: 356 bytes in 216 runs, all inside {4 cells, Y[1..9] of 28 records, 6 CRC trailers}; zero below 0xC0000; Y[0]=0 and X untouched in all 28 records. Built vs stock: 386 bytes, 0 outside (V37A edits UNION V37 edits). Bytes below 0x13000 are all 0xFF. No exact .5 ties exist, so round-half-up vs down is moot. |
| CRC mismatch | CLEAR. All 6 trailers equal zlib.crc32 of [start,end). Kit walk (49) + walk_all_blocks (50) = 0 fails on the image AND on the rwd payload placed in a 0xFF 1 MB image. I did not hand-walk the linked list (format not documented in the lib); I relied on the kit replay plus per-trailer recompute. |
| rwd payload != image | CLEAR. Payload decrypted with keys (BF,10,9E) == image[0x13000:0x100000]. Single block 0x13000, len 970752. |
| header differs from V37 | CLEAR. All six header groups, the cipher key BF109E and every byte up to payload start are identical to V37. File length equals V37 (986042). Trailer is a plain byte-sum of the body and is correct (04d47b88). Re-encoding the V37 base window reproduces the V37 rwd payload exactly. |

## Item 6 / 7
- Exactly one V37A .rwd and one V37A image exist under accord-firmwares (find -iname).
- The base `...V37-V36-DTC0x49-OFF-...rwd` in flashing-2020accord/rwd/ has sha 8a809d1b..., identical to the Downloads file (the "V37-2xTorque" name exists only in Downloads). The base image decrypts from it byte-exactly.
- accord-firmwares git: only the two new V37A files untracked. Expected.
- Kit repo git: untracked build_v37a_tva.py (expected). UNEXPECTED for a cal-only build: modified `model/eps_chain_control.py`, `eps_chain_delivery.py`, `eps_lkas_chain_model.py`. BELIEF: the orchestrator's own golden-model edit (e.g. a `_self_check_v37a`). The facade 94-symbol and stdout-hash contract should be re-run before commit. Ghidra project files also show modified (ignorable).

## Assertion census (69 `check(` calls; 37 grep hits on `check(` text because per-slot checks are in a loop)
- LOAD-BEARING (about 24): d_base allow-set; zero code bytes changed; mid==6 touched blocks; both built-image CRC walks; decoded-rwd CRC walk; carried cells; live Y == LIVE_Y_NEW; golden LERP == 4*idx for 0..240; fb ratio; the three reverts vs stock; per-slot checks for Y1 == 2*Y1 and monotone and max<32767; rail/E-sign model checks.
- VACUOUS, entailed by the base/stock hash (about 15): sizes, base-rec==stock, X==stock, 28 distinct pointers, base live Y stock, base CRC, the three "base == V37 value" reads, base fb==stock, gain-load-site bytes, the three ld.hu reader bytes, stock lerp shape, part-number bytes, "V37 torque ~2x stock".
- TAUTOLOGICAL (about 10): per-slot `gX==X and gY==newY` (reads back what was just written), 0xC62E6==FB_NEW, `u16(code)==stv`, rwd round-trip `back==window`, end-state re-read of the same window.
- STALE/HARD-CODED: LIVE_Y_NEW/LIVE_Y_STOCK; loose bounds 252<=changed<=504, 400<=t_rail<=420, 60<=rail_from<=66; Downloads path is hard-coded and silently skipped if absent (then the base-rwd link rests only on the sha constant).

## Mutation tests (mutated copies of the script, run in-memory, never written; baseline 0 fails)
| mutation | caught |
|---|---|
| live slot Y[3]+1 | YES (3 fails) |
| **non-live record 3, Y[5]+1** | **NO (0 fails)** |
| clamp 42864 | YES, by ratio check only (1 fail) |
| gain 892 | YES (3) |
| stale CRC at 0xE6FFC | YES (2) |
| Y[0]=1 everywhere | YES (32) |
| stray byte at 0x20000 | YES (5) |
| record 5 X[3] changed | YES (2) |
| 0xC61B2 = 513 | YES (3) |
| record 9 Y[1] +2 | YES (1) |
| touch carried cell 0xC64B4 | YES (2) |
| round-down instead of half-up | no, but equivalent (no ties) |

## Defects (all PASS_WITH_DEFECTS grade)
1. Interior knots of the 27 non-live records are only checked by readback plus monotonicity (M1b uncaught). My independent rebuild shows the shipped bytes ARE correct, so this is assertion weakness only.
2. The script never re-reads the files it writes from disk; all checks run on in-memory objects. I did that post-write (hash, decrypt, CRC, diff).
3. fb-clamp 42864 is caught only by the 2e-5 ratio tolerance (1.39531 vs 1.39535), a thin margin.
4. Golden-model files modified in the working tree (see above) need the 94-symbol / stdout-hash contract re-run.
