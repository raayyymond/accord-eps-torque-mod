---
name: accord-fork-dev-branch-sgsp-is-the-rework-2026-10-27
description: 2026-10-27 — fork work moved to branch `dev` (accord-PTM + upstream Dom merge, pushed); upstream Dom has no rework, the rework is SecretGoodStarPilot (StarPilot 7.0, unrelated history, port not merge)
metadata:
  type: project
---

**2026-10-27.** Operator: *"I do not want to work off of accord-PTM. Copy accord-PTM to a new branch, dev."*
- `dev` = `accord-PTM` `0b1b09a1eb` + merge of `upstream/Dom` `4bfdfd0074` ("Trick or Treat", 3 files, clean) → `5ec9ae7449`, pushed `origin/dev`. `accord-PTM` frozen as the release record.
- **Upstream `Dom` has NO major rework** (EVIDENCE: `git rev-list --left-right --count accord-PTM...upstream/Dom` = 14 / 1). The rework is **`upstream/SecretGoodStarPilot`**: StarPilot 7.0 "Domathon", fresh rebase onto openpilot 0.11.x, 19 060 commits, NO common ancestor with Dom, tree under `openpilot/`, Honda port stock (our carcontroller differs by 514 lines), no `the_galaxy.py`. Its README says feature migration is in progress. `upstream/testing` shares its history (142 behind).
- Porting our 30-file / +840-line Accord delta onto SGSP is a port, not a merge — not started, operator's call.

**How to apply:** check out `dev` on the device and locally; `upstream/Dom` stays the merge source until the operator chooses SGSP. Related: [[accord-follow-floor-0p4s-fork-0b1b09a1eb-2026-10-22]].
