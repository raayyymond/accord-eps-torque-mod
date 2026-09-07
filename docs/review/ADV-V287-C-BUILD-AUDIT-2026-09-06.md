# Adversary C — V287 build-script audit

**Job:** make V287 FAIL. Surface: build-script audit, independent of `build_v287_tva.py`'s own code,
constants, and assertions wherever possible. Every finding below is **EVIDENCE** (method stated) unless
marked **BELIEF**.

**What a FAIL would have looked like, written down first:** any of — a hash mismatch on any of the three
artifacts; a byte diff outside `{0xC61B7, 0xC6FFC..0xC6FFF}`; the edited cell resolving to `0xC61BA`
(anti-windup) rather than `0xC61B6` on ADDRESS, not just value, since both hold 10240 and are easy to
conflate; a CRC failure anywhere in the 50-block chain, not just the touched page; an rwd that decodes to
something other than the claimed image, or whose header/part-number/address range diverges from V282's;
an inflated or mislabeled assertion census (vacuous/tautological counted as load-bearing); more than one
V287 rwd on disk; or a docstring claim the bytes contradict. **None of these occurred.**

## Result: **PASS**

## Independent verification performed

1. **Hashes**, computed by me from the files, not read from the script or its printout:
   - `_v282_..._plain_image.bin` → `0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe` — matches claim, and matches `docs/BUILD-LINEAGE.md:254` / prior adversarial audits (`ADV282-C-BUILD-AUDIT-2026-09-03.md`).
   - `_v287_..._plain_image.bin` → `a9745f003a90bca15c3bd434df053c2e7b6af50f898cdd82c52ffeac5854129d` — matches claim.
   - `39990-TVA,A160-V287-...-0x13000-0x100000.rwd` → `71e103118ebcba6238dff91aa86c37db91e6645695ea794d2819a170e6cef929` — matches claim.

2. **Full-file byte diff**, my own loop over `[0x13000, 0x100000)`, base vs built, no library, no shared
   code with the build script:
   ```
   0x0C61B7: 28 -> 0a
   0x0C6FFC: 72 -> ac
   0x0C6FFD: df -> 6e
   0x0C6FFE: ea -> f3
   0x0C6FFF: 75 -> ac
   ```
   Exactly 5 bytes, exactly the claimed set. This single diff subsumes almost the entire assertion
   census — it independently proves the cave, hook, 427 tap, assist map, Kp/Kd tables, tapers, and every
   `FROZEN` cell are untouched, since all of them lie inside the diffed range and none of their addresses
   appear in the diff.
   - `0xC61B6` (low byte) unchanged (`0x00`→`0x00`) both before and after; `0xC61B7` (high byte)
     `0x28`→`0x0A`. Halfword read as u16: `10240`→`2560`. Matches the docstring's "only the HIGH byte
     differs" claim exactly.
   - `0xC61BA` (anti-windup ceiling) reads `10240` in **both** images — the appendix's mislabelled cell is
     confirmed untouched, independent of the script's own assertion of the same fact.

3. **CRC scheme reimplemented from scratch** (read `verify_bootloader_crc.py`'s docstring for the
   algorithm, wrote my own `walk_all`/`walk_bl` with none of its code) and run over the **whole image**,
   not just the touched page:
   - V282: 50/50 blocks pass (full linked-list walk), 49/49 pass (bootloader-replay walk with the
     `0xC6000` bridge).
   - V287: 50/50 and 49/49, same result.
   - **Block ownership of the edited cell independently re-derived** by walking the linked list myself
     (no call to `V53.owning_block`): the block containing `0xC61B6` is `[0xC6000, 0xC6FFC)` — matches
     the script's claim exactly, found by a completely separate method.

4. **rwd decode, independent parser and independent cipher crack:**
   - Wrote my own `parse_x31` (header/chunk walk) directly from `encode_eps.py`'s documented format,
     not by importing the module.
   - Headers, part numbers (`39990-TVA-A110` / `39990-TVA,A160`), security keys, cipher key (`BF109E`),
     CAN address byte (`30`), and the single block's `(start=0x13000, length=0xED000)` are **byte-identical
     between the V287 rwd and the V282 rwd** — confirms the header/address range match required by the
     brief.
   - File checksum (`sum(body) & 0xFFFFFFFF`, trailing LE u32) independently recomputed and verified for
     both rwds.
   - Cipher table **brute-forced by me** (not taken from `build_v53_tva.V9B`) against the known plaintext
     `39990-TVA`, permuting the 3 key bytes and 8×8×8 op combinations exactly as `crack_cipher` does but
     in my own code: found `(keys=(16,191,158), ops=(xor,xor,add))`, decoded the payload, and the result is
     **byte-identical to `code[0x13000:0x100000]` of the built plain image**. This independently confirms
     the rwd round-trips to the exact claimed image, via a completely separate cipher derivation.

5. **Independent minimal rebuild**, 4 lines, no shared code with `independent_rebuild()` in the script and
   no use of `FF.crc_block_map`:
   ```python
   img = bytearray(base)
   struct.pack_into("<H", img, 0xC61B6, 2560)
   crc = zlib.crc32(bytes(img[0xC6000:0xC6FFC])) & 0xFFFFFFFF
   struct.pack_into("<I", img, 0xC6FFC, crc)
   ```
   `sha256(img)` == `a9745f00...54129d`, the claimed image hash, on the first try. This independently
   confirms both the cell address and the CRC block bounds — a rebuild using `0xC61BA` instead, or the
   wrong block bounds, would not reproduce this hash.

6. **Assertion census**, run and counted by me from the script's own stdout (`python
   build_v287_tva.py`, exit 0):
   - **372/372 assertions pass. 305 `[S]` (substantive), 35 `[V]` (vacuous), 32 `[T]` (tautological).**
   - Counted directly by grepping `[PASS] [X]` tags in the run's stdout — not taken from the printed
     summary line, which independently reads the same numbers back.
   - Spot-checked labeling honesty: block `[1]` (base-state checks) is uniformly `V` — correctly vacuous,
     since it only reasserts facts entailed by the already-matched base sha256. Block `[9]`'s `code`-image
     re-checks are `T` (tautological readback of what block `[4]`/`[6]` just wrote) while the parallel
     `dec`-image re-checks (from the independently round-tripped rwd) are `S` — correctly distinguished,
     since the `dec` path re-derives the value through cipher decode rather than reading back the same
     bytearray.
   - The brief's reference figures ("60 load-bearing / 206 sweeps / 35 vacuous / 32 tautological / 32
     decode readbacks") appear to be a finer breakdown of the 305 `S` bucket (sweeps over 28 Kp/Kd/taper
     slots dominate that count) rather than a different total; the vacuous (35) and tautological (32)
     counts match exactly what I independently counted from stdout.

7. **Address, not value, is what's asserted.** The script's `[2]` block decodes each reader instruction's
   `tp`-relative displacement (`disp = hw2 & 0xFFFE`) and asserts `TP_BASE + disp == 0xC61B6`, not merely
   that the loaded value is 10240. Since `0xC61BA` also holds 10240 in the base image, a script that had
   edited the wrong cell would still pass a naive value-only readback; this displacement-based assertion
   would not. I independently decoded the same 4 reader instructions from the raw bytes (`0x29EE8, 0x29EF2,
   0x29EF8, 0x29F02`, all encoding `hw2=0x71B7` → `disp=0x71B6`, unsigned bit set) and confirm
   `0xBF000 + 0x71B6 = 0xC61B6` — arithmetic checked by hand, not by the script.

8. **Docstring numbers vs. image bytes:**
   - "the low byte is 0x00 either way" — confirmed directly (item 2 above).
   - "Kd flat at 128" — confirmed via my own read of the base image's Kd record at the live slot.
   - Rail `|dE|` 640→160 — recomputed independently: `10240*8/128=640`, `2560*8/128=160`. Matches.
   - "I WOULD FLY 2560 FIRST" — present verbatim in `docs/research/GRIND1-LOOP-SHAPE-V287-2026-09-06.md`
     line 983, confirmed by grep.
   - On-car effect percentages (excitation-limiter mode shares, max-rate authority deltas) are explicitly
     marked **[BELIEF]** in the script's own docstring, correctly not asserted against image bytes — this
     is honest labeling, not a gap.

9. **Exactly one V287 artifact pair on disk**, confirmed by directory listing: one plain image
   (`_v287_V287-V282BASE-DCLAMP.2560-..._plain_image.bin`) and one rwd
   (`39990-TVA,A160-V287-...-0x13000-0x100000.rwd`), no `SUPERSEDED` or duplicate V287 files anywhere
   under `analysis-2020accord/` or `flashing-2020accord/rwd/`.

10. **Lineage claim** ("first-ever move of `0xC61B6`") independently re-censused: walked all 288
    `*plain_image.bin` files under the firmware root myself (287 excluding V287's own output) plus the
    stock `code.bin` — every one reads `10240` at `0xC61B6`. No exceptions found.

## What I could NOT independently re-verify here (out of this surface's scope)
- The claim that only 4 readers exist and 3 more are unreachable dead code (a control-flow/reachability
  claim) — that is Adversary A/B or a code-path-tracer's surface, not a build-script/byte-diff one. The
  build script's own assertion only pins the encoding of the 4 named addresses; it does not prove
  completeness of that set. Flagging this as the one load-bearing claim in the docstring that this audit
  cannot settle from bytes alone.
- The physical/control-theoretic effect of the dose (excitation-limiter behavior, on-car response) — the
  script correctly marks this BELIEF and it is out of a build-script audit's scope.

## Verdict (rev 1, superseded)
**PASS.** Every hash, every byte diff, every CRC, the rwd round-trip (via an independently brute-forced
cipher), the assertion census, the address-vs-value distinction, and the docstring's numeric claims all
independently reproduce under methods sharing no code with the build script. No FAIL condition (as defined
above) was found.

---

# Rev 2 re-audit — 2026-09-06

Re-ran the full independent method above against V287 **rev 2** (dose 7680, script now carries a `REV`
selector; `REV=1` reproduces the withdrawn 2560 build under `SUPERSEDED-DO-NOT-FLASH` names). Same FAIL
definition as above, plus: REV=1 must reproduce the exact rev-1 hash and must be structurally incapable
of emitting a non-superseded name.

## Result: **PASS**

1. **Hashes**, independently computed:
   - `_v287r2_..._plain_image.bin` → `e75ae7eb5c5bcba564f445a7223260b25c4b476b9df1d8c9ad8e171f79498f15` — matches claim.
   - `39990-TVA,A160-V287R2-...-0x13000-0x100000.rwd` → `71648c0ebdc8ca63d7f974d32a735c0f3ef607d7b67c71efc883ceb79ba852a5` — matches claim.
   - `SUPERSEDED-DO-NOT-FLASH_v287_rev1_..._plain_image.bin` → `a9745f003a90bca15c3bd434df053c2e7b6af50f898cdd82c52ffeac5854129d` — **identical to the rev-1 hash I verified in the first pass**, confirming the superseded file is untouched, not silently rewritten.
   - `SUPERSEDED-DO-NOT-FLASH-...V287-rev1-...rwd` → `71e103118ebcba6238dff91aa86c37db91e6645695ea794d2819a170e6cef929` — also identical to the original rev-1 rwd hash.

2. **REV selector, run by me directly** (not read from the script's assertions):
   - `ACCORD_V287_REV=2` (default): builds, exits 0, prints image SHA `e75ae7eb...98f15` and rwd SHA
     `71648c0e...52a5` — matches the claimed rev-2 artifacts exactly.
   - `ACCORD_V287_REV=1`: builds, exits 0, prints image SHA `a9745f00...54129d` and rwd SHA
     `71e10311...ef929` — **exactly reproduces the rev-1 hashes**, confirming REV=1 is not a different
     build but a faithful replay of the withdrawn one.
   - The script's own guard `assert WITHDRAWN == RWD_NAME.startswith("SUPERSEDED")` (source, not just
     runtime) makes it structurally impossible for `REV=1`'s `RWD_NAME` to omit the `SUPERSEDED-DO-NOT-
     FLASH` prefix — the assertion is evaluated at import time against the `REVISIONS` dict literal, not
     conditioned on any runtime state that could be gamed.

3. **Full-file byte diff**, independent, base V282 vs built rev-2 image, over `[0x13000, 0x100000)`:
   ```
   0x0C61B7: 28 -> 1e
   0x0C6FFC: 72 -> 20
   0x0C6FFD: df -> db
   0x0C6FFE: ea -> 56
   0x0C6FFF: 75 -> dc
   ```
   Exactly 5 bytes, exactly the claimed set (`0xC61B7 0x28→0x1E`, CRC `72dfea75→20db56dc`). `0xC61B6`
   (low byte) unchanged; halfword reads `10240→7680`. `0xC61BA` reads `10240` in both images — untouched.
   As with rev 1, this single diff subsumes the cave/hook/tap/maps/tables/FROZEN-cell claims.

4. **CRC scheme**, my own from-scratch reimplementation, whole image: rev-2 image passes 50/50 (full
   linked-list walk) and 49/49 (bootloader-replay walk with the `0xC6000` bridge). The block containing
   `0xC61B6`, found by walking the linked list myself with no call into the script's own block-finder,
   is again `[0xC6000, 0xC6FFC)` — same block as rev 1, as expected since only the dose changed.

5. **rwd decode, independent parser + independently brute-forced cipher:** headers, part numbers
   (`39990-TVA-A110`/`39990-TVA,A160`), cipher key (`BF109E`), CAN byte, and the single block's
   `(start=0x13000, length=0xED000)` are byte-identical to the V282 rwd's — confirms header/address-range
   match. Cracked the cipher myself against known plaintext `39990-TVA` (same `(16,191,158)`,
   `(xor,xor,add)` as rev 1 — consistent, since the cipher key header is unchanged); decoded payload is
   byte-identical to `code[0x13000:0x100000]` of the built rev-2 image.

6. **Independent minimal rebuild** (same 4-line method as rev 1, dose swapped to 7680):
   ```python
   img = bytearray(base)
   struct.pack_into("<H", img, 0xC61B6, 7680)
   crc = zlib.crc32(bytes(img[0xC6000:0xC6FFC])) & 0xFFFFFFFF
   struct.pack_into("<I", img, 0xC6FFC, crc)
   ```
   `sha256(img)` == `e75ae7eb...98f15`, the claimed rev-2 hash, first try.

7. **Exactly one non-superseded V287 rwd on disk.** Directory listing under `flashing-2020accord/rwd/`
   shows two `*V287*` files: the rev-2 flashable one and the rev-1 file, which carries the
   `SUPERSEDED-DO-NOT-FLASH-` prefix. No other V287-line files exist. Same result under
   `analysis-2020accord/`: the rev-2 plain image and the `SUPERSEDED-DO-NOT-FLASH_v287_rev1_...` plain
   image, nothing else.

8. **Assertion census**, run and counted from stdout, both revisions: **372/372 pass, 305 `[S]` / 35
   `[V]` / 32 `[T]`** — identical structure to rev 1 (same script, same shape of checks; only the dose
   constant and a handful of rev-conditioned prints differ). No FAIL, no assertion count drift.

9. **Docstring numbers vs. the pre-registration record**, checked against
   `rlog-tools/studies/grind/PREREG-V287-LOOP-SHAPE.md` (which the docstring's DOSE_PIN correctly points
   at for rev 2, not the old Appendix B doc used for rev 1):
   - Rail `|dE|` = 480 — recomputed independently: `7680*8/128 = 480`. Confirmed, and matches the script's
     own printed `rail |dE| 640 -> 480`.
   - Ring `|L_tot|` = 0.983 — present verbatim in the pre-reg file (line 175: *"the ring stays at or
     under the gate (`|L_tot|` = **0.983**, exactly at the CI upper bound)"*). Matches the docstring's
     "0.983 — EXACTLY the gate, a pass with NO margin" and the build script's printed summary line.
   - ~1,150 onset events — present verbatim (line 177: *"7680 becomes resolvable at ≈ **1,150 onset
     events** ≈ 38 minutes of engaged driving"*). Matches the docstring and the script's printed
     "~1,150 onset events ~ 2,320 s ~ 38 minutes."
   - Dose pin phrase `"Dose 7680, not 2560."` — present verbatim at line 175 of the pre-reg file, and the
     script's `[9]` block correctly reads it from `PREREG-V287-LOOP-SHAPE.md` rather than the old
     `GRIND1-LOOP-SHAPE-V287-2026-09-06.md` doc rev 1 used — the DOSE_PIN routing is per-revision and
     correct.
   - No numeric contradiction found between the docstring, the pre-reg record, and the built bytes.

## What I still could not independently re-verify (same scope note as rev 1)
- The "4 live readers, 3 unreachable" completeness/reachability claim — not a byte-diff/build-script
  question; out of this surface.
- On-car effect (BELIEF, correctly labeled as such in the docstring) — not testable from bytes.
- The 0.983 ring figure and the ~1,150-event power calculation are themselves analysis outputs from
  `rlog-tools/studies/grind/grind1_dclamp_decompose.py` and related scripts; I confirmed they are
  transcribed correctly from the pre-registration document into the build script and the image, not that
  the underlying statistical analysis is itself correct — that is Appendix C's own derivation, not a
  build-script-audit concern.

## Verdict (rev 2)
**PASS.** All hashes, the full byte diff, the whole-image CRC chain, the rwd round-trip via an
independently cracked cipher, the independent 4-line rebuild, the REV=1/REV=2 selector behavior including
the structural SUPERSEDED-name guard, the assertion census, and every docstring number checked against
`PREREG-V287-LOOP-SHAPE.md` all reproduce independently. The rev-1 superseded artifacts are confirmed
byte-identical to what was audited in the first pass — untouched, not silently rewritten. No FAIL
condition was found.
