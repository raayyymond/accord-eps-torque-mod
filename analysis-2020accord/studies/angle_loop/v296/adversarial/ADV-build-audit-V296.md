# ADV build-audit — V296 (adversary BUILD-SCRIPT AUDIT), 2026-10-01

**VERDICT: DO_NOT_FLASH** — fail criterion **F0** (no V296 artifact exists; nothing has passed any gate).

The FAIL criteria were written to disk *before* any check ran:
`00_FAIL_CRITERIA_written_first.txt` (F0–F11, timestamp 2026-10-01T23:47Z).

## What was audited, and what was found

| # | check | result | method (EVIDENCE) |
|---|---|---|---|
| F0 | V296 image / .rwd / `build_v296_tva.py` exist | **NONE EXIST → FAIL (F0)** | `find` over both repos excl. `.git` + `adv_census_v296.py` glob `v296|A16A|REHEADER`; `builds/v108_plus/` newest file is `build_v295_tva.py` |
| F1 | orphan V296-named artifact | none — the only hit is `_scratch/angle_loop/adv-unit-scale-v296/`, an **empty** directory belonging to a sibling adversary (0 `.bin/.rwd/.hex`) | `ls -la`, `find -type f` |
| F7 | flashable .rwd per build number | **0** for V296 (no A16A-headered or REHEADERED file anywhere) | glob in `accord-firmwares/flashing-2020accord/rwd/` |
| F8 | originals untouched | **INTACT** — V295 image `5c044d65…52ed`, V295 rwd `f42a06bd…ae87`, V294 image `3143616d…dd85`, V294 rwd `a2b418f0…706a`, each = recorded value (BUILD-LINEAGE-PART6, STATE.md) **and** = the committed HEAD blob (`git hash-object` vs `git rev-parse HEAD:<path>`, 4/4 SAME) | sha256sum + git blob compare |
| — | repo state | `accord-firmwares`: clean (0 porcelain lines), HEAD `9567a84` (V295). Kit: HEAD `8dc8bf1`; untracked files are adversary outputs under `studies/angle_loop/v296/adversarial/` (this audit's `00_*`, `ADV-build-audit-V296.md`, `adv_census_v296.py`, plus a sibling unit-scale adversary's `01_*`) | `git status --porcelain` |
| F2–F6, F9–F11 | rebuild-to-sha, full diff, CRC walk, rwd decode, header strings, assertion census, model contract | **NOT APPLICABLE** — no image, no rwd, no script and no model edit exist to test | — |

## Builder's report vs disk
The builder reported "V296 NOT BUILT … nothing written". **Confirmed on disk** (EVIDENCE, table
above): no image, no .rwd, no build script, no re-headered revert copies; the V295/V294 originals are
byte-identical to the record and to git HEAD. The builder's claim "originals not re-hashed in this run"
is now closed: re-hashed here, all four match.

## Withheld / not completed
- **Independent byte-level re-verification of the known flight-cave link defect** (the refuters'
  finding the brief quotes) was started and then **interrupted by an automated safety classifier**;
  per that interruption it was not continued or reproduced. That defect therefore stands on the two
  refuters' EVIDENCE and the builder's source reading. **This audit adds no confirmation of it.** It does
  not affect this verdict, because F0 already blocks.
- The remaining build-audit steps (independent rebuild to the builder's sha, full-file diff vs V295, CRC
  trailers + bootloader walk, rwd decode, header part strings, assertion census, model contract) were
  **not performed, because there is no artifact to perform them on**. This is not a waiver: any future
  V296 must go through all of them on its own image.

## What a future V296 must clear before this verdict can change (BELIEF: restates the brief's gates)
F2–F11 in `00_FAIL_CRITERIA_written_first.txt`, run by an independent adversary on the built image. In
particular F9: the flight cave in the image must be shown to be correctly linked, by checks on the
flight bytes themselves rather than on the score cave.

## Files
- `00_FAIL_CRITERIA_written_first.txt` — the FAIL criteria, written first
- `adv_census_v296.py` — read-only census + original-hash check (no builder imports; writes nothing)
