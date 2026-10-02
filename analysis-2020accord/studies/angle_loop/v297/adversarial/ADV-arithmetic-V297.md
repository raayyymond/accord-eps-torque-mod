# ADV ARITHMETIC: V297 (C3-rev2 fallback), adversarial pass on the built image

**Verdict: DO_NOT_FLASH.** No V297 image exists, so there are no bytes to re-derive. Criteria A0 and A11
fire. This verdict does not say the C3-rev2 arithmetic is wrong. It says that no V297 arithmetic has been
checked, because nothing was built to check.

Written 2026-10-01 by the ARITHMETIC adversary (a subagent of the workflow). I built nothing, changed no
bytes and touched no other repo file. Everything this pass wrote is in this folder.

## 1. FAIL criteria, written before any check ran

See `00_FAIL_CRITERIA_written_first.txt` (timestamp 2026-10-01T23:48Z). Summary:

- **A0 / A1.** A0: there is no image. A1: there is an orphan V297 artefact.
- **A2.** The image or .rwd identity does not match.
- **A3.** My image-derived integer model and the scorer lane or the lane mirror disagree at any tick.
- **A4.** Width or sign error: an int16 store overflows, a 32-bit mul wraps, or ld.h and ld.hu disagree.
- **A5.** The sar-5 integrator increment has a dead zone or a one-sided drift at any G.
- **A6.** An input can break the A3 authority bound, or the bound overflows before its compare.
- **A7.** The freeze or op-skip path has a stale link, or the flight cave differs from the score cave.
- **A8.** The fade is non-monotone, exceeds unity, or overflows.
- **A9.** The 0x7FFF sentinel is used as a number.
- **A10.** The init of a new state word is not traced.
- **A11.** Any of A2–A10 was not run. A check that was not run does not count as a pass.

**DO_NOT_FLASH is the default.** It holds unless all of A2–A10 run on the built image and pass, so it is
reachable by construction.

## 2. What was checked (script `adv_arith_v297_presence.py`, output `adv_arith_v297_presence.out.txt`)

| # | Check | Result | Class |
|---|---|---|---|
| A0 | `_v297*_plain_image.bin` in `accord-firmwares/analysis-2020accord/` | **NONE** | EVIDENCE (Python glob, plus `ls` by hand) |
| A0 | `*V297*.rwd` in `accord-firmwares/flashing-2020accord/rwd/` | **NONE** | EVIDENCE (Python glob, plus `ls` by hand) |
| A0 | `builds/v108_plus/build_v297_tva.py` | **absent** | EVIDENCE (`Path.exists`) |
| A1 | Any file or folder named `*v297*` in either repo (walked, `.git` skipped) | Only `studies/angle_loop/v297/`, which **this pass created** (it was absent from the `angle_loop/` listing taken before `mkdir`) and which holds only `adversarial/` | EVIDENCE |
| ctx | V295 plain image sha256 | `5c044d65…40452ed`, matches the record | EVIDENCE (sha256) |
| ctx | V295 .rwd sha256 | `f42a06bd…beaae87`, matches the record | EVIDENCE (sha256) |
| ctx | git status, both repos | clean | EVIDENCE |

All of this matches the builder's own report ("NOT BUILT … no plain image … no .rwd").

## 3. Not run, so not passed (A11)

A2–A10 were **not run**. Each needs the built image's bytes:

- **A3.** The tick-by-tick mirror comparison against `panel2/score_freq.py`, `score_time.py` and `lane_mirror_v295.py`.
- **A4.** A census of store widths and sign extension over the cave as it sits in the image.
- **A5.** The sar-5 I quantum at every G-table row, read from the image's G table.
- **A6.** The A3 bound arithmetic, including saturated operands.
- **A7.** Freeze and op-skip landing addresses, and the G-table base pointer, decoded from the image.
- **A8.** The fade.
- **A9.** The 0x7FFF sentinel at every entry.
- **A10.** Engage, disengage and bail init.

## 4. Notes on the candidate caves (not V297, and not a verdict)

These are recorded so that a pass on a future V297 can confirm which cave it is reading. A defect or a pass
found in a loose hex file is not a finding on any image ("a null from the wrong image is not a null").

| Cave (decoded bytes) | Flight | Score | Flight = score? | Class |
|---|---|---|---|---|
| C3B-F (`rev2B/c3b_cave_C3B-F*.hex`) | 220 B, sha `9de9365fa952` | 220 B, sha `9de9365fa952` | **identical** (this supports the builder's point (b)) | EVIDENCE (decoded-byte sha256 and byte compare) |
| C3B-P (`rev2B/c3b_cave_C3B-P*.hex`) | 240 B, sha `9a10cdc4ec75` | 238 B, sha `b5a1d0ce1e0e` | differ from offset 0x12 (216 of the common 238 bytes differ) | EVIDENCE for the size and diff. **BELIEF** that this is the +2 B splice shift plus the known stale links; I did not re-decode the links. |

Note: the sha256 of each hex *text file* differs from these decoded-byte hashes. The decoded-byte hashes
are the ones that match the record (`9de9365fa952`, `9a10cdc4ec75`).

**The merged design page's recommended fallback has no bytes to check yet.** EVIDENCE: the
"What this page did not do" section of `DESIGN-ANGLE-LOOP-C3-rev2-2026-10-01.md` says *"The merged
fallback's F3 hardening is specified, not assembled — the builder assembles + H1s it"*. If V297 is built as
the hardened fallback, its cave will be new code. A7, the stale-link check, then applies in full, because
the most likely tool for the splice is `rb_build.add_opskip`, the helper with the known defect. If V297 is
built as the default C3B-F (220 B), the C3B-F flight and score caves are the same bytes. In that case A7's
flight-vs-score clause is answered by that identity, but A3–A10 must still be run on the image.

## 5. What a valid re-run needs

1. A V297 plain image, its .rwd and its build script on disk, with a reported sha256. Then re-run
   `adv_arith_v297_presence.py`, and A0 clears.
2. The whole ARITHMETIC pass (A2–A10) run against **those** bytes. That means an integer re-implementation
   built by reading the cave and the lane out of the image (an offset-checked extract, decoded with Ghidra
   dry-run or a fresh import with full analysis), not from the build script or the design page.
3. The same written-first FAIL criteria (`00_FAIL_CRITERIA_written_first.txt`), unchanged.

## 6. Scope and what was withheld

- I did not run arithmetic re-derivations on the loose candidate cave hex files. The brief names the BUILT
  image, and results on a hex file outside an image would not be evidence about V297.
- I built, assembled, relinked and flashed nothing, and wrote no image or .rwd.
- This is a snapshot taken at the time of writing. If another agent writes a V297 artefact afterwards, it
  has **not** passed this pass.
