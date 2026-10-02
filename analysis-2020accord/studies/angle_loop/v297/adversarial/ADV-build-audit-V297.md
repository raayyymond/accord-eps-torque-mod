# ADV BUILD-AUDIT — V297 (C3-rev2-F fallback) — 2026-10-01

**Verdict: DO_NOT_FLASH.** There is no V297 to flash. There is no plain image, no .rwd, no build script, no flight cave hex and no revert copy. An audit of an absent build cannot clear anything, so the only verdict available is DO_NOT_FLASH, and it was reachable by construction (FAIL criterion F0).

The builder's own report ("NOT BUILT, no bytes changed") is **confirmed from the filesystem**. It is EVIDENCE, by the method in §2.

Nothing in this audit flashes, sends or edits anything. The checks are read-only, apart from the files written into this folder.

| file | sha256[:16] | role |
|---|---|---|
| `00_FAIL_CRITERIA_written_first.txt` | — | FAIL criteria F0–F12, written before the rebuild, CRC, decode and census checks ran |
| `adv_v297_audit.py` | `a6fc6e3da06b97e9` | independent audit, stdlib only, **no kit or builder imports**: own x31 parser, own cipher solver, own CRC chain replay, census |
| `adv_v297_audit_out.txt` | — | its output: **42 checks, 41 pass, 1 fail** (the V31P duplicate, §3 finding 4) |
| `adv_v297_model_contract.py` | `1328f425e0cdd3e3` | re-runs the golden-model contract, read-only |
| `adv_v297_model_contract_out.txt` | — | 94 symbols, 2512 B, sha `740f4bcd…`: **PASS** |

---

## 1. FAIL criteria (verbatim summary of the file written first)

DO_NOT_FLASH if any one holds:
- **F0** no artifact
- **F1** orphan V29x/A16A/REHEADERED artifact
- **F2** rebuild sha mismatch
- **F3** unexplained byte vs V295
- **F4** CRC trailer/walk failure
- **F5** .rwd does not decode to the image
- **F6** '/' header missing a part string
- **F7** more than one flashable .rwd per build number
- **F8** V294/V295 originals changed
- **F9** stale relink in the flight cave
- **F10** cave not pinned byte-exact by the design
- **F11** pass resting on vacuous, tautological or stale assertions
- **F12** model contract broken

## 2. Results per criterion

| crit | result | method (EVIDENCE unless marked) |
|---|---|---|
| **F0** | **TRIPPED: DO_NOT_FLASH** | Census over both repo trees for `v29[6-9]`, `a16a` and `reheadered`. It finds no image, no .rwd, no `build_v297_tva.py` and no hex. Every name hit is an adversary note or script in `studies/angle_loop/v29[67]/` or `_scratch/angle_loop/adv-*`. The firmware repo's newest files are V295's (2026-09-30 12:21). `git status --porcelain --ignored` is clean in accord-firmwares except `__pycache__`; in the kit the only untracked items are the adversary folders `studies/angle_loop/v296/` and `v297/`. |
| F1 | clear | Same census. 0 unexpected of 14 name hits. Positive control: it finds the adversary folders, the V294/V295 .rwds and the V31P duplicate. |
| F2, F3, F5 (for V297) | **not testable: no V297 image** | — |
| F4, F5, F6 (for the V295 base) | clear | Own x31 parse plus own cipher solve: key `BF109E`, order (0x10, 0xBF, 0x9E), ops (xor, xor, add). V295 and V294 each decode to their plain image over `[0x13000,0x100000)` bit-for-bit (0 differing bytes). File checksum trailers are correct (V295 `0x04D4BBCA`, V294 `0x04D4BB0B`). Own CRC replay: bootloader walk with the 0xC6000 bridge **49/49**, full linked chain **50/50**, both images. **Negative controls:** a 1-bit flip at 0xC4C00 fails exactly block 0x13000; a flip at 0xC5100 is invisible to the bootloader walk but caught by the full chain, as the bridge predicts. |
| F7 | clear for V294–V299 (V297 = 0, V296 = 0, V298 = 0, V295 = 1, V294 = 1); **pre-existing violation at V31P** (finding 4) | Scan of `flashing-2020accord/rwd/` excluding SUPERSEDED, DO-NOT-FLASH and REHEADERED names. |
| **F8** | clear: **revert path intact** | sha256 vs the recorded values in `BUILD-LINEAGE-PART6-V291-ONWARD.md` (V294 entry, V295 entry) and `STATE.md`: V295 image `5c044d65…52ed`, V295 .rwd `f42a06bd…ae87`, V294 image `3143616d…dd85`, V294 .rwd `a2b418f0…706a`, all equal. `git hash-object` equals the index blob for all four files. **No REHEADERED copy exists**, so none was written and none can have touched the originals. |
| F9 | **not applicable to V297 as it stands; applies to any hardened fallback** (finding 3) | The default C3B-F flight hex is byte-identical to its score hex (both sha `9de9365fa952`, 220 B), so add_opskip never spliced it. The known defect is reproduced on C3B-P (finding 3). |
| **F10** | **TRIPPED for the RECOMMENDED fallback** (finding 2) | Merged page, ruling 3 ("Harden the FALLBACK's F3"): "≈+20 B". Cave row: "≈240 B (hardened)", and only the default carries a sha. Close-out paragraph: "the fallback's F3 hardening is specified, not assembled". No hardened hex exists in `c3/`, `c3/rev2A/` or `c3/rev2B/` (full inventory hashed). |
| F11 | **builder census: 0 assertions; nothing to census (no script)** | `build_v297_tva.py` is absent. My own assertion census is in §4. |
| F12 | clear | `import eps_lkas_chain_model`: **94** non-dunder symbols. `_self_check()` + `_demo()` stdout is **2512 B, sha `740f4bcd0534212a0c200a9359b0b4318e1419bea33823d66e2e89c12961102d`**. No `_self_check_v29[6-9]` or `V29[6-9]` appears in any `model/*.py`. The model dir is unchanged in git (last commit `0f750c3`, 2026-09-30). |

## 3. Findings (most severe first)

1. **BLOCKING: no V297 build exists (F0).** The builder stopped during the design read, after an automated-classifier interruption, and produced nothing. It said so. The filesystem agrees on every point checked. **Do not flash anything under a V297 name; none exists.** A file that later appears under that name is unaudited until a fresh adversarial pass runs on that exact image.

2. **BLOCKING for the recommended variant: the hardened C3-rev2-F has no byte-exact reference (F10).** The merged design recommends the hardened fallback (ruling 3, a `jr 0x2a164` validity op-skip, ≈+20 B, ≈240 B, ≈287 B written). It then delegates the assembly to the builder ("the builder assembles + H1s it"). Any V297 cut to the recommended variant therefore has no design hash to rebuild against. An adversary would have to re-derive about 20 B of new cave code from prose. Only the 220 B default C3B-F (sha `9de9365fa952`, F3 rate-invalid PI-only ring *declared*) exists as bytes.
   **Fix (orchestrator ruling, not mine):**
   - either build the default C3B-F and accept the declared F3 fault (the page offers this as "the byte-minimal alternative if the orchestrator accepts the declared rare fault");
   - or have a designer publish a byte-exact, relinked, H1-validated hardened listing with its sha before any builder starts.

   This matches the builder's first concern. EVIDENCE: a grep of the merged page plus the hex inventory.

3. **HIGH (inherited by any hardened-fallback assembly): the add_opskip relink defect, reproduced from the C3B-P bytes.**
   - **The table pointer is stale.** The flight hex `c3b_cave_C3B-P.hex` (240 B, sha `9a10cdc4ec75`) carries `29 06 c4 4c 0c 00` at +0x1C, i.e. `mov 0x000C4CC4, r9`. Its table now sits at **0xC4CC6**: `score[+0xC4:] == flight[+0xC6:]`, tail `ca029a0411043307…`.
   - **The freeze-return lands 2 B off.** The jr at flight +0xC0 lands at **0x29D80**. The score cave's jr at +0xBE lands at **0x29D7E**.
   - **The splice itself is correctly placed.** The op-skip sits at +0x12…+0x15. Its jr at +0x14 → 0x2A164 is right for its location.
   - **Mechanism:** every byte after the splice was copied verbatim, so after a 2-byte insert 216/220 tail bytes match the score cave, including the stale absolute and relative references.

   The default C3B-F is **not** affected: its flight bytes equal its score bytes (table pointer `0xC4CB2`, jr at +0xAC → 0x29D7E).
   **Status:** EVIDENCE at byte level. The Python decode uses Format VI `mov imm32` (hw1 = `0x0620|reg`) and Format V `jr` (hw1 & 0xFFC0 = `0x0780`, even target, hw2 bit 0 = 0). Positive controls: the decoder reproduces the design's stated `0x29D7E` from the score cave and `0x2A164` from the op-skip.
   **Ghidra NOT run on these bytes.** They are in no open program; only stock `code.bin` and V294 are open. A Ghidra decode of an imported cave program is the pending second method. The defect was already EVIDENCE from two refuters; this is a third, independent reading.
   **Fix:** relink inside `rb_build.add_opskip` (shift every absolute pointer into the cave at or after the splice, and every PC-relative displacement that crosses it). Then run H1 on the **flight** bytes and require the flight to equal score plus the declared op-skip, with no other difference.

4. **LOW, pre-existing, not V297: two flashable .rwds for V31P.**
   - `39990-TVA,A160-V31P-gateflags-330piggyback-caveC4B34-…rwd`
   - `39990-TVA,A160-V31P-V2-gateflags-v2-angleconsensus-hardcut-caveC4B34-…rwd`

   They are different files (sha `20365964…` and `28890150…`), both from commit `21debdf initial`, and neither is marked SUPERSEDED. This breaks the "exactly ONE flashable .rwd per build number" rule. Renaming the superseded one is the operator's call; it is outside this audit's scope and I touched nothing.

5. **INFO: header and naming traps a future V297 must clear.**
   - The image's version string at 0x13100 is `39990-TVA,A160`, with a **comma**; byte 0x1310D = `0x30`. After 0x30 → 0x41 it reads `39990-TVA,A16A`. The '/' header must then list `39990-TVA,A16A` **and** `39990-TVA,A160` in that comma form. V294/V295 today list `['39990-TVA-A110', '39990-TVA,A160']`. A hyphenated `TVA-A16A` would not match the image.
   - The kit helper `encode_eps.roundtrip` / `build_rwd_from_template` derives its known-plaintext from the filename with `39990[-]?([A-Za-z0-9]{3})[-_]?([A-Za-z0-9]{4})`. That pattern **returns None on every comma-form name** (tested on `39990-TVA,A160-V295-…` and `39990-TVA,A16A-V297-…`). A builder using those helpers must pass `expected_part_override`.
   - The template `build_v295_tva.py` calls `encode_x31` directly, so it is unaffected.

   EVIDENCE: my own decoder reproduced the original version of this trap. My first run used the hyphen form and failed the cipher solve until I corrected it to the comma form.

6. **INFO: the base is exactly as the brief states.** V295 − V294 over `[0x13000,0x100000)` is **6 bytes**: cal `0xC63EA` u16 **567 → 1050**, plus the CRC word at `0xC6FFC` (block `[0xC6000,0xC6FFC)`). Zero bytes are unexplained.

7. **INFO for the orchestrator's roll-call.**
   - A parallel **V298** builder is live: `_scratch/angle_loop/v298-build/probe1.py`, 2026-10-01 16:48, read-only (it reads V295 and prints sites). It has no V298 image or .rwd yet.
   - Other V297 adversaries are writing into this same folder: `ADV-arithmetic-V297.md`, `ADV-interlocks-gates-V297.md`, `adv_ig_v297_inputs.py`, `u1_prebuild_bytes.py`, and a unit-scale fail-criteria note.
   - V296 adversary notes also exist.
   - None of these is a build artifact.

## 4. Assertion census

**Builder's assertions:** none; there is no build script. Nothing can be vacuous, tautological or stale because nothing exists.

**My own 42 checks**, classified honestly:

| class | n | what |
|---|---|---|
| V297-specific, non-vacuous | 5 | no unexpected artifact; V297 .rwd count = 0; `build_v297_tva.py` absent; no `_v29[67]_` image; no duplicate per build number *(this last one FAILs on V31P)* |
| neighbouring build numbers | 3 | V296 = 0, V295 = 1, V294 = 1 flashable .rwd |
| **load-bearing for the revert path** | 10 | 4 sha256-vs-record, 4 git-blob-vs-disk, 2 single-image |
| **entailed by the hashes above** (vacuous *for "did the base change"*) | 16 | 10 decode/header/checksum + 4 CRC + 2 V295−V294 diff. They re-prove that the *recorded* artifacts are internally consistent, but add nothing once the hash checks pass. |
| design-record (hex files, not an image) | 5 | C3B-F flight = score, 2 design-page shas, table moved, defect reproduced |
| negative controls | 3 | CRC walker can fail (main block); bridge blind spot caught by the full chain; the image comparison can tell V294 from V295 |
| tautological (readback of something I wrote) | **0** | — |
| stale hard-coded expectations | 6 *(risk, not failure)* | the 4 RECORDED sha256 values, copied from BUILD-LINEAGE-PART6 (they go stale if the record is re-issued), and the expected block counts 49/50 |

The three script bugs in my own first run are disclosed, not hidden. Each is marked `SCRIPT FIX r2/r3` in the source.
- **Known plaintext:** the hyphen form → the comma form.
- **Census allowlist:** it missed the `_scratch/angle_loop/adv-*` folders.
- **Census pattern:** widened to V298/V299 after a live V298 builder was found.

## 5. Pre-registration for the real V297 audit (when bytes exist)

A future V297 is **DO_NOT_FLASH** unless every one of these holds:
- an independent rebuild from `5c044d65…` reproduces its sha;
- every differing byte in `[0x13000,0x100000)` maps to:
  - the 20 B hook/ops edit,
  - the 24 B edits,
  - the cave at `0xC4C00` (220 B default, or the published hardened length),
  - `0x1310D` (0x30 → 0x41),
  - and CRC trailer words only;
- the cave equals the design's published sha: `9de9365fa952` for the default, or the hash of a published hardened listing (finding 2);
- for a hardened cave, flight = score plus exactly the declared op-skip, with every pointer and displacement after the splice relinked (finding 3);
- CRC 49/49 and 50/50;
- the .rwd decodes bit-for-bit;
- '/' lists `39990-TVA,A16A` and `39990-TVA,A160`;
- exactly one flashable V297 .rwd;
- the REHEADERED revert copies of V295/V294 decode to the untouched images, while the originals keep the four hashes above;
- `_self_check_v297` is added with the contract still 94 symbols / `740f4bcd…`;
- H1 has run on the **flight** bytes.

## 6. Withheld

Nothing was withheld by choice. Everything that targets a V297 image could not run, because no image exists:
- the rebuild to the builder's sha;
- the full-file diff vs V295;
- the CRC recomputation on V297;
- the V297 .rwd decode and its header check;
- the census of the builder's assertions;
- the revert-artifact verification.

The Ghidra decode of the C3B-P cave bytes is pending (finding 3).
