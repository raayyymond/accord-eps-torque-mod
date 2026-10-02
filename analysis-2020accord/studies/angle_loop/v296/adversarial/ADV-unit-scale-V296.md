# ADV UNIT-SCALE — V296 — verdict: DO_NOT_FLASH

Adversary: UNIT-SCALE (a subagent). Date: 2026-10-01. Read-only. Nothing was built, written to the firmware repo,
flashed or sent.

## FAIL criteria (written first)
See `01_FAIL_CRITERIA_unit_scale_written_first.txt` in this folder. It lists U0–U10. Any one of them means DO_NOT_FLASH.
U0 is: "no V296 image or .rwd exists on disk, so no unit chain can be re-derived from it".

## Result
- **U0 FIRES (EVIDENCE).** Method: a Python listing of `accord-firmwares/analysis-2020accord/` (301 files) and
  `accord-firmwares/flashing-2020accord/rwd/` (306 files) for V294–V299 names. Positive control: the same scan finds
  the V294 and V295 image and .rwd. There is no V296 image, no V296 .rwd and no `build_v296_tva.py`. The newest file
  in either firmware folder is V295 (2026-09-30 12:21). This agrees with the builder's report: "V296 NOT BUILT".
- **U1 does not fire (EVIDENCE).** The same scan, plus `find -iname "*v296*"` over both repos, finds only this
  `studies/angle_loop/v296/adversarial/` folder. There are no orphan V296 artifacts.
- **U2–U10 were not evaluated.** A unit and scale chain must be re-derived from the built image, and there is no
  image. A check made against design files instead would not meet the brief.

## Withheld
I started a byte-level check of the existing rev2B flight cave against its score cave. A safety classifier
interrupted it. That analysis is withheld, and this report does not repeat or extend it.

## What a future pass needs
A built V296 image and .rwd, and the builder's reported hashes. Each of U2–U10 is then re-derived from that image.
