# FAIL CRITERIA — V299 build-script audit lens (written BEFORE the audit ran)

**Role:** adversary, build-audit lens (CLAUDE.md lens 3). Subagent of the V299 build round. Nothing flashed, no CAN, no git.
**Object under test:** the BUILT image `_v299_V299-ANGLELOOP...A3-2LVL.4096.6144.V2880.FRZ1229...A16B_plain_image.bin`
in `accord-firmwares/analysis-2020accord/` and `builds/v108_plus/build_v299_tva.py`, against V298 `177abf04...`.
Independence: my rebuild uses MY OWN script and MY OWN CRC/bootloader-walk code; the only inputs taken from the spec
are the 66-byte span contents (the thing being built) and the three point edits — every derived quantity (hashes,
CRC, block chain, rwd payload) is recomputed from bytes.

## DO_NOT_FLASH — any one of these
1. **Diff set wrong.** Full-file diff V298 -> built image is not EXACTLY the attributed set: {0xC4C64,0xC4C65} imm16
   00 02 -> cd 04; the bytes inside 0xC4C6A..0xC4CAB that the spec's table changes (60); 0x1310D 41 -> 42;
   0xC4FFC..FF f3 d8 7c 6b -> 95 3b dd 70. Any stray byte anywhere in the 1 MiB file (incl. outside the flashed
   region 0x13000..0x100000), or a missing one = FAIL.
2. **My independent rebuild does not reproduce the image** sha256 `30ff05fa...` bit-for-bit.
3. **CRC chain broken.** My own walk of the block/CRC chain over the built image finds any block whose stored CRC
   != computed CRC, or the main trailer != crc32 of its covered range, or the kit's `walk_all_blocks` / bootloader
   `walk` (NRC 0x72 predictor) report != 0 bad on the built image; or an edit straddles a block boundary.
4. **Cave decode != spec / mirror.** The built cave 0xC4C00..0xC4D04 sha != `e22193b9...`, OR the built span decodes
   (Ghidra) to anything other than the 24 rev-2 instructions, OR any branch outside the span targets inside it, OR
   any in-span branch targets outside {span, 0xC4CAC tail}, OR the cave contains any `st.*`/new RAM write.
5. **rwd wrong.** The V299 rwd (when produced by the build script) does not decode back byte-identical to the built
   image over 0x13000..0x100000; '/' header does not contain A16A AND A16B (the car currently reports A16A on V298);
   x31/container checksum fails; the revert rwds (V298, V295) do not carry A16B or their payload `encs` differ from
   the originals; V294's revert still offered as a live flash candidate.
6. **F181 mismatch.** The image's F181 string is not `39990-TVA,A16B`, or A16B is not in the V299 rwd's '/' list
   (that would make the build un-reflashable over itself) — or the image's F181 is in the '/' list of a revert
   in a way that blocks reverting.
7. **Build script would emit something other than what was audited** — e.g. its write mode writes a different image
   than its predict mode, an assertion that would have to fail is not checked, or the script asserts a hash that
   only its own constants entail while a substantive check (CRC chain, decode) is missing.

## PASS_WITH_DEFECTS
Image correct by items 1-4 and 6, but: rwd not yet produced/verifiable, assertion census shows most checks vacuous or
tautological with a load-bearing property unasserted, stale strings/paths, or documentation mismatches.

## PASS
None of the above; the rwd round-trips to the image and every header reads back as required.
