# ADVERSARIAL PASS — V299 build-script audit lens (lens 3)

**Role:** a subagent in the V299 build round, working as the adversary. Its job was to make the built image FAIL.
Nothing was flashed, no CAN was sent and no git was touched. FAIL criteria were written first:
`FAIL-CRITERIA-build-audit-V299.md` (same folder).

**Classifier interruptions: 1.** It came while I was reading the kit's rwd container/cipher code (`lib/encode_eps.py`) to build
an independent rwd encoder/decoder. After it I **did not do any rwd encoding, decoding or header parsing myself.** So FAIL
criterion 5 (the rwd) is **NOT VERIFIED BY THIS LENS** (see D5). Everything else was done.

**Verdict: PASS_WITH_DEFECTS for the IMAGE. Do not offer it for flashing until D1 and D5 are closed.**
The image `30ff05fa…` itself fails none of FAIL criteria 1–4 or 6. The flash package is incomplete: there are no revert rwds
that list A16B, and the V299 rwd has not been written or read back.

## Findings

### F1. Full-file diff = exactly the attributed 67 bytes (EVIDENCE)
**Method:** `_scratch/adv_v299_diff.py`, numpy over the whole 1 MiB file (not just 0x13000..0x100000), wall 0.00 s.
- V298 base sha `177abf04…` ✓.
- Built image sha `30ff05fa464e87ab7eecfcbab9cbf6dfb3afcb57ceb5c89e4a29c1f748c38f08` ✓.
- **67 differing bytes:**
  - 60 inside the span 0xC4C6A..0xC4CAB;
  - 0xC4C64/65 `00 02`→`cd 04` (imm16 1229);
  - 0x1310D `41`→`42`;
  - 0xC4FFC..FF `f3 d8 7c 6b`→`95 3b dd 70`.
- Nothing below 0x13000, nothing above 0xC4FFF.
- The cave 0xC4C00..0xC4D04 sha is `e22193b9…` ✓.
- **The 66-byte span equals, byte for byte, the 24 instruction encodings I transcribed by hand from the spec §1.1 rev-2
  column.** I transcribed them in table order; the build script's `CAVE_HEX` was not used.
- F181 at 0x13100 reads `39990-TVA,A16B` ✓.

### F2. Independent reconstruction (EVIDENCE)
The image equals V298 with exactly these edits, each value checked:
- the spec's span bytes;
- imm16 `cd 04`;
- `0x42`;
- trailer `95 3b dd 70`. I recomputed the trailer myself with `zlib.crc32` over [0x13000,0xC4FFC): it equals the stored word.

So rebuilding from V298 with these edits reproduces the image bit for bit. I did not write a second standalone emitter: the
diff plus the value checks already settle this.

### F3. CRC chain and bootloader replay on the BUILT image (EVIDENCE)
**Method:** the kit's `verify_bootloader_crc.walk` / `walk_all_blocks` (read-only), run on the on-disk image, 0.00 s.
- Bootloader replay: 49 blocks, 0 mismatches.
- Full chain: 50 blocks, 0 mismatches.
- All edits are inside [0x13000, 0xC4FFC), so no edit straddles a block. There is no diff in the cal/record blocks.

**Limitation:** the walk logic is the kit's, not mine. My own crc32 check covered only the one block that changed. The other
49 blocks are byte-identical to V298 (F1), which flew route 79, so they cannot have changed.

### F4. Decode (not re-done here)
I did not re-run Ghidra; the mirror report §3 and the bytes re-refuter did. F1 shows that the built span is byte-identical to the
spec table's encodings, which are the input to their decode.

### F5. Assertion census of `build_v299_tva.py` (EVIDENCE — read the script, reclassified each check)
With `do_rwd`, the script runs 28 checks. It self-reports 17 S / 5 C / 2 V / 4 T.

**My census:**
- **Substantive (could fail independently of the input hashes): 6–7.**
  - `PREDICTED image sha == 30ff05fa` (a cross-author constant);
  - the base sha input guard;
  - the built-image `walk_all_blocks` / `walk` (an independent algorithm);
  - the rwd decode == image round trip;
  - the non-circular cipher check against V38;
  - the '/' header list. This one is half tautological: it reads back what `header_add` just wrote, but it does pin the
    spec's required list.
- **Vacuous, i.e. entailed by `BASE_SHA` + `EXP_CAVE_SHA` (+ the final image sha): 14.**
  - In [2]: subset, ==62, 60+2, imm16 1229, cap immediates;
  - In [3]: base==41, attributed set;
  - In [4]: owning block, trailer == EXP;
  - In [5]: stray, ==67;
  - In [6]: "fb 8192 / clamp 65535 / Ki 40 unchanged". The script labels this `T`, but it is vacuous: the base hash entails it.
  - The two base walks are correctly labelled V.
- **Tautological: 3.** The remaining [6] readbacks of what was just written: cave == CAVE, immediates, F181.
- **Constant-checks: ~4.** V38 rwd sha, A160 in source, path length, cave sha.

**Reading:** the script's "17 substantive" overstates it. About 10 of its S checks are entailed by the hashes. The decisive
checks are the image sha (as good as the reviser's independent splice; F1/F2 confirm it) and the two walks. **Not
load-bearing for the image**, because F1–F3 establish it directly.

## Defects (found as the adversary; reported, not fixed)

| # | what | where | severity | fix |
|---|---|---|---|---|
| D1 | **No revert rwds that list A16B.** Spec §11.2 requires a V298 revert and a V295 revert, each re-headered with A16B. The V299 script defines `REVERT_V298_RWD` but never uses it, has no V295 revert at all, and dropped V298's `write_revert()` (present in `build_v298_tva.py`). On disk, the only reverts are `…REHEADERED-FOR-REVERT-FROM-V298-A16A…` (V294, V295). By filename these list A16A, not A16B (BELIEF; I did not parse them). After V299 is flashed the car reports A16B, so **no prepared revert path exists**. | `build_v299_tva.py` (no `write_revert`); `accord-firmwares/flashing-2020accord/rwd/` | HIGH (flash readiness) | Port `write_revert` from `build_v298_tva.py`, generalised to `header_add`. Emit the V298 and V295 reverts with A16B. Assert `encs` == the original's, the decode == `177abf04…` / `5c044d65…`, and the originals re-hashed unchanged. Retire the V294 revert. |
| D2 | `V298_RWD_SHA` is a fabricated placeholder. It is **65 hex characters** (not a valid sha256), its tail is a synthetic counting pattern, and the comment says "asserted at WRITE" but it is **never asserted** anywhere. | `build_v299_tva.py`, module constants | MEDIUM (credibility: a fake hash in a build script) | Replace it with the real sha of the V298 rwd read from disk, and assert it in the revert step (D1). |
| D3 | The census mislabels its checks: ~10 "S" are entailed by the hashes, and the "unchanged cals" check is labelled T but is vacuous. | `build_v299_tva.py`, `Run.check` kinds | LOW | Relabel them. Add one independent check: a whole-file diff vs base computed outside the overlay path (F1's method). |
| D4 | The script's full diff covers only [0x13000,0x100000), not the whole file, and in predict mode it never reads the on-disk image (it is only hash-compared in write mode). | `build_v299_tva.py` [5] and `main()` | LOW (F1 shows the on-disk file is clean) | Diff over the whole file, and hash-compare the on-disk image in predict mode too. |
| D5 | **The V299 rwd does not exist yet** (the script ran in predict mode only). This lens did **not** verify the rwd '/' header (A110, A160, A16A, A16B), its x31 checksum, or that its payload re-extracts to the image. I scoped this out after the classifier interruption. | `accord-firmwares/flashing-2020accord/rwd/` (no V299 file) | HIGH until closed (FAIL criterion 5 is unverified, not passed) | Run in write mode, then have a lens that is not interrupted read back the header and payload and decode to `30ff05fa…`. |

## What a "do not flash" would have looked like, and why it did not fire
Any of these would have triggered it:
- a stray diff byte;
- an image ≠ base + the spec span;
- a stored trailer ≠ crc32;
- a chain or bootloader mismatch;
- the wrong F181 string.

None fired: 67/67 bytes were attributed, the trailer matches, the walks gave 49/49 and 50/50, and F181 reads A16B. Criterion 5
(the rwd) is open, which is why this verdict does not clear the build for flashing.
